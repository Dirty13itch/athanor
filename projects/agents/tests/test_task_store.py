from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock


def _mock_redis():
    mock = AsyncMock()
    mock.hget = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hset = AsyncMock()
    mock.hdel = AsyncMock()
    mock.smembers = AsyncMock(return_value=set())
    mock.sadd = AsyncMock()
    mock.srem = AsyncMock()
    mock.zadd = AsyncMock()
    mock.zrem = AsyncMock()
    return mock


class TestTaskStoreNormalization(unittest.TestCase):
    def test_normalizes_legacy_task_record(self):
        from athanor_agents.task_store import normalize_task_record

        record = normalize_task_record(
            {
                "id": "task-1",
                "agent_id": "coding-agent",
                "status": "in_progress",
                "metadata": {
                    "source": "scheduler",
                    "job_family": "overnight",
                    "execution_lease": {"provider": "local-qwen"},
                    "session_id": "session-1",
                    "retry_of": "task-0",
                },
            },
            now=123.0,
        )

        self.assertEqual(record["agent"], "coding-agent")
        self.assertEqual(record["source"], "scheduler")
        self.assertEqual(record["lane"], "overnight")
        self.assertEqual(record["status"], "running")
        self.assertEqual(record["assigned_runtime"], "local-qwen")
        self.assertEqual(record["session_id"], "session-1")
        self.assertEqual(record["retry_lineage"], ["task-0"])
        self.assertEqual(record["updated_at"], 123.0)


class TestTaskStoreWrites(unittest.IsolatedAsyncioTestCase):
    async def test_write_task_record_updates_indexes(self):
        from athanor_agents.task_store import write_task_record

        mock_r = _mock_redis()
        record = {
            "id": "task-2",
            "agent": "research-agent",
            "status": "pending",
            "lane": "research",
            "session_id": "session-2",
            "created_at": 10.0,
            "updated_at": 10.0,
        }

        stored = await write_task_record(mock_r, record)

        self.assertEqual(stored["status"], "pending")
        mock_r.hset.assert_awaited_once()
        mock_r.sadd.assert_any_await("athanor:tasks:status:pending", "task-2")
        mock_r.sadd.assert_any_await("athanor:tasks:lane:research", "task-2")
        mock_r.sadd.assert_any_await("athanor:tasks:session:session-2", "task-2")
        mock_r.zadd.assert_awaited_once()

    async def test_backfill_rewrites_existing_records(self):
        from athanor_agents.task_store import backfill_task_store_indexes

        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(
            return_value={
                "task-3": json.dumps(
                    {
                        "id": "task-3",
                        "agent_id": "general-assistant",
                        "status": "pending",
                        "metadata": {"source": "scheduler"},
                    }
                )
            }
        )

        updated = await backfill_task_store_indexes(mock_r)

        self.assertEqual(updated, 1)
        mock_r.hset.assert_awaited_once()
        mock_r.sadd.assert_any_await("athanor:tasks:status:pending", "task-3")

    async def test_read_task_records_by_status_uses_secondary_index(self):
        from athanor_agents.task_store import read_task_records_by_status

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(return_value={"task-4", "task-5"})
        mock_r.hget = AsyncMock(
            side_effect=[
                json.dumps(
                    {
                        "id": "task-4",
                        "agent": "coding-agent",
                        "status": "pending",
                        "updated_at": 20.0,
                    }
                ),
                json.dumps(
                    {
                        "id": "task-5",
                        "agent": "research-agent",
                        "status": "pending",
                        "updated_at": 10.0,
                    }
                ),
            ]
        )

        records = await read_task_records_by_status(mock_r, "pending")

        self.assertEqual(["task-4", "task-5"], [record["id"] for record in records])
        mock_r.smembers.assert_awaited_once_with("athanor:tasks:status:pending")

    async def test_read_task_records_by_statuses_unions_secondary_indexes(self):
        from athanor_agents.task_store import read_task_records_by_statuses

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(side_effect=[{"task-4"}, {"task-5"}])
        mock_r.hget = AsyncMock(
            side_effect=[
                json.dumps(
                    {
                        "id": "task-4",
                        "agent": "coding-agent",
                        "status": "pending",
                        "updated_at": 20.0,
                    }
                ),
                json.dumps(
                    {
                        "id": "task-5",
                        "agent": "research-agent",
                        "status": "running",
                        "updated_at": 10.0,
                    }
                ),
            ]
        )

        records = await read_task_records_by_statuses(mock_r, "pending", "running")

        self.assertEqual(["task-4", "task-5"], [record["id"] for record in records])
        mock_r.smembers.assert_any_await("athanor:tasks:status:pending")
        mock_r.smembers.assert_any_await("athanor:tasks:status:running")
