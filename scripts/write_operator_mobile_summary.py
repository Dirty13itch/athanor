#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
STEADY_STATE_STATUS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
STABLE_OPERATING_DAY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "stable-operating-day.json"
SYSTEM_CAPABILITY_SCORECARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "system-capability-scorecard.json"
CONTINUITY_SUPERVISOR_HEALTH_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-supervisor-health.json"
AUTONOMOUS_VALUE_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomous-value-proof.json"
PROJECT_OUTPUT_READINESS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-readiness.json"
PROJECT_OUTPUT_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "project-output-proof.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "operator-mobile-summary.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_payload(
    *,
    steady_state: dict[str, Any],
    blocker_map: dict[str, Any],
    continuity_state: dict[str, Any],
    runtime_parity: dict[str, Any],
    result_evidence: dict[str, Any],
    stable_operating_day: dict[str, Any],
    capability_scorecard: dict[str, Any],
    supervisor_health: dict[str, Any],
    project_output_readiness: dict[str, Any],
    project_output_proof: dict[str, Any],
    autonomous_value_proof: dict[str, Any],
) -> dict[str, Any]:
    next_target = dict(steady_state.get("next_target") or continuity_state.get("next_target") or {})
    runtime_packet_next = dict(steady_state.get("runtime_packet_next") or {})
    return {
        "generated_at": _iso_now(),
        "attention_level": str(steady_state.get("intervention_level") or "unknown"),
        "attention_label": str(steady_state.get("intervention_label") or "unknown"),
        "needs_you": bool(steady_state.get("needs_you")),
        "current_objective": str(blocker_map.get("objective") or "unknown"),
        "current_work": dict(steady_state.get("current_work") or {}),
        "next_target": next_target,
        "controller": {
            "host": str(continuity_state.get("controller_host") or "dev"),
            "mode": str(continuity_state.get("controller_mode") or "unknown"),
            "status": str(continuity_state.get("controller_status") or "unknown"),
            "active_pass_id": continuity_state.get("active_pass_id"),
            "typed_brake": continuity_state.get("typed_brake"),
        },
        "only_typed_brakes_remain": bool(steady_state.get("only_typed_brakes_remain")),
        "next_operator_action": steady_state.get("next_operator_action"),
        "runtime_packet_next": runtime_packet_next,
        "runtime_parity": {
            "drift_class": str(runtime_parity.get("drift_class") or "unknown"),
            "detail": runtime_parity.get("detail"),
        },
        "proof_gate": {
            "open": bool((blocker_map.get("proof_gate") or {}).get("open")),
            "blocking_check_ids": list((blocker_map.get("proof_gate") or {}).get("blocking_check_ids") or []),
            "threshold_progress": int(result_evidence.get("threshold_progress") or 0),
            "threshold_required": int(result_evidence.get("threshold_required") or 5),
            "covered_window_hours": float(stable_operating_day.get("covered_window_hours") or 0.0),
            "required_window_hours": int(stable_operating_day.get("required_window_hours") or 24),
        },
        "system_capabilities": {
            "required_now_green": bool(capability_scorecard.get("required_now_green")),
            "blocking_domain_ids": list(capability_scorecard.get("blocking_domain_ids") or []),
        },
        "supervisor_health": {
            "health_status": str(supervisor_health.get("health_status") or "unknown"),
            "detail": supervisor_health.get("detail"),
        },
        "project_factory": {
            "factory_operating_mode": str(project_output_readiness.get("factory_operating_mode") or "unknown"),
            "top_priority_project_id": str(project_output_readiness.get("top_priority_project_id") or "none"),
            "top_priority_project_label": str(project_output_readiness.get("top_priority_project_label") or "none"),
            "broad_project_factory_ready": bool(
                dict(project_output_readiness.get("summary") or {}).get("broad_project_factory_ready")
            ),
            "eligible_now_count": int(dict(project_output_readiness.get("summary") or {}).get("eligible_now_count") or 0),
            "accepted_project_output_count": int(project_output_proof.get("accepted_project_output_count") or 0),
            "distinct_project_count": int(project_output_proof.get("distinct_project_count") or 0),
            "pending_candidate_count": int(project_output_proof.get("pending_candidate_count") or 0),
            "pending_hybrid_acceptance_count": int(project_output_proof.get("pending_hybrid_acceptance_count") or 0),
            "project_output_stage_met": bool(dict(project_output_proof.get("stage_status") or {}).get("met")),
            "remaining_project_outputs": int(
                dict(project_output_proof.get("stage_status") or {}).get("remaining_project_outputs") or 0
            ),
            "latest_pending_project_id": str(
                dict(project_output_proof.get("latest_pending_candidate") or {}).get("project_id") or "none"
            ),
            "latest_pending_deliverable_kind": str(
                dict(project_output_proof.get("latest_pending_candidate") or {}).get("deliverable_kind") or "none"
            ),
            "latest_project_id": str(
                dict(project_output_proof.get("latest_accepted_entry") or {}).get("project_id") or "none"
            ),
            "latest_deliverable_kind": str(
                dict(project_output_proof.get("latest_accepted_entry") or {}).get("deliverable_kind") or "none"
            ),
        },
        "autonomous_value": {
            "accepted_operator_value_count": int(autonomous_value_proof.get("accepted_operator_value_count") or 0),
            "accepted_product_value_count": int(autonomous_value_proof.get("accepted_product_value_count") or 0),
            "operator_value_stage_met": bool(
                dict(autonomous_value_proof.get("stage_status") or {})
                .get("operator_value", {})
                .get("met")
            ),
            "product_value_stage_met": bool(
                dict(autonomous_value_proof.get("stage_status") or {})
                .get("product_value", {})
                .get("met")
            ),
            "latest_value_class": str(
                dict(autonomous_value_proof.get("latest_accepted_entry") or {}).get("value_class") or "none"
            ),
            "latest_beneficiary_surface": str(
                dict(autonomous_value_proof.get("latest_accepted_entry") or {}).get("beneficiary_surface") or "none"
            ),
            "latest_deliverable_kind": str(
                dict(autonomous_value_proof.get("latest_accepted_entry") or {}).get("deliverable_kind") or "none"
            ),
            "remaining_operator_value_required": int(
                dict(autonomous_value_proof.get("stage_status") or {})
                .get("operator_value", {})
                .get("remaining_required")
                or 0
            ),
            "remaining_product_value_required": int(
                dict(autonomous_value_proof.get("stage_status") or {})
                .get("product_value", {})
                .get("remaining_required")
                or 0
            ),
        },
        "available_actions": ["observe", "approve", "deny", "pause", "resume", "inspect", "nudge"],
        "source_artifacts": {
            "steady_state_status": str(STEADY_STATE_STATUS_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "stable_operating_day": str(STABLE_OPERATING_DAY_PATH),
            "system_capability_scorecard": str(SYSTEM_CAPABILITY_SCORECARD_PATH),
            "continuity_supervisor_health": str(CONTINUITY_SUPERVISOR_HEALTH_PATH),
            "project_output_readiness": str(PROJECT_OUTPUT_READINESS_PATH),
            "project_output_proof": str(PROJECT_OUTPUT_PROOF_PATH),
            "autonomous_value_proof": str(AUTONOMOUS_VALUE_PROOF_PATH),
            "operator_mobile_summary": str(OUTPUT_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor phone-safe operator summary artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when operator-mobile-summary.json is stale.")
    args = parser.parse_args()

    payload = build_payload(
        steady_state=_load_optional_json(STEADY_STATE_STATUS_PATH),
        blocker_map=_load_optional_json(BLOCKER_MAP_PATH),
        continuity_state=_load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH),
        runtime_parity=_load_optional_json(RUNTIME_PARITY_PATH),
        result_evidence=_load_optional_json(RESULT_EVIDENCE_LEDGER_PATH),
        stable_operating_day=_load_optional_json(STABLE_OPERATING_DAY_PATH),
        capability_scorecard=_load_optional_json(SYSTEM_CAPABILITY_SCORECARD_PATH),
        supervisor_health=_load_optional_json(CONTINUITY_SUPERVISOR_HEALTH_PATH),
        project_output_readiness=_load_optional_json(PROJECT_OUTPUT_READINESS_PATH),
        project_output_proof=_load_optional_json(PROJECT_OUTPUT_PROOF_PATH),
        autonomous_value_proof=_load_optional_json(AUTONOMOUS_VALUE_PROOF_PATH),
    )
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if args.check:
        if current != rendered:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
