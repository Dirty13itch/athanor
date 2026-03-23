"""Continuous Dispatch Loop — runs as part of the Governor service.
Checks for queued tasks every 60 seconds and dispatches immediately.
No waiting for 10pm. Agents work ALL THE TIME.
"""
import asyncio
from task_monitor import monitor_tasks
from act_first import report_completed_tasks
import logging
from datetime import datetime

# Per-subscription cooldown (minutes between dispatches)
SUBSCRIPTION_COOLDOWN = {
    "claude-max": 5,       # 5 min between Claude tasks (preserve 5hr quota)
    "chatgpt-pro": 5,      # Same for Codex
    "copilot-pro-plus": 2,  # Copilot GPT-5 mini is unlimited, can go faster
    "kimi-code": 10,        # Kimi has token-based billing
    "glm-zai": 10,          # GLM has monthly quota
    "gemini-advanced": 5,   # Gemini free tier: 1000/day
    "local-opencode": 1,    # Local = free, go fast
    "local-aider": 1,
    "local-goose": 1,
}
last_dispatch_time: dict[str, float] = {}

logger = logging.getLogger("governor.continuous")

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
                updated = monitor_tasks(tq, aa)
                if updated:
                    for u in updated:
                        try:
                            db.update_task_status(u["task_id"], u["new_status"], result="completed by agent")
                        except: pass
                    for u in updated:
                        logger.info(f"Task {u['task_id']} completed: {u['new_status']}")
            except Exception as e:
                logger.error(f"Monitor error: {e}")

            # Import here to avoid circular imports
            from main import task_queue, SUBSCRIPTIONS, active_agents
            import db

            # Load queued tasks from BOTH stores (in-memory + SQLite)
            db_tasks = db.get_queued_tasks(limit=20)
            # Merge: in-memory tasks + SQLite tasks (deduplicate by id)
            in_memory_ids = {t["id"] for t in task_queue}
            for dt in db_tasks:
                if dt["id"] not in in_memory_ids:
                    task_queue.append(dt)
                    in_memory_ids.add(dt["id"])
            from dispatch import dispatch_task

            queued = [t for t in task_queue if t["status"] == "queued"]
            if not queued:
                continue

            # Find available subscription (not already running a task)
            busy_subs = set(a.get("assigned_to") for a in active_agents.values())

            for task in queued:
                # Content class check first
                if task.get("content_class") == "sovereign_only":
                    candidates = ["local-opencode", "local-aider", "local-goose"]
                elif task["complexity"] == "critical":
                    candidates = ["claude-max"]
                elif task["complexity"] == "high":
                    candidates = ["claude-max", "chatgpt-pro"]
                elif task["complexity"] == "low":
                    candidates = ["local-aider", "local-opencode", "copilot-pro-plus"]
                else:
                    candidates = ["claude-max", "local-opencode", "chatgpt-pro"]

                # Find first available candidate (with rate limiting)
                import time
                for sub in candidates:
                    if sub not in busy_subs and SUBSCRIPTIONS.get(sub, {}).get("status") == "active":
                        # Check cooldown
                        cooldown = SUBSCRIPTION_COOLDOWN.get(sub, 5) * 60
                        last = last_dispatch_time.get(sub, 0)
                        if time.time() - last < cooldown:
                            continue  # Skip, still in cooldown
                        task["assigned_to"] = sub
                        task["status"] = "running"

                        try:
                            result = dispatch_task(task, sub)
                            active_agents[task["id"]] = result
                            busy_subs.add(sub)
                            last_dispatch_time[sub] = time.time()
                            try:
                                db.update_task_status(task["id"], "running", assigned_to=sub)
                            except: pass
                            logger.info(f"Dispatched {task['id']} to {sub}: {task['title'][:50]}")
                        except Exception as e:
                            task["status"] = "queued"  # Reset on failure
                            task["assigned_to"] = None
                            logger.error(f"Dispatch failed for {task['id']}: {e}")
                        break

        except Exception as e:
            logger.error(f"Continuous dispatch error: {e}")
            await asyncio.sleep(30)
