"""Tests for GWT workspace manager.

Covers:
- Salience computation (urgency x recency + coalition)
- Keyword relevance scoring
- Self-reaction prevention
- Priority weights
- Workspace capacity constant
"""

import importlib.util
import os
import sys
import time
from unittest.mock import MagicMock

# Mock dependencies
_mock_config = MagicMock()
_mock_config.settings.redis_url = "redis://localhost:6379"
_mock_config.settings.redis_password = None

sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = _mock_config
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()

_WS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "workspace.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.workspace", _WS_PATH,
    submodule_search_locations=[],
)
ws = importlib.util.module_from_spec(spec)
ws.__package__ = "athanor_agents"
spec.loader.exec_module(ws)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]


class TestSalienceComputation:
    """compute_salience scoring."""

    def test_critical_priority_highest(self):
        item = ws.WorkspaceItem(
            source_agent="system",
            content="alert",
            priority="critical",
            created_at=time.time(),
            ttl=300,
        )
        salience = ws.compute_salience(item)
        assert salience > 5.0  # Critical weight is 10.0

    def test_low_priority_lowest(self):
        item = ws.WorkspaceItem(
            source_agent="test",
            content="background task",
            priority="low",
            created_at=time.time(),
            ttl=300,
        )
        salience = ws.compute_salience(item)
        assert salience <= 1.0  # Low weight is 1.0

    def test_recency_decay(self):
        now = time.time()
        fresh = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=now, ttl=300,
        )
        stale = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=now - 250, ttl=300,
        )
        assert ws.compute_salience(fresh) > ws.compute_salience(stale)

    def test_expired_item_zero_salience(self):
        item = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=time.time() - 600, ttl=300,
        )
        salience = ws.compute_salience(item)
        assert salience == 0.0  # Past TTL

    def test_coalition_boosts_salience(self):
        base = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=time.time(), ttl=300,
            coalition=[],
        )
        boosted = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=time.time(), ttl=300,
            coalition=["agent-a", "agent-b", "agent-c"],
        )
        assert ws.compute_salience(boosted) > ws.compute_salience(base)
        # Coalition bonus = 3 * 0.15 = 0.45
        diff = ws.compute_salience(boosted) - ws.compute_salience(base)
        assert abs(diff - 0.45) < 0.05

    def test_zero_ttl_no_decay(self):
        item = ws.WorkspaceItem(
            source_agent="test", content="test", priority="normal",
            created_at=time.time() - 1000, ttl=0,
        )
        salience = ws.compute_salience(item)
        assert salience > 0  # recency=1.0 when ttl=0


class TestKeywordRelevance:
    """compute_keyword_relevance scoring."""

    def test_keyword_match(self):
        item = ws.WorkspaceItem(
            source_agent="research-agent",
            content="New findings about GPU performance optimization",
        )
        sub = ws.AgentSubscription(
            agent_name="coding-agent",
            keywords=["GPU", "performance", "optimization"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score > 0.5

    def test_no_keyword_match(self):
        item = ws.WorkspaceItem(
            source_agent="media-agent",
            content="New movie recommendations available",
        )
        sub = ws.AgentSubscription(
            agent_name="coding-agent",
            keywords=["python", "code", "bug"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score == 0.0

    def test_source_filter_match(self):
        item = ws.WorkspaceItem(
            source_agent="research-agent",
            content="General update",
        )
        sub = ws.AgentSubscription(
            agent_name="knowledge-agent",
            keywords=[],
            source_filters=["research-agent"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score == 0.5  # Source match gives 0.5

    def test_self_reaction_blocked(self):
        """Agents should not react to their own items."""
        item = ws.WorkspaceItem(
            source_agent="coding-agent",
            content="I found a bug in the code",
        )
        sub = ws.AgentSubscription(
            agent_name="coding-agent",
            keywords=["bug", "code"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score == 0.0

    def test_combined_source_and_keyword(self):
        item = ws.WorkspaceItem(
            source_agent="research-agent",
            content="Found new GPU benchmarks for inference",
        )
        sub = ws.AgentSubscription(
            agent_name="coding-agent",
            keywords=["GPU", "inference", "benchmarks"],
            source_filters=["research-agent"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score > 0.5  # Both source and keywords match
        assert score <= 1.0

    def test_case_insensitive_keywords(self):
        item = ws.WorkspaceItem(
            source_agent="other-agent",
            content="GPU Performance Optimization Tips",
        )
        sub = ws.AgentSubscription(
            agent_name="test-agent",
            keywords=["gpu", "performance"],
        )
        score = ws.compute_keyword_relevance(item, sub)
        assert score > 0.0


class TestWorkspaceConfig:
    """Workspace constants and structure."""

    def test_workspace_capacity(self):
        assert ws.WORKSPACE_CAPACITY == 7

    def test_competition_interval(self):
        assert ws.COMPETITION_INTERVAL == 1.0

    def test_coalition_bonus(self):
        assert ws.COALITION_BONUS == 0.15

    def test_priority_weights(self):
        assert ws.PRIORITY_WEIGHTS[ws.ItemPriority.CRITICAL] == 10.0
        assert ws.PRIORITY_WEIGHTS[ws.ItemPriority.HIGH] == 5.0
        assert ws.PRIORITY_WEIGHTS[ws.ItemPriority.NORMAL] == 2.0
        assert ws.PRIORITY_WEIGHTS[ws.ItemPriority.LOW] == 1.0


class TestWorkspaceItem:
    """WorkspaceItem data structure."""

    def test_default_id(self):
        item = ws.WorkspaceItem(source_agent="test", content="test")
        assert len(item.id) == 8

    def test_to_dict_roundtrip(self):
        item = ws.WorkspaceItem(
            source_agent="test-agent",
            content="test content",
            priority="high",
        )
        data = item.to_dict()
        restored = ws.WorkspaceItem.from_dict(data)
        assert restored.source_agent == "test-agent"
        assert restored.content == "test content"
        assert restored.priority == "high"


class TestAgentSubscription:
    """AgentSubscription data structure."""

    def test_to_dict_roundtrip(self):
        sub = ws.AgentSubscription(
            agent_name="coding-agent",
            keywords=["python", "code"],
            source_filters=["research-agent"],
            threshold=0.5,
        )
        data = sub.to_dict()
        restored = ws.AgentSubscription.from_dict(data)
        assert restored.agent_name == "coding-agent"
        assert restored.keywords == ["python", "code"]
        assert restored.threshold == 0.5
