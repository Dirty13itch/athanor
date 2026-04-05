from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .model_governance import (
    get_current_autonomy_phase,
    get_next_autonomy_phase,
    get_operator_runbooks_registry,
    get_unmet_autonomy_prerequisites,
)
from .subscriptions import get_provider_catalog_snapshot


REQUIRED_LAUNCH_RUNBOOK_IDS = {
    "constrained-mode",
    "degraded-mode",
    "recovery-only",
    "postgres-restore",
    "redis-reconciliation",
    "failed-promotion",
    "stuck-media-pipeline",
    "source-auth-expiry",
    "model-lane-outage",
    "operator-auth-failure",
}

PROVIDER_VERIFICATION_POSTURES = {
    "live_burn_observed_cost_unverified",
    "supported_tool_subscription_unverified",
    "routing_enabled_without_observed_tool",
    "cli_configured_without_observed_tool",
    "vault_provider_specific_auth_failed",
    "vault_provider_specific_request_failed",
    "vault_provider_specific_not_supported",
    "vault_proxy_active_no_provider_specific_evidence",
}


def _candidate_truth_inventory_dirs() -> list[Path]:
    candidates: list[Path] = []
    env_dir = str(os.getenv("ATHANOR_REPORTS_DIR") or "").strip()
    if env_dir:
        candidates.append(Path(env_dir))
    runtime_artifact_root = str(os.getenv("ATHANOR_RUNTIME_ARTIFACT_ROOT") or "").strip()
    if runtime_artifact_root:
        candidates.append(Path(runtime_artifact_root) / "reports" / "truth-inventory")
    candidates.extend(
        [
            Path.cwd() / "reports" / "truth-inventory",
            Path("/output/reports/truth-inventory"),
            Path("/workspace/reports/truth-inventory"),
            Path("/opt/athanor/reports/truth-inventory"),
            Path("/opt/athanor/agents/reports/truth-inventory"),
            Path("/app/reports/truth-inventory"),
        ]
    )
    return candidates


def _truth_inventory_artifact_path(filename: str) -> Path:
    for directory in _candidate_truth_inventory_dirs():
        candidate = directory / filename
        if candidate.exists():
            return candidate
    first_dir = next(iter(_candidate_truth_inventory_dirs()), Path("/output/reports/truth-inventory"))
    return first_dir / filename


def _provider_usage_evidence_path() -> Path:
    return _truth_inventory_artifact_path("provider-usage-evidence.json")


def _vault_litellm_env_audit_path() -> Path:
    return _truth_inventory_artifact_path("vault-litellm-env-audit.json")


