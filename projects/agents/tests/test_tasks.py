"""Tests for task execution engine — user-facing task lifecycle.

Covers Task dataclass, prompt building, priority ordering, and Redis-backed CRUD.
"""

import asyncio
import importlib.util
import json
import os
import sys
import time
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock langchain_core only when the package is genuinely unavailable.
if "langchain_core" not in sys.modules and importlib.util.find_spec("langchain_core") is None:
    _lc_mock = MagicMock()
    sys.modules["langchain_core"] = _lc_mock
    sys.modules["langchain_core.messages"] = _lc_mock


class SilentError(Exception):
    def __str__(self) -> str:
        return ""


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

    def test_build_task_message_content_trims_large_payloads(self):
        from athanor_agents.tasks import (
            MAX_TASK_MESSAGE_CHARS,
            Task,
            _build_task_message_content,
            _build_task_prompt,
        )

        task = Task(agent="coding-agent", prompt="A" * 40000)
        content = _build_task_message_content(task, "B" * 12000, _build_task_prompt(task))

        self.assertLessEqual(len(content), MAX_TASK_MESSAGE_CHARS)
        self.assertIn("[Context]", content)
        self.assertIn("[Task Instructions]", content)
        self.assertIn("truncated", content)


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


class TestTaskFailureFormatting(unittest.TestCase):
    def test_describe_exception_falls_back_to_exception_type(self):
        from athanor_agents.tasks import _describe_exception

        details = _describe_exception(SilentError())

        self.assertEqual("SilentError", details["type"])
        self.assertEqual("SilentError", details["message"])
        self.assertEqual("SilentError()", details["repr"])

    def test_stamp_task_failure_records_structured_metadata(self):
        from athanor_agents.tasks import Task, _stamp_task_failure

        task = Task(id="failmeta", agent="coding-agent", prompt="fail")
        completed_at = _stamp_task_failure(
            task,
            error_message="SilentError",
            failure_type="SilentError",
            retry_eligible=True,
            exception_repr="SilentError()",
            stage="execution_exception",
            now=1234.5,
        )

        self.assertEqual(1234.5, completed_at)
        self.assertEqual("failed", task.status)
        self.assertEqual("SilentError", task.error)
        self.assertEqual(1234.5, task.completed_at)
        self.assertEqual("SilentError", task.metadata["failure"]["type"])
        self.assertEqual("SilentError", task.metadata["failure"]["message"])
        self.assertEqual("SilentError()", task.metadata["failure"]["repr"])
        self.assertTrue(task.metadata["failure"]["retry_eligible"])
        self.assertEqual("execution_exception", task.metadata["failure"]["stage"])


# ---------------------------------------------------------------------------
# Redis-backed async tests
# ---------------------------------------------------------------------------


def _mock_redis():
    """Create a mock Redis instance with async methods."""
    mock = AsyncMock()
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.hset = AsyncMock()
    mock.hget = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hdel = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.sadd = AsyncMock(return_value=1)
    mock.srem = AsyncMock(return_value=1)
    mock.zadd = AsyncMock(return_value=1)
    mock.zrevrange = AsyncMock(return_value=[])
    mock.zrem = AsyncMock(return_value=1)
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

    async def test_normalizes_legacy_failed_task_without_detail(self):
        from athanor_agents.tasks import LEGACY_FAILED_TASK_DETAIL, Task, get_task

        task_data = Task(id="legacy-fail", agent="home-agent", status="failed", error="", metadata={}).to_dict()
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_record", AsyncMock(return_value=task_data)),
        ):
            result = await get_task("legacy-fail")

        self.assertIsNotNone(result)
        self.assertEqual(LEGACY_FAILED_TASK_DETAIL, result.error)
        self.assertTrue(result.metadata["failure_display"]["missing_detail"])
        self.assertEqual("synthetic_legacy_gap", result.metadata["failure_display"]["source"])


