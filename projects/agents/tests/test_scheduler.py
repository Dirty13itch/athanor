"""Tests for proactive agent scheduler.

Covers:
- Schedule definitions (agents, intervals, enabled flags)
- INFRA-003: Peak hours check in scheduler loop
- _humanize_interval formatting
- Schedule constants
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock

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


class TestSchedulerPriorities:
    """Schedule priority assignments."""

    def test_valid_priorities(self):
        valid = {"critical", "high", "normal", "low"}
        for agent, config in scheduler.AGENT_SCHEDULES.items():
            assert config["priority"] in valid, (
                f"{agent} has invalid priority: {config['priority']}"
            )
