from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from watchdog_test_utils import load_watchdog_module


async def _idle_main_loop() -> None:
    return None


def _envelope(**extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "actor": "test-suite",
        "session_id": "watchdog-session",
        "correlation_id": "corr-123",
        "reason": "Route contract test",
        "protected_mode": True,
    }
    payload.update(extra)
    return payload


def test_resume_requires_operator_envelope(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_MUTATIONS_ENABLED": "true",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "executed",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with TestClient(module.app) as client:
            response = client.post("/resume", json={})

    assert response.status_code == 400
    assert "missing required fields" in response.json()["detail"]


def test_resume_denied_while_mutation_gate_closed(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_MUTATIONS_ENABLED": "false",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "ready_for_approval",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with TestClient(module.app) as client:
            response = client.post("/resume", json=_envelope())

    assert response.status_code == 409
    assert "mutation gate closed" in response.json()["detail"]


def test_manual_restart_rejects_unknown_service(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_MUTATIONS_ENABLED": "true",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "executed",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with patch.object(module, "page_ntfy", new=AsyncMock(return_value=None)):
            with patch.object(module, "restart_container", new=AsyncMock(return_value=None)):
                with TestClient(module.app) as client:
                    response = client.post("/service/unknown.service/restart", json=_envelope())

    assert response.status_code == 404
    assert "unknown service_id" in response.json()["detail"]


def test_manual_restart_rejects_protected_service_even_with_gate_open(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_MUTATIONS_ENABLED": "true",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "executed",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with TestClient(module.app) as client:
            response = client.post("/service/foundry.vllm-tp4/restart", json=_envelope())

    assert response.status_code == 409
    assert "protected service" in response.json()["detail"]


def test_manual_restart_dry_run_returns_plan_without_mutation(tmp_path: Path) -> None:
    module = load_watchdog_module(
        {
            "WATCHDOG_MUTATIONS_ENABLED": "true",
            "WATCHDOG_RUNTIME_PACKET_STATUS": "executed",
            "WATCHDOG_AUDIT_LOG": str(tmp_path / "watchdog-audit.log"),
        }
    )
    restart_mock = AsyncMock()
    with patch.object(module, "main_loop", new=_idle_main_loop):
        with patch.object(module, "page_ntfy", new=AsyncMock(return_value=None)):
            with patch.object(module, "restart_container", new=restart_mock):
                with TestClient(module.app) as client:
                    response = client.post(
                        "/service/foundry.graphrag/restart",
                        json=_envelope(dry_run=True),
                    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["success"] is True
    assert payload["planned_action"] == "docker restart athanor-graphrag on foundry"
    restart_mock.assert_not_awaited()