class TestListTasks(unittest.IsolatedAsyncioTestCase):
    """Test list_tasks() filtering and sorting."""

    async def test_returns_all_tasks(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [
            Task(id="t1", agent="a", status="pending", created_at=1000).to_dict(),
            Task(id="t2", agent="b", status="completed", created_at=1001).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            result = await list_tasks()

        self.assertEqual(len(result), 2)

    async def test_filters_by_status(self):
        from athanor_agents.tasks import list_tasks, Task

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(return_value={"t1"})
        mock_r.hget = AsyncMock(return_value=json.dumps(Task(id="t1", status="pending", created_at=1000).to_dict()))

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await list_tasks(status="pending")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "pending")

    async def test_filters_by_agent(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [
            Task(id="t1", agent="coding-agent", status="pending", created_at=1000).to_dict(),
            Task(id="t2", agent="research-agent", status="pending", created_at=1001).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            result = await list_tasks(agent="coding-agent")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["agent"], "coding-agent")

    async def test_filters_by_multiple_statuses(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [
            Task(id="t1", agent="coding-agent", status="pending", created_at=1000).to_dict(),
            Task(id="t2", agent="coding-agent", status="running", created_at=1001, started_at=1001).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)) as read_by_statuses,
        ):
            result = await list_tasks(statuses=["pending", "running"], limit=None)

        read_by_statuses.assert_awaited_once_with(mock_r, "pending", "running", limit=None)
        self.assertEqual(2, len(result))

    async def test_agent_filter_does_not_push_limit_into_store_reads(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [
            Task(id="t1", agent="other-agent", status="pending", created_at=1000).to_dict(),
            Task(id="t2", agent="coding-agent", status="pending", created_at=1001).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_status", AsyncMock(return_value=records)) as read_by_status,
        ):
            result = await list_tasks(status="pending", agent="coding-agent", limit=1)

        read_by_status.assert_awaited_once_with(mock_r, "pending", limit=None)
        self.assertEqual(1, len(result))
        self.assertEqual("coding-agent", result[0]["agent"])

    async def test_pending_sorted_by_priority_then_created(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [
            Task(id="t1", status="pending", priority="low", created_at=1000).to_dict(),
            Task(id="t2", status="pending", priority="critical", created_at=1002).to_dict(),
            Task(id="t3", status="pending", priority="high", created_at=1001).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            result = await list_tasks()

        # Should be: critical, high, low
        self.assertEqual(result[0]["priority"], "critical")
        self.assertEqual(result[1]["priority"], "high")
        self.assertEqual(result[2]["priority"], "low")

    async def test_respects_limit(self):
        from athanor_agents.tasks import list_tasks, Task

        records = [Task(id=f"t{i}", status="pending", created_at=1000 + i).to_dict() for i in range(10)]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            result = await list_tasks(limit=3)

        self.assertEqual(len(result), 3)

    async def test_normalizes_legacy_failed_task_rows(self):
        from athanor_agents.tasks import LEGACY_FAILED_TASK_DETAIL, Task, list_tasks

        records = [
            Task(id="legacy-fail", agent="media-agent", status="failed", error="", metadata={}).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            result = await list_tasks(limit=10)

        self.assertEqual(LEGACY_FAILED_TASK_DETAIL, result[0]["error"])
        self.assertTrue(result[0]["metadata"]["failure_display"]["missing_detail"])


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

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(return_value={"t1", "t2"})
        mock_r.hget = AsyncMock(
            side_effect=[
                json.dumps(Task(id="t1", status="pending", priority="low", created_at=1000).to_dict()),
                json.dumps(Task(id="t2", status="pending", priority="high", created_at=1001).to_dict()),
            ]
        )

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await _get_next_pending()

        self.assertIsNotNone(result)
        self.assertEqual(result.id, "t2")  # high priority, completed is skipped

    async def test_fifo_within_same_priority(self):
        from athanor_agents.tasks import _get_next_pending, Task

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(return_value={"t1", "t2", "t3"})
        mock_r.hget = AsyncMock(
            side_effect=[
                json.dumps(Task(id="t1", status="pending", priority="normal", created_at=1002).to_dict()),
                json.dumps(Task(id="t2", status="pending", priority="normal", created_at=1000).to_dict()),
                json.dumps(Task(id="t3", status="pending", priority="normal", created_at=1001).to_dict()),
            ]
        )

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            result = await _get_next_pending()

        self.assertEqual(result.id, "t2")  # Oldest first

    async def test_returns_none_when_no_pending(self):
        from athanor_agents.tasks import _get_next_pending, Task

        mock_r = _mock_redis()
        mock_r.smembers = AsyncMock(return_value=set())

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
        decision = types.SimpleNamespace(
            status_override="pending",
            autonomy_level="B",
            reason="Retry allowed inside autonomy phase",
        )
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.governor.Governor.get", return_value=governor),
        ):
            await _maybe_retry(task)

        # Should have stored a new retry task
        mock_r.hset.assert_called_once()
        mock_r.publish.assert_awaited_once()
        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(stored["retry_count"], 1)
        self.assertEqual(stored["agent"], "coding-agent")
        self.assertIn("OOM on GPU", stored["previous_error"])
        self.assertEqual("pending", stored["status"])
        self.assertEqual("Retry allowed inside autonomy phase", stored["metadata"]["governor_decision"])

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

    async def test_retry_hold_respects_governor_phase_gate(self):
        from athanor_agents.tasks import _maybe_retry, Task

        task = Task(
            id="fail3",
            agent="coding-agent",
            prompt="Retry the pipeline step",
            status="failed",
            error="Needs operator review",
            retry_count=0,
        )
        mock_r = _mock_redis()
        decision = types.SimpleNamespace(
            status_override="pending_approval",
            autonomy_level="D",
            reason="Autonomy phase software_core_phase_1 is not enabled",
        )
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.governor.Governor.get", return_value=governor),
        ):
            await _maybe_retry(task)

        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual("pending_approval", stored["status"])
        self.assertTrue(stored["metadata"]["requires_approval"])
        self.assertEqual("D", stored["metadata"]["governor_autonomy_level"])

    async def test_retry_uses_structured_failure_context_when_task_error_is_blank(self):
        from athanor_agents.tasks import _maybe_retry, Task

        task = Task(
            id="fail4",
            agent="coding-agent",
            prompt="Retry with structured failure metadata",
            status="failed",
            error="",
            retry_count=0,
            metadata={
                "failure": {
                    "type": "SilentError",
                    "message": "SilentError",
                    "retry_eligible": True,
                }
            },
        )
        mock_r = _mock_redis()
        decision = types.SimpleNamespace(
            status_override="pending",
            autonomy_level="B",
            reason="Retry allowed inside autonomy phase",
        )
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.governor.Governor.get", return_value=governor),
        ):
            await _maybe_retry(task)

        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual("SilentError", stored["previous_error"])

    async def test_retry_strips_transient_metadata_and_updates_backlog_lineage(self):
        from athanor_agents.tasks import _maybe_retry, Task

        task = Task(
            id="fail5",
            agent="coding-agent",
            prompt="Retry governed dispatch work",
            status="failed",
            error="stale lease",
            retry_count=0,
            metadata={
                "backlog_id": "backlog-123",
                "claim_id": "claim-123",
                "work_class": "system_improvement",
                "execution_lease": {"provider": "athanor_local"},
                "latest_task_id": "task-old",
                "latest_run_id": "task-old",
                "last_dispatch_reason": "stale dispatch",
                "governor_reason": "old reason",
                "governor_level": "A",
                "execution_claim": {"trigger": "worker"},
                "recovery": {"event": "stale_lease_recovered"},
                "failure": {"message": "old failure"},
                "execution_run_id": "run-old",
            },
        )
        mock_r = _mock_redis()
        decision = types.SimpleNamespace(
            status_override="pending",
            autonomy_level="B",
            reason="Retry allowed inside autonomy phase",
        )
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))
        backlog_record = {
            "id": "backlog-123",
            "title": "Dispatch and Work-Economy Closure",
            "prompt": "Retry governed dispatch work",
            "owner_agent": "coding-agent",
            "support_agents": [],
            "scope_type": "global",
            "scope_id": "athanor",
            "work_class": "system_improvement",
            "priority": 4,
            "status": "running",
            "approval_mode": "none",
            "dispatch_policy": "planner_eligible",
            "preconditions": [],
            "blocking_reason": "",
            "linked_goal_ids": [],
            "linked_todo_ids": [],
            "linked_idea_id": "",
            "metadata": {"latest_task_id": "task-old", "latest_run_id": "task-old"},
            "created_by": "operator",
            "origin": "operator",
            "ready_at": 0.0,
            "scheduled_for": 0.0,
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_at": 0.0,
        }

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch(
                "athanor_agents.operator_state.fetch_backlog_record",
                AsyncMock(return_value=backlog_record),
            ),
            patch(
                "athanor_agents.operator_state.upsert_backlog_record",
                AsyncMock(),
            ) as mock_upsert_backlog,
        ):
            await _maybe_retry(task)

        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual("fail5", stored["metadata"]["retry_of"])
        self.assertEqual("auto-retry", stored["metadata"]["source"])
        self.assertEqual("backlog-123", stored["metadata"]["backlog_id"])
        self.assertEqual({"provider": "athanor_local"}, stored["metadata"]["execution_lease"])
        self.assertNotIn("latest_task_id", stored["metadata"])
        self.assertNotIn("latest_run_id", stored["metadata"])
        self.assertNotIn("last_dispatch_reason", stored["metadata"])
        self.assertNotIn("governor_reason", stored["metadata"])
        self.assertNotIn("governor_level", stored["metadata"])
        self.assertNotIn("execution_claim", stored["metadata"])
        self.assertNotIn("recovery", stored["metadata"])
        self.assertNotIn("failure", stored["metadata"])
        self.assertNotIn("execution_run_id", stored["metadata"])

        updated_backlog = mock_upsert_backlog.await_args.args[0]
        self.assertEqual("scheduled", updated_backlog["status"])
        self.assertEqual(stored["id"], updated_backlog["metadata"]["latest_task_id"])
        self.assertEqual(stored["id"], updated_backlog["metadata"]["latest_run_id"])
        self.assertIn("fail5", updated_backlog["metadata"]["last_dispatch_reason"])


