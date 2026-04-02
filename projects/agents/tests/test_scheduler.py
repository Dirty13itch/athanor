"""Tests for proactive agent scheduler.

Covers:
- Schedule definitions (agents, intervals, enabled flags)
- INFRA-003: Peak hours check in scheduler loop
- _humanize_interval formatting
- Schedule constants
"""

import asyncio
import importlib.util
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Mock dependencies
_mock_config = MagicMock()
_mock_config.settings.redis_url = "redis://localhost:6379"
_mock_config.settings.redis_password = None

# Load constitution for is_peak_hours
_CONST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "constitution.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.constitution", _CONST_PATH,
    submodule_search_locations=[],
)
constitution = importlib.util.module_from_spec(spec)
constitution.__package__ = "athanor_agents"

sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = _mock_config
sys.modules["athanor_agents.workspace"] = MagicMock()

spec.loader.exec_module(constitution)
sys.modules["athanor_agents.constitution"] = constitution

# Load scheduler
_SCHED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "scheduler.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.scheduler", _SCHED_PATH,
    submodule_search_locations=[],
)
scheduler = importlib.util.module_from_spec(spec)
scheduler.__package__ = "athanor_agents"
spec.loader.exec_module(scheduler)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]


class TestScheduleDefinitions:
    """Agent schedule configuration."""

    def test_general_assistant_schedule(self):
        config = scheduler.AGENT_SCHEDULES["general-assistant"]
        assert config["interval"] == 1800  # 30 min
        assert config["enabled"] is True

    def test_media_agent_schedule(self):
        config = scheduler.AGENT_SCHEDULES["media-agent"]
        assert config["interval"] == 900  # 15 min

    def test_all_schedules_have_required_keys(self):
        for agent, config in scheduler.AGENT_SCHEDULES.items():
            assert "interval" in config, f"{agent} missing interval"
            assert "prompt" in config, f"{agent} missing prompt"
            assert "priority" in config, f"{agent} missing priority"

    def test_all_schedules_have_prompts(self):
        for agent, config in scheduler.AGENT_SCHEDULES.items():
            assert len(config["prompt"]) > 10, f"{agent} prompt too short"


class TestScheduleConstants:
    """Schedule timing constants."""

    def test_scheduler_interval(self):
        assert scheduler.SCHEDULER_INTERVAL == 30.0

    def test_consolidation_time(self):
        assert scheduler.CONSOLIDATION_HOUR == 3
        assert scheduler.CONSOLIDATION_MINUTE == 0

    def test_digest_time(self):
        assert scheduler.DIGEST_HOUR == 6
        assert scheduler.DIGEST_MINUTE == 55

    def test_pattern_detection_time(self):
        assert scheduler.PATTERN_HOUR == 5

    def test_alert_check_interval(self):
        assert scheduler.ALERT_CHECK_INTERVAL == 300  # 5 min

    def test_benchmark_interval(self):
        assert scheduler.BENCHMARK_INTERVAL == 21600  # 6 hours

    def test_cache_cleanup_interval(self):
        assert scheduler.CACHE_CLEANUP_INTERVAL == 3600  # 1 hour

    def test_workplan_refill_interval(self):
        assert scheduler.WORKPLAN_REFILL_INTERVAL == 7200  # 2 hours


class TestHumanizeInterval:
    """_humanize_interval formatting."""

    def test_seconds(self):
        assert scheduler._humanize_interval(30) == "30s"

    def test_minutes(self):
        assert scheduler._humanize_interval(300) == "5min"

    def test_hours(self):
        assert scheduler._humanize_interval(3600) == "1h"
        assert scheduler._humanize_interval(7200) == "2h"

    def test_days(self):
        assert scheduler._humanize_interval(86400) == "1d"
        assert scheduler._humanize_interval(172800) == "2d"


class TestPeakHoursIntegration:
    """INFRA-003: Scheduler imports and uses is_peak_hours."""

    def test_is_peak_hours_imported(self):
        assert hasattr(scheduler, "is_peak_hours")
        assert callable(scheduler.is_peak_hours)

    def test_peak_hours_function_works(self):
        # Just verify it doesn't crash — actual time-dependent behavior
        # tested in test_constitution.py
        result = scheduler.is_peak_hours()
        assert isinstance(result, bool)


class TestAutonomyPolicyIntegration:
    """Shared autonomy-policy seam."""

    def test_autonomy_allows_workload_uses_shared_policy(self):
        original = scheduler._load_autonomy_policy
        scheduler._load_autonomy_policy = lambda: SimpleNamespace(
            phase_id="software_core_phase_1",
            is_active=True,
            activation_state="software_core_active",
            phase_status="active",
            enabled_agents=frozenset({"coding-agent"}),
            allowed_workload_classes=frozenset({"coding_implementation"}),
            blocked_workload_classes=frozenset({"background_transform"}),
            unmet_prerequisite_ids=(),
            broad_autonomy_enabled=False,
            runtime_mutations_approval_gated=True,
        )
        try:
            assert scheduler._autonomy_allows_workload(
                "coding_implementation",
                agent="coding-agent",
                loop_id="scheduler-test",
            )
            assert not scheduler._autonomy_allows_workload(
                "background_transform",
                agent="coding-agent",
                loop_id="scheduler-test",
            )
        finally:
            scheduler._load_autonomy_policy = original


class TestSchedulerPriorities:
    """Schedule priority assignments."""

    def test_valid_priorities(self):
        valid = {"critical", "high", "normal", "low"}
        for agent, config in scheduler.AGENT_SCHEDULES.items():
            assert config["priority"] in valid, (
                f"{agent} has invalid priority: {config['priority']}"
            )


