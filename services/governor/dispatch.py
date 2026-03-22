"""Agent dispatch module for the Governor."""
import subprocess
import os
from datetime import datetime

REPO_PATHS = {
    "athanor": "/home/shaun/repos/athanor",
}

def create_worktree(repo, task_id):
    repo_path = REPO_PATHS.get(repo, REPO_PATHS["athanor"])
    branch = "agent/" + task_id
    worktree_path = "/tmp/agent-worktrees/" + task_id
    os.makedirs(worktree_path, exist_ok=True)
    subprocess.run(["git", "-C", repo_path, "branch", branch, "HEAD"], capture_output=True)
    subprocess.run(["git", "-C", repo_path, "worktree", "add", worktree_path, branch], capture_output=True)
    return worktree_path

def dispatch_claude(task, worktree):
    session = "agent-claude-" + task["id"]
    prompt = "Task " + task["id"] + ": " + task["title"] + ". " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-claude.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'claude -p \"" + prompt + "\" --dangerously-skip-permissions 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "claude", "status": "running"}

def dispatch_codex(task, worktree):
    session = "agent-codex-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-codex.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'codex exec \"" + prompt + "\" --full-auto 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "codex", "status": "running"}

def dispatch_copilot(task, worktree):
    session = "agent-copilot-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-copilot.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'copilot \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "copilot", "status": "running"}

def dispatch_opencode(task, worktree):
    session = "agent-opencode-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-opencode.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'opencode \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "opencode", "status": "running"}

DISPATCHERS = {
    "claude-max": dispatch_claude,
    "chatgpt-pro": dispatch_codex,
    "copilot-pro-plus": dispatch_copilot,
    "kimi-code": dispatch_opencode,
    "glm-zai": dispatch_opencode,
    "gemini-advanced": dispatch_opencode,
}

def dispatch_task(task, subscription):
    os.makedirs("/tmp/agent-logs", exist_ok=True)
    os.makedirs("/tmp/agent-worktrees", exist_ok=True)
    worktree = create_worktree(task.get("repo", "athanor"), task["id"])
    dispatcher = DISPATCHERS.get(subscription, dispatch_opencode)
    result = dispatcher(task, worktree)
    result["worktree"] = worktree
    result["task_id"] = task["id"]
    result["dispatched_at"] = datetime.utcnow().isoformat()
    return result
