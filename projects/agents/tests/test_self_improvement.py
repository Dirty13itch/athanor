"""Tests for Self-Improvement Engine.

Covers:
- AUTO-003: Forbidden file rejection in validate_proposal
- Proposal lifecycle (create, validate, status transitions)
- Syntax validation (Python, YAML)
- Conservative v1 mutation posture
- Admission gating and backlog materialization
"""

import asyncio
import importlib.util
import json
import os
import sys
import types
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from unittest.mock import patch

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

_REPO_PATHS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "athanor_agents", "repo_paths.py"
)
spec = importlib.util.spec_from_file_location(
    "athanor_agents.repo_paths", _REPO_PATHS_PATH,
    submodule_search_locations=[],
)
repo_paths = importlib.util.module_from_spec(spec)
repo_paths.__package__ = "athanor_agents"
spec.loader.exec_module(repo_paths)
sys.modules["athanor_agents.repo_paths"] = repo_paths

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
    """Proposal creation and conservative v1 mutation posture."""

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

    def test_prompt_no_longer_auto_deploys_in_v1(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Prompt fix", description="Fix", category="prompt",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is False

    def test_config_no_longer_auto_deploys_in_v1(self):
        engine = _make_engine()
        proposal = _run(engine.propose_improvement(
            title="Config tune", description="Tune", category="config",
            target_files=[], proposed_changes={}, expected_improvement="",
        ))
        assert proposal.auto_deploy is False

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
        assert si.SelfImprovementEngine.AUTO_DEPLOY_CATEGORIES == set()


class _FakeRedis:
    def __init__(self, *, report: dict | None = None, last_cycle: dict | None = None) -> None:
        self.report = report
        self.last_cycle = last_cycle
        self.values: dict[str, str] = {}
        self.history: list[str] = []

    async def get(self, key: str):
        if key == "athanor:patterns:report" and self.report is not None:
            return json.dumps(self.report)
        if key == "improvement:last_cycle" and self.last_cycle is not None:
            return json.dumps(self.last_cycle)
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.values[key] = value

    async def lpush(self, key: str, value: str):
        if key == "improvement:cycle_history":
            self.history.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int):
        if key == "improvement:cycle_history":
            self.history = self.history[start : end + 1]


