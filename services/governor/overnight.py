"""Overnight Coding Pipeline for the Governor.
Runs at 10pm, dispatches tasks to all available subscription agents,
monitors progress, and sends morning summary.
"""
import subprocess
import json
import os
from datetime import datetime

import os
NTFY_URL = os.environ.get("NTFY_URL", "http://192.168.1.203:8880")
NTFY_TOPIC = "athanor"
GOVERNOR_URL = "http://localhost:8760"

def notify(title: str, message: str, priority: str = "default"):
    """Send ntfy notification."""
    subprocess.run([
        "curl", "-sf", "-X", "POST", NTFY_URL + "/" + NTFY_TOPIC,
        "-H", f"Title: {title}",
        "-H", f"Priority: {priority}",
        "-H", "Tags: robot,athanor",
        "-d", message
    ], capture_output=True)

def get_queue():
    """Get current task queue from governor."""
    result = subprocess.run(
        ["curl", "-sf", GOVERNOR_URL + "/queue"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout).get("tasks", [])
    return []

def dispatch_task():
    """Tell governor to dispatch next task."""
    result = subprocess.run(
        ["curl", "-sf", "-X", "POST", GOVERNOR_URL + "/dispatch-and-run"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None

def run_overnight():
    """Main overnight pipeline."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Check queue
    tasks = get_queue()
    queued = [t for t in tasks if t["status"] == "queued"]
    
    if not queued:
        notify("Overnight: No Tasks", f"Queue empty at {timestamp}. Add tasks to /queue.", "low")
        return
    
    notify(
        "Overnight Starting",
        f"{len(queued)} tasks in queue at {timestamp}. Dispatching...",
        "default"
    )
    
    # Dispatch up to 5 agents (practical ceiling)
    dispatched = []
    max_agents = min(5, len(queued))
    
    for i in range(max_agents):
        result = dispatch_task()
        if result and result.get("task_id"):
            dispatched.append(result)
            notify(
                f"Agent Dispatched: {result.get("agent", "?")}",
                f"Task {result.get("task_id", "?")} assigned to {result.get("assigned_to", "?")} in {result.get("session", "?")}",
                "low"
            )
    
    if dispatched:
        notify(
            f"Overnight: {len(dispatched)} Agents Running",
            f"Dispatched: {", ".join(d.get("agent","?") for d in dispatched)}. Check in the morning.",
            "default"
        )
    else:
        notify("Overnight: Dispatch Failed", "No agents could be dispatched. Check governor logs.", "high")

if __name__ == "__main__":
    run_overnight()
