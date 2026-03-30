from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from athanor_agents.governor_runtime import Governor


class GovernorRuntimePhaseGateTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _policy(
        *,
        phase_id: str = "software_core_phase_1",
        is_active: bool = True,
        activation_state: str = "software_core_active",
        phase_status: str = "active",
        enabled_agents: list[str] | None = None,
        allowed_workload_classes: list[str] | None = None,
        blocked_workload_classes: list[str] | None = None,
        unmet_prerequisite_ids: tuple[str, ...] = (),
        broad_autonomy_enabled: bool = False,
        runtime_mutations_approval_gated: bool = True,
    ):
        return SimpleNamespace(
            phase_id=phase_id,
            is_active=is_active,
            activation_state=activation_state,
            phase_status=phase_status,
            enabled_agents=frozenset(
                enabled_agents
                or ["coding-agent", "research-agent", "knowledge-agent", "general-assistant"]
            ),
            allowed_workload_classes=frozenset(
                allowed_workload_classes
                or ["coding_implementation", "repo_audit", "private_automation"]
            ),
            blocked_workload_classes=frozenset(blocked_workload_classes or []),
            unmet_prerequisite_ids=unmet_prerequisite_ids,
            broad_autonomy_enabled=broad_autonomy_enabled,
            runtime_mutations_approval_gated=runtime_mutations_approval_gated,
        )

    async def test_scheduler_source_runs_once_phase_is_enabled(self) -> None:
        governor = Governor()
        policy = self._policy(broad_autonomy_enabled=True)

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.72)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "at_desk"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="coding_implementation",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="coding-agent",
                prompt="Implement the next repo contract fix.",
                source="scheduler",
            )

        self.assertTrue(decision.allowed)
        self.assertEqual("pending", decision.status_override)
        self.assertEqual("A", decision.autonomy_level)
        self.assertIn("coding_implementation", decision.reason)
        record_decision.assert_awaited_once()

    async def test_scheduler_source_respects_software_core_phase_allowlist(self) -> None:
        governor = Governor()
        policy = self._policy(
            is_active=False,
            activation_state="ready_for_operator_enable",
            phase_status="ready",
        )

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.72)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "at_desk"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="coding_implementation",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="coding-agent",
                prompt="Implement the next repo contract fix.",
                source="scheduler",
            )

        self.assertFalse(decision.allowed)
        self.assertEqual("pending_approval", decision.status_override)
        self.assertEqual("D", decision.autonomy_level)
        self.assertIn("software_core_phase_1", decision.reason)
        self.assertIn("not enabled", decision.reason)
        record_decision.assert_awaited_once()

    async def test_pipeline_source_holds_out_of_phase_agent_for_approval(self) -> None:
        governor = Governor()
        policy = self._policy(broad_autonomy_enabled=True)

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.51)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "away"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="private_automation",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="media-agent",
                prompt="Run the next media cycle.",
                source="pipeline",
            )

        self.assertFalse(decision.allowed)
        self.assertEqual("pending_approval", decision.status_override)
        self.assertEqual("D", decision.autonomy_level)
        self.assertIn("outside autonomy phase", decision.reason)
        record_decision.assert_awaited_once()

    async def test_work_planner_autonomy_managed_submission_holds_out_of_phase_agent(self) -> None:
        governor = Governor()
        policy = self._policy(broad_autonomy_enabled=True)

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.61)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "away"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="refusal_sensitive_creative",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="creative-agent",
                prompt="Generate the next queen portrait.",
                source="work_planner",
                metadata={"_autonomy_managed": True, "source": "work_planner"},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual("pending_approval", decision.status_override)
        self.assertEqual("D", decision.autonomy_level)
        self.assertIn("outside autonomy phase", decision.reason)
        record_decision.assert_awaited_once()

    async def test_scheduler_source_holds_blocked_workload_for_approval(self) -> None:
        governor = Governor()
        policy = self._policy(
            broad_autonomy_enabled=True,
            blocked_workload_classes=["background_transform"],
        )

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.81)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "at_desk"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="background_transform",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="coding-agent",
                prompt="Run the background transform cycle.",
                source="scheduler",
                metadata={"source": "dpo_training"},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual("pending_approval", decision.status_override)
        self.assertEqual("D", decision.autonomy_level)
        self.assertIn("background_transform", decision.reason)
        record_decision.assert_awaited_once()

    async def test_scheduler_source_holds_runtime_mutation_even_when_phase_is_active(self) -> None:
        governor = Governor()
        policy = self._policy(
            broad_autonomy_enabled=True,
            runtime_mutations_approval_gated=True,
        )

        with (
            patch.object(governor, "_get_state", AsyncMock(return_value={"global_mode": "active"})),
            patch.object(governor, "_get_paused_lanes", AsyncMock(return_value=set())),
            patch.object(governor, "_get_agent_trust", AsyncMock(return_value=0.81)),
            patch.object(governor, "get_effective_presence", AsyncMock(return_value={"state": "at_desk"})),
            patch.object(governor, "_record_decision", AsyncMock()) as record_decision,
            patch(
                "athanor_agents.governor_runtime._load_autonomy_policy",
                return_value=policy,
            ),
            patch(
                "athanor_agents.governor_runtime._autonomy_workload_class",
                return_value="coding_implementation",
            ),
        ):
            decision = await governor.gate_task_submission(
                agent="coding-agent",
                prompt="Restart the runtime service after updating the model lane.",
                source="scheduler",
                metadata={"requires_runtime_mutation": True},
            )

        self.assertFalse(decision.allowed)
        self.assertEqual("pending_approval", decision.status_override)
        self.assertEqual("D", decision.autonomy_level)
        self.assertIn("approval-gated", decision.reason)
        record_decision.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
