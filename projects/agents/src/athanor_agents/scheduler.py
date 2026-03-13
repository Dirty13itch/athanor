"""Proactive Agent Scheduler — scheduled autonomous agent tasks.

Agents run on configurable schedules without external triggers.
Uses the Task Execution Engine (tasks.py) for actual execution.
Schedules are defined per-agent with interval, prompt, and priority.

The scheduler runs as a background asyncio loop, checking every 30s
whether any agent's schedule has elapsed. When it has, it submits
a task to the task queue.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

SCHEDULER_KEY = "athanor:scheduler:last_run"
SCHEDULER_INTERVAL = 30.0  # Check schedules every 30s

_scheduler_task: asyncio.Task | None = None


# --- Schedule definitions ---
# Each entry: interval_seconds, prompt, priority
# Only agents with schedules are included.

DAILY_DIGEST_KEY = "athanor:scheduler:daily_digest"
PATTERN_DETECTION_KEY = "athanor:scheduler:pattern_detection"
CONSOLIDATION_KEY = "athanor:scheduler:consolidation"
ALERT_CHECK_KEY = "athanor:alerts:last_check"
WORKPLAN_MORNING_KEY = "athanor:scheduler:morning_plan"
WORKPLAN_REFILL_KEY = "athanor:workplan:last_refill_check"
CONSOLIDATION_HOUR = 3  # 3:00 AM local time
CONSOLIDATION_MINUTE = 0
DIGEST_HOUR = 6   # 6:55 AM local time
DIGEST_MINUTE = 55
PATTERN_HOUR = 5   # 5:00 AM local time
PATTERN_MINUTE = 0
WORKPLAN_HOUR = 7  # 7:00 AM local time
WORKPLAN_MINUTE = 0
ALERT_CHECK_INTERVAL = 300  # 5 minutes
WORKPLAN_REFILL_INTERVAL = 7200  # 2 hours
BENCHMARK_KEY = "athanor:scheduler:benchmark"
BENCHMARK_INTERVAL = 21600  # 6 hours
CACHE_CLEANUP_KEY = "athanor:scheduler:cache_cleanup"
CACHE_CLEANUP_INTERVAL = 3600  # 1 hour
IMPROVEMENT_CYCLE_KEY = "athanor:scheduler:improvement_cycle"
IMPROVEMENT_CYCLE_HOUR = 5
IMPROVEMENT_CYCLE_MINUTE = 30

BUILTIN_JOB_SCOPES = {
    "daily-digest": "scheduler",
    "pattern-detection": "scheduler",
    "consolidation": "scheduler",
    "morning-plan": "scheduler",
    "workplan-refill": "scheduler",
    "alert-check": "alerts",
    "benchmark-cycle": "benchmark_cycle",
    "cache-cleanup": "maintenance",
    "improvement-cycle": "benchmark_cycle",
}

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
        "interval": 3600,  # 1 hour
        "prompt": (
            "Check knowledge base health. Run get_knowledge_stats to see collection sizes. "
            "If any docs were modified recently (check timestamps), note them for re-indexing. "
            "Report collection sizes and any freshness issues."
        ),
        "priority": "low",
        "enabled": True,
    },
    "research-agent": {
        "interval": 7200,  # 2 hours
        "prompt": (
            "Check the intelligence signals pipeline. Search recent signals for "
            "high-relevance items (min_relevance=0.7). If any are actionable for "
            "Athanor (new model releases, vLLM updates, infrastructure tools), "
            "summarize the key findings. Skip if no high-relevance signals."
        ),
        "priority": "low",
        "enabled": True,
    },
    "creative-agent": {
        "interval": 14400,  # 4 hours
        "prompt": (
            "Check ComfyUI health — verify the queue endpoint responds. "
            "Report queue status (pending/running/completed). "
            "If idle, note GPU availability for creative work."
        ),
        "priority": "low",
        "enabled": True,
    },
    "coding-agent": {
        "interval": 10800,  # 3 hours
        "prompt": (
            "Run a quick code health check. Verify the agent server is responding "
            "at the /v1/agents endpoint. Check if any recent tasks had errors. "
            "Report only issues found."
        ),
        "priority": "low",
        "enabled": True,
    },
    "stash-agent": {
        "interval": 21600,  # 6 hours
        "prompt": (
            "Check Stash library stats. Look for recently added scenes that are "
            "untagged or uncategorized. Report counts of unorganized content. "
            "Only report if there are items needing attention."
        ),
        "priority": "low",
        "enabled": True,
    },
    "data-curator": {
        "interval": 21600,  # 6 hours
        "prompt": (
            "Run an autonomous data curation cycle. "
            "1. Check what's already indexed (get_scan_status). "
            "2. Scan accessible roots for new or changed files. "
            "3. Parse and index any unindexed files, prioritizing recently modified "
            "and files in high-value directories (energy audits, AI docs, finance). "
            "4. Report a summary of what was found and indexed."
        ),
        "priority": "low",
        "enabled": True,
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


def get_schedule_control_scope(job_id: str) -> str | None:
    if job_id.startswith("agent-schedule:"):
        return "scheduler"
    if job_id.startswith("research:"):
        return "research_jobs"
    return BUILTIN_JOB_SCOPES.get(job_id)


async def _governor_allows(
    *,
    job_id: str,
    job_family: str,
    owner_agent: str,
    capacity_snapshot: dict[str, Any] | None = None,
) -> bool:
    from .governor import evaluate_job_governance

    decision = await evaluate_job_governance(
        job_id=job_id,
        job_family=job_family,
        control_scope=get_schedule_control_scope(job_id),
        owner_agent=owner_agent,
        capacity_snapshot=capacity_snapshot,
    )
    return bool(decision.get("allowed"))


def _manual_job_governance_context(job_id: str) -> tuple[str, str]:
    if job_id.startswith("agent-schedule:"):
        agent = job_id.split(":", 1)[1]
        return "agent_schedule", agent
    if job_id == "daily-digest":
        return "daily_digest", "general-assistant"
    if job_id == "consolidation":
        return "consolidation", "system"
    if job_id == "pattern-detection":
        return "pattern_detection", "system"
    if job_id == "morning-plan":
        return "workplan", "system"
    if job_id == "workplan-refill":
        return "workplan_refill", "system"
    if job_id == "alert-check":
        return "alerts", "system"
    if job_id == "research:scheduler":
        return "research_jobs", "research-agent"
    if job_id.startswith("research:"):
        return "research_job", "research-agent"
    if job_id == "benchmark-cycle":
        return "benchmarks", "system"
    if job_id == "improvement-cycle":
        return "improvement_cycle", "system"
    if job_id == "cache-cleanup":
        return "cache_cleanup", "system"
    raise KeyError(job_id)


async def _emit_schedule_event(
    *,
    event_type: str,
    job_id: str,
    job_family: str,
    owner_agent: str,
    trigger_mode: str,
    summary: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    from .activity import log_event

    payload: dict[str, Any] = {
        "job_id": job_id,
        "job_family": job_family,
        "owner_agent": owner_agent,
        "trigger_mode": trigger_mode,
        "outcome": outcome,
        "summary": summary,
        "control_scope": get_schedule_control_scope(job_id),
        "error": error,
    }
    if metadata:
        payload.update(metadata)

    await log_event(
        event_type=event_type,
        agent=owner_agent,
        description=summary,
        data=payload,
    )


async def _run_agent_schedule(
    agent: str,
    schedule: dict[str, Any],
    *,
    trigger_mode: str,
    actor: str,
    force_override: bool = False,
) -> dict[str, Any]:
    from .tasks import submit_task

    interval = int(schedule["interval"])
    task = await submit_task(
        agent=agent,
        prompt=schedule["prompt"],
        priority=schedule["priority"],
        metadata={
            "source": "scheduler",
            "interval": interval,
            "trigger_mode": trigger_mode,
            "schedule_job_id": f"agent-schedule:{agent}",
            "schedule_actor": actor,
            "force_override": force_override,
        },
    )
    await _set_last_run(agent, time.time())
    summary = f"{agent} proactive task submitted"
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id=f"agent-schedule:{agent}",
        job_family="agent_schedule",
        owner_agent=agent,
        trigger_mode=trigger_mode,
        summary=summary,
        outcome="queued",
        metadata={"task_id": task.id, "interval": interval, "priority": schedule["priority"]},
    )
    return {
        "job_id": f"agent-schedule:{agent}",
        "status": "queued",
        "task_id": task.id,
        "summary": summary,
    }


async def _run_daily_digest(
    *,
    trigger_mode: str,
    actor: str,
    force_override: bool = False,
) -> dict[str, Any]:
    from .goals import generate_digest_prompt
    from .tasks import submit_task

    prompt = await generate_digest_prompt()
    task = await submit_task(
        agent="general-assistant",
        prompt=prompt,
        priority="normal",
        metadata={
            "source": "daily_digest",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "trigger_mode": trigger_mode,
            "schedule_job_id": "daily-digest",
            "schedule_actor": actor,
            "force_override": force_override,
        },
    )
    summary = "Daily digest submitted"
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="daily-digest",
        job_family="daily_digest",
        owner_agent="general-assistant",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome="queued",
        metadata={"task_id": task.id},
    )
    return {"job_id": "daily-digest", "status": "queued", "task_id": task.id, "summary": summary}


async def _check_daily_digest():
    """Check if it's time to run the daily digest (6:55 AM local)."""

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

    try:
        logger.info("Scheduler: generating daily digest")
        await _run_daily_digest(trigger_mode="daily", actor="scheduler")
        r = await _get_redis()
        await r.set(DAILY_DIGEST_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Daily digest submitted for %s", now.strftime("%Y-%m-%d"))
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="daily-digest",
            job_family="daily_digest",
            owner_agent="general-assistant",
            trigger_mode="daily",
            summary="Daily digest failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Scheduler: failed to submit daily digest: %s", e)


