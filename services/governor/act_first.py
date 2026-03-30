"""Upgrade Governor to act-first-report-after behavior.
- Auto-report completed or failed tasks via ntfy
- Auto-retry failures with different agent
- Auto-escalate sovereign tasks that fail on cloud
"""

from __future__ import annotations

import subprocess

import requests

from _imports import AGENT_SERVER_URL, NTFY_URL


NTFY_TOPIC = "athanor"
AGENT_SERVER = AGENT_SERVER_URL


def notify(title, message, priority="default", tags="robot"):
    try:
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
                f"Tags: {tags}",
                "-d",
                message,
            ],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def report_completed_tasks():
    """Report recent completed or failed canonical tasks.

    This helper no longer reads or mutates the legacy governor-local queue.
    """
    try:
        r = requests.get(f"{AGENT_SERVER}/v1/tasks?limit=50", timeout=5)
        if r.status_code != 200:
            return

        tasks = r.json().get("tasks", [])
        for task in tasks:
            prompt_preview = str(task.get("prompt", "")).strip()[:50] or str(task.get("id", "task"))
            if task.get("status") == "completed":
                notify(
                    f"Task Done: {prompt_preview}",
                    f"Completed by {task.get('assigned_runtime', '?')}. Check canonical task results.",
                    priority="default",
                    tags="white_check_mark,athanor",
                )

            if task.get("status") == "failed":
                notify(
                    f"Task Failed: {prompt_preview}",
                    f"Failed on {task.get('assigned_runtime', '?')}. Review canonical task state before retrying.",
                    priority="high",
                    tags="warning,athanor",
                )

    except Exception:
        pass


if __name__ == "__main__":
    report_completed_tasks()
