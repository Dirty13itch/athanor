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


def test_build_payload_reports_healthy_supervisor_when_recent_pass_and_clean_parity_exist() -> None:
    module = _load_module(
        f"write_continuity_supervisor_health_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_continuity_supervisor_health.py",
    )

    payload = module.build_payload(
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "closure_debt",
            "controller_status": "idle",
            "last_successful_pass_at": "2026-04-19T08:00:00+00:00",
            "typed_brake": None,
        },
        runtime_parity={"drift_class": "clean"},
        blocker_map={"proof_gate": {"open": False}},
        now_iso="2026-04-19T08:03:00+00:00",
    )

    assert payload["health_status"] == "healthy"
    assert payload["controller_host"] == "dev"
    assert payload["service_name"] == "athanor-continuity.service"


def test_build_payload_reports_degraded_when_typed_brake_or_parity_drift_exists() -> None:
    module = _load_module(
        f"write_continuity_supervisor_health_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_continuity_supervisor_health.py",
    )

    payload = module.build_payload(
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "typed_brake",
            "controller_status": "blocked",
            "last_successful_pass_at": "2026-04-19T06:00:00+00:00",
            "typed_brake": "proof_workspace_drift",
        },
        runtime_parity={"drift_class": "proof_workspace_drift"},
        blocker_map={"proof_gate": {"open": False}},
        now_iso="2026-04-19T08:03:00+00:00",
    )

    assert payload["health_status"] == "degraded"
    assert payload["typed_brake"] == "proof_workspace_drift"


def test_build_payload_reports_degraded_when_controller_is_marked_running_but_no_continuity_process_exists() -> None:
    module = _load_module(
        f"write_continuity_supervisor_health_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_continuity_supervisor_health.py",
    )
    module._supervisor_pid_is_live = lambda pid: False
    module._any_continuity_process_alive = lambda: False

    payload = module.build_payload(
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "proof_hold",
            "controller_status": "running",
            "controller_pid": 999999,
            "last_successful_pass_at": "2026-04-19T08:00:00+00:00",
            "typed_brake": None,
        },
        runtime_parity={"drift_class": "clean"},
        blocker_map={"proof_gate": {"open": False}},
        now_iso="2026-04-19T08:03:00+00:00",
    )

    assert payload["health_status"] == "degraded"
    assert payload["controller_process_alive"] is False


def test_build_payload_treats_running_worker_processes_as_healthy_even_when_control_pid_is_ephemeral() -> None:
    module = _load_module(
        f"write_continuity_supervisor_health_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_continuity_supervisor_health.py",
    )
    module._supervisor_pid_is_live = lambda pid: False
    module._any_continuity_process_alive = lambda: True

    payload = module.build_payload(
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "closure_debt",
            "controller_status": "running",
            "controller_pid": 999999,
            "last_successful_pass_at": "2026-04-20T01:42:50.023616+00:00",
            "typed_brake": None,
        },
        runtime_parity={"drift_class": "clean"},
        blocker_map={"proof_gate": {"open": False}},
        now_iso="2026-04-20T01:51:00+00:00",
    )

    assert payload["health_status"] == "healthy"
    assert payload["continuity_process_alive"] is True


def test_build_payload_accepts_generated_surface_drift_without_degrading_health() -> None:
    module = _load_module(
        f"write_continuity_supervisor_health_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_continuity_supervisor_health.py",
    )
    module._supervisor_pid_is_live = lambda pid: True
    module._any_continuity_process_alive = lambda: True

    payload = module.build_payload(
        continuity_state={
            "controller_host": "dev",
            "controller_mode": "closure_debt",
            "controller_status": "running",
            "controller_pid": 1234,
            "last_successful_pass_at": "2026-04-20T18:39:20.897932+00:00",
            "typed_brake": None,
        },
        runtime_parity={"drift_class": "generated_surface_drift", "detail": "managed generated surfaces only"},
        blocker_map={"proof_gate": {"open": False}},
        now_iso="2026-04-20T18:45:00+00:00",
    )

    assert payload["health_status"] == "healthy"
    assert payload["detail"] == "Continuity supervisor is active with recent successful passes."