class TestImprovementAdmission:
    def test_review_debt_blocks_improvement_cycle(self):
        engine = _make_engine()
        redis = _FakeRedis(report={"patterns": [], "recommendations": []})
        engine._get_redis = AsyncMock(return_value=redis)
        engine._load_value_throughput_scorecard = AsyncMock(return_value={})

        governor = types.SimpleNamespace(
            build_capacity_snapshot=AsyncMock(
                return_value={
                    "posture": "healthy",
                    "queue": {"posture": "healthy"},
                    "provider_reserve": {"posture": "healthy"},
                    "local_compute": {
                        "idle_harvest_slots_open": True,
                        "harvestable_scheduler_slot_count": 2,
                        "scheduler_slot_count": 5,
                    },
                }
            )
        )
        execution = types.SimpleNamespace(
            get_approval_request_stats=AsyncMock(return_value={"total": 1, "by_status": {"pending": 1}})
        )
        operator_state = types.SimpleNamespace(list_backlog_records=AsyncMock(return_value=[]))
        operator_work = types.SimpleNamespace(materialize_improvement_proposal=AsyncMock())

        with patch.dict(
            sys.modules,
            {
                "athanor_agents.governor_backbone": governor,
                "athanor_agents.execution_state": execution,
                "athanor_agents.operator_state": operator_state,
                "athanor_agents.operator_work": operator_work,
            },
        ):
            result = _run(engine.run_improvement_cycle())

        assert result["status"] == "blocked_by_review_debt"
        assert result["admission_classification"] == "blocked_by_review_debt"
        assert "review debt" in result["admission_reason"].lower()
        assert result["proposals_generated"] == 0
        assert result["backlog_items_created"] == 0

    def test_dispatchable_product_backlog_blocks_improvement_cycle(self):
        engine = _make_engine()
        redis = _FakeRedis(report={"patterns": [], "recommendations": []})
        engine._get_redis = AsyncMock(return_value=redis)
        engine._load_value_throughput_scorecard = AsyncMock(return_value={})

        governor = types.SimpleNamespace(
            build_capacity_snapshot=AsyncMock(
                return_value={
                    "posture": "healthy",
                    "queue": {"posture": "healthy"},
                    "provider_reserve": {"posture": "healthy"},
                    "local_compute": {
                        "idle_harvest_slots_open": True,
                        "harvestable_scheduler_slot_count": 2,
                        "scheduler_slot_count": 5,
                    },
                }
            )
        )
        execution = types.SimpleNamespace(
            get_approval_request_stats=AsyncMock(return_value={"total": 0, "by_status": {}})
        )
        operator_state = types.SimpleNamespace(
            list_backlog_records=AsyncMock(
                return_value=[
                    {
                        "id": "backlog-builder-1",
                        "title": "Builder fix",
                        "owner_agent": "coding-agent",
                        "work_class": "coding_implementation",
                        "priority": 4,
                        "status": "ready",
                        "family": "builder",
                        "materialization_source": "operator_request",
                        "metadata": {},
                    }
                ]
            )
        )
        operator_work = types.SimpleNamespace(materialize_improvement_proposal=AsyncMock())

        with patch.dict(
            sys.modules,
            {
                "athanor_agents.governor_backbone": governor,
                "athanor_agents.execution_state": execution,
                "athanor_agents.operator_state": operator_state,
                "athanor_agents.operator_work": operator_work,
            },
        ):
            result = _run(engine.run_improvement_cycle())

        assert result["status"] == "blocked_by_queue_priority"
        assert result["admission_classification"] == "blocked_by_queue_priority"
        assert "backlog" in result["admission_reason"].lower()
        assert result["proposals_generated"] == 0
        assert result["backlog_items_created"] == 0

    def test_value_throughput_drift_blocks_improvement_cycle(self):
        engine = _make_engine()
        redis = _FakeRedis(report={"patterns": [], "recommendations": []})
        engine._get_redis = AsyncMock(return_value=redis)
        engine._load_value_throughput_scorecard = AsyncMock(
            return_value={
                "degraded_sections": [],
                "stale_claim_count": 1,
                "reconciliation": {
                    "issue_count": 1,
                },
            }
        )

        governor = types.SimpleNamespace(
            build_capacity_snapshot=AsyncMock(
                return_value={
                    "posture": "healthy",
                    "queue": {"posture": "healthy"},
                    "provider_reserve": {"posture": "healthy"},
                    "local_compute": {
                        "idle_harvest_slots_open": True,
                        "harvestable_scheduler_slot_count": 2,
                        "scheduler_slot_count": 5,
                    },
                }
            )
        )
        execution = types.SimpleNamespace(
            get_approval_request_stats=AsyncMock(return_value={"total": 0, "by_status": {}})
        )
        operator_state = types.SimpleNamespace(list_backlog_records=AsyncMock(return_value=[]))
        operator_work = types.SimpleNamespace(materialize_improvement_proposal=AsyncMock())

        with patch.dict(
            sys.modules,
            {
                "athanor_agents.governor_backbone": governor,
                "athanor_agents.execution_state": execution,
                "athanor_agents.operator_state": operator_state,
                "athanor_agents.operator_work": operator_work,
            },
        ):
            result = _run(engine.run_improvement_cycle())

        assert result["status"] == "blocked_by_headroom"
        assert result["admission_classification"] == "blocked_by_headroom"
        assert "throughput" in result["admission_reason"].lower()
        assert result["proposals_generated"] == 0
        assert result["backlog_items_created"] == 0

    def test_improvement_cycle_materializes_generated_proposals_into_backlog(self):
        engine = _make_engine()
        redis = _FakeRedis(
            report={
                "patterns": [{"id": "pattern-1"}],
                "recommendations": ["Tighten the coding-agent handoff prompt."],
            }
        )
        engine._get_redis = AsyncMock(return_value=redis)
        engine._load_value_throughput_scorecard = AsyncMock(return_value={})
        engine.run_benchmark_suite = AsyncMock(
            return_value={
                "timestamp": "2026-04-18T12:00:00Z",
                "passed": 4,
                "total": 5,
                "pass_rate": 0.8,
                "results": [],
                "comparison": {
                    "agent_health": {
                        "baseline": 90.0,
                        "new": 70.0,
                        "delta": -20.0,
                        "improved": False,
                        "regressed": True,
                    }
                },
            }
        )

        governor = types.SimpleNamespace(
            build_capacity_snapshot=AsyncMock(
                return_value={
                    "posture": "healthy",
                    "queue": {"posture": "healthy"},
                    "provider_reserve": {"posture": "healthy"},
                    "local_compute": {
                        "idle_harvest_slots_open": True,
                        "harvestable_scheduler_slot_count": 2,
                        "scheduler_slot_count": 5,
                    },
                }
            )
        )
        execution = types.SimpleNamespace(
            get_approval_request_stats=AsyncMock(return_value={"total": 0, "by_status": {}})
        )
        operator_state = types.SimpleNamespace(list_backlog_records=AsyncMock(return_value=[]))
        operator_work = types.SimpleNamespace(
            materialize_improvement_proposal=AsyncMock(
                side_effect=[
                    {
                        "status": "created",
                        "backlog_id": "backlog-improvement-1",
                        "family": "maintenance",
                    },
                    {
                        "status": "refreshed",
                        "backlog_id": "backlog-improvement-2",
                        "family": "maintenance",
                    },
                ]
            )
        )

        with patch.dict(
            sys.modules,
            {
                "athanor_agents.governor_backbone": governor,
                "athanor_agents.execution_state": execution,
                "athanor_agents.operator_state": operator_state,
                "athanor_agents.operator_work": operator_work,
            },
        ):
            result = _run(engine.run_improvement_cycle())

        assert result["status"] == "proposal_only"
        assert result["admission_classification"] == "proposal_only"
        assert result["proposals_generated"] == 2
        assert result["backlog_items_created"] == 1
        assert result["backlog_items_refreshed"] == 1
        assert result["backlog_ids"] == ["backlog-improvement-1", "backlog-improvement-2"]
        assert result["review_ids"] == []
        assert operator_work.materialize_improvement_proposal.await_count == 2
