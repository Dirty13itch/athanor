"""Tests for skill learning module — data integrity.

Covers Skill dataclass, relevance scoring, and Redis-backed CRUD.
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
# Dataclass tests
# ---------------------------------------------------------------------------


class TestSkillDataclass(unittest.TestCase):
    """Test Skill data model."""

    def test_default_values(self):
        from athanor_agents.skill_learning import Skill

        s = Skill()
        self.assertEqual(s.name, "")
        self.assertEqual(s.category, "general")
        self.assertEqual(s.execution_count, 0)
        self.assertEqual(s.success_rate, 0.0)
        self.assertIsInstance(s.skill_id, str)
        self.assertEqual(len(s.skill_id), 8)

    def test_round_trip_serialization(self):
        from athanor_agents.skill_learning import Skill

        original = Skill(
            name="Test Skill",
            description="A test",
            category="testing",
            trigger_conditions=["test", "check"],
            steps=["step 1", "step 2"],
            tags=["test"],
            created_by="unit-test",
            execution_count=5,
            success_count=4,
            success_rate=0.8,
        )
        data = original.to_dict()
        restored = Skill.from_dict(data)

        self.assertEqual(restored.name, "Test Skill")
        self.assertEqual(restored.category, "testing")
        self.assertEqual(restored.execution_count, 5)
        self.assertEqual(restored.success_rate, 0.8)
        self.assertEqual(restored.trigger_conditions, ["test", "check"])
        self.assertEqual(restored.steps, ["step 1", "step 2"])

    def test_from_dict_ignores_extra_keys(self):
        from athanor_agents.skill_learning import Skill

        data = {"name": "Test", "nonexistent_field": "value"}
        s = Skill.from_dict(data)
        self.assertEqual(s.name, "Test")

    def test_json_round_trip(self):
        from athanor_agents.skill_learning import Skill

        original = Skill(name="JSON Test", tags=["a", "b"])
        json_str = json.dumps(original.to_dict())
        restored = Skill.from_dict(json.loads(json_str))
        self.assertEqual(restored.name, "JSON Test")
        self.assertEqual(restored.tags, ["a", "b"])


# ---------------------------------------------------------------------------
# Relevance scoring tests
# ---------------------------------------------------------------------------


class TestComputeRelevance(unittest.TestCase):
    """Test _compute_relevance() keyword matching logic."""

    def _make_skill(self, **kwargs):
        from athanor_agents.skill_learning import Skill

        defaults = {
            "name": "Test Skill",
            "description": "A skill for testing",
            "trigger_conditions": ["run tests", "check code"],
            "tags": ["testing"],
        }
        defaults.update(kwargs)
        return Skill(**defaults)

    def _score(self, skill, query: str) -> float:
        from athanor_agents.skill_learning import _compute_relevance

        return _compute_relevance(skill, query)

    def test_exact_trigger_match_high_score(self):
        skill = self._make_skill(trigger_conditions=["research"])
        score = self._score(skill, "I want to research AI models")
        self.assertGreaterEqual(score, 0.6)

    def test_partial_word_trigger_match(self):
        skill = self._make_skill(trigger_conditions=["deploy containers"])
        score = self._score(skill, "I need to deploy my new service")
        # "deploy" (>3 chars) matches in trigger condition
        self.assertGreaterEqual(score, 0.3)

    def test_name_description_match(self):
        skill = self._make_skill(
            name="Infrastructure Diagnosis",
            description="Diagnose service health issues",
            trigger_conditions=[],
        )
        score = self._score(skill, "diagnose the failing container")
        self.assertGreater(score, 0.0)

    def test_tag_match(self):
        skill = self._make_skill(
            trigger_conditions=[],
            tags=["infrastructure"],
        )
        score = self._score(skill, "check infrastructure status")
        self.assertGreaterEqual(score, 0.2)

    def test_no_match_returns_zero(self):
        skill = self._make_skill(
            name="Media Workflow",
            description="Handle media requests",
            trigger_conditions=["add movie"],
            tags=["media"],
        )
        score = self._score(skill, "compile the C++ program")
        self.assertEqual(score, 0.0)

    def test_combined_signals_add_up(self):
        skill = self._make_skill(
            name="Search then Synthesize",
            description="Web search followed by synthesis",
            trigger_conditions=["research", "find information"],
            tags=["research", "web"],
        )
        score = self._score(skill, "research the latest vLLM benchmarks")
        # trigger match (0.6) + possibly tag match (0.2) = capped at 1.0
        self.assertGreaterEqual(score, 0.6)

    def test_short_words_ignored(self):
        # Words <= 3 chars are skipped in word matching
        skill = self._make_skill(
            trigger_conditions=["run the app"],
            tags=[],
        )
        score = self._score(skill, "do it now for me")
        # All query words are <= 3 chars, no trigger substring match
        self.assertEqual(score, 0.0)

    def test_score_capped_at_one(self):
        skill = self._make_skill(
            name="research synthesis analysis",
            description="comprehensive research and analysis tool",
            trigger_conditions=["research", "analyze", "investigate"],
            tags=["research", "analysis"],
        )
        score = self._score(skill, "research and analyze the investigation results")
        self.assertLessEqual(score, 1.0)


# ---------------------------------------------------------------------------
# Redis-backed async tests
# ---------------------------------------------------------------------------


def _mock_redis():
    """Create a mock Redis instance with async methods."""
    mock = AsyncMock()
    mock.hset = AsyncMock()
    mock.hget = AsyncMock(return_value=None)
    mock.hgetall = AsyncMock(return_value={})
    mock.hdel = AsyncMock(return_value=1)
    mock.hlen = AsyncMock(return_value=0)
    return mock


class TestAddSkill(unittest.IsolatedAsyncioTestCase):
    """Test add_skill() Redis storage."""

    async def test_stores_skill_in_redis(self):
        from athanor_agents.skill_learning import add_skill, SKILLS_KEY

        mock_r = _mock_redis()
        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            skill_id = await add_skill(
                name="Test Skill",
                description="A test skill",
                trigger_conditions=["test"],
                steps=["step 1"],
                category="testing",
            )

        self.assertIsInstance(skill_id, str)
        mock_r.hset.assert_called_once()
        call_args = mock_r.hset.call_args
        self.assertEqual(call_args[0][0], SKILLS_KEY)
        # Verify stored JSON is valid
        stored_json = call_args[0][2]
        stored = json.loads(stored_json)
        self.assertEqual(stored["name"], "Test Skill")
        self.assertEqual(stored["category"], "testing")


class TestGetSkill(unittest.IsolatedAsyncioTestCase):
    """Test get_skill() Redis retrieval."""

    async def test_returns_skill_when_found(self):
        from athanor_agents.skill_learning import get_skill, Skill

        skill_data = Skill(skill_id="abc123", name="Found Skill").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(skill_data))

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await get_skill("abc123")

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Found Skill")

    async def test_returns_none_when_not_found(self):
        from athanor_agents.skill_learning import get_skill

        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=None)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await get_skill("nonexistent")

        self.assertIsNone(result)


class TestGetAllSkills(unittest.IsolatedAsyncioTestCase):
    """Test get_all_skills() bulk retrieval."""

    async def test_returns_all_skills(self):
        from athanor_agents.skill_learning import get_all_skills, Skill

        skills = {
            "s1": json.dumps(Skill(skill_id="s1", name="Skill 1").to_dict()),
            "s2": json.dumps(Skill(skill_id="s2", name="Skill 2").to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=skills)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await get_all_skills()

        self.assertEqual(len(result), 2)
        names = {s.name for s in result}
        self.assertEqual(names, {"Skill 1", "Skill 2"})

    async def test_empty_library(self):
        from athanor_agents.skill_learning import get_all_skills

        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value={})

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await get_all_skills()

        self.assertEqual(result, [])


class TestRecordExecution(unittest.IsolatedAsyncioTestCase):
    """Test record_execution() learning feedback loop."""

    async def test_increments_count_and_updates_rate(self):
        from athanor_agents.skill_learning import Skill

        skill_data = Skill(
            skill_id="exec1",
            name="Test",
            execution_count=4,
            success_count=3,
            success_rate=0.75,
            avg_duration_ms=100.0,
        )
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(skill_data.to_dict()))

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import record_execution

            result = await record_execution("exec1", success=True, duration_ms=200.0)

        self.assertTrue(result)
        # Verify the updated skill was stored
        stored_json = mock_r.hset.call_args[0][2]
        stored = json.loads(stored_json)
        self.assertEqual(stored["execution_count"], 5)
        self.assertEqual(stored["success_count"], 4)
        self.assertAlmostEqual(stored["success_rate"], 0.8)

    async def test_failure_decreases_rate(self):
        from athanor_agents.skill_learning import Skill

        skill_data = Skill(
            skill_id="exec2",
            name="Test",
            execution_count=4,
            success_count=4,
            success_rate=1.0,
            avg_duration_ms=100.0,
        )
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(skill_data.to_dict()))

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import record_execution

            result = await record_execution("exec2", success=False, duration_ms=500.0)

        self.assertTrue(result)
        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(stored["success_count"], 4)  # Not incremented
        self.assertAlmostEqual(stored["success_rate"], 0.8)  # 4/5

    async def test_nonexistent_skill_returns_false(self):
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=None)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import record_execution

            result = await record_execution("missing", success=True, duration_ms=100.0)

        self.assertFalse(result)

    async def test_stores_context_in_examples(self):
        from athanor_agents.skill_learning import Skill

        skill_data = Skill(skill_id="exec3", name="Test").to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(skill_data))

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import record_execution

            await record_execution(
                "exec3",
                success=True,
                duration_ms=150.0,
                context={"task_id": "t1", "agent": "coding-agent"},
            )

        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(len(stored["examples"]), 1)
        self.assertEqual(stored["examples"][0]["context"]["task_id"], "t1")

    async def test_examples_capped_at_10(self):
        from athanor_agents.skill_learning import Skill

        existing_examples = [{"success": True, "duration_ms": 100, "timestamp": time.time()} for _ in range(10)]
        skill_data = Skill(
            skill_id="exec4",
            name="Test",
            examples=existing_examples,
            execution_count=10,
            success_count=10,
        ).to_dict()
        mock_r = _mock_redis()
        mock_r.hget = AsyncMock(return_value=json.dumps(skill_data))

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import record_execution

            await record_execution(
                "exec4", success=True, duration_ms=200.0,
                context={"new": True},
            )

        stored = json.loads(mock_r.hset.call_args[0][2])
        self.assertEqual(len(stored["examples"]), 10)  # Still 10, oldest dropped


class TestDeleteSkill(unittest.IsolatedAsyncioTestCase):
    """Test delete_skill() Redis removal."""

    async def test_returns_true_on_success(self):
        from athanor_agents.skill_learning import delete_skill

        mock_r = _mock_redis()
        mock_r.hdel = AsyncMock(return_value=1)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await delete_skill("abc123")

        self.assertTrue(result)

    async def test_returns_false_when_not_found(self):
        from athanor_agents.skill_learning import delete_skill

        mock_r = _mock_redis()
        mock_r.hdel = AsyncMock(return_value=0)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            result = await delete_skill("nonexistent")

        self.assertFalse(result)


class TestFindMatchingSkill(unittest.IsolatedAsyncioTestCase):
    """Test find_matching_skill() threshold matching."""

    async def test_returns_best_match_above_threshold(self):
        from athanor_agents.skill_learning import Skill

        skills = {
            "s1": json.dumps(Skill(
                skill_id="s1",
                name="Search Skill",
                trigger_conditions=["research", "search"],
            ).to_dict()),
            "s2": json.dumps(Skill(
                skill_id="s2",
                name="Deploy Skill",
                trigger_conditions=["deploy", "release"],
            ).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=skills)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import find_matching_skill

            result = await find_matching_skill("I want to research AI papers")

        self.assertIsNotNone(result)
        skill_id, relevance = result
        self.assertEqual(skill_id, "s1")
        self.assertGreaterEqual(relevance, 0.3)

    async def test_returns_none_below_threshold(self):
        from athanor_agents.skill_learning import Skill

        skills = {
            "s1": json.dumps(Skill(
                skill_id="s1",
                name="Very Specific Skill",
                trigger_conditions=["xyzzy unique trigger"],
            ).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=skills)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import find_matching_skill

            result = await find_matching_skill("completely unrelated query about cooking")

        self.assertIsNone(result)

    async def test_returns_none_with_empty_library(self):
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value={})

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import find_matching_skill

            result = await find_matching_skill("anything")

        self.assertIsNone(result)


class TestSearchSkillsForContext(unittest.IsolatedAsyncioTestCase):
    """Test search_skills_for_context() formatting."""

    async def test_returns_empty_for_no_matches(self):
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value={})

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import search_skills_for_context

            result = await search_skills_for_context("test-agent", "unrelated query")

        self.assertEqual(result, "")

    async def test_formats_matching_skills(self):
        from athanor_agents.skill_learning import Skill

        skills = {
            "s1": json.dumps(Skill(
                skill_id="s1",
                name="Research Workflow",
                category="research",
                trigger_conditions=["research"],
                steps=["Search web", "Synthesize"],
                execution_count=10,
                success_count=8,
                success_rate=0.8,
                avg_duration_ms=5000,
            ).to_dict()),
        }
        mock_r = _mock_redis()
        mock_r.hgetall = AsyncMock(return_value=skills)

        with patch("athanor_agents.skill_learning._get_redis", return_value=mock_r):
            from athanor_agents.skill_learning import search_skills_for_context

            result = await search_skills_for_context("research-agent", "research AI")

        self.assertIn("## Relevant Skills", result)
        self.assertIn("### Research Workflow", result)
        self.assertIn("80% success", result)


class TestInitialSkills(unittest.TestCase):
    """Test INITIAL_SKILLS seed data."""

    def test_seed_data_has_all_categories(self):
        from athanor_agents.skill_learning import INITIAL_SKILLS

        categories = {s["category"] for s in INITIAL_SKILLS}
        expected = {"research", "media", "creative", "knowledge", "infrastructure", "coding", "home", "stash"}
        self.assertEqual(categories, expected)

    def test_each_seed_has_required_fields(self):
        from athanor_agents.skill_learning import INITIAL_SKILLS

        for skill in INITIAL_SKILLS:
            self.assertIn("name", skill)
            self.assertIn("description", skill)
            self.assertIn("trigger_conditions", skill)
            self.assertIn("steps", skill)
            self.assertIsInstance(skill["trigger_conditions"], list)
            self.assertIsInstance(skill["steps"], list)
            self.assertGreater(len(skill["steps"]), 0)


if __name__ == "__main__":
    unittest.main()
