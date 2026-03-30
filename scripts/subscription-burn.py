#!/usr/bin/env python3
"""
Athanor Subscription Burn
=========================
Actively consumes rolling-window AI subscription quotas before they expire.
Runs as a FastAPI service on DEV:8065.

This service schedules automated burn sessions to maximize utilization.
Provider pricing truth now comes from the provider catalog when available;
legacy hardcoded schedule metadata is not treated as authoritative cost truth.
"""

import asyncio
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)
from service_contract import build_health_snapshot, dependency_record

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

try:
    from scripts._cluster_config import get_url
except ModuleNotFoundError:
    from _cluster_config import get_url

_CLI_ROUTER_PATH = Path(__file__).resolve().with_name("cli-router.py")
_cli_router_spec = importlib.util.spec_from_file_location("athanor_cli_router", _CLI_ROUTER_PATH)
if _cli_router_spec is None or _cli_router_spec.loader is None:
    raise RuntimeError(f"Unable to load CLI router from {_CLI_ROUTER_PATH}")
_cli_router_mod = importlib.util.module_from_spec(_cli_router_spec)
_cli_router_spec.loader.exec_module(_cli_router_mod)
CLIRouter = _cli_router_mod.CLIRouter
register_router_endpoints = _cli_router_mod.register_router_endpoints

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_TIMEZONE = os.environ.get("ATHANOR_TIMEZONE", "America/Chicago")
TZ = ZoneInfo(DEFAULT_TIMEZONE)
TASKS_DIR = Path.home() / ".athanor" / "subscription-tasks"
LOG_DIR = Path("/var/log/athanor")
USAGE_LOG = LOG_DIR / "subscription-usage.log"
STATE_FILE = Path.home() / ".athanor" / "subscription-burn-state.json"
NTFY_URL = get_url("ntfy_topic")
REPO_ROOT = Path(__file__).resolve().parent.parent
PROVIDER_CATALOG_PATH = REPO_ROOT / "config" / "automation-backbone" / "provider-catalog.json"
BURN_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "subscription-burn-registry.json"
SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()
SERVICE_NAME = "subscription-burn"
DEFAULT_WORKING_DIR = Path(
    os.environ.get("ATHANOR_RUNTIME_REPO_ROOT", "").strip() or str(REPO_ROOT)
)

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


def _resolve_cli_command(env_name: str, command_name: str, legacy_path: str | None = None) -> str:
    override = os.environ.get(env_name, "").strip()
    if override:
        return override
    discovered = shutil.which(command_name)
    if discovered:
        return discovered
    if legacy_path and Path(legacy_path).exists():
        return legacy_path
    return command_name


