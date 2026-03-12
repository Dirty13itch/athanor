from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from .activity import query_activity
from .alerts import get_active_alerts, get_alert_history
from .research_jobs import list_jobs
from .scheduler import (
    ALERT_CHECK_INTERVAL,
    ALERT_CHECK_KEY,
    BENCHMARK_INTERVAL,
    BENCHMARK_KEY,
    CACHE_CLEANUP_INTERVAL,
    CACHE_CLEANUP_KEY,
    CONSOLIDATION_HOUR,
    CONSOLIDATION_KEY,
    CONSOLIDATION_MINUTE,
    DIGEST_HOUR,
    DIGEST_MINUTE,
    DAILY_DIGEST_KEY,
    IMPROVEMENT_CYCLE_HOUR,
    IMPROVEMENT_CYCLE_KEY,
    IMPROVEMENT_CYCLE_MINUTE,
    PATTERN_DETECTION_KEY,
    PATTERN_HOUR,
    PATTERN_MINUTE,
    WORKPLAN_HOUR,
    WORKPLAN_MINUTE,
    WORKPLAN_MORNING_KEY,
    WORKPLAN_REFILL_INTERVAL,
    WORKPLAN_REFILL_KEY,
    _get_redis,
    get_schedule_status,
)
from .subscriptions import get_policy_snapshot, get_quota_summary, list_execution_leases
from .tasks import list_tasks


