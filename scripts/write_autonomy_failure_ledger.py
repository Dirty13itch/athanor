#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
VALUE_THROUGHPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
RUNTIME_PARITY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-parity.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
AUTONOMOUS_VALUE_PROOF_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomous-value-proof.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "autonomy-failure-ledger.json"


FAILURE_MAP = {
    "stale_claim_recurrence": ("research_audit", "Dispatch and stale-claim recurrence analysis"),
    "validator_drift": ("research_audit", "Validator drift analysis"),
    "proof_workspace_drift": ("research_audit", "Proof workspace parity repair"),
    "runtime_ownership_drift": ("maintenance", "Runtime ownership repair"),
    "no_delta_cycles": ("research_audit", "No-delta continuity churn analysis"),
    "result_credit_rejection": ("builder", "Result-credit path repair"),
    "approval_stop_recurrence": ("review", "Approval-stop review packet"),
    "bookkeeping_only": ("maintenance", "Replace bookkeeping-only output with a bounded deliverable"),
    "control_plane_only": ("maintenance", "Replace control-plane-only output with accepted operator or product value"),
    "operator_steered": ("review", "Convert steered work into an approval-backed value packet"),
    "verification_passed_but_no_deliverable": ("builder", "Attach a concrete deliverable to verified work"),
    "deliverable_present_but_not_accepted": ("review", "Close the acceptance gap on a produced deliverable"),
}


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
    value_throughput: dict[str, Any],
    continuity_state: dict[str, Any],
    runtime_parity: dict[str, Any],
    result_evidence: dict[str, Any],
    autonomous_value_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    autonomous_value_proof = dict(autonomous_value_proof or {})

    stale_claim_count = int(value_throughput.get("stale_claim_count") or 0)
    if stale_claim_count > 0:
        failures.append(
            {
                "failure_id": "stale_claim_recurrence",
                "count": stale_claim_count,
                "detail": f"stale_claim_count={stale_claim_count}",
            }
        )

    proof_checks = blocker_map.get("proof_gate", {}).get("checks", [])
    validator_check = next(
        (
            dict(item)
            for item in proof_checks
            if isinstance(item, dict) and str(item.get("id") or "") == "validator_and_contract_healer"
        ),
        {},
    )
    if validator_check and not bool(validator_check.get("met")):
        failures.append(
            {
                "failure_id": "validator_drift",
                "count": 1,
                "detail": str(validator_check.get("detail") or "validator red"),
            }
        )

    drift_class = str(runtime_parity.get("drift_class") or "")
    if drift_class in {"proof_workspace_drift", "runtime_ownership_drift"}:
        failures.append(
            {
                "failure_id": drift_class,
                "count": 1,
                "detail": str(runtime_parity.get("detail") or drift_class),
            }
        )

    no_delta_cycles = int(continuity_state.get("consecutive_no_delta_passes") or 0)
    if no_delta_cycles >= 6:
        failures.append(
            {
                "failure_id": "no_delta_cycles",
                "count": no_delta_cycles,
                "detail": f"consecutive_no_delta_passes={no_delta_cycles}",
            }
        )

    if int(result_evidence.get("threshold_progress") or 0) <= 0:
        failures.append(
            {
                "failure_id": "result_credit_rejection",
                "count": 1,
                "detail": "No result-backed or review-backed closure is currently creditable.",
            }
        )

    approval_skip_reason = str(continuity_state.get("last_skip_reason") or "")
    if approval_skip_reason == "approval_gated_runtime_packet":
        failures.append(
            {
                "failure_id": "approval_stop_recurrence",
                "count": 1,
                "detail": approval_skip_reason,
            }
        )

    failure_counts = dict(autonomous_value_proof.get("failure_counts") or {})
    for failure_id in (
        "bookkeeping_only",
        "control_plane_only",
        "operator_steered",
        "verification_passed_but_no_deliverable",
        "deliverable_present_but_not_accepted",
    ):
        count = int(failure_counts.get(failure_id) or 0)
        if count <= 0:
            continue
        failures.append(
            {
                "failure_id": failure_id,
                "count": count,
                "detail": f"{failure_id}={count}",
            }
        )

    dispatchable_queue = int((blocker_map.get("queue") or {}).get("dispatchable") or 0)
    review_debt_count = int((value_throughput.get("review_debt") or {}).get("count") or 0)
    suppressed_by_queue_priority = dispatchable_queue > 0
    suppressed_by_review_debt = review_debt_count > 0

    materialized_outputs: list[dict[str, Any]] = []
    if not suppressed_by_queue_priority and not suppressed_by_review_debt:
        for failure in failures:
            mapped_family, title = FAILURE_MAP[failure["failure_id"]]
            materialized_outputs.append(
                {
                    "failure_id": failure["failure_id"],
                    "mapped_family": mapped_family,
                    "title": title,
                }
            )

    for failure in failures:
        mapped_family, _ = FAILURE_MAP[failure["failure_id"]]
        failure["mapped_family"] = mapped_family
        failure["suppressed"] = suppressed_by_queue_priority or suppressed_by_review_debt

    return {
        "generated_at": _iso_now(),
        "failure_count": len(failures),
        "failures": failures,
        "materialized_output_count": len(materialized_outputs),
        "materialized_outputs": materialized_outputs,
        "suppressed_by_queue_priority": suppressed_by_queue_priority,
        "suppressed_by_review_debt": suppressed_by_review_debt,
        "source_artifacts": {
            "blocker_map": str(BLOCKER_MAP_PATH),
            "value_throughput_scorecard": str(VALUE_THROUGHPUT_PATH),
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
            "runtime_parity": str(RUNTIME_PARITY_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "autonomous_value_proof": str(AUTONOMOUS_VALUE_PROOF_PATH),
            "autonomy_failure_ledger": str(OUTPUT_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor autonomy failure-learning ledger.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when autonomy-failure-ledger.json is stale.")
    args = parser.parse_args()

    payload = build_payload(
        blocker_map=_load_optional_json(BLOCKER_MAP_PATH),
        value_throughput=_load_optional_json(VALUE_THROUGHPUT_PATH),
        continuity_state=_load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH),
        runtime_parity=_load_optional_json(RUNTIME_PARITY_PATH),
        result_evidence=_load_optional_json(RESULT_EVIDENCE_LEDGER_PATH),
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
