from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from athanor_agents.routes import governor as governor_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(governor_routes.router)
    return TestClient(app)


class GovernorRouteContractTests(unittest.TestCase):
    def test_governor_snapshot_uses_extended_timeout_budget(self) -> None:
        with (
            patch(
                "athanor_agents.routes.governor._await_snapshot",
                AsyncMock(return_value={"status": "live"}),
            ) as await_snapshot,
            patch("athanor_agents.governor.build_governor_snapshot", Mock(return_value=object())),
        ):
            response = _make_client().get("/v1/governor")

        self.assertEqual(200, response.status_code)
        await_snapshot.assert_awaited_once()
        self.assertEqual(
            governor_routes.GOVERNOR_SNAPSHOT_TIMEOUT_SECONDS,
            await_snapshot.await_args.kwargs["timeout_seconds"],
        )

    def test_governor_snapshot_reads_canonical_builder(self) -> None:
        client = _make_client()
        snapshot = {
            "generated_at": "2026-03-27T00:00:00Z",
            "status": "live",
            "global_mode": "active",
            "degraded_mode": "normal",
            "reason": "",
            "updated_at": None,
            "updated_by": "system",
            "lanes": [],
            "capacity": {
                "posture": "healthy",
                "queue": {
                    "posture": "healthy",
                    "pending": 0,
                    "running": 0,
                    "pending_approval": 0,
                    "failed": 0,
                },
                "provider_reserve": {
                    "posture": "healthy",
                    "ready": 0,
                    "handoff_ready": 0,
                    "direct_ready": 0,
                    "degraded": 0,
                },
                "nodes": [],
                "active_time_windows": [],
                "recommendations": [],
            },
            "presence": {
                "state": "at_desk",
                "label": "At Desk",
                "automation_posture": "normal bounded autonomy",
                "notification_posture": "full detail",
                "approval_posture": "low friction",
                "updated_at": None,
                "updated_by": "system",
                "mode": "auto",
                "configured_state": "at_desk",
                "configured_label": "At Desk",
                "signal_state": None,
                "signal_source": None,
                "signal_updated_at": None,
                "signal_updated_by": "system",
                "signal_fresh": False,
                "signal_age_seconds": None,
                "effective_reason": "",
            },
            "release_tier": {
                "state": "standard",
                "available_tiers": ["strict", "standard", "expansive"],
                "status": "configured",
                "updated_at": None,
                "updated_by": "system",
            },
            "command_rights_version": "test",
            "control_stack": [],
        }
        with patch(
            "athanor_agents.governor.build_governor_snapshot",
            AsyncMock(return_value=snapshot),
        ) as builder:
            response = client.get("/v1/governor")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        builder.assert_awaited_once_with()

    def test_governor_snapshot_degrades_when_builder_times_out(self) -> None:
        client = _make_client()
        with patch(
            "athanor_agents.governor.build_governor_snapshot",
            AsyncMock(side_effect=TimeoutError("governor timed out")),
        ):
            response = client.get("/v1/governor")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("degraded", payload["status"])
        self.assertEqual("degraded", payload["capacity"]["posture"])
        self.assertIn("recommendations", payload["capacity"])

    def test_governor_router_does_not_redeclare_canonical_task_mutation_paths(self) -> None:
        client = _make_client()
        route_paths = {
            route.path
            for route in client.app.routes
            if isinstance(route, APIRoute)
        }

        self.assertNotIn("/v1/tasks/batch-approve", route_paths)
        self.assertNotIn("/v1/tasks/{task_id}/reject", route_paths)

    def test_governor_heartbeat_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.governor.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.governor.Governor.get") as get_governor,
        ):
            response = client.post("/v1/governor/heartbeat", json={"source": "dashboard_heartbeat"})

        self.assertEqual(400, response.status_code)
        get_governor.assert_not_called()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])
        self.assertEqual("/v1/governor/heartbeat", audit.await_args.kwargs["route"])

    def test_governor_heartbeat_emits_accepted_audit(self) -> None:
        client = _make_client()
        governor = AsyncMock()
        with (
            patch("athanor_agents.routes.governor.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.governor.Governor.get", return_value=governor),
        ):
            response = client.post(
                "/v1/governor/heartbeat",
                json={
                    "actor": "dashboard-heartbeat",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "state": "away",
                    "source": "dashboard_heartbeat",
                },
            )

        self.assertEqual(200, response.status_code)
        governor.record_heartbeat.assert_awaited_once_with(source="dashboard_heartbeat", state="away")
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual("dashboard_heartbeat", audit.await_args.kwargs["target"])

    def test_governor_operations_reads_canonical_operations_snapshot(self) -> None:
        client = _make_client()
        snapshot = {
            "generated_at": "2026-03-27T00:00:00Z",
            "status": "live_partial",
            "runbooks": {"status": "live_partial", "items": []},
            "backup_restore": {"status": "live_partial", "critical_stores": []},
            "release_ritual": {"status": "configured", "tiers": [], "ritual": []},
            "deprecation_retirement": {"status": "configured", "asset_classes": [], "stages": [], "rule": ""},
            "economic_governance": {
                "status": "configured",
                "premium_reserve_lanes": [],
                "automatic_spend_lanes": [],
                "approval_required_lanes": [],
                "downgrade_order": [],
            },
            "data_lifecycle": {"status": "configured", "classes": []},
            "tool_permissions": {"status": "configured", "default_mode": "governor_mediated", "subjects": []},
            "synthetic_operator_tests": {
                "generated_at": "2026-03-27T00:00:00Z",
                "status": "configured",
                "last_outcome": "not_run",
                "last_run_at": None,
                "flow_count": 0,
                "flows": [],
            },
        }
        with patch(
            "athanor_agents.governor.build_operations_readiness_snapshot",
            AsyncMock(return_value=snapshot),
        ) as builder:
            response = client.get("/v1/governor/operations")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        builder.assert_awaited_once_with()

    def test_governor_operations_degrades_when_builder_times_out(self) -> None:
        client = _make_client()
        with patch(
            "athanor_agents.governor.build_operations_readiness_snapshot",
            AsyncMock(side_effect=TimeoutError("operations timed out")),
        ):
            response = client.get("/v1/governor/operations")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("degraded", payload["status"])
        self.assertEqual("degraded", payload["runbooks"]["status"])
        self.assertEqual("degraded", payload["tool_permissions"]["status"])

    def test_governor_operator_tests_reads_canonical_snapshot(self) -> None:
        client = _make_client()
        snapshot = {
            "generated_at": "2026-03-27T00:00:00Z",
            "status": "live_partial",
            "last_outcome": "partial",
            "last_run_at": "2026-03-27T00:00:00Z",
            "flow_count": 1,
            "flows": [
                {
                    "id": "pause_resume",
                    "title": "Pause and resume",
                    "description": "Exercise pause and resume",
                    "status": "live_partial",
                    "last_outcome": "passed",
                    "last_run_at": "2026-03-27T00:00:00Z",
                    "last_duration_ms": 123,
                    "checks_passed": 1,
                    "checks_total": 1,
                    "evidence": ["test_operator_tests.py"],
                    "notes": [],
                    "details": {},
                }
            ],
        }
        with patch(
            "athanor_agents.operator_tests.build_operator_tests_snapshot",
            AsyncMock(return_value=snapshot),
        ) as builder:
            response = client.get("/v1/governor/operator-tests")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        builder.assert_awaited_once_with()

    def test_governor_run_operator_tests_returns_canonical_snapshot(self) -> None:
        client = _make_client()
        snapshot = {
            "generated_at": "2026-03-27T00:00:00Z",
            "status": "live_partial",
            "last_outcome": "partial",
            "last_run_at": "2026-03-27T00:00:00Z",
            "flow_count": 2,
            "flows": [
                {
                    "id": "pause_resume",
                    "title": "Pause and resume",
                    "description": "Exercise pause and resume",
                    "status": "live_partial",
                    "last_outcome": "passed",
                    "last_run_at": "2026-03-27T00:00:00Z",
                    "last_duration_ms": 123,
                    "checks_passed": 1,
                    "checks_total": 1,
                    "evidence": ["test_operator_tests.py"],
                    "notes": [],
                    "details": {},
                },
                {
                    "id": "restore_drill",
                    "title": "Restore drill",
                    "description": "Exercise recovery evidence",
                    "status": "degraded",
                    "last_outcome": "failed",
                    "last_run_at": "2026-03-27T00:00:00Z",
                    "last_duration_ms": 456,
                    "checks_passed": 0,
                    "checks_total": 1,
                    "evidence": ["test_operator_tests.py"],
                    "notes": [],
                    "details": {},
                },
            ],
        }
        with (
            patch("athanor_agents.routes.governor.emit_operator_audit_event", AsyncMock()) as audit,
            patch(
                "athanor_agents.operator_tests.run_operator_tests",
                AsyncMock(return_value=snapshot),
            ) as runner,
        ):
            response = client.post(
                "/v1/governor/operator-tests/run",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Run canonical operator tests",
                    "flow_ids": ["pause_resume", "restore_drill"],
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        runner.assert_awaited_once_with(
            flow_ids=["pause_resume", "restore_drill"],
            actor="operator",
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual(["pause_resume", "restore_drill"], audit.await_args.kwargs["metadata"]["flow_ids"])

    def test_governor_run_operator_tests_preserves_pilot_flow_ids(self) -> None:
        client = _make_client()
        pilot_flow_ids = [
            "goose_operator_shell",
            "openhands_bounded_worker",
            "letta_memory_plane",
            "agt_policy_plane",
        ]
        snapshot = {
            "generated_at": "2026-04-11T00:00:00Z",
            "status": "live_partial",
            "last_outcome": "partial",
            "last_run_at": "2026-04-11T00:00:00Z",
            "flow_count": len(pilot_flow_ids),
            "flows": [
                {
                    "id": flow_id,
                    "title": flow_id.replace("_", " "),
                    "description": "Pilot flow",
                    "status": "configured",
                    "last_outcome": "blocked",
                    "last_run_at": "2026-04-11T00:00:00Z",
                    "last_duration_ms": 123,
                    "checks_passed": 0,
                    "checks_total": 1,
                    "evidence": ["pilot"],
                    "notes": [],
                    "details": {},
                }
                for flow_id in pilot_flow_ids
            ],
        }
        with (
            patch("athanor_agents.routes.governor.emit_operator_audit_event", AsyncMock()) as audit,
            patch(
                "athanor_agents.operator_tests.run_operator_tests",
                AsyncMock(return_value=snapshot),
            ) as runner,
        ):
            response = client.post(
                "/v1/governor/operator-tests/run",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Run bounded pilot flows",
                    "flow_ids": pilot_flow_ids,
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        runner.assert_awaited_once_with(flow_ids=pilot_flow_ids, actor="operator")
        audit.assert_awaited_once()
        self.assertEqual(pilot_flow_ids, audit.await_args.kwargs["metadata"]["flow_ids"])

    def test_governor_tool_permissions_reads_canonical_snapshot(self) -> None:
        client = _make_client()
        snapshot = {
            "status": "live_partial",
            "default_mode": "governor_mediated",
            "subject_count": 3,
            "enforced_subject_count": 3,
            "denied_action_count": 2,
            "last_verified_at": "2026-03-27T00:00:00Z",
            "last_outcome": "passed",
            "subjects": [
                {
                    "subject": "coding-agent",
                    "label": "Coding Agent",
                    "mode": "scoped_execution",
                    "allow": ["read_file"],
                    "deny": ["deployment_mutation"],
                    "allow_count": 1,
                    "deny_count": 1,
                    "direct_execution": False,
                }
            ],
        }
        with patch(
            "athanor_agents.governor.build_tool_permissions_snapshot",
            AsyncMock(return_value=snapshot),
        ) as builder:
            response = client.get("/v1/governor/tool-permissions")

        self.assertEqual(200, response.status_code)
        self.assertEqual(snapshot, response.json())
        builder.assert_awaited_once_with()