class TestExecuteTaskFailures(unittest.IsolatedAsyncioTestCase):
    async def test_execute_task_records_nonempty_error_for_blank_string_exceptions(self):
        from athanor_agents.tasks import Task, _execute_task

        class ExplodingAgent:
            async def astream_events(self, *_args, **_kwargs):
                if False:
                    yield {}
                raise SilentError()

        breaker = types.SimpleNamespace(
            can_execute=AsyncMock(return_value=True),
            record_failure=AsyncMock(),
            record_success=AsyncMock(),
        )
        breakers = types.SimpleNamespace(get_or_create=lambda _agent: breaker)

        agents_stub = types.SimpleNamespace(get_agent=lambda _agent: ExplodingAgent())
        context_stub = types.SimpleNamespace(enrich_context=AsyncMock(return_value=""))
        activity_stub = types.SimpleNamespace(
            log_activity=AsyncMock(),
            log_event=AsyncMock(),
            log_conversation=AsyncMock(),
        )
        workspace_stub = types.SimpleNamespace(post_item=AsyncMock())
        escalation_stub = types.SimpleNamespace(add_notification=MagicMock())
        circuit_stub = types.SimpleNamespace(get_circuit_breakers=lambda: breakers)

        def _close_coro(coro):
            coro.close()
            return MagicMock()

        task = Task(
            id="explode1",
            agent="coding-agent",
            prompt="Force a blank-string failure",
            status="running",
            started_at=time.time(),
            last_heartbeat=time.time(),
            metadata={"source": "manual"},
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "athanor_agents.agents": agents_stub,
                    "athanor_agents.context": context_stub,
                    "athanor_agents.activity": activity_stub,
                    "athanor_agents.workspace": workspace_stub,
                    "athanor_agents.escalation": escalation_stub,
                    "athanor_agents.circuit_breaker": circuit_stub,
                },
            ),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks._maybe_retry", AsyncMock()) as maybe_retry,
            patch("athanor_agents.tasks._release_task_claim", AsyncMock()),
            patch("athanor_agents.tasks._record_skill_execution_for_task", AsyncMock()),
            patch("athanor_agents.tasks.asyncio.create_task", side_effect=_close_coro),
        ):
            await _execute_task(task)

        failed_task = persist_task_state.await_args.args[0]
        self.assertEqual("failed", failed_task.status)
        self.assertEqual("SilentError", failed_task.error)
        self.assertEqual("SilentError", failed_task.metadata["failure"]["type"])
        self.assertTrue(failed_task.metadata["failure"]["retry_eligible"])
        breaker.record_failure.assert_awaited_once()
        maybe_retry.assert_awaited_once()


