"""Continuous Dispatch Loop — runs as part of the Governor service.
Checks for queued tasks every 60 seconds and dispatches immediately.
No waiting for 10pm. Agents work ALL THE TIME.
"""
import asyncio
import subprocess
from task_monitor import monitor_tasks
from act_first import report_completed_tasks
import logging
import time
from datetime import datetime, timezone

# Per-subscription cooldown (minutes between dispatches)
SUBSCRIPTION_COOLDOWN = {
    "claude-max": 5,        # 5 min between Claude tasks (preserve 5hr quota)
    "chatgpt-pro": 5,       # Same for Codex
    "copilot-pro-plus": 2,  # Copilot GPT-5 mini is unlimited, can go faster
    "kimi-code": 10,        # Kimi has token-based billing
    "glm-zai": 10,          # GLM has monthly quota
    "gemini-advanced": 5,   # Gemini free tier: 1000/day
    "local-opencode": 1,    # Local = free, go fast
    "local-aider": 1,
    "local-goose": 1,
}
last_dispatch_time: dict[str, float] = {}

# Subscription priority tiers — try cloud first to maximize burn, local as overflow
DISPATCH_ORDER = [
    # Tier 1: $200/mo powerhouses — burn these first
    "claude-max", "chatgpt-pro",
    # Tier 2: Paid subs — keep busy
    "copilot-pro-plus", "kimi-code", "glm-zai", "gemini-advanced",
    # Tier 3: Local/free — overflow capacity
    "local-aider", "local-opencode", "local-goose",
]

# Maximum time (seconds) a task can run before being killed
TASK_TIMEOUT_SECONDS = 20 * 60  # 20 minutes

logger = logging.getLogger("governor.continuous")


def kill_timed_out_tasks(active_agents, task_queue):
    """Kill agent sessions that have been running longer than TASK_TIMEOUT_SECONDS.
    Returns list of task IDs that were killed.
    """
    killed = []
    now = time.time()

    # Iterate over a copy since we modify during iteration
    for task_id, agent_info in list(active_agents.items()):
        dispatch_time = agent_info.get("dispatch_time")
        if dispatch_time is None:
            continue

        elapsed = now - dispatch_time
        if elapsed > TASK_TIMEOUT_SECONDS:
            session_name = agent_info.get("session", "")
            elapsed_min = int(elapsed / 60)
            logger.warning(f"Task {task_id} timed out after {elapsed_min}m — killing session {session_name}")

            # Kill the tmux session
            if session_name:
                try:
                    subprocess.run(
                        ["tmux", "kill-session", "-t", session_name],
                        capture_output=True, timeout=10
                    )
                except Exception as e:
                    logger.error(f"Failed to kill tmux session {session_name}: {e}")

            # Update task status in the in-memory queue
            for task in task_queue:
                if task["id"] == task_id:
                    task["status"] = "failed"
                    task["completed_at"] = datetime.now(timezone.utc).isoformat()
                    task["result"] = f"timeout: killed after {elapsed_min} minutes"
                    break

            # Remove from active agents
            del active_agents[task_id]
            killed.append(task_id)

    return killed


async def continuous_dispatch_loop(app_state):
    """Background task that continuously dispatches queued tasks."""
    logger.info("Continuous dispatch loop started — agents work 24/7")

    while True:
        try:
            await asyncio.sleep(60)  # Check every 60 seconds

            # Report completed/failed tasks (act first, report after)
            try:
                report_completed_tasks()
            except Exception as e:
                logger.error(f"Report error: {e}")

            # Monitor running tasks for completion
            try:
                from main import task_queue as tq, active_agents as aa
                import db

                # Kill timed-out tasks before monitoring
                killed_ids = kill_timed_out_tasks(aa, tq)
                for kid in killed_ids:
                    try:
                        # Find the task to get the result text
                        result_text = "timeout: killed after 20 minutes"
                        for t in tq:
                            if t["id"] == kid:
                                result_text = t.get("result", result_text)
                                break
                        db.update_task_status(kid, "failed", result=result_text)
                        logger.info(f"Task {kid} -> failed: {result_text}")
                    except Exception as db_err:
                        logger.error(f"DB update error for timed-out {kid}: {db_err}")

                updated = monitor_tasks(tq, aa)
                if updated:
                    for u in updated:
                        try:
                            db.update_task_status(
                                u["task_id"],
                                u["new_status"],
                                result=u.get("result", "status updated by monitor")
                            )
                        except Exception as db_err:
                            logger.error(f"DB update error for {u['task_id']}: {db_err}")
                    for u in updated:
                        logger.info(f"Task {u['task_id']} -> {u['new_status']}: {u.get('result', '')[:80]}")
            except Exception as e:
                logger.error(f"Monitor error: {e}")

            # Import here to avoid circular imports
            from main import task_queue, SUBSCRIPTIONS, active_agents
            import db
            from dispatch import dispatch_task

            # Load queued tasks from BOTH stores (in-memory + SQLite)
            db_tasks = db.get_queued_tasks(limit=20)
            in_memory_ids = {t["id"] for t in task_queue}
            for dt in db_tasks:
                if dt["id"] not in in_memory_ids:
                    task_queue.append(dt)
                    in_memory_ids.add(dt["id"])

            queued = [t for t in task_queue if t["status"] == "queued"]
            if not queued:
                continue

            # Find available subscriptions (not already running a task)
            busy_subs = set()
            for a in active_agents.values():
                sub = a.get("subscription") or a.get("assigned_to")
                if sub:
                    busy_subs.add(sub)

            for task in queued:
                # Content class determines eligible candidates
                if task.get("content_class") == "sovereign_only":
                    candidates = ["local-aider", "local-opencode", "local-goose"]
                elif task.get("complexity") == "critical":
                    candidates = ["claude-max", "chatgpt-pro"]
                elif task.get("complexity") == "high":
                    candidates = ["claude-max", "chatgpt-pro", "copilot-pro-plus"]
                elif task.get("complexity") == "low":
                    candidates = ["copilot-pro-plus", "local-aider", "local-opencode", "local-goose"]
                else:
                    # Medium — use DISPATCH_ORDER to maximize paid sub burn
                    candidates = DISPATCH_ORDER

                # Find first available candidate respecting cooldowns
                dispatched = False
                for sub in candidates:
                    if sub in busy_subs:
                        continue
                    if SUBSCRIPTIONS.get(sub, {}).get("status") != "active":
                        continue

                    # Check cooldown
                    cooldown = SUBSCRIPTION_COOLDOWN.get(sub, 5) * 60
                    last = last_dispatch_time.get(sub, 0)
                    if time.time() - last < cooldown:
                        continue

                    task["assigned_to"] = sub
                    task["status"] = "running"

                    try:
                        result = dispatch_task(task, sub)
                        # Track dispatch time for timeout enforcement
                        result["dispatch_time"] = time.time()
                        active_agents[task["id"]] = result
                        busy_subs.add(sub)
                        last_dispatch_time[sub] = time.time()
                        try:
                            db.update_task_status(task["id"], "running", assigned_to=sub)
                        except Exception as db_err:
                            logger.error(f"DB status update error: {db_err}")
                        logger.info(f"Dispatched {task['id']} to {sub}: {task['title'][:50]}")
                        dispatched = True
                    except Exception as e:
                        task["status"] = "queued"
                        task["assigned_to"] = None
                        logger.error(f"Dispatch failed for {task['id']} to {sub}: {e}")
                    break

        except Exception as e:
            logger.error(f"Continuous dispatch error: {e}")
            await asyncio.sleep(30)
