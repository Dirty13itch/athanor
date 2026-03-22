"""Continuous Dispatch Loop — runs as part of the Governor service.
Checks for queued tasks every 60 seconds and dispatches immediately.
No waiting for 10pm. Agents work ALL THE TIME.
"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("governor.continuous")

async def continuous_dispatch_loop(app_state):
    """Background task that continuously dispatches queued tasks."""
    logger.info("Continuous dispatch loop started — agents work 24/7")

    while True:
        try:
            await asyncio.sleep(60)  # Check every 60 seconds

            # Import here to avoid circular imports
            from main import task_queue, SUBSCRIPTIONS, active_agents
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

                # Find first available candidate
                for sub in candidates:
                    if sub not in busy_subs and SUBSCRIPTIONS.get(sub, {}).get("status") == "active":
                        task["assigned_to"] = sub
                        task["status"] = "running"

                        try:
                            result = dispatch_task(task, sub)
                            active_agents[task["id"]] = result
                            busy_subs.add(sub)
                            logger.info(f"Dispatched {task['id']} to {sub}: {task['title'][:50]}")
                        except Exception as e:
                            task["status"] = "queued"  # Reset on failure
                            task["assigned_to"] = None
                            logger.error(f"Dispatch failed for {task['id']}: {e}")
                        break

        except Exception as e:
            logger.error(f"Continuous dispatch error: {e}")
            await asyncio.sleep(30)
