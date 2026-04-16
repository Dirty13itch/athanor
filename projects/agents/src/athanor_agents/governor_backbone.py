from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, time as dt_time, timezone
from pathlib import Path
from typing import Any

from .model_governance import (
    get_backup_restore_readiness,
    get_capacity_governor_registry,
    get_data_lifecycle_registry,
    get_economic_governance_registry,
    get_operator_presence_model,
    get_operator_runbooks_registry,
    get_release_ritual_registry,
)
from .tool_permissions import build_tool_permission_snapshot as build_tool_permission_registry_snapshot

GOVERNOR_STATE_KEY = "athanor:governor:state"
DEFAULT_PRESENCE_HEARTBEAT_TTL_SECONDS = 180
TRUTH_INVENTORY_ENV_VAR = "ATHANOR_TRUTH_INVENTORY_DIR"

DEFAULT_GOVERNOR_STATE = {
    "global_mode": "active",
    "degraded_mode": "normal",
    "paused_lanes": [],
    "reason": "",
    "updated_at": None,
    "updated_by": "system",
    "operator_presence": None,
    "presence_mode": "auto",
    "presence_reason": "",
    "presence_updated_at": None,
    "presence_updated_by": "system",
    "presence_signal_state": None,
    "presence_signal_source": "",
    "presence_signal_reason": "",
    "presence_signal_updated_at": None,
    "presence_signal_updated_by": "system",
    "release_tier": None,
    "tier_reason": "",
    "tier_updated_at": None,
    "tier_updated_by": "system",
}

LANE_DEFINITIONS = [
    {
        "id": "task_worker",
        "label": "Task worker",
        "description": "Durable task execution loop for queued background work.",
    },
    {
        "id": "scheduler",
        "label": "Scheduler",
        "description": "Recurring automation and proactive agent scheduling.",
    },
    {
        "id": "research_jobs",
        "label": "Research jobs",
        "description": "Autonomous research-job triggering inside the scheduler.",
    },
    {
        "id": "benchmark_cycle",
        "label": "Benchmark cycle",
        "description": "Model-proving and self-improvement benchmark cadence.",
    },
    {
        "id": "alerts",
        "label": "Alerts",
        "description": "Prometheus polling and operator-facing alert refresh.",
    },
    {
        "id": "maintenance",
        "label": "Maintenance",
        "description": "Cache cleanup and similar low-risk maintenance loops.",
    },
]


PRESENCE_DEFERRED_JOB_FAMILIES: dict[str, set[str]] = {
    "away": {"benchmarks"},
    "phone_only": {"benchmarks"},
    "asleep": {"agent_schedule", "research_jobs", "research_job"},
}

RELEASE_TIER_ALLOWLIST: dict[str, set[str]] = {
    "offline_eval": {"alerts", "benchmarks", "improvement_cycle", "cache_cleanup"},
    "shadow": {
        "alerts",
        "benchmarks",
        "cache_cleanup",
        "consolidation",
        "daily_digest",
        "improvement_cycle",
        "pattern_detection",
        "workplan",
        "workplan_refill",
    },
    "sandbox": {
        "alerts",
        "benchmarks",
        "cache_cleanup",
        "consolidation",
        "daily_digest",
        "improvement_cycle",
        "pattern_detection",
        "research_job",
        "research_jobs",
        "workplan",
        "workplan_refill",
    },
}

