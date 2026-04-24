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


def test_build_payload_scores_required_now_capabilities_from_live_truth() -> None:
    module = _load_module(
        f"write_system_capability_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_system_capability_scorecard.py",
    )

    payload = module.build_payload(
        blocker_map={
            "objective": "closure_debt",
            "proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day", "runtime_parity"]},
        },
        runtime_parity={"drift_class": "proof_workspace_drift"},
        result_evidence={"threshold_progress": 0, "threshold_required": 5},
        failure_ledger={"failure_count": 2, "materialized_outputs": []},
        controller_of_controllers={"primary_lane": "athanor_core_closure"},
        steady_state={"intervention_level": "review_recommended"},
        operator_mobile_summary={"available_actions": ["observe", "pause", "resume"]},
    )

    observe_truth = next(item for item in payload["domains"] if item["id"] == "observe_truth")
    verify_and_credit = next(item for item in payload["domains"] if item["id"] == "verify_and_credit")
    adopt_new = next(item for item in payload["domains"] if item["id"] == "adopt_new_capabilities")

    assert payload["required_now_green"] is False
    assert observe_truth["status"] == "blocking"
    assert verify_and_credit["status"] == "blocking"
    assert adopt_new["status"] == "gated_future"


def test_build_payload_treats_quiescent_failure_learning_as_ready() -> None:
    module = _load_module(
        f"write_system_capability_scorecard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_system_capability_scorecard.py",
    )

    payload = module.build_payload(
        blocker_map={
            "objective": "closure_debt",
            "proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day"]},
        },
        runtime_parity={"drift_class": "clean"},
        result_evidence={"threshold_progress": 6, "threshold_required": 5},
        failure_ledger={
            "failure_count": 0,
            "materialized_outputs": [],
            "suppressed_by_queue_priority": True,
            "suppressed_by_review_debt": False,
        },
        controller_of_controllers={"primary_lane": "athanor_core_closure"},
        steady_state={"intervention_level": "review_recommended"},
        operator_mobile_summary={"available_actions": ["observe", "pause", "resume"]},
    )

    learn_from_failures = next(item for item in payload["domains"] if item["id"] == "learn_from_failures")

    assert learn_from_failures["status"] == "ready"
    assert payload["blocking_domain_ids"] == []
    assert payload["required_now_green"] is True
