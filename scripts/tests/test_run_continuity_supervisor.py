from __future__ import annotations

import importlib.util
import subprocess
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


def test_run_cycle_exits_without_overlap_when_pass_is_already_active() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    calls: list[tuple[str, ...]] = []

    def _runner(*args: str):
        calls.append(args)
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "skipped",
                "last_skip_reason": "pass_active",
                "active_pass_id": "continuity-pass-live",
            }
        raise AssertionError(f"unexpected call: {args}")

    outcome = module.run_cycle(command_runner=_runner)

    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "pass_active"
    assert calls == [
        ("scripts/run_continuity_control_pass.py", "begin", "--json"),
        *module.STATUS_REFRESH_COMMANDS,
    ]
    assert len(outcome["status_refresh"]) == len(module.STATUS_REFRESH_COMMANDS)


def test_run_cycle_refreshes_status_surfaces_when_pass_is_skipped() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    calls: list[tuple[str, ...]] = []

    def _runner(*args: str):
        calls.append(args)
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "skipped",
                "last_skip_reason": "backoff_active",
                "active_pass_id": None,
            }
        if args in module.STATUS_REFRESH_COMMANDS:
            return {"success": True}
        raise AssertionError(f"unexpected call: {args}")

    outcome = module.run_cycle(command_runner=_runner)

    assert outcome["status"] == "skipped"
    assert outcome["reason"] == "backoff_active"
    assert calls == [
        ("scripts/run_continuity_control_pass.py", "begin", "--json"),
        *module.STATUS_REFRESH_COMMANDS,
    ]
    assert len(outcome["status_refresh"]) == len(module.STATUS_REFRESH_COMMANDS)


def test_run_cycle_runs_fixed_point_and_finishes_when_pass_is_acquired() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    calls: list[tuple[str, ...]] = []

    def _runner(*args: str):
        calls.append(args)
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "running",
                "active_pass_id": "continuity-pass-001",
            }
        if args[0] == "scripts/run_steady_state_control_plane.py":
            return {"success": True}
        if args[:2] == ("scripts/run_continuity_control_pass.py", "finish"):
            return {"controller_status": "idle"}
        if args in module.POST_FINISH_REFRESH_COMMANDS:
            return {"success": True}
        raise AssertionError(f"unexpected call: {args}")

    outcome = module.run_cycle(command_runner=_runner)

    assert outcome["status"] == "completed"
    assert outcome["pass_id"] == "continuity-pass-001"
    assert calls == [
        ("scripts/run_continuity_control_pass.py", "begin", "--json"),
        ("scripts/run_steady_state_control_plane.py", "--skip-restart-brief", "--json"),
        ("scripts/run_continuity_control_pass.py", "finish", "--pass-id", "continuity-pass-001", "--json"),
        ("scripts/write_runtime_parity.py", "--json"),
        ("scripts/write_result_evidence_ledger.py", "--json"),
        ("scripts/write_stable_operating_day.py", "--json"),
        ("scripts/run_continuity_control_pass.py", "status", "--json"),
        ("scripts/write_blocker_map.py", "--json"),
        ("scripts/write_blocker_execution_plan.py", "--json"),
        ("scripts/write_continuity_supervisor_health.py", "--json"),
        ("scripts/write_project_output_readiness.py", "--json"),
        ("scripts/write_project_output_candidates.py", "--json"),
        ("scripts/materialize_project_output_acceptance.py", "--all-pending", "--json"),
        ("scripts/write_project_output_candidates.py", "--json"),
        ("scripts/write_project_output_proof.py", "--json"),
        ("scripts/write_autonomy_failure_ledger.py", "--json"),
        ("scripts/write_controller_of_controllers.py", "--json"),
        ("scripts/write_steady_state_status.py", "--json"),
        ("scripts/write_operator_mobile_summary.py", "--json"),
        ("scripts/write_command_center_final_form_status.py", "--json"),
        ("scripts/write_system_capability_scorecard.py", "--json"),
        ("scripts/generate_truth_inventory_reports.py",),
        ("scripts/triage_publication_tranche.py", "--write", "docs/operations/PUBLICATION-TRIAGE-REPORT.md"),
        ("scripts/generate_publication_deferred_family_queue.py",),
        ("scripts/generate_ecosystem_master_plan.py",),
        ("scripts/generate_full_system_audit.py", "--skip-checks"),
        ("scripts/validate_platform_contract.py",),
        ("scripts/run_contract_healer.py",),
        ("scripts/write_blocker_map.py", "--json"),
        ("scripts/write_blocker_execution_plan.py", "--json"),
        ("scripts/write_continuity_supervisor_health.py", "--json"),
        ("scripts/write_autonomy_failure_ledger.py", "--json"),
        ("scripts/write_controller_of_controllers.py", "--json"),
        ("scripts/write_steady_state_status.py", "--json"),
        ("scripts/write_operator_mobile_summary.py", "--json"),
        ("scripts/write_command_center_final_form_status.py", "--json"),
        ("scripts/write_system_capability_scorecard.py", "--json"),
    ]
    assert len(outcome["post_finish_refresh"]) == len(module.POST_FINISH_REFRESH_COMMANDS)