class TestExecuteTaskProviderExecution(unittest.IsolatedAsyncioTestCase):
    async def test_execute_task_routes_async_backlog_leases_to_provider_execution(self):
        from athanor_agents.tasks import Task, _execute_task

        breaker = types.SimpleNamespace(
            can_execute=AsyncMock(return_value=True),
            record_failure=AsyncMock(),
            record_success=AsyncMock(),
        )
        breakers = types.SimpleNamespace(get_or_create=lambda _agent: breaker)
        agents_stub = types.SimpleNamespace(
            get_agent=lambda _agent: (_ for _ in ()).throw(AssertionError("local agent path should not run"))
        )
        context_stub = types.SimpleNamespace(enrich_context=AsyncMock(return_value=""))
        activity_stub = types.SimpleNamespace(
            log_activity=AsyncMock(),
            log_event=AsyncMock(),
            log_conversation=AsyncMock(),
        )
        workspace_stub = types.SimpleNamespace(post_item=AsyncMock())
        circuit_stub = types.SimpleNamespace(get_circuit_breakers=lambda: breakers)
        provider_execution_stub = types.SimpleNamespace(
            execute_provider_request=AsyncMock(
                return_value={
                    "status": "handoff_created",
                    "provider": "zai_glm_coding",
                    "message": "Direct execution is unavailable; structured handoff bundle created.",
                    "adapter": {
                        "execution_mode": "handoff_bundle",
                        "adapter_available": False,
                    },
                    "handoff": {
                        "id": "handoff-123",
                        "lease_id": "lease-123",
                        "status": "pending",
                        "execution_mode": "handoff_bundle",
                        "artifact_refs": [{"label": "tasks", "href": "/tasks"}],
                    },
                }
            )
        )

        task = Task(
            id="provider1",
            agent="coding-agent",
            prompt="Advance the governed dispatch claim.",
            status="running",
            started_at=time.time(),
            last_heartbeat=time.time(),
            metadata={
                "source": "operator_backlog",
                "task_class": "async_backlog_execution",
                "execution_lease": {
                    "id": "lease-123",
                    "provider": "zai_glm_coding",
                    "metadata": {
                        "expected_context": "medium",
                        "parallelism": "low",
                    },
                },
            },
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "athanor_agents.agents": agents_stub,
                    "athanor_agents.context": context_stub,
                    "athanor_agents.activity": activity_stub,
                    "athanor_agents.workspace": workspace_stub,
                    "athanor_agents.circuit_breaker": circuit_stub,
                    "athanor_agents.provider_execution": provider_execution_stub,
                },
            ),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks._maybe_retry", AsyncMock()) as maybe_retry,
            patch("athanor_agents.tasks._release_task_claim", AsyncMock()),
        ):
            await _execute_task(task)

        persisted_task = persist_task_state.await_args.args[0]
        self.assertEqual("completed", persisted_task.status)
        self.assertIn("Provider lane: zai_glm_coding", persisted_task.result)
        self.assertEqual(
            "handoff_created",
            persisted_task.metadata["provider_execution"]["status"],
        )
        self.assertEqual(
            "handoff-123",
            persisted_task.metadata["provider_execution"]["handoff_id"],
        )
        provider_execution_stub.execute_provider_request.assert_awaited_once()
        self.assertFalse(breaker.record_failure.await_count)
        self.assertFalse(breaker.record_success.await_count)
        maybe_retry.assert_not_awaited()

    async def test_execute_task_records_provider_execution_failure_and_retries(self):
        from athanor_agents.tasks import Task, _execute_task

        breaker = types.SimpleNamespace(
            can_execute=AsyncMock(return_value=True),
            record_failure=AsyncMock(),
            record_success=AsyncMock(),
        )
        breakers = types.SimpleNamespace(get_or_create=lambda _agent: breaker)
        agents_stub = types.SimpleNamespace(
            get_agent=lambda _agent: (_ for _ in ()).throw(AssertionError("local agent path should not run"))
        )
        context_stub = types.SimpleNamespace(enrich_context=AsyncMock(return_value=""))
        activity_stub = types.SimpleNamespace(
            log_activity=AsyncMock(),
            log_event=AsyncMock(),
            log_conversation=AsyncMock(),
        )
        workspace_stub = types.SimpleNamespace(post_item=AsyncMock())
        circuit_stub = types.SimpleNamespace(get_circuit_breakers=lambda: breakers)
        provider_execution_stub = types.SimpleNamespace(
            execute_provider_request=AsyncMock(
                return_value={
                    "status": "failed",
                    "provider": "zai_glm_coding",
                    "message": "Provider execution failed and no governed handoff fallback is available.",
                    "adapter": {
                        "execution_mode": "direct_cli",
                        "adapter_available": True,
                    },
                    "execution": {
                        "summary": "Direct execution failed.",
                        "stderr": "socket timeout",
                    },
                    "handoff": {
                        "id": "handoff-456",
                        "lease_id": "lease-456",
                        "status": "failed",
                        "execution_mode": "direct_cli",
                    },
                }
            )
        )

        task = Task(
            id="provider2",
            agent="coding-agent",
            prompt="Advance the governed dispatch claim.",
            status="running",
            started_at=time.time(),
            last_heartbeat=time.time(),
            metadata={
                "source": "operator_backlog",
                "task_class": "async_backlog_execution",
                "execution_lease": {
                    "id": "lease-456",
                    "provider": "zai_glm_coding",
                },
            },
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "athanor_agents.agents": agents_stub,
                    "athanor_agents.context": context_stub,
                    "athanor_agents.activity": activity_stub,
                    "athanor_agents.workspace": workspace_stub,
                    "athanor_agents.circuit_breaker": circuit_stub,
                    "athanor_agents.provider_execution": provider_execution_stub,
                },
            ),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks._maybe_retry", AsyncMock()) as maybe_retry,
            patch("athanor_agents.tasks._release_task_claim", AsyncMock()),
        ):
            await _execute_task(task)

        failed_task = persist_task_state.await_args.args[0]
        self.assertEqual("failed", failed_task.status)
        self.assertEqual("socket timeout", failed_task.error)
        self.assertEqual(
            "provider_execution_failed",
            failed_task.metadata["failure"]["type"],
        )
        maybe_retry.assert_awaited_once()