async def _run_consolidation_job(
    *,
    trigger_mode: str,
    actor: str,
    force_override: bool = False,
) -> dict[str, Any]:
    from .consolidation import run_consolidation

    results = await run_consolidation()
    summary = (
        f"Memory consolidation deleted {results.get('total_deleted', 0)} points "
        f"with {len(results.get('errors', []))} error(s)"
    )
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="consolidation",
        job_family="consolidation",
        owner_agent="system",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome="completed" if not results.get("errors") else "degraded",
        metadata={
            "total_deleted": results.get("total_deleted", 0),
            "actor": actor,
            "force_override": force_override,
        },
    )
    return {"job_id": "consolidation", "status": "completed", "summary": summary}


async def _check_consolidation():
    """Check if it's time to run memory consolidation (3:00 AM local)."""
    now = datetime.now()
    if now.hour != CONSOLIDATION_HOUR or now.minute != CONSOLIDATION_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(CONSOLIDATION_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception:
        pass

    try:
        logger.info("Scheduler: running memory consolidation")
        results = await _run_consolidation_job(trigger_mode="daily", actor="scheduler")
        r = await _get_redis()
        await r.set(CONSOLIDATION_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Memory consolidation completed: %s", results.get("summary", "done"))
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="consolidation",
            job_family="consolidation",
            owner_agent="system",
            trigger_mode="daily",
            summary="Memory consolidation failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Scheduler: memory consolidation failed: %s", e)


async def _run_pattern_detection_job(
    *,
    trigger_mode: str,
    actor: str,
    force_override: bool = False,
) -> dict[str, Any]:
    from .patterns import run_pattern_detection

    report = await run_pattern_detection()
    pattern_count = len(report.get("patterns", []))
    rec_count = len(report.get("recommendations", []))
    summary = f"Pattern detection produced {pattern_count} patterns and {rec_count} recommendations"
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="pattern-detection",
        job_family="pattern_detection",
        owner_agent="system",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome="completed",
        metadata={
            "pattern_count": pattern_count,
            "recommendation_count": rec_count,
            "actor": actor,
            "force_override": force_override,
        },
    )
    return {"job_id": "pattern-detection", "status": "completed", "summary": summary}


