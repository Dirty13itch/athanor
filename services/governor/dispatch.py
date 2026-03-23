"""Smart dispatch — leverage each tool's unique capabilities."""
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
    """Claude Code — best for complex architecture, multi-file features."""
    session = "agent-claude-" + task["id"]
    prompt = "Task " + task["id"] + ": " + task["title"] + ". " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-claude.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'claude -p \"" + prompt + "\" --dangerously-skip-permissions 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "claude", "status": "running", "mode": "autonomous"}

def dispatch_codex(task, worktree):
    """Codex CLI — uses LiteLLM proxy for local models. For ChatGPT Pro sub, needs device-auth."""
    session = "agent-codex-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-codex.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'OPENAI_BASE_URL=http://192.168.1.203:4000 OPENAI_API_KEY=sk-athanor-litellm-2026 codex exec \"" + prompt + "\" --full-auto 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "codex", "status": "running", "mode": "litellm-local"}

def dispatch_copilot(task, worktree):
    """Copilot CLI — unlimited GPT-5 mini. Use autopilot mode."""
    session = "agent-copilot-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-copilot.log"
    # Use autopilot mode for fully autonomous operation
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'COPILOT_GITHUB_TOKEN=$(cat ~/.secrets/github-pat) copilot \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "copilot", "status": "running", "mode": "autopilot-gpt5mini"}

def dispatch_kimi(task, worktree):
    """Kimi CLI — use swarm mode for batch operations."""
    session = "agent-kimi-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-kimi.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'kimi \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "kimi", "status": "running", "mode": "swarm"}

def dispatch_opencode(task, worktree):
    """OpenCode — local models via LiteLLM, parallel agents."""
    session = "agent-opencode-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-opencode.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'opencode \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "opencode", "status": "running", "mode": "local-parallel"}

def dispatch_aider(task, worktree):
    """aider — git pair programming with clean auto-commits."""
    session = "agent-aider-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-aider.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'aider --yes --message \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "aider", "status": "running", "mode": "pair-program"}

def dispatch_goose(task, worktree):
    """Goose — system automation, MCP-native recipes."""
    session = "agent-goose-" + task["id"]
    prompt = task["title"] + ": " + task["description"]
    log = "/tmp/agent-logs/" + task["id"] + "-goose.log"
    cmd = "tmux new-session -d -s " + session + " -c " + worktree + " 'goose run \"" + prompt + "\" 2>&1 | tee " + log + "'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "goose", "status": "running", "mode": "mcp-recipe"}

DISPATCHERS = {
    "claude-max": dispatch_claude,
    "chatgpt-pro": dispatch_codex,
    "copilot-pro-plus": dispatch_copilot,
    "kimi-code": dispatch_kimi,
    "glm-zai": dispatch_opencode,  # GLM via LiteLLM through opencode
    "local-opencode": dispatch_opencode,
    "local-aider": dispatch_aider,
    "local-goose": dispatch_goose,
}

def dispatch_task(task, subscription):
    os.makedirs("/tmp/agent-logs", exist_ok=True)
    os.makedirs("/tmp/agent-worktrees", exist_ok=True)
    worktree = create_worktree(task.get("repo", "athanor"), task["id"])
    dispatcher = DISPATCHERS.get(subscription, dispatch_opencode)
    result = dispatcher(task, worktree)
    result["worktree"] = worktree
    result["task_id"] = task["id"]
    result["subscription"] = subscription
    result["dispatched_at"] = datetime.utcnow().isoformat()
    return result