class TestSubmitTask(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_check_ignores_stale_lease_tasks(self):
        from athanor_agents.tasks import Task, _has_duplicate_pending

        mock_r = _mock_redis()
        stale = Task(
            id="stale1",
            agent="coding-agent",
            prompt="Write a contract test",
            status="stale_lease",
        ).to_dict()

        async def fake_read_task_records_by_statuses(_redis, *statuses, limit=None):
            return [stale] if "stale_lease" in statuses else []

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(side_effect=fake_read_task_records_by_statuses)) as read_records,
        ):
            existing = await _has_duplicate_pending("coding-agent", "Write a contract test")

        self.assertIsNone(existing)
        self.assertEqual(tuple(read_records.await_args.args[1:]), ("pending", "pending_approval", "running"))

    async def test_submit_task_persists_and_publishes_event(self):
        from athanor_agents.tasks import submit_task

        mock_r = _mock_redis()
        subscriptions_stub = types.SimpleNamespace(
            attach_task_execution_lease=AsyncMock(return_value={"source": "task_api"})
        )
        agents_stub = types.SimpleNamespace(list_agents=lambda: ["coding-agent"])

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks._has_duplicate_pending", AsyncMock(return_value=None)),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks.publish_task_event", AsyncMock()) as publish_task_event,
            patch.dict(
                sys.modules,
                {
                    "athanor_agents.agents": agents_stub,
                    "athanor_agents.subscriptions": subscriptions_stub,
                },
            ),
        ):
            task = await submit_task("coding-agent", "Write a contract test")

        self.assertEqual(task.agent, "coding-agent")
        persist_task_state.assert_awaited_once()
        publish_task_event.assert_awaited_once()
        published = publish_task_event.await_args.args[0]
        self.assertEqual("task_submitted", published["event"])
        self.assertEqual("coding-agent", published["agent"])

    async def test_submit_task_stamps_policy_execution_hints_before_leasing(self):
        from athanor_agents.tasks import submit_task

        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks._has_duplicate_pending", AsyncMock(return_value=None)),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()),
            patch("athanor_agents.tasks.publish_task_event", AsyncMock()),
            patch("athanor_agents.agents.list_agents", return_value=["knowledge-agent"]),
            patch(
                "athanor_agents.subscriptions.attach_task_execution_lease",
                AsyncMock(side_effect=lambda **kwargs: kwargs["metadata"]),
            ),
        ):
            task = await submit_task("knowledge-agent", "Review the indexed knowledge gaps and summarize them.")

        self.assertEqual("private_automation", task.metadata["task_class"])
        self.assertEqual("private", task.metadata["sensitivity"])
        self.assertEqual("small", task.metadata["expected_context"])
        self.assertEqual("low", task.metadata["parallelism"])

    def test_should_use_provider_execution_for_bounded_cloud_background_work(self):
        from athanor_agents.tasks import Task, _should_use_provider_execution

        task = Task(
            agent="coding-agent",
            prompt="Implement the next PR-sized change set.",
            metadata={
                "task_class": "multi_file_implementation",
                "interactive": False,
                "execution_lease": {
                    "provider": "openai_codex",
                    "task_class": "multi_file_implementation",
                },
            },
        )

        self.assertTrue(_should_use_provider_execution(task))

    def test_should_not_use_provider_execution_for_local_or_interactive_work(self):
        from athanor_agents.tasks import Task, _should_use_provider_execution

        local_task = Task(
            agent="knowledge-agent",
            prompt="Refresh internal context.",
            metadata={
                "task_class": "private_automation",
                "interactive": False,
                "execution_lease": {
                    "provider": "athanor_local",
                    "task_class": "private_automation",
                },
            },
        )
        interactive_task = Task(
            agent="coding-agent",
            prompt="Talk through the implementation tradeoffs.",
            metadata={
                "task_class": "multi_file_implementation",
                "interactive": True,
                "execution_lease": {
                    "provider": "openai_codex",
                    "task_class": "multi_file_implementation",
                },
            },
        )

        self.assertFalse(_should_use_provider_execution(local_task))
        self.assertFalse(_should_use_provider_execution(interactive_task))

    async def test_submit_governed_task_records_governor_context(self):
        from athanor_agents.tasks import Task, submit_governed_task

        decision = types.SimpleNamespace(
            status_override="pending",
            autonomy_level="B",
            reason="Level B - execute with notification",
        )
        task = Task(id="gov1", agent="coding-agent", prompt="Write a contract test")
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch("athanor_agents.tasks.submit_task", AsyncMock(return_value=task)) as submit_task_mock,
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            submission = await submit_governed_task(
                "coding-agent",
                "Write a contract test",
                priority="high",
                metadata={"source": "manual", "project": "core"},
                source="manual",
            )

        submit_metadata = submit_task_mock.await_args.kwargs["metadata"]
        self.assertEqual("Level B - execute with notification", submit_metadata["governor_decision"])
        self.assertEqual("B", submit_metadata["governor_autonomy_level"])
        self.assertEqual("pending", submit_metadata["governor_status_override"])
        self.assertNotIn("requires_approval", submit_metadata)
        persist_task_state.assert_not_awaited()
        self.assertEqual("gov1", submission.task.id)
        self.assertIs(submission.decision, decision)
        self.assertFalse(submission.held_for_approval)

    async def test_submit_governed_task_preserves_execution_hints(self):
        from athanor_agents.tasks import Task, submit_governed_task

        decision = types.SimpleNamespace(
            status_override="pending",
            autonomy_level="B",
            reason="Execute with notification",
        )
        task = Task(id="gov-hints", agent="coding-agent", prompt="Implement the next multi-file change")
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch("athanor_agents.tasks.submit_task", AsyncMock(return_value=task)) as submit_task_mock,
        ):
            await submit_governed_task(
                "coding-agent",
                "Implement the next multi-file change",
                metadata={"source": "manual", "task_class": "multi_file_implementation", "expected_context": "large"},
                source="manual",
            )

        submit_metadata = submit_task_mock.await_args.kwargs["metadata"]
        self.assertEqual("multi_file_implementation", submit_metadata["task_class"])
        self.assertEqual("large", submit_metadata["expected_context"])

    async def test_submit_governed_task_persists_pending_approval_override(self):
        from athanor_agents.tasks import Task, submit_governed_task

        decision = types.SimpleNamespace(
            status_override="pending_approval",
            autonomy_level="D",
            reason="Requires approval",
        )
        task = Task(
            id="gov2",
            agent="general-assistant",
            prompt="Generate digest",
            status="pending",
            metadata={"source": "scheduler"},
        )
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch("athanor_agents.tasks.submit_task", AsyncMock(return_value=task)) as submit_task_mock,
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            submission = await submit_governed_task(
                "general-assistant",
                "Generate digest",
                metadata={"source": "scheduler", "date": "2026-03-27"},
                source="scheduler",
            )

        submit_metadata = submit_task_mock.await_args.kwargs["metadata"]
        self.assertTrue(submit_metadata["requires_approval"])
        self.assertEqual("D", submit_metadata["governor_autonomy_level"])
        self.assertEqual("pending_approval", submit_metadata["governor_status_override"])
        persist_task_state.assert_awaited_once_with(task)
        self.assertEqual("pending_approval", task.status)
        self.assertTrue(submission.held_for_approval)

    async def test_submit_governed_task_stamps_governor_metadata_and_requires_approval(self):
        from athanor_agents.tasks import GovernedTaskSubmission, Task, submit_governed_task

        decision = types.SimpleNamespace(
            autonomy_level="B",
            reason="Needs operator review",
            status_override="pending_approval",
        )
        task = Task(id="gov-1", agent="coding-agent", prompt="Review", status="pending_approval")
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch("athanor_agents.tasks.submit_task", AsyncMock(return_value=task)) as submit_task_mock,
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            result = await submit_governed_task(
                "coding-agent",
                "Review contract",
                priority="high",
                metadata={"project": "athanor"},
                source="manual",
            )

        self.assertIsInstance(result, GovernedTaskSubmission)
        self.assertIs(result.task, task)
        self.assertIs(result.decision, decision)
        self.assertTrue(result.held_for_approval)
        submit_kwargs = submit_task_mock.await_args.kwargs
        self.assertEqual("manual", submit_kwargs["metadata"]["source"])
        self.assertEqual("Needs operator review", submit_kwargs["metadata"]["governor_decision"])
        self.assertTrue(submit_kwargs["metadata"]["requires_approval"])
        self.assertEqual("athanor", submit_kwargs["metadata"]["project"])
        persist_task_state.assert_not_awaited()

    async def test_submit_governed_task_persists_override_when_submitter_bypasses_pending_state(self):
        from athanor_agents.tasks import Task, submit_governed_task

        decision = types.SimpleNamespace(
            autonomy_level="B",
            reason="Scheduler-held for approval",
            status_override="pending_approval",
        )
        task = Task(id="gov-2", agent="general-assistant", prompt="Digest", status="pending")
        governor = types.SimpleNamespace(gate_task_submission=AsyncMock(return_value=decision))

        with (
            patch("athanor_agents.governor.Governor.get", return_value=governor),
            patch("athanor_agents.tasks.submit_task", AsyncMock(return_value=task)),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            result = await submit_governed_task(
                "general-assistant",
                "Generate digest",
                metadata={"source": "daily_digest"},
                source="scheduler",
            )

        self.assertTrue(result.held_for_approval)
        self.assertEqual("pending_approval", task.status)
        persist_task_state.assert_awaited_once_with(task)


class TestTaskClaiming(unittest.IsolatedAsyncioTestCase):
    async def test_claim_pending_task_sets_running_state(self):
        from athanor_agents.tasks import Task, _claim_pending_task

        task_data = Task(id="claim1", agent="coding-agent", prompt="Fix drift", status="pending").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(task_data))

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            claimed = await _claim_pending_task("claim1", trigger="worker")

        self.assertIsNotNone(claimed)
        self.assertEqual("running", claimed.status)
        self.assertIn("execution_claim", claimed.metadata)
        mock_r.set.assert_awaited_once()
        persist_task_state.assert_awaited_once()

    async def test_claim_pending_task_returns_none_when_already_claimed(self):
        from athanor_agents.tasks import _claim_pending_task

        mock_r = _mock_redis()
        mock_r.set = AsyncMock(return_value=False)

        with patch("athanor_agents.tasks._get_redis", return_value=mock_r):
            claimed = await _claim_pending_task("claim2", trigger="dashboard")

        self.assertIsNone(claimed)


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

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch(
                "athanor_agents.tasks.read_task_records_by_statuses",
                AsyncMock(return_value=[old_task.to_dict()]),
            ),
        ):
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

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=[recent_task.to_dict()])),
        ):
            await _cleanup_old_tasks()

        mock_r.hdel.assert_not_called()


