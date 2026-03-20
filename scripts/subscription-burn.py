#!/usr/bin/env python3
"""
Athanor Subscription Burn Scheduler
====================================
Actively consumes rolling-window AI subscription quotas before they expire.
Runs as a FastAPI service on DEV:8065.

$543/mo in AI subscriptions with use-it-or-lose-it windows.
This service schedules automated burn sessions to maximize utilization.
"""

import asyncio
import importlib
import json
import logging
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from fastapi import FastAPI, HTTPException

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
# Import CLI Router (hyphenated filename requires importlib)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url
_cli_router_mod = importlib.import_module("cli-router")
CLIRouter = _cli_router_mod.CLIRouter
register_router_endpoints = _cli_router_mod.register_router_endpoints

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TZ = ZoneInfo("America/Los_Angeles")
TASKS_DIR = Path.home() / ".athanor" / "subscription-tasks"
LOG_DIR = Path("/var/log/athanor")
USAGE_LOG = LOG_DIR / "subscription-usage.log"
STATE_FILE = Path.home() / ".athanor" / "subscription-burn-state.json"
NTFY_URL = get_url("ntfy_topic")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("subscription-burn")

if LOG_DIR.exists():
    _fh = logging.FileHandler(USAGE_LOG)
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    log.addHandler(_fh)

# ---------------------------------------------------------------------------
# ntfy helper
# ---------------------------------------------------------------------------
async def ntfy(title: str, message: str, priority: str = "default", tags: str = "robot"):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                NTFY_URL,
                json={"topic": "athanor", "title": title, "message": message,
                      "priority": priority, "tags": [tags]},
            )
    except Exception as e:
        log.warning(f"ntfy send failed: {e}")

# ---------------------------------------------------------------------------
# Subscription definitions
# ---------------------------------------------------------------------------
SUBSCRIPTIONS: dict[str, dict[str, Any]] = {
    "claude_max": {
        "type": "rolling_window",
        "window_hours": 5,
        "tokens_per_window": 220000,
        "cost_per_month": 200,
        "cli": "/home/shaun/.local/bin/claude",
        "cli_args": ["-p", "--dangerously-skip-permissions"],
        "task_file": "claude-tasks.yaml",
    },
    "chatgpt_pro": {
        "type": "daily_reset",
        "daily_limit": 200,
        "reset_time": "00:00",
        "cost_per_month": 200,
        "cli": "codex",
        "task_file": "codex-tasks.yaml",
    },
    "gemini_advanced": {
        "type": "daily_reset",
        "daily_limit": 100,
        "reset_time": "00:00",
        "cost_per_month": 20,
        "cli": "gemini",
        "task_file": "gemini-tasks.yaml",
    },
    "kimi_allegretto": {
        "type": "rolling_window",
        "window_hours": 5,
        "max_concurrent": 30,
        "cost_per_month": 19,
        "cli": "kimi",
        "task_file": "kimi-tasks.yaml",
    },
    "copilot_pro": {
        "type": "monthly_reset",
        "monthly_limit": 300,
        "cost_per_month": 33,
    },
    "perplexity_pro": {
        "type": "mixed",
        "weekly_searches": 200,
        "monthly_deep_research": 20,
        "cost_per_month": 20,
    },
    "zai_glm_pro": {
        "type": "rolling_window",
        "window_hours": 5,
        "cost_per_month": 30,
    },
    "venice_pro": {
        "type": "depleting",
        "credits_remaining": 312,
        "auto_cancel": "2026-07-01",
        "cost_per_month": 12,
    },
}

# ---------------------------------------------------------------------------
# Burn schedule (times in PDT / America/Los_Angeles)
# ---------------------------------------------------------------------------
BURN_SCHEDULE = [
    {"hour": 7,  "minute": 0, "label": "Window 1 - Morning",   "subs": ["claude_max", "gemini_advanced", "kimi_allegretto"]},
    {"hour": 12, "minute": 0, "label": "Window 2 - Midday",    "subs": ["claude_max", "chatgpt_pro"]},
    {"hour": 17, "minute": 0, "label": "Window 3 - Evening",   "subs": ["claude_max", "kimi_allegretto"]},
    {"hour": 22, "minute": 0, "label": "Window 4 - Overnight", "subs": ["claude_max", "chatgpt_pro"]},
]

# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------
class BurnState:
    """Track subscription usage and active processes."""

    def __init__(self):
        self.active_pids: dict[str, int] = {}
        self.active_procs: dict[str, subprocess.Popen] = {}  # Popen objects for reaping
        self.daily_usage: dict[str, int] = {}
        self.last_burn: dict[str, str] = {}
        self.total_burns_today: dict[str, int] = {}
        self._load()

    def _load(self):
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text())
            today = datetime.now(TZ).strftime("%Y-%m-%d")
            self.last_burn = data.get("last_burn", {})
            if data.get("date") == today:
                self.daily_usage = data.get("daily_usage", {})
                self.total_burns_today = data.get("total_burns_today", {})
            log.info(f"Loaded state from {STATE_FILE}")
        except Exception as e:
            log.warning(f"Failed to load state: {e}")

    def save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({
            "date": datetime.now(TZ).strftime("%Y-%m-%d"),
            "daily_usage": self.daily_usage,
            "total_burns_today": self.total_burns_today,
            "last_burn": self.last_burn,
        }, indent=2))

    def record_burn(self, sub_name: str):
        now = datetime.now(TZ)
        self.last_burn[sub_name] = now.isoformat()
        self.daily_usage[sub_name] = self.daily_usage.get(sub_name, 0) + 1
        self.total_burns_today[sub_name] = self.total_burns_today.get(sub_name, 0) + 1
        self.save()

    def is_running(self, sub_name: str) -> bool:
        proc = self.active_procs.get(sub_name)
        if proc is not None:
            rc = proc.poll()  # reaps zombie via waitpid
            if rc is None:
                return True
            # Process exited -- clean up
            self.active_procs.pop(sub_name, None)
            self.active_pids.pop(sub_name, None)
            return False
        pid = self.active_pids.get(sub_name)
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            del self.active_pids[sub_name]
            return False

    def get_utilization(self, sub_name: str) -> dict:
        sub = SUBSCRIPTIONS[sub_name]
        sub_type = sub["type"]
        burns_today = self.total_burns_today.get(sub_name, 0)
        last = self.last_burn.get(sub_name)

        if sub_type == "rolling_window":
            window_h = sub.get("window_hours", 5)
            max_windows = 24 // window_h
            return {
                "type": sub_type,
                "burns_today": burns_today,
                "max_possible_today": max_windows,
                "utilization_pct": round(burns_today / max_windows * 100) if max_windows else 0,
                "last_burn": last,
                "running": self.is_running(sub_name),
            }
        elif sub_type == "daily_reset":
            limit = sub.get("daily_limit", 0)
            used = self.daily_usage.get(sub_name, 0)
            return {
                "type": sub_type,
                "used_today": used,
                "daily_limit": limit,
                "utilization_pct": round(used / limit * 100) if limit else 0,
                "last_burn": last,
                "running": self.is_running(sub_name),
            }
        elif sub_type == "monthly_reset":
            return {
                "type": sub_type,
                "burns_today": burns_today,
                "monthly_limit": sub.get("monthly_limit", 0),
                "last_burn": last,
                "running": self.is_running(sub_name),
            }
        elif sub_type == "depleting":
            return {
                "type": sub_type,
                "credits_remaining": sub.get("credits_remaining", 0),
                "auto_cancel": sub.get("auto_cancel"),
                "last_burn": last,
                "running": self.is_running(sub_name),
            }
        else:
            return {
                "type": sub_type,
                "burns_today": burns_today,
                "last_burn": last,
                "running": self.is_running(sub_name),
            }


state = BurnState()

# ---------------------------------------------------------------------------
# Task queue helpers
# ---------------------------------------------------------------------------
def load_tasks(sub_name: str) -> list[dict]:
    sub = SUBSCRIPTIONS.get(sub_name, {})
    task_file = sub.get("task_file")
    if not task_file:
        return []
    path = TASKS_DIR / task_file
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict):
            return data.get("tasks", [])
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        log.warning(f"Failed to load tasks from {path}: {e}")
        return []


def pop_next_task(sub_name: str) -> Optional[dict]:
    sub = SUBSCRIPTIONS.get(sub_name, {})
    task_file = sub.get("task_file")
    if not task_file:
        return None
    path = TASKS_DIR / task_file
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text())
        tasks = raw.get("tasks", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])

        for task in tasks:
            if not isinstance(task, dict):
                continue
            if task.get("status", "pending") == "pending":
                task["status"] = "in_progress"
                task["started_at"] = datetime.now(TZ).isoformat()
                if isinstance(raw, dict):
                    raw["tasks"] = tasks
                    path.write_text(yaml.dump(raw, default_flow_style=False, sort_keys=False))
                else:
                    path.write_text(yaml.dump(tasks, default_flow_style=False, sort_keys=False))
                return task
        return None
    except Exception as e:
        log.warning(f"Failed to pop task from {path}: {e}")
        return None