async def _check_pattern_detection():
    """Check if it's time to run daily pattern detection (5:00 AM local)."""
    now = datetime.now()
    if now.hour != PATTERN_HOUR or now.minute != PATTERN_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(PATTERN_DETECTION_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception:
        pass

    try:
        logger.info("Scheduler: running pattern detection")
        report = await _run_pattern_detection_job(trigger_mode="daily", actor="scheduler")
        r = await _get_redis()
        await r.set(PATTERN_DETECTION_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Pattern detection completed: %s", report.get("summary", "done"))
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="pattern-detection",
            job_family="pattern_detection",
            owner_agent="system",
            trigger_mode="daily",
            summary="Pattern detection failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Scheduler: pattern detection failed: %s", e)

    # Apply trust → autonomy threshold adjustments after pattern detection
    try:
        from .goals import apply_trust_adjustments
        adj_result = await apply_trust_adjustments()
        logger.info(
            "Trust adjustments applied: %d agents updated",
            adj_result.get("agent_count", 0),
        )
    except Exception as e:
        logger.warning("Scheduler: trust adjustment failed: %s", e)


async def _check_morning_plan():
    """Check if it's time to run the morning work plan (7:00 AM local)."""
    from .workplanner import generate_work_plan

    now = datetime.now()
    if now.hour != WORKPLAN_HOUR or now.minute != WORKPLAN_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(WORKPLAN_MORNING_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception:
        pass

    logger.info("Scheduler: generating morning work plan")
    try:
        plan = await generate_work_plan(focus="morning planning — prioritize creative work for EoBQ")
        r = await _get_redis()
        await r.set(WORKPLAN_MORNING_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Morning work plan generated: %d tasks (plan_id=%s)",
            plan.get("task_count", 0),
            plan.get("plan_id", "?"),
        )
    except Exception as e:
        logger.warning("Scheduler: morning work plan failed: %s", e)


async def _check_workplan_refill():
    """Check if the task queue needs refilling (every 2 hours)."""
    from .workplanner import should_refill, generate_work_plan

    try:
        r = await _get_redis()
        last_check = await r.get(WORKPLAN_REFILL_KEY)
        if last_check:
            ts = float(last_check.decode() if isinstance(last_check, bytes) else last_check)
            if time.time() - ts < WORKPLAN_REFILL_INTERVAL:
                return
    except Exception:
        pass

    try:
        if not await should_refill():
            # Still update the check timestamp so we don't re-check too often
            r = await _get_redis()
            await r.set(WORKPLAN_REFILL_KEY, str(time.time()))
            return

        logger.info("Scheduler: task queue low, generating refill work plan")
        plan = await generate_work_plan(focus="queue refill — pick up where we left off")
        r = await _get_redis()
        await r.set(WORKPLAN_REFILL_KEY, str(time.time()))
        logger.info(
            "Refill work plan generated: %d tasks (plan_id=%s)",
            plan.get("task_count", 0),
            plan.get("plan_id", "?"),
        )
    except Exception as e:
        logger.warning("Scheduler: work plan refill failed: %s", e)


async def _check_alerts():
    """Check Prometheus alerts every 5 minutes."""
    from .alerts import check_prometheus_alerts

    try:
        r = await _get_redis()
        last_check = await r.get(ALERT_CHECK_KEY)
        if last_check:
            ts = float(last_check.decode() if isinstance(last_check, bytes) else last_check)
            if time.time() - ts < ALERT_CHECK_INTERVAL:
                return
    except Exception:
        pass

    try:
        result = await check_prometheus_alerts()
        r = await _get_redis()
        await r.set(ALERT_CHECK_KEY, str(time.time()))
        if result.get("new", 0) > 0:
            logger.info(
                "Alert check: %d active, %d new",
                result["active"],
                result["new"],
            )
    except Exception as e:
        logger.warning("Alert check failed: %s", e)


async def _check_research_jobs():
    """Check for autonomous research jobs that need to run."""
    try:
        from .research_jobs import check_scheduled_jobs

        triggered = await check_scheduled_jobs()
        if triggered > 0:
            await _emit_schedule_event(
                event_type="schedule_run",
                job_id="research:scheduler",
                job_family="research_jobs",
                owner_agent="research-agent",
                trigger_mode="interval",
                summary=f"Research scheduler triggered {triggered} job(s)",
                outcome="queued",
                metadata={"triggered": triggered, "actor": "scheduler"},
            )
            logger.info("Scheduler: triggered %d research job(s)", triggered)
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="research:scheduler",
            job_family="research_jobs",
            owner_agent="research-agent",
            trigger_mode="interval",
            summary="Research scheduler check failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Scheduler: research job check failed: %s", e)


async def _check_benchmarks():
    """Run self-improvement benchmarks every 6 hours."""
    try:
        r = await _get_redis()
        last = await r.get(BENCHMARK_KEY)
        if last:
            ts = float(last.decode() if isinstance(last, bytes) else last)
            if time.time() - ts < BENCHMARK_INTERVAL:
                return
    except Exception:
        pass

    try:
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_benchmark_suite()
        r = await _get_redis()
        await r.set(BENCHMARK_KEY, str(time.time()))

        passed = result.get("passed", 0)
        total = result.get("total", 0)
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id="benchmark-cycle",
            job_family="benchmarks",
            owner_agent="system",
            trigger_mode="interval",
            summary=f"Benchmark cycle completed: {passed}/{total} passed",
            outcome="completed",
            metadata={"passed": passed, "total": total, "actor": "scheduler"},
        )
        logger.info(
            "Self-improvement benchmarks: %d/%d passed (%.0f%%)",
            passed, total, result.get("pass_rate", 0) * 100,
        )

        # Check for regressions
        for bid, comp in result.get("comparison", {}).items():
            if comp.get("regressed"):
                logger.warning(
                    "REGRESSION detected: %s (%.1f → %.1f)",
                    bid, comp.get("baseline", 0), comp.get("new", 0),
                )
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="benchmark-cycle",
            job_family="benchmarks",
            owner_agent="system",
            trigger_mode="interval",
            summary="Benchmark cycle failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Benchmark run failed: %s", e)


