#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "config" / "automation-backbone" / "system-capability-contract.json"
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
AUTONOMY_FAILURE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomy-failure-ledger.json"
CONTROLLER_OF_CONTROLLERS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "controller-of-controllers.json"
STEADY_STATE_STATUS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
OPERATOR_MOBILE_SUMMARY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "operator-mobile-summary.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "system-capability-scorecard.json"


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
    blocker_map: dict[str, Any],
    runtime_parity: dict[str, Any],
    result_evidence: dict[str, Any],
    failure_ledger: dict[str, Any],
    controller_of_controllers: dict[str, Any],
    steady_state: dict[str, Any],
    operator_mobile_summary: dict[str, Any],
) -> dict[str, Any]:
    contract = _load_optional_json(CONTRACT_PATH)
    domains = [dict(item) for item in contract.get("domains", []) if isinstance(item, dict)]

    proof_gate = dict(blocker_map.get("proof_gate") or {})
    drift_class = str(runtime_parity.get("drift_class") or "unknown")
    threshold_progress = int(result_evidence.get("threshold_progress") or 0)
    failure_count = int(failure_ledger.get("failure_count") or 0)
    failure_learning_suppressed = bool(
        failure_ledger.get("suppressed_by_queue_priority") or failure_ledger.get("suppressed_by_review_debt")
    )
    primary_lane = str(controller_of_controllers.get("primary_lane") or "")
    intervention_level = str(steady_state.get("intervention_level") or "")
    mobile_actions = operator_mobile_summary.get("available_actions", [])

    scored_domains: list[dict[str, Any]] = []
    blocking_domain_ids: list[str] = []
    for domain in domains:
        domain_id = str(domain.get("id") or "")
        required_now = bool(domain.get("required_now"))
        gated_future = bool(domain.get("gated_future"))
        status = "ready"
        detail = "Capability contract is satisfied."

        if gated_future:
            status = "gated_future"
            detail = "Capability remains intentionally gated behind later proof."
        elif domain_id == "observe_truth" and drift_class not in {"clean", "generated_surface_drift"}:
            status = "blocking"
            detail = f"Runtime parity is `{drift_class}`."
        elif domain_id == "decide_next_work" and not blocker_map.get("objective"):
            status = "blocking"
            detail = "Blocker map objective is unavailable."
        elif domain_id == "act_within_scope" and primary_lane not in {
            "athanor_core_closure",
            "athanor_core_throughput",
            "proof_gate_holding_pattern",
        }:
            status = "blocking"
            detail = "Primary controller lane is unavailable."
        elif domain_id == "verify_and_credit" and threshold_progress <= 0:
            status = "blocking"
            detail = "No result-backed or review-backed closure is creditable yet."
        elif domain_id == "learn_from_failures" and failure_count <= 0:
            if failure_learning_suppressed:
                detail = "Failure-learning lane is quiescent because higher-priority closure work is still active."
            else:
                status = "blocking"
                detail = "Failure-learning ledger has not materialized any failures yet."
        elif domain_id == "govern_boundaries" and not primary_lane:
            status = "blocking"
            detail = "Controller-of-controllers primary lane is unavailable."
        elif domain_id == "expose_operator_surface" and (not intervention_level or not mobile_actions):
            status = "blocking"
            detail = "Operator surfaces are missing desktop or mobile truth."

        if required_now and status != "ready":
            blocking_domain_ids.append(domain_id)
        scored_domains.append(
            {
                "id": domain_id,
                "label": str(domain.get("label") or domain_id),
                "required_now": required_now,
                "gated_future": gated_future,
                "status": status,
                "detail": detail,
                "proof_surfaces": list(domain.get("proof_surfaces") or []),
            }
        )

    return {
        "generated_at": _iso_now(),
        "required_now_ids": list(contract.get("required_now") or []),
        "gated_future_ids": list(contract.get("gated_future") or []),
        "required_now_green": not blocking_domain_ids,
        "proof_gate_open": bool(proof_gate.get("open")),
        "blocking_domain_ids": blocking_domain_ids,
        "domains": scored_domains,
        "source_artifacts": {
            "system_capability_contract": str(CONTRACT_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "autonomy_failure_ledger": str(AUTONOMY_FAILURE_LEDGER_PATH),
            "controller_of_controllers": str(CONTROLLER_OF_CONTROLLERS_PATH),
            "steady_state_status": str(STEADY_STATE_STATUS_PATH),
            "operator_mobile_summary": str(OPERATOR_MOBILE_SUMMARY_PATH),
            "system_capability_scorecard": str(OUTPUT_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor top-level capability scorecard.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when system-capability-scorecard.json is stale.")
    args = parser.parse_args()

    payload = build_payload(
        blocker_map=_load_optional_json(BLOCKER_MAP_PATH),
        runtime_parity=_load_optional_json(RUNTIME_PARITY_PATH),
        result_evidence=_load_optional_json(RESULT_EVIDENCE_LEDGER_PATH),
        failure_ledger=_load_optional_json(AUTONOMY_FAILURE_LEDGER_PATH),
        controller_of_controllers=_load_optional_json(CONTROLLER_OF_CONTROLLERS_PATH),
        steady_state=_load_optional_json(STEADY_STATE_STATUS_PATH),
        operator_mobile_summary=_load_optional_json(OPERATOR_MOBILE_SUMMARY_PATH),
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
