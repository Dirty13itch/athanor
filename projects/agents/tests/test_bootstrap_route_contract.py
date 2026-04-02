from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import bootstrap as bootstrap_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(bootstrap_routes.router)
    return TestClient(app)


class BootstrapRouteContractTests(unittest.TestCase):
    def test_list_programs_returns_status_and_takeover(self) -> None:
        client = _make_client()
        takeover = {"ready": False, "blocker_ids": ["durable_persistence_live"]}
        status = {"mode": "ready", "program_count": 1, "takeover": takeover}
        with (
            patch("athanor_agents.bootstrap_state.list_bootstrap_programs", AsyncMock(return_value=[{"id": "launch-readiness-bootstrap"}])),
            patch("athanor_agents.bootstrap_state.build_bootstrap_runtime_snapshot", AsyncMock(return_value=status)) as build_snapshot,
        ):
            response = client.get("/v1/bootstrap/programs")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(status, payload["status"])
        self.assertEqual(takeover, payload["takeover"])
        build_snapshot.assert_awaited_once_with(include_snapshot_write=False)

    def test_get_program_detail_returns_specific_program(self) -> None:
        client = _make_client()
        program = {"id": "launch-readiness-bootstrap", "current_family": "compatibility_retirement"}
        with patch("athanor_agents.bootstrap_state.get_bootstrap_program_detail", AsyncMock(return_value=program)) as get_detail:
            response = client.get("/v1/bootstrap/programs/launch-readiness-bootstrap")

        self.assertEqual(200, response.status_code)
        self.assertEqual(program, response.json()["program"])
        get_detail.assert_awaited_once_with("launch-readiness-bootstrap")

    def test_list_integrations_returns_projected_queue(self) -> None:
        client = _make_client()
        integrations = [{"id": "integration-1", "status": "queued"}]
        with patch("athanor_agents.bootstrap_state.list_bootstrap_integrations", AsyncMock(return_value=integrations)) as list_integrations:
            response = client.get("/v1/bootstrap/integrations?status=queued")

        self.assertEqual(200, response.status_code)
        self.assertEqual(integrations, response.json()["integrations"])
        list_integrations.assert_awaited_once_with(status="queued", family="", limit=50)

    def test_claim_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.bootstrap.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.bootstrap_state.claim_bootstrap_slice", AsyncMock()) as claim,
        ):
            response = client.post("/v1/bootstrap/slices/slice-1/claim", json={"host_id": "codex_external"})

        self.assertEqual(400, response.status_code)
        claim.assert_not_awaited()
        audit.assert_awaited_once()

    def test_claim_returns_claimed_payload(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.bootstrap.emit_operator_audit_event", AsyncMock()) as audit,
            patch(
                "athanor_agents.bootstrap_state.claim_bootstrap_slice",
                AsyncMock(return_value={"id": "slice-1", "host_id": "codex_external", "status": "claimed"}),
            ) as claim,
        ):
            response = client.post(
                "/v1/bootstrap/slices/slice-1/claim",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Claim slice",
                    "host_id": "codex_external",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("claimed", response.json()["status"])
        claim.assert_awaited_once()
        audit.assert_awaited_once()

    def test_nudge_runs_supervisor_cycle(self) -> None:
        client = _make_client()
        result = {
            "active_program_id": "launch-readiness-bootstrap",
            "active_family": "compatibility_retirement",
            "recommendation": {"slice_id": "slice-compatibility-retirement", "host_id": "codex_external"},
        }
        with (
            patch("athanor_agents.routes.bootstrap.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.bootstrap_state.run_bootstrap_supervisor_cycle", AsyncMock(return_value=result)) as nudge,
        ):
            response = client.post(
                "/v1/bootstrap/programs/launch-readiness-bootstrap/nudge",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Advance supervisor",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("nudged", response.json()["status"])
        nudge.assert_awaited_once_with(
            program_id="launch-readiness-bootstrap",
            execute=False,
            retry_blockers=True,
            process_integrations=True,
        )
        audit.assert_awaited_once()

    def test_approve_program_packet_returns_updated_snapshot(self) -> None:
        client = _make_client()
        result = {
            "approved_packet_id": "db_schema_change",
            "approved_slice_ids": ["persist-04-activation-cutover", "persist-05-restart-proof"],
            "resolved_blocker_ids": ["blocker-1"],
            "program": {"id": "launch-readiness-bootstrap", "status": "active", "next_slice_id": "persist-04-activation-cutover"},
            "snapshot": {
                "active_program_id": "launch-readiness-bootstrap",
                "active_family": "durable_persistence_activation",
                "next_slice_id": "persist-04-activation-cutover",
                "waiting_on_approval_family": "",
                "waiting_on_approval_slice_id": "",
            },
            "takeover": {"ready": False, "blocker_ids": ["durable_persistence_live"]},
            "recommendation": {"slice_id": "persist-04-activation-cutover", "host_id": "codex_external"},
            "next_action": {"kind": "dispatch", "slice_id": "persist-04-activation-cutover"},
        }
        with (
            patch("athanor_agents.routes.bootstrap.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.bootstrap_state.approve_bootstrap_packet", AsyncMock(return_value=result)) as approve,
        ):
            response = client.post(
                "/v1/bootstrap/programs/launch-readiness-bootstrap/approve",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Approve durable persistence packet",
                    "packet_id": "db_schema_change",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("approved", response.json()["status"])
        approve.assert_awaited_once_with(
            "launch-readiness-bootstrap",
            packet_id="db_schema_change",
            approved_by="operator",
            reason="Approve durable persistence packet",
        )
        audit.assert_awaited_once()

    def test_promote_program_returns_promoted_payload(self) -> None:
        client = _make_client()
        program = {"id": "launch-readiness-bootstrap", "status": "takeover_promoted"}
        with (
            patch("athanor_agents.routes.bootstrap.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.bootstrap_state.promote_bootstrap_program", AsyncMock(return_value=program)) as promote,
        ):
            response = client.post(
                "/v1/bootstrap/programs/launch-readiness-bootstrap/promote",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Promote internal builder",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("promoted", response.json()["status"])
        promote.assert_awaited_once_with(
            "launch-readiness-bootstrap",
            promoted_by="operator",
            reason="Promote internal builder",
            force=False,
        )
        audit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
