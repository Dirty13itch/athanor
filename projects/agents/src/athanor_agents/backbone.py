from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from .activity import query_activity, query_events
from .alerts import get_active_alerts, get_alert_history
from .model_governance import (
    get_contract_registry,
    get_eval_corpus_registry,
    get_experiment_ledger_policy,
    get_policy_class_registry,
)
from .provider_execution import build_provider_posture_records, list_handoff_bundles
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
    DAILY_DIGEST_KEY,
    DIGEST_HOUR,
    DIGEST_MINUTE,
    DPO_TRAINING_HOUR,
    DPO_TRAINING_KEY,
    DPO_TRAINING_MINUTE,
    DPO_TRAINING_WEEKDAY,
    CODE_CASCADE_INTERVAL,
    CODE_CASCADE_KEY,
    IMPROVEMENT_CYCLE_HOUR,
    IMPROVEMENT_CYCLE_KEY,
    IMPROVEMENT_CYCLE_MINUTE,
    KNOWLEDGE_REFRESH_HOUR,
    KNOWLEDGE_REFRESH_KEY,
    KNOWLEDGE_REFRESH_MINUTE,
    NIGHTLY_OPTIMIZATION_HOUR,
    NIGHTLY_OPTIMIZATION_KEY,
    NIGHTLY_OPTIMIZATION_MINUTE,
    OWNER_MODEL_HOUR,
    OWNER_MODEL_KEY,
    OWNER_MODEL_MINUTE,
    PATTERN_DETECTION_KEY,
    PATTERN_HOUR,
    PATTERN_MINUTE,
    PIPELINE_INTERVAL,
    PIPELINE_KEY,
    SCHEDULER_INTERVAL,
    CREATIVE_CASCADE_INTERVAL,
    CREATIVE_CASCADE_KEY,
    WORKPLAN_HOUR,
    WORKPLAN_MINUTE,
    WORKPLAN_MORNING_KEY,
    WORKPLAN_REFILL_INTERVAL,
    WORKPLAN_REFILL_KEY,
    _get_redis,
    get_schedule_control_scope,
    get_schedule_status,
)
from .subscriptions import get_policy_snapshot, list_execution_leases
from .tasks import list_recent_tasks


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


def _build_governance_versions(
    metadata: dict[str, Any],
    command_decision: dict[str, Any],
    plan_packet: dict[str, Any],
) -> dict[str, Any]:
    seeded = dict(metadata.get("governance_versions") or {})
    return {
        "prompt_version": str(
            seeded.get("prompt_version")
            or metadata.get("prompt_version")
            or plan_packet.get("prompt_version")
            or command_decision.get("prompt_version")
            or "inline-unversioned"
        ),
        "policy_version": str(
            seeded.get("policy_version")
            or command_decision.get("policy_version")
            or plan_packet.get("policy_version")
            or get_policy_class_registry().get("version", "unknown")
        ),
        "corpus_version": seeded.get("corpus_version")
        or metadata.get("corpus_version")
        or plan_packet.get("corpus_version")
        or command_decision.get("corpus_version"),
        "contract_registry_version": str(
            seeded.get("contract_registry_version")
            or get_contract_registry().get("version", "unknown")
        ),
        "eval_corpus_registry_version": str(
            seeded.get("eval_corpus_registry_version")
            or get_eval_corpus_registry().get("version", "unknown")
        ),
        "experiment_ledger_version": str(
            seeded.get("experiment_ledger_version")
            or get_experiment_ledger_policy().get("version", "unknown")
        ),
    }


