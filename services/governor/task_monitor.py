"""Task Monitor — checks if dispatched agent sessions have completed.
Runs periodically to update task status from running -> done/failed.
"""
import subprocess
import os
import glob
from datetime import datetime, timezone

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
        return "unknown", "no log file found"

    for log_path in logs:
        try:
            with open(log_path) as f:
                content = f.read()

            if not content.strip():
                return "failed", "empty log - agent produced no output"

            lower = content.lower()

            # Check for stuck/interactive prompts (agent couldn't run headless)
            stuck_indicators = [
                "would you like to initialize",
                "press enter to continue",
                "waiting for input",
                "select a model",
            ]
            if any(x in lower for x in stuck_indicators):
                return "failed", "agent stuck at interactive prompt"

            # Strong completion indicators
            done_indicators = [
                "pull request created", "pr created", "committed",
                "changes committed", "task complete", "done.",
                "successfully", "completed", "finished",
                "applied changes", "wrote file", "created file",
            ]
            if any(x in lower for x in done_indicators):
                return "done", "completion indicators found in log"

            # Strong failure indicators
            fail_indicators = [
                "fatal error", "unhandled exception", "panic:",
                "authentication failed", "rate limit exceeded",
                "permission denied", "command not found",
                "out of memory", "killed",
            ]
            if any(x in lower for x in fail_indicators):
                return "failed", "error indicators found in log"

            # Soft error indicators - only if no completion indicators
            soft_fail = ["error:", "failed", "traceback"]
            if any(x in lower for x in soft_fail) and len(content) > 200:
                return "failed", "errors detected in substantial output"

            # Agent ran and produced output but no clear signal
            if len(content) > 100:
                return "done", "agent produced output, no errors detected"

            # Very short output, unclear
            return "failed", "minimal output, likely did not complete"

        except Exception as e:
            return "failed", f"log read error: {e}"

    return "unknown", "no readable logs"

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
            log_status, reason = check_log_for_completion(task_id)
            now = datetime.now(timezone.utc).isoformat()

            if log_status == "done":
                task["status"] = "done"
                task["completed_at"] = now
                task["result"] = reason
            elif log_status == "failed":
                task["status"] = "failed"
                task["completed_at"] = now
                task["result"] = reason
            else:
                # Unknown — be optimistic but note it
                task["status"] = "done"
                task["completed_at"] = now
                task["result"] = "session ended, status unclear"

            # Remove from active agents
            if task_id in active_agents:
                del active_agents[task_id]

            updated.append({
                "task_id": task_id,
                "new_status": task["status"],
                "result": task.get("result", reason),
            })

    return updated