class TestRecoverStaleTasks(unittest.IsolatedAsyncioTestCase):
    """Test restart recovery for in-flight tasks."""

    async def test_marks_running_tasks_stale_and_retries(self):
        from athanor_agents.tasks import Task, _recover_stale_tasks

        mock_r = _mock_redis()
        running = Task(
            id="stale1",
            agent="coding-agent",
            prompt="Write tests",
            status="running",
            retry_count=0,
        ).to_dict()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_status", AsyncMock(return_value=[running])),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks._maybe_retry", AsyncMock()) as mock_retry,
        ):
            await _recover_stale_tasks()

        recovered_task = persist_task_state.await_args.args[0]
        self.assertEqual(recovered_task.status, "stale_lease")
        self.assertEqual(recovered_task.error, "Execution lease expired during server restart")
        self.assertEqual(recovered_task.metadata["recovery"]["event"], "stale_lease_recovered")
        mock_retry.assert_awaited_once()

    async def test_does_not_retry_exhausted_stale_task(self):
        from athanor_agents.tasks import Task, _recover_stale_tasks, MAX_TASK_RETRIES

        mock_r = _mock_redis()
        running = Task(
            id="stale2",
            agent="coding-agent",
            prompt="Write tests",
            status="running",
            retry_count=MAX_TASK_RETRIES,
        ).to_dict()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_status", AsyncMock(return_value=[running])),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
            patch("athanor_agents.tasks._maybe_retry", AsyncMock()) as mock_retry,
        ):
            await _recover_stale_tasks()

        recovered_task = persist_task_state.await_args.args[0]
        self.assertEqual(recovered_task.status, "stale_lease")
        mock_retry.assert_not_awaited()

    async def test_keeps_pending_tasks_regardless_of_age(self):
        from athanor_agents.tasks import _cleanup_old_tasks, Task

        old_pending = Task(
            id="pending1",
            status="pending",
            completed_at=0,
        )
        tasks = {"pending1": json.dumps(old_pending.to_dict())}
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=[])),
        ):
            await _cleanup_old_tasks()

        mock_r.hdel.assert_not_called()


