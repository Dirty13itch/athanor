from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import operator_work as operator_work_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(operator_work_routes.router)
    return TestClient(app)


class OperatorWorkRouteContractTests(unittest.TestCase):
    def test_summary_includes_governance_payload(self) -> None:
        client = _make_client()
        governance = {"launch_ready": False, "launch_blockers": ["providers:evidence_missing"]}
        task_stats = {
            "total": 12,
            "by_status": {"completed": 3, "failed": 4, "pending_approval": 2, "stale_lease": 1},
            "failed_actionable": 2,
            "failed_historical_repaired": 2,
            "failed_missing_detail": 0,
            "worker_running": True,
        }
        with (
            patch("athanor_agents.operator_work.idea_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.inbox_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.todo_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.backlog_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.run_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.approval_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value=task_stats)),
            patch("athanor_agents.operator_work.digest_summary", AsyncMock(return_value={"summary": "digest"})),
            patch("athanor_agents.operator_work.project_summary", AsyncMock(return_value={"stalled_total": 0, "stalled_preview": []})),
            patch("athanor_agents.operator_work.output_summary", AsyncMock(return_value={"total": 0, "recent": []})),
            patch("athanor_agents.operator_work.pattern_summary", AsyncMock(return_value={"available": True, "patterns": [], "recommendations": []})),
            patch("athanor_agents.governance_state.build_governance_snapshot", AsyncMock(return_value=governance)),
        ):
            response = client.get("/v1/operator/summary")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(governance, payload["governance"])
        self.assertEqual("digest", payload["digest"]["summary"])
        self.assertEqual(task_stats, payload["tasks"])
        self.assertIn("projects", payload)
        self.assertIn("outputs", payload)
        self.assertIn("patterns", payload)

    def test_summary_degrades_individual_sections_when_components_timeout(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.operator_work.idea_stats", AsyncMock(side_effect=TimeoutError("ideas timed out"))),
            patch("athanor_agents.operator_work.inbox_stats", AsyncMock(return_value={"total": 2, "by_status": {"new": 2}})),
            patch("athanor_agents.operator_work.todo_stats", AsyncMock(return_value={"total": 1, "by_status": {"open": 1}})),
            patch("athanor_agents.operator_work.backlog_stats", AsyncMock(return_value={"total": 1, "by_status": {"ready": 1}})),
            patch("athanor_agents.operator_work.run_stats", AsyncMock(return_value={"total": 1, "by_status": {"running": 1}})),
            patch("athanor_agents.operator_work.approval_stats", AsyncMock(return_value={"total": 0, "by_status": {}})),
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value={"total": 0, "by_status": {}, "pending_approval": 0, "stale_lease": 0, "failed_actionable": 0, "failed_historical_repaired": 0, "failed_missing_detail": 0})),
            patch("athanor_agents.bootstrap_state.build_bootstrap_runtime_snapshot", AsyncMock(side_effect=TimeoutError("bootstrap timed out"))),
            patch("athanor_agents.governance_state.build_governance_snapshot", AsyncMock(return_value={"launch_ready": True, "launch_blockers": []})),
            patch("athanor_agents.operator_work.digest_summary", AsyncMock(return_value={"summary": "digest"})),
            patch("athanor_agents.operator_work.project_summary", AsyncMock(return_value={"stalled_total": 0, "stalled_preview": []})),
            patch("athanor_agents.operator_work.output_summary", AsyncMock(return_value={"total": 0, "recent": []})),
            patch("athanor_agents.operator_work.pattern_summary", AsyncMock(return_value={"available": True, "patterns": [], "recommendations": []})),
        ):
            response = client.get("/v1/operator/summary")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("degraded", payload["status"])
        self.assertEqual(0, payload["ideas"]["total"])
        self.assertEqual("degraded", payload["bootstrap"]["status"])
        self.assertGreaterEqual(len(payload["degraded_sections"]), 2)

    def test_create_todo_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.create_todo", AsyncMock()) as create_todo,
        ):
            response = client.post("/v1/operator/todos", json={"title": "Follow up"})

        self.assertEqual(400, response.status_code)
        create_todo.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])
        self.assertEqual("/v1/operator/todos", audit.await_args.kwargs["route"])

    def test_create_todo_returns_created_payload(self) -> None:
        client = _make_client()
        todo = {"id": "todo-123", "title": "Follow up", "category": "ops", "scope_type": "global"}
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.create_todo", AsyncMock(return_value=todo)) as create_todo,
        ):
            response = client.post(
                "/v1/operator/todos",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Create todo",
                    "title": "Follow up",
                    "category": "ops",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("created", response.json()["status"])
        create_todo.assert_awaited_once()
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual("todo-123", audit.await_args.kwargs["target"])

    def test_transition_todo_reports_missing_record(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.transition_todo", AsyncMock(return_value=None)) as transition_todo,
        ):
            response = client.post(
                "/v1/operator/todos/todo-123/transition",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Move todo",
                    "status": "ready",
                },
            )

        self.assertEqual(404, response.status_code)
        transition_todo.assert_awaited_once_with("todo-123", status="ready", note="")
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])

    def test_convert_inbox_returns_linked_todo(self) -> None:
        client = _make_client()
        payload = {
            "inbox": {"id": "inbox-1", "status": "converted"},
            "todo": {"id": "todo-9", "status": "open"},
        }
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.convert_inbox_item_to_todo", AsyncMock(return_value=payload)) as convert_inbox_item_to_todo,
        ):
            response = client.post(
                "/v1/operator/inbox/inbox-1/convert",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Convert inbox item",
                    "category": "decision",
                    "priority": 4,
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("converted", response.json()["status"])
        convert_inbox_item_to_todo.assert_awaited_once_with(
            "inbox-1",
            category="decision",
            priority=4,
            energy_class="quick",
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual("inbox-1", audit.await_args.kwargs["target"])

    def test_list_approvals_returns_projected_records(self) -> None:
        client = _make_client()
        approvals = [{"id": "approval-1", "status": "pending"}]
        with patch("athanor_agents.operator_work.list_approvals", AsyncMock(return_value=approvals)) as list_approvals:
            response = client.get("/v1/operator/approvals?status=pending")

        self.assertEqual(200, response.status_code)
        self.assertEqual(approvals, response.json()["approvals"])
        list_approvals.assert_awaited_once_with(status="pending", limit=50)

    def test_list_runs_degrades_to_empty_when_runtime_times_out(self) -> None:
        client = _make_client()
        with patch("athanor_agents.operator_work.list_runs", AsyncMock(side_effect=TimeoutError("runs timed out"))):
            response = client.get("/v1/operator/runs?limit=12")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual([], payload["runs"])
        self.assertEqual(0, payload["count"])

    def test_list_backlog_degrades_to_empty_when_runtime_times_out(self) -> None:
        client = _make_client()
        with patch("athanor_agents.operator_work.list_backlog", AsyncMock(side_effect=TimeoutError("backlog timed out"))):
            response = client.get("/v1/operator/backlog?limit=12")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual([], payload["backlog"])
        self.assertEqual(0, payload["count"])

    def test_create_backlog_accepts_canonical_queue_fields(self) -> None:
        client = _make_client()
        backlog = {
            "id": "backlog-queue-1",
            "title": "Packet maintenance",
            "family": "maintenance",
            "project_id": "kindred",
            "source_type": "program_signal",
            "source_ref": "project-packet:kindred:weekly",
            "routing_class": "private_but_cloud_allowed",
            "verification_contract": "maintenance_proof",
            "closure_rule": "proof_or_review_required",
            "materialization_source": "project_packet_cadence",
            "materialization_reason": "Recurring maintenance signal emitted governed queue work.",
            "recurrence_program_id": "weekly-kindred-maintenance",
            "result_id": "",
            "review_id": "",
        }
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.create_backlog_item", AsyncMock(return_value=backlog)) as create_backlog_item,
        ):
            response = client.post(
                "/v1/operator/backlog",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Create backlog",
                    "title": "Packet maintenance",
                    "prompt": "Refresh maintenance evidence.",
                    "owner_agent": "coding-agent",
                    "family": "maintenance",
                    "project_id": "kindred",
                    "source_type": "program_signal",
                    "source_ref": "project-packet:kindred:weekly",
                    "routing_class": "private_but_cloud_allowed",
                    "verification_contract": "maintenance_proof",
                    "closure_rule": "proof_or_review_required",
                    "materialization_source": "project_packet_cadence",
                    "materialization_reason": "Recurring maintenance signal emitted governed queue work.",
                    "recurrence_program_id": "weekly-kindred-maintenance",
                },
            )

        self.assertEqual(200, response.status_code)
        create_backlog_item.assert_awaited_once()
        self.assertEqual("maintenance", create_backlog_item.await_args.kwargs["family"])
        self.assertEqual("kindred", create_backlog_item.await_args.kwargs["project_id"])
        self.assertEqual("program_signal", create_backlog_item.await_args.kwargs["source_type"])
        self.assertEqual("project_packet_cadence", create_backlog_item.await_args.kwargs["materialization_source"])
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_create_backlog_accepts_autonomous_value_fields(self) -> None:
        client = _make_client()
        backlog = {
            "id": "backlog-value-1",
            "title": "Accepted operator-value proof",
            "family": "research_audit",
            "value_class": "operator_value",
            "deliverable_kind": "report",
            "deliverable_refs": ["docs/operations/REPO-ROOTS-REPORT.md"],
            "beneficiary_surface": "athanor_core",
            "acceptance_mode": "automated",
            "accepted_by": "system",
            "accepted_at": "2026-04-20T05:00:00+00:00",
            "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-1.json"],
            "operator_steered": False,
        }
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.create_backlog_item", AsyncMock(return_value=backlog)) as create_backlog_item,
        ):
            response = client.post(
                "/v1/operator/backlog",
                json={
                    "actor": "codex",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Create autonomous value acceptance backlog",
                    "title": "Accepted operator-value proof",
                    "prompt": "Persist the accepted autonomous value proof.",
                    "owner_agent": "research-agent",
                    "family": "research_audit",
                    "value_class": "operator_value",
                    "deliverable_kind": "report",
                    "deliverable_refs": ["docs/operations/REPO-ROOTS-REPORT.md"],
                    "beneficiary_surface": "athanor_core",
                    "acceptance_mode": "automated",
                    "accepted_by": "system",
                    "accepted_at": "2026-04-20T05:00:00+00:00",
                    "acceptance_proof_refs": ["reports/truth-inventory/autonomous-value-acceptance/backlog-1.json"],
                    "operator_steered": False,
                },
            )

        self.assertEqual(200, response.status_code)
        create_backlog_item.assert_awaited_once()
        self.assertEqual("operator_value", create_backlog_item.await_args.kwargs["value_class"])
        self.assertEqual("report", create_backlog_item.await_args.kwargs["deliverable_kind"])
        self.assertEqual(
            ["docs/operations/REPO-ROOTS-REPORT.md"],
            create_backlog_item.await_args.kwargs["deliverable_refs"],
        )
        self.assertEqual("athanor_core", create_backlog_item.await_args.kwargs["beneficiary_surface"])
        self.assertEqual("automated", create_backlog_item.await_args.kwargs["acceptance_mode"])
        self.assertEqual("system", create_backlog_item.await_args.kwargs["accepted_by"])
        self.assertEqual(
            "2026-04-20T05:00:00+00:00",
            create_backlog_item.await_args.kwargs["accepted_at"],
        )
        self.assertEqual(
            ["reports/truth-inventory/autonomous-value-acceptance/backlog-1.json"],
            create_backlog_item.await_args.kwargs["acceptance_proof_refs"],
        )
        self.assertIs(False, create_backlog_item.await_args.kwargs["operator_steered"])
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_materialize_maintenance_backlog_endpoint_uses_canonical_materializer(self) -> None:
        client = _make_client()
        backlog = {
            "id": "backlog-maint-1",
            "family": "maintenance",
            "project_id": "kindred",
            "source_type": "program_signal",
        }
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.materialize_maintenance_signal", AsyncMock(return_value=backlog)) as materialize_maintenance_signal,
        ):
            response = client.post(
                "/v1/operator/backlog/materialize-maintenance",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Materialize maintenance",
                    "project_id": "kindred",
                    "title": "Weekly packet maintenance",
                    "prompt": "Refresh project maintenance evidence.",
                    "source_ref": "project-packet:kindred:weekly",
                    "owner_agent": "coding-agent",
                    "recurrence_program_id": "weekly-kindred-maintenance",
                },
            )

        self.assertEqual(200, response.status_code)
        materialize_maintenance_signal.assert_awaited_once_with(
            project_id="kindred",
            title="Weekly packet maintenance",
            prompt="Refresh project maintenance evidence.",
            source_ref="project-packet:kindred:weekly",
            owner_agent="coding-agent",
            recurrence_program_id="weekly-kindred-maintenance",
            approval_mode="none",
            metadata={},
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_materialize_bootstrap_follow_up_endpoint_uses_canonical_materializer(self) -> None:
        client = _make_client()
        backlog = {
            "id": "backlog-bootstrap-1",
            "family": "project_bootstrap",
            "project_id": "athanor",
            "source_type": "bootstrap_follow_up",
        }
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.materialize_bootstrap_follow_up", AsyncMock(return_value=backlog)) as materialize_bootstrap_follow_up,
        ):
            response = client.post(
                "/v1/operator/backlog/materialize-bootstrap-follow-up",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Materialize bootstrap follow-up",
                    "program_id": "launch-readiness-bootstrap",
                    "slice_id": "slice-foundry-completion",
                    "family": "project_bootstrap",
                    "title": "Follow up foundry completion slice",
                    "prompt": "Convert the foundry completion bootstrap slice into governed queue work.",
                    "project_id": "athanor",
                    "source_ref": "bootstrap:launch-readiness-bootstrap:slice-foundry-completion",
                    "owner_agent": "coding-agent",
                },
            )

        self.assertEqual(200, response.status_code)
        materialize_bootstrap_follow_up.assert_awaited_once_with(
            program_id="launch-readiness-bootstrap",
            slice_id="slice-foundry-completion",
            family="project_bootstrap",
            title="Follow up foundry completion slice",
            prompt="Convert the foundry completion bootstrap slice into governed queue work.",
            project_id="athanor",
            source_ref="bootstrap:launch-readiness-bootstrap:slice-foundry-completion",
            owner_agent="coding-agent",
            metadata={},
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_approve_operator_approval_bridges_to_task_approval(self) -> None:
        client = _make_client()
        approval = {"id": "approval-1", "status": "pending", "related_task_id": "task-7", "related_run_id": "run-1"}
        updated = {**approval, "status": "approved"}
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.get_approval", AsyncMock(side_effect=[approval, updated])) as get_approval,
            patch("athanor_agents.tasks.approve_task", AsyncMock(return_value=True)) as approve_task,
        ):
            response = client.post(
                "/v1/operator/approvals/approval-1/approve",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Approve request",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("approved", response.json()["status"])
        approve_task.assert_awaited_once_with("task-7", decided_by="operator")
        self.assertEqual(2, get_approval.await_count)
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])

    def test_reject_operator_approval_reports_missing_record(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.operator_work.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.operator_work.get_approval", AsyncMock(return_value=None)) as get_approval,
            patch("athanor_agents.tasks.reject_task", AsyncMock()) as reject_task,
        ):
            response = client.post(
                "/v1/operator/approvals/approval-missing/reject",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Reject request",
                },
            )

        self.assertEqual(404, response.status_code)
        get_approval.assert_awaited_once_with("approval-missing")
        reject_task.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])


if __name__ == "__main__":
    unittest.main()