def _iso_from_unix(value: Any) -> str | None:
    if value in (None, "", 0, 0.0):
        return None
    try:
        return datetime.fromtimestamp(float(value)).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_artifact_refs(task: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = [{"label": "task", "href": f"/tasks?task={task.get('id', '')}"}]
    metadata = dict(task.get("metadata") or {})
    if metadata.get("job_id"):
        refs.append({"label": "research-job", "href": "/workplanner"})
    if metadata.get("project"):
        refs.append({"label": "project", "href": f"/workplanner?project={metadata['project']}"})
    elif metadata.get("project_id"):
        refs.append({"label": "project", "href": f"/workplanner?project={metadata['project_id']}"})
    if task.get("result"):
        refs.append({"label": "result", "href": "/tasks"})
    return refs


def _run_summary(task: dict[str, Any]) -> str:
    prompt = str(task.get("prompt") or "").strip()
    if prompt:
        return prompt[:96]
    metadata = dict(task.get("metadata") or {})
    if metadata.get("topic"):
        return str(metadata["topic"])
    return f"Task {task.get('id', 'unknown')}"


async def build_execution_run_records(agent: str = "", limit: int = 50) -> list[dict[str, Any]]:
    task_limit = max(limit * 3, 50)
    tasks = await list_tasks(agent=agent, limit=task_limit)
    runs: list[dict[str, Any]] = []

    for task in tasks:
        metadata = dict(task.get("metadata") or {})
        lease = dict(metadata.get("execution_lease") or {})
        provider = str(lease.get("provider") or metadata.get("provider") or "athanor_local")
        source_lane = str(lease.get("surface") or metadata.get("source") or "local_inference")
        created_at = _iso_from_unix(task.get("created_at"))
        started_at = _iso_from_unix(task.get("started_at")) or created_at
        completed_at = _iso_from_unix(task.get("completed_at"))
        status = str(task.get("status") or "pending")
        failure_reason = str(task.get("error") or "") or None

        runs.append(
            {
                "id": f"run-{task.get('id', 'unknown')}",
                "source_lane": source_lane,
                "run_type": str(metadata.get("source") or "task"),
                "task_id": task.get("id"),
                "job_id": metadata.get("job_id"),
                "agent": task.get("agent"),
                "provider": provider,
                "lease_id": lease.get("id"),
                "status": status,
                "created_at": created_at,
                "started_at": started_at,
                "completed_at": completed_at,
                "artifact_refs": _build_artifact_refs(task),
                "failure_reason": failure_reason,
                "summary": _run_summary(task),
            }
        )

    runs.sort(
        key=lambda run: run.get("started_at") or run.get("created_at") or "",
        reverse=True,
    )
    return runs[:limit]


def _recent_outcomes(stats: dict[str, Any]) -> list[dict[str, Any]]:
    outcomes = dict(stats.get("outcomes") or {})
    return [
        {"outcome": outcome, "count": int(count)}
        for outcome, count in sorted(outcomes.items(), key=lambda item: item[0])
    ]


async def build_quota_lease_summary(limit: int = 10) -> dict[str, Any]:
    policy = get_policy_snapshot()
    quotas = await get_quota_summary()
    recent_leases = await list_execution_leases(limit=limit)
    provider_stats = dict(quotas.get("providers") or {})
    providers: list[dict[str, Any]] = []

    for provider_id, provider_meta in dict(policy.get("providers") or {}).items():
        stats = dict(provider_stats.get(provider_id) or {})
        providers.append(
            {
                "provider": provider_id,
                "lane": provider_meta.get("role", "unclassified"),
                "availability": "constrained"
                if int(stats.get("throttle_events", 0)) > 0
                else str(stats.get("status") or "available"),
                "reserve_state": provider_meta.get("reserve", "standard"),
                "limit": int(stats.get("limit", 0) or 0),
                "remaining": int(stats.get("remaining", 0) or 0),
                "throttle_events": int(stats.get("throttle_events", 0) or 0),
                "recent_outcomes": _recent_outcomes(stats),
                "last_issued_at": _iso_from_unix(stats.get("last_issued_at")),
                "last_outcome_at": _iso_from_unix(stats.get("last_outcome_at")),
            }
        )

    providers.sort(key=lambda item: item["provider"])
    recent_runs = [
        {
            "id": f"lease-{lease.get('id', 'unknown')}",
            "source_lane": lease.get("surface", "unknown"),
            "run_type": "lease",
            "task_id": None,
            "job_id": None,
            "agent": lease.get("requester", "unknown"),
            "provider": lease.get("provider", "unknown"),
            "lease_id": lease.get("id"),
            "status": lease.get("outcome", "issued"),
            "created_at": _iso_from_unix(lease.get("created_at")),
            "started_at": _iso_from_unix(lease.get("created_at")),
            "completed_at": _iso_from_unix(lease.get("completed_at")),
            "artifact_refs": [{"label": "agents", "href": "/agents"}],
            "failure_reason": lease.get("notes") or None,
            "summary": f"{lease.get('requester', 'agent')} -> {lease.get('task_class', 'task')}",
        }
        for lease in recent_leases
    ]

    return {
        "policy_source": policy.get("policy_source", "unknown"),
        "provider_summaries": providers,
        "recent_leases": recent_runs,
        "count": len(providers),
    }


def _next_daily_occurrence(hour: int, minute: int) -> str:
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate.isoformat()


async def _read_schedule_marker(key: str) -> str | None:
    redis = await _get_redis()
    value = await redis.get(key)
    if not value:
        return None
    raw = value.decode() if isinstance(value, bytes) else str(value)
    try:
        if raw.count("-") == 2 and len(raw) == 10:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
            return parsed.isoformat()
        return _iso_from_unix(float(raw))
    except (TypeError, ValueError):
        return None


async def build_scheduled_job_records(limit: int = 50) -> list[dict[str, Any]]:
    schedule_status = await get_schedule_status()
    now = time.time()
    jobs: list[dict[str, Any]] = []

    for entry in schedule_status.get("schedules", []):
        next_run_in = int(entry.get("next_run_in", 0) or 0)
        jobs.append(
            {
                "id": f"agent-schedule:{entry.get('agent', 'unknown')}",
                "job_family": "agent_schedule",
                "title": f"{entry.get('agent', 'unknown')} proactive loop",
                "cadence": entry.get("interval_human", "interval"),
                "trigger_mode": "interval",
                "last_run": _iso_from_unix(entry.get("last_run")),
                "next_run": _iso_from_unix(now + next_run_in),
                "current_state": "running"
                if entry.get("enabled", True) and schedule_status.get("scheduler_running")
                else "paused",
                "last_outcome": "scheduled",
                "owner_agent": entry.get("agent"),
                "deep_link": f"/agents?agent={entry.get('agent', '')}",
            }
        )

    builtin_definitions = [
        {
            "id": "daily-digest",
            "key": DAILY_DIGEST_KEY,
            "job_family": "daily_digest",
            "title": "Daily briefing",
            "cadence": "daily 6:55",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(DIGEST_HOUR, DIGEST_MINUTE),
            "deep_link": "/",
        },
        {
            "id": "pattern-detection",
            "key": PATTERN_DETECTION_KEY,
            "job_family": "pattern_detection",
            "title": "Pattern detection",
            "cadence": "daily 5:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(PATTERN_HOUR, PATTERN_MINUTE),
            "deep_link": "/insights",
        },
        {
            "id": "consolidation",
            "key": CONSOLIDATION_KEY,
            "job_family": "consolidation",
            "title": "Memory consolidation",
            "cadence": "daily 3:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(CONSOLIDATION_HOUR, CONSOLIDATION_MINUTE),
            "deep_link": "/personal-data",
        },
        {
            "id": "morning-plan",
            "key": WORKPLAN_MORNING_KEY,
            "job_family": "workplan",
            "title": "Morning workplan refresh",
            "cadence": "daily 7:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(WORKPLAN_HOUR, WORKPLAN_MINUTE),
            "deep_link": "/workplanner",
        },
        {
            "id": "workplan-refill",
            "key": WORKPLAN_REFILL_KEY,
            "job_family": "workplan_refill",
            "title": "Workplan refill check",
            "cadence": "every 2h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + WORKPLAN_REFILL_INTERVAL),
            "deep_link": "/workplanner",
        },
        {
            "id": "alert-check",
            "key": ALERT_CHECK_KEY,
            "job_family": "alerts",
            "title": "Alert polling",
            "cadence": "every 5m",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + ALERT_CHECK_INTERVAL),
            "deep_link": "/notifications",
        },
        {
            "id": "benchmark-cycle",
            "key": BENCHMARK_KEY,
            "job_family": "benchmarks",
            "title": "Benchmark cycle",
            "cadence": "every 6h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + BENCHMARK_INTERVAL),
            "deep_link": "/learning",
        },
        {
            "id": "cache-cleanup",
            "key": CACHE_CLEANUP_KEY,
            "job_family": "cache_cleanup",
            "title": "Semantic cache cleanup",
            "cadence": "every 1h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + CACHE_CLEANUP_INTERVAL),
            "deep_link": "/learning",
        },
        {
            "id": "improvement-cycle",
            "key": IMPROVEMENT_CYCLE_KEY,
            "job_family": "improvement_cycle",
            "title": "Improvement cycle",
            "cadence": "daily 5:30",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(IMPROVEMENT_CYCLE_HOUR, IMPROVEMENT_CYCLE_MINUTE),
            "deep_link": "/review",
        },
    ]

    for definition in builtin_definitions:
        jobs.append(
            {
                "id": definition["id"],
                "job_family": definition["job_family"],
                "title": definition["title"],
                "cadence": definition["cadence"],
                "trigger_mode": definition["trigger_mode"],
                "last_run": await _read_schedule_marker(definition["key"]),
                "next_run": definition["next_run"],
                "current_state": "scheduled",
                "last_outcome": "scheduled",
                "owner_agent": "system",
                "deep_link": definition["deep_link"],
            }
        )

    for job in await list_jobs():
        schedule_hours = int(job.get("schedule_hours", 0) or 0)
        last_run_raw = _safe_float(job.get("last_run"))
        next_run = _iso_from_unix(last_run_raw + (schedule_hours * 3600)) if schedule_hours > 0 and last_run_raw else None
        jobs.append(
            {
                "id": f"research:{job.get('id') or job.get('job_id')}",
                "job_family": "research_job",
                "title": job.get("topic", "Research job"),
                "cadence": f"every {schedule_hours}h" if schedule_hours > 0 else "manual",
                "trigger_mode": "interval" if schedule_hours > 0 else "manual",
                "last_run": _iso_from_unix(job.get("last_run")),
                "next_run": next_run,
                "current_state": job.get("status", "scheduled"),
                "last_outcome": "failed" if job.get("error") else job.get("status", "scheduled"),
                "owner_agent": "research-agent",
                "deep_link": "/workplanner",
            }
        )

    jobs.sort(key=lambda item: item.get("next_run") or item.get("last_run") or "", reverse=False)
    return jobs[:limit]


