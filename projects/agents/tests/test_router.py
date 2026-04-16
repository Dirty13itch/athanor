"""Tests for Quality Cascade routing.

Covers:
- Task classification (SIMPLE/CODE/REASONING/CREATIVE/HOME/MEDIA)
- Model tier routing (FAST/REASONING/WORKER)
- Queue depth fallback logic
- Prefer quality flag
- Cost tracker
"""

import importlib.util
import os

_ROUTE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "routing.py"
)
spec = importlib.util.spec_from_file_location("routing", _ROUTE_PATH)
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


class TestTaskClassification:
    """classify_task maps prompts to TaskType."""

    def test_simple_greeting(self):
        assert routing.classify_task("Hello, how are you?") == routing.TaskType.SIMPLE

    def test_simple_definition(self):
        assert routing.classify_task("What is Python?") == routing.TaskType.SIMPLE

    def test_code_from_keywords(self):
        assert routing.classify_task(
            "Write a Python function to sort a list"
        ) == routing.TaskType.CODE

    def test_code_from_code_block(self):
        assert routing.classify_task(
            "Fix this code:\n```python\ndef broken():\n```"
        ) == routing.TaskType.CODE

    def test_code_debug(self):
        assert routing.classify_task(
            "Debug this function that throws an error"
        ) == routing.TaskType.CODE

    def test_home_automation(self):
        assert routing.classify_task(
            "Turn off the living room lights"
        ) == routing.TaskType.HOME

    def test_media_request(self):
        assert routing.classify_task(
            "What movies should I watch tonight?"
        ) == routing.TaskType.MEDIA

    def test_creative_writing(self):
        assert routing.classify_task(
            "Write a poem about autumn"
        ) == routing.TaskType.CREATIVE

    def test_research_task(self):
        assert routing.classify_task(
            "Research the latest developments in quantum computing"
        ) == routing.TaskType.RESEARCH

    def test_reasoning_from_complexity(self):
        assert routing.classify_task(
            "Analyze the tradeoffs between vLLM and SGLang for production inference"
        ) == routing.TaskType.REASONING

    def test_empty_prompt_is_chat(self):
        assert routing.classify_task("") == routing.TaskType.CHAT

    def test_ambiguous_is_chat(self):
        assert routing.classify_task("I was thinking about something today") == routing.TaskType.CHAT


class TestModelRouting:
    """route() selects model based on task type."""

    def test_simple_routes_to_fast(self):
        decision = routing.route("Hello there")
        assert decision.tier == routing.ModelTier.FAST
        assert decision.model == "coder"

    def test_code_routes_to_reasoning(self):
        decision = routing.route("Write a Python function to sort a list")
        assert decision.tier == routing.ModelTier.REASONING
        assert decision.model == "reasoning"

    def test_home_routes_to_fast(self):
        decision = routing.route("Turn off the kitchen lights")
        assert decision.tier == routing.ModelTier.FAST

    def test_media_routes_to_fast(self):
        decision = routing.route("Recommend a movie to watch")
        assert decision.tier == routing.ModelTier.FAST

    def test_sovereign_request_ignores_cloud_execution_lease(self):
        decision = routing.route(
            "Draft the next EOQ scene.",
            metadata={
                "policy_class": "sovereign_only",
                "execution_lease": {"provider": "openai_codex"},
            },
        )
        assert decision.model == "reasoning"
        assert decision.tier == routing.ModelTier.REASONING


class TestPreferQuality:
    """prefer_quality flag bumps FAST to REASONING."""

    def test_prefer_quality_upgrades_fast(self):
        decision = routing.route("Hello there", prefer_quality=True)
        assert decision.tier == routing.ModelTier.REASONING

    def test_prefer_quality_doesnt_change_reasoning(self):
        decision = routing.route(
            "Analyze the architecture decision",
            prefer_quality=True,
        )
        assert decision.tier == routing.ModelTier.REASONING


class TestQueueDepthFallback:
    """Fallback when primary model queue is full."""

    def test_fallback_on_high_queue(self):
        decision = routing.route(
            "Hello there",
            queue_depths={"coder": 10, "worker": 2, "reasoning": 3},
        )
        # coder is busy, should fallback
        assert decision.model != "coder"
        assert decision.confidence == 0.7
        assert "busy" in decision.reason

    def test_no_fallback_on_low_queue(self):
        decision = routing.route(
            "Hello there",
            queue_depths={"coder": 2, "worker": 1, "reasoning": 0},
        )
        assert decision.model == "coder"

    def test_custom_threshold(self):
        decision = routing.route(
            "Hello there",
            queue_depths={"fast": 3},
            high_queue_threshold=2,
        )
        # fast queue=3 > threshold=2, should fallback
        assert decision.model != "fast"

    def test_sovereign_queue_fallback_stays_local(self):
        decision = routing.route(
            "Create an explicit scene outline.",
            queue_depths={"reasoning": 10, "fast": 10, "worker": 1, "claude": 0},
            metadata={"policy_class": "sovereign_only"},
        )
        assert decision.model == "worker"


class TestRoutingDecision:
    """RoutingDecision structure."""

    def test_decision_has_required_fields(self):
        decision = routing.route("test prompt")
        assert hasattr(decision, "model")
        assert hasattr(decision, "tier")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reason")
        assert hasattr(decision, "task_type")

    def test_confidence_range(self):
        decision = routing.route("Write a Python class for data processing")
        assert 0.0 <= decision.confidence <= 1.0


class TestCostTracker:
    """Cost tracking for inference."""

    def test_record_and_summary(self):
        tracker = routing.CostTracker()
        tracker.record("fast", 100, 50, 200.0)
        tracker.record("reasoning", 500, 300, 1500.0)

        summary = tracker.summary()
        assert summary["total_requests"] == 2
        assert "fast" in summary["by_model"]
        assert "reasoning" in summary["by_model"]
        assert summary["by_model"]["fast"]["requests"] == 1
        assert summary["by_model"]["reasoning"]["tokens"] == 800

    def test_max_records_capped(self):
        tracker = routing.CostTracker()
        for i in range(6000):
            tracker.record("fast", 10, 10, 50.0)
        assert len(tracker.records) == 5000


class TestFallbackChains:
    """Fallback chain configuration."""

    def test_reasoning_fallback_chain(self):
        assert routing.FALLBACK_CHAINS["reasoning"] == ["fast", "claude", "worker"]

    def test_fast_fallback_chain(self):
        assert routing.FALLBACK_CHAINS["fast"] == ["reasoning", "claude", "worker"]

    def test_all_tiers_have_fallbacks(self):
        for tier_model in routing.TIER_MODELS.values():
            assert tier_model in routing.FALLBACK_CHAINS

    def test_sovereign_fallback_chain_strips_cloud_models(self):
        assert routing._fallback_chain("reasoning", local_only=True) == ["fast", "worker"]


class TestTaskRouting:
    """Task type → model tier mapping."""

    def test_code_uses_reasoning(self):
        assert routing.TASK_ROUTING[routing.TaskType.CODE] == routing.ModelTier.REASONING

    def test_simple_uses_fast(self):
        assert routing.TASK_ROUTING[routing.TaskType.SIMPLE] == routing.ModelTier.FAST

    def test_home_uses_fast(self):
        assert routing.TASK_ROUTING[routing.TaskType.HOME] == routing.ModelTier.FAST

    def test_all_task_types_mapped(self):
        for task_type in routing.TaskType:
            assert task_type in routing.TASK_ROUTING
