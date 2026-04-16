from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from watchdog_test_utils import load_watchdog_module


async def _idle_main_loop() -> None:
    return None


def test_default_health_reports_paused_guarded_mode(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_INITIAL_PAUSED": "true",
            "WATCHDOG_MUTATIONS_ENABLED": "false",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "ready_for_approval",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with TestClient(module.app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["paused"] is True
    assert payload["mutation_gate_open"] is False
    assert payload["control_plane"]["mode"] == "paused_guarded"
    assert "WATCHDOG_MUTATIONS_ENABLED=false" in payload["control_plane"]["mutation_gate_blockers"]
    assert payload["control_plane"]["runtime_packet_status"] == "ready_for_approval"


def test_status_marks_protected_services_as_manual_restart_blocked(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_INITIAL_PAUSED": "true",
            "WATCHDOG_MUTATIONS_ENABLED": "true",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "executed",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with TestClient(module.app) as client:
            response = client.get("/status")

    assert response.status_code == 200
    payload = response.json()
    protected = payload["services"]["foundry.vllm-tp4"]
    assert protected["manual_restart_allowed"] is False
    assert protected["allowed_actions"]["manual_restart"]["allowed"] is False
    assert "protected service" in protected["allowed_actions"]["manual_restart"]["blocked_by"][0]