def _build_artifact_provenance(
    *,
    metadata: dict[str, Any],
    command_decision: dict[str, Any],
    plan_packet: dict[str, Any],
    artifact_refs: list[dict[str, str]],
    source_lane: str,
    provider: str,
    run_id: str,
    governance_versions: dict[str, Any],
) -> dict[str, Any]:
    seeded = dict(metadata.get("artifact_provenance") or {})
    return {
        "run_id": run_id,
        "status": str(seeded.get("status") or ("linked" if artifact_refs else "partial")),
        "deciding_layer": str(
            seeded.get("deciding_layer")
            or command_decision.get("authority_layer")
            or "governor"
        ),
        "policy_class": command_decision.get("policy_class") or seeded.get("policy_class"),
        "meta_lane": command_decision.get("meta_lane") or seeded.get("meta_lane") or source_lane,
        "supervisor_lane": plan_packet.get("supervisor_lane") or seeded.get("supervisor_lane"),
        "worker_lane": plan_packet.get("worker_lane") or seeded.get("worker_lane"),
        "judge_lane": plan_packet.get("judge_lane") or seeded.get("judge_lane"),
        "provider": provider,
        "artifact_ref_count": len(artifact_refs),
        "prompt_version": governance_versions.get("prompt_version"),
        "policy_version": governance_versions.get("policy_version"),
        "corpus_version": governance_versions.get("corpus_version"),
        "contract_registry_version": governance_versions.get("contract_registry_version"),
        "experiment_ledger_version": governance_versions.get("experiment_ledger_version"),
    }