async def _check_improvement_cycle():
    """Run the self-improvement cycle at 5:30 AM (after pattern detection at 5:00 AM).

    This is the self-feeding loop: benchmarks → read patterns → generate proposals.
    """
    from .self_improvement import get_improvement_engine

    now = datetime.now()
    if now.hour != IMPROVEMENT_CYCLE_HOUR or now.minute != IMPROVEMENT_CYCLE_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(IMPROVEMENT_CYCLE_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception:
        pass

    logger.info("Scheduler: running self-improvement cycle")
    try:
        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_improvement_cycle()
        r = await _get_redis()
        await r.set(IMPROVEMENT_CYCLE_KEY, now.strftime("%Y-%m-%d"))
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id="improvement-cycle",
            job_family="improvement_cycle",
            owner_agent="system",
            trigger_mode="daily",
            summary=(
                f"Improvement cycle generated {result.get('proposals_generated', 0)} proposals "
                f"from {result.get('patterns_consumed', 0)} patterns"
            ),
            outcome="completed",
            metadata={
                "proposals_generated": result.get("proposals_generated", 0),
                "patterns_consumed": result.get("patterns_consumed", 0),
                "actor": "scheduler",
            },
        )
        logger.info(
            "Self-improvement cycle: %d proposals generated, %d patterns consumed",
            result.get("proposals_generated", 0),
            result.get("patterns_consumed", 0),
        )
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="improvement-cycle",
            job_family="improvement_cycle",
            owner_agent="system",
            trigger_mode="daily",
            summary="Improvement cycle failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Scheduler: improvement cycle failed: %s", e)


