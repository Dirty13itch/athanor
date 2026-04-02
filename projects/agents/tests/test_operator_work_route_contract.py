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
        with (
            patch("athanor_agents.operator_work.idea_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.inbox_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.todo_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.backlog_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.run_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
            patch("athanor_agents.operator_work.approval_stats", AsyncMock(return_value={"total": 1, "by_status": {}})),
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
        self.assertIn("projects", payload)
        self.assertIn("outputs", payload)
        self.assertIn("patterns", payload)

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
