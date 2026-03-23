"""Smart dispatch — leverage each tool's unique capabilities.
Each agent gets the correct headless/non-interactive flags.
Prompts are written to tempfiles to avoid shell injection.
"""
import subprocess
import os
import tempfile
from datetime import datetime, timezone

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

def _write_prompt(task):
    """Write prompt to a temp file to avoid shell escaping issues."""
    prompt = f"Task {task['id']}: {task['title']}. {task['description']}"
    fd, path = tempfile.mkstemp(suffix=".txt", prefix=f"governor-{task['id']}-")
    with os.fdopen(fd, "w") as f:
        f.write(prompt)
    return path, prompt

def dispatch_claude(task, worktree):
    """Claude Code — best for complex architecture, multi-file features."""
    session = "agent-claude-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-claude.log"
    # claude -p reads prompt from arg, --dangerously-skip-permissions for full autonomy
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'claude -p \"$(cat {prompt_file})\" --dangerously-skip-permissions 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "claude", "status": "running", "mode": "autonomous"}

def dispatch_codex(task, worktree):
    """Codex CLI — ChatGPT Pro subscription, device-auth. Full auto mode."""
    session = "agent-codex-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-codex.log"
    # codex exec with --full-auto for autonomous operation
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'codex exec \"$(cat {prompt_file})\" --full-auto 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "codex", "status": "running", "mode": "chatgpt-pro"}

def dispatch_copilot(task, worktree):
    """Copilot CLI — unlimited GPT-5 mini. Non-interactive with -p and --yolo."""
    session = "agent-copilot-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-copilot.log"
    # copilot -p for non-interactive, --yolo for all permissions
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'copilot -p \"$(cat {prompt_file})\" --yolo 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "copilot", "status": "running", "mode": "autopilot-gpt5mini"}

def dispatch_kimi(task, worktree):
    """Kimi CLI — non-interactive with -p flag."""
    session = "agent-kimi-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-kimi.log"
    # kimi -p for non-interactive prompt
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'kimi -p \"$(cat {prompt_file})\" 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "kimi", "status": "running", "mode": "kimi-k2.5"}

def dispatch_opencode(task, worktree):
    """OpenCode — local models via LiteLLM, non-interactive with -p flag."""
    session = "agent-opencode-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-opencode.log"
    # opencode -p for non-interactive mode
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'opencode -p \"$(cat {prompt_file})\" 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "opencode", "status": "running", "mode": "local-litellm"}

def dispatch_aider(task, worktree):
    """aider — git pair programming with clean auto-commits."""
    session = "agent-aider-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-aider.log"
    # aider --yes for auto-confirm, --message for the prompt
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'aider --yes --message \"$(cat {prompt_file})\" 2>&1 | tee {log}; rm -f {prompt_file}'"
    subprocess.run(cmd, shell=True, capture_output=True)
    return {"session": session, "agent": "aider", "status": "running", "mode": "pair-program"}

def dispatch_goose(task, worktree):
    """Goose — system automation, MCP-native. Uses 'goose run -t' for text input."""
    session = "agent-goose-" + task["id"]
    prompt_file, _ = _write_prompt(task)
    log = "/tmp/agent-logs/" + task["id"] + "-goose.log"
    # goose run -t for text-based non-interactive execution
    cmd = f"tmux new-session -d -s {session} -c {worktree} 'goose run -t \"$(cat {prompt_file})\" 2>&1 | tee {log}; rm -f {prompt_file}'"
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
    result["dispatched_at"] = datetime.now(timezone.utc).isoformat()
    return result
