from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .model_governance import (
    get_lane_selection_matrix,
    get_provider_catalog_registry,
)
from .repo_paths import resolve_repo_root, resolve_subscription_policy_path

REPO_ROOT = resolve_repo_root(__file__)
REPORTS_DIR = REPO_ROOT / "reports" / "truth-inventory"
CAPABILITY_INTELLIGENCE_PATH = REPORTS_DIR / "capability-intelligence.json"
LOCAL_ENDPOINT_CAPABILITY_PATH = REPORTS_DIR / "local-endpoint-capability.json"
CAPABILITY_REFRESH_HISTORY_PATH = REPORTS_DIR / "capability-refresh-history.json"
POLICY_PATH = resolve_subscription_policy_path(__file__)
QUOTA_TRUTH_PATH = REPORTS_DIR / "quota-truth.json"
CAPACITY_TELEMETRY_PATH = REPORTS_DIR / "capacity-telemetry.json"

PRIMARY_TASK_FIT = 92
FALLBACK_TASK_FIT = 74
MATCHED_STRENGTH_FIT = 62
DEFAULT_TASK_FIT = 38

LOCAL_ENDPOINT_HINTS = [
    {
        "subject_id": "foundry-interactive-reserve",
        "subject_kind": "local_endpoint",
        "node_id": "foundry",
        "reserve_class": "interactive_local_reserve",
        "task_fit": {
            "multi_file_implementation": 88,
            "interactive_architecture": 84,
            "private_automation": 82,
            "sovereign_coding": 94,
        },
    },
    {
        "subject_id": "foundry-coder-lane",
        "subject_kind": "local_endpoint",
        "node_id": "foundry",
        "reserve_class": "interactive_local_reserve",
        "task_fit": {
            "multi_file_implementation": 94,
            "async_backlog_execution": 82,
            "repo_wide_audit": 58,
            "private_automation": 76,
        },
    },
    {
        "subject_id": "foundry-bulk-pool",
        "subject_kind": "local_endpoint",
        "node_id": "foundry",
        "reserve_class": "harvest_local_bulk",
        "task_fit": {
            "cheap_bulk_transform": 96,
            "async_backlog_execution": 86,
            "private_automation": 78,
        },
    },
    {
        "subject_id": "workshop-creative-reserve",
        "subject_kind": "local_endpoint",
        "node_id": "workshop",
        "reserve_class": "interactive_local_reserve",
        "task_fit": {
            "creative_sovereign": 98,
            "private_automation": 52,
        },
    },
    {
        "subject_id": "workshop-batch-support-lane",
        "subject_kind": "local_endpoint",
        "node_id": "workshop",
        "reserve_class": "harvest_local_bulk",
        "task_fit": {
            "cheap_bulk_transform": 72,
            "creative_sovereign": 78,
            "private_automation": 58,
        },
    },
    {
        "subject_id": "dev-support-endpoints",
        "subject_kind": "local_endpoint",
        "node_id": "dev",
        "reserve_class": "ops_non_harvest",
        "task_fit": {
            "private_automation": 64,
            "repo_wide_audit": 46,
            "knowledge_memory": 58,
        },
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {"providers": {}, "task_classes": {}}
    try:
        payload = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {"providers": {}, "task_classes": {}}
    if not isinstance(payload, dict):
        return {"providers": {}, "task_classes": {}}
    payload.setdefault("providers", {})
    payload.setdefault("task_classes", {})
    return payload


def _quota_truth() -> dict[str, Any]:
    return _load_json(QUOTA_TRUTH_PATH)


def _capacity_telemetry() -> dict[str, Any]:
    return _load_json(CAPACITY_TELEMETRY_PATH)


def _quota_index() -> dict[str, dict[str, Any]]:
    records = _quota_truth().get("records", [])
    if not isinstance(records, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        provider_id = str(record.get("provider_id") or "").strip()
        if provider_id:
            indexed[provider_id] = dict(record)
    return indexed


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _freshness_score(value: Any, *, max_age_days: int = 30) -> int:
    parsed = _parse_dt(value)
    if parsed is None:
        return 35
    age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    age_days = max(age_seconds, 0) / 86400
    if age_days <= 3:
        return 96
    if age_days <= 7:
        return 88
    if age_days <= 14:
        return 76
    if age_days <= max_age_days:
        return 58
    return 32


def _task_strength_fit(policy: dict[str, Any], provider_id: str, task_class: str) -> int:
    task_meta = dict(policy.get("task_classes", {}).get(task_class, {}))
    primary = [str(item) for item in task_meta.get("primary", [])]
    fallback = [str(item) for item in task_meta.get("fallback", [])]
    if provider_id in primary:
        return PRIMARY_TASK_FIT
    if provider_id in fallback:
        return FALLBACK_TASK_FIT

    strengths = [
        str(item).strip().lower()
        for item in dict(policy.get("providers", {}).get(provider_id, {})).get("strengths", [])
        if str(item).strip()
    ]
    task_tokens = set(task_class.lower().split("_"))
    for strength in strengths:
        if strength == task_class.lower():
            return MATCHED_STRENGTH_FIT
        if task_tokens & set(strength.split("_")):
            return MATCHED_STRENGTH_FIT
    return DEFAULT_TASK_FIT


def _runtime_posture(provider: dict[str, Any]) -> tuple[str, int]:
    observed_runtime = dict(provider.get("observed_runtime") or {})
    access_mode = str(provider.get("access_mode") or "")
    evidence = dict(provider.get("evidence") or {})
    cli_probe = dict(evidence.get("cli_probe") or {})
    cli_probe_status = str(cli_probe.get("status") or "")
    routing_enabled = bool(observed_runtime.get("routing_policy_enabled"))
    active_burn = bool(observed_runtime.get("active_burn_observed"))
    api_configured = bool(observed_runtime.get("api_configured"))
    proxy_activity = bool(observed_runtime.get("proxy_activity_observed"))

    if access_mode == "local" and routing_enabled:
        return "local_runtime_available", 92
    if active_burn:
        return "live_burn_observed", 92
    if access_mode == "cli" and routing_enabled and cli_probe_status == "installed":
        return "routing_enabled_cli_ready", 82
    if access_mode == "cli" and cli_probe_status == "installed":
        return "tool_installed_no_recent_burn", 70
    if access_mode == "cli" and routing_enabled:
        return "routing_enabled_without_observed_tool", 58
    if access_mode == "api" and api_configured and proxy_activity:
        return "proxy_configured", 48
    if access_mode == "api" and api_configured:
        return "api_configured_no_recent_burn", 38
    return "catalog_only", 28


def _subscription_headroom(record: dict[str, Any]) -> int:
    remaining = record.get("remaining_units")
    if remaining is None:
        return 54
    try:
        value = int(remaining)
    except (TypeError, ValueError):
        return 54
    if value >= 100:
        return 88
    if value >= 25:
        return 74
    if value > 0:
        return 56
    return 20


def _quota_window_priority(record: dict[str, Any]) -> int:
    usage_mode = str(record.get("usage_mode") or "")
    if usage_mode == "local_compute":
        return 76
    target = _parse_dt(record.get("next_reset_at"))
    if usage_mode == "metered_api":
        return 18
    if target is None:
        return 44 if usage_mode == "subscription" else 30
    seconds_until_reset = (target - datetime.now(timezone.utc)).total_seconds()
    if seconds_until_reset <= 0:
        return 40
    if seconds_until_reset <= 8 * 3600:
        return 96
    if seconds_until_reset <= 24 * 3600:
        return 72
    return 46


def _eval_fit(provider: dict[str, Any]) -> int:
    state_classes = {str(item).strip() for item in provider.get("state_classes", []) if str(item).strip()}
    if "active-burn" in state_classes:
        return 84
    if "active-routing" in state_classes:
        return 76
    if "configured-unused" in state_classes:
        return 58
    return 50


def _provider_record(
    policy: dict[str, Any],
    provider: dict[str, Any],
    task_class: str,
    quota_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    provider_id = str(provider.get("id") or "").strip()
    provider_meta = dict(policy.get("providers", {}).get(provider_id, {}))
    reserve_class = str(provider_meta.get("reserve") or "unknown")
    posture_label, runtime_readiness = _runtime_posture(provider)
    quota_record = dict(quota_index.get(provider_id) or {})
    docs_fit = _task_strength_fit(policy, provider_id, task_class)
    freshness = _freshness_score(dict(provider.get("observed_runtime") or {}).get("last_verified_at"))
    observed_success = runtime_readiness if posture_label != "catalog_only" else 24
    headroom_fit = _subscription_headroom(quota_record)
    quota_priority = _quota_window_priority(quota_record)
    eval_fit = _eval_fit(provider)

    capability_score = round(
        (docs_fit * 0.15)
        + (runtime_readiness * 0.20)
        + (eval_fit * 0.25)
        + (observed_success * 0.15)
        + (freshness * 0.10)
        + (max(headroom_fit, quota_priority) * 0.10)
        + (4 if provider_id == "athanor_local" else 2),
        2,
    )
    capability_confidence = round(
        min(1.0, ((runtime_readiness + freshness + eval_fit) / 300)),
        2,
    )

    demotion_state = "healthy"
    demotion_reason = None
    if runtime_readiness < 40:
        demotion_state = "demoted"
        demotion_reason = posture_label
    elif runtime_readiness < 65:
        demotion_state = "degraded"
        demotion_reason = posture_label

    return {
        "subject_id": provider_id,
        "subject_kind": "provider",
        "task_class": task_class,
        "reserve_class": reserve_class,
        "docs_fit": docs_fit,
        "docs_freshness": freshness,
        "runtime_readiness": runtime_readiness,
        "quota_window_priority": quota_priority,
        "headroom_fit": headroom_fit,
        "eval_fit": eval_fit,
        "observed_success_posture": observed_success,
        "capability_score": capability_score,
        "capability_confidence": capability_confidence,
        "demotion_state": demotion_state,
        "demotion_reason": demotion_reason,
        "promotion_required": bool(str(provider_meta.get("routing_posture") or "") == "governed_handoff_only"),
        "evidence_sources": [
            "projects/agents/config/subscription-routing-policy.yaml",
            "config/automation-backbone/provider-catalog.json",
            "reports/truth-inventory/quota-truth.json",
        ],
        "verified_at": _now_iso(),
    }


def _node_samples(capacity: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    samples = capacity.get("gpu_samples", [])
    if not isinstance(samples, list):
        return []
    return [dict(sample) for sample in samples if str(sample.get("node_id") or "") == node_id]


def _local_endpoint_records(capacity: dict[str, Any]) -> list[dict[str, Any]]:
    summary = dict(capacity.get("capacity_summary") or {})
    harvestable_by_node = dict(summary.get("harvestable_by_node") or {})
    queue_depth = int(summary.get("scheduler_queue_depth") or 0)
    generated_at = str(capacity.get("generated_at") or _now_iso())

    records: list[dict[str, Any]] = []
    for hint in LOCAL_ENDPOINT_HINTS:
        node_id = str(hint["node_id"])
        node_samples = _node_samples(capacity, node_id)
        if not node_samples:
            continue

        avg_utilization = sum(float(sample.get("utilization_percent") or 0) for sample in node_samples) / max(
            len(node_samples), 1
        )
        protected_count = sum(1 for sample in node_samples if bool(sample.get("protected_reserve")))
        harvestable_count = int(harvestable_by_node.get(node_id, 0) or 0)
        reserve_class = str(hint["reserve_class"])
        if reserve_class == "interactive_local_reserve":
            runtime_readiness = 90 if protected_count > 0 else 50
            headroom_fit = max(30, round(100 - avg_utilization))
            demotion_state = "healthy" if protected_count > 0 else "degraded"
            demotion_reason = None if protected_count > 0 else "protected_reserve_missing"
        elif reserve_class == "harvest_local_bulk":
            harvest_gate_open = queue_depth == 0 and avg_utilization < 20 and harvestable_count > 0
            runtime_readiness = 92 if harvest_gate_open else 58
            headroom_fit = min(98, 42 + (harvestable_count * 12)) if harvestable_count else max(24, 65 - round(avg_utilization))
            demotion_state = "healthy" if harvest_gate_open else "degraded"
            demotion_reason = None if harvest_gate_open else "harvest_gate_closed"
        else:
            runtime_readiness = 62 if avg_utilization < 80 else 44
            headroom_fit = max(20, 75 - round(avg_utilization))
            demotion_state = "healthy" if avg_utilization < 80 else "degraded"
            demotion_reason = None if avg_utilization < 80 else "ops_lane_constrained"

        freshness = _freshness_score(generated_at, max_age_days=7)
        for task_class, docs_fit in dict(hint["task_fit"]).items():
            capability_score = round(
                (docs_fit * 0.25)
                + (runtime_readiness * 0.25)
                + (62 * 0.15)
                + (runtime_readiness * 0.10)
                + (freshness * 0.10)
                + (headroom_fit * 0.15),
                2,
            )
            records.append(
                {
                    "subject_id": hint["subject_id"],
                    "subject_kind": hint["subject_kind"],
                    "task_class": task_class,
                    "node_id": node_id,
                    "reserve_class": reserve_class,
                    "docs_fit": docs_fit,
                    "docs_freshness": freshness,
                    "runtime_readiness": runtime_readiness,
                    "quota_window_priority": 0,
                    "headroom_fit": headroom_fit,
                    "eval_fit": 62,
                    "observed_success_posture": runtime_readiness,
                    "capability_score": capability_score,
                    "capability_confidence": round(min(1.0, (runtime_readiness + headroom_fit + freshness) / 300), 2),
                    "demotion_state": demotion_state,
                    "demotion_reason": demotion_reason,
                    "promotion_required": False,
                    "evidence_sources": [
                        "reports/truth-inventory/capacity-telemetry.json",
                        "config/automation-backbone/lane-selection-matrix.json",
                    ],
                    "verified_at": generated_at,
                }
            )
    return records


def build_capability_intelligence_snapshot() -> dict[str, Any]:
    policy = _load_policy()
    provider_catalog = get_provider_catalog_registry()
    quota_index = _quota_index()
    capacity = _capacity_telemetry()
    lane_selection = get_lane_selection_matrix()
    provider_entries = [
        dict(item)
        for item in provider_catalog.get("providers", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip() in policy.get("providers", {})
    ]
    task_classes = [
        str(task_class)
        for task_class in policy.get("task_classes", {}).keys()
        if str(task_class).strip()
    ]
    provider_records = [
        _provider_record(policy, provider, task_class, quota_index)
        for provider in provider_entries
        for task_class in task_classes
    ]
    local_endpoint_records = _local_endpoint_records(capacity)
    degraded_subjects = [
        {
            "subject_id": record["subject_id"],
            "subject_kind": record["subject_kind"],
            "task_class": record["task_class"],
            "demotion_state": record["demotion_state"],
            "demotion_reason": record["demotion_reason"],
        }
        for record in [*provider_records, *local_endpoint_records]
        if record["demotion_state"] != "healthy"
    ]
    generated_at = _now_iso()
    return {
        "version": "2026-04-17.1",
        "generated_at": generated_at,
        "source_of_truth": "reports/truth-inventory/capability-intelligence.json",
        "provider_count": len(provider_records),
        "local_endpoint_count": len(local_endpoint_records),
        "providers": provider_records,
        "local_endpoints": local_endpoint_records,
        "degraded_subjects": degraded_subjects,
        "evidence_sources": [
            "projects/agents/config/subscription-routing-policy.yaml",
            "config/automation-backbone/provider-catalog.json",
            "reports/truth-inventory/quota-truth.json",
            "reports/truth-inventory/capacity-telemetry.json",
            "config/automation-backbone/lane-selection-matrix.json",
        ],
        "dispatch_reference": str(lane_selection.get("version") or "unknown"),
    }


def get_capability_intelligence_artifact() -> dict[str, Any]:
    payload = _load_json(CAPABILITY_INTELLIGENCE_PATH)
    if payload:
        return payload
    return build_capability_intelligence_snapshot()


def get_local_endpoint_capability_artifact() -> dict[str, Any]:
    payload = _load_json(LOCAL_ENDPOINT_CAPABILITY_PATH)
    if payload:
        return payload
    snapshot = build_capability_intelligence_snapshot()
    return {
        "version": snapshot["version"],
        "generated_at": snapshot["generated_at"],
        "source_of_truth": "reports/truth-inventory/local-endpoint-capability.json",
        "local_endpoints": snapshot["local_endpoints"],
    }


def get_capability_refresh_history_artifact() -> dict[str, Any]:
    payload = _load_json(CAPABILITY_REFRESH_HISTORY_PATH)
    if payload:
        return payload
    snapshot = build_capability_intelligence_snapshot()
    return {
        "version": snapshot["version"],
        "updated_at": snapshot["generated_at"],
        "history": [
            {
                "generated_at": snapshot["generated_at"],
                "provider_count": snapshot["provider_count"],
                "local_endpoint_count": snapshot["local_endpoint_count"],
                "degraded_subject_count": len(snapshot["degraded_subjects"]),
            }
        ],
    }


def find_capability_record(
    artifact: dict[str, Any],
    *,
    subject_id: str,
    task_class: str,
    subject_kind: str = "provider",
) -> dict[str, Any]:
    key = "providers" if subject_kind == "provider" else "local_endpoints"
    records = artifact.get(key, [])
    if not isinstance(records, list):
        return {}
    for record in records:
        if not isinstance(record, dict):
            continue
        if str(record.get("subject_id") or "") != subject_id:
            continue
        if str(record.get("task_class") or "") != task_class:
            continue
        return dict(record)
    return {}


def best_local_endpoint_for_task(artifact: dict[str, Any], task_class: str) -> dict[str, Any]:
    records = artifact.get("local_endpoints", [])
    if not isinstance(records, list):
        return {}
    matches = [
        dict(record)
        for record in records
        if isinstance(record, dict) and str(record.get("task_class") or "") == task_class
    ]
    if not matches:
        return {}
    matches.sort(key=lambda record: float(record.get("capability_score") or 0), reverse=True)
    return matches[0]


def _capability_sort_key(record: dict[str, Any]) -> tuple[int, float]:
    state = str(record.get("demotion_state") or "unknown")
    penalty = 0 if state == "healthy" else (1 if state == "degraded" else 2)
    return (penalty, -float(record.get("capability_score") or 0))


def _select_capability_leader(records: list[dict[str, Any]], task_class: str) -> dict[str, Any] | None:
    matches = [
        dict(record)
        for record in records
        if isinstance(record, dict) and str(record.get("task_class") or "") == task_class
    ]
    candidates = matches if matches else [dict(record) for record in records if isinstance(record, dict)]
    if not candidates:
        return None
    leader = sorted(candidates, key=_capability_sort_key)[0]
    return {
        "subject_id": str(leader.get("subject_id") or ""),
        "task_class": str(leader.get("task_class") or task_class),
        "capability_score": float(leader.get("capability_score") or 0),
        "demotion_state": str(leader.get("demotion_state") or "unknown"),
        "reserve_class": leader.get("reserve_class"),
    }


def build_capability_governance_summary(artifact: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = dict(artifact or get_capability_intelligence_artifact())
    providers = [dict(record) for record in snapshot.get("providers", []) if isinstance(record, dict)]
    local_endpoints = [dict(record) for record in snapshot.get("local_endpoints", []) if isinstance(record, dict)]
    degraded_subjects = [dict(record) for record in snapshot.get("degraded_subjects", []) if isinstance(record, dict)]
    implementation = _select_capability_leader(providers, "multi_file_implementation")
    audit = _select_capability_leader(providers, "repo_wide_audit")
    local_endpoint = _select_capability_leader(local_endpoints, "multi_file_implementation")

    next_actions: list[str] = []
    if degraded_subjects:
        next_actions.append("Repair degraded or demoted capability subjects before widening ordinary auto-routing.")
    if not providers:
        next_actions.append("Generate or refresh provider capability intelligence before relying on subscription burn posture.")
    if local_endpoint and str(local_endpoint.get("demotion_state") or "unknown") != "healthy":
        next_actions.append("Re-check local endpoint headroom before treating Foundry or Workshop as an implementation leader.")
    if not next_actions:
        next_actions.append("Capability posture is healthy enough for normal routing and executive-kernel summaries.")

    status = "live"
    if not providers and not local_endpoints:
        status = "degraded"
    elif degraded_subjects:
        status = "live_partial"

    return {
        "generated_at": str(snapshot.get("generated_at") or _now_iso()),
        "version": str(snapshot.get("version") or "unknown"),
        "status": status,
        "source_of_truth": str(snapshot.get("source_of_truth") or "reports/truth-inventory/capability-intelligence.json"),
        "provider_count": int(snapshot.get("provider_count") or len(providers)),
        "local_endpoint_count": int(snapshot.get("local_endpoint_count") or len(local_endpoints)),
        "degraded_subject_count": len(degraded_subjects),
        "implementation": implementation,
        "audit": audit,
        "local_endpoint": local_endpoint,
        "dispatch_reference": str(snapshot.get("dispatch_reference") or "unknown"),
        "next_actions": next_actions,
    }


async def build_live_capability_snapshot() -> dict[str, Any]:
    snapshot = get_capability_intelligence_artifact()
    snapshot = dict(snapshot)
    snapshot.setdefault("generated_at", _now_iso())
    snapshot.setdefault("version", "unknown")
    snapshot.setdefault("source_of_truth", "reports/truth-inventory/capability-intelligence.json")
    snapshot.setdefault("providers", [])
    snapshot.setdefault("local_endpoints", [])
    snapshot.setdefault("degraded_subjects", [])
    return snapshot


async def build_live_capability_governance_snapshot() -> dict[str, Any]:
    return build_capability_governance_summary(await build_live_capability_snapshot())
