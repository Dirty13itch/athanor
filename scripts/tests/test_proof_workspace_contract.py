from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_proof_workspace_sync_paths_cover_repo_root_validator_surface() -> None:
    module = _load_module(
        f"proof_workspace_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "proof_workspace_contract.py",
    )

    manifest = set(module.proof_workspace_sync_paths())

    assert {
        "AGENTS.md",
        "CLAUDE.md",
        "MEMORY.md",
        "PROJECT.md",
        "README.md",
        "SESSION-LOG.md",
        "STATUS.md",
        "audit/automation/contract-healer-latest.json",
        ".claude",
        ".gitea",
        ".mcp.json",
        "ansible",
        "config",
        "docs",
        "evals/pilot-agent-compare",
        "projects/agents",
        "projects/dashboard/docker-compose.yml",
        "projects/dashboard/src/generated",
        "projects/gpu-orchestrator",
        "projects/ws-pty-bridge",
        "services/governor",
        "services/gateway",
        "services/quality-gate",
        "services/sentinel",
        "tests/ui-audit",
        "reports",
        "scripts",
        "services/cluster_config.py",
    }.issubset(manifest)


def test_proof_workspace_sync_manifest_paths_exist_in_repo() -> None:
    module = _load_module(
        f"proof_workspace_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "proof_workspace_contract.py",
    )

    assert module.missing_paths(REPO_ROOT, module.proof_workspace_sync_paths()) == []


def test_devstack_proof_sync_manifest_stays_narrow_and_stable() -> None:
    module = _load_module(
        f"proof_workspace_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "proof_workspace_contract.py",
    )

    assert module.devstack_proof_root() == "_external/devstack"
    manifest = set(module.devstack_proof_sync_paths())

    assert "configs/devstack-capability-lane-registry.json" in manifest
    assert "reports/master-atlas/latest.json" in manifest
    assert "docs/promotion-packets/watchdog-runtime-guard.md" in manifest
    assert "docs/promotion-packets/agent-governance-toolkit-policy-plane.md" in manifest
    assert "docs/research/2026-04-11-ai-os-agent-registry-review.md" in manifest
