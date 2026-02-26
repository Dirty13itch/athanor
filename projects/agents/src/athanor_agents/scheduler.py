"""Proactive Agent Scheduler — scheduled autonomous agent tasks.

Agents run on configurable schedules without external triggers.
Uses the Task Execution Engine (tasks.py) for actual execution.
Schedules are defined per-agent with interval, prompt, and priority.

The scheduler runs as a background asyncio loop, checking every 30s
whether any agent's schedule has elapsed. When it has, it submits
a task to the task queue.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)

SCHEDULER_KEY = "athanor:scheduler:last_run"
SCHEDULER_INTERVAL = 30.0  # Check schedules every 30s

_scheduler_task: asyncio.Task | None = None


# --- Schedule definitions ---
# Each entry: interval_seconds, prompt, priority
# Only agents with schedules are included.

DAILY_DIGEST_KEY = "athanor:scheduler:daily_digest"
DIGEST_HOUR = 6   # 6:55 AM local time
DIGEST_MINUTE = 55

AGENT_SCHEDULES = {
    "general-assistant": {
        "interval": 1800,  # 30 min
        "prompt": (
            "Run a system health check. Check all service health, GPU status, "
            "and report anything that's down or degraded. Only report issues — "
            "don't list services that are working fine unless everything is healthy."
        ),
        "priority": "normal",
        "enabled": True,
    },
    "media-agent": {
        "interval": 900,  # 15 min
        "prompt": (
            "Check for any active downloads, new additions, or queue items in "
            "Sonarr and Radarr. Check Plex for current activity. Report only "
            "notable items — active downloads, new content added, or streams in progress."
        ),
        "priority": "low",
        "enabled": True,
    },
    "home-agent": {
        "interval": 300,  # 5 min
        "prompt": (
            "Check the current state of all Home Assistant entities. "
            "Report any unusual states, recently triggered automations, "
            "or entities that seem anomalous. If everything looks normal, "
            "report a brief status summary."
        ),
        "priority": "low",
        "enabled": True,
    },
    "knowledge-agent": {
        "interval": 86400,  # 24 hours
        "prompt": (
            "Check the knowledge base stats. Report total documents indexed, "
            "collection sizes, and the most recently indexed documents. "
            "Identify any gaps in coverage."
        ),
        "priority": "low",
        "enabled": False,  # Enable when re-indexing is wired
    },
}


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def _get_last_run(agent: str) -> float:
    """Get the last scheduled run timestamp for an agent."""
    try:
        r = await _get_redis()
        ts = await r.hget(SCHEDULER_KEY, agent)
        return float(ts) if ts else 0.0
    except Exception:
        return 0.0


async def _set_last_run(agent: str, timestamp: float):
    """Record the last scheduled run timestamp."""
    try:
        r = await _get_redis()
        await r.hset(SCHEDULER_KEY, agent, str(timestamp))
    except Exception as e:
        logger.warning("Failed to set last run for %s: %s", agent, e)


async def _check_daily_digest():
    """Check if it's time to run the daily digest (6:55 AM local)."""
    from .tasks import submit_task
    from .goals import generate_digest_prompt

    now = datetime.now()
    if now.hour != DIGEST_HOUR or now.minute != DIGEST_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(DAILY_DIGEST_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception:
        pass

    logger.info("Scheduler: generating daily digest")
    try:
        prompt = await generate_digest_prompt()
        await submit_task(
            agent="general-assistant",
            prompt=prompt,
            priority="normal",
            metadata={"source": "daily_digest", "date": now.strftime("%Y-%m-%d")},
        )
        r = await _get_redis()
        await r.set(DAILY_DIGEST_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Daily digest submitted for %s", now.strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning("Scheduler: failed to submit daily digest: %s", e)


async def _scheduler_loop():
    """Background scheduler — checks agent schedules and submits tasks."""
    from .tasks import submit_task

    logger.info("Proactive scheduler started (interval=%.0fs)", SCHEDULER_INTERVAL)

    # Wait 60s after startup before first check (let everything initialize)
    await asyncio.sleep(60)

    while True:
        try:
            now = time.time()

            # Check time-of-day tasks
            await _check_daily_digest()

            for agent, schedule in AGENT_SCHEDULES.items():
                if not schedule.get("enabled", True):
                    continue

                interval = schedule["interval"]
                last_run = await _get_last_run(agent)

                if now - last_run >= interval:
                    logger.info(
                        "Scheduler: submitting proactive task for %s (interval=%ds)",
                        agent, interval,
                    )
                    try:
                        await submit_task(
                            agent=agent,
                            prompt=schedule["prompt"],
                            priority=schedule["priority"],
                            metadata={"source": "scheduler", "interval": interval},
                        )
                        await _set_last_run(agent, now)
                    except Exception as e:
                        logger.warning("Scheduler: failed to submit task for %s: %s", agent, e)

        except Exception as e:
            logger.warning("Scheduler loop error: %s", e)

        await asyncio.sleep(SCHEDULER_INTERVAL)


async def get_schedule_status() -> dict:
    """Get current schedule status for all agents."""
    now = time.time()
    statuses = []

    for agent, schedule in AGENT_SCHEDULES.items():
        last_run = await _get_last_run(agent)
        next_run = last_run + schedule["interval"] if last_run else now
        time_until = max(0, next_run - now)

        statuses.append({
            "agent": agent,
            "interval_seconds": schedule["interval"],
            "interval_human": _humanize_interval(schedule["interval"]),
            "enabled": schedule.get("enabled", True),
            "last_run": last_run if last_run else None,
            "next_run_in": int(time_until),
            "priority": schedule["priority"],
        })

    return {
        "schedules": statuses,
        "scheduler_running": _scheduler_task is not None and not _scheduler_task.done(),
    }


def _humanize_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}min"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


async def start_scheduler():
    """Start the proactive agent scheduler."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.info("Scheduler already running")
        return

    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Proactive agent scheduler started")


async def stop_scheduler():
    """Stop the proactive agent scheduler."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("Proactive agent scheduler stopped")