def test_run_json_command_treats_successful_non_json_stdout_as_success(monkeypatch) -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="docs/operations/PUBLICATION-TRIAGE-REPORT.md\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    payload = module._run_json_command("scripts/triage_publication_tranche.py", "--write", "docs/operations/PUBLICATION-TRIAGE-REPORT.md")

    assert payload["success"] is True
    assert "PUBLICATION-TRIAGE-REPORT.md" in payload["stdout"]


def test_run_json_command_sets_runtime_proof_env_for_validator(monkeypatch) -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    captured_env: dict[str, str] | None = None

    def fake_run(command, **kwargs):
        nonlocal captured_env
        captured_env = kwargs.get("env")
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module._run_json_command("scripts/validate_platform_contract.py")

    assert captured_env is not None
    assert captured_env["ATHANOR_RUNTIME_PROOF_CONTEXT"] == "1"


def test_run_cycle_finishes_pass_when_fixed_point_raises() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    calls: list[tuple[str, ...]] = []

    def _runner(*args: str):
        calls.append(args)
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "running",
                "active_pass_id": "continuity-pass-002",
            }
        if args[0] == "scripts/run_steady_state_control_plane.py":
            raise RuntimeError("fixed-point failed")
        if args[:2] == ("scripts/run_continuity_control_pass.py", "finish"):
            return {"controller_status": "idle"}
        if args in module.POST_FINISH_REFRESH_COMMANDS:
            return {"success": True}
        raise AssertionError(f"unexpected call: {args}")

    outcome = module.run_cycle(command_runner=_runner)

    assert outcome["status"] == "failed"
    assert outcome["pass_id"] == "continuity-pass-002"
    assert outcome["error"] == "fixed-point failed"
    assert ("scripts/run_continuity_control_pass.py", "finish", "--pass-id", "continuity-pass-002", "--json") in calls
    assert len(outcome["post_finish_refresh"]) == len(module.POST_FINISH_REFRESH_COMMANDS)


def test_run_cycle_records_finish_error_when_release_fails() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    calls: list[tuple[str, ...]] = []

    def _runner(*args: str):
        calls.append(args)
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "running",
                "active_pass_id": "continuity-pass-003",
            }
        if args[0] == "scripts/run_steady_state_control_plane.py":
            raise RuntimeError("fixed-point failed")
        if args[:2] == ("scripts/run_continuity_control_pass.py", "finish"):
            raise RuntimeError("finish failed")
        raise AssertionError(f"unexpected call: {args}")

    outcome = module.run_cycle(command_runner=_runner)

    assert outcome["status"] == "failed"
    assert outcome["pass_id"] == "continuity-pass-003"
    assert outcome["error"] == "fixed-point failed"
    assert outcome["finish_error"] == "finish failed"


def test_run_supervisor_single_cycle_exits_without_sleeping_on_backoff_skip() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    sleep_calls: list[float] = []
    payload = module.run_supervisor(
        loop=False,
        runtime_budget_seconds=600,
        poll_interval_seconds=180,
        cycle_runner=lambda: {"status": "skipped", "reason": "backoff_active", "pass_id": None},
        sleeper=sleep_calls.append,
        monotonic=lambda: 0.0,
    )

    assert payload["success"] is False
    assert payload["run_count"] == 1
    assert payload["history"][0]["reason"] == "backoff_active"
    assert sleep_calls == []


def test_run_supervisor_passes_runtime_budget_to_child_commands() -> None:
    module = _load_module(
        f"run_continuity_supervisor_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_continuity_supervisor.py",
    )

    observed_calls: list[tuple[tuple[str, ...], int | None]] = []

    def _runner(*args: str, timeout_seconds: int | None = None):
        observed_calls.append((args, timeout_seconds))
        if args[:2] == ("scripts/run_continuity_control_pass.py", "begin"):
            return {
                "controller_status": "skipped",
                "last_skip_reason": "backoff_active",
                "active_pass_id": None,
            }
        raise AssertionError(f"unexpected call: {args}")

    payload = module.run_supervisor(
        loop=False,
        runtime_budget_seconds=10,
        poll_interval_seconds=180,
        command_runner=_runner,
        monotonic=lambda: 0.0,
    )

    assert payload["success"] is False
    assert payload["run_count"] == 1
    assert observed_calls == [
        (("scripts/run_continuity_control_pass.py", "begin", "--json"), 10),
        *((command, 10) for command in module.STATUS_REFRESH_COMMANDS),
    ]
