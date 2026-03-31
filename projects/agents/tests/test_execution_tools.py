import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


class _FakeTool:
    def __init__(self, func):
        self.func = func

    async def ainvoke(self, payload):
        return await self.func(**payload)


def _langchain_tool(*args, **kwargs):
    if args and callable(args[0]) and not kwargs:
        return _FakeTool(args[0])

    def decorator(func):
        return _FakeTool(func)

    return decorator


class TestDelegateToAgent(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_to_agent_uses_governed_submission(self):
        langchain_core = types.ModuleType("langchain_core")
        langchain_tools = types.ModuleType("langchain_core.tools")
        langchain_tools.tool = _langchain_tool
        langchain_core.tools = langchain_tools

        with patch.dict(
            sys.modules,
            {
                "langchain_core": langchain_core,
                "langchain_core.tools": langchain_tools,
            },
        ):
            from athanor_agents.tools.execution import delegate_to_agent

        submission = types.SimpleNamespace(
            task=types.SimpleNamespace(id="task-123", status="pending"),
            held_for_approval=False,
        )

        with patch(
            "athanor_agents.tasks.submit_governed_task",
            AsyncMock(return_value=submission),
        ) as submit_governed_task:
            result = await delegate_to_agent.ainvoke(
                {
                    "agent_name": "research-agent",
                    "prompt": "Research the latest autonomy blockers",
                    "priority": "high",
                }
            )

        submit_governed_task.assert_awaited_once()
        kwargs = submit_governed_task.await_args.kwargs
        self.assertEqual("research-agent", kwargs["agent"])
        self.assertEqual("Research the latest autonomy blockers", kwargs["prompt"])
        self.assertEqual("high", kwargs["priority"])
        self.assertEqual("delegation", kwargs["source"])
        self.assertEqual("delegation", kwargs["metadata"]["source"])
        self.assertEqual(
            "delegate_to_agent",
            kwargs["metadata"]["delegation"]["submitted_via"],
        )
        self.assertEqual(
            "research-agent",
            kwargs["metadata"]["delegation"]["target_agent"],
        )
        self.assertIn("task-123", result)

    async def test_delegate_to_agent_reports_pending_approval(self):
        langchain_core = types.ModuleType("langchain_core")
        langchain_tools = types.ModuleType("langchain_core.tools")
        langchain_tools.tool = _langchain_tool
        langchain_core.tools = langchain_tools

        with patch.dict(
            sys.modules,
            {
                "langchain_core": langchain_core,
                "langchain_core.tools": langchain_tools,
            },
        ):
            from athanor_agents.tools.execution import delegate_to_agent

        submission = types.SimpleNamespace(
            task=types.SimpleNamespace(id="task-456", status="pending_approval"),
            held_for_approval=True,
        )

        with patch(
            "athanor_agents.tasks.submit_governed_task",
            AsyncMock(return_value=submission),
        ):
            result = await delegate_to_agent.ainvoke(
                {
                    "agent_name": "coding-agent",
                    "prompt": "Implement the next tranche",
                    "priority": "normal",
                }
            )

        self.assertIn("held for approval", result)
        self.assertIn("task-456", result)


if __name__ == "__main__":
    unittest.main()
