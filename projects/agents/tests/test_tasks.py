"""Tests for task execution engine — user-facing task lifecycle.

Covers Task dataclass, prompt building, priority ordering, and Redis-backed CRUD.
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Mock langchain_core before importing tasks.py — not installed on DEV
if "langchain_core" not in sys.modules:
    _lc_mock = MagicMock()
    sys.modules["langchain_core"] = _lc_mock
    sys.modules["langchain_core.messages"] = _lc_mock


# ---------------------------------------------------------------------------
# Task dataclass tests
# ---------------------------------------------------------------------------


class TestTaskDataclass(unittest.TestCase):
    """Test Task data model."""

    def test_default_values(self):
        from athanor_agents.tasks import Task

        t = Task()
        self.assertEqual(t.status, "pending")
        self.assertEqual(t.priority, "normal")
        self.assertEqual(t.agent, "")
        self.assertEqual(t.result, "")
        self.assertEqual(t.error, "")
        self.assertEqual(t.retry_count, 0)
        self.assertIsInstance(t.id, str)
        self.assertEqual(len(t.id), 12)

    def test_round_trip_serialization(self):
        from athanor_agents.tasks import Task

        original = Task(
            agent="coding-agent",
            prompt="Write a test",
            priority="high",
            status="running",
            metadata={"source": "test"},
        )
        data = original.to_dict()
        restored = Task.from_dict(data)

        self.assertEqual(restored.agent, "coding-agent")
        self.assertEqual(restored.prompt, "Write a test")
        self.assertEqual(restored.priority, "high")
        self.assertEqual(restored.status, "running")
        self.assertEqual(restored.metadata, {"source": "test"})

    def test_from_dict_ignores_extra_keys(self):
        from athanor_agents.tasks import Task

        data = {"agent": "test", "unknown_field": "value"}
        t = Task.from_dict(data)
        self.assertEqual(t.agent, "test")

    def test_duration_ms_calculated(self):
        from athanor_agents.tasks import Task

        t = Task(started_at=1000.0, completed_at=1002.5)
        self.assertEqual(t.duration_ms, 2500)

    def test_duration_ms_none_when_incomplete(self):
        from athanor_agents.tasks import Task

        t = Task(started_at=1000.0, completed_at=0.0)
        self.assertIsNone(t.duration_ms)

    def test_json_round_trip(self):
        from athanor_agents.tasks import Task

        original = Task(
            agent="research-agent",
            prompt="Research vLLM",
            steps=[{"index": 0, "type": "tool_call", "tool_name": "web_search"}],
        )
        json_str = json.dumps(original.to_dict())
        restored = Task.from_dict(json.loads(json_str))
        self.assertEqual(restored.agent, "research-agent")
        self.assertEqual(len(restored.steps), 1)


# ---------------------------------------------------------------------------
# Priority ordering tests
# ---------------------------------------------------------------------------


class TestPriorityOrder(unittest.TestCase):
    """Test task priority ordering logic."""

    def test_priority_values(self):
        from athanor_agents.tasks import PRIORITY_ORDER

        self.assertEqual(PRIORITY_ORDER["critical"], 0)
        self.assertEqual(PRIORITY_ORDER["high"], 1)
        self.assertEqual(PRIORITY_ORDER["normal"], 2)
        self.assertEqual(PRIORITY_ORDER["low"], 3)

    def test_critical_before_low(self):
        from athanor_agents.tasks import PRIORITY_ORDER

        self.assertLess(PRIORITY_ORDER["critical"], PRIORITY_ORDER["low"])

    def test_sorting_by_priority(self):
        from athanor_agents.tasks import Task, PRIORITY_ORDER

        tasks = [
            Task(priority="low", created_at=1000),
            Task(priority="critical", created_at=1002),
            Task(priority="normal", created_at=1001),
            Task(priority="high", created_at=1003),
        ]
        tasks.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 2), t.created_at))

        priorities = [t.priority for t in tasks]
        self.assertEqual(priorities, ["critical", "high", "normal", "low"])


# ---------------------------------------------------------------------------
# Task prompt building tests
# ---------------------------------------------------------------------------


class TestBuildTaskPrompt(unittest.TestCase):
    """Test _build_task_prompt() output."""

    def test_basic_prompt(self):
        from athanor_agents.tasks import Task, _build_task_prompt

        task = Task(id="abc123", agent="coding-agent", priority="normal")
        prompt = _build_task_prompt(task)

        self.assertIn("Task ID: abc123", prompt)
        self.assertIn("Priority: normal", prompt)
        self.assertIn("autonomous task", prompt)

    def test_includes_agent_hints(self):
        from athanor_agents.tasks import Task, _build_task_prompt

        task = Task(agent="coding-agent")
        prompt = _build_task_prompt(task)
        self.assertIn("filesystem tools", prompt)

    def test_no_hints_for_unknown_agent(self):
        from athanor_agents.tasks import Task, _build_task_prompt, _AGENT_TASK_HINTS

        task = Task(agent="nonexistent-agent")
        prompt = _build_task_prompt(task)
        # Should still have instructions but no agent-specific hints
        self.assertIn("Instructions:", prompt)
        self.assertNotIn("filesystem tools", prompt)

    def test_retry_includes_error_context(self):
        from athanor_agents.tasks import Task, _build_task_prompt

        task = Task(
            agent="coding-agent",
            retry_count=1,
            previous_error="Connection timeout to Redis",
        )
        prompt = _build_task_prompt(task)
        self.assertIn("retry #1", prompt)
        self.assertIn("Connection timeout to Redis", prompt)
        self.assertIn("different approach", prompt)

    def test_no_retry_context_on_first_attempt(self):
        from athanor_agents.tasks import Task, _build_task_prompt

        task = Task(agent="coding-agent", retry_count=0)
        prompt = _build_task_prompt(task)
        self.assertNotIn("retry", prompt)

    def test_execution_lease_included(self):
        from athanor_agents.tasks import Task, _build_task_prompt

        task = Task(
            agent="coding-agent",
            metadata={
                "execution_lease": {
                    "provider": "local-qwen",
                    "surface": "api",
                    "privacy": "private",
                    "max_parallel_children": 2,
                    "fallback": ["cloud-claude"],
                    "reason": "Routine coding task",
                }
            },
        )
        prompt = _build_task_prompt(task)
        self.assertIn("Execution lease:", prompt)
        self.assertIn("local-qwen", prompt)
        self.assertIn("cloud-claude", prompt)

    def test_all_known_agents_have_hints(self):
        from athanor_agents.tasks import _AGENT_TASK_HINTS

        expected_agents = {
            "coding-agent", "general-assistant", "research-agent",
            "knowledge-agent", "media-agent", "home-agent",
            "creative-agent", "stash-agent",
        }
        self.assertTrue(expected_agents.issubset(set(_AGENT_TASK_HINTS.keys())))


# ---------------------------------------------------------------------------
# Task state transitions
# ---------------------------------------------------------------------------


class TestTaskStateTransitions(unittest.TestCase):
    """Test task lifecycle state transitions."""

    def test_pending_to_running(self):
        from athanor_agents.tasks import Task

        t = Task(status="pending")
        t.status = "running"
        t.started_at = time.time()
        self.assertEqual(t.status, "running")
        self.assertGreater(t.started_at, 0)

    def test_running_to_completed(self):
        from athanor_agents.tasks import Task

        t = Task(status="running", started_at=time.time())
        t.status = "completed"
        t.result = "Done"
        t.completed_at = time.time()
        self.assertEqual(t.status, "completed")
        self.assertIsNotNone(t.duration_ms)

    def test_running_to_failed(self):
        from athanor_agents.tasks import Task

        t = Task(status="running", started_at=time.time())
        t.status = "failed"
        t.error = "OOM"
        t.completed_at = time.time()
        self.assertEqual(t.status, "failed")
        self.assertEqual(t.error, "OOM")

    def test_pending_to_cancelled(self):
        from athanor_agents.tasks import Task

        t = Task(status="pending")
        t.status = "cancelled"
        t.completed_at = time.time()
        self.assertEqual(t.status, "cancelled")

    def test_pending_approval_state(self):
        from athanor_agents.tasks import Task

        t = Task(status="pending_approval")
        self.assertEqual(t.status, "pending_approval")
        t.status = "pending"
        self.assertEqual(t.status, "pending")


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestTaskConstants(unittest.TestCase):
    """Test task engine constants are reasonable."""

    def test_max_concurrent_tasks(self):
        from athanor_agents.tasks import MAX_CONCURRENT_TASKS

        self.assertGreater(MAX_CONCURRENT_TASKS, 0)
        self.assertLessEqual(MAX_CONCURRENT_TASKS, 10)

    def test_task_timeout(self):
        from athanor_agents.tasks import TASK_TIMEOUT

        self.assertGreater(TASK_TIMEOUT, 60)
        self.assertLessEqual(TASK_TIMEOUT, 3600)

    def test_ttl_completed_shorter_than_failed(self):
        from athanor_agents.tasks import TASK_TTL_COMPLETED, TASK_TTL_FAILED

        self.assertLess(TASK_TTL_COMPLETED, TASK_TTL_FAILED)


# ---------------------------------------------------------------------------
# Redis-backed async tests
# ---------------------------------------------------------------------------


def _mock_redis():
    """Create a mock Redis instance with async methods."""
    mock = AsyncMock()
    mock.hset = AsyncMock()
    mock.hget = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hdel = AsyncMock(return_value=1)
    mock.publish = AsyncMock()
    return mock


class TestGetTask(unittest.IsolatedAsyncioTestCase):
    """Test get_task() Redis retrieval."""

    async def test_returns_task_when_found(self):
        from athanor_agents.tasks import get_task, Task

        task_data = Task(id="t123", agent="coding-agent", prompt="test").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await get_task("t123")

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "t123")
        self.assertEqual(result.agent, "coding-agent")

    async def test_returns_none_when_not_found(self):
        from athanor_agents.tasks import get_task

        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=None)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await get_task("nonexistent")

        self.assertIsNone(result)


class TestListTasks(unittest.IsolatedAsyncioTestCase):
    """Test list_tasks() filtering and sorting."""

    async def test_returns_all_tasks(self):
        from athanor_agents.tasks import list_tasks, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", agent="a", status="pending", created_at=1000).to_dict()),
            "t2": json.dumps(Task(id="t2", agent="b", status="completed", created_at=1001).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks()

        self.assertEqual(len(result), 2)

    async def test_filters_by_status(self):
        from athanor_agents.tasks import list_tasks, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", status="pending", created_at=1000).to_dict()),
            "t2": json.dumps(Task(id="t2", status="completed", created_at=1001).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks(status="pending")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "pending")

    async def test_filters_by_agent(self):
        from athanor_agents.tasks import list_tasks, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", agent="coding-agent", status="pending", created_at=1000).to_dict()),
            "t2": json.dumps(Task(id="t2", agent="research-agent", status="pending", created_at=1001).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks(agent="coding-agent")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["agent"], "coding-agent")

    async def test_pending_sorted_by_priority_then_created(self):
        from athanor_agents.tasks import list_tasks, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", status="pending", priority="low", created_at=1000).to_dict()),
            "t2": json.dumps(Task(id="t2", status="pending", priority="critical", created_at=1002).to_dict()),
            "t3": json.dumps(Task(id="t3", status="pending", priority="high", created_at=1001).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks()

        # Should be: critical, high, low
        self.assertEqual(result[0]["priority"], "critical")
        self.assertEqual(result[1]["priority"], "high")
        self.assertEqual(result[2]["priority"], "low")

    async def test_respects_limit(self):
        from athanor_agents.tasks import list_tasks, Task

        tasks = {
            f"t{i}": json.dumps(Task(id=f"t{i}", status="pending", created_at=1000 + i).to_dict())
            for i in range(10)
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks(limit=3)

        self.assertEqual(len(result), 3)


class TestCancelTask(unittest.IsolatedAsyncioTestCase):
    """Test cancel_task() state transition."""

    async def test_cancels_pending_task(self):
        from athanor_agents.tasks import cancel_task, Task

        task_data = Task(id="c1", status="pending").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await cancel_task("c1")

        self.assertTrue(result)
        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(stored["status"], "cancelled")

    async def test_cannot_cancel_completed_task(self):
        from athanor_agents.tasks import cancel_task, Task

        task_data = Task(id="c2", status="completed").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await cancel_task("c2")

        self.assertFalse(result)

    async def test_cancel_nonexistent_returns_false(self):
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=None)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            from athanor_agents.tasks import cancel_task

            result = await cancel_task("nonexistent")

        self.assertFalse(result)


class TestApproveTask(unittest.IsolatedAsyncioTestCase):
    """Test approve_task() approval workflow."""

    async def test_approves_pending_approval_task(self):
        from athanor_agents.tasks import approve_task, Task

        task_data = Task(id="a1", status="pending_approval").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await approve_task("a1")

        self.assertTrue(result)
        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(stored["status"], "pending")

    async def test_cannot_approve_already_pending_task(self):
        from athanor_agents.tasks import approve_task, Task

        task_data = Task(id="a2", status="pending").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await approve_task("a2")

        self.assertFalse(result)


class TestGetNextPending(unittest.IsolatedAsyncioTestCase):
    """Test _get_next_pending() priority selection."""

    async def test_picks_highest_priority(self):
        from athanor_agents.tasks import _get_next_pending, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", status="pending", priority="low", created_at=1000).to_dict()),
            "t2": json.dumps(Task(id="t2", status="pending", priority="high", created_at=1001).to_dict()),
            "t3": json.dumps(Task(id="t3", status="completed", priority="critical", created_at=999).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await _get_next_pending()

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "t2")  # high priority, completed is skipped

    async def test_fifo_within_same_priority(self):
        from athanor_agents.tasks import _get_next_pending, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", status="pending", priority="normal", created_at=1002).to_dict()),
            "t2": json.dumps(Task(id="t2", status="pending", priority="normal", created_at=1000).to_dict()),
            "t3": json.dumps(Task(id="t3", status="pending", priority="normal", created_at=1001).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await _get_next_pending()

        self.assertEqual(result.id, "t2")  # Oldest first

    async def test_returns_none_when_no_pending(self):
        from athanor_agents.tasks import _get_next_pending, Task

        tasks = {
            "t1": json.dumps(Task(id="t1", status="completed").to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await _get_next_pending()

        self.assertIsNone(result)


class TestMaybeRetry(unittest.IsolatedAsyncioTestCase):
    """Test _maybe_retry() auto-retry logic."""

    async def test_creates_retry_task(self):
        from athanor_agents.tasks import _maybe_retry, Task, MAX_TASK_RETRIES

        task = Task(
            id="fail1",
            agent="coding-agent",
            prompt="Write tests",
            priority="normal",
            status="failed",
            error="OOM on GPU",
            retry_count=0,
        )
        mock_r = _mock_redis()

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            await _maybe_retry(task)

        # Should have stored a new retry task
        mock_r.hset.assert_called_once()
        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(stored["retry_count"], 1)
        self.assertEqual(stored["agent"], "coding-agent")
        self.assertIn("OOM on GPU", stored["previous_error"])

    async def test_does_not_retry_when_exhausted(self):
        from athanor_agents.tasks import _maybe_retry, Task, MAX_TASK_RETRIES

        task = Task(
            id="fail2",
            agent="coding-agent",
            prompt="Write tests",
            status="failed",
            error="Still OOM",
            retry_count=MAX_TASK_RETRIES,
        )
        mock_r = _mock_redis()

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            await _maybe_retry(task)

        mock_r.hset.assert_not_called()


class TestCleanupOldTasks(unittest.IsolatedAsyncioTestCase):
    """Test _cleanup_old_tasks() TTL enforcement."""

    async def test_removes_expired_completed_tasks(self):
        from athanor_agents.tasks import _cleanup_old_tasks, Task, TASK_TTL_COMPLETED

        old_task = Task(
            id="old1",
            status="completed",
            completed_at=time.time() - TASK_TTL_COMPLETED - 100,
        )
        tasks = {"old1": json.dumps(old_task.to_dict())}
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            await _cleanup_old_tasks()

        mock_r.hdel.assert_called_once()

    async def test_keeps_recent_completed_tasks(self):
        from athanor_agents.tasks import _cleanup_old_tasks, Task

        recent_task = Task(
            id="recent1",
            status="completed",
            completed_at=time.time() - 60,
        )
        tasks = {"recent1": json.dumps(recent_task.to_dict())}
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            await _cleanup_old_tasks()

        mock_r.hdel.assert_not_called()

    async def test_keeps_pending_tasks_regardless_of_age(self):
        from athanor_agents.tasks import _cleanup_old_tasks, Task

        old_pending = Task(
            id="pending1",
            status="pending",
            completed_at=0,
        )
        tasks = {"pending1": json.dumps(old_pending.to_dict())}
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=tasks)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            await _cleanup_old_tasks()

        mock_r.hdel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
