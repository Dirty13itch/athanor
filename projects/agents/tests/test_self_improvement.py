"""Tests for Self-Improvement Engine.

Covers:
- AUTO-003: Forbidden file rejection in validate_proposal
- Proposal lifecycle (create, validate, status transitions)
- Syntax validation (Python, YAML)
- Auto-deploy category classification
"""

import asyncio
import importlib.util
import os
import sys
from unittest.mock import MagicMock

import pytest

# Mock dependencies before import
_mock_config = MagicMock()
_mock_config.settings.qdrant_url = "http://localhost:6333"
_mock_config.settings.redis_url = "redis://localhost:6379"
_mock_config.settings.redis_password = None
_mock_config.settings.llm_base_url = "http://localhost:4000"

sys.modules["athanor_agents"] = MagicMock()
sys.modules["athanor_agents.config"] = _mock_config
sys.modules["athanor_agents.workspace"] = MagicMock()
sys.modules["athanor_agents.services"] = MagicMock()

# Load constitution (needed for forbidden file checks)
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

# Set up constitution with test forbidden/allowed patterns
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

# Load self_improvement
_SI_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "self_improvement.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.self_improvement", _SI_PATH,
    submodule_search_locations=[],
)
si = importlib.util.module_from_spec(spec)
si.__package__ = "athanor_agents"
spec.loader.exec_module(si)

# Cleanup: remove MagicMock entries to prevent polluting other test files
for _k in list(sys.modules):
    if isinstance(sys.modules[_k], MagicMock):
        del sys.modules[_k]


def _run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


def _make_engine():
    """Create a fresh engine with no Redis."""
    engine = si.SelfImprovementEngine()
    engine._redis = None
    return engine


class TestProposalCreation:
    """Proposal creation and auto-deploy classification."""

    def test_create_proposal(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Test improvement",
            description="A test proposal",
            category="prompt",
            target_files=["projects/agents/prompts/test.md"],
            proposed_changes={},
            expected_improvement="Better responses",
        ))
        assert proposal.title == "Test improvement"
        assert proposal.status == "proposed"
        assert len(proposal.id) == 8

    def test_prompt_auto_deploys(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Prompt fix", description="Fix", category="prompt",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is True

    def test_config_auto_deploys(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Config tune", description="Tune", category="config",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is True

    def test_code_requires_review(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Code change", description="Change", category="code",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is False

    def test_infra_requires_review(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Infra change", description="Change", category="infrastructure",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is False


class TestForbiddenFileValidation:
    """AUTO-003: validate_proposal rejects forbidden files."""

    def test_constitution_yaml_rejected(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Modify constitution", description="Bad idea",
            category="config",
            target_files=["CONSTITUTION.yaml"],
            proposed_changes={},
            expected_improvement="",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"
        assert not result["ready_to_deploy"]

    def test_env_file_rejected(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Modify env", description="Bad",
            category="config",
            target_files=[".env.production"],
            proposed_changes={},
            expected_improvement="",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"

    def test_secrets_dir_rejected(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Secrets access", description="Bad",
            category="config",
            target_files=["path/to/secrets/key.pem"],
            proposed_changes={},
            expected_improvement="",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"

    def test_proposed_changes_also_checked(self):
        """Forbidden check applies to proposed_changes keys too."""
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Sneak through changes", description="Bad",
            category="prompt",
            target_files=["projects/agents/prompts/safe.md"],
            proposed_changes={"CONSTITUTION.yaml": "evil content"},
            expected_improvement="",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"

    def test_allowed_path_passes_forbidden_check(self):
        """Files in allowed paths pass the forbidden check."""
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Safe change", description="Good",
            category="prompt",
            target_files=["projects/agents/prompts/assistant.md"],
            proposed_changes={},
            expected_improvement="Better",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        # No forbidden file checks should fail — status should be validated
        assert result["status"] == "validated"


class TestSyntaxValidation:
    """validate_proposal checks Python and YAML syntax."""

    def test_valid_python_passes(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Valid Python", description="Good code",
            category="code",
            target_files=["projects/agents/src/athanor_agents/test.py"],
            proposed_changes={
                "projects/agents/src/athanor_agents/test.py": "def hello():\n    return 'world'\n",
            },
            expected_improvement="Better code",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "validated"
        assert result["ready_to_deploy"]

    def test_invalid_python_fails(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Bad Python", description="Broken code",
            category="code",
            target_files=["projects/agents/src/athanor_agents/test.py"],
            proposed_changes={
                "projects/agents/src/athanor_agents/test.py": "def hello(\n    broken syntax",
            },
            expected_improvement="Worse code",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"
        assert not result["ready_to_deploy"]

    def test_valid_yaml_passes(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Valid YAML", description="Good config",
            category="config",
            target_files=["projects/agents/config.yml"],
            proposed_changes={
                "projects/agents/config.yml": "key: value\nlist:\n  - item1\n  - item2\n",
            },
            expected_improvement="Better config",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "validated"

    def test_invalid_yaml_fails(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Bad YAML", description="Broken config",
            category="config",
            target_files=["projects/agents/config.yml"],
            proposed_changes={
                "projects/agents/config.yml": "key: value\n  bad indent: [unterminated",
            },
            expected_improvement="Worse config",
        ))
        result = _run(engine.validate_proposal(proposal.id))
        assert result["status"] == "failed"

    def test_nonexistent_proposal_returns_error(self):
        engine = _make_engine()
        result = _run(engine.validate_proposal("nonexistent-id"))
        assert "error" in result


class TestImprovementStatus:
    """Status enum values."""

    def test_status_values(self):
        assert si.ImprovementStatus.PROPOSED.value == "proposed"
        assert si.ImprovementStatus.TESTING.value == "testing"
        assert si.ImprovementStatus.VALIDATED.value == "validated"
        assert si.ImprovementStatus.DEPLOYED.value == "deployed"
        assert si.ImprovementStatus.FAILED.value == "failed"
        assert si.ImprovementStatus.ROLLED_BACK.value == "rolled_back"

    def test_auto_deploy_categories(self):
        assert si.SelfImprovementEngine.AUTO_DEPLOY_CATEGORIES == {"prompt", "config"}
