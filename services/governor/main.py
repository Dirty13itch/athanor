"""Athanor Governor - Subscription Burn Factory
Keeps all cloud coding subscriptions maximally busy on real projects.
Port: 8760 on DEV
"""
import os
import json
import glob
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field

import db
from continuous_dispatch import continuous_dispatch_loop
from dispatch import dispatch_task

app = FastAPI(title="Athanor Governor", version="0.4.0")

@app.on_event("startup")
async def start_continuous_dispatch():
    """Start the 24/7 dispatch loop."""
    import asyncio
    asyncio.create_task(continuous_dispatch_loop(None))

task_queue: list[dict] = []
active_agents: dict[str, dict] = {}

SUBSCRIPTIONS = {
    "claude-max": {"name": "Claude Max 20x", "monthly_cost": 200, "cli_tool": "claude", "status": "active"},
    "chatgpt-pro": {"name": "ChatGPT Pro", "monthly_cost": 200, "cli_tool": "codex", "status": "active"},
    "copilot-pro-plus": {"name": "Copilot Pro+", "monthly_cost": 39, "cli_tool": "copilot", "status": "active"},
    "kimi-code": {"name": "Kimi Code", "monthly_cost": 19, "cli_tool": "kimi", "status": "active"},
    "glm-zai": {"name": "GLM Z.ai Pro", "monthly_cost": 30, "cli_tool": "litellm", "status": "active"},
    "gemini-advanced": {"name": "Gemini Advanced", "monthly_cost": 20, "cli_tool": "gemini", "status": "needs_auth"},
    "local-opencode": {"name": "Local OpenCode", "monthly_cost": 0, "cli_tool": "opencode", "status": "active"},
    "local-aider": {"name": "Local aider", "monthly_cost": 0, "cli_tool": "aider", "status": "active"},
    "local-goose": {"name": "Local Goose", "monthly_cost": 0, "cli_tool": "goose", "status": "active"},
}

class Task(BaseModel):
    id: str = ""
    title: str
    description: str
    repo: str = "athanor"
    complexity: str = "medium"
    content_class: str = "cloud_safe"
    assigned_to: Optional[str] = None
    status: str = "queued"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.3.0",
        "queue_size": len(task_queue),
        "active_agents": len(active_agents),
        "subscriptions": {k: v["status"] for k, v in SUBSCRIPTIONS.items()},
        "db_stats": db.get_stats(),
    }

@app.get("/queue")
async def get_queue():
    return {"tasks": task_queue}

@app.post("/queue")
async def add_task(task: Task):
    task.id = "task-" + str(len(task_queue) + 1).zfill(4)
    task_queue.append(task.model_dump())
    return {"id": task.id, "status": "queued"}

@app.get("/agents")
async def get_agents():
    return {"active": active_agents, "subscriptions": SUBSCRIPTIONS}

@app.post("/dispatch")
async def dispatch_next():
    queued = [t for t in task_queue if t["status"] == "queued"]
    if not queued:
        return {"status": "empty", "message": "No tasks in queue"}
    task = queued[0]
    # CONTENT CLASS CHECK FIRST — sovereign content NEVER goes to cloud
    if task.get("content_class") == "sovereign_only":
        sub = "local-opencode"  # Uses abliterated model via LiteLLM ($0)
    elif task["complexity"] == "critical":
        sub = "claude-max"
    elif task["complexity"] == "high":
        sub = "chatgpt-pro" if SUBSCRIPTIONS["chatgpt-pro"]["status"] == "active" else "claude-max"
    elif task["complexity"] == "low":
        # Use free local for low-priority, save cloud subs for hard problems
        sub = "local-aider" if SUBSCRIPTIONS["local-aider"]["status"] == "active" else "copilot-pro-plus"
    else:
        sub = "claude-max"
    task["assigned_to"] = sub
    task["status"] = "assigned"
    return {"task_id": task["id"], "assigned_to": sub, "cli_tool": SUBSCRIPTIONS[sub]["cli_tool"]}

@app.post("/dispatch-and-run")
async def dispatch_and_run():
    queued = [t for t in task_queue if t["status"] == "queued"]
    if not queued:
        return {"status": "empty", "message": "No tasks in queue"}
    task = queued[0]
    # CONTENT CLASS CHECK FIRST — sovereign content NEVER goes to cloud
    if task.get("content_class") == "sovereign_only":
        sub = "local-opencode"  # Uses abliterated model via LiteLLM ($0)
    elif task["complexity"] == "critical":
        sub = "claude-max"
    elif task["complexity"] == "high":
        sub = "chatgpt-pro" if SUBSCRIPTIONS["chatgpt-pro"]["status"] == "active" else "claude-max"
    elif task["complexity"] == "low":
        # Use free local for low-priority, save cloud subs for hard problems
        sub = "local-aider" if SUBSCRIPTIONS["local-aider"]["status"] == "active" else "copilot-pro-plus"
    else:
        sub = "claude-max"
    task["assigned_to"] = sub
    task["status"] = "running"
    result = dispatch_task(task, sub)
    active_agents[task["id"]] = result
    return {"task_id": task["id"], "assigned_to": sub, "agent": result["agent"], "session": result["session"], "worktree": result["worktree"]}

