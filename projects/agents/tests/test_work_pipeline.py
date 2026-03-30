from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from athanor_agents.work_pipeline import _check_starvation, run_pipeline_cycle


class WorkPipelineTaskEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_starvation_uses_canonical_task_event_helper(self) -> None:
        mock_r = AsyncMock()
        stale_timestamp = time.time() - (25 * 3600)
        mock_r.hgetall = AsyncMock(
            return_value={
                b"project-alpha": str(stale_timestamp).encode(),
            }
        )
        mock_r.publish = AsyncMock()

        with (
            patch("athanor_agents.work_pipeline._get_redis", return_value=mock_r),
            patch(
                "athanor_agents.tasks.submit_governed_task",
                AsyncMock(return_value=SimpleNamespace(task=SimpleNamespace(id="task-1"), held_for_approval=False)),
            ) as submit_governed_task,
            patch("athanor_agents.tasks.publish_task_event", AsyncMock()) as publish_task_event,
        ):
            await _check_starvation()

        submit_governed_task.assert_awaited_once_with(
            agent="general-assistant",
            prompt=(
                "Project 'project-alpha' has had no activity for over 24 hours. "
                "Review its current status, check for blockers, and suggest "
                "the next actionable step. Be specific and practical."
            ),
            priority="low",
            metadata={"source": "pipeline", "trigger": "starvation_recovery", "project": "project-alpha", "task_class": "workplan_generation"},
            source="pipeline",
        )
        publish_task_event.assert_awaited_once()
        payload = publish_task_event.await_args.args[0]
        self.assertEqual("starvation_detected", payload["event"])
        self.assertEqual(["project-alpha"], payload["projects"])
        mock_r.publish.assert_not_awaited()

    async def test_run_pipeline_cycle_submits_decomposed_tasks_via_canonical_governed_helper(self) -> None:
        intent = SimpleNamespace(text="Fix provider drift", source="synth", priority_hint="high", metadata={})
        plan = SimpleNamespace(
            id="plan-1",
            title="Fix provider drift",
            risk_level="low",
            estimated_minutes=20,
            assigned_agents=["coding-agent"],
            status="approved",
            metadata={},
        )
        submission = SimpleNamespace(task=SimpleNamespace(id="task-1"), held_for_approval=True)
        gate_task_submission = AsyncMock(
            return_value=SimpleNamespace(allowed=True, status_override="pending", autonomy_level="A")
        )

        with (
            patch("athanor_agents.tasks.get_task_stats", AsyncMock(return_value={"by_status": {"pending": 0}})),
            patch("athanor_agents.owner_model.ensure_fresh", AsyncMock()),
            patch("athanor_agents.intent_synthesizer.synthesize_strategic_intents", AsyncMock(return_value=[intent])),
            patch("athanor_agents.intent_miner.mine_all_sources", AsyncMock(return_value=[])),
            patch("athanor_agents.plan_generator.is_duplicate_intent", AsyncMock(return_value=False)),
            patch("athanor_agents.plan_generator.record_intent_hash", AsyncMock()),
            patch(
                "athanor_agents.plan_generator.generate_plan_from_intent",
                AsyncMock(return_value=plan),
            ) as generate_plan_from_intent,
            patch("athanor_agents.plan_generator.decompose_plan_to_tasks", AsyncMock(return_value=[{
                "agent": "coding-agent",
                "prompt": "Close provider drift",
                "priority": "high",
                "metadata": {"source": "pipeline", "plan_id": "plan-1"},
            }])),
            patch("athanor_agents.plan_generator.approve_plan", AsyncMock(return_value=plan)),
            patch(
                "athanor_agents.governor.Governor.get",
                return_value=SimpleNamespace(gate_task_submission=gate_task_submission),
            ),
            patch("athanor_agents.tasks.submit_governed_task", AsyncMock(return_value=submission)) as submit_governed_task,
            patch("athanor_agents.work_pipeline._record_cycle", AsyncMock()),
            patch("athanor_agents.work_pipeline._check_starvation", AsyncMock()),
        ):
            result = await run_pipeline_cycle()

        gate_task_submission.assert_awaited_once_with(
            agent="coding-agent",
            prompt="Fix provider drift",
            priority="normal",
            metadata={"source": "pipeline", "plan_id": "plan-1", "task_class": "workplan_generation"},
            source="pipeline",
        )
        plan_metadata = generate_plan_from_intent.await_args.kwargs["metadata"]
        self.assertTrue(plan_metadata["_autonomy_managed"])
        self.assertEqual("pipeline", plan_metadata["_autonomy_source"])
        submit_governed_task.assert_awaited_once_with(
            agent="coding-agent",
            prompt="Close provider drift",
            priority="high",
            metadata={"source": "pipeline", "plan_id": "plan-1"},
            source="pipeline",
        )
        self.assertEqual(0, result.tasks_submitted)
        self.assertEqual(1, result.tasks_held)
