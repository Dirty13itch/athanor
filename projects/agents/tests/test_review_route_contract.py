from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import review as review_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(review_routes.router)
    return TestClient(app)


class ReviewRouteContractTests(unittest.TestCase):
    def test_get_judge_plane_returns_honest_snapshot(self) -> None:
        client = _make_client()
        with patch(
            "athanor_agents.tasks.get_task_stats",
            AsyncMock(return_value={"pending_approval": 3}),
        ):
            response = client.get("/v1/review/judges?limit=12")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("limited", payload["status"])
        self.assertEqual(3, payload["summary"]["pending_review_queue"])
        self.assertEqual(3, payload["summary"]["review_required"])
        self.assertEqual([], payload["recent_verdicts"])

    def test_get_judge_plane_degrades_when_task_stats_timeout(self) -> None:
        client = _make_client()
        with patch(
            "athanor_agents.tasks.get_task_stats",
            AsyncMock(side_effect=TimeoutError("task stats timed out")),
        ):
            response = client.get("/v1/review/judges?limit=12")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("degraded", payload["status"])
        self.assertEqual(0, payload["summary"]["pending_review_queue"])
        self.assertEqual([], payload["recent_verdicts"])