@app.get("/logs/{task_id}")
async def get_task_logs(task_id: str):
    log_path = "/tmp/agent-logs/" + task_id + "-*.log"
    logs = {}
    for f in glob.glob(log_path):
        with open(f) as fh:
            logs[os.path.basename(f)] = fh.read()[-2000:]
    return {"task_id": task_id, "logs": logs}

@app.post("/queue/batch")
async def add_batch(tasks: list[Task]):
    results = []
    for task in tasks:
        task.id = "task-" + str(len(task_queue) + 1).zfill(4)
        task_queue.append(task.model_dump())
        results.append({"id": task.id, "status": "queued"})
    return {"added": len(results), "tasks": results}

@app.get("/stats")
async def get_stats():
    return db.get_stats()

@app.post("/tasks")
async def create_task_db(task: Task):
    task_id = db.add_task(task.title, task.description, task.repo, task.complexity, task.content_class)
    return {"id": task_id, "status": "queued", "persistent": True}

@app.get("/status")
async def system_status():
    return {
        "governor": "active",
        "version": "0.3.0",
        "timestamp": datetime.utcnow().isoformat(),
        "queue": {"in_memory": len(task_queue), "db": db.get_stats()},
        "active_agents": len(active_agents),
        "subscriptions_active": len([s for s in SUBSCRIPTIONS.values() if s["status"] == "active"]),
        "monthly_spend": sum(s["monthly_cost"] for s in SUBSCRIPTIONS.values()),
    }



@app.get("/attention")
async def get_attention_items():
    """What needs the user's attention RIGHT NOW. Designed for the command center."""
    import requests as req

    items = []

    # 1. Tasks completed overnight (need review)
    done_tasks = [t for t in task_queue if t["status"] in ("done", "review")]
    for t in done_tasks:
        items.append({"type": "review", "priority": "high", "title": f"Review: {t['title']}", "detail": f"Completed by {t.get('assigned_to','?')}", "action": "Review PR and merge"})

    # 2. Failed tasks (need investigation)
    failed_tasks = [t for t in task_queue if t["status"] == "failed"]
    for t in failed_tasks:
        items.append({"type": "failed", "priority": "high", "title": f"Failed: {t['title']}", "detail": f"Agent: {t.get('assigned_to','?')}", "action": "Check logs, reassign or fix"})

    # 3. Subscriptions needing auth
    needs_auth = [k for k, v in SUBSCRIPTIONS.items() if v["status"] == "needs_auth"]
    if needs_auth:
        items.append({"type": "auth", "priority": "medium", "title": f"{len(needs_auth)} subscriptions need login", "detail": ", ".join(needs_auth), "action": "Run: codex login, gemini auth, copilot auth"})

    # 4. Self-improvement proposals waiting
    try:
        r = req.get("http://192.168.1.244:9000/v1/improvement/proposals", timeout=5)
        if r.status_code == 200:
            proposals = r.json().get("proposals", [])
            pending = [p for p in proposals if p.get("status") == "proposed"]
            if pending:
                items.append({"type": "improvement", "priority": "low", "title": f"{len(pending)} improvement proposals pending", "detail": pending[0].get("title","")[:60], "action": "Review on /improvement page"})
    except:
        pass

    # 5. Queued tasks ready for dispatch
    queued = [t for t in task_queue if t["status"] == "queued"]
    if queued:
        items.append({"type": "dispatch", "priority": "low", "title": f"{len(queued)} tasks queued for dispatch", "detail": "Next overnight run at 10pm or dispatch manually", "action": "POST /dispatch-and-run"})

    return {
        "attention_count": len([i for i in items if i["priority"] in ("high", "medium")]),
        "total_items": len(items),
        "items": sorted(items, key=lambda x: {"high":0,"medium":1,"low":2}.get(x["priority"],3))
    }




@app.post("/cleanup-stuck")
async def cleanup_stuck_tasks():
    """Kill tasks stuck in 'running' for over 4 hours. Circuit breaker."""
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(hours=4)).isoformat()
    stuck = []
    for task in task_queue:
        if task["status"] == "running" and task.get("created_at", "") < cutoff:
            task["status"] = "failed"
            task["result"] = "Circuit breaker: stuck for >4 hours"
            stuck.append(task["id"])
            # Remove from active agents
            if task["id"] in active_agents:
                del active_agents[task["id"]]
    return {"cleaned": len(stuck), "task_ids": stuck}




@app.get("/recent-commits")
async def get_recent_commits():
    """Get recent git commits from agent branches and main."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", "/home/shaun/repos/athanor", "log", "--all", "--oneline", "--since=24 hours ago", "--format=%H|%an|%s|%ar"],
            capture_output=True, text=True, timeout=5
        )
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "message": parts[2],
                    "when": parts[3],
                })
        return {"commits": commits, "count": len(commits)}
    except:
        return {"commits": [], "count": 0}

@app.get("/active-sessions")
async def get_active_sessions():
    """Get currently running tmux agent sessions."""
    import subprocess
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}|#{session_created}|#{session_activity}"],
            capture_output=True, text=True, timeout=5
        )
        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line or "agent-" not in line:
                continue
            parts = line.split("|")
            sessions.append({
                "name": parts[0],
                "created": parts[1] if len(parts) > 1 else "",
                "last_activity": parts[2] if len(parts) > 2 else "",
            })
        return {"sessions": sessions, "count": len(sessions)}
    except:
        return {"sessions": [], "count": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8760)
