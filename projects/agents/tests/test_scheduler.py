import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from athanor_agents.scheduler import get_schedule_control_scope, run_scheduled_job


class FakeImprovementEngine:
    async def load(self) -> None:
        return None

    async def run_benchmark_suite(self) -> dict:
        return {
            "passed": 3,
            "total": 4,
            "pass_rate": 0.75,
        }


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    def test_control_scope_maps_builtin_and_research_jobs(self) -> None:
        self.assertEqual("scheduler", get_schedule_control_scope("daily-digest"))
        self.assertEqual("benchmark_cycle", get_schedule_control_scope("benchmark-cycle"))
        self.assertEqual("research_jobs", get_schedule_control_scope("research:rj-1234"))
        self.assertEqual("scheduler", get_schedule_control_scope("agent-schedule:coding-agent"))

    async def test_run_scheduled_job_uses_agent_schedule_delegate(self) -> None:
        with patch(
            "athanor_agents.scheduler._run_agent_schedule",
            AsyncMock(return_value={"job_id": "agent-schedule:coding-agent", "status": "queued"}),
        ) as delegate, patch(
            "athanor_agents.governor.build_capacity_snapshot",
            AsyncMock(
                return_value={
                    "posture": "healthy",
                    "queue": {"posture": "healthy"},
                    "provider_reserve": {"posture": "healthy"},
                    "active_time_windows": [],
                }
            ),
        ), patch(
            "athanor_agents.governor.evaluate_job_governance",
            AsyncMock(return_value={"allowed": True, "status": "active"}),
        ):
            result = await run_scheduled_job("agent-schedule:coding-agent", actor="dashboard-operator")

        delegate.assert_awaited_once()
        self.assertEqual("queued", result["status"])

    async def test_run_scheduled_job_executes_benchmark_cycle(self) -> None:
        engine = FakeImprovementEngine()
        with (
            patch("athanor_agents.self_improvement.get_improvement_engine", return_value=engine),
            patch("athanor_agents.scheduler._emit_schedule_event", AsyncMock()) as emit_event,
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "posture": "healthy",
                        "queue": {"posture": "healthy"},
                        "provider_reserve": {"posture": "healthy"},
                        "active_time_windows": [],
                    }
                ),
            ),
            patch(
                "athanor_agents.governor.evaluate_job_governance",
                AsyncMock(return_value={"allowed": True, "status": "active"}),
            ),
        ):
            result = await run_scheduled_job("benchmark-cycle", actor="dashboard-operator")

        self.assertEqual("completed", result["status"])
        emit_event.assert_awaited_once()

    async def test_run_scheduled_job_defers_when_governor_blocks_manual_run(self) -> None:
        decision = {
            "allowed": False,
            "status": "deferred",
            "reason": "Deferred while operator is away (quiet hours).",
            "presence_state": "away",
            "release_tier": "production",
        }
        with (
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "posture": "constrained",
                        "queue": {"posture": "constrained"},
                        "provider_reserve": {"posture": "healthy"},
                        "active_time_windows": [],
                    }
                ),
            ),
            patch("athanor_agents.governor.evaluate_job_governance", AsyncMock(return_value=decision)),
            patch("athanor_agents.scheduler._emit_schedule_event", AsyncMock()) as emit_event,
        ):
            result = await run_scheduled_job("benchmark-cycle", actor="dashboard-operator")

        self.assertEqual("deferred", result["status"])
        self.assertEqual(decision, result["governor_decision"])
        emit_event.assert_awaited_once()

    async def test_run_scheduled_job_force_override_executes_blocked_job(self) -> None:
        engine = FakeImprovementEngine()
        decision = {
            "allowed": False,
            "status": "deferred",
            "reason": "Deferred while operator is away (quiet hours).",
            "presence_state": "away",
            "release_tier": "production",
        }
        with (
            patch(
                "athanor_agents.governor.build_capacity_snapshot",
                AsyncMock(
                    return_value={
                        "posture": "constrained",
                        "queue": {"posture": "constrained"},
                        "provider_reserve": {"posture": "healthy"},
                        "active_time_windows": [],
                    }
                ),
            ),
            patch("athanor_agents.governor.evaluate_job_governance", AsyncMock(return_value=decision)),
            patch("athanor_agents.self_improvement.get_improvement_engine", return_value=engine),
            patch("athanor_agents.scheduler._emit_schedule_event", AsyncMock()) as emit_event,
        ):
            result = await run_scheduled_job(
                "benchmark-cycle",
                actor="dashboard-operator",
                force=True,
            )

        self.assertEqual("completed", result["status"])
        emit_event.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
