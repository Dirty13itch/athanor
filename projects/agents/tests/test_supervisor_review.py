from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.tasks import Task


class SupervisorReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_review_task_output_persists_review_packet_for_unverified_backlog_task(self) -> None:
        from athanor_agents import supervisor

        task = Task(
            id="task-review-1",
            agent="coding-agent",
            prompt="Advance capacity truth.",
            status="completed",
            result="Completed without automatic verification.",
            metadata={"backlog_id": "backlog-1", "execution_run_id": "run-1"},
        )

        class _Response:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "0.87"}}]}

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return _Response()

        with (
            patch("athanor_agents.tasks.get_task", AsyncMock(return_value=task)),
            patch("httpx.AsyncClient", return_value=_Client()),
            patch("athanor_agents.work_pipeline.record_outcome", AsyncMock(return_value=None)),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock(return_value=True)) as persist_task_state,
            patch(
                "athanor_agents.operator_work.sync_backlog_item_from_task",
                AsyncMock(return_value={"status": "waiting_approval"}),
            ) as sync_backlog_item_from_task,
        ):
            result = await supervisor.review_task_output("task-review-1")

        self.assertEqual("review:task-review-1", result["review_id"])
        self.assertEqual("waiting_approval", result["backlog_status"])
        self.assertEqual("review:task-review-1", task.metadata["approval_request_id"])
        persist_task_state.assert_awaited_once()
        sync_backlog_item_from_task.assert_awaited_once()
