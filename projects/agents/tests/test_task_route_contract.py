from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import tasks as task_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(task_routes.router)
    return TestClient(app)


class TaskRouteContractTests(unittest.TestCase):
    def test_create_task_emits_denied_audit_for_invalid_payload(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.governor.Governor.get") as governor_get,
        ):
            response = client.post(
                "/v1/tasks",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Submit task",
                    "agent": "research-agent",
                    "prompt": "",
                },
            )

        self.assertEqual(400, response.status_code)
        self.assertEqual("Both 'agent' and 'prompt' are required", response.json()["error"])
        governor_get.assert_not_called()
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("denied", kwargs["decision"])
        self.assertEqual(400, kwargs["status_code"])
        self.assertEqual("/v1/tasks", kwargs["route"])

    def test_dispatch_task_requires_operator_action_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.tasks.dispatch_next_pending_task", AsyncMock()) as dispatch_next_pending_task,
        ):
            response = client.post("/v1/tasks/dispatch", json={})

        self.assertEqual(400, response.status_code)
        dispatch_next_pending_task.assert_not_awaited()
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("denied", kwargs["decision"])
        self.assertEqual(400, kwargs["status_code"])
        self.assertEqual("/v1/tasks/dispatch", kwargs["route"])

    def test_create_task_uses_canonical_governed_submission_helper(self) -> None:
        client = _make_client()
        submission = SimpleNamespace(
            task=SimpleNamespace(
                id="task-123",
                to_dict=lambda: {"id": "task-123", "status": "pending"},
            ),
            decision=SimpleNamespace(autonomy_level="A", reason="Allowed"),
        )
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
        ):
            response = client.post(
                "/v1/tasks",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Submit task",
                    "agent": "research-agent",
                    "prompt": "Audit routing drift",
                    "priority": "high",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("submitted", response.json()["status"])
        self.assertEqual("A", response.json()["governor"]["level"])
        self.assertEqual("Allowed", response.json()["governor"]["reason"])
        submit_governed_task.assert_awaited_once_with(
            agent="research-agent",
            prompt="Audit routing drift",
            priority="high",
            metadata={},
            source="manual",
        )
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual("task-123", audit.await_args.kwargs["target"])

    def test_dispatch_task_emits_accepted_audit_on_success(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch(
                "athanor_agents.tasks.dispatch_next_pending_task",
                AsyncMock(return_value={"status": "dispatched", "task": {"id": "task-123"}}),
            ) as dispatch_next_pending_task,
        ):
            response = client.post(
                "/v1/tasks/dispatch",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Dispatch next task",
                },
            )

        self.assertEqual(200, response.status_code)
        dispatch_next_pending_task.assert_awaited_once_with(trigger="dashboard")
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("accepted", kwargs["decision"])
        self.assertEqual(200, kwargs["status_code"])
        self.assertEqual("/v1/tasks/dispatch", kwargs["route"])
        self.assertEqual("task-123", kwargs["target"])

    def test_cancel_task_requires_operator_action_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.tasks.cancel_task", AsyncMock()) as cancel_task,
        ):
            response = client.post("/v1/tasks/task-123/cancel", json={})

        self.assertEqual(400, response.status_code)
        cancel_task.assert_not_awaited()
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("denied", kwargs["decision"])
        self.assertEqual(400, kwargs["status_code"])
        self.assertEqual("/v1/tasks/{task_id}/cancel", kwargs["route"])

    def test_cancel_task_emits_accepted_audit_on_success(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.tasks.cancel_task", AsyncMock(return_value=True)) as cancel_task,
        ):
            response = client.post(
                "/v1/tasks/task-123/cancel",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "cancelled", "task_id": "task-123"}, response.json())
        cancel_task.assert_awaited_once_with("task-123")
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("accepted", kwargs["decision"])
        self.assertEqual(200, kwargs["status_code"])
        self.assertEqual("task-123", kwargs["target"])

    def test_approve_task_emits_denied_audit_when_task_is_missing(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.tasks.approve_task", AsyncMock(return_value=False)) as approve_task,
        ):
            response = client.post(
                "/v1/tasks/task-123/approve",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                },
            )

        self.assertEqual(404, response.status_code)
        approve_task.assert_awaited_once_with("task-123")
        audit.assert_awaited_once()
        kwargs = audit.await_args.kwargs
        self.assertEqual("denied", kwargs["decision"])
        self.assertEqual(404, kwargs["status_code"])
        self.assertEqual("/v1/tasks/{task_id}/approve", kwargs["route"])

    def test_review_task_requires_admin_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.supervisor.review_task_output", AsyncMock()) as review_task_output,
        ):
            response = client.post("/v1/tasks/task-123/review", json={})

        self.assertEqual(400, response.status_code)
        review_task_output.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])
        self.assertEqual("/v1/tasks/{task_id}/review", audit.await_args.kwargs["route"])

    def test_review_task_emits_accepted_audit_on_success(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.tasks.emit_operator_audit_event", AsyncMock()) as audit,
            patch(
                "athanor_agents.supervisor.review_task_output",
                AsyncMock(return_value={"task_id": "task-123", "quality_score": 0.92, "agent": "coding-agent"}),
            ) as review_task_output,
        ):
            response = client.post(
                "/v1/tasks/task-123/review",
                json={
                    "actor": "operator",
                    "session_id": "sess-1",
                    "correlation_id": "corr-1",
                    "reason": "Review task output",
                },
            )

        self.assertEqual(200, response.status_code)
        review_task_output.assert_awaited_once_with("task-123")
        audit.assert_awaited_once()
        self.assertEqual("accepted", audit.await_args.kwargs["decision"])
        self.assertEqual("task-123", audit.await_args.kwargs["target"])
