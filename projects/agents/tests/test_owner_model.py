from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents import owner_model


class _FakePrometheusResponse:
    status_code = 200

    def json(self) -> dict:
        return {"data": {"result": [{"value": [0, "15"]}]}}


class _FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, *args, **kwargs):
        return _FakePrometheusResponse()


class OwnerModelCapacityTests(unittest.IsolatedAsyncioTestCase):
    async def test_gather_capacity_uses_complete_active_task_read(self) -> None:
        with (
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"by_status": {"pending": 80}}),
            ),
            patch(
                "athanor_agents.tasks.list_tasks",
                AsyncMock(
                    return_value=[
                        {"agent": "general-assistant", "status": "pending"},
                        {"agent": "research-agent", "status": "running"},
                    ]
                ),
            ) as list_tasks,
            patch("athanor_agents.owner_model.httpx.AsyncClient", return_value=_FakeAsyncClient()),
        ):
            capacity = await owner_model._gather_capacity()

        list_tasks.assert_awaited_once_with(statuses=["pending", "running"], limit=None)
        self.assertEqual(80, capacity["queue_depth"])
        self.assertNotIn("general-assistant", capacity["agents_idle"])
        self.assertNotIn("research-agent", capacity["agents_idle"])
        self.assertIn("coding-agent", capacity["agents_idle"])
