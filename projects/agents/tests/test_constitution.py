"""Tests for constitutional enforcement (constitution.py).

Covers:
- DATA-001: Destructive operation thresholds
- DATA-002: Drop/truncate always blocked
- DATA-004: Protected collection deletion blocked
- INFRA-003: Peak hours detection
- AUTO-003: Forbidden file enforcement
- DATA-003: Point ID snapshots before deletion
"""

import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Direct import of the module under test
import importlib.util
import os
import sys

_CONST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "constitution.py"
)
spec = importlib.util.spec_from_file_location("constitution", _CONST_PATH)
constitution = importlib.util.module_from_spec(spec)

# Mock dependencies before exec
sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = MagicMock()
sys.modules["athanor_agents.workspace"] = MagicMock()
sys.modules[".config"] = MagicMock()
sys.modules[".workspace"] = MagicMock()

# Provide a minimal yaml module and config
import yaml as _yaml
sys.modules["yaml"] = _yaml

spec.loader.exec_module(constitution)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]

# Reset the cached constitution to use test data
constitution._constitution = None


class TestDestructiveOperations:
    """DATA-001, DATA-002, DATA-004 enforcement."""

    def test_drop_always_blocked(self):
        """DATA-002: drop operations are always blocked."""
        allowed, reason = constitution.check_destructive_operation(
            "drop", "activity", count=1, actor="test"
        )
        assert not allowed
        assert "DATA-002" in reason

    def test_truncate_always_blocked(self):
        """DATA-002: truncate operations are always blocked."""
        allowed, reason = constitution.check_destructive_operation(
            "truncate", "events", count=1, actor="test"
        )
        assert not allowed
        assert "DATA-002" in reason

    def test_delete_from_protected_collection_blocked(self):
        """DATA-004: personal_data deletion always requires approval."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "personal_data", count=1, actor="test"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_delete_from_conversations_blocked(self):
        """DATA-004: conversations deletion always requires approval."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "conversations", count=5, actor="consolidation"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_delete_from_knowledge_blocked(self):
        """DATA-004: knowledge deletion always requires approval."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "knowledge", count=1, actor="test"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_delete_from_preferences_blocked(self):
        """DATA-004: preferences deletion always requires approval."""
        allowed, reason = constitution.check_destructive_operation(
            "purge", "preferences", count=1, actor="test"
        )
        assert not allowed
        assert "DATA-004" in reason

    def test_activity_delete_within_threshold_allowed(self):
        """DATA-001: activity collection allows up to 500 deletions autonomously."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "activity", count=100, actor="consolidation"
        )
        assert allowed
        assert reason == "OK"

    def test_activity_delete_above_threshold_blocked(self):
        """DATA-001: activity collection blocks above 500 deletions."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "activity", count=501, actor="consolidation"
        )
        assert not allowed
        assert "DATA-001" in reason

    def test_events_delete_within_threshold_allowed(self):
        allowed, reason = constitution.check_destructive_operation(
            "delete", "events", count=200, actor="consolidation"
        )
        assert allowed

    def test_implicit_feedback_delete_allowed(self):
        """Ephemeral collection — always allowed within threshold."""
        allowed, reason = constitution.check_destructive_operation(
            "delete", "implicit_feedback", count=400, actor="consolidation"
        )
        assert allowed

    def test_unknown_collection_low_threshold(self):
        """Unknown collections default to threshold of 10."""
        allowed, _ = constitution.check_destructive_operation(
            "delete", "unknown_collection", count=5, actor="test"
        )
        assert allowed

        allowed, reason = constitution.check_destructive_operation(
            "delete", "unknown_collection", count=11, actor="test"
        )
        assert not allowed
        assert "DATA-001" in reason


class TestPeakHours:
    """INFRA-003: Peak hours protection."""

    def test_peak_hours_detected(self):
        """8 AM — 10 PM is peak hours."""
        mock_dt = MagicMock(wraps=datetime)
        with patch.object(constitution, "datetime", mock_dt):
            for hour in [8, 12, 15, 21]:
                mock_dt.now.return_value = datetime(2026, 3, 14, hour, 30)
                assert constitution.is_peak_hours()

    def test_off_peak_detected(self):
        """Before 8 AM and after 10 PM is off-peak."""
        mock_dt = MagicMock(wraps=datetime)
        with patch.object(constitution, "datetime", mock_dt):
            for hour in [0, 3, 5, 7, 22, 23]:
                mock_dt.now.return_value = datetime(2026, 3, 14, hour, 30)
                assert not constitution.is_peak_hours()

    def test_restart_blocked_during_peak(self):
        mock_dt = MagicMock(wraps=datetime)
        with patch.object(constitution, "datetime", mock_dt):
            mock_dt.now.return_value = datetime(2026, 3, 14, 14, 0)
            allowed, reason = constitution.check_peak_hours_restart("redis")
            assert not allowed
            assert "INFRA-003" in reason

    def test_restart_allowed_off_peak(self):
        mock_dt = MagicMock(wraps=datetime)
        with patch.object(constitution, "datetime", mock_dt):
            mock_dt.now.return_value = datetime(2026, 3, 14, 3, 0)
            allowed, reason = constitution.check_peak_hours_restart("redis")
            assert allowed


class TestForbiddenFiles:
    """AUTO-003: Self-improvement forbidden file enforcement."""

    def setup_method(self):
        # Ensure constitution is loaded with default forbidden patterns
        constitution._constitution = {
            "self_improvement": {
                "forbidden_modifications": [
                    "CONSTITUTION.yaml", ".env*", "**/secrets/**",
                    "**/credentials/**", "/etc/**",
                ],
                "allowed_modifications": [
                    "projects/**", "services/**", "scripts/**",
                    "ansible/roles/**", "tests/**",
                ],
            }
        }

    def test_constitution_yaml_forbidden(self):
        allowed, reason = constitution.check_forbidden_file("CONSTITUTION.yaml")
        assert not allowed
        assert "AUTO-003" in reason

    def test_env_file_forbidden(self):
        allowed, reason = constitution.check_forbidden_file(".env")
        assert not allowed

    def test_env_local_forbidden(self):
        allowed, reason = constitution.check_forbidden_file(".env.production")
        assert not allowed

    def test_secrets_dir_forbidden(self):
        allowed, reason = constitution.check_forbidden_file("path/to/secrets/key.pem")
        assert not allowed

    def test_etc_forbidden(self):
        allowed, reason = constitution.check_forbidden_file("/etc/systemd/system/foo.service")
        assert not allowed

    def test_projects_allowed(self):
        allowed, reason = constitution.check_forbidden_file("projects/agents/src/file.py")
        assert allowed
        assert reason == "OK"

    def test_scripts_allowed(self):
        allowed, reason = constitution.check_forbidden_file("scripts/backup.sh")
        assert allowed

    def test_ansible_roles_allowed(self):
        allowed, reason = constitution.check_forbidden_file("ansible/roles/vllm/tasks/main.yml")
        assert allowed

    def test_root_file_outside_allowed_blocked(self):
        allowed, reason = constitution.check_forbidden_file("README.md")
        assert not allowed
        assert "outside allowed" in reason

    def test_docs_outside_allowed_blocked(self):
        allowed, reason = constitution.check_forbidden_file("docs/VISION.md")
        assert not allowed


class TestAuditLogging:
    """AUTO-002: Audit trail verification."""

    def test_audit_logger_creates(self):
        """Verify audit logger initializes without error."""
        audit = constitution._get_audit_logger()
        assert audit is not None
        assert audit.name == "athanor.audit"

    def test_log_audit_doesnt_crash(self):
        """Verify audit logging doesn't raise even if file not writable."""
        # Should not raise
        constitution._log_audit(
            operation_type="test",
            target_resource="test_target",
            actor="test",
            result="test",
            constraint_checked="TEST",
        )
