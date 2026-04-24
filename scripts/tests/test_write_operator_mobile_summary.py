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


def test_build_payload_emits_phone_safe_operator_summary_from_canonical_truth() -> None:
    module = _load_module(
        f"write_operator_mobile_summary_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_operator_mobile_summary.py",
    )

    payload = module.build_payload(
        steady_state={
            "intervention_level": "review_recommended",
            "intervention_label": "Review recommended",
            "needs_you": True,
            "current_work": {"task_title": "Validation and Publication"},
        },
        blocker_map={
            "objective": "closure_debt",
            "proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day", "runtime_parity"]},
        },
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "closure_debt",
            "controller_status": "running",
            "active_pass_id": "continuity-pass-123",
            "typed_brake": None,
        },
        runtime_parity={"drift_class": "proof_workspace_drift", "detail": "FOUNDRY behind DESK"},
        result_evidence={"threshold_progress": 0, "threshold_required": 5},
        stable_operating_day={"covered_window_hours": 0.0, "required_window_hours": 24},
        capability_scorecard={
            "required_now_green": False,
            "blocking_domain_ids": ["observe_truth", "verify_and_credit"],
        },
        supervisor_health={"health_status": "degraded"},
        project_output_readiness={
            "top_priority_project_id": "eoq",
            "top_priority_project_label": "Empire of Broken Queens",
            "factory_operating_mode": "core_runtime_hold",
            "summary": {
                "broad_project_factory_ready": False,
                "eligible_now_count": 0,
            },
        },
        project_output_proof={
            "accepted_project_output_count": 1,
            "distinct_project_count": 1,
            "pending_candidate_count": 1,
            "pending_hybrid_acceptance_count": 1,
            "latest_pending_candidate": {
                "project_id": "eoq",
                "deliverable_kind": "content_artifact",
            },
            "stage_status": {
                "met": False,
                "remaining_project_outputs": 2,
            },
            "latest_accepted_entry": {
                "project_id": "eoq",
                "deliverable_kind": "content_artifact",
            },
        },
        autonomous_value_proof={
            "accepted_operator_value_count": 2,
            "accepted_product_value_count": 1,
            "latest_accepted_entry": {
                "value_class": "product_value",
                "beneficiary_surface": "dashboard",
                "deliverable_kind": "ui_change",
            },
            "stage_status": {
                "operator_value": {"met": False, "remaining_required": 1},
                "product_value": {"met": False, "remaining_required": 1},
            },
        },
    )

    assert payload["attention_level"] == "review_recommended"
    assert payload["controller"]["host"] == "dev"
    assert payload["runtime_parity"]["drift_class"] == "proof_workspace_drift"
    assert payload["autonomous_value"]["accepted_operator_value_count"] == 2
    assert payload["autonomous_value"]["latest_beneficiary_surface"] == "dashboard"
    assert payload["project_factory"]["top_priority_project_id"] == "eoq"
    assert payload["project_factory"]["accepted_project_output_count"] == 1
    assert payload["project_factory"]["pending_candidate_count"] == 1
    assert payload["project_factory"]["pending_hybrid_acceptance_count"] == 1
    assert payload["project_factory"]["latest_pending_project_id"] == "eoq"
    assert payload["available_actions"] == ["observe", "approve", "deny", "pause", "resume", "inspect", "nudge"]


def test_build_payload_prefers_steady_state_next_target_and_runtime_packet_visibility() -> None:
    module = _load_module(
        f"write_operator_mobile_summary_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_operator_mobile_summary.py",
    )

    payload = module.build_payload(
        steady_state={
            "intervention_level": "approval_required",
            "intervention_label": "Approval required",
            "needs_you": True,
            "current_work": {"task_title": "Capacity and Harvest Truth"},
            "only_typed_brakes_remain": True,
            "next_operator_action": "Review the runtime packet inbox and execute or approve the next bounded mutation packet.",
            "next_target": {
                "kind": "runtime_packet",
                "family_id": "runtime-packet-inbox",
                "family_title": "Runtime Packet Inbox",
                "subtranche_id": "workshop-ulrich-energy-retirement-packet",
                "subtranche_title": "WORKSHOP retired ulrich-energy runtime retirement packet",
                "approval_gated": True,
            },
            "runtime_packet_next": {
                "subtranche_id": "workshop-ulrich-energy-retirement-packet",
                "subtranche_title": "WORKSHOP retired ulrich-energy runtime retirement packet",
                "host": "workshop",
                "approval_type": "runtime_host_reconfiguration",
            },
        },
        blocker_map={
            "objective": "result_backed_throughput",
            "proof_gate": {"open": False, "blocking_check_ids": ["stable_operating_day"]},
        },
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "closure_debt",
            "controller_status": "idle",
            "active_pass_id": None,
            "typed_brake": None,
            "next_target": {
                "family_id": "tenant-product-lanes",
                "family_title": "Tenant Product Lanes",
            },
        },
        runtime_parity={"drift_class": "generated_surface_drift", "detail": "managed truth regenerated"},
        result_evidence={"threshold_progress": 16, "threshold_required": 5},
        stable_operating_day={"covered_window_hours": 1.0, "required_window_hours": 24},
        capability_scorecard={"required_now_green": True, "blocking_domain_ids": []},
        supervisor_health={"health_status": "healthy"},
        project_output_readiness={
            "top_priority_project_id": "eoq",
            "top_priority_project_label": "Empire of Broken Queens",
            "factory_operating_mode": "core_runtime_hold",
            "summary": {"broad_project_factory_ready": False, "eligible_now_count": 0},
        },
        project_output_proof={
            "accepted_project_output_count": 3,
            "distinct_project_count": 3,
            "pending_candidate_count": 0,
            "pending_hybrid_acceptance_count": 0,
            "stage_status": {"met": True, "remaining_project_outputs": 0},
            "latest_accepted_entry": {"project_id": "lawnsignal", "deliverable_kind": "feature_tranche"},
        },
        autonomous_value_proof={
            "accepted_operator_value_count": 3,
            "accepted_product_value_count": 5,
            "latest_accepted_entry": {
                "value_class": "product_value",
                "beneficiary_surface": "consumer_web_companion",
                "deliverable_kind": "feature_tranche",
            },
            "stage_status": {
                "operator_value": {"met": True, "remaining_required": 0},
                "product_value": {"met": True, "remaining_required": 0},
            },
        },
    )

    assert payload["next_target"]["family_id"] == "runtime-packet-inbox"
    assert payload["only_typed_brakes_remain"] is True
    assert payload["runtime_packet_next"]["host"] == "workshop"
    assert payload["next_operator_action"] == "Review the runtime packet inbox and execute or approve the next bounded mutation packet."