def _load_json_artifact(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception:
        return None, "unreadable"


def _latest_provider_capture_index(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    captures = list((payload or {}).get("captures") or [])
    latest_by_provider: dict[str, dict[str, Any]] = {}
    for capture in captures:
        if not isinstance(capture, dict):
            continue
        provider_id = str(capture.get("provider_id") or "").strip()
        observed_at = str(capture.get("observed_at") or "").strip()
        if not provider_id or not observed_at:
            continue
        current = latest_by_provider.get(provider_id)
        current_observed_at = str((current or {}).get("observed_at") or "")
        if not current or observed_at >= current_observed_at:
            latest_by_provider[provider_id] = dict(capture)
    return latest_by_provider


def _count_capture_statuses(latest_by_provider: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for capture in latest_by_provider.values():
        status = str(capture.get("status") or "").strip() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _provider_env_names_for_audit(
    provider: dict[str, Any],
    audit: dict[str, Any],
    field_name: str,
) -> list[str]:
    provider_envs = {
        str(name).strip()
        for name in provider.get("env_contracts", [])
        if str(name).strip()
    }
    if not provider_envs:
        return []
    return sorted(
        str(name).strip()
        for name in audit.get(field_name, [])
        if str(name).strip() and str(name).strip() in provider_envs
    )


def _required_vault_env_names(provider: dict[str, Any]) -> list[str]:
    runtime_contract = dict(provider.get("vault_runtime_contract") or {})
    required = sorted(
        {
            str(rule.get("name") or "").strip()
            for rule in runtime_contract.get("env_rules", [])
            if str(rule.get("name") or "").strip()
            and str(rule.get("role") or "").strip() == "required"
        }
    )
    if required:
        return required
    return sorted(str(name).strip() for name in provider.get("env_contracts", []) if str(name).strip())


def _format_name_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _classify_vault_auth_failure(
    provider: dict[str, Any],
    capture: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, str]:
    provider_label = str(provider.get("label") or provider.get("id") or "provider")
    proxy = dict(dict(provider.get("evidence") or {}).get("proxy") or {})
    requested_model = str(capture.get("requested_model") or proxy.get("alias") or provider_label)
    error_snippet = str(capture.get("error_snippet") or "").strip().lower()
    missing_names = _provider_env_names_for_audit(provider, audit, "container_missing_env_names")
    present_names = _provider_env_names_for_audit(provider, audit, "container_present_env_names")
    required_names = _required_vault_env_names(provider)
    if not missing_names and required_names:
        missing_names = [name for name in required_names if name not in present_names]
    if not present_names and required_names:
        present_names = [name for name in required_names if name not in missing_names]

    if "cookie auth" in error_snippet:
        env_names = missing_names or required_names or present_names
        env_suffix = f" Ensure {_format_name_list(env_names)} is delivered to litellm." if env_names else ""
        return {
            "code": "auth_mode_mismatch",
            "next_action": (
                f"Verify the upstream auth mode for served model `{requested_model}` before re-probing `{provider_label}`."
                f"{env_suffix}"
            ),
        }
    if missing_names and any(
        marker in error_snippet for marker in ("missing", "no key is set", "api key", "auth token")
    ):
        return {
            "code": "missing_required_env",
            "next_action": (
                f"Use the VAULT LiteLLM repair packet to restore {_format_name_list(missing_names)}, "
                f"recreate or redeploy `litellm`, then re-probe served model `{requested_model}`."
            ),
        }
    if present_names and any(
        marker in error_snippet
        for marker in ("incorrect api key", "invalid api key", "authenticationerror", "unauthorized", "token expired")
    ):
        return {
            "code": "present_key_invalid",
            "next_action": (
                f"Use the VAULT LiteLLM repair packet to rotate {_format_name_list(present_names)}, "
                f"recreate or redeploy `litellm`, then re-probe served model `{requested_model}`."
            ),
        }
    env_names = missing_names or present_names or required_names
    env_suffix = f" Check {_format_name_list(env_names)} while reconciling the auth path." if env_names else ""
    return {
        "code": "auth_failed_unknown",
        "next_action": (
            f"Inspect the latest auth failure for served model `{requested_model}` and reconcile `{provider_label}` on VAULT."
            f"{env_suffix}"
        ),
    }


def _provider_verification_steps(
    provider: dict[str, Any],
    *,
    evidence_posture: str,
    provider_usage_capture: dict[str, Any],
    vault_litellm_env_audit: dict[str, Any],
) -> list[str]:
    explicit_steps = [str(step).strip() for step in provider.get("verification_steps", []) if str(step).strip()]
    provider_label = str(provider.get("label") or provider.get("id") or "provider")
    alias = str(
        provider_usage_capture.get("requested_model")
        or dict(dict(provider.get("evidence") or {}).get("proxy") or {}).get("alias")
        or provider_label
    )

    if evidence_posture == "vault_provider_specific_auth_failed":
        classification = _classify_vault_auth_failure(provider, provider_usage_capture, vault_litellm_env_audit)
        return [
            classification["next_action"],
            f"Do not treat `{provider_label}` as provider-specifically proven until the auth failure is gone and a successful completion is recorded.",
        ]
    if evidence_posture == "vault_provider_specific_request_failed":
        return [
            f"Debug the failed provider-specific VAULT LiteLLM request for served model `{alias}`.",
            f"Capture one successful completion for `{provider_label}` or keep the lane explicitly demoted.",
        ]
    if evidence_posture == "vault_provider_specific_not_supported":
        return [
            f"Update the provider evidence contract for `{provider_label}` to match a currently served LiteLLM model id, or keep it demoted.",
            "Do not mark this lane proven until a provider-specific served model is actually callable.",
        ]
    if explicit_steps:
        return explicit_steps
    if evidence_posture == "vault_proxy_active_no_provider_specific_evidence":
        return [
            f"Run a provider-specific request through the VAULT LiteLLM served model `{alias}` and record the result.",
            f"Keep `{provider_label}` demoted until the proxy activity is backed by provider-specific evidence.",
        ]
    return ["No immediate verification gap recorded."]


def _provider_verification_priority(evidence_posture: str, pricing_truth_label: str) -> int:
    if evidence_posture == "live_burn_observed_cost_unverified":
        return 0
    if evidence_posture in {"supported_tool_subscription_unverified", "cli_configured_without_observed_tool"}:
        return 1
    if evidence_posture in {"routing_enabled_without_observed_tool", "vault_provider_specific_auth_failed", "vault_provider_specific_request_failed"}:
        return 2
    if evidence_posture in {"vault_provider_specific_not_supported", "vault_proxy_active_no_provider_specific_evidence"}:
        return 3
    if pricing_truth_label == "flat_rate_unverified":
        return 5
    return 99


def _build_provider_launch_summary(
    *,
    evidence_payload: dict[str, Any] | None,
    vault_litellm_env_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    provider_snapshot = get_provider_catalog_snapshot(policy_only=False)
    providers = [
        dict(item)
        for item in provider_snapshot.get("providers", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    latest_captures = _latest_provider_capture_index(evidence_payload)
    capture_status_counts = _count_capture_statuses(latest_captures)
    weak_posture_counts: dict[str, int] = {}
    weak_provider_ids: list[str] = []
    verification_queue: list[dict[str, Any]] = []
    vault_litellm_env_audit = dict(vault_litellm_env_audit or {})

    for provider in providers:
        provider_id = str(provider.get("id") or "").strip()
        evidence_posture = str(provider.get("evidence_posture") or "").strip()
        pricing_truth_label = str(provider.get("pricing_truth_label") or "").strip()
        if evidence_posture not in PROVIDER_VERIFICATION_POSTURES and pricing_truth_label != "flat_rate_unverified":
            continue

        priority = _provider_verification_priority(evidence_posture, pricing_truth_label)
        if priority >= 99:
            continue
        weak_posture_counts[evidence_posture] = weak_posture_counts.get(evidence_posture, 0) + 1
        weak_provider_ids.append(provider_id)
        provider_usage_capture = dict(latest_captures.get(provider_id) or provider.get("provider_usage_capture") or {})
        verification_steps = _provider_verification_steps(
            provider,
            evidence_posture=evidence_posture,
            provider_usage_capture=provider_usage_capture,
            vault_litellm_env_audit=vault_litellm_env_audit,
        )
        verification_queue.append(
            {
                "provider_id": provider_id,
                "label": str(provider.get("label") or provider_id),
                "evidence_posture": evidence_posture,
                "pricing_truth_label": pricing_truth_label,
                "next_verification": verification_steps[0],
                "verification_steps": verification_steps,
                "capture_status": str(provider_usage_capture.get("status") or "") or None,
                "capture_observed_at": str(provider_usage_capture.get("observed_at") or "") or None,
                "missing_env_names": _provider_env_names_for_audit(
                    provider,
                    vault_litellm_env_audit,
                    "container_missing_env_names",
                ),
                "present_env_names": _provider_env_names_for_audit(
                    provider,
                    vault_litellm_env_audit,
                    "container_present_env_names",
                ),
                "priority": priority,
            }
        )

    verification_queue.sort(
        key=lambda item: (
            99 if item.get("priority") is None else int(item.get("priority")),
            str(item.get("label") or ""),
        )
    )
    auth_failed_provider_ids = [
        str(item.get("provider_id") or "")
        for item in verification_queue
        if str(item.get("evidence_posture") or "") == "vault_provider_specific_auth_failed"
    ]
    cost_unverified_provider_ids = [
        str(item.get("provider_id") or "")
        for item in verification_queue
        if str(item.get("evidence_posture") or "") == "live_burn_observed_cost_unverified"
    ]
    supported_tool_unverified_provider_ids = [
        str(item.get("provider_id") or "")
        for item in verification_queue
        if str(item.get("evidence_posture") or "") == "supported_tool_subscription_unverified"
    ]

    return {
        "provider_count": len(providers),
        "latest_provider_capture_count": len(latest_captures),
        "capture_status_counts": capture_status_counts,
        "provider_specific_observed_count": capture_status_counts.get("observed", 0),
        "provider_specific_auth_failed_count": capture_status_counts.get("auth_failed", 0),
        "provider_specific_request_failed_count": capture_status_counts.get("request_failed", 0),
        "weak_lane_count": len(verification_queue),
        "weak_provider_ids": weak_provider_ids,
        "weak_posture_counts": weak_posture_counts,
        "auth_failed_provider_ids": auth_failed_provider_ids,
        "cost_unverified_provider_ids": cost_unverified_provider_ids,
        "supported_tool_unverified_provider_ids": supported_tool_unverified_provider_ids,
        "verification_queue": verification_queue,
    }


def build_launch_governance_posture() -> dict[str, Any]:
    activation, current_phase = get_current_autonomy_phase()
    current_phase_id = str(activation.get("current_phase_id") or "").strip()
    next_phase = get_next_autonomy_phase(activation, phase_id=current_phase_id)
    next_phase_id = str(next_phase.get("id") or "").strip() or None
    current_phase_blockers = [
        str(item.get("id") or "").strip()
        for item in get_unmet_autonomy_prerequisites(activation, phase_id=current_phase_id)
        if str(item.get("id") or "").strip()
    ]
    next_phase_blockers = (
        [
            str(item.get("id") or "").strip()
            for item in get_unmet_autonomy_prerequisites(activation, phase_id=next_phase_id)
            if str(item.get("id") or "").strip()
        ]
        if next_phase_id
        else []
    )

    runbooks = get_operator_runbooks_registry()
    registered_runbook_ids = {
        str(entry.get("id") or "").strip()
        for entry in runbooks.get("runbooks", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    missing_runbook_ids = sorted(
        runbook_id for runbook_id in REQUIRED_LAUNCH_RUNBOOK_IDS if runbook_id not in registered_runbook_ids
    )

    provider_evidence_issue: str | None = None
    provider_usage_evidence_path = _provider_usage_evidence_path()
    provider_usage_evidence_payload, provider_usage_issue = _load_json_artifact(provider_usage_evidence_path)
    if provider_usage_issue == "missing":
        provider_evidence_issue = "providers:evidence_missing"
    elif provider_usage_issue == "unreadable":
        provider_evidence_issue = "providers:evidence_unreadable"

    vault_litellm_env_audit_path = _vault_litellm_env_audit_path()
    vault_litellm_env_audit_payload, _ = _load_json_artifact(vault_litellm_env_audit_path)
    provider_summary = _build_provider_launch_summary(
        evidence_payload=provider_usage_evidence_payload,
        vault_litellm_env_audit=vault_litellm_env_audit_payload,
    )

    launch_blockers: list[str] = []
    issues: list[str] = []
    if provider_evidence_issue:
        launch_blockers.append(provider_evidence_issue)
        issues.append(provider_evidence_issue)
    launch_blockers.extend(f"autonomy:current_phase:{item}" for item in current_phase_blockers)
    issues.extend(f"autonomy:current_phase:{item}" for item in current_phase_blockers)
    launch_blockers.extend(f"autonomy:next_phase:{item}" for item in next_phase_blockers)
    issues.extend(f"autonomy:next_phase:{item}" for item in next_phase_blockers)
    launch_blockers.extend(f"runbook:{item}" for item in missing_runbook_ids)
    issues.extend(f"runbook:{item}" for item in missing_runbook_ids)

    return {
        "activation_state": str(activation.get("activation_state") or "unknown"),
        "current_phase_id": current_phase_id or None,
        "current_phase_status": str(current_phase.get("status") or "unknown"),
        "next_phase_id": next_phase_id,
        "next_phase_status": str(next_phase.get("status") or "complete") if next_phase_id else None,
        "current_phase_blockers": current_phase_blockers,
        "next_phase_blockers": next_phase_blockers,
        "provider_evidence": {
            "path": str(provider_usage_evidence_path),
            "exists": provider_usage_evidence_path.exists(),
            "capture_count": len(list((provider_usage_evidence_payload or {}).get("captures") or [])),
            "latest_provider_capture_count": provider_summary["latest_provider_capture_count"],
            "observed_count": provider_summary["provider_specific_observed_count"],
            "auth_failed_count": provider_summary["provider_specific_auth_failed_count"],
            "request_failed_count": provider_summary["provider_specific_request_failed_count"],
            "provider_count": provider_summary["provider_count"],
            "weak_lane_count": provider_summary["weak_lane_count"],
            "weak_provider_ids": provider_summary["weak_provider_ids"],
            "weak_posture_counts": provider_summary["weak_posture_counts"],
            "capture_status_counts": provider_summary["capture_status_counts"],
            "auth_failed_provider_ids": provider_summary["auth_failed_provider_ids"],
            "cost_unverified_provider_ids": provider_summary["cost_unverified_provider_ids"],
            "supported_tool_unverified_provider_ids": provider_summary["supported_tool_unverified_provider_ids"],
            "verification_queue": provider_summary["verification_queue"],
            "vault_litellm_env_audit_path": str(vault_litellm_env_audit_path),
            "vault_litellm_env_audit_exists": vault_litellm_env_audit_path.exists(),
        },
        "required_runbook_count": len(REQUIRED_LAUNCH_RUNBOOK_IDS),
        "registered_runbook_count": len(registered_runbook_ids),
        "missing_runbook_ids": missing_runbook_ids,
        "launch_blockers": launch_blockers,
        "issues": issues,
    }
