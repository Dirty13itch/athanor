import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

from athanor_agents.workplanner import generate_work_plan


class _FakeResponse:
    def __init__(self, content: str = "[]") -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeAsyncClient:
    def __init__(self, content: str = "[]") -> None:
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        return _FakeResponse(self._content)


class _FakeRedis:
    async def get(self, key):
        return None

    async def set(self, *args, **kwargs):
        return None

    async def lpush(self, *args, **kwargs):
        return None

    async def ltrim(self, *args, **kwargs):
        return None


class WorkPlannerTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_work_plan_reads_recent_and_pending_from_canonical_surfaces(self) -> None:
        with (
            patch("athanor_agents.tasks.list_recent_tasks", AsyncMock(side_effect=[[], []])) as list_recent_tasks,
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value={"pending": 0, "pending_approval": 0})),
            patch(
                "athanor_agents.workplanner._gather_knowledge_context",
                AsyncMock(return_value={"knowledge": [], "preferences": [], "goals": [], "completed_outputs": []}),
            ),
            patch("athanor_agents.workplanner.httpx.AsyncClient", return_value=_FakeAsyncClient()),
        ):
            result = await generate_work_plan()

        self.assertEqual(
            [
                call(limit=20),
                call(statuses=["pending", "pending_approval"], limit=20),
            ],
            list_recent_tasks.await_args_list,
        )
        self.assertEqual(0, result["task_count"])
        self.assertEqual("No tasks generated", result["error"])

    async def test_should_refill_uses_task_stats_instead_of_capped_samples(self) -> None:
        from athanor_agents.workplanner import should_refill

        with (
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value={"pending": 1, "pending_approval": 0})),
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=_FakeRedis())),
        ):
            self.assertTrue(await should_refill())

        with (
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value={"pending": 2, "pending_approval": 0})),
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=_FakeRedis())),
        ):
            self.assertFalse(await should_refill())

    async def test_generate_work_plan_submits_tasks_via_canonical_governed_helper(self) -> None:
        response_payload = """
[
  {
    "project": "athanor",
    "agent": "research-agent",
    "priority": "high",
    "prompt": "Audit remaining provider truth drift",
    "rationale": "Close routing evidence gaps"
  }
]
"""
        submission = SimpleNamespace(task=SimpleNamespace(id="task-77"))
        with (
            patch("athanor_agents.tasks.list_recent_tasks", AsyncMock(side_effect=[[], []])),
            patch(
                "athanor_agents.workplanner._gather_knowledge_context",
                AsyncMock(return_value={"knowledge": [], "preferences": [], "goals": [], "completed_outputs": []}),
            ),
            patch("athanor_agents.workplanner.httpx.AsyncClient", return_value=_FakeAsyncClient(response_payload)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=_FakeRedis())),
            patch("athanor_agents.activity.log_event", AsyncMock()),
            patch("athanor_agents.workplanner.asyncio.create_task", side_effect=lambda coro: coro.close()),
        ):
            result = await generate_work_plan(focus="provider truth")

        self.assertEqual(1, result["task_count"])
        submit_governed_task.assert_awaited_once_with(
            agent="research-agent",
            prompt="Audit remaining provider truth drift",
            priority="high",
            metadata={
                "source": "work_planner",
                "plan_id": result["plan_id"],
                "project": "athanor",
                "rationale": "Close routing evidence gaps",
                "_autonomy_managed": False,
                "autonomy_phase_id": None,
            },
            source="work_planner",
        )

    async def test_generate_work_plan_filters_autonomy_managed_tasks_to_allowed_agents(self) -> None:
        response_payload = """
[
  {
    "project": "athanor",
    "agent": "creative-agent",
    "priority": "high",
    "prompt": "Generate the next queen portrait",
    "rationale": "Creative lane"
  },
  {
    "project": "athanor",
    "agent": "coding-agent",
    "priority": "high",
    "prompt": "Close the next repo contract seam",
    "rationale": "Core autonomy lane"
  }
]
"""
        submission = SimpleNamespace(task=SimpleNamespace(id="task-88"))
        with (
            patch("athanor_agents.tasks.list_recent_tasks", AsyncMock(side_effect=[[], []])),
            patch(
                "athanor_agents.workplanner._gather_knowledge_context",
                AsyncMock(return_value={"knowledge": [], "preferences": [], "goals": [], "completed_outputs": []}),
            ),
            patch(
                "athanor_agents.workplanner._load_autonomy_submission_scope",
                return_value=({"coding-agent", "research-agent"}, "software_core_phase_1"),
            ),
            patch("athanor_agents.workplanner.httpx.AsyncClient", return_value=_FakeAsyncClient(response_payload)),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
            patch("athanor_agents.workspace.get_redis", AsyncMock(return_value=_FakeRedis())),
            patch("athanor_agents.activity.log_event", AsyncMock()),
            patch("athanor_agents.workplanner.asyncio.create_task", side_effect=lambda coro: coro.close()),
        ):
            result = await generate_work_plan(focus="core autonomy", autonomy_managed=True)

        self.assertEqual(1, result["task_count"])
        submit_governed_task.assert_awaited_once_with(
            agent="coding-agent",
            prompt="Close the next repo contract seam",
            priority="high",
            metadata={
                "source": "work_planner",
                "plan_id": result["plan_id"],
                "project": "athanor",
                "rationale": "Core autonomy lane",
                "_autonomy_managed": True,
                "autonomy_phase_id": "software_core_phase_1",
            },
            source="work_planner",
        )
