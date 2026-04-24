from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_payload_materializes_stable_failure_identities_without_churn() -> None:
    module = _load_module(
        f"write_autonomy_failure_ledger_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomy_failure_ledger.py",
    )

    payload = module.build_payload(
        blocker_map={
            "objective": "queue_backed_throughput",
            "queue": {"dispatchable": 0},
            "proof_gate": {"checks": [{"id": "validator_and_contract_healer", "met": False, "detail": "validator red"}]},
        },
        value_throughput={
            "stale_claim_count": 2,
            "review_debt": {"count": 0},
            "reconciliation": {"issue_count": 0},
        },
        continuity_state={
            "consecutive_no_delta_passes": 6,
            "last_skip_reason": "backoff_active",
        },
        runtime_parity={
            "drift_class": "proof_workspace_drift",
            "detail": "Foundry proof workspace hash is behind DESK.",
        },
        result_evidence={
            "threshold_progress": 0,
            "result_backed_completion_count": 0,
            "review_backed_output_count": 0,
        },
    )

    failure_ids = [item["failure_id"] for item in payload["failures"]]
    assert "stale_claim_recurrence" in failure_ids
    assert "validator_drift" in failure_ids
    assert "proof_workspace_drift" in failure_ids
    assert "no_delta_cycles" in failure_ids
    assert payload["materialized_outputs"][0]["mapped_family"] == "research_audit"


def test_build_payload_suppresses_materialization_when_dispatchable_work_or_review_debt_is_present() -> None:
    module = _load_module(
        f"write_autonomy_failure_ledger_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomy_failure_ledger.py",
    )

    payload = module.build_payload(
        blocker_map={
            "objective": "queue_backed_throughput",
            "queue": {"dispatchable": 3},
            "proof_gate": {"checks": []},
        },
        value_throughput={
            "stale_claim_count": 1,
            "review_debt": {"count": 2},
            "reconciliation": {"issue_count": 0},
        },
        continuity_state={"consecutive_no_delta_passes": 0},
        runtime_parity={"drift_class": "clean", "detail": "clean"},
        result_evidence={"threshold_progress": 0},
    )

    assert payload["materialized_outputs"] == []
    assert payload["suppressed_by_queue_priority"] is True
    assert payload["suppressed_by_review_debt"] is True


def test_build_payload_accounts_for_valid_but_not_useful_autonomous_value_failures() -> None:
    module = _load_module(
        f"write_autonomy_failure_ledger_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_autonomy_failure_ledger.py",
    )

    payload = module.build_payload(
        blocker_map={
            "objective": "queue_backed_throughput",
            "queue": {"dispatchable": 0},
            "proof_gate": {"checks": []},
        },
        value_throughput={
            "stale_claim_count": 0,
            "review_debt": {"count": 0},
            "reconciliation": {"issue_count": 0},
        },
        continuity_state={"consecutive_no_delta_passes": 0},
        runtime_parity={"drift_class": "clean", "detail": "clean"},
        result_evidence={"threshold_progress": 2},
        autonomous_value_proof={
            "failure_counts": {
                "bookkeeping_only": 1,
                "operator_steered": 1,
                "deliverable_present_but_not_accepted": 2,
            }
        },
    )

    failure_ids = [item["failure_id"] for item in payload["failures"]]
    assert "bookkeeping_only" in failure_ids
    assert "operator_steered" in failure_ids
    assert "deliverable_present_but_not_accepted" in failure_ids
