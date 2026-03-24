"""Tests for preference learning module — data integrity.

Covers task classification, model scoring, feedback recording, and preference persistence.
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


# ---------------------------------------------------------------------------
# Task classification tests
# ---------------------------------------------------------------------------


class TestClassifyTask(unittest.TestCase):
    """Test PreferenceLearner._classify_task() keyword matching."""

    def setUp(self):
        from athanor_agents.preference_learning import PreferenceLearner

        self.learner = PreferenceLearner(user_id="test")

    def test_code_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Write a function to sort items",
            "Debug this code block",
            "Implement the API endpoint",
            "Refactor the class hierarchy",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.CODE, f"Failed for: {prompt}")

    def test_creative_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Write a story about a dragon",
            "Create a creative poem",
            "Write a fiction piece",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.CREATIVE, f"Failed for: {prompt}")

    def test_analysis_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Analyze the performance data",
            "Compare these two approaches",
            "Evaluate the proposal",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.ANALYSIS, f"Failed for: {prompt}")

    def test_research_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Research the latest GPU benchmarks",
            "Investigate the memory leak",
            "Look up the vLLM documentation",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.RESEARCH, f"Failed for: {prompt}")

    def test_home_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Turn on the lights",
            "Set the thermostat to 22",
            "Check home assistant status",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.HOME, f"Failed for: {prompt}")

    def test_media_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Add this movie to my list",
            "Check plex for new content",
            "Search sonarr for the series",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.MEDIA, f"Failed for: {prompt}")

    def test_system_classification(self):
        from athanor_agents.preference_learning import TaskType

        for prompt in [
            "Deploy the new container",
            "Check the ansible playbook",
            "Update the vllm configuration",
        ]:
            result = self.learner._classify_task(prompt)
            self.assertEqual(result, TaskType.SYSTEM, f"Failed for: {prompt}")

    def test_general_fallback(self):
        from athanor_agents.preference_learning import TaskType

        result = self.learner._classify_task("Hello, how are you today?")
        self.assertEqual(result, TaskType.GENERAL)

    def test_translation_classification(self):
        from athanor_agents.preference_learning import TaskType

        result = self.learner._classify_task("Translate this text in spanish please")
        self.assertEqual(result, TaskType.TRANSLATION)

    def test_summarization_classification(self):
        from athanor_agents.preference_learning import TaskType

        result = self.learner._classify_task("Summarize the key points of this doc")
        self.assertEqual(result, TaskType.SUMMARIZATION)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestEnums(unittest.TestCase):
    """Test enum completeness and values."""

    def test_feedback_types(self):
        from athanor_agents.preference_learning import FeedbackType

        values = {f.value for f in FeedbackType}
        self.assertIn("positive", values)
        self.assertIn("negative", values)
        self.assertIn("regenerate", values)
        self.assertIn("edit", values)

    def test_task_types_cover_all_agents(self):
        from athanor_agents.preference_learning import TaskType

        values = {t.value for t in TaskType}
        self.assertIn("home", values)
        self.assertIn("media", values)
        self.assertIn("system", values)
        self.assertIn("research", values)
        self.assertIn("creative", values)

    def test_default_models_cover_all_task_types(self):
        from athanor_agents.preference_learning import DEFAULT_MODELS, TaskType

        for task_type in TaskType:
            self.assertIn(task_type, DEFAULT_MODELS, f"Missing default model for {task_type}")


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestModelStats(unittest.TestCase):
    """Test ModelStats dataclass."""

    def test_default_values(self):
        from athanor_agents.preference_learning import ModelStats

        stats = ModelStats(model="test-model")
        self.assertEqual(stats.total_uses, 0)
        self.assertEqual(stats.positive_feedback, 0)
        self.assertEqual(stats.negative_feedback, 0)
        self.assertEqual(stats.success_rate, 1.0)

    def test_success_rate_calculation(self):
        from athanor_agents.preference_learning import ModelStats

        stats = ModelStats(
            model="test",
            positive_feedback=7,
            negative_feedback=3,
        )
        total = stats.positive_feedback + stats.negative_feedback
        rate = stats.positive_feedback / total
        self.assertAlmostEqual(rate, 0.7)


class TestUserPreferences(unittest.TestCase):
    """Test UserPreferences dataclass."""

    def test_default_empty(self):
        from athanor_agents.preference_learning import UserPreferences

        prefs = UserPreferences()
        self.assertEqual(prefs.preferred_models, {})
        self.assertEqual(prefs.model_stats, {})

    def test_creative_style_defaults(self):
        from athanor_agents.preference_learning import CreativeStylePreferences

        style = CreativeStylePreferences()
        self.assertEqual(style.tone, "balanced")
        self.assertEqual(style.verbosity, "balanced")
        self.assertTrue(style.nsfw_enabled)


# ---------------------------------------------------------------------------
# PreferenceLearner core methods
# ---------------------------------------------------------------------------


class TestPreferenceLearnerInit(unittest.TestCase):
    """Test PreferenceLearner initialization."""

    def test_default_user_id(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        self.assertEqual(learner.user_id, "default")

    def test_custom_user_id(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="shaun")
        self.assertEqual(learner.user_id, "shaun")

    def test_redis_key_generation(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        key = learner._redis_key("preferences")
        self.assertEqual(key, "athanor:prefs:test:preferences")

    def test_prompt_hash_deterministic(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        h1 = learner._hash_prompt("test prompt")
        h2 = learner._hash_prompt("test prompt")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)

    def test_prompt_hash_different_for_different_inputs(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        h1 = learner._hash_prompt("prompt A")
        h2 = learner._hash_prompt("prompt B")
        self.assertNotEqual(h1, h2)


# ---------------------------------------------------------------------------
# Export/import tests
# ---------------------------------------------------------------------------


class TestExportImport(unittest.TestCase):
    """Test preference serialization round-trip."""

    def test_export_empty(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        result = learner.export_preferences()
        self.assertEqual(result, {})

    def test_export_with_data(self):
        from athanor_agents.preference_learning import (
            PreferenceLearner, UserPreferences, ModelStats,
        )

        learner = PreferenceLearner(user_id="test")
        learner._preferences_cache = UserPreferences(
            preferred_models={"code": "reasoning"},
            model_stats={"reasoning": ModelStats(model="reasoning", total_uses=10)},
        )
        exported = learner.export_preferences()

        self.assertEqual(exported["user_id"], "test")
        self.assertIn("code", exported["preferred_models"])
        self.assertIn("reasoning", exported["model_stats"])

    def test_import_round_trip(self):
        from athanor_agents.preference_learning import (
            PreferenceLearner, UserPreferences, ModelStats,
        )

        learner = PreferenceLearner(user_id="test")
        learner._preferences_cache = UserPreferences(
            preferred_models={"code": "reasoning", "creative": "fast"},
            model_stats={
                "reasoning": ModelStats(model="reasoning", total_uses=10, positive_feedback=8),
            },
            style_preferences={"verbosity": "terse"},
        )
        exported = learner.export_preferences()

        new_learner = PreferenceLearner(user_id="test2")
        success = new_learner.import_preferences(exported)

        self.assertTrue(success)
        self.assertEqual(new_learner._preferences_cache.preferred_models["code"], "reasoning")
        self.assertEqual(new_learner._preferences_cache.model_stats["reasoning"].total_uses, 10)
        self.assertEqual(new_learner._preferences_cache.style_preferences["verbosity"], "terse")

    def test_import_handles_missing_fields(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        success = learner.import_preferences({})
        self.assertTrue(success)
        self.assertEqual(learner._preferences_cache.preferred_models, {})

    def test_import_handles_corrupt_data(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner()
        # model_stats expects ModelStats-compatible dicts
        success = learner.import_preferences({
            "model_stats": {"bad": "not a dict with model field"},
        })
        self.assertFalse(success)


# ---------------------------------------------------------------------------
# Async Redis-backed tests
# ---------------------------------------------------------------------------


def _mock_redis():
    """Create a mock Redis instance."""
    mock = AsyncMock()
    mock.set = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.lpush = AsyncMock()
    mock.ltrim = AsyncMock()
    return mock


class TestRecordInteraction(unittest.IsolatedAsyncioTestCase):
    """Test record_interaction() persistence."""

    async def test_records_and_returns_interaction(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            interaction = await learner.record_interaction(
                prompt="Write a function",
                model="reasoning",
                response="Here is the function...",
                latency_ms=500,
                feedback="positive",
                agent="coding-agent",
            )

        self.assertIsNotNone(interaction.id)
        self.assertEqual(interaction.model, "reasoning")
        self.assertEqual(interaction.task_type, "code")
        self.assertEqual(interaction.feedback, "positive")
        # Should have called set (for interaction) + set (for preferences persist)
        self.assertGreater(mock_r.set.call_count, 0)

    async def test_classifies_task_type_automatically(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            interaction = await learner.record_interaction(
                prompt="Research the latest GPU benchmarks",
                model="reasoning",
                response="Here are the benchmarks...",
            )

        self.assertEqual(interaction.task_type, "research")


class TestUpdateModelStats(unittest.IsolatedAsyncioTestCase):
    """Test _update_model_stats() rolling statistics."""

    async def test_first_use_sets_latency(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            await learner._update_model_stats("fast", TaskType.GENERAL, 200, None)

        stats = learner._preferences_cache.model_stats["fast"]
        self.assertEqual(stats.total_uses, 1)
        self.assertAlmostEqual(stats.avg_latency_ms, 200)

    async def test_rolling_average_latency(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            await learner._update_model_stats("fast", TaskType.GENERAL, 100, None)
            await learner._update_model_stats("fast", TaskType.GENERAL, 200, None)

        stats = learner._preferences_cache.model_stats["fast"]
        # EMA: first=100, second = 100*0.9 + 200*0.1 = 110
        self.assertAlmostEqual(stats.avg_latency_ms, 110)

    async def test_positive_feedback_increments(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            await learner._update_model_stats("fast", TaskType.GENERAL, 100, "positive")

        stats = learner._preferences_cache.model_stats["fast"]
        self.assertEqual(stats.positive_feedback, 1)
        self.assertEqual(stats.success_rate, 1.0)

    async def test_negative_feedback_lowers_rate(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            await learner._update_model_stats("fast", TaskType.GENERAL, 100, "positive")
            await learner._update_model_stats("fast", TaskType.GENERAL, 100, "negative")

        stats = learner._preferences_cache.model_stats["fast"]
        self.assertAlmostEqual(stats.success_rate, 0.5)

    async def test_regeneration_tracked(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        with patch.object(learner, "_get_redis", return_value=mock_r):
            await learner._update_model_stats("fast", TaskType.GENERAL, 100, "regenerate")

        stats = learner._preferences_cache.model_stats["fast"]
        self.assertEqual(stats.regenerations, 1)


class TestRecordFeedback(unittest.IsolatedAsyncioTestCase):
    """Test record_feedback() for retroactive feedback."""

    async def test_updates_existing_interaction(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()

        existing_interaction = {
            "id": "123-abc",
            "model": "reasoning",
            "task_type": "code",
            "feedback": None,
        }
        mock_r.get = AsyncMock(return_value=json.dumps(existing_interaction))

        with patch.object(learner, "_get_redis", return_value=mock_r):
            result = await learner.record_feedback("123-abc", "positive")

        self.assertTrue(result)

    async def test_returns_false_for_missing_interaction(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()
        mock_r.get = AsyncMock(return_value=None)

        with patch.object(learner, "_get_redis", return_value=mock_r):
            result = await learner.record_feedback("nonexistent", "positive")

        self.assertFalse(result)


class TestGetPreferredModel(unittest.IsolatedAsyncioTestCase):
    """Test get_preferred_model() recommendation logic."""

    async def test_returns_default_for_task_type(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()
        mock_r.get = AsyncMock(return_value=None)

        with patch.object(learner, "_get_redis", return_value=mock_r):
            model = await learner.get_preferred_model(task_type=TaskType.CODE)

        self.assertEqual(model, "coding")

    async def test_returns_explicit_preference(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType, UserPreferences

        learner = PreferenceLearner(user_id="test")
        learner._preferences_cache = UserPreferences(
            preferred_models={"code": "my-custom-model"},
        )
        learner._cache_timestamp = time.time()

        mock_r = _mock_redis()
        with patch.object(learner, "_get_redis", return_value=mock_r):
            model = await learner.get_preferred_model(task_type=TaskType.CODE)

        self.assertEqual(model, "my-custom-model")

    async def test_classifies_from_prompt_when_no_task_type(self):
        from athanor_agents.preference_learning import PreferenceLearner

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()
        mock_r.get = AsyncMock(return_value=None)

        with patch.object(learner, "_get_redis", return_value=mock_r):
            model = await learner.get_preferred_model(prompt="Write a function to sort")

        self.assertEqual(model, "coding")

    async def test_respects_available_models(self):
        from athanor_agents.preference_learning import PreferenceLearner, TaskType

        learner = PreferenceLearner(user_id="test")
        mock_r = _mock_redis()
        mock_r.get = AsyncMock(return_value=None)

        with patch.object(learner, "_get_redis", return_value=mock_r):
            model = await learner.get_preferred_model(
                task_type=TaskType.CODE,
                available_models=["fast", "worker"],
            )

        # "coding" not in available, should fall back
        self.assertIn(model, ["fast", "worker"])


class TestSingleton(unittest.TestCase):
    """Test get_preference_learner() singleton pattern."""

    def test_returns_same_instance(self):
        from athanor_agents.preference_learning import get_preference_learner, _instance

        # Reset singleton
        import athanor_agents.preference_learning as pl
        pl._instance = None

        learner1 = get_preference_learner("test")
        learner2 = get_preference_learner("test")
        self.assertIs(learner1, learner2)

        # Cleanup
        pl._instance = None


if __name__ == "__main__":
    unittest.main()
