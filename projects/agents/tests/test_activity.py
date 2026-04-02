import httpx
import unittest
from unittest.mock import AsyncMock, patch


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self._request = httpx.Request("POST", "http://test.local")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self._request,
                response=httpx.Response(self.status_code, request=self._request, json=self._payload),
            )

    def json(self):
        return self._payload


class TestQueryEvents(unittest.IsolatedAsyncioTestCase):
    def test_coerce_unix_timestamp_handles_strings(self):
        from athanor_agents.activity import _coerce_unix_timestamp

        self.assertEqual(123, _coerce_unix_timestamp("123"))
        self.assertEqual(123, _coerce_unix_timestamp("123.9"))
        self.assertEqual(0, _coerce_unix_timestamp(""))
        self.assertEqual(0, _coerce_unix_timestamp("bad"))

    async def test_query_events_falls_back_to_paginated_scroll(self):
        from athanor_agents.activity import query_events

        recent_failed = {
            "payload": {
                "event_type": "task_failed",
                "agent": "general-assistant",
                "description": "Recent failure",
                "data": {"code": "E1"},
                "timestamp": "2026-04-02T14:00:00Z",
                "timestamp_unix": "200",
            }
        }
        old_failed = {
            "payload": {
                "event_type": "task_failed",
                "agent": "general-assistant",
                "description": "Old failure",
                "data": {"code": "E0"},
                "timestamp": "2026-04-02T13:00:00Z",
                "timestamp_unix": 100,
            }
        }
        other_event = {
            "payload": {
                "event_type": "task_completed",
                "agent": "creative-agent",
                "description": "Complete",
                "data": {},
                "timestamp": "2026-04-02T14:01:00Z",
                "timestamp_unix": 210,
            }
        }

        calls = [
            _FakeResponse(500, {"status": {"error": "LiteralOutOfBounds"}}),
            _FakeResponse(
                200,
                {
                    "result": {
                        "points": [old_failed, other_event],
                        "next_page_offset": "page-2",
                    }
                },
            ),
            _FakeResponse(
                200,
                {
                    "result": {
                        "points": [recent_failed],
                        "next_page_offset": None,
                    }
                },
            ),
        ]

        with patch("athanor_agents.activity.httpx.post", side_effect=calls):
            results = await query_events(
                event_type="task_failed",
                agent="general-assistant",
                since_unix=150,
                limit=10,
            )

        self.assertEqual(1, len(results))
        self.assertEqual("Recent failure", results[0]["description"])
        self.assertEqual(200, results[0]["timestamp_unix"])

    async def test_query_events_falls_back_to_task_store_when_qdrant_is_unavailable(self):
        from athanor_agents.activity import query_events

        with (
            patch(
                "athanor_agents.activity.httpx.post",
                side_effect=[
                    _FakeResponse(500, {"status": {"error": "LiteralOutOfBounds"}}),
                    _FakeResponse(500, {"status": {"error": "LiteralOutOfBounds"}}),
                ],
            ),
            patch(
                "athanor_agents.activity._query_task_store_events",
                AsyncMock(
                    return_value=[
                        {
                            "event_type": "task_failed",
                            "agent": "coding-agent",
                            "description": "Task abc failed",
                            "data": {"task_id": "abc", "synthetic": True},
                            "timestamp": "2026-04-02T14:00:00+00:00",
                            "timestamp_unix": 200,
                        }
                    ]
                ),
            ) as fallback,
        ):
            results = await query_events(limit=10, since_unix=150)

        self.assertEqual(1, len(results))
        self.assertTrue(results[0]["data"]["synthetic"])
        fallback.assert_awaited_once()

    async def test_query_task_store_events_synthesizes_task_and_schedule_events(self):
        from athanor_agents.activity import _query_task_store_events

        records = [
            {
                "id": "task-complete",
                "agent": "coding-agent",
                "status": "completed",
                "created_at": 180,
                "completed_at": 200,
                "priority": "normal",
                "source": "scheduler",
                "lane": "coding-agent",
                "result": "Patched issue",
                "metadata": {"source": "scheduler", "job_family": "agent_schedule"},
            },
            {
                "id": "task-failed",
                "agent": "research-agent",
                "status": "failed",
                "created_at": 150,
                "completed_at": 250,
                "priority": "high",
                "source": "task_api",
                "lane": "research-agent",
                "error": "HTTP 500",
                "retry_count": 1,
                "metadata": {"failure": {"message": "HTTP 500"}},
            },
            {
                "id": "task-approval",
                "agent": "general-assistant",
                "status": "pending_approval",
                "created_at": 300,
                "priority": "normal",
                "source": "task_api",
                "lane": "general-assistant",
                "metadata": {"requires_approval": True},
            },
        ]

        with (
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=object())),
            patch(
                "athanor_agents.task_store.read_task_records_by_statuses",
                AsyncMock(return_value=records),
            ),
        ):
            events = await _query_task_store_events(limit=10, since_unix=120)

        self.assertGreaterEqual(len(events), 4)
        event_types = [event["event_type"] for event in events]
        self.assertIn("task_completed", event_types)
        self.assertIn("task_failed", event_types)
        self.assertIn("schedule_run", event_types)
        self.assertIn("escalation_triggered", event_types)
        self.assertTrue(all(event["data"].get("synthetic") for event in events))


if __name__ == "__main__":
    unittest.main()