def _build_run_lineage(
    *,
    run_id: str,
    source_lane: str,
    provider: str,
    parent_task_id: str = "",
    metadata: dict[str, Any] | None = None,
    plan_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = metadata or {}
    packet = plan_packet or {}
    parent_run_id = str(meta.get("parent_run_id") or "").strip() or None
    if not parent_run_id and parent_task_id:
        parent_run_id = f"run-{parent_task_id}"
    return {
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "supervisor_run_id": str(meta.get("supervisor_run_id") or "").strip() or parent_run_id,
        "worker_run_id": str(meta.get("worker_run_id") or "").strip() or (run_id if packet.get("worker_lane") else None),
        "judge_run_id": str(meta.get("judge_run_id") or "").strip() or None,
        "provider": provider,
        "lane": source_lane,
    }


async def build_execution_run_records(agent: str = "", limit: int = 50) -> list[dict[str, Any]]:
    task_limit = max(limit * 3, 50)
    tasks = await list_recent_tasks(agent=agent, limit=task_limit)
    runs: list[dict[str, Any]] = []

    for task in tasks:
        metadata = dict(task.get("metadata") or {})
        lease = dict(metadata.get("execution_lease") or {})
        command_decision = dict(metadata.get("command_decision") or {})
        plan_packet = dict(metadata.get("plan_packet") or {})
        provider = str(lease.get("provider") or metadata.get("provider") or "athanor_local")
        source_lane = str(
            command_decision.get("meta_lane")
            or lease.get("metadata", {}).get("meta_lane")
            or metadata.get("meta_lane")
            or lease.get("surface")
            or metadata.get("source")
            or "local_inference"
        )
        created_at = _iso_from_unix(task.get("created_at"))
        started_at = _iso_from_unix(task.get("started_at")) or created_at
        completed_at = _iso_from_unix(task.get("completed_at"))
        status = str(task.get("status") or "pending")
        failure_reason = str(task.get("error") or "") or None
        run_id = f"run-{task.get('id', 'unknown')}"
        artifact_refs = _build_artifact_refs(task)
        governance_versions = _build_governance_versions(metadata, command_decision, plan_packet)
        lineage = _build_run_lineage(
            run_id=run_id,
            source_lane=source_lane,
            provider=provider,
            parent_task_id=str(task.get("parent_task_id") or ""),
            metadata=metadata,
            plan_packet=plan_packet,
        )
        artifact_provenance = _build_artifact_provenance(
            metadata=metadata,
            command_decision=command_decision,
            plan_packet=plan_packet,
            artifact_refs=artifact_refs,
            source_lane=source_lane,
            provider=provider,
            run_id=run_id,
            governance_versions=governance_versions,
        )

        runs.append(
            {
                "id": run_id,
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
                "policy_class": command_decision.get("policy_class") or lease.get("metadata", {}).get("policy_class"),
                "approval_mode": plan_packet.get("approval_mode") or lease.get("metadata", {}).get("approval_mode"),
                "command_decision_id": command_decision.get("id") or lease.get("metadata", {}).get("command_decision_id"),
                "supervisor_lane": plan_packet.get("supervisor_lane"),
                "worker_lane": plan_packet.get("worker_lane"),
                "judge_lane": plan_packet.get("judge_lane"),
                "prompt_version": governance_versions.get("prompt_version"),
                "policy_version": governance_versions.get("policy_version"),
                "corpus_version": governance_versions.get("corpus_version"),
                "lineage": lineage,
                "artifact_provenance": artifact_provenance,
                "artifact_refs": artifact_refs,
                "failure_reason": failure_reason,
                "summary": _run_summary(task),
            }
        )

    handoffs = await list_handoff_bundles(requester=agent, limit=max(limit * 2, 25))
    for handoff in handoffs:
        command_decision = dict(handoff.get("command_decision") or {})
        plan_packet = dict(handoff.get("plan_packet") or {})
        metadata = {
            "governance_versions": dict(handoff.get("governance_versions") or {}),
            "artifact_provenance": dict(handoff.get("artifact_provenance") or {}),
            "parent_run_id": handoff.get("parent_run_id"),
            "supervisor_run_id": handoff.get("supervisor_run_id"),
            "worker_run_id": handoff.get("worker_run_id"),
            "judge_run_id": handoff.get("judge_run_id"),
            "corpus_version": handoff.get("corpus_version"),
            "prompt_version": handoff.get("prompt_version"),
        }
        summary = str(handoff.get("result_summary") or handoff.get("summary") or "Provider handoff")
        created_at = _iso_from_unix(handoff.get("created_at"))
        completed_at = _iso_from_unix(handoff.get("completed_at"))
        status = str(handoff.get("status") or "pending")
        failure_reason = str(handoff.get("failure_reason") or "") or None
        run_id = str(handoff.get("id") or "handoff")
        source_lane = str(handoff.get("meta_lane") or handoff.get("execution_mode") or "frontier_cloud")
        provider = str(handoff.get("provider") or "athanor_local")
        artifact_refs = list(handoff.get("artifact_refs") or [{"label": "agents", "href": "/agents"}])
        governance_versions = _build_governance_versions(metadata, command_decision, plan_packet)
        lineage = _build_run_lineage(
            run_id=run_id,
            source_lane=source_lane,
            provider=provider,
            metadata=metadata,
            plan_packet=plan_packet,
        )
        artifact_provenance = _build_artifact_provenance(
            metadata=metadata,
            command_decision=command_decision,
            plan_packet=plan_packet,
            artifact_refs=artifact_refs,
            source_lane=source_lane,
            provider=provider,
            run_id=run_id,
            governance_versions=governance_versions,
        )
        runs.append(
            {
                "id": run_id,
                "source_lane": source_lane,
                "run_type": "handoff",
                "task_id": None,
                "job_id": None,
                "agent": str(handoff.get("requester") or "agent"),
                "provider": provider,
                "lease_id": handoff.get("lease_id"),
                "status": status,
                "created_at": created_at,
                "started_at": created_at,
                "completed_at": completed_at,
                "policy_class": handoff.get("policy_class"),
                "approval_mode": plan_packet.get("approval_mode"),
                "command_decision_id": command_decision.get("id"),
                "supervisor_lane": plan_packet.get("supervisor_lane"),
                "worker_lane": plan_packet.get("worker_lane"),
                "judge_lane": plan_packet.get("judge_lane"),
                "prompt_version": governance_versions.get("prompt_version"),
                "policy_version": governance_versions.get("policy_version"),
                "corpus_version": governance_versions.get("corpus_version"),
                "lineage": lineage,
                "artifact_provenance": artifact_provenance,
                "artifact_refs": artifact_refs,
                "failure_reason": failure_reason,
                "summary": summary,
            }
        )

    runs.sort(key=lambda run: run.get("started_at") or run.get("created_at") or "", reverse=True)
    return runs[:limit]


async def build_quota_lease_summary(limit: int = 10) -> dict[str, Any]:
    policy = get_policy_snapshot()
    recent_leases = await list_execution_leases(limit=limit)
    providers = await build_provider_posture_records(limit=limit)
    recent_runs = [
        {
            "id": f"lease-{lease.get('id', 'unknown')}",
            "source_lane": lease.get("metadata", {}).get("meta_lane") or lease.get("surface", "unknown"),
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
            "policy_class": lease.get("metadata", {}).get("policy_class"),
            "approval_mode": lease.get("metadata", {}).get("approval_mode"),
            "command_decision_id": lease.get("metadata", {}).get("command_decision_id"),
            "supervisor_lane": None,
            "worker_lane": None,
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


def _next_weekly_occurrence(weekday: int, hour: int, minute: int) -> str:
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    days_ahead = (weekday - candidate.weekday()) % 7
    if days_ahead == 0 and candidate <= now:
        days_ahead = 7
    candidate += timedelta(days=days_ahead)
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
    from .governor_backbone import build_capacity_snapshot, evaluate_job_governance, get_governor_state

    governor_state = await get_governor_state()
    capacity_snapshot = await build_capacity_snapshot()
    global_paused = governor_state.get("global_mode") == "paused"
    paused_lanes = set(governor_state.get("paused_lanes", []))
    now = time.time()
    jobs: list[dict[str, Any]] = []
    recent_events: list[dict[str, Any]] = []
    for event_type in ("schedule_run", "schedule_failed", "schedule_skipped"):
        recent_events.extend(await query_events(event_type=event_type, limit=100))
    recent_events.sort(key=lambda item: item.get("timestamp_unix", 0), reverse=True)
    latest_events: dict[str, dict[str, Any]] = {}
    for event in recent_events:
        data = dict(event.get("data") or {})
        job_id = str(data.get("job_id") or "")
        if job_id and job_id not in latest_events:
            latest_events[job_id] = event

    for entry in schedule_status.get("schedules", []):
        next_run_in = int(entry.get("next_run_in", 0) or 0)
        job_id = f"agent-schedule:{entry.get('agent', 'unknown')}"
        control_scope = get_schedule_control_scope(job_id)
        event = latest_events.get(job_id)
        event_data = dict(event.get("data") or {}) if event else {}
        governance = await evaluate_job_governance(
            job_id=job_id,
            job_family="agent_schedule",
            control_scope=control_scope,
            owner_agent=str(entry.get("agent") or "system"),
            capacity_snapshot=capacity_snapshot,
        )
        paused = global_paused or (control_scope in paused_lanes if control_scope else False)
        current_state = "paused" if paused else ("deferred" if not governance["allowed"] else "scheduled")
        jobs.append(
            {
                "id": job_id,
                "job_family": "agent_schedule",
                "title": f"{entry.get('agent', 'unknown')} proactive loop",
                "cadence": entry.get("interval_human", "interval"),
                "trigger_mode": "interval",
                "last_run": event.get("timestamp") if event else _iso_from_unix(entry.get("last_run")),
                "next_run": _iso_from_unix(now + next_run_in),
                "current_state": "paused"
                if not entry.get("enabled", True) or not schedule_status.get("scheduler_running")
                else current_state,
                "last_outcome": str(event_data.get("outcome") or "scheduled"),
                "owner_agent": entry.get("agent"),
                "deep_link": f"/agents?agent={entry.get('agent', '')}",
                "control_scope": control_scope,
                "paused": paused,
                "can_run_now": bool(governance["allowed"]) and not paused,
                "can_override_now": not bool(governance["allowed"]) and not paused,
                "governor_reason": (
                    None if paused or governance["allowed"] else str(governance.get("reason") or "") or None
                ),
                "presence_state": str(governance.get("presence_state") or ""),
                "release_tier": str(governance.get("release_tier") or ""),
                "last_summary": str(event_data.get("summary") or ""),
                "last_error": str(event_data.get("error") or "") or None,
                "capacity_posture": str(governance.get("capacity_posture") or ""),
                "queue_posture": str(governance.get("queue_posture") or ""),
                "provider_posture": str(governance.get("provider_posture") or ""),
                "active_window_ids": list(governance.get("active_window_ids") or []),
                "priority_band": str(governance.get("priority_band") or ""),
                "deferred_by": str(governance.get("deferred_by") or "") or None,
                "next_action": str(governance.get("next_action") or "") or None,
                "last_actor": str(event_data.get("actor") or "") or None,
                "last_force_override": bool(event_data.get("force_override", False)),
                "last_task_id": str(event_data.get("task_id") or "") or None,
                "last_plan_id": str(event_data.get("plan_id") or "") or None,
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
            "id": "pipeline-cycle",
            "key": PIPELINE_KEY,
            "job_family": "pipeline",
            "title": "Pipeline cycle",
            "cadence": "every 2h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + PIPELINE_INTERVAL),
            "deep_link": "/workplanner",
        },
        {
            "id": "owner-model",
            "key": OWNER_MODEL_KEY,
            "job_family": "owner_model",
            "title": "Owner model rebuild",
            "cadence": "daily 4:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(OWNER_MODEL_HOUR, OWNER_MODEL_MINUTE),
            "deep_link": "/operator",
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
            "id": "weekly-dpo-training",
            "key": DPO_TRAINING_KEY,
            "job_family": "weekly_dpo_training",
            "title": "Weekly DPO training prep",
            "cadence": "weekly Sat 2:00",
            "trigger_mode": "weekly",
            "next_run": _next_weekly_occurrence(DPO_TRAINING_WEEKDAY, DPO_TRAINING_HOUR, DPO_TRAINING_MINUTE),
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
            "id": "nightly-optimization",
            "key": NIGHTLY_OPTIMIZATION_KEY,
            "job_family": "nightly_optimization",
            "title": "Nightly optimization",
            "cadence": "daily 22:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(NIGHTLY_OPTIMIZATION_HOUR, NIGHTLY_OPTIMIZATION_MINUTE),
            "deep_link": "/review",
        },
        {
            "id": "knowledge-refresh",
            "key": KNOWLEDGE_REFRESH_KEY,
            "job_family": "knowledge_refresh",
            "title": "Knowledge refresh",
            "cadence": "daily 0:00",
            "trigger_mode": "daily",
            "next_run": _next_daily_occurrence(KNOWLEDGE_REFRESH_HOUR, KNOWLEDGE_REFRESH_MINUTE),
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
        {
            "id": "creative-cascade",
            "key": CREATIVE_CASCADE_KEY,
            "job_family": "creative_cascade",
            "title": "Creative cascade",
            "cadence": "every 4h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + CREATIVE_CASCADE_INTERVAL),
            "deep_link": "/gallery",
            "owner_agent": "creative-agent",
        },
        {
            "id": "code-cascade",
            "key": CODE_CASCADE_KEY,
            "job_family": "code_cascade",
            "title": "Code cascade",
            "cadence": "every 6h",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + CODE_CASCADE_INTERVAL),
            "deep_link": "/review",
            "owner_agent": "coding-agent",
        },
        {
            "id": "research:scheduler",
            "key": None,
            "job_family": "research_jobs",
            "title": "Research scheduler scan",
            "cadence": "every 30s",
            "trigger_mode": "interval",
            "next_run": _iso_from_unix(now + SCHEDULER_INTERVAL),
            "deep_link": "/workplanner",
            "owner_agent": "research-agent",
        },
    ]

    for definition in builtin_definitions:
        control_scope = get_schedule_control_scope(definition["id"])
        event = latest_events.get(definition["id"])
        event_data = dict(event.get("data") or {}) if event else {}
        governance = await evaluate_job_governance(
            job_id=definition["id"],
            job_family=definition["job_family"],
            control_scope=control_scope,
            owner_agent=str(definition.get("owner_agent") or "system"),
            capacity_snapshot=capacity_snapshot,
        )
        paused = global_paused or (control_scope in paused_lanes if control_scope else False)
        jobs.append(
            {
                "id": definition["id"],
                "job_family": definition["job_family"],
                "title": definition["title"],
                "cadence": definition["cadence"],
                "trigger_mode": definition["trigger_mode"],
                "last_run": (
                    event.get("timestamp")
                    if event
                    else (
                        await _read_schedule_marker(definition["key"])
                        if definition.get("key")
                        else None
                    )
                ),
                "next_run": definition["next_run"],
                "current_state": "paused" if paused else ("deferred" if not governance["allowed"] else "scheduled"),
                "last_outcome": str(event_data.get("outcome") or "scheduled"),
                "owner_agent": str(definition.get("owner_agent") or "system"),
                "deep_link": definition["deep_link"],
                "control_scope": control_scope,
                "paused": paused,
                "can_run_now": bool(governance["allowed"]) and not paused,
                "can_override_now": not bool(governance["allowed"]) and not paused,
                "governor_reason": (
                    None if paused or governance["allowed"] else str(governance.get("reason") or "") or None
                ),
                "presence_state": str(governance.get("presence_state") or ""),
                "release_tier": str(governance.get("release_tier") or ""),
                "last_summary": str(event_data.get("summary") or ""),
                "last_error": str(event_data.get("error") or "") or None,
                "capacity_posture": str(governance.get("capacity_posture") or ""),
                "queue_posture": str(governance.get("queue_posture") or ""),
                "provider_posture": str(governance.get("provider_posture") or ""),
                "active_window_ids": list(governance.get("active_window_ids") or []),
                "priority_band": str(governance.get("priority_band") or ""),
                "deferred_by": str(governance.get("deferred_by") or "") or None,
                "next_action": str(governance.get("next_action") or "") or None,
                "last_actor": str(event_data.get("actor") or "") or None,
                "last_force_override": bool(event_data.get("force_override", False)),
                "last_task_id": str(event_data.get("task_id") or "") or None,
                "last_plan_id": str(event_data.get("plan_id") or "") or None,
            }
        )

    for job in await list_jobs():
        schedule_hours = int(job.get("schedule_hours", 0) or 0)
        last_run_raw = _safe_float(job.get("last_run"))
        next_run = _iso_from_unix(last_run_raw + (schedule_hours * 3600)) if schedule_hours > 0 and last_run_raw else None
        job_id = f"research:{job.get('id') or job.get('job_id')}"
        control_scope = get_schedule_control_scope(job_id)
        event = latest_events.get(job_id)
        event_data = dict(event.get("data") or {}) if event else {}
        governance = await evaluate_job_governance(
            job_id=job_id,
            job_family="research_job",
            control_scope=control_scope,
            owner_agent="research-agent",
            capacity_snapshot=capacity_snapshot,
        )
        paused = global_paused or (control_scope in paused_lanes if control_scope else False)
        current_state = str(job.get("status", "scheduled"))
        if paused and current_state != "running":
            current_state = "paused"
        elif not governance["allowed"] and current_state != "running":
            current_state = "deferred"
        jobs.append(
            {
                "id": job_id,
                "job_family": "research_job",
                "title": job.get("topic", "Research job"),
                "cadence": f"every {schedule_hours}h" if schedule_hours > 0 else "manual",
                "trigger_mode": "interval" if schedule_hours > 0 else "manual",
                "last_run": event.get("timestamp") if event else _iso_from_unix(job.get("last_run")),
                "next_run": next_run,
                "current_state": current_state,
                "last_outcome": str(event_data.get("outcome") or ("failed" if job.get("error") else job.get("status", "scheduled"))),
                "owner_agent": "research-agent",
                "deep_link": "/workplanner",
                "control_scope": control_scope,
                "paused": paused,
                "can_run_now": bool(governance["allowed"]) and not paused,
                "can_override_now": not bool(governance["allowed"]) and not paused,
                "governor_reason": (
                    None if paused or governance["allowed"] else str(governance.get("reason") or "") or None
                ),
                "presence_state": str(governance.get("presence_state") or ""),
                "release_tier": str(governance.get("release_tier") or ""),
                "last_summary": str(event_data.get("summary") or job.get("last_result") or ""),
                "last_error": str(event_data.get("error") or job.get("error") or "") or None,
                "capacity_posture": str(governance.get("capacity_posture") or ""),
                "queue_posture": str(governance.get("queue_posture") or ""),
                "provider_posture": str(governance.get("provider_posture") or ""),
                "active_window_ids": list(governance.get("active_window_ids") or []),
                "priority_band": str(governance.get("priority_band") or ""),
                "deferred_by": str(governance.get("deferred_by") or "") or None,
                "next_action": str(governance.get("next_action") or "") or None,
                "last_actor": str(event_data.get("actor") or "") or None,
                "last_force_override": bool(event_data.get("force_override", False)),
                "last_task_id": str(event_data.get("task_id") or "") or None,
                "last_plan_id": str(event_data.get("plan_id") or "") or None,
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
