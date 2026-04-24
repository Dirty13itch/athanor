from __future__ import annotations

import importlib.util
import json
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


def test_load_or_build_execution_plan_refreshes_stale_existing_payload(tmp_path: Path) -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    execution_plan_path = tmp_path / "blocker-execution-plan.json"
    execution_plan_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-20T19:00:00+00:00",
                "selection_mode": "closure_debt",
                "next_target": {
                    "kind": "family",
                    "family_id": "reference-and-archive-prune",
                    "family_title": "Reference and Archive Prune",
                    "subtranche_id": None,
                    "subtranche_title": None,
                    "execution_class": "cash_now",
                    "approval_gated": False,
                    "external_blocked": False,
                },
                "families": [
                    {
                        "id": "reference-and-archive-prune",
                        "title": "Reference and Archive Prune",
                        "execution_class": "cash_now",
                        "match_count": 0,
                        "next_action": "",
                        "decomposition_required": False,
                        "decomposition_reasons": [],
                        "categories": ["reference/archive"],
                        "sample_paths": [],
                        "subtranches": [],
                        "next_subtranche_id": None,
                        "next_subtranche_title": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    module.BLOCKER_EXECUTION_PLAN_PATH = execution_plan_path

    blocker_map = {
        "objective": "result_backed_throughput",
        "remaining": {
            "family_ids": ["reference-and-archive-prune"],
            "families": [
                {
                    "id": "reference-and-archive-prune",
                    "title": "Reference and Archive Prune",
                    "execution_class": "cash_now",
                    "match_count": 0,
                    "next_action": "",
                    "decomposition_required": False,
                    "decomposition_reasons": [],
                    "categories": ["reference/archive"],
                    "sample_paths": [],
                }
            ],
        },
        "throughput_target": {
            "kind": "queue_backed_throughput",
            "family_id": "builder",
            "family_title": "Builder",
            "subtranche_id": "unscoped",
            "subtranche_title": None,
            "execution_class": "queue_backed_throughput",
            "approval_gated": False,
            "external_blocked": False,
        },
    }

    payload = module._load_or_build_execution_plan(blocker_map)

    assert payload["next_target"]["family_id"] == "builder"
    persisted = json.loads(execution_plan_path.read_text(encoding="utf-8"))
    assert persisted["next_target"]["family_id"] == "builder"


def _base_blocker_map():
    return {
        "generated_at": "2026-04-19T04:00:00+00:00",
        "runtime_packets": {"count": 0, "approval_gated_count": 0},
        "next_tranche": {
            "id": "control-plane-registry-and-routing",
            "title": "Control-Plane Registry and Routing",
        },
    }


def _base_execution_plan():
    return {
        "generated_at": "2026-04-19T04:00:00+00:00",
        "next_target": {
            "kind": "subtranche",
            "family_id": "control-plane-registry-and-routing",
            "family_title": "Control-Plane Registry and Routing",
            "subtranche_id": "registry-ledgers-and-matrices",
            "subtranche_title": "Registry Ledgers and Matrices",
            "execution_class": "program_slice",
            "approval_gated": False,
            "external_blocked": False,
        },
    }


def test_evaluate_begin_skips_when_pass_is_already_active() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    existing_state = {
        "controller_status": "running",
        "controller_pid": 4242,
        "active_pass_id": "pass-active",
        "active_family_id": "control-plane-registry-and-routing",
        "active_subtranche_id": "registry-ledgers-and-matrices",
        "started_at": "2026-04-19T04:10:00+00:00",
        "finished_at": None,
        "consecutive_no_delta_passes": 2,
        "last_blocker_map_hash": "same-blocker",
        "last_validator_hash": "same-validator",
        "last_value_throughput_hash": "same-throughput",
    }

    payload = module.evaluate_begin(
        existing_state=existing_state,
        blocker_map=_base_blocker_map(),
        execution_plan=_base_execution_plan(),
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        ralph={"stop_state": "none"},
        now_iso="2026-04-19T04:25:00+00:00",
        process_is_live=lambda pid: pid == 4242,
    )

    assert payload["controller_status"] == "skipped"
    assert payload["last_skip_reason"] == "pass_active"
    assert payload["active_pass_id"] == "pass-active"
    assert payload["active_family_id"] == "control-plane-registry-and-routing"
    assert payload["active_subtranche_id"] == "registry-ledgers-and-matrices"


def test_evaluate_begin_skips_recent_no_new_evidence_pass() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    blocker_map = _base_blocker_map()
    value_throughput = {"result_backed_completion_count": 0}
    validator_snapshot = {"success": True}
    existing_state = {
        "controller_status": "idle",
        "finished_at": "2026-04-19T04:18:00+00:00",
        "consecutive_no_delta_passes": 3,
        "last_blocker_map_hash": module._hash_payload(blocker_map),
        "last_validator_hash": module._hash_payload(validator_snapshot),
        "last_value_throughput_hash": module._hash_payload(value_throughput),
    }

    payload = module.evaluate_begin(
        existing_state=existing_state,
        blocker_map=blocker_map,
        execution_plan=_base_execution_plan(),
        value_throughput=value_throughput,
        validator_snapshot=validator_snapshot,
        ralph={"stop_state": "none"},
        now_iso="2026-04-19T04:20:00+00:00",
    )

    assert payload["controller_status"] == "skipped"
    assert payload["last_skip_reason"] == "recent_pass_no_new_evidence"
    assert payload["consecutive_no_delta_passes"] == 3


def test_evaluate_finish_sets_backoff_after_six_no_delta_passes() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    blocker_map = _base_blocker_map()
    value_throughput = {"result_backed_completion_count": 0}
    validator_snapshot = {"success": True}
    existing_state = {
        "controller_status": "running",
        "active_pass_id": "pass-123",
        "active_family_id": "control-plane-registry-and-routing",
        "active_subtranche_id": "registry-ledgers-and-matrices",
        "consecutive_no_delta_passes": 5,
        "last_blocker_map_hash": module._hash_payload(blocker_map),
        "last_validator_hash": module._hash_payload(validator_snapshot),
        "last_value_throughput_hash": module._hash_payload(value_throughput),
    }

    payload = module.evaluate_finish(
        existing_state=existing_state,
        blocker_map=blocker_map,
        value_throughput=value_throughput,
        validator_snapshot=validator_snapshot,
        now_iso="2026-04-19T04:30:00+00:00",
        pass_id="pass-123",
    )

    assert payload["controller_status"] == "idle"
    assert payload["consecutive_no_delta_passes"] == 6
    assert payload["backoff_until"] == "2026-04-19T04:45:00+00:00"
    assert payload["active_pass_id"] is None
    assert payload["active_family_id"] is None
    assert payload["active_subtranche_id"] is None


def test_evaluate_finish_clears_backoff_when_meaningful_delta_appears() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    existing_state = {
        "controller_status": "running",
        "active_pass_id": "pass-456",
        "active_family_id": "control-plane-registry-and-routing",
        "active_subtranche_id": "registry-ledgers-and-matrices",
        "consecutive_no_delta_passes": 6,
        "backoff_until": "2026-04-19T04:45:00+00:00",
        "last_blocker_map_hash": "older-blocker",
        "last_validator_hash": "older-validator",
        "last_value_throughput_hash": "older-throughput",
    }

    payload = module.evaluate_finish(
        existing_state=existing_state,
        blocker_map={**_base_blocker_map(), "generated_at": "2026-04-19T04:40:00+00:00"},
        value_throughput={"result_backed_completion_count": 1},
        validator_snapshot={"success": True, "summary": "fresh"},
        now_iso="2026-04-19T04:31:00+00:00",
        pass_id="pass-456",
    )

    assert payload["controller_status"] == "idle"
    assert payload["consecutive_no_delta_passes"] == 0
    assert payload["backoff_until"] is None
    assert payload["last_meaningful_delta_at"] == "2026-04-19T04:31:00+00:00"


def test_evaluate_begin_marks_external_or_approval_blockers_without_churn() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    payload = module.evaluate_begin(
        existing_state={},
        blocker_map={
            **_base_blocker_map(),
            "runtime_packets": {"count": 1, "approval_gated_count": 1},
        },
        execution_plan=_base_execution_plan(),
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        ralph={"stop_state": "external_block"},
        now_iso="2026-04-19T04:20:00+00:00",
    )

    assert payload["controller_status"] == "blocked"
    assert payload["last_skip_reason"] == "external_dependency_blocked"
    assert payload["active_pass_id"] is None
    assert payload["active_family_id"] == "control-plane-registry-and-routing"
    assert payload["active_subtranche_id"] == "registry-ledgers-and-matrices"


def test_evaluate_begin_starts_queue_backed_pass_when_closure_debt_is_clear() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    payload = module.evaluate_begin(
        existing_state={},
        blocker_map={
            **_base_blocker_map(),
            "remaining": {"family_count": 0, "path_count": 0},
            "next_tranche": {"id": None, "title": None},
        },
        execution_plan={
            "generated_at": "2026-04-19T04:00:00+00:00",
            "next_target": {
                "kind": "queue_backed_throughput",
                "family_id": "builder",
                "family_title": "Builder",
                "subtranche_id": "unscoped",
                "subtranche_title": None,
                "execution_class": "queue_backed_throughput",
                "approval_gated": False,
                "external_blocked": False,
            },
        },
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        ralph={"stop_state": "none"},
        now_iso="2026-04-19T04:20:00+00:00",
    )

    assert payload["controller_status"] == "running"
    assert payload["active_pass_id"].startswith("continuity-pass-")
    assert payload["active_family_id"] == "builder"
    assert payload["active_subtranche_id"] == "unscoped"
    assert payload["started_at"] == "2026-04-19T04:20:00+00:00"
    assert payload["controller_pid"] is not None


def test_evaluate_begin_reclaims_stale_running_pass_when_supervisor_pid_is_gone() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    payload = module.evaluate_begin(
        existing_state={
            "controller_status": "running",
            "controller_pid": 999999,
            "active_pass_id": "continuity-pass-stale",
            "active_family_id": "builder",
            "active_subtranche_id": "unscoped",
            "started_at": "2026-04-19T04:00:00+00:00",
        },
        blocker_map={
            **_base_blocker_map(),
            "remaining": {"family_count": 0, "path_count": 0},
            "next_tranche": {"id": None, "title": None},
        },
        execution_plan={
            "generated_at": "2026-04-19T04:00:00+00:00",
            "next_target": {
                "kind": "queue_backed_throughput",
                "family_id": "builder",
                "family_title": "Builder",
                "subtranche_id": "unscoped",
                "subtranche_title": None,
                "execution_class": "queue_backed_throughput",
                "approval_gated": False,
                "external_blocked": False,
            },
        },
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        ralph={"stop_state": "none"},
        now_iso="2026-04-19T04:20:00+00:00",
        process_is_live=lambda pid: False,
        continuity_process_is_alive=lambda **_: False,
    )

    assert payload["controller_status"] == "running"
    assert payload["active_pass_id"] != "continuity-pass-stale"
    assert payload["active_family_id"] == "builder"
    assert payload["controller_pid"] is not None


def test_build_status_surfaces_controller_host_mode_typed_brake_and_workspace_drift() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    payload = module.build_status(
        existing_state={},
        blocker_map={
            **_base_blocker_map(),
            "objective": "closure_debt",
        },
        execution_plan=_base_execution_plan(),
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        now_iso="2026-04-19T04:20:00+00:00",
        runtime_parity={"drift_class": "proof_workspace_drift"},
    )

    assert payload["controller_host"] == "dev"
    assert payload["controller_mode"] == "closure_debt"
    assert payload["active_objective"] == "closure_debt"
    assert payload["workspace_drift_status"] == "proof_workspace_drift"
    assert payload["typed_brake"] == "proof_workspace_drift"


def test_build_status_prefers_runtime_packet_target_when_typed_brakes_only() -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    payload = module.build_status(
        existing_state={},
        blocker_map={
            **_base_blocker_map(),
            "objective": "result_backed_throughput",
        },
        execution_plan={
            "generated_at": "2026-04-19T04:00:00+00:00",
            "next_target": {
                "kind": "queue_backed_throughput",
                "family_id": "builder",
                "family_title": "Builder",
                "subtranche_id": "unscoped",
                "subtranche_title": None,
                "execution_class": "queue_backed_throughput",
                "approval_gated": False,
                "external_blocked": False,
            },
        },
        value_throughput={"result_backed_completion_count": 0},
        validator_snapshot={"success": True},
        now_iso="2026-04-19T04:20:00+00:00",
        runtime_parity={"drift_class": "generated_surface_drift"},
        runtime_packet_inbox={
            "packet_count": 1,
            "packets": [
                {
                    "id": "workshop-ulrich-energy-retirement-packet",
                    "label": "WORKSHOP retired ulrich-energy runtime retirement packet",
                    "host": "workshop",
                    "approval_type": "runtime_host_reconfiguration",
                    "goal": "Retire remaining lineage.",
                    "readiness_state": "ready_for_approval",
                    "next_operator_action": "Backup before mutation.",
                }
            ],
        },
    )

    assert payload["next_target"]["kind"] == "runtime_packet"
    assert payload["next_target"]["family_id"] == "runtime-packet-inbox"
    assert payload["next_target"]["subtranche_id"] == "workshop-ulrich-energy-retirement-packet"


def test_append_pass_ledger_records_selected_tranche_and_proof_state(tmp_path: Path) -> None:
    module = _load_module(
        f"run_continuity_control_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_control_pass.py",
    )

    ledger_path = tmp_path / "completion-pass-ledger.json"
    module.COMPLETION_PASS_LEDGER_PATH = ledger_path

    entry = module.append_pass_ledger(
        existing_state={
            "active_pass_id": "continuity-pass-123",
            "active_family_id": "agent-execution-kernel-follow-on",
            "active_subtranche_id": "operator-queue-state",
            "started_at": "2026-04-19T04:00:00+00:00",
        },
        finished_state={
            "finished_at": "2026-04-19T04:30:00+00:00",
            "last_meaningful_delta_at": "2026-04-19T04:30:00+00:00",
        },
        blocker_map={
            "remaining": {"family_count": 2, "path_count": 31},
            "proof_gate": {
                "checks": [
                    {"id": "stale_claim_failures", "met": True, "detail": "clean"},
                    {"id": "artifact_consistency", "met": True, "detail": "consistent"},
                    {"id": "validator_and_contract_healer", "met": True, "detail": "green"},
                ]
            },
        },
        result_evidence={
            "threshold_required": 5,
            "threshold_progress": 2,
            "threshold_met": False,
            "result_backed_completion_count": 2,
            "review_backed_output_count": 0,
        },
        validator_snapshot={
            "ralph_validation": {"ran": True, "all_passed": True},
            "contract_healer": {"success": True},
            "validation_summary": "6/6 validation checks passed.",
        },
    )

    assert entry["pass_id"] == "continuity-pass-123"
    assert entry["family_id"] == "agent-execution-kernel-follow-on"
    assert entry["subtranche_id"] == "operator-queue-state"
    assert entry["healthy"] is True
    assert entry["proofs"]["validator_and_contract_healer"]["met"] is True
    assert "validation_passed=True" in entry["proofs"]["validator_and_contract_healer"]["detail"]
    assert entry["result_evidence"]["threshold_progress"] == 2

    stored = ledger_path.read_text(encoding="utf-8")
    assert "continuity-pass-123" in stored
