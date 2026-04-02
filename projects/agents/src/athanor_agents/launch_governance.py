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


def _provider_usage_evidence_path() -> Path:
    filename = "provider-usage-evidence.json"
    for directory in _candidate_truth_inventory_dirs():
        candidate = directory / filename
        if candidate.exists():
            return candidate
    first_dir = next(iter(_candidate_truth_inventory_dirs()), Path("/output/reports/truth-inventory"))
    return first_dir / filename


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

    provider_capture_count = 0
    provider_observed_count = 0
    provider_auth_failed_count = 0
    provider_evidence_issue: str | None = None
    provider_usage_evidence_path = _provider_usage_evidence_path()
    if not provider_usage_evidence_path.exists():
        provider_evidence_issue = "providers:evidence_missing"
    else:
        try:
            payload = json.loads(provider_usage_evidence_path.read_text(encoding="utf-8"))
            captures = payload.get("captures", [])
            if isinstance(captures, list):
                provider_capture_count = len(captures)
                provider_observed_count = sum(
                    1 for item in captures if isinstance(item, dict) and str(item.get("status") or "") == "observed"
                )
                provider_auth_failed_count = sum(
                    1 for item in captures if isinstance(item, dict) and str(item.get("status") or "") == "auth_failed"
                )
        except Exception:
            provider_evidence_issue = "providers:evidence_unreadable"

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
            "capture_count": provider_capture_count,
            "observed_count": provider_observed_count,
            "auth_failed_count": provider_auth_failed_count,
        },
        "required_runbook_count": len(REQUIRED_LAUNCH_RUNBOOK_IDS),
        "registered_runbook_count": len(registered_runbook_ids),
        "missing_runbook_ids": missing_runbook_ids,
        "launch_blockers": launch_blockers,
        "issues": issues,
    }
