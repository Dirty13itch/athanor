"""Task Monitor — checks if dispatched agent sessions have completed.
Runs periodically to update task status from running -> done/failed.
Includes cleanup for stale worktrees and old logs.
"""
import subprocess
import os
import glob
import shutil
import gzip
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger("governor.monitor")

WORKTREE_DIR = "/tmp/agent-worktrees"
LOG_DIR = "/tmp/agent-logs"
WORKTREE_MAX_AGE_HOURS = 24
LOG_COMPRESS_AGE_HOURS = 48
LOG_DELETE_AGE_DAYS = 7


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
    logs = glob.glob(f"{LOG_DIR}/{task_id}-*.log")
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


def cleanup_worktrees():
    """Remove worktrees older than WORKTREE_MAX_AGE_HOURS.
    Also prunes git worktree references for removed directories.
    """
    if not os.path.isdir(WORKTREE_DIR):
        return 0

    removed = 0
    cutoff = datetime.now() - timedelta(hours=WORKTREE_MAX_AGE_HOURS)
    active_sessions = get_active_tmux_sessions()

    for entry in os.listdir(WORKTREE_DIR):
        path = os.path.join(WORKTREE_DIR, entry)
        if not os.path.isdir(path):
            continue

        # Don't remove worktrees for actively running sessions
        if any(entry in sess for sess in active_sessions):
            continue

        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError:
            pass

    # Prune stale git worktree references
    if removed > 0:
        repo_path = os.path.expanduser("~/repos/athanor")
        if os.path.isdir(repo_path):
            subprocess.run(
                ["git", "-C", repo_path, "worktree", "prune"],
                capture_output=True, timeout=30
            )

    if removed > 0:
        logger.info(f"Cleaned up {removed} stale worktrees")
    return removed


def cleanup_logs():
    """Compress logs older than LOG_COMPRESS_AGE_HOURS, delete logs older than LOG_DELETE_AGE_DAYS."""
    if not os.path.isdir(LOG_DIR):
        return 0, 0

    compressed = 0
    deleted = 0
    compress_cutoff = datetime.now() - timedelta(hours=LOG_COMPRESS_AGE_HOURS)
    delete_cutoff = datetime.now() - timedelta(days=LOG_DELETE_AGE_DAYS)

    for entry in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, entry)
        if not os.path.isfile(path):
            continue

        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))

            # Delete old logs (both .log and .log.gz)
            if mtime < delete_cutoff:
                os.remove(path)
                deleted += 1
                continue

            # Compress uncompressed logs older than threshold
            if entry.endswith(".log") and mtime < compress_cutoff:
                gz_path = path + ".gz"
                with open(path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        f_out.write(f_in.read())
                os.remove(path)
                compressed += 1
        except OSError:
            pass

    if compressed > 0 or deleted > 0:
        logger.info(f"Log cleanup: compressed={compressed}, deleted={deleted}")
    return compressed, deleted


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

    # Run cleanup after every monitor cycle
    try:
        cleanup_worktrees()
        cleanup_logs()
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

    return updated
