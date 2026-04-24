from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import projects as project_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(project_routes.router)
    return TestClient(app)


class FoundryRouteContractTests(unittest.TestCase):
    def test_get_project_packet_returns_seeded_payload(self) -> None:
        client = _make_client()
        packet = {"id": "athanor", "stage": "active_build", "template": "internal_operator_app"}
        with patch("athanor_agents.foundry_state.fetch_project_packet_record", AsyncMock(return_value=packet)):
            response = client.get("/v1/projects/athanor/packet")

        self.assertEqual(200, response.status_code)
        self.assertEqual("athanor", response.json()["packet"]["id"])

    def test_update_project_packet_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.upsert_project_packet_record", AsyncMock()) as upsert_packet,
        ):
            response = client.post("/v1/projects/athanor/packet", json={"stage": "active_build"})

        self.assertEqual(400, response.status_code)
        upsert_packet.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_update_project_packet_returns_saved_payload(self) -> None:
        client = _make_client()
        saved = {"id": "athanor", "stage": "active_build", "template": "internal_operator_app"}
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_project_packet_record", AsyncMock(side_effect=[None, saved])),
            patch("athanor_agents.foundry_state.upsert_project_packet_record", AsyncMock(return_value=True)) as upsert_packet,
        ):
            response = client.post(
                "/v1/projects/athanor/packet",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Update packet",
                    "stage": "active_build",
                    "template": "internal_operator_app",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("updated", response.json()["status"])
        upsert_packet.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_create_deploy_candidate_requires_project_packet(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_project_packet_record", AsyncMock(return_value=None)),
        ):
            response = client.post(
                "/v1/projects/athanor/deployments",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Record candidate",
                    "channel": "internal_preview",
                },
            )

        self.assertEqual(404, response.status_code)
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_list_execution_slices_returns_records(self) -> None:
        client = _make_client()
        slices = [{"id": "slice-1", "project_id": "athanor", "status": "planned"}]
        with patch("athanor_agents.foundry_state.list_execution_slice_records", AsyncMock(return_value=slices)):
            response = client.get("/v1/projects/athanor/slices")

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()["count"])
        self.assertEqual("slice-1", response.json()["slices"][0]["id"])

    def test_create_maintenance_run_requires_project_packet(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_project_packet_record", AsyncMock(return_value=None)),
        ):
            response = client.post(
                "/v1/projects/athanor/maintenance",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "kind": "smoke",
                    "trigger": "manual",
                },
            )

        self.assertEqual(404, response.status_code)
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_create_maintenance_run_can_materialize_backlog_follow_up(self) -> None:
        client = _make_client()
        project_packet = {"id": "athanor", "stage": "active_build"}
        maintenance_run = {
            "id": "maintenance-1",
            "project_id": "athanor",
            "kind": "smoke",
            "trigger": "manual",
            "status": "queued",
            "evidence_ref": "reports/maintenance/athanor-smoke.json",
        }
        backlog = {"id": "backlog-maint-1", "family": "maintenance"}
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_project_packet_record", AsyncMock(return_value=project_packet)),
            patch("athanor_agents.foundry_state.upsert_maintenance_run_record", AsyncMock(return_value=True)) as upsert_maintenance_run_record,
            patch("athanor_agents.foundry_state.list_maintenance_run_records", AsyncMock(return_value=[maintenance_run])),
            patch("athanor_agents.operator_work.materialize_maintenance_signal", AsyncMock(return_value=backlog)) as materialize_maintenance_signal,
        ):
            response = client.post(
                "/v1/projects/athanor/maintenance",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Record maintenance run",
                    "kind": "smoke",
                    "trigger": "manual",
                    "status": "queued",
                    "materialize_backlog": True,
                    "owner_agent": "coding-agent",
                    "recurrence_program_id": "weekly-athanor-maintenance",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("created", response.json()["status"])
        self.assertEqual("backlog-maint-1", response.json()["backlog"]["id"])
        upsert_maintenance_run_record.assert_awaited_once()
        materialize_maintenance_signal.assert_awaited_once()
        self.assertEqual("athanor", materialize_maintenance_signal.await_args.kwargs["project_id"])
        self.assertEqual("weekly-athanor-maintenance", materialize_maintenance_signal.await_args.kwargs["recurrence_program_id"])
        self.assertEqual(
            "maintenance:athanor:program:weekly-athanor-maintenance",
            materialize_maintenance_signal.await_args.kwargs["source_ref"],
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_list_rollback_events_returns_records(self) -> None:
        client = _make_client()
        rollbacks = [{"id": "rollback-1", "project_id": "athanor", "status": "executed"}]
        with patch("athanor_agents.foundry_state.list_rollback_event_records", AsyncMock(return_value=rollbacks)):
            response = client.get("/v1/projects/athanor/rollbacks")

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json()["count"])
        self.assertEqual("rollback-1", response.json()["rollbacks"][0]["id"])

    def test_promote_candidate_rejects_missing_rollback_target(self) -> None:
        client = _make_client()
        candidate = {"id": "candidate-1", "rollback_target": {}, "metadata": {}, "project_id": "athanor"}
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_deploy_candidate_record", AsyncMock(return_value=candidate)),
        ):
            response = client.post(
                "/v1/projects/athanor/promote",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Promote candidate",
                    "candidate_id": "candidate-1",
                    "channel": "internal_prod",
                },
            )

        self.assertEqual(400, response.status_code)
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_promote_candidate_records_rollback_anchor(self) -> None:
        client = _make_client()
        candidate = {
            "id": "candidate-1",
            "project_id": "athanor",
            "rollback_target": {"deployment": "prev"},
            "metadata": {},
        }
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_deploy_candidate_record", AsyncMock(return_value=dict(candidate))),
            patch("athanor_agents.foundry_state.upsert_deploy_candidate_record", AsyncMock(return_value=True)) as upsert_candidate,
            patch("athanor_agents.foundry_state.record_rollback_event", AsyncMock(return_value=True)) as record_rollback_event,
        ):
            response = client.post(
                "/v1/projects/athanor/promote",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Promote candidate",
                    "candidate_id": "candidate-1",
                    "channel": "internal_prod",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("promoted", response.json()["status"])
        upsert_candidate.assert_awaited_once()
        record_rollback_event.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_materialize_project_proving_stage_calls_foundry_helper(self) -> None:
        client = _make_client()
        proving = {
            "project_id": "athanor",
            "stage": "slice_execution",
            "storage": {"storage_mode": "local_fallback"},
        }
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.materialize_foundry_proving_stage", AsyncMock(return_value=proving)) as materialize,
        ):
            response = client.post(
                "/v1/projects/athanor/proving",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Record proving slice",
                    "stage": "slice_execution",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("recorded", response.json()["status"])
        materialize.assert_awaited_once_with("athanor", stage="slice_execution")
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_rollback_candidate_records_execution_event(self) -> None:
        client = _make_client()
        candidate = {
            "id": "candidate-1",
            "project_id": "athanor",
            "channel": "internal_prod",
            "promotion_status": "promoted",
            "rollback_target": {"deployment": "prev"},
            "metadata": {},
        }
        with (
            patch("athanor_agents.routes.projects.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.foundry_state.fetch_deploy_candidate_record", AsyncMock(return_value=dict(candidate))),
            patch("athanor_agents.foundry_state.upsert_deploy_candidate_record", AsyncMock(return_value=True)) as upsert_candidate,
            patch("athanor_agents.foundry_state.record_rollback_event", AsyncMock(return_value=True)) as record_rollback_event,
        ):
            response = client.post(
                "/v1/projects/athanor/rollback",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Rollback candidate",
                    "candidate_id": "candidate-1",
                    "protected_mode": True,
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("rolled_back", response.json()["status"])
        upsert_candidate.assert_awaited_once()
        record_rollback_event.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])


if __name__ == "__main__":
    unittest.main()