def _operator_action_payload(body: dict[str, Any]) -> dict[str, Any]:
    payload = body.get("operator_action")
    if isinstance(payload, dict):
        return dict(payload)
    return body


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    payload = _operator_action_payload(body)
    candidate = build_operator_action(payload, default_reason=default_reason)
    try:
        action = require_operator_action(payload, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


def _resolve_working_dir(raw_value: Any) -> str:
    candidate = str(raw_value or "").strip()
    if candidate:
        resolved = Path(os.path.expanduser(candidate))
        if resolved.exists():
            return str(resolved)
    return str(DEFAULT_WORKING_DIR)

# ---------------------------------------------------------------------------
# Registry-backed subscription definitions
# ---------------------------------------------------------------------------
def load_subscription_burn_registry() -> dict[str, Any]:
    if not BURN_REGISTRY_PATH.exists():
        log.warning("Burn registry unavailable at %s", BURN_REGISTRY_PATH)
        return {}
    try:
        payload = json.loads(BURN_REGISTRY_PATH.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("subscription-burn-registry.json must be a mapping")
        return payload
    except Exception as exc:
        log.warning("Failed to load burn registry from %s: %s", BURN_REGISTRY_PATH, exc)
        return {}


def build_runtime_subscriptions_from_registry(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runtime: dict[str, dict[str, Any]] = {}
    for entry in registry.get("subscriptions", []):
        if not isinstance(entry, dict):
            continue
        sub_id = str(entry.get("id") or "").strip()
        if not sub_id:
            continue
        cli_env = str(entry.get("cli_env") or "").strip()
        cli_command = str(entry.get("cli_command") or "").strip()
        if not cli_env or not cli_command:
            continue
        runtime[sub_id] = {
            "provider_id": str(entry.get("provider_id") or "").strip(),
            "stats_key": str(entry.get("stats_key") or "").strip(),
            "type": str(entry.get("type") or "").strip(),
            "window_hours": entry.get("window_hours"),
            "tokens_per_window": entry.get("tokens_per_window"),
            "daily_limit": entry.get("daily_limit"),
            "reset_time": str(entry.get("reset_time") or "").strip() or None,
            "monthly_limit": entry.get("monthly_limit"),
            "credits_remaining": entry.get("credits_remaining"),
            "auto_cancel": entry.get("auto_cancel"),
            "max_concurrent": entry.get("max_concurrent"),
            "task_file": str(entry.get("task_file") or "").strip(),
            "cli_env": cli_env,
            "cli_command": cli_command,
            "cli_args": list(entry.get("cli_args") or []),
            "legacy_path": str(entry.get("legacy_path") or "").strip() or None,
            "cli": _resolve_cli_command(
                cli_env,
                cli_command,
                legacy_path=str(entry.get("legacy_path") or "").strip() or None,
            ),
        }
    return runtime


def build_burn_schedule_from_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    schedule: list[dict[str, Any]] = []
    for entry in registry.get("windows", []):
        if not isinstance(entry, dict):
            continue
        schedule.append(
            {
                "id": str(entry.get("id") or "").strip(),
                "hour": int(entry.get("hour") or 0),
                "minute": int(entry.get("minute") or 0),
                "label": str(entry.get("label") or "").strip() or "Unnamed window",
                "subs": [str(item) for item in entry.get("subscriptions", []) if str(item).strip()],
            }
        )
    return schedule


def apply_burn_registry(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    global BURN_REGISTRY
    global SUBSCRIPTIONS
    global BURN_SCHEDULE

    BURN_REGISTRY = dict(registry or load_subscription_burn_registry())
    SUBSCRIPTIONS = build_runtime_subscriptions_from_registry(BURN_REGISTRY)
    BURN_SCHEDULE = build_burn_schedule_from_registry(BURN_REGISTRY)
    return BURN_REGISTRY


def load_provider_catalog_index() -> dict[str, dict[str, Any]]:
    if not PROVIDER_CATALOG_PATH.exists():
        return {}
    try:
        payload = json.loads(PROVIDER_CATALOG_PATH.read_text(encoding="utf-8"))
        providers = payload.get("providers", [])
        if not isinstance(providers, list):
            return {}
        return {
            entry["id"]: entry
            for entry in providers
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
    except Exception as exc:
        log.warning("Failed to load provider catalog from %s: %s", PROVIDER_CATALOG_PATH, exc)
        return {}


PROVIDER_CATALOG = load_provider_catalog_index()
BURN_REGISTRY: dict[str, Any] = {}
SUBSCRIPTIONS: dict[str, dict[str, Any]] = {}
BURN_SCHEDULE: list[dict[str, Any]] = []
apply_burn_registry()


def get_subscription_truth(sub_name: str) -> dict[str, Any]:
    provider_id = str(SUBSCRIPTIONS.get(sub_name, {}).get("provider_id") or "").strip() or None
    provider = PROVIDER_CATALOG.get(provider_id) if provider_id else None
    monthly_cost = provider.get("monthly_cost_usd") if provider else None
    if not isinstance(monthly_cost, (int, float)):
        monthly_cost = None
    pricing_status = (
        provider.get("official_pricing_status")
        if provider and isinstance(provider.get("official_pricing_status"), str)
        else "missing_provider_catalog_entry"
    )
    return {
        "provider_id": provider_id,
        "label": provider.get("label") if provider else sub_name,
        "subscription_product": provider.get("subscription_product") if provider else sub_name,
        "known_monthly_cost": monthly_cost,
        "pricing_status": pricing_status,
    }

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
    working_dir = _resolve_working_dir(task.get("working_dir") if isinstance(task, dict) else None)

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
    total_known_cost = 0.0
    pricing_gaps = 0

    for sub_name, sub in SUBSCRIPTIONS.items():
        util = state.get_utilization(sub_name)
        truth = get_subscription_truth(sub_name)
        cost = truth["known_monthly_cost"]
        daily_cost = (cost / 30) if isinstance(cost, (int, float)) else None
        if daily_cost is not None:
            total_known_cost += daily_cost
        else:
            pricing_gaps += 1

        pct = util.get("utilization_pct", 0)
        waste = (daily_cost * (1 - pct / 100)) if daily_cost is not None else None
        if waste is not None:
            total_waste += waste
        if "utilization_pct" in util and waste is not None:
            lines.append(
                f"  {sub_name}: {pct}% utilized (${waste:.1f}/day wasted, pricing={truth['pricing_status']})"
            )
        elif "utilization_pct" in util:
            lines.append(f"  {sub_name}: {pct}% utilized (pricing={truth['pricing_status']})")
        else:
            lines.append(f"  {sub_name}: {util.get('burns_today', 0)} burns")

    lines.append(f"\nKnown flat-rate burn: ${total_known_cost:.0f}/day, ~${total_waste:.1f}/day wasted")
    lines.append(f"Known monthly waste projection: ~${total_waste * 30:.0f}/mo")
    if pricing_gaps:
        lines.append(f"Pricing gaps still present for {pricing_gaps} scheduler lanes.")

    summary = "\n".join(lines)
    log.info(summary)
    await ntfy("Daily Burn Summary", summary, tags="chart_with_upwards_trend")

# ---------------------------------------------------------------------------
# Scheduler loop (simple async — no APScheduler dependency needed)
# ---------------------------------------------------------------------------
_scheduler_running = True
_scheduler_task: asyncio.Task | None = None
_reaper_task: asyncio.Task | None = None

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
    global _scheduler_running, _scheduler_task, _reaper_task
    _scheduler_running = True
    log.info("Subscription Burn starting...")
    known_total = sum(
        truth["known_monthly_cost"]
        for truth in (get_subscription_truth(name) for name in SUBSCRIPTIONS)
        if isinstance(truth["known_monthly_cost"], (int, float))
    )
    pricing_gaps = sum(
        1
        for name in SUBSCRIPTIONS
        if not isinstance(get_subscription_truth(name)["known_monthly_cost"], (int, float))
    )
    log.info(
        "Tracking %s subscriptions, known flat-rate total=$%s/mo, pricing_gaps=%s",
        len(SUBSCRIPTIONS),
        int(known_total),
        pricing_gaps,
    )
    log.info(f"Task dir: {TASKS_DIR}")
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize CLI Router embedding index
    try:
        await _cli_router.build_index()
        log.info("CLI Router index built successfully")
    except Exception as e:
        log.warning(f"CLI Router index build failed (non-fatal): {e}")

    _scheduler_task = asyncio.create_task(scheduler_loop())
    _reaper_task = asyncio.create_task(reaper_loop())
    await ntfy("Subscription Burn Online", f"Tracking {len(SUBSCRIPTIONS)} subscriptions", tags="rocket")
    yield

    _scheduler_running = False
    if _scheduler_task is not None:
        _scheduler_task.cancel()
    if _reaper_task is not None:
        _reaper_task.cancel()
    try:
        if _scheduler_task is not None:
            await _scheduler_task
    except asyncio.CancelledError:
        pass
    try:
        if _reaper_task is not None:
            await _reaper_task
    except asyncio.CancelledError:
        pass
    _scheduler_task = None
    _reaper_task = None
    await _cli_router.close()
    state.save()
    log.info("Subscription Burn stopped.")


app = FastAPI(
    title="Athanor Subscription Burn",
    description="Actively consumes rolling-window AI subscription quotas before they expire.",
    version="1.0.0",
    lifespan=lifespan,
)


def build_subscription_burn_health_snapshot() -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    dependencies = [
        dependency_record(
            "scheduler_loop",
            status="healthy" if _scheduler_task is not None and not _scheduler_task.done() else "degraded",
            detail=(
                "Subscription burn scheduler loop active"
                if _scheduler_task is not None and not _scheduler_task.done()
                else "Subscription burn scheduler loop is not active"
            ),
            last_checked_at=checked_at,
        ),
        dependency_record(
            "reaper_loop",
            status="healthy" if _reaper_task is not None and not _reaper_task.done() else "degraded",
            detail=(
                "Subscription burn process reaper active"
                if _reaper_task is not None and not _reaper_task.done()
                else "Subscription burn process reaper is not active"
            ),
            last_checked_at=checked_at,
        ),
        dependency_record(
            "task_directory",
            status="healthy" if TASKS_DIR.exists() else "degraded",
            detail=f"Task directory at {TASKS_DIR}",
            last_checked_at=checked_at,
        ),
        dependency_record(
            "provider_catalog",
            status="healthy" if PROVIDER_CATALOG else "degraded",
            detail=(
                f"Loaded {len(PROVIDER_CATALOG)} provider entries from {PROVIDER_CATALOG_PATH.name}"
                if PROVIDER_CATALOG
                else f"Provider catalog unavailable at {PROVIDER_CATALOG_PATH}"
            ),
            last_checked_at=checked_at,
        ),
        dependency_record(
            "burn_registry",
            status="healthy" if BURN_REGISTRY else "degraded",
            detail=(
                f"Loaded {len(SUBSCRIPTIONS)} burn subscriptions and {len(BURN_SCHEDULE)} windows from {BURN_REGISTRY_PATH.name}"
                if BURN_REGISTRY
                else f"Burn registry unavailable at {BURN_REGISTRY_PATH}"
            ),
            last_checked_at=checked_at,
        ),
        dependency_record(
            "cli_router_index",
            status="healthy" if _cli_router.index.ready else "degraded",
            detail=(
                f"Embedding index ready for {len(_cli_router.index.centroids)} task types"
                if _cli_router.index.ready
                else "CLI router index not ready; dispatch will fall back to slower classification"
            ),
            required=False,
            last_checked_at=checked_at,
        ),
        dependency_record(
            "ntfy_topic",
            status="healthy" if NTFY_URL else "degraded",
            detail=NTFY_URL or "Notification topic URL is not configured",
            required=False,
            last_checked_at=checked_at,
        ),
    ]

    return build_health_snapshot(
        service=SERVICE_NAME,
        version=app.version,
        auth_class="internal_only",
        dependencies=dependencies,
        started_at=SERVICE_STARTED_AT,
        actions_allowed=[
            "burn.execute",
            "router.dispatch",
            "router.learning.record",
            "router.cache.invalidate",
        ],
        subscriptions_tracked=len(SUBSCRIPTIONS),
        burn_registry_version=str(BURN_REGISTRY.get("version") or ""),
        burn_registry_source=str(BURN_REGISTRY.get("source_of_truth") or ""),
        windows_tracked=len(BURN_SCHEDULE),
        scheduler_running=_scheduler_running,
        task_directory=str(TASKS_DIR),
    )


# Register CLI Router endpoints (/route, /dispatch, /classify, /router-stats)
register_router_endpoints(app, _cli_router, service_name=SERVICE_NAME)
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    snapshot = build_subscription_burn_health_snapshot()
    snapshot["timestamp"] = datetime.now(TZ).isoformat()
    return snapshot


@app.get("/status")
async def get_status():
    now = datetime.now(TZ)
    subs = {}
    for name, sub in SUBSCRIPTIONS.items():
        truth = get_subscription_truth(name)
        subs[name] = {
            "cost_per_month": truth["known_monthly_cost"],
            "pricing_status": truth["pricing_status"],
            "provider_id": truth["provider_id"],
            "label": truth["label"],
            "subscription_product": truth["subscription_product"],
            **state.get_utilization(name),
        }
    known_total = sum(
        truth["known_monthly_cost"]
        for truth in (get_subscription_truth(name) for name in SUBSCRIPTIONS)
        if isinstance(truth["known_monthly_cost"], (int, float))
    )
    return {
        "timestamp": now.isoformat(),
        "burn_registry_version": str(BURN_REGISTRY.get("version") or ""),
        "burn_registry_source": str(BURN_REGISTRY.get("source_of_truth") or ""),
        "total_monthly_cost": known_total,
        "known_flat_rate_monthly_cost": known_total,
        "pricing_gap_count": sum(
            1
            for name in SUBSCRIPTIONS
            if not isinstance(get_subscription_truth(name)["known_monthly_cost"], (int, float))
        ),
        "subscriptions": subs,
    }


@app.get("/waste-report")
async def waste_report():
    now = datetime.now(TZ)
    report = {}
    total_waste_daily = 0.0
    for name, sub in SUBSCRIPTIONS.items():
        util = state.get_utilization(name)
        truth = get_subscription_truth(name)
        cost = truth["known_monthly_cost"]
        daily_cost = (cost / 30) if isinstance(cost, (int, float)) else None
        pct = util.get("utilization_pct", 0)
        dw = (daily_cost * (1 - pct / 100)) if daily_cost is not None else None
        if dw is not None:
            total_waste_daily += dw
        report[name] = {
            "cost_per_month": cost,
            "pricing_status": truth["pricing_status"],
            "provider_id": truth["provider_id"],
            "utilization_pct": pct,
            "daily_waste_est": round(dw, 2) if dw is not None else None,
            "monthly_waste_est": round(dw * 30, 2) if dw is not None else None,
        }
    known_total = sum(
        truth["known_monthly_cost"]
        for truth in (get_subscription_truth(name) for name in SUBSCRIPTIONS)
        if isinstance(truth["known_monthly_cost"], (int, float))
    )
    return {
        "timestamp": now.isoformat(),
        "burn_registry_version": str(BURN_REGISTRY.get("version") or ""),
        "total_monthly_cost": known_total,
        "known_flat_rate_monthly_cost": known_total,
        "total_daily_waste_est": round(total_waste_daily, 2),
        "total_monthly_waste_est": round(total_waste_daily * 30, 2),
        "pricing_gap_count": sum(
            1
            for name in SUBSCRIPTIONS
            if not isinstance(get_subscription_truth(name)["known_monthly_cost"], (int, float))
        ),
        "subscriptions": report,
    }


@app.post("/burn/{subscription}")
async def manual_burn(subscription: str, request: Request):
    route = "/burn/{subscription}"
    _body, action, denial = await _load_operator_body(
        request,
        route=route,
        action_class="admin",
        default_reason=f"Executed manual subscription burn for {subscription}",
    )
    if denial:
        return denial
    if subscription not in SUBSCRIPTIONS:
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route=route,
            action_class="admin",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Unknown subscription: {subscription}",
            target=subscription,
        )
        raise HTTPException(status_code=404, detail=f"Unknown subscription: {subscription}")
    result = await execute_burn(subscription, manual=True)
    if "error" in result and not result.get("skipped"):
        await emit_operator_audit_event(
            service=SERVICE_NAME,
            route=route,
            action_class="admin",
            decision="denied",
            status_code=500,
            action=action,
            detail=str(result["error"]),
            target=subscription,
        )
        raise HTTPException(status_code=500, detail=result["error"])
    await emit_operator_audit_event(
        service=SERVICE_NAME,
        route=route,
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=(
            f"Triggered manual burn for {subscription}"
            if "pid" in result
            else str(result.get("error") or "Manual burn request skipped")
        ),
        target=subscription,
        metadata={
            "skipped": bool(result.get("skipped")),
            "pid": result.get("pid"),
        },
    )
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
            "id": w.get("id"),
            "label": w["label"],
            "time": target.strftime("%H:%M %Z"),
            "subscriptions": w["subs"],
            "hours_until": round(hours_until, 1),
            "next_fire": target.isoformat(),
        })
    upcoming.sort(key=lambda x: x["hours_until"])
    return {
        "timestamp": now.isoformat(),
        "burn_registry_version": str(BURN_REGISTRY.get("version") or ""),
        "windows": upcoming,
    }


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