JOB_FAMILY_GOVERNANCE_PROFILES: dict[str, dict[str, Any]] = {
    "daily_digest": {
        "priority_band": "governor_critical",
        "protected_tags": ["daily briefing", "notifications"],
        "defer_when_constrained": False,
        "defer_when_degraded": False,
        "respect_active_windows": False,
    },
    "workplan": {
        "priority_band": "governor_critical",
        "protected_tags": ["daily briefing", "workplan refresh"],
        "defer_when_constrained": False,
        "defer_when_degraded": False,
        "respect_active_windows": False,
    },
    "workplan_refill": {
        "priority_band": "governor_critical",
        "protected_tags": ["workplan refresh"],
        "defer_when_constrained": False,
        "defer_when_degraded": False,
        "respect_active_windows": False,
    },
    "alerts": {
        "priority_band": "governor_critical",
        "protected_tags": ["notifications"],
        "defer_when_constrained": False,
        "defer_when_degraded": False,
        "respect_active_windows": False,
    },
    "consolidation": {
        "priority_band": "scheduled_low_risk",
        "protected_tags": ["consolidation"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "pattern_detection": {
        "priority_band": "scheduled_low_risk",
        "protected_tags": ["benchmarking"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "research_jobs": {
        "priority_band": "scheduled_low_risk",
        "protected_tags": ["research"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "research_job": {
        "priority_band": "scheduled_low_risk",
        "protected_tags": ["research"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "agent_schedule": {
        "priority_band": "scheduled_low_risk",
        "protected_tags": ["research"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "benchmarks": {
        "priority_band": "benchmark",
        "protected_tags": ["benchmarking"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "improvement_cycle": {
        "priority_band": "benchmark",
        "protected_tags": ["benchmarking"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
    "cache_cleanup": {
        "priority_band": "maintenance",
        "protected_tags": ["indexing", "maintenance"],
        "defer_when_constrained": True,
        "defer_when_degraded": True,
        "respect_active_windows": True,
    },
}


async def _get_redis():
    from .workspace import get_redis

    return await get_redis()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _candidate_truth_inventory_dirs() -> list[Path]:
    module_path = Path(__file__).resolve()
    candidates: list[Path] = []
    env_path = str(os.getenv(TRUTH_INVENTORY_ENV_VAR) or "").strip()
    if env_path:
        candidates.append(Path(env_path))
    for parent in [module_path.parent, *module_path.parents]:
        candidates.append(parent / "reports" / "truth-inventory")
    candidates.extend(
        [
            Path("/workspace/reports/truth-inventory"),
            Path("/opt/athanor/reports/truth-inventory"),
            Path("/app/reports/truth-inventory"),
        ]
    )
    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_key = str(candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        unique_candidates.append(candidate)
    return unique_candidates


def _truth_inventory_dir() -> Path:
    for candidate in _candidate_truth_inventory_dirs():
        if candidate.exists():
            return candidate
    return _candidate_truth_inventory_dirs()[0]


def _load_truth_inventory_payload(name: str) -> dict[str, Any]:
    path = _truth_inventory_dir() / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_local_compute_truth() -> dict[str, Any]:
    capacity_payload = _load_truth_inventory_payload("capacity-telemetry.json")
    quota_payload = _load_truth_inventory_payload("quota-truth.json")
    summary = dict(capacity_payload.get("capacity_summary") or {})

    records = quota_payload.get("records") or []
    local_compute_record = next(
        (
            dict(item)
            for item in records
            if isinstance(item, dict)
            and (
                str(item.get("usage_mode") or "").strip() == "local_compute"
                or str(item.get("provider_id") or "").strip() == "athanor_local"
            )
        ),
        {},
    )
    breakdown = dict(local_compute_record.get("capacity_breakdown") or {})
    slot_samples = [
        dict(item)
        for item in breakdown.get("scheduler_slot_samples", [])
        if isinstance(item, dict)
    ]
    open_harvest_slots = [
        {
            "id": str(item.get("scheduler_slot_id") or "").strip(),
            "zone_id": str(item.get("scheduler_zone_id") or "").strip() or None,
            "harvest_intent": str(item.get("harvest_intent") or "").strip() or None,
            "harvestable_gpu_count": int(item.get("harvestable_gpu_count") or 0),
            "node_ids": [str(node_id) for node_id in item.get("node_ids", []) if str(node_id).strip()],
        }
        for item in slot_samples
        if bool(item.get("idle_window_open")) and str(item.get("scheduler_slot_id") or "").strip()
    ]
    return {
        "sample_posture": str(summary.get("sample_posture") or breakdown.get("sample_posture") or "").strip() or None,
        "scheduler_slot_count": int(summary.get("scheduler_slot_count") or breakdown.get("scheduler_slot_count") or 0),
        "harvestable_scheduler_slot_count": int(
            summary.get("harvestable_scheduler_slot_count")
            or breakdown.get("harvestable_scheduler_slot_count")
            or 0
        ),
        "idle_harvest_slots_open": bool(any(bool(item.get("idle_window_open")) for item in slot_samples)),
        "open_harvest_slots": open_harvest_slots,
        "scheduler_queue_depth": int(summary.get("scheduler_queue_depth") or breakdown.get("scheduler_queue_depth") or 0),
        "scheduler_source": str(summary.get("scheduler_source") or "").strip() or None,
        "scheduler_observed_at": (
            str(summary.get("scheduler_observed_at") or "").strip()
            or str(breakdown.get("scheduler_observed_at") or "").strip()
            or None
        ),
    }


def _quota_summary_from_truth_inventory(limit: int = 5) -> dict[str, Any]:
    quota_payload = _load_truth_inventory_payload("quota-truth.json")
    provider_summaries: list[dict[str, Any]] = []
    for item in quota_payload.get("records") or []:
        if not isinstance(item, dict):
            continue
        provider_id = str(item.get("provider_id") or "").strip()
        if not provider_id:
            continue
        remaining_units = item.get("remaining_units")
        budget_remaining_usd = item.get("budget_remaining_usd")
        degraded_reason = str(item.get("degraded_reason") or "").strip()
        availability = "available"
        if degraded_reason:
            availability = "degraded"
        else:
            try:
                if remaining_units is not None and int(remaining_units) <= 0:
                    availability = "degraded"
            except (TypeError, ValueError):
                pass
            try:
                if budget_remaining_usd is not None and float(budget_remaining_usd) <= 0:
                    availability = "degraded"
            except (TypeError, ValueError):
                pass
        provider_summaries.append(
            {
                "provider": provider_id,
                "availability": availability,
                "provider_state": availability,
                "limit": 0,
                "remaining": int(remaining_units or 0) if remaining_units is not None else 0,
                "state_reasons": [degraded_reason] if degraded_reason else [],
                "reserve_state": str(item.get("harvest_priority") or item.get("usage_mode") or "standard"),
                "last_observed_at": item.get("last_observed_at"),
                "recent_execution_state": str(item.get("capture_status") or item.get("confidence") or "observed"),
                "next_action": "refresh_provider_truth",
            }
        )
    provider_summaries.sort(key=lambda item: str(item.get("provider") or ""))
    return {
        "policy_source": "truth_inventory_fallback",
        "provider_summaries": provider_summaries[:limit],
        "recent_leases": [],
        "count": len(provider_summaries),
    }


async def _build_quota_summary_for_capacity(limit: int = 5, timeout_seconds: float = 1.5) -> dict[str, Any]:
    from .backbone import build_quota_lease_summary

    try:
        return await asyncio.wait_for(build_quota_lease_summary(limit=limit), timeout=timeout_seconds)
    except Exception:
        return _quota_summary_from_truth_inventory(limit=limit)


def _presence_registry() -> dict[str, Any]:
    return get_operator_presence_model()


def _presence_profiles() -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("id")): dict(entry)
        for entry in _presence_registry().get("states", [])
        if entry.get("id")
    }


def _default_presence_state() -> str:
    registry = _presence_registry()
    default_state = str(registry.get("default_state") or "").strip()
    if default_state:
        return default_state
    profiles = _presence_profiles()
    return next(iter(profiles), "at_desk")


def _presence_auto_mode() -> dict[str, Any]:
    registry = _presence_registry()
    auto_mode = registry.get("auto_mode")
    return dict(auto_mode) if isinstance(auto_mode, dict) else {}


def _presence_heartbeat_ttl_seconds() -> int:
    auto_mode = _presence_auto_mode()
    raw = auto_mode.get("heartbeat_ttl_seconds", DEFAULT_PRESENCE_HEARTBEAT_TTL_SECONDS)
    try:
        ttl = int(raw)
    except (TypeError, ValueError):
        ttl = DEFAULT_PRESENCE_HEARTBEAT_TTL_SECONDS
    return max(ttl, 15)


def _presence_stale_state() -> str:
    auto_mode = _presence_auto_mode()
    raw = str(auto_mode.get("stale_state") or "away").strip()
    return raw or "away"


def _normalize_protected_tags(values: list[Any]) -> set[str]:
    return {str(item).strip().lower() for item in values if str(item).strip()}


def _job_governance_profile(job_family: str, owner_agent: str = "system") -> dict[str, Any]:
    profile = dict(
        JOB_FAMILY_GOVERNANCE_PROFILES.get(
            job_family,
            {
                "priority_band": "scheduled_low_risk",
                "protected_tags": [],
                "defer_when_constrained": True,
                "defer_when_degraded": True,
                "respect_active_windows": True,
            },
        )
    )
    normalized_owner = str(owner_agent or "").strip().lower()
    if job_family == "agent_schedule" and normalized_owner in {"general-assistant", "coding-agent"}:
        profile["protected_tags"] = sorted(
            _normalize_protected_tags(list(profile.get("protected_tags", [])) + ["notifications"])
        )
    return profile


def _window_conflicts_for_job(
    active_time_windows: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    if not active_time_windows or not bool(profile.get("respect_active_windows")):
        return []
    protected_tags = _normalize_protected_tags(list(profile.get("protected_tags", [])))
    if not protected_tags:
        return [dict(window) for window in active_time_windows]
    conflicts: list[dict[str, Any]] = []
    for window in active_time_windows:
        window_tags = _normalize_protected_tags(list(window.get("protects", [])))
        if protected_tags.isdisjoint(window_tags):
            conflicts.append(dict(window))
    return conflicts


def _presence_allowed_heartbeat_states() -> set[str]:
    auto_mode = _presence_auto_mode()
    values = auto_mode.get("allowed_heartbeat_states", ["at_desk", "away"])
    allowed = {str(item).strip() for item in values if str(item).strip()}
    if allowed:
        return allowed
    return {"at_desk", "away"}


def _presence_profile(state_id: str | None) -> dict[str, Any]:
    profiles = _presence_profiles()
    selected = str(state_id or _default_presence_state())
    return dict(
        profiles.get(
            selected,
            profiles.get(
                _default_presence_state(),
                {
                    "id": selected,
                    "label": selected.replace("_", " ").title(),
                    "automation_posture": "normal bounded autonomy",
                    "notification_posture": "full detail",
                    "approval_posture": "low friction",
                },
            ),
        )
    )


def _humanize_registry_id(raw: str) -> str:
    return raw.replace("_", " ").replace("-", " ").strip().title()


def _autonomy_activation_summary() -> dict[str, Any]:
    from .model_governance import (
        get_current_autonomy_phase,
        get_next_autonomy_phase,
        get_unmet_autonomy_prerequisites,
    )

    activation, current_phase = get_current_autonomy_phase()
    current_phase_id = str(activation.get("current_phase_id") or "")
    next_phase = get_next_autonomy_phase(activation, phase_id=current_phase_id)
    next_phase_id = str(next_phase.get("id") or "").strip() or None
    next_phase_blockers = (
        get_unmet_autonomy_prerequisites(activation, phase_id=next_phase_id)
        if next_phase_id
        else []
    )
    return {
        "status": str(activation.get("status") or "configured"),
        "activation_state": str(activation.get("activation_state") or "unknown"),
        "current_phase_id": current_phase_id or None,
        "current_phase_status": str(current_phase.get("status") or "unknown"),
        "current_phase_scope": str(current_phase.get("scope") or "") or None,
        "next_phase_id": next_phase_id,
        "next_phase_status": str(next_phase.get("status") or "complete") if next_phase_id else None,
        "next_phase_scope": str(next_phase.get("scope") or "") or None,
        "next_phase_blocker_count": len(next_phase_blockers),
        "next_phase_blocker_ids": [
            str(item.get("id") or "").strip()
            for item in next_phase_blockers
            if str(item.get("id") or "").strip()
        ],
        "broad_autonomy_enabled": bool(activation.get("broad_autonomy_enabled")),
        "runtime_mutations_approval_gated": bool(
            activation.get("runtime_mutations_approval_gated", True)
        ),
        "enabled_agents": list(current_phase.get("enabled_agents", [])),
        "allowed_workload_classes": list(current_phase.get("allowed_workload_classes", [])),
        "blocked_workload_classes": list(current_phase.get("blocked_workload_classes", [])),
    }


def _release_registry() -> dict[str, Any]:
    return get_release_ritual_registry()


def _release_tiers() -> list[str]:
    tiers = [str(item) for item in _release_registry().get("tiers", []) if str(item).strip()]
    if tiers:
        return tiers
    return ["offline_eval", "shadow", "sandbox", "canary", "production"]


def _default_release_tier() -> str:
    tiers = _release_tiers()
    return "production" if "production" in tiers else tiers[-1]


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_governor_state(state: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(DEFAULT_GOVERNOR_STATE)
    normalized.update(state)
    normalized["paused_lanes"] = sorted({str(item) for item in normalized.get("paused_lanes", [])})
    normalized["operator_presence"] = str(
        normalized.get("operator_presence") or _default_presence_state()
    )
    raw_mode = str(state.get("presence_mode") or "").strip()
    if raw_mode in {"auto", "manual"}:
        normalized["presence_mode"] = raw_mode
    elif state:
        normalized["presence_mode"] = (
            "manual"
            if str(state.get("presence_updated_by") or state.get("updated_by") or "system") != "system"
            else "auto"
        )
    else:
        normalized["presence_mode"] = "auto"
    normalized["release_tier"] = str(normalized.get("release_tier") or _default_release_tier())
    normalized["presence_updated_by"] = str(
        normalized.get("presence_updated_by") or normalized.get("updated_by") or "system"
    )
    signal_state = str(normalized.get("presence_signal_state") or "").strip()
    normalized["presence_signal_state"] = (
        signal_state if signal_state in set(_presence_profiles()) else None
    )
    normalized["presence_signal_source"] = str(normalized.get("presence_signal_source") or "")
    normalized["presence_signal_reason"] = str(normalized.get("presence_signal_reason") or "")
    normalized["presence_signal_updated_by"] = str(
        normalized.get("presence_signal_updated_by") or normalized.get("updated_by") or "system"
    )
    normalized["tier_updated_by"] = str(
        normalized.get("tier_updated_by") or normalized.get("updated_by") or "system"
    )
    return normalized


async def get_governor_state() -> dict[str, Any]:
    redis = await _get_redis()
    raw = await redis.get(GOVERNOR_STATE_KEY)
    if not raw:
        return _normalize_governor_state({})
    try:
        payload = json.loads(raw)
        return _normalize_governor_state(payload if isinstance(payload, dict) else {})
    except (TypeError, ValueError, json.JSONDecodeError):
        return _normalize_governor_state({})


async def _save_governor_state(state: dict[str, Any]) -> dict[str, Any]:
    redis = await _get_redis()
    normalized = _normalize_governor_state(state)
    normalized["updated_at"] = normalized.get("updated_at") or _now_iso()
    await redis.set(GOVERNOR_STATE_KEY, json.dumps(normalized))
    return normalized


def _build_presence_snapshot(state: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    current_time = now or _now()
    manual_state = str(state.get("operator_presence") or _default_presence_state())
    manual_profile = _presence_profile(manual_state)
    mode = str(state.get("presence_mode") or "auto")
    signal_state = str(state.get("presence_signal_state") or "").strip() or None
    signal_source = str(state.get("presence_signal_source") or "").strip() or None
    signal_reason = str(state.get("presence_signal_reason") or "").strip() or None
    signal_updated_at = state.get("presence_signal_updated_at")
    signal_updated_by = str(state.get("presence_signal_updated_by") or state.get("updated_by") or "system")
    signal_age_seconds: float | None = None
    signal_fresh = False

    parsed_signal_time = _parse_iso_datetime(signal_updated_at)
    if parsed_signal_time is not None:
        signal_age_seconds = max((current_time - parsed_signal_time).total_seconds(), 0.0)
        signal_fresh = signal_age_seconds <= _presence_heartbeat_ttl_seconds()

    if mode == "manual":
        effective_state = manual_state
        effective_profile = manual_profile
        effective_reason = str(state.get("presence_reason") or "Manual operator presence override is active.")
        updated_at = state.get("presence_updated_at") or state.get("updated_at")
        updated_by = str(state.get("presence_updated_by") or state.get("updated_by") or "system")
    else:
        if signal_state and signal_fresh:
            effective_state = signal_state
            effective_profile = _presence_profile(signal_state)
            effective_reason = signal_reason or "Recent dashboard heartbeat is driving presence posture."
            updated_at = signal_updated_at
            updated_by = signal_updated_by
        else:
            effective_state = _presence_stale_state()
            effective_profile = _presence_profile(effective_state)
            effective_reason = "No recent operator heartbeat; governor is using stale-signal fallback posture."
            updated_at = signal_updated_at or state.get("updated_at")
            updated_by = signal_updated_by if signal_updated_at else str(state.get("updated_by") or "system")

    return {
        "mode": mode,
        "state": str(effective_profile.get("id") or effective_state),
        "label": str(effective_profile.get("label") or _humanize_registry_id(effective_state)),
        "automation_posture": str(
            effective_profile.get("automation_posture") or "normal bounded autonomy"
        ),
        "notification_posture": str(
            effective_profile.get("notification_posture") or "full detail"
        ),
        "approval_posture": str(effective_profile.get("approval_posture") or "low friction"),
        "updated_at": updated_at,
        "updated_by": updated_by,
        "configured_state": manual_state,
        "configured_label": str(
            manual_profile.get("label") or _humanize_registry_id(manual_state)
        ),
        "signal_state": signal_state,
        "signal_source": signal_source,
        "signal_updated_at": signal_updated_at,
        "signal_updated_by": signal_updated_by,
        "signal_fresh": signal_fresh,
        "signal_age_seconds": round(signal_age_seconds, 1) if signal_age_seconds is not None else None,
        "effective_reason": effective_reason,
    }


async def pause_automation(scope: str = "global", reason: str = "", actor: str = "operator") -> dict[str, Any]:
    state = await get_governor_state()
    if scope == "global":
        state["global_mode"] = "paused"
    else:
        paused = set(state.get("paused_lanes", []))
        paused.add(scope)
        state["paused_lanes"] = sorted(paused)
    state["reason"] = reason
    state["updated_by"] = actor
    state["updated_at"] = _now_iso()
    return await _save_governor_state(state)


async def resume_automation(scope: str = "global", actor: str = "operator") -> dict[str, Any]:
    state = await get_governor_state()
    if scope == "global":
        state["global_mode"] = "active"
        state["reason"] = ""
    else:
        paused = set(state.get("paused_lanes", []))
        paused.discard(scope)
        state["paused_lanes"] = sorted(paused)
    state["updated_by"] = actor
    state["updated_at"] = _now_iso()
    return await _save_governor_state(state)


async def set_operator_presence(
    state_id: str,
    *,
    reason: str = "",
    actor: str = "operator",
    mode: str = "manual",
) -> dict[str, Any]:
    state = await get_governor_state()
    now_iso = _now_iso()
    normalized_mode = str(mode or "manual").strip().lower()
    if normalized_mode not in {"auto", "manual"}:
        raise ValueError("Invalid operator presence mode.")

    if normalized_mode == "manual":
        profile = _presence_profile(state_id)
        normalized_state_id = str(profile.get("id") or "").strip()
        if not normalized_state_id:
            raise ValueError("Invalid operator presence state.")
        state["operator_presence"] = normalized_state_id
        state["presence_reason"] = reason
        state["presence_mode"] = "manual"
        state["presence_updated_at"] = now_iso
        state["presence_updated_by"] = actor
    else:
        state["presence_mode"] = "auto"
        state["presence_reason"] = reason or "Automatic dashboard heartbeat governs presence posture."
        state["presence_updated_at"] = now_iso
        state["presence_updated_by"] = actor
        requested_state = str(state_id or "").strip()
        if requested_state:
            profile = _presence_profile(requested_state)
            normalized_state_id = str(profile.get("id") or "").strip()
            if not normalized_state_id:
                raise ValueError("Invalid operator presence state.")
            state["presence_signal_state"] = normalized_state_id
            state["presence_signal_source"] = str(
                _presence_auto_mode().get("signal_source") or "dashboard_heartbeat"
            )
            state["presence_signal_reason"] = reason or "Automatic presence resumed from operator control."
            state["presence_signal_updated_at"] = now_iso
            state["presence_signal_updated_by"] = actor

    state["updated_by"] = actor
    state["updated_at"] = now_iso
    return await _save_governor_state(state)


async def record_presence_heartbeat(
    state_id: str,
    *,
    source: str = "dashboard_heartbeat",
    reason: str = "",
    actor: str = "dashboard-heartbeat",
) -> dict[str, Any]:
    profile = _presence_profile(state_id)
    normalized_state_id = str(profile.get("id") or "").strip()
    if not normalized_state_id:
        raise ValueError("Invalid operator heartbeat state.")
    if normalized_state_id not in _presence_allowed_heartbeat_states():
        raise ValueError("Heartbeat state is not allowed for automatic presence.")

    state = await get_governor_state()
    now_iso = _now_iso()
    state["presence_signal_state"] = normalized_state_id
    state["presence_signal_source"] = str(source or "dashboard_heartbeat")
    state["presence_signal_reason"] = reason or "Dashboard heartbeat updated operator presence."
    state["presence_signal_updated_at"] = now_iso
    state["presence_signal_updated_by"] = actor
    if str(state.get("presence_mode") or "auto") != "manual":
        state["presence_mode"] = "auto"
        state["presence_reason"] = "Automatic dashboard heartbeat governs presence posture."
    state["updated_by"] = actor
    state["updated_at"] = now_iso
    return await _save_governor_state(state)


async def set_release_tier(
    tier: str,
    *,
    reason: str = "",
    actor: str = "operator",
) -> dict[str, Any]:
    normalized_tier = str(tier or "").strip()
    if normalized_tier not in set(_release_tiers()):
        raise ValueError(f"Unknown release tier: {tier}")

    state = await get_governor_state()
    state["release_tier"] = normalized_tier
    state["tier_reason"] = reason
    state["tier_updated_at"] = _now_iso()
    state["tier_updated_by"] = actor
    state["updated_by"] = actor
    state["updated_at"] = _now_iso()
    return await _save_governor_state(state)


async def is_automation_paused(scope: str = "global") -> bool:
    state = await get_governor_state()
    if state.get("global_mode") == "paused":
        return True
    return scope in set(state.get("paused_lanes", []))


def _queue_posture(task_stats: dict[str, Any]) -> str:
    running = int(task_stats.get("currently_running", 0) or 0)
    max_concurrent = max(int(task_stats.get("max_concurrent", 0) or 0), 1)
    pending = int(dict(task_stats.get("by_status") or {}).get("pending", 0) or 0)
    failed = int(dict(task_stats.get("by_status") or {}).get("failed", 0) or 0)
    if failed > 0:
        return "degraded"
    if running >= max_concurrent or pending >= max_concurrent * 3:
        return "constrained"
    return "healthy"


def _provider_posture(provider_summaries: list[dict[str, Any]]) -> str:
    constrained = sum(1 for item in provider_summaries if item.get("availability") == "constrained")
    exhausted = sum(
        1
        for item in provider_summaries
        if int(item.get("limit", 0) or 0) > 0 and int(item.get("remaining", 0) or 0) <= 0
    )
    if exhausted > 0:
        return "degraded"
    if constrained > 0:
        return "constrained"
    return "healthy"


def _node_posture(nodes: list[dict[str, Any]]) -> str:
    if any(not node.get("alive") or node.get("stale") for node in nodes):
        return "degraded"
    if any(node.get("max_gpu_util_pct", 0) >= 85 for node in nodes):
        return "constrained"
    return "healthy"


def _parse_local_window(raw: str) -> tuple[dt_time, dt_time] | None:
    try:
        window_part = raw.split()[0]
        start_raw, end_raw = window_part.split("-", 1)
        start_hour, start_minute = (int(item) for item in start_raw.split(":"))
        end_hour, end_minute = (int(item) for item in end_raw.split(":"))
        return dt_time(hour=start_hour, minute=start_minute), dt_time(hour=end_hour, minute=end_minute)
    except (TypeError, ValueError):
        return None


def get_active_time_windows(now: datetime | None = None) -> list[dict[str, Any]]:
    registry = get_capacity_governor_registry()
    current = now or datetime.now()
    current_local_time = current.time()
    active: list[dict[str, Any]] = []
    for entry in registry.get("time_windows", []):
        parsed = _parse_local_window(str(entry.get("window", "")))
        if not parsed:
            continue
        start_time, end_time = parsed
        in_window = start_time <= current_local_time <= end_time
        if in_window:
            active.append(
                {
                    "id": str(entry.get("id") or "window"),
                    "window": str(entry.get("window") or ""),
                    "protects": list(entry.get("protects", [])),
                    "status": str(entry.get("status", "configured")),
                }
            )
    return active


async def evaluate_job_governance(
    *,
    job_id: str,
    job_family: str,
    control_scope: str | None,
    owner_agent: str = "system",
    capacity_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = await get_governor_state()
    presence = _build_presence_snapshot(state)
    presence_state = str(presence.get("state") or _default_presence_state())
    release_tier = str(state.get("release_tier") or _default_release_tier())
    profile = _job_governance_profile(job_family, owner_agent=owner_agent)

    queue_posture = "unknown"
    provider_posture = "unknown"
    capacity_posture = "unknown"
    active_time_windows: list[dict[str, Any]] = []
    if capacity_snapshot is not None:
        queue_posture = str(dict(capacity_snapshot.get("queue") or {}).get("posture") or "unknown")
        provider_posture = str(
            dict(capacity_snapshot.get("provider_reserve") or {}).get("posture") or "unknown"
        )
        capacity_posture = str(capacity_snapshot.get("posture") or "unknown")
        active_time_windows = list(capacity_snapshot.get("active_time_windows") or [])

    def _decision(
        *,
        allowed: bool,
        status: str,
        reason: str,
        deferred_by: str | None = None,
        next_action: str | None = None,
    ) -> dict[str, Any]:
        return {
            "allowed": allowed,
            "status": status,
            "reason": reason,
            "control_scope": control_scope,
            "presence_state": presence_state,
            "presence_mode": str(presence.get("mode") or "auto"),
            "release_tier": release_tier,
            "capacity_posture": capacity_posture,
            "queue_posture": queue_posture,
            "provider_posture": provider_posture,
            "active_window_ids": [str(item.get("id") or "") for item in active_time_windows],
            "priority_band": str(profile.get("priority_band") or "scheduled_low_risk"),
            "deferred_by": deferred_by,
            "next_action": next_action,
        }

    if state.get("global_mode") == "paused":
        return _decision(
            allowed=False,
            status="paused",
            reason=state.get("reason") or "Global automation pause is active.",
            deferred_by="global_pause",
            next_action="resume_global_automation",
        )

    paused_lanes = set(state.get("paused_lanes", []))
    if control_scope and control_scope in paused_lanes:
        return _decision(
            allowed=False,
            status="paused",
            reason=f"{control_scope.replace('_', ' ')} lane is paused.",
            deferred_by="lane_pause",
            next_action=f"resume_{control_scope}",
        )

    deferred_families = PRESENCE_DEFERRED_JOB_FAMILIES.get(presence_state, set())
    if job_family in deferred_families:
        profile = _presence_profile(presence_state)
        return _decision(
            allowed=False,
            status="deferred",
            reason=(
                f"Deferred while operator is {presence_state.replace('_', ' ')} "
                f"({profile.get('automation_posture', 'conservative')})."
            ),
            deferred_by="presence",
            next_action="wait_for_presence_change",
        )

    allowlist = RELEASE_TIER_ALLOWLIST.get(release_tier)
    if allowlist is not None and job_family not in allowlist:
        return _decision(
            allowed=False,
            status="deferred",
            reason=(
                f"Deferred outside the {release_tier.replace('_', ' ')} release tier; "
                f"{job_family.replace('_', ' ')} is not in the active ladder."
            ),
            deferred_by="release_tier",
            next_action="advance_release_tier_or_override",
        )

    conflicting_windows = _window_conflicts_for_job(active_time_windows, profile)
    if conflicting_windows:
        window_labels = ", ".join(str(item.get("id") or "window").replace("_", " ") for item in conflicting_windows)
        return _decision(
            allowed=False,
            status="deferred",
            reason=(
                f"Deferred during active protected window(s): {window_labels}. "
                f"{job_family.replace('_', ' ')} is outside the current protected work window."
            ),
            deferred_by="time_window",
            next_action="wait_for_window_clear",
        )

    if capacity_posture == "degraded" and bool(profile.get("defer_when_degraded")):
        return _decision(
            allowed=False,
            status="deferred",
            reason=(
                f"Deferred because capacity is degraded "
                f"(queue {queue_posture}, provider reserve {provider_posture})."
            ),
            deferred_by="capacity",
            next_action="reduce_background_load",
        )

    if capacity_posture == "constrained" and bool(profile.get("defer_when_constrained")):
        return _decision(
            allowed=False,
            status="deferred",
            reason=(
                f"Deferred because capacity is constrained "
                f"(queue {queue_posture}, provider reserve {provider_posture})."
            ),
            deferred_by="capacity",
            next_action="wait_for_capacity_or_override",
        )

    return _decision(
        allowed=True,
        status="active",
        reason=f"{job_id} is permitted for {owner_agent} under current governor posture.",
        next_action="run",
    )


async def build_capacity_snapshot() -> dict[str, Any]:
    from .scheduler import get_schedule_status
    from .tasks import get_task_stats
    from .workspace import get_cluster_capacity, get_stats as get_workspace_stats

    task_stats, schedule_status, workspace_stats, cluster_capacity, quota_summary = await asyncio.gather(
        get_task_stats(),
        get_schedule_status(),
        get_workspace_stats(),
        get_cluster_capacity(),
        _build_quota_summary_for_capacity(limit=5),
    )
    local_compute_truth = _load_local_compute_truth()

    nodes: list[dict[str, Any]] = []
    stale_count = 0
    for node_id, payload in cluster_capacity.items():
        gpus = list(payload.get("gpus") or [])
        max_gpu_util = max((float(gpu.get("util_pct", 0) or 0) for gpu in gpus), default=0.0)
        healthy_models = sum(1 for item in dict(payload.get("models") or {}).values() if item.get("healthy"))
        total_models = len(dict(payload.get("models") or {}))
        stale = bool(payload.get("stale"))
        if stale or not payload.get("alive"):
            stale_count += 1
        nodes.append(
            {
                "id": node_id,
                "alive": bool(payload.get("alive")),
                "stale": stale,
                "max_gpu_util_pct": round(max_gpu_util, 1),
                "healthy_models": healthy_models,
                "total_models": total_models,
                "load_1m": float(dict(payload.get("system") or {}).get("load_1m", 0) or 0),
                "ram_available_mb": int(dict(payload.get("system") or {}).get("ram_available_mb", 0) or 0),
            }
        )

    queue_posture = _queue_posture(task_stats)
    provider_posture = _provider_posture(list(quota_summary.get("provider_summaries") or []))
    node_posture = _node_posture(nodes)
    posture = "healthy"
    if "degraded" in {queue_posture, provider_posture, node_posture}:
        posture = "degraded"
    elif "constrained" in {queue_posture, provider_posture, node_posture}:
        posture = "constrained"

    recommendations: list[str] = []
    if stale_count > 0:
        recommendations.append(f"{stale_count} node heartbeat(s) are stale or missing.")
    if queue_posture != "healthy":
        recommendations.append("Queue pressure is elevated; reduce autonomous batch work.")
    if provider_posture != "healthy":
        recommendations.append("Provider reserve pressure is elevated; favor local execution.")
    if not recommendations:
        recommendations.append("Capacity posture is healthy across queue, nodes, and provider reserves.")
    if local_compute_truth["idle_harvest_slots_open"]:
        open_slot_ids = ", ".join(
            item["id"] for item in local_compute_truth["open_harvest_slots"] if item.get("id")
        )
        recommendations.append(
            f"{local_compute_truth['harvestable_scheduler_slot_count']} harvestable scheduler slot(s) are open"
            + (f": {open_slot_ids}" if open_slot_ids else ".")
        )

    workspace_capacity = int(workspace_stats.get("capacity", 0) or 0)
    workspace_utilization = float(workspace_stats.get("utilization", 0.0) or 0.0)
    if workspace_capacity <= 0 and local_compute_truth["scheduler_slot_count"] > 0:
        workspace_capacity = int(local_compute_truth["scheduler_slot_count"])
        open_slots = len(local_compute_truth["open_harvest_slots"])
        workspace_utilization = round(max(workspace_capacity - open_slots, 0) / workspace_capacity, 2)

    return {
        "generated_at": _now_iso(),
        "posture": posture,
        "queue": {
            "posture": queue_posture,
            "pending": int(dict(task_stats.get("by_status") or {}).get("pending", 0) or 0),
            "running": int(task_stats.get("currently_running", 0) or 0),
            "max_concurrent": int(task_stats.get("max_concurrent", 0) or 0),
            "failed": int(dict(task_stats.get("by_status") or {}).get("failed", 0) or 0),
        },
        "workspace": {
            "broadcast_items": int(workspace_stats.get("broadcast_items", 0) or 0),
            "capacity": workspace_capacity,
            "utilization": workspace_utilization,
        },
        "scheduler": {
            "running": bool(schedule_status.get("scheduler_running")),
            "enabled_count": sum(1 for item in schedule_status.get("schedules", []) if item.get("enabled")),
        },
        "local_compute": local_compute_truth,
        "provider_reserve": {
            "posture": provider_posture,
            "constrained_count": sum(
                1 for item in quota_summary.get("provider_summaries", []) if item.get("availability") == "constrained"
            ),
        },
        "active_time_windows": get_active_time_windows(),
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "recommendations": recommendations,
    }


async def build_governor_snapshot() -> dict[str, Any]:
    from .command_hierarchy import CONTROL_STACK
    from .model_governance import get_command_rights_registry

    state = await get_governor_state()
    capacity = await build_capacity_snapshot()
    rights_registry = get_command_rights_registry()
    presence_snapshot = _build_presence_snapshot(state)
    release_registry = _release_registry()

    lanes = []
    paused = set(state.get("paused_lanes", []))
    global_paused = state.get("global_mode") == "paused"
    for lane in LANE_DEFINITIONS:
        lane_id = lane["id"]
        lanes.append(
            {
                "id": lane_id,
                "label": lane["label"],
                "description": lane["description"],
                "paused": global_paused or lane_id in paused,
                "status": "paused" if global_paused or lane_id in paused else "active",
            }
        )

    return {
        "generated_at": _now_iso(),
        "status": "live",
        "global_mode": state.get("global_mode", "active"),
        "degraded_mode": state.get("degraded_mode", "normal"),
        "reason": state.get("reason", ""),
        "updated_at": state.get("updated_at"),
        "updated_by": state.get("updated_by", "system"),
        "lanes": lanes,
        "capacity": capacity,
        "presence": {
            "state": str(presence_snapshot.get("state") or _default_presence_state()),
            "label": str(presence_snapshot.get("label") or "Unknown"),
            "automation_posture": str(
                presence_snapshot.get("automation_posture") or "normal bounded autonomy"
            ),
            "notification_posture": str(
                presence_snapshot.get("notification_posture") or "full detail"
            ),
            "approval_posture": str(presence_snapshot.get("approval_posture") or "low friction"),
            "updated_at": presence_snapshot.get("updated_at"),
            "updated_by": str(presence_snapshot.get("updated_by") or state.get("updated_by", "system")),
            "mode": str(presence_snapshot.get("mode") or "auto"),
            "configured_state": str(
                presence_snapshot.get("configured_state") or state.get("operator_presence") or _default_presence_state()
            ),
            "configured_label": str(presence_snapshot.get("configured_label") or "Unknown"),
            "signal_state": presence_snapshot.get("signal_state"),
            "signal_source": presence_snapshot.get("signal_source"),
            "signal_updated_at": presence_snapshot.get("signal_updated_at"),
            "signal_updated_by": str(
                presence_snapshot.get("signal_updated_by") or state.get("updated_by", "system")
            ),
            "signal_fresh": bool(presence_snapshot.get("signal_fresh")),
            "signal_age_seconds": presence_snapshot.get("signal_age_seconds"),
            "effective_reason": str(presence_snapshot.get("effective_reason") or ""),
        },
        "release_tier": {
            "state": str(state.get("release_tier") or _default_release_tier()),
            "available_tiers": _release_tiers(),
            "status": str(release_registry.get("status", "configured")),
            "updated_at": state.get("tier_updated_at") or state.get("updated_at"),
            "updated_by": state.get("tier_updated_by") or state.get("updated_by", "system"),
        },
        "command_rights_version": rights_registry.get("version", "unknown"),
        "control_stack": [
            {
                "id": item["id"],
                "label": item["label"],
                "status": "live" if item["id"] == "capacity-governor" else item["status"],
            }
            for item in CONTROL_STACK
        ],
    }


async def build_operations_readiness_snapshot() -> dict[str, Any]:
    backup_restore = get_backup_restore_readiness()
    release_ritual = get_release_ritual_registry()
    economic = get_economic_governance_registry()
    lifecycle = get_data_lifecycle_registry()
    runbooks = get_operator_runbooks_registry()
    from .operator_tests import build_operator_tests_snapshot
    from .promotion_control import build_promotion_controls_snapshot
    from .retirement_control import build_retirement_controls_snapshot

    runbook_items = []
    for item in runbooks.get("runbooks", []):
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("label", _humanize_registry_id(str(item.get("id") or item.get("label") or "runbook")))
            normalized.setdefault(
                "id",
                str(item.get("id") or str(normalized.get("label", "runbook")).replace(" ", "-").lower()),
            )
            runbook_items.append(normalized)
        else:
            value = str(item)
            runbook_items.append(
                {
                    "id": value.replace(" ", "-").lower(),
                    "label": value.title(),
                    "description": None,
                    "cadence": None,
                    "related_surface": None,
                }
            )

    synthetic_operator_tests = await build_operator_tests_snapshot()
    promotion_controls = await build_promotion_controls_snapshot(limit=12)
    retirement_controls = await build_retirement_controls_snapshot(limit=12)
    tool_permissions = await build_tool_permissions_snapshot(operator_tests=synthetic_operator_tests)
    autonomy_activation = _autonomy_activation_summary()
    flow_status_map = {
        str(flow.get("id")): str(flow.get("status") or "configured")
        for flow in synthetic_operator_tests.get("flows", [])
        if flow.get("id")
    }
    restore_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "restore_drill"),
        {},
    )
    promotion_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "promotion_ladder"),
        {},
    )
    retirement_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "retirement_policy"),
        {},
    )
    economic_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "economic_governance"),
        {},
    )
    lifecycle_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "data_lifecycle"),
        {},
    )
    tool_permissions_flow = next(
        (flow for flow in synthetic_operator_tests.get("flows", []) if str(flow.get("id")) == "tool_permissions"),
        {},
    )
    restore_details = dict(restore_flow.get("details") or {})
    economic_details = dict(economic_flow.get("details") or {})
    lifecycle_details = dict(lifecycle_flow.get("details") or {})
    restore_store_results = {
        str(store.get("id")): dict(store)
        for store in restore_details.get("stores", [])
        if isinstance(store, dict) and store.get("id")
    }

    critical_stores = []
    for item in backup_restore.get("critical_stores", []):
        if not isinstance(item, dict):
            continue
        store_id = str(item.get("id") or "store")
        evidence = restore_store_results.get(store_id, {})
        critical_stores.append(
            {
                "id": store_id,
                "label": str(item.get("label") or _humanize_registry_id(store_id)),
                "drill_status": str(
                    evidence.get("probe_status")
                    or item.get("drill_status")
                    or item.get("restore_status")
                    or "configured"
                ),
                "cadence": str(item.get("cadence") or ""),
                "restore_order": item.get("restore_order") or item.get("recovery_order"),
                "verified": bool(evidence.get("verified")),
                "probe_status": str(evidence.get("probe_status") or "") or None,
                "probe_summary": str(evidence.get("probe_summary") or "") or None,
                "last_drill_at": evidence.get("checked_at") or restore_flow.get("last_run_at"),
                "last_outcome": restore_flow.get("last_outcome"),
                "artifacts": list(evidence.get("artifacts") or []),
            }
        )

    backup_restore_status = str(backup_restore.get("status", "configured"))
    restore_flow_status = str(restore_flow.get("status") or "")
    if restore_flow_status in {"live", "live_partial"} and backup_restore_status == "configured":
        backup_restore_status = "live_partial"
    if restore_flow_status == "degraded":
        backup_restore_status = "degraded"

    release_ritual_status = str(release_ritual.get("status", "configured"))
    promotion_flow_status = str(promotion_flow.get("status") or "")
    if promotion_flow_status in {"live", "live_partial"} and release_ritual_status == "configured":
        release_ritual_status = "live_partial"
    if promotion_flow_status == "degraded":
        release_ritual_status = "degraded"

    retirement_status = str(retirement_controls.get("status", "configured"))
    retirement_flow_status = str(retirement_flow.get("status") or "")
    if retirement_flow_status in {"live", "live_partial"} and retirement_status == "configured":
        retirement_status = "live_partial"
    if retirement_flow_status == "degraded":
        retirement_status = "degraded"

    runbooks_status = str(runbooks.get("status", "configured"))
    evidenced_runbooks = 0
    for item in runbook_items:
        evidence_flow_ids = [str(flow_id) for flow_id in item.get("evidence_flow_ids", []) if str(flow_id).strip()]
        support_status = "registry_only"
        if evidence_flow_ids:
            evidence_statuses = [flow_status_map.get(flow_id, "configured") for flow_id in evidence_flow_ids]
            if all(status in {"live", "live_partial"} for status in evidence_statuses):
                support_status = "evidenced"
                evidenced_runbooks += 1
            elif any(status == "degraded" for status in evidence_statuses):
                support_status = "degraded"
        elif item.get("description") and item.get("related_surface"):
            support_status = "documented"
        item["support_status"] = support_status
        item["evidence_flow_ids"] = evidence_flow_ids
    if runbooks_status == "configured" and evidenced_runbooks:
        runbooks_status = "live_partial"
    if any(str(item.get("support_status")) == "degraded" for item in runbook_items):
        runbooks_status = "degraded"

    economic_status = str(economic.get("status", "configured"))
    economic_flow_status = str(economic_flow.get("status") or "")
    if economic_flow_status in {"live", "live_partial"} and economic_status == "configured":
        economic_status = "live_partial"
    if economic_flow_status == "degraded":
        economic_status = "degraded"

    lifecycle_status = str(lifecycle.get("status", "configured"))
    lifecycle_flow_status = str(lifecycle_flow.get("status") or "")
    if lifecycle_flow_status in {"live", "live_partial"} and lifecycle_status == "configured":
        lifecycle_status = "live_partial"
    if lifecycle_flow_status == "degraded":
        lifecycle_status = "degraded"

    autonomy_status = str(autonomy_activation.get("status", "configured"))

    statuses = {
        backup_restore_status,
        release_ritual_status,
        economic_status,
        lifecycle_status,
        retirement_status,
        autonomy_status,
        str(tool_permissions.get("status", "configured")),
        runbooks_status,
        str(synthetic_operator_tests.get("status", "configured")),
    }
    status = (
        "live_partial"
        if {"configured", "planned", "live_partial"} & statuses
        else "live"
    )
    if "degraded" in statuses:
        status = "degraded"

    return {
        "generated_at": _now_iso(),
        "status": status,
        "runbooks": {
            "status": runbooks_status,
            "items": runbook_items,
        },
        "backup_restore": {
            "status": backup_restore_status,
            "drill_mode": str(restore_details.get("drill_mode") or "registry_posture"),
            "last_drill_at": restore_flow.get("last_run_at"),
            "last_outcome": restore_flow.get("last_outcome"),
            "verified_store_count": int(restore_details.get("verified_store_count", 0) or 0),
            "store_count": int(restore_details.get("store_count", len(critical_stores)) or len(critical_stores)),
            "critical_stores": critical_stores,
        },
        "release_ritual": {
            "status": release_ritual_status,
            "tiers": list(release_ritual.get("tiers", [])),
            "ritual": list(release_ritual.get("ritual", [])),
            "last_rehearsal_at": promotion_flow.get("last_run_at"),
            "last_outcome": promotion_flow.get("last_outcome"),
            "rehearsal_status": promotion_flow_status or "configured",
            "active_promotion_count": len(promotion_controls.get("active_promotions", [])),
        },
        "deprecation_retirement": {
            "status": retirement_status,
            "asset_classes": list(retirement_controls.get("asset_classes", [])),
            "stages": list(retirement_controls.get("stages", [])),
            "rule": str(retirement_controls.get("rule") or ""),
            "recent_retirement_count": len(retirement_controls.get("recent_retirements", [])),
            "active_retirement_count": len(retirement_controls.get("active_retirements", [])),
            "last_rehearsal_at": retirement_flow.get("last_run_at"),
            "last_outcome": retirement_flow.get("last_outcome"),
            "recent_retirements": list(retirement_controls.get("recent_retirements", [])),
        },
        "economic_governance": {
            "status": economic_status,
            "premium_reserve_lanes": list(economic.get("premium_reserve_lanes", [])),
            "automatic_spend_lanes": list(economic.get("automatic_spend_lanes", [])),
            "approval_required_lanes": list(economic.get("approval_required_lanes", [])),
            "downgrade_order": list(economic.get("downgrade_order", [])),
            "provider_count": int(economic_details.get("provider_count", 0) or 0),
            "recent_lease_count": int(economic_details.get("recent_lease_count", 0) or 0),
            "constrained_count": int(economic_details.get("constrained_count", 0) or 0),
            "last_verified_at": economic_flow.get("last_run_at"),
            "last_outcome": economic_flow.get("last_outcome"),
        },
        "data_lifecycle": {
            "status": lifecycle_status,
            "classes": list(lifecycle.get("classes", [])),
            "class_count": int(lifecycle_details.get("class_count", 0) or 0),
            "run_count": int(lifecycle_details.get("run_count", 0) or 0),
            "eval_artifact_count": int(lifecycle_details.get("eval_artifact_count", 0) or 0),
            "last_verified_at": lifecycle_flow.get("last_run_at"),
            "last_outcome": lifecycle_flow.get("last_outcome"),
        },
        "tool_permissions": {
            "status": str(tool_permissions.get("status", "configured")),
            "default_mode": str(tool_permissions.get("default_mode", "governor_mediated")),
            "subject_count": int(tool_permissions.get("subject_count", 0) or 0),
            "enforced_subject_count": int(tool_permissions.get("enforced_subject_count", 0) or 0),
            "denied_action_count": int(tool_permissions.get("denied_action_count", 0) or 0),
            "last_verified_at": tool_permissions.get("last_verified_at") or tool_permissions_flow.get("last_run_at"),
            "last_outcome": tool_permissions.get("last_outcome") or tool_permissions_flow.get("last_outcome"),
            "subjects": list(tool_permissions.get("subjects", [])),
        },
        "autonomy_activation": autonomy_activation,
        "synthetic_operator_tests": synthetic_operator_tests,
    }


async def build_tool_permissions_snapshot(
    *, operator_tests: dict[str, Any] | None = None
) -> dict[str, Any]:
    snapshot = build_tool_permission_registry_snapshot()
    operator_tests = operator_tests or {}
    if not operator_tests:
        from .operator_tests import build_operator_tests_snapshot

        operator_tests = await build_operator_tests_snapshot()

    flow = next(
        (item for item in operator_tests.get("flows", []) if str(item.get("id")) == "tool_permissions"),
        {},
    )
    details = dict(flow.get("details") or {})
    status = str(snapshot.get("status", "configured"))
    flow_status = str(flow.get("status") or "")
    if flow_status in {"live", "live_partial"} and status == "configured":
        status = "live_partial"
    if flow_status == "degraded":
        status = "degraded"

    subjects = []
    for item in snapshot.get("subjects", []):
        if not isinstance(item, dict):
            continue
        subjects.append(
            {
                "subject": str(item.get("subject") or "subject"),
                "label": str(item.get("label") or _humanize_registry_id(str(item.get("subject") or "subject"))),
                "mode": str(item.get("mode") or snapshot.get("default_mode", "governor_mediated")),
                "allow": list(item.get("allow") or []),
                "deny": list(item.get("deny") or []),
                "allow_count": len(list(item.get("allow") or [])),
                "deny_count": len(list(item.get("deny") or [])),
                "direct_execution": bool(item.get("direct_execution")),
            }
        )

    return {
        **snapshot,
        "status": status,
        "subjects": subjects,
        "enforced_subject_count": int(details.get("enforced_subject_count", snapshot.get("subject_count", 0)) or 0),
        "denied_action_count": int(details.get("denied_action_count", 0) or 0),
        "last_verified_at": flow.get("last_run_at"),
        "last_outcome": flow.get("last_outcome"),
    }
