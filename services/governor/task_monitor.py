"""Task Monitor — checks if dispatched agent sessions have completed.
Runs periodically to update task status from running → done/failed.
"""
import subprocess
import os
import glob
from datetime import datetime

def get_active_tmux_sessions():
    """List all active tmux sessions starting with 'agent-'."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return [s.strip() for s in result.stdout.strip().split("\n") if s.startswith("agent-")]
    return []

def check_log_for_completion(task_id):
    """Check if an agent's log file indicates completion or failure."""
    logs = glob.glob(f"/tmp/agent-logs/{task_id}-*.log")
    if not logs:
        return "unknown"

    for log_path in logs:
        try:
            with open(log_path) as f:
                content = f.read()

            # Check for common completion indicators
            lower = content.lower()
            if any(x in lower for x in ["pull request created", "pr created", "committed", "push", "task complete", "done"]):
                return "done"
            if any(x in lower for x in ["error:", "failed", "exception", "traceback", "abort"]):
                if len(content) > 100:  # Only count as failed if substantial output
                    return "failed"
        except:
            pass

    return "running"

def monitor_tasks(task_queue, active_agents):
    """Check all running tasks and update their status."""
    active_sessions = get_active_tmux_sessions()
    updated = []

    for task in task_queue:
        if task["status"] != "running":
            continue

        task_id = task["id"]
        session_name = active_agents.get(task_id, {}).get("session", "")

        # If tmux session is gone, the agent finished (or crashed)
        if session_name and session_name not in active_sessions:
            log_status = check_log_for_completion(task_id)
            if log_status == "done":
                task["status"] = "done"
                task["completed_at"] = datetime.utcnow().isoformat()
            elif log_status == "failed":
                task["status"] = "failed"
                task["completed_at"] = datetime.utcnow().isoformat()
            else:
                # Session gone but log inconclusive — mark as done (optimistic)
                task["status"] = "done"
                task["completed_at"] = datetime.utcnow().isoformat()

            # Remove from active agents
            if task_id in active_agents:
                del active_agents[task_id]

            updated.append({"task_id": task_id, "new_status": task["status"]})

    return updated
