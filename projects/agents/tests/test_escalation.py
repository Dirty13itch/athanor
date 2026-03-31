"""Tests for escalation protocol — confidence-based tiers and queue management.

Covers:
- Tier evaluation (ACT/NOTIFY/ASK)
- Threshold logic with defaults and per-agent overrides
- PURGE category (never autonomous)
- Pending action queue operations
"""

import importlib.util
import os
import sys
from unittest.mock import MagicMock

# Mock dependencies before import
_mock_config = MagicMock()
_mock_config.settings.dashboard_url = "http://localhost:3001"
_mock_config.settings.ntfy_url = "http://localhost:8880"
_mock_config.settings.ntfy_topic = "athanor"

for mod in ["httpx", "athanor_agents.workspace", "athanor_agents.goals"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = _mock_config
sys.modules[".config"] = _mock_config

_ESC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "escalation.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.escalation", _ESC_PATH,
    submodule_search_locations=[],
)
escalation = importlib.util.module_from_spec(spec)
escalation.__package__ = "athanor_agents"
spec.loader.exec_module(escalation)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]


class TestTierEvaluation:
    """Escalation tier determination."""

    def test_read_always_acts(self):
        tier = escalation.evaluate(
            "general-assistant", "check status", escalation.ActionCategory.READ, 0.1
        )
        assert tier == escalation.EscalationTier.ACT

    def test_delete_high_confidence_acts(self):
        tier = escalation.evaluate(
            "media-agent", "remove movie", escalation.ActionCategory.DELETE, 0.96
        )
        assert tier == escalation.EscalationTier.ACT

    def test_delete_medium_confidence_notifies(self):
        tier = escalation.evaluate(
            "media-agent", "remove movie", escalation.ActionCategory.DELETE, 0.7
        )
        assert tier == escalation.EscalationTier.NOTIFY

    def test_delete_low_confidence_asks(self):
        tier = escalation.evaluate(
            "media-agent", "remove movie", escalation.ActionCategory.DELETE, 0.3
        )
        assert tier == escalation.EscalationTier.ASK

    def test_security_never_autonomous(self):
        """SECURITY category threshold is 1.0 — never autonomous."""
        tier = escalation.evaluate(
            "general-assistant", "disable auth", escalation.ActionCategory.SECURITY, 0.99
        )
        assert tier == escalation.EscalationTier.NOTIFY

    def test_purge_never_autonomous(self):
        """PURGE category threshold is 1.0 — never autonomous."""
        tier = escalation.evaluate(
            "system", "purge personal data", escalation.ActionCategory.PURGE, 0.99
        )
        assert tier == escalation.EscalationTier.NOTIFY

    def test_home_agent_lower_routine_threshold(self):
        """Home agent has lower threshold for routine actions."""
        tier = escalation.evaluate(
            "home-agent", "turn off light", escalation.ActionCategory.ROUTINE, 0.45
        )
        assert tier == escalation.EscalationTier.ACT


class TestPendingActions:
    """Pending action queue operations."""

    def setup_method(self):
        # Clear queue
        escalation._pending_actions.clear()
        escalation._notification_counter = 0

    def test_queue_pending_action(self):
        pending = escalation.queue_pending_action(
            agent="test-agent",
            action="test action",
            category="delete",
            confidence=0.3,
            description="Testing the queue",
        )
        assert pending.id.startswith("pending-")
        assert pending.agent == "test-agent"
        assert not pending.resolved

    def test_get_pending_returns_unresolved(self):
        escalation.queue_pending_action(
            "test", "action1", "delete", 0.3, "desc1"
        )
        escalation.queue_pending_action(
            "test", "action2", "config", 0.4, "desc2"
        )
        pending = escalation.get_pending()
        assert len(pending) == 2

    def test_resolve_action_approve(self):
        pa = escalation.queue_pending_action(
            "test", "action", "delete", 0.3, "desc"
        )
        result = escalation.resolve_action(pa.id, approved=True)
        assert result is True
        assert pa.resolved
        assert pa.resolution == "approved"

    def test_resolve_action_reject(self):
        pa = escalation.queue_pending_action(
            "test", "action", "delete", 0.3, "desc"
        )
        result = escalation.resolve_action(pa.id, approved=False)
        assert result is True
        assert pa.resolution == "rejected"

    def test_resolve_nonexistent_returns_false(self):
        result = escalation.resolve_action("nonexistent-id", approved=True)
        assert result is False

    def test_get_pending_excludes_resolved(self):
        pa = escalation.queue_pending_action(
            "test", "action", "delete", 0.3, "desc"
        )
        escalation.resolve_action(pa.id, approved=True)
        pending = escalation.get_pending(include_resolved=False)
        assert len(pending) == 0

    def test_get_pending_includes_resolved(self):
        pa = escalation.queue_pending_action(
            "test", "action", "delete", 0.3, "desc"
        )
        escalation.resolve_action(pa.id, approved=True)
        all_pending = escalation.get_pending(include_resolved=True)
        assert len(all_pending) == 1

    def test_unread_count(self):
        escalation.queue_pending_action("t", "a", "d", 0.3, "d")
        escalation.queue_pending_action("t", "b", "d", 0.3, "d")
        assert escalation.get_unread_count() == 2

    def test_notification_adds_as_resolved(self):
        notif = escalation.add_notification(
            "test", "did thing", "routine", 0.8, "already done"
        )
        assert notif.resolved  # Notifications are pre-resolved
        assert escalation.get_unread_count() == 0


class TestThresholds:
    """Threshold configuration and retrieval."""

    def test_default_thresholds(self):
        config = escalation.get_thresholds_config()
        assert config["read"]["default"] == 0.0
        assert config["security"]["default"] == 1.0
        assert config["purge"]["default"] == 1.0

    def test_get_threshold_default(self):
        threshold = escalation.get_threshold("unknown-agent", escalation.ActionCategory.DELETE)
        assert threshold == 0.95

    def test_get_threshold_agent_override(self):
        threshold = escalation.get_threshold("home-agent", escalation.ActionCategory.ROUTINE)
        assert threshold == 0.4


class TestNotificationLinks:
    def test_notifications_review_hint_prefers_canonical_front_door(self):
        assert escalation._notifications_review_hint() == (
            "Review: https://athanor.local/notifications "
            "(fallback http://localhost:3001/notifications)"
        )
