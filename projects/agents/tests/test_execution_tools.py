import types
import unittest
from unittest.mock import AsyncMock, patch


class TestDelegateToAgent(unittest.IsolatedAsyncioTestCase):
    async def test_delegate_to_agent_uses_governed_submission(self):
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