def _event_severity_for_run(status: str) -> str:
    if status == "failed":
        return "error"
    if status in {"pending", "running"}:
        return "info"
    return "success"


async def build_operator_stream(limit: int = 30) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    alert_history = await get_alert_history(limit=max(limit, 10))
    active_alerts = await get_active_alerts()
    activity_items = await query_activity(limit=max(limit, 10))
    runs = await build_execution_run_records(limit=max(limit, 10))

    for alert in alert_history:
        timestamp = _iso_from_unix(alert.get("timestamp")) or datetime.now().isoformat()
        events.append(
            {
                "id": f"alert-history:{alert.get('alertname', 'alert')}:{timestamp}",
                "timestamp": timestamp,
                "severity": "error" if alert.get("severity") == "critical" else "warning",
                "subsystem": "alerts",
                "event_type": "alert_history",
                "subject": alert.get("alertname", "runtime alert"),
                "summary": alert.get("body", "Alert history item"),
                "deep_link": "/notifications",
                "related_run_id": None,
            }
        )

    for alert in active_alerts.get("alerts", []):
        timestamp = alert.get("active_at") or datetime.now().isoformat()
        events.append(
            {
                "id": f"alert-active:{alert.get('alertname', 'alert')}:{timestamp}",
                "timestamp": timestamp,
                "severity": "error" if alert.get("severity") == "critical" else "warning",
                "subsystem": "alerts",
                "event_type": "alert_active",
                "subject": alert.get("alertname", "runtime alert"),
                "summary": alert.get("summary") or alert.get("description") or "Active alert",
                "deep_link": "/notifications",
                "related_run_id": None,
            }
        )

    for item in activity_items:
        timestamp = str(item.get("timestamp") or datetime.now().isoformat())
        agent = item.get("agent", "system")
        events.append(
            {
                "id": f"activity:{agent}:{timestamp}:{item.get('action_type', 'activity')}",
                "timestamp": timestamp,
                "severity": "info",
                "subsystem": "agents",
                "event_type": item.get("action_type", "activity"),
                "subject": agent,
                "summary": item.get("input_summary") or item.get("output_summary") or "Agent activity",
                "deep_link": f"/agents?agent={agent}",
                "related_run_id": None,
            }
        )

    for run in runs:
        status = str(run.get("status") or "pending")
        events.append(
            {
                "id": f"run-event:{run['id']}",
                "timestamp": run.get("completed_at") or run.get("started_at") or run.get("created_at"),
                "severity": _event_severity_for_run(status),
                "subsystem": "provider-plane" if run.get("provider") != "athanor_local" else "tasks",
                "event_type": f"run_{status}",
                "subject": run.get("agent", "agent"),
                "summary": f"{run.get('summary', 'Execution run')} via {run.get('provider', 'unknown')}",
                "deep_link": "/tasks" if run.get("task_id") else "/agents",
                "related_run_id": run["id"],
            }
        )

    events.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return events[:limit]