async def _check_cache_cleanup():
    """Clean expired semantic cache entries every hour."""
    try:
        r = await _get_redis()
        last = await r.get(CACHE_CLEANUP_KEY)
        if last:
            ts = float(last.decode() if isinstance(last, bytes) else last)
            if time.time() - ts < CACHE_CLEANUP_INTERVAL:
                return
    except Exception:
        pass

    try:
        from .semantic_cache import get_semantic_cache

        cache = get_semantic_cache()
        deleted = await cache.cleanup_expired()
        r = await _get_redis()
        await r.set(CACHE_CLEANUP_KEY, str(time.time()))
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id="cache-cleanup",
            job_family="cache_cleanup",
            owner_agent="system",
            trigger_mode="interval",
            summary=f"Semantic cache cleanup removed {deleted} expired entries",
            outcome="completed",
            metadata={"deleted": deleted, "actor": "scheduler"},
        )
        if deleted > 0:
            logger.info("Semantic cache cleanup: %d expired entries removed", deleted)
    except Exception as e:
        await _emit_schedule_event(
            event_type="schedule_failed",
            job_id="cache-cleanup",
            job_family="cache_cleanup",
            owner_agent="system",
            trigger_mode="interval",
            summary="Semantic cache cleanup failed",
            outcome="failed",
            error=str(e),
        )
        logger.warning("Cache cleanup failed: %s", e)