class TestTaskStats(unittest.IsolatedAsyncioTestCase):
    async def test_get_task_stats_includes_flattened_status_counts(self):
        from athanor_agents.tasks import Task, get_task_stats

        records = [
            Task(id="p1", status="pending", agent="coding-agent", created_at=1000).to_dict(),
            Task(id="r1", status="running", agent="coding-agent", created_at=1001, started_at=1001).to_dict(),
            Task(
                id="c1",
                status="completed",
                agent="research-agent",
                created_at=1000,
                started_at=1001,
                completed_at=1003,
            ).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            stats = await get_task_stats()

        self.assertEqual(1, stats["pending"])
        self.assertEqual(1, stats["running"])
        self.assertEqual(1, stats["completed"])
        self.assertEqual(0, stats["failed"])
        self.assertEqual(0, stats["pending_approval"])
        self.assertEqual(0, stats["cancelled"])
        self.assertEqual(0, stats["stale_lease"])
        self.assertEqual(1, stats["by_status"]["pending"])
        self.assertEqual(1, stats["currently_running"])
        self.assertTrue(stats["worker_running"])

    async def test_get_task_stats_uses_recorded_running_and_pending_truth(self):
        from athanor_agents.tasks import Task, get_task_stats

        records = [
            Task(id="p1", status="pending", agent="coding-agent", created_at=1000).to_dict(),
            Task(id="r1", status="running", agent="research-agent", created_at=1001, started_at=1002).to_dict(),
            Task(id="r2", status="running", agent="home-agent", created_at=1003, started_at=1004).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
            patch("athanor_agents.tasks._worker_task", None),
            patch("athanor_agents.tasks._running_count", 0),
        ):
            stats = await get_task_stats()

        self.assertEqual(2, stats["running"])
        self.assertEqual(2, stats["currently_running"])
        self.assertTrue(stats["worker_running"])

    async def test_get_task_stats_falls_back_to_durable_state(self):
        from athanor_agents.tasks import get_task_stats

        with (
            patch("athanor_agents.tasks._get_redis", AsyncMock(side_effect=RuntimeError("redis unavailable"))),
            patch(
                "athanor_agents.tasks.get_task_snapshot_stats",
                AsyncMock(return_value={"total": 4, "by_status": {"pending": 1, "running": 2, "completed": 1}}),
            ),
            patch("athanor_agents.tasks._worker_task", None),
            patch("athanor_agents.tasks._running_count", 0),
        ):
            stats = await get_task_stats()

        self.assertEqual(4, stats["total"])
        self.assertEqual(1, stats["pending"])
        self.assertEqual(2, stats["running"])
        self.assertEqual(1, stats["completed"])
        self.assertEqual(2, stats["currently_running"])
        self.assertTrue(stats["worker_running"])
        self.assertEqual("durable_state_fallback", stats["source"])
        self.assertEqual(0, stats["failed_missing_detail"])
        self.assertEqual(0, stats["stale_lease_actionable"])
        self.assertEqual(0, stats["stale_lease_recovered_historical"])

    async def test_get_task_stats_breaks_out_failed_detail_quality(self):
        from athanor_agents.tasks import Task, get_task_stats

        records = [
            Task(id="f1", status="failed", agent="home-agent", error="", metadata={}).to_dict(),
            Task(id="f2", status="failed", agent="media-agent", error="Timed out", metadata={}).to_dict(),
            Task(
                id="f3",
                status="failed",
                agent="coding-agent",
                error="",
                metadata={"failure": {"message": "Circuit breaker open", "type": "circuit_breaker_open"}},
            ).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            stats = await get_task_stats()

        self.assertEqual(3, stats["failed"])
        self.assertEqual(2, stats["failed_with_detail"])
        self.assertEqual(2, stats["failed_actionable"])
        self.assertEqual(0, stats["failed_historical_repaired"])
        self.assertEqual(1, stats["failed_missing_detail"])
        self.assertEqual(1, stats["failure_detail_quality"]["failed_missing_detail"])
        self.assertEqual(2, stats["failure_detail_quality"]["failed_actionable"])

    async def test_get_task_stats_separates_historical_repaired_failures(self):
        from athanor_agents.tasks import Task, get_task_stats

        records = [
            Task(
                id="legacy-repaired",
                status="failed",
                agent="general-assistant",
                error="Legacy failed task missing recorded failure detail",
                metadata={
                    "failure": {
                        "message": "Legacy failed task missing recorded failure detail",
                        "type": "historical_failure_detail_missing",
                        "historical_residue": True,
                        "synthetic": True,
                    },
                    "failure_repair": {"source": "startup_legacy_failed_task_backfill"},
                },
            ).to_dict(),
            Task(id="recent-fail", status="failed", agent="coding-agent", error="Timed out", metadata={}).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            stats = await get_task_stats()

        self.assertEqual(2, stats["failed"])
        self.assertEqual(2, stats["failed_with_detail"])
        self.assertEqual(1, stats["failed_actionable"])
        self.assertEqual(1, stats["failed_historical_repaired"])
        self.assertEqual(0, stats["failed_missing_detail"])

    async def test_get_task_stats_separates_recovered_stale_leases(self):
        from athanor_agents.tasks import Task, get_task_stats

        records = [
            Task(
                id="recovered-stale",
                status="stale_lease",
                agent="coding-agent",
                error="Execution lease expired during server restart",
                metadata={
                    "recovery": {
                        "event": "stale_lease_recovered",
                        "reason": "server_restart",
                    }
                },
            ).to_dict(),
            Task(
                id="live-stale",
                status="stale_lease",
                agent="research-agent",
                error="Execution lease expired during remote disconnect",
                metadata={},
            ).to_dict(),
        ]
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_statuses", AsyncMock(return_value=records)),
        ):
            stats = await get_task_stats()

        self.assertEqual(2, stats["stale_lease"])
        self.assertEqual(1, stats["stale_lease_actionable"])
        self.assertEqual(1, stats["stale_lease_recovered_historical"])


class TestDurableTaskPersistence(unittest.IsolatedAsyncioTestCase):
    async def test_persist_task_state_dual_writes_to_durable_store(self):
        from athanor_agents.tasks import Task, persist_task_state

        task = Task(id="dual1", agent="coding-agent", prompt="Fix drift")
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.write_task_record", AsyncMock(return_value=task.to_dict())),
            patch("athanor_agents.tasks.upsert_task_snapshot", AsyncMock(return_value=True)) as upsert_task_snapshot,
            patch("athanor_agents.tasks.sync_task_execution_projection", AsyncMock(return_value=None)) as sync_task_execution_projection,
        ):
            await persist_task_state(task)

        upsert_task_snapshot.assert_awaited_once()

    async def test_repair_legacy_failed_task_details_backfills_durable_metadata(self):
        from athanor_agents.tasks import LEGACY_FAILED_TASK_DETAIL, Task, repair_legacy_failed_task_details

        legacy_task = Task(
            id="legacy-fail",
            agent="general-assistant",
            status="failed",
            error="",
            created_at=1004,
            updated_at=1005,
            metadata={},
        ).to_dict()
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_records_by_status", AsyncMock(return_value=[legacy_task])),
            patch("athanor_agents.tasks.persist_task_state", AsyncMock()) as persist_task_state,
        ):
            repaired = await repair_legacy_failed_task_details()

        self.assertEqual(1, repaired)
        repaired_task = persist_task_state.await_args.args[0]
        self.assertEqual(1005, repaired_task.updated_at)
        self.assertEqual(LEGACY_FAILED_TASK_DETAIL, repaired_task.error)
        self.assertTrue(repaired_task.metadata["failure"]["historical_residue"])
        self.assertTrue(repaired_task.metadata["failure"]["synthetic"])
        self.assertEqual("startup_legacy_failed_task_backfill", repaired_task.metadata["failure_repair"]["source"])
        self.assertTrue(persist_task_state.await_args.kwargs["preserve_updated_at"])

    async def test_get_task_falls_back_to_durable_snapshot(self):
        from athanor_agents.tasks import Task, get_task

        durable_record = Task(id="fallback1", agent="research-agent", prompt="Research").to_dict()
        mock_r = _mock_redis()

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_record", AsyncMock(return_value=None)),
            patch("athanor_agents.tasks.fetch_task_snapshot", AsyncMock(return_value=durable_record)) as fetch_task_snapshot,
        ):
            task = await get_task("fallback1")

        self.assertIsNotNone(task)
        self.assertEqual("fallback1", task.id)
        fetch_task_snapshot.assert_awaited_once_with("fallback1")

    async def test_list_tasks_falls_back_to_durable_snapshot(self):
        from athanor_agents.tasks import Task, list_tasks

        durable_record = Task(id="fallback2", agent="coding-agent", prompt="Build", status="running").to_dict()

        with (
            patch("athanor_agents.tasks._get_redis", AsyncMock(side_effect=RuntimeError("redis unavailable"))),
            patch("athanor_agents.tasks.list_task_snapshots", AsyncMock(return_value=[durable_record])) as list_task_snapshots,
        ):
            tasks = await list_tasks(statuses=["running"], limit=5)

        self.assertEqual(["fallback2"], [task["id"] for task in tasks])
        list_task_snapshots.assert_awaited_once_with(statuses=["running"], agent="", limit=5)