class TestSchedulerControlScopes:
    def test_builtin_scope_mappings_cover_native_loop_jobs(self):
        assert scheduler.get_schedule_control_scope("pipeline-cycle") == "scheduler"
        assert scheduler.get_schedule_control_scope("owner-model") == "scheduler"
        assert scheduler.get_schedule_control_scope("nightly-optimization") == "scheduler"
        assert scheduler.get_schedule_control_scope("creative-cascade") == "scheduler"
        assert scheduler.get_schedule_control_scope("code-cascade") == "scheduler"
        assert scheduler.get_schedule_control_scope("weekly-dpo-training") == "benchmark_cycle"
        assert scheduler.get_schedule_control_scope("knowledge-refresh") == "maintenance"
        assert scheduler.get_schedule_control_scope("research:scheduler") == "research_jobs"


class TestManualJobGovernanceContext:
    def test_manual_governance_context_covers_native_loop_jobs(self):
        assert scheduler._manual_job_governance_context("pipeline-cycle") == ("pipeline", "system")
        assert scheduler._manual_job_governance_context("owner-model") == ("owner_model", "system")
        assert scheduler._manual_job_governance_context("nightly-optimization") == (
            "nightly_optimization",
            "system",
        )
        assert scheduler._manual_job_governance_context("knowledge-refresh") == (
            "knowledge_refresh",
            "system",
        )
        assert scheduler._manual_job_governance_context("weekly-dpo-training") == (
            "weekly_dpo_training",
            "system",
        )
        assert scheduler._manual_job_governance_context("creative-cascade") == (
            "creative_cascade",
            "creative-agent",
        )
        assert scheduler._manual_job_governance_context("code-cascade") == (
            "code_cascade",
            "coding-agent",
        )


class TestManualRunnerHelpers:
    def test_manual_runner_helpers_exist_for_scheduler_routes(self):
        assert hasattr(scheduler, "_run_agent_schedule")
        assert hasattr(scheduler, "_run_daily_digest")
        assert hasattr(scheduler, "_run_consolidation_job")
        assert hasattr(scheduler, "_run_pattern_detection_job")


class _FakeRedis:
    def __init__(self, last_run=None):
        self.last_run = last_run
        self.set_calls = []

    async def get(self, key):
        if key == scheduler.PIPELINE_KEY:
            return self.last_run
        return None

    async def set(self, key, value):
        self.set_calls.append((key, value))


class TestBackgroundPipelineTimeouts:
    def test_background_pipeline_uses_shared_timeout_budget(self):
        fake_redis = _FakeRedis()
        policy = SimpleNamespace(
            phase_id="full_system_phase_3",
            is_active=True,
            activation_state="full_system_active",
            phase_status="active",
            enabled_agents=frozenset({"general-assistant", "coding-agent"}),
            allowed_workload_classes=frozenset({"workplan_generation"}),
            blocked_workload_classes=frozenset(),
            unmet_prerequisite_ids=(),
            broad_autonomy_enabled=True,
            runtime_mutations_approval_gated=True,
        )
        pipeline_module = types.ModuleType("athanor_agents.work_pipeline")
        pipeline_module.PIPELINE_CYCLE_TIMEOUT_SECONDS = 900

        async def _run_pipeline_cycle():
            return SimpleNamespace(
                intents_mined=1,
                intents_new=1,
                plans_created=1,
                tasks_submitted=1,
                tasks_held=0,
            )

        async def _wait_for(coro, timeout):
            assert timeout == 900
            return await coro

        pipeline_module.run_pipeline_cycle = _run_pipeline_cycle

        with (
            patch.object(scheduler, "_get_redis", AsyncMock(return_value=fake_redis)),
            patch.object(scheduler, "_load_autonomy_policy", return_value=policy),
            patch.object(scheduler.asyncio, "wait_for", _wait_for),
            patch.object(scheduler, "logger") as logger,
            patch.dict(sys.modules, {"athanor_agents.work_pipeline": pipeline_module}),
        ):
            asyncio.run(scheduler._check_work_pipeline())

        assert fake_redis.set_calls
        logger.warning.assert_not_called()

    def test_background_pipeline_logs_timeout_without_blank_error(self):
        fake_redis = _FakeRedis()
        policy = SimpleNamespace(
            phase_id="full_system_phase_3",
            is_active=True,
            activation_state="full_system_active",
            phase_status="active",
            enabled_agents=frozenset({"general-assistant", "coding-agent"}),
            allowed_workload_classes=frozenset({"workplan_generation"}),
            blocked_workload_classes=frozenset(),
            unmet_prerequisite_ids=(),
            broad_autonomy_enabled=True,
            runtime_mutations_approval_gated=True,
        )
        pipeline_module = types.ModuleType("athanor_agents.work_pipeline")
        pipeline_module.PIPELINE_CYCLE_TIMEOUT_SECONDS = 900

        async def _run_pipeline_cycle():
            await asyncio.sleep(0)
            return None

        async def _wait_for(coro, timeout):
            assert timeout == 900
            coro.close()
            raise asyncio.TimeoutError()

        pipeline_module.run_pipeline_cycle = _run_pipeline_cycle

        with (
            patch.object(scheduler, "_get_redis", AsyncMock(return_value=fake_redis)),
            patch.object(scheduler, "_load_autonomy_policy", return_value=policy),
            patch.object(scheduler.asyncio, "wait_for", _wait_for),
            patch.object(scheduler, "logger") as logger,
            patch.dict(sys.modules, {"athanor_agents.work_pipeline": pipeline_module}),
        ):
            asyncio.run(scheduler._check_work_pipeline())

        logger.warning.assert_called_once_with(
            "Scheduler: work pipeline cycle timed out after %ds",
            900,
        )