async def run_scheduled_job(
    job_id: str,
    actor: str = "operator",
    *,
    force: bool = False,
) -> dict[str, Any]:
    from .governor import build_capacity_snapshot, evaluate_job_governance

    job_family, owner_agent = _manual_job_governance_context(job_id)
    capacity_snapshot = await build_capacity_snapshot()
    governance = await evaluate_job_governance(
        job_id=job_id,
        job_family=job_family,
        control_scope=get_schedule_control_scope(job_id),
        owner_agent=owner_agent,
        capacity_snapshot=capacity_snapshot,
    )
    if not governance.get("allowed") and not force:
        summary = (
            f"Governor deferred manual run for {job_id}: "
            f"{str(governance.get('reason') or 'not permitted under current posture')}"
        )
        await _emit_schedule_event(
            event_type="schedule_skipped",
            job_id=job_id,
            job_family=job_family,
            owner_agent=owner_agent,
            trigger_mode="manual",
            summary=summary,
            outcome="deferred",
            metadata={
                "actor": actor,
                "governor_status": governance.get("status"),
                "presence_state": governance.get("presence_state"),
                "release_tier": governance.get("release_tier"),
                "capacity_posture": governance.get("capacity_posture"),
                "queue_posture": governance.get("queue_posture"),
                "provider_posture": governance.get("provider_posture"),
                "active_window_ids": governance.get("active_window_ids"),
                "deferred_by": governance.get("deferred_by"),
                "force_override": False,
            },
        )
        return {
            "job_id": job_id,
            "status": "deferred",
            "summary": summary,
            "governor_decision": governance,
            "override_available": True,
        }

    if job_id.startswith("agent-schedule:"):
        agent = job_id.split(":", 1)[1]
        schedule = AGENT_SCHEDULES.get(agent)
        if not schedule:
            raise KeyError(job_id)
        return await _run_agent_schedule(
            agent,
            schedule,
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "daily-digest":
        return await _run_daily_digest(trigger_mode="manual", actor=actor, force_override=force)

    if job_id == "consolidation":
        return await _run_consolidation_job(
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "pattern-detection":
        return await _run_pattern_detection_job(
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "morning-plan":
        from .workplanner import generate_work_plan

        plan = await generate_work_plan(focus="morning planning - prioritize creative work for EoBQ")
        summary = f"Manual morning work plan generated with {plan.get('task_count', 0)} tasks"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="workplan",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "plan_id": plan.get("plan_id"),
                "task_count": plan.get("task_count", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary, "plan_id": plan.get("plan_id")}

    if job_id == "workplan-refill":
        from .workplanner import generate_work_plan, should_refill

        needs_refill = await should_refill()
        if not needs_refill:
            summary = "Manual workplan refill skipped because queue posture is healthy"
            await _emit_schedule_event(
                event_type="schedule_skipped",
                job_id=job_id,
                job_family="workplan_refill",
                owner_agent="system",
                trigger_mode="manual",
                summary=summary,
                outcome="skipped",
                metadata={"actor": actor, "force_override": force},
            )
            return {"job_id": job_id, "status": "skipped", "summary": summary}

        plan = await generate_work_plan(focus="queue refill - pick up where we left off")
        summary = f"Manual workplan refill generated {plan.get('task_count', 0)} tasks"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="workplan_refill",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "plan_id": plan.get("plan_id"),
                "task_count": plan.get("task_count", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary, "plan_id": plan.get("plan_id")}

    if job_id == "alert-check":
        from .alerts import check_prometheus_alerts

        result = await check_prometheus_alerts()
        summary = f"Manual alert check saw {result.get('active', 0)} active and {result.get('new', 0)} new alerts"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="alerts",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if result.get("checked") else "failed",
            metadata={
                "active": result.get("active", 0),
                "new": result.get("new", 0),
                "actor": actor,
                "force_override": force,
            },
            error=str(result.get("error", "")) if result.get("error") else "",
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "research:scheduler":
        from .research_jobs import check_scheduled_jobs

        triggered = await check_scheduled_jobs()
        summary = f"Manual research scheduler run triggered {triggered} job(s)"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="research_jobs",
            owner_agent="research-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="queued" if triggered > 0 else "completed",
            metadata={"triggered": triggered, "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "queued" if triggered > 0 else "completed", "summary": summary}

    if job_id.startswith("research:"):
        from .research_jobs import execute_job

        research_job_id = job_id.split(":", 1)[1]
        result = await execute_job(research_job_id)
        if result.get("error"):
            await _emit_schedule_event(
                event_type="schedule_failed",
                job_id=job_id,
                job_family="research_job",
                owner_agent="research-agent",
                trigger_mode="manual",
                summary="Research job execution failed",
                outcome="failed",
                error=str(result["error"]),
            )
            return {"job_id": job_id, "status": "failed", "summary": str(result["error"])}

        summary = f"Research job {research_job_id} submitted"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="research_job",
            owner_agent="research-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="queued",
            metadata={"task_id": result.get("task_id"), "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "queued", "task_id": result.get("task_id"), "summary": summary}

    if job_id == "benchmark-cycle":
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_benchmark_suite()
        summary = f"Manual benchmark cycle completed: {result.get('passed', 0)}/{result.get('total', 0)} passed"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="benchmarks",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "passed": result.get("passed", 0),
                "total": result.get("total", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "improvement-cycle":
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_improvement_cycle()
        summary = (
            f"Manual improvement cycle generated {result.get('proposals_generated', 0)} proposals "
            f"from {result.get('patterns_consumed', 0)} patterns"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="improvement_cycle",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "cache-cleanup":
        from .semantic_cache import get_semantic_cache

        cache = get_semantic_cache()
        deleted = await cache.cleanup_expired()
        summary = f"Manual cache cleanup removed {deleted} expired entries"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="cache_cleanup",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"deleted": deleted, "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    raise KeyError(job_id)


async def _scheduler_loop():
    """Background scheduler — checks agent schedules and submits tasks."""
    from .governor import build_capacity_snapshot, is_automation_paused

    logger.info("Proactive scheduler started (interval=%.0fs)", SCHEDULER_INTERVAL)

    # Wait 60s after startup before first check (let everything initialize)
    await asyncio.sleep(60)

    while True:
        try:
            now = time.time()
            capacity_snapshot = await build_capacity_snapshot()

            if not await is_automation_paused("alerts") and await _governor_allows(
                job_id="alert-check",
                job_family="alerts",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            ):
                await _check_alerts()

            if not await is_automation_paused("scheduler"):
                await _check_consolidation()
                await _check_pattern_detection()
                await _check_daily_digest()
                await _check_morning_plan()
                await _check_workplan_refill()

            if not await is_automation_paused("research_jobs") and await _governor_allows(
                job_id="research:scheduler",
                job_family="research_jobs",
                owner_agent="research-agent",
                capacity_snapshot=capacity_snapshot,
            ):
                await _check_research_jobs()

            if not await is_automation_paused("benchmark_cycle") and await _governor_allows(
                job_id="improvement-cycle",
                job_family="improvement_cycle",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            ):
                await _check_improvement_cycle()
            if not await is_automation_paused("benchmark_cycle") and await _governor_allows(
                job_id="benchmark-cycle",
                job_family="benchmarks",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            ):
                await _check_benchmarks()

            if not await is_automation_paused("maintenance") and await _governor_allows(
                job_id="cache-cleanup",
                job_family="cache_cleanup",
                owner_agent="system",
                capacity_snapshot=capacity_snapshot,
            ):
                await _check_cache_cleanup()

            if not await is_automation_paused("scheduler"):
                for agent, schedule in AGENT_SCHEDULES.items():
                    if not schedule.get("enabled", True):
                        continue

                    interval = schedule["interval"]
                    last_run = await _get_last_run(agent)

                    if now - last_run >= interval:
                        if not await _governor_allows(
                            job_id=f"agent-schedule:{agent}",
                            job_family="agent_schedule",
                            owner_agent=agent,
                            capacity_snapshot=capacity_snapshot,
                        ):
                            continue
                        logger.info(
                            "Scheduler: submitting proactive task for %s (interval=%ds)",
                            agent, interval,
                        )
                        try:
                            await _run_agent_schedule(agent, schedule, trigger_mode="interval", actor="scheduler")
                        except Exception as e:
                            await _emit_schedule_event(
                                event_type="schedule_failed",
                                job_id=f"agent-schedule:{agent}",
                                job_family="agent_schedule",
                                owner_agent=agent,
                                trigger_mode="interval",
                                summary=f"{agent} proactive task failed",
                                outcome="failed",
                                error=str(e),
                            )
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


async def get_model_intelligence_cadence() -> list[dict[str, Any]]:
    now = time.time()
    schedule_status = await get_schedule_status()
    research_schedule = next(
        (entry for entry in schedule_status.get("schedules", []) if entry.get("agent") == "research-agent"),
        None,
    )

    async def _read_marker(key: str) -> str | None:
        try:
            redis = await _get_redis()
            raw = await redis.get(key)
            if not raw:
                return None
            value = raw.decode() if isinstance(raw, bytes) else str(raw)
            if value.count("-") == 2 and len(value) == 10:
                return datetime.strptime(value, "%Y-%m-%d").isoformat()
            return datetime.fromtimestamp(float(value)).isoformat()
        except Exception:
            return None

    cadence = [
        {
            "id": "agent-schedule:research-agent",
            "title": "Weekly horizon scan posture",
            "cadence": research_schedule.get("interval_human", "interval") if research_schedule else "interval",
            "last_run": datetime.fromtimestamp(research_schedule.get("last_run")).isoformat()
            if research_schedule and research_schedule.get("last_run")
            else None,
            "next_run": datetime.fromtimestamp(
                now + int(research_schedule.get("next_run_in", 0) or 0)
            ).isoformat()
            if research_schedule
            else None,
            "owner_agent": "research-agent",
            "job_family": "agent_schedule",
        },
        {
            "id": "benchmark-cycle",
            "title": "Monthly champion rebaseline posture",
            "cadence": "every 6h",
            "last_run": await _read_marker(BENCHMARK_KEY),
            "next_run": datetime.fromtimestamp(now + BENCHMARK_INTERVAL).isoformat(),
            "owner_agent": "system",
            "job_family": "benchmarks",
        },
        {
            "id": "improvement-cycle",
            "title": "Weekly candidate triage posture",
            "cadence": "daily 5:30",
            "last_run": await _read_marker(IMPROVEMENT_CYCLE_KEY),
            "next_run": _next_daily_occurrence(IMPROVEMENT_CYCLE_HOUR, IMPROVEMENT_CYCLE_MINUTE),
            "owner_agent": "system",
            "job_family": "improvement_cycle",
        },
    ]

    items: list[dict[str, Any]] = []
    for entry in cadence:
        decision = await _governor_allows(
            job_id=str(entry["id"]),
            job_family=str(entry["job_family"]),
            owner_agent=str(entry["owner_agent"]),
        )
        items.append(
            {
                "id": str(entry["id"]),
                "title": str(entry["title"]),
                "cadence": str(entry["cadence"]),
                "current_state": "scheduled" if decision else "deferred",
                "last_run": entry.get("last_run"),
                "next_run": entry.get("next_run"),
                "last_outcome": "scheduled",
                "paused": False,
                "governor_reason": None
                if decision
                else "Governor deferred this cadence under current presence or release posture.",
            }
        )
    return items


def _humanize_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}min"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def _next_daily_occurrence(hour: int, minute: int) -> str:
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate.isoformat()


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