def mark_task_done(sub_name: str, task_prompt: str):
    sub = SUBSCRIPTIONS.get(sub_name, {})
    task_file = sub.get("task_file")
    if not task_file:
        return
    path = TASKS_DIR / task_file
    if not path.exists():
        return
    try:
        raw = yaml.safe_load(path.read_text())
        tasks = raw.get("tasks", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        for task in tasks:
            if isinstance(task, dict) and task.get("status") == "in_progress":
                task["status"] = "done"
                task["completed_at"] = datetime.now(TZ).isoformat()
                break
        if isinstance(raw, dict):
            raw["tasks"] = tasks
            path.write_text(yaml.dump(raw, default_flow_style=False, sort_keys=False))
        else:
            path.write_text(yaml.dump(tasks, default_flow_style=False, sort_keys=False))
    except Exception as e:
        log.warning(f"Failed to mark task done: {e}")

# ---------------------------------------------------------------------------
# Burn execution
# ---------------------------------------------------------------------------
async def execute_burn(sub_name: str, manual: bool = False) -> dict:
    sub = SUBSCRIPTIONS.get(sub_name)
    if not sub:
        return {"error": f"Unknown subscription: {sub_name}"}

    cli = sub.get("cli")
    if not cli:
        return {"error": f"No CLI configured for {sub_name}", "skipped": True}

    if state.is_running(sub_name):
        pid = state.active_pids.get(sub_name)
        return {"error": f"{sub_name} already running (PID {pid})", "skipped": True}

    task = pop_next_task(sub_name)
    if not task:
        return {"error": f"No pending tasks for {sub_name}", "skipped": True}

    prompt = task.get("prompt", task.get("description", "")) if isinstance(task, dict) else str(task)
    working_dir = task.get("working_dir", str(Path.home() / "repos" / "athanor")) if isinstance(task, dict) else str(Path.home() / "repos" / "athanor")

    if not prompt:
        return {"error": f"Empty task for {sub_name}", "skipped": True}

    cli_args = sub.get("cli_args", [])
    cmd = [cli] + cli_args + [prompt]
    log.info(f"Launching burn: {sub_name} | cmd: {cmd[0]} | task: {prompt[:80]}")

    try:
        proc = subprocess.Popen(
            cmd, cwd=working_dir,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        state.active_pids[sub_name] = proc.pid
        state.active_procs[sub_name] = proc  # store for reaping
        state.record_burn(sub_name)

        source = "manual" if manual else "scheduled"
        log.info(f"[{source}] {sub_name} burn started - PID {proc.pid} - {prompt[:80]}")

        await ntfy(
            f"Burn: {sub_name}",
            f"[{source}] PID {proc.pid}\n{prompt[:120]}",
            tags="fire",
        )
        return {
            "subscription": sub_name, "pid": proc.pid,
            "task": prompt[:120], "source": source,
            "started_at": datetime.now(TZ).isoformat(),
        }
    except FileNotFoundError:
        return {"error": f"CLI not found: {cli}"}
    except Exception as e:
        return {"error": f"Failed to launch {sub_name}: {e}"}

# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------
async def run_burn_window(window: dict):
    label = window["label"]
    subs = window["subs"]
    log.info(f"=== Burn window: {label} ===")
    await ntfy(f"Burn Window: {label}", f"Starting burns: {', '.join(subs)}", tags="clock")

    results = []
    for sub_name in subs:
        result = await execute_burn(sub_name)
        results.append(result)
        await asyncio.sleep(2)

    launched = [r for r in results if "pid" in r]
    skipped = [r for r in results if r.get("skipped")]
    log.info(f"Window {label}: {len(launched)} launched, {len(skipped)} skipped")


async def check_waste_alerts():
    now = datetime.now(TZ)
    alerts = []
    for sub_name, sub in SUBSCRIPTIONS.items():
        if sub["type"] != "rolling_window":
            continue
        window_h = sub.get("window_hours", 5)
        last_str = state.last_burn.get(sub_name)
        if not last_str:
            alerts.append(f"{sub_name}: never burned today!")
            continue
        last = datetime.fromisoformat(last_str)
        if last.tzinfo is None:
            last = last.replace(tzinfo=TZ)
        window_end = last + timedelta(hours=window_h)
        time_left = window_end - now
        if timedelta(0) < time_left < timedelta(hours=1):
            mins = int(time_left.total_seconds() / 60)
            alerts.append(f"{sub_name}: window expires in {mins}min - UNUSED quota!")
    if alerts:
        msg = "\n".join(alerts)
        log.warning(f"Waste alerts:\n{msg}")
        await ntfy("Quota Waste Alert", msg, priority="high", tags="warning")


async def daily_summary():
    now = datetime.now(TZ)
    lines = [f"Subscription utilization for {now.strftime('%Y-%m-%d')}:"]
    total_waste = 0.0
    total_cost = 0.0

    for sub_name, sub in SUBSCRIPTIONS.items():
        util = state.get_utilization(sub_name)
        cost = sub.get("cost_per_month", 0)
        daily_cost = cost / 30
        total_cost += daily_cost

        pct = util.get("utilization_pct", 0)
        waste = daily_cost * (1 - pct / 100)
        total_waste += waste
        if "utilization_pct" in util:
            lines.append(f"  {sub_name}: {pct}% utilized (${waste:.1f}/day wasted)")
        else:
            lines.append(f"  {sub_name}: {util.get('burns_today', 0)} burns")

    lines.append(f"\nDaily: ${total_cost:.0f}/day cost, ~${total_waste:.1f}/day wasted")
    lines.append(f"Monthly projection: ~${total_waste * 30:.0f}/mo waste")

    summary = "\n".join(lines)
    log.info(summary)
    await ntfy("Daily Burn Summary", summary, tags="chart_with_upwards_trend")

# ---------------------------------------------------------------------------
# Scheduler loop (simple async — no APScheduler dependency needed)
# ---------------------------------------------------------------------------
_scheduler_running = True

# CLI Router instance (lifecycle managed in lifespan)
_cli_router = CLIRouter()



# ---------------------------------------------------------------------------
# Zombie process reaper
# ---------------------------------------------------------------------------
async def reaper_loop():
    """Periodically reap completed burn processes and update state."""
    while _scheduler_running:
        try:
            for sub_name in list(state.active_procs.keys()):
                proc = state.active_procs.get(sub_name)
                if proc is None:
                    continue
                rc = proc.poll()
                if rc is not None:
                    pid = proc.pid
                    duration_s = None
                    last_str = state.last_burn.get(sub_name)
                    if last_str:
                        try:
                            started = datetime.fromisoformat(last_str)
                            if started.tzinfo is None:
                                started = started.replace(tzinfo=TZ)
                            duration_s = round((datetime.now(TZ) - started).total_seconds())
                        except Exception:
                            pass

                    state.active_procs.pop(sub_name, None)
                    state.active_pids.pop(sub_name, None)
                    state.save()

                    status_str = "success" if rc == 0 else f"failed (exit {rc})"
                    dur_str = f" in {duration_s // 60}m{duration_s % 60}s" if duration_s else ""
                    log.info(f"[reaper] {sub_name} PID {pid} completed: {status_str}{dur_str}")
                    mark_task_done(sub_name, "")

                    await ntfy(
                        f"Burn Complete: {sub_name}",
                        f"PID {pid} {status_str}{dur_str}",
                        tags="white_check_mark" if rc == 0 else "x",
                    )

            # Check for orphaned PIDs (from pre-restart state) with no Popen object
            for sub_name in list(state.active_pids.keys()):
                if sub_name in state.active_procs:
                    continue
                pid = state.active_pids[sub_name]
                try:
                    os.kill(pid, 0)
                except (ProcessLookupError, PermissionError):
                    state.active_pids.pop(sub_name, None)
                    state.save()
                    log.info(f"[reaper] Cleared stale PID {pid} for {sub_name}")
        except Exception as e:
            log.error(f"[reaper] Error: {e}")

        await asyncio.sleep(30)


async def scheduler_loop():
    fired_today: set[str] = set()
    last_waste_check: Optional[datetime] = None

    while _scheduler_running:
        now = datetime.now(TZ)
        today_key = now.strftime("%Y-%m-%d")

        # Reset fired set at midnight
        stale = [k for k in fired_today if not k.startswith(today_key)]
        for k in stale:
            fired_today.discard(k)

        # Check burn windows
        for window in BURN_SCHEDULE:
            wkey = f"{today_key}-{window['hour']:02d}:{window['minute']:02d}"
            if wkey in fired_today:
                continue
            target = now.replace(hour=window["hour"], minute=window["minute"], second=0, microsecond=0)
            diff = (now - target).total_seconds()
            if 0 <= diff < 120:
                fired_today.add(wkey)
                asyncio.create_task(run_burn_window(window))

        # Hourly waste check
        if last_waste_check is None or (now - last_waste_check).total_seconds() > 3600:
            last_waste_check = now
            asyncio.create_task(check_waste_alerts())

        # Daily summary at 23:00
        skey = f"{today_key}-summary"
        if now.hour == 23 and now.minute < 2 and skey not in fired_today:
            fired_today.add(skey)
            asyncio.create_task(daily_summary())

        await asyncio.sleep(30)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_running
    log.info("Subscription Burn Scheduler starting...")
    total = sum(s["cost_per_month"] for s in SUBSCRIPTIONS.values())
    log.info(f"Tracking {len(SUBSCRIPTIONS)} subscriptions, ${total}/mo total")
    log.info(f"Task dir: {TASKS_DIR}")
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize CLI Router embedding index
    try:
        await _cli_router.build_index()
        log.info("CLI Router index built successfully")
    except Exception as e:
        log.warning(f"CLI Router index build failed (non-fatal): {e}")

    sched_task = asyncio.create_task(scheduler_loop())
    reaper_task = asyncio.create_task(reaper_loop())
    await ntfy("Burn Scheduler Online", f"Tracking {len(SUBSCRIPTIONS)} subscriptions", tags="rocket")
    yield

    _scheduler_running = False
    sched_task.cancel()
    reaper_task.cancel()
    try:
        await sched_task
    except asyncio.CancelledError:
        pass
    try:
        await reaper_task
    except asyncio.CancelledError:
        pass
    await _cli_router.close()
    state.save()
    log.info("Subscription Burn Scheduler stopped.")


app = FastAPI(
    title="Athanor Subscription Burn Scheduler",
    description="Actively consumes rolling-window AI subscription quotas before they expire.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register CLI Router endpoints (/route, /dispatch, /classify, /router-stats)
register_router_endpoints(app, _cli_router)
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "subscription-burn",
        "subscriptions_tracked": len(SUBSCRIPTIONS),
        "timestamp": datetime.now(TZ).isoformat(),
    }


@app.get("/status")
async def get_status():
    now = datetime.now(TZ)
    subs = {}
    for name, sub in SUBSCRIPTIONS.items():
        subs[name] = {"cost_per_month": sub["cost_per_month"], **state.get_utilization(name)}
    return {
        "timestamp": now.isoformat(),
        "total_monthly_cost": sum(s["cost_per_month"] for s in SUBSCRIPTIONS.values()),
        "subscriptions": subs,
    }


@app.get("/waste-report")
async def waste_report():
    now = datetime.now(TZ)
    report = {}
    total_waste_daily = 0.0
    for name, sub in SUBSCRIPTIONS.items():
        util = state.get_utilization(name)
        cost = sub["cost_per_month"]
        daily_cost = cost / 30
        pct = util.get("utilization_pct", 0)
        dw = daily_cost * (1 - pct / 100)
        total_waste_daily += dw
        report[name] = {
            "cost_per_month": cost,
            "utilization_pct": pct,
            "daily_waste_est": round(dw, 2),
            "monthly_waste_est": round(dw * 30, 2),
        }
    return {
        "timestamp": now.isoformat(),
        "total_monthly_cost": sum(s["cost_per_month"] for s in SUBSCRIPTIONS.values()),
        "total_daily_waste_est": round(total_waste_daily, 2),
        "total_monthly_waste_est": round(total_waste_daily * 30, 2),
        "subscriptions": report,
    }


@app.post("/burn/{subscription}")
async def manual_burn(subscription: str):
    if subscription not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown subscription: {subscription}")
    result = await execute_burn(subscription, manual=True)
    if "error" in result and not result.get("skipped"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/schedule")
async def get_schedule():
    now = datetime.now(TZ)
    upcoming = []
    for w in BURN_SCHEDULE:
        target = now.replace(hour=w["hour"], minute=w["minute"], second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        hours_until = (target - now).total_seconds() / 3600
        upcoming.append({
            "label": w["label"],
            "time": target.strftime("%H:%M %Z"),
            "subscriptions": w["subs"],
            "hours_until": round(hours_until, 1),
            "next_fire": target.isoformat(),
        })
    upcoming.sort(key=lambda x: x["hours_until"])
    return {"timestamp": now.isoformat(), "windows": upcoming}


@app.get("/tasks/{subscription}")
async def get_tasks(subscription: str):
    if subscription not in SUBSCRIPTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown subscription: {subscription}")
    tasks = load_tasks(subscription)
    pending = [t for t in tasks if isinstance(t, dict) and t.get("status", "pending") == "pending"]
    in_progress = [t for t in tasks if isinstance(t, dict) and t.get("status") == "in_progress"]
    done = [t for t in tasks if isinstance(t, dict) and t.get("status") == "done"]
    return {
        "subscription": subscription,
        "task_file": SUBSCRIPTIONS[subscription].get("task_file"),
        "total": len(tasks),
        "pending": len(pending),
        "in_progress": len(in_progress),
        "done": len(done),
        "tasks": tasks,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8065, log_level="info")
