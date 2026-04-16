from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from athanor_agents.routes import metrics as metrics_routes


class _FakeResponse:
    status_code = 200

    def json(self) -> dict:
        return {"result": {"count": 0}}


class _FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse()


class AgentMetricsRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_metrics_uses_canonical_task_stats(self) -> None:
        tracker = type("Tracker", (), {"summary": lambda self: {"providers": []}})()
        agents = [
            {"id": "general-assistant", "name": "General Assistant", "tools": ["shell"], "status": "ready"},
            {"id": "research-agent", "name": "Research Agent", "tools": [], "status": "ready"},
        ]

        with (
            patch("athanor_agents.agents.get_agent_info", return_value=agents),
            patch("athanor_agents.routing.get_cost_tracker", return_value=tracker),
            patch("athanor_agents.routes.metrics.httpx.AsyncClient", return_value=_FakeAsyncClient()),
            patch(
                "athanor_agents.goals.compute_trust_scores",
                AsyncMock(return_value={"general-assistant": {"trust_score": 0.75}}),
            ),
            patch(
                "athanor_agents.tasks.get_task_stats",
                AsyncMock(return_value={"by_agent": {"general-assistant": 3}}),
            ),
        ):
            payload = await metrics_routes.agent_metrics()

        self.assertEqual({"providers": []}, payload["cost"])
        self.assertEqual({"total": 3}, payload["agents"][0]["tasks"])
        self.assertEqual({}, payload["agents"][1]["tasks"])
        self.assertEqual(0.75, payload["agents"][0]["trust_score"])
