"""Tests for memory consolidation pipeline.

Covers:
- Constitutional gate integration (DATA-001/004)
- Protected collections blocked from autonomous purge
- Allowed collections within threshold pass
- Purge function with mocked HTTP
"""

import asyncio
import importlib.util
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock dependencies before import
_mock_config = MagicMock()
_mock_config.settings.qdrant_url = "http://localhost:6333"
_mock_config.settings.redis_url = "redis://localhost:6379"
_mock_config.settings.redis_password = None

sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = _mock_config
sys.modules["athanor_agents.workspace"] = MagicMock()
sys.modules["athanor_agents.goals"] = MagicMock()

# Load constitution with real enforcement logic
_CONST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "constitution.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.constitution", _CONST_PATH,
    submodule_search_locations=[],
)
constitution = importlib.util.module_from_spec(spec)
constitution.__package__ = "athanor_agents"
spec.loader.exec_module(constitution)
sys.modules["athanor_agents.constitution"] = constitution

# Mock escalation
sys.modules["athanor_agents.escalation"] = MagicMock()
sys.modules["athanor_agents.activity"] = MagicMock()

# Load consolidation
_CONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "consolidation.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.consolidation", _CONS_PATH,
    submodule_search_locations=[],
)
consolidation = importlib.util.module_from_spec(spec)
consolidation.__package__ = "athanor_agents"
spec.loader.exec_module(consolidation)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]


class TestRetentionConfig:
    """Verify retention policies match CONSTITUTION expectations."""

    def test_retention_days(self):
        assert consolidation.RETENTION["activity"] == 30
        assert consolidation.RETENTION["conversations"] == 30
        assert consolidation.RETENTION["implicit_feedback"] == 7
        assert consolidation.RETENTION["events"] == 14

    def test_max_batch_size(self):
        assert consolidation.MAX_DELETE_BATCH == 500


class TestConstitutionalGate:
    """DATA-001/004: Constitutional checks gate purge operations."""

    def test_activity_within_threshold_allowed(self):
        allowed, reason = constitution.check_destructive_operation(
            "delete", "activity", count=100, actor="consolidation"
        )
        assert allowed

    def test_activity_above_threshold_blocked(self):
        allowed, reason = constitution.check_destructive_operation(
            "delete", "activity", count=501, actor="consolidation"
        )
        assert not allowed
        assert "DATA-001" in reason

    def test_conversations_always_blocked(self):
        """DATA-004: Protected collections always blocked."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "conversations", count=1, actor="consolidation"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_personal_data_always_blocked(self):
        allowed, reason = constitution.check_destructive_operation(
            "delete", "personal_data", count=1, actor="consolidation"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_implicit_feedback_allowed(self):
        allowed, reason = constitution.check_destructive_operation(
            "delete", "implicit_feedback", count=400, actor="consolidation"
        )
        assert allowed


class TestPurgeFunction:
    """Test _purge_old_points with mocked HTTP."""

    def test_empty_collection_returns_zero(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(status_code=200)
        count_resp = MagicMock(status_code=200)
        count_resp.json.return_value = {"result": {"count": 0}}
        scroll_resp = MagicMock(status_code=200)
        scroll_resp.json.return_value = {"result": {"points": [], "next_page_offset": None}}
        mock_client.post.side_effect = [count_resp, scroll_resp]

        deleted = asyncio.run(consolidation._purge_old_points(mock_client, "activity", 30))
        assert deleted == 0

    def test_missing_collection_returns_zero(self):
        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(status_code=404)

        deleted = asyncio.run(consolidation._purge_old_points(mock_client, "nonexistent", 30))
        assert deleted == 0

    def test_blocked_collection_returns_zero(self):
        """Purging a protected collection is blocked by constitution."""
        mock_client = AsyncMock()
        mock_client.get.return_value = MagicMock(status_code=200)
        count_resp = MagicMock(status_code=200)
        count_resp.json.return_value = {"result": {"count": 50}}
        scroll_resp = MagicMock(status_code=200)
        scroll_resp.json.return_value = {
            "result": {
                "points": [{"id": f"pt-{i}"} for i in range(10)],
                "next_page_offset": None,
            }
        }
        mock_client.post.side_effect = [count_resp, scroll_resp]

        # personal_data is DATA-004 protected
        deleted = asyncio.run(
            consolidation._purge_old_points(mock_client, "personal_data", 30)
        )
        assert deleted == 0
