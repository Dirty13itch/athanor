"""Overnight compatibility helper for the canonical task engine.
Runs at 10pm, dispatches pending canonical tasks, and sends a summary.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime

from _imports import AGENT_SERVER_URL, NTFY_URL


NTFY_TOPIC = "athanor"
TASK_API_URL = AGENT_SERVER_URL


def notify(title: str, message: str, priority: str = "default"):
    """Send ntfy notification."""
    subprocess.run(
        [
            "curl",
            "-sf",
            "-X",
            "POST",
            f"{NTFY_URL}/{NTFY_TOPIC}",
            "-H",
            f"Title: {title}",
            "-H",
            f"Priority: {priority}",
            "-H",
            "Tags: robot,athanor",
            "-d",
            message,
        ],
        capture_output=True,
    )


def get_pending_tasks():
    """Get current pending tasks from the canonical task engine."""
    result = subprocess.run(
        ["curl", "-sf", f"{TASK_API_URL}/v1/tasks?status=pending&limit=50"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return json.loads(result.stdout).get("tasks", [])
    return []


def dispatch_task():
    """Tell the canonical task engine to dispatch the next pending task."""
    payload = json.dumps(
        {
            "actor": "overnight-governor",
            "session_id": "overnight-governor",
            "correlation_id": uuid.uuid4().hex,
            "reason": "Overnight dispatch cycle",
        }
    )
    result = subprocess.run(
        [
            "curl",
            "-sf",
            "-X",
            "POST",
            f"{TASK_API_URL}/v1/tasks/dispatch",
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None


def run_overnight():
    """Main overnight pipeline."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    tasks = get_pending_tasks()
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]

    if not pending_tasks:
        notify("Overnight: No Pending Tasks", f"No pending tasks at {timestamp}. Add tasks to /v1/tasks.", "low")
        return

    notify(
        "Overnight Starting",
        f"{len(pending_tasks)} pending tasks at {timestamp}. Dispatching...",
        "default",
    )

    dispatched = []
    max_agents = min(5, len(pending_tasks))

    for _ in range(max_agents):
        result = dispatch_task()
        if result and result.get("task_id"):
            dispatched.append(result)
            notify(
                f"Agent Dispatched: {result.get('agent', '?')}",
                f"Task {result.get('task_id', '?')} assigned to {result.get('assigned_to', '?')} in {result.get('session', '?')}",
                "low",
            )

    if dispatched:
        notify(
            f"Overnight: {len(dispatched)} Agents Running",
            f"Dispatched: {', '.join(d.get('agent', '?') for d in dispatched)}. Check in the morning.",
            "default",
        )
    else:
        notify("Overnight: Dispatch Failed", "No agents could be dispatched. Check task-engine and agent-server logs.", "high")


if __name__ == "__main__":
    run_overnight()
