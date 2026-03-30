from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from athanor_agents.routes import digests as digests_routes


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(digests_routes.router)
    return TestClient(app)


class DigestsRouteContractTests(unittest.TestCase):
    def test_generate_digest_requires_operator_envelope(self) -> None:
        client = _make_client()
        with (
            patch("athanor_agents.routes.digests.emit_operator_audit_event", AsyncMock()) as audit,
            patch("athanor_agents.routes.digests._generate_digest_from_tasks", AsyncMock()) as generate_digest,
        ):
            response = client.post("/v1/digests/generate", json={"period": "24h"})

        self.assertEqual(400, response.status_code)
        generate_digest.assert_not_awaited()
        audit.assert_awaited_once()
        self.assertEqual("denied", audit.await_args.kwargs["decision"])
        self.assertEqual("/v1/digests/generate", audit.await_args.kwargs["route"])


class DigestsGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_digest_uses_terminal_status_indexes_and_terminal_timestamps(self) -> None:
        now = 1_800_000_000.0
        redis_client = object()
        recent_completion = {
            "id": "task-completed",
            "agent": "general-assistant",
            "status": "completed",
            "prompt": "Generate digest from recent tasks",
            "created_at": now - 172800,
            "updated_at": now - 60,
            "completed_at": now - 60,
            "result": "Digest completed successfully.",
        }
        recent_failure = {
            "id": "task-failed",
            "agent": "home-agent",
            "status": "failed",
            "prompt": "Health check for workshop services",
            "created_at": now - 172800,
            "updated_at": now - 120,
            "error": "Timed out waiting for service health.",
        }
        stale_completion = {
            "id": "task-stale",
            "agent": "media-agent",
            "status": "completed",
            "prompt": "Sonarr queue audit",
            "created_at": now - 400000,
            "updated_at": now - 400000,
            "completed_at": now - 400000,
            "result": "Old result",
        }

        with (
            patch("athanor_agents.routes.digests.time.time", return_value=now),
            patch(
                "athanor_agents.routes.digests.read_task_records_by_statuses",
                AsyncMock(return_value=[recent_completion, recent_failure, stale_completion]),
            ) as read_by_statuses,
        ):
            digest = await digests_routes._generate_digest_from_tasks(redis_client)

        read_by_statuses.assert_awaited_once_with(redis_client, "completed", "failed")
        self.assertEqual(2, digest["task_count"])
        self.assertEqual(1, digest["completed_count"])
        self.assertEqual(1, digest["failed_count"])
        self.assertEqual({"general-assistant": 1, "home-agent": 1}, digest["by_agent"])
        self.assertEqual("general-assistant", digest["recent_completions"][0]["agent"])
        self.assertEqual("Generate digest from recent tasks", digest["recent_completions"][0]["prompt"])
        self.assertEqual("home-agent", digest["recent_failures"][0]["agent"])
        self.assertIn("Health check for workshop services", digest["summary"])


if __name__ == "__main__":
    unittest.main()
