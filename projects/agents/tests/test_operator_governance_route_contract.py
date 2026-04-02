from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import operator_governance as operator_governance_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(operator_governance_routes.router)
    return TestClient(app)


class OperatorGovernanceRouteContractTests(unittest.TestCase):
    def test_get_governance_returns_snapshot(self) -> None:
        client = _make_client()
        snapshot = {"launch_ready": False, "launch_blockers": ["providers:evidence_missing"]}
        with patch("athanor_agents.routes.operator_governance.build_governance_snapshot", AsyncMock(return_value=snapshot)):
            response = client.get("/v1/operator/governance")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())

    def test_get_governance_drills_returns_snapshot(self) -> None:
        client = _make_client()
        snapshot = {"evidence_complete": True, "all_green": False, "drills": []}
        with patch("athanor_agents.routes.operator_governance.build_governance_drill_snapshot", return_value=snapshot):
            response = client.get("/v1/operator/governance/drills")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())

    def test_set_system_mode_requires_admin_envelope(self) -> None:
        client = _make_client()
        with patch("athanor_agents.routes.operator_governance.emit_operator_audit_event", AsyncMock()) as audit:
            response = client.post("/v1/operator/system-mode", json={"mode": "constrained"})

        self.assertEqual(400, response.status_code)
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_set_system_mode_returns_updated_payload(self) -> None:
        client = _make_client()
        record = {"id": "mode-1", "mode": "constrained"}
        with (
            patch("athanor_agents.routes.operator_governance.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.routes.operator_governance.enter_system_mode_record", AsyncMock(return_value=record)) as enter_system_mode_record,
        ):
            response = client.post(
                "/v1/operator/system-mode",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Constrain noisy work",
                    "mode": "constrained",
                    "trigger": "attention_breach",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("updated", response.json()["status"])
        enter_system_mode_record.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_rehearse_governance_drill_requires_admin_envelope(self) -> None:
        client = _make_client()
        with patch("athanor_agents.routes.operator_governance.emit_operator_audit_event", AsyncMock()) as audit:
            response = client.post("/v1/operator/governance/drills/constrained-mode/rehearse", json={})

        self.assertEqual(400, response.status_code)
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_rehearse_governance_drill_returns_recorded_payload(self) -> None:
        client = _make_client()
        artifact = {"drill_id": "blocked-approval", "passed": True, "blocker_id": ""}
        with (
            patch("athanor_agents.routes.operator_governance.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.routes.operator_governance.rehearse_governance_drill", AsyncMock(return_value=artifact)) as rehearse,
        ):
            response = client.post(
                "/v1/operator/governance/drills/blocked-approval/rehearse",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Record blocked approval evidence",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", response.json()["status"])
        rehearse.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_get_attention_budgets_includes_attention_posture(self) -> None:
        client = _make_client()
        budgets = [{"id": "general-assistant", "daily_limit": 12}]
        posture = {"recommended_mode": "normal", "breaches": []}
        with (
            patch("athanor_agents.routes.operator_governance.list_attention_budget_records", AsyncMock(return_value=budgets)),
            patch("athanor_agents.routes.operator_governance.compute_attention_posture", AsyncMock(return_value=posture)),
        ):
            response = client.get("/v1/operator/attention-budgets")

        self.assertEqual(200, response.status_code)
        self.assertEqual(budgets, response.json()["budgets"])
        self.assertEqual(posture, response.json()["attention_posture"])


if __name__ == "__main__":
    unittest.main()