class TestListRecentTasks(unittest.IsolatedAsyncioTestCase):
    async def test_list_recent_tasks_uses_updated_index_order(self):
        from athanor_agents.tasks import Task, list_recent_tasks

        mock_r = _mock_redis()
        mock_r.zrevrange = AsyncMock(return_value=["t3", "t2", "t1"])
        records = {
            "t1": Task(id="t1", agent="coding-agent", status="completed", updated_at=1001, created_at=1000).to_dict(),
            "t2": Task(id="t2", agent="coding-agent", status="running", updated_at=1003, created_at=1002).to_dict(),
            "t3": Task(id="t3", agent="research-agent", status="pending", updated_at=1005, created_at=1004).to_dict(),
        }

        async def _read_task_record(_redis, task_id):
            return records.get(task_id)

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_record", AsyncMock(side_effect=_read_task_record)),
        ):
            result = await list_recent_tasks(limit=3)

        self.assertEqual(["t3", "t2", "t1"], [task["id"] for task in result])

    async def test_list_recent_tasks_filters_agent_and_status(self):
        from athanor_agents.tasks import Task, list_recent_tasks

        mock_r = _mock_redis()
        mock_r.zrevrange = AsyncMock(return_value=["t3", "t2", "t1"])
        records = {
            "t1": Task(id="t1", agent="coding-agent", status="completed", updated_at=1001, created_at=1000).to_dict(),
            "t2": Task(id="t2", agent="coding-agent", status="running", updated_at=1003, created_at=1002).to_dict(),
            "t3": Task(id="t3", agent="research-agent", status="pending", updated_at=1005, created_at=1004).to_dict(),
        }

        async def _read_task_record(_redis, task_id):
            return records.get(task_id)

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_record", AsyncMock(side_effect=_read_task_record)),
        ):
            result = await list_recent_tasks(agent="coding-agent", statuses=["running", "completed"], limit=5)

        self.assertEqual(["t2", "t1"], [task["id"] for task in result])

    async def test_list_recent_tasks_normalizes_legacy_failed_rows(self):
        from athanor_agents.tasks import LEGACY_FAILED_TASK_DETAIL, Task, list_recent_tasks

        mock_r = _mock_redis()
        mock_r.zrevrange = AsyncMock(return_value=["legacy-fail"])
        records = {
            "legacy-fail": Task(
                id="legacy-fail",
                agent="general-assistant",
                status="failed",
                error="",
                updated_at=1005,
                created_at=1004,
                metadata={},
            ).to_dict(),
        }

        async def _read_task_record(_redis, task_id):
            return records.get(task_id)

        with (
            patch("athanor_agents.tasks._get_redis", return_value=mock_r),
            patch("athanor_agents.tasks.read_task_record", AsyncMock(side_effect=_read_task_record)),
        ):
            result = await list_recent_tasks(limit=5)

        self.assertEqual(LEGACY_FAILED_TASK_DETAIL, result[0]["error"])
        self.assertTrue(result[0]["metadata"]["failure_display"]["legacy_record"])


class TestManualDispatch(unittest.TestCase):
    """Test manual dispatch through the canonical task engine."""

    def test_dispatch_next_pending_task_returns_empty_when_no_tasks_exist(self):
        from athanor_agents.tasks import dispatch_next_pending_task

        with patch("athanor_agents.tasks._get_next_pending", AsyncMock(return_value=None)):
            result = asyncio.run(dispatch_next_pending_task())

        self.assertEqual("empty", result["status"])

    def test_dispatch_next_pending_task_persists_and_schedules_task(self):
        from athanor_agents.tasks import Task, dispatch_next_pending_task

        task = Task(id="task-123", agent="coding-agent", prompt="Fix the contract drift")
        claimed_task = Task(
            id="task-123",
            agent="coding-agent",
            prompt="Fix the contract drift",
            status="running",
            started_at=1000.0,
            last_heartbeat=1000.0,
        )

        with (
            patch("athanor_agents.tasks._get_next_pending", AsyncMock(return_value=task)),
            patch("athanor_agents.tasks._evaluate_dispatch_gate", AsyncMock(return_value=(True, ""))),
            patch("athanor_agents.tasks._claim_pending_task", AsyncMock(return_value=claimed_task)) as claim_task,
            patch("athanor_agents.tasks.asyncio.create_task") as create_task,
            patch("athanor_agents.tasks._execute_task", AsyncMock()),
        ):
            result = asyncio.run(dispatch_next_pending_task(trigger="dashboard"))
            scheduled = create_task.call_args.args[0]
            scheduled.close()

        self.assertEqual("dispatched", result["status"])
        self.assertEqual("running", claimed_task.status)
        self.assertEqual("task-123", result["task"]["id"])
        claim_task.assert_awaited_once_with("task-123", trigger="dashboard")
        create_task.assert_called_once()

    def test_dispatch_next_pending_task_reports_claimed_elsewhere(self):
        from athanor_agents.tasks import Task, dispatch_next_pending_task

        task = Task(id="task-123", agent="coding-agent", prompt="Fix the contract drift")

        with (
            patch("athanor_agents.tasks._get_next_pending", AsyncMock(return_value=task)),
            patch("athanor_agents.tasks._evaluate_dispatch_gate", AsyncMock(return_value=(True, ""))),
            patch("athanor_agents.tasks._claim_pending_task", AsyncMock(return_value=None)),
        ):
            result = asyncio.run(dispatch_next_pending_task(trigger="dashboard"))

        self.assertEqual("claimed_elsewhere", result["status"])
        self.assertEqual("task-123", result["task"]["id"])


if __name__ == "__main__":
    unittest.main()
