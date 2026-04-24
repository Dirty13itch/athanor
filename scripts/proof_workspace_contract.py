from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final


REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTACK_LOCAL_ROOT = Path("/mnt/c/athanor-devstack")
PROOF_WORKSPACE_SYNC_PATHS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    "CLAUDE.md",
    "MEMORY.md",
    "PROJECT.md",
    "README.md",
    "SESSION-LOG.md",
    "STATUS.md",
    "CONSTITUTION.yaml",
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
    "reports",
    "scripts",
    "services/cluster_config.py",
    "services/governor",
    "services/gateway",
    "services/quality-gate",
    "services/sentinel",
    "tests/ui-audit",
)

DEVSTACK_PROOF_SYNC_ROOT: Final[str] = "_external/devstack"
BASE_DEVSTACK_PROOF_SYNC_PATHS: Final[tuple[str, ...]] = (
    "configs/devstack-capability-lane-registry.json",
    "reports/master-atlas/latest.json",
)
DEVSTACK_SOURCE_PREFIX = "C:/athanor-devstack/"
DEVSTACK_PROOF_SOURCE_REGISTRIES: Final[tuple[Path, ...]] = (
    REPO_ROOT / "config" / "automation-backbone" / "artifact-provenance-ledger.json",
    REPO_ROOT / "config" / "automation-backbone" / "eval-run-ledger.json",
    REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json",
)
PROJECT_MATURITY_REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "project-maturity-registry.json"


def proof_workspace_sync_paths() -> tuple[str, ...]:
    collected: set[str] = set(PROOF_WORKSPACE_SYNC_PATHS)
    project_maturity = json.loads(PROJECT_MATURITY_REGISTRY_PATH.read_text(encoding="utf-8"))
    for project in project_maturity.get("projects", []):
        if not isinstance(project, dict):
            continue
        for field_name in ("workspace", "env_example"):
            relative = str(project.get(field_name) or "").strip()
            if relative and REPO_ROOT.joinpath(relative).exists():
                collected.add(relative)
        for relative_doc in project.get("docs", []) or []:
            relative = str(relative_doc or "").strip()
            if relative and REPO_ROOT.joinpath(relative).exists():
                collected.add(relative)
    return tuple(sorted(collected))


def _collect_prefixed_strings(value: object, prefix: str, sink: set[str]) -> None:
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized.lower().startswith(prefix.lower()):
            sink.add(normalized[len(prefix) :])
        return
    if isinstance(value, dict):
        for nested in value.values():
            _collect_prefixed_strings(nested, prefix, sink)
        return
    if isinstance(value, list):
        for nested in value:
            _collect_prefixed_strings(nested, prefix, sink)


def devstack_proof_sync_paths() -> tuple[str, ...]:
    collected: set[str] = set(BASE_DEVSTACK_PROOF_SYNC_PATHS)
    for path in DEVSTACK_PROOF_SOURCE_REGISTRIES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        _collect_prefixed_strings(payload, DEVSTACK_SOURCE_PREFIX, collected)
    if DEVSTACK_LOCAL_ROOT.exists():
        collected = {
            relative
            for relative in collected
            if DEVSTACK_LOCAL_ROOT.joinpath(relative).exists()
        }
    return tuple(sorted(collected))


def devstack_proof_root() -> str:
    return DEVSTACK_PROOF_SYNC_ROOT


def missing_paths(base: Path, paths: tuple[str, ...]) -> list[str]:
    return [relative for relative in paths if not base.joinpath(relative).exists()]


def _emit(paths: tuple[str, ...]) -> None:
    for relative in paths:
        print(relative)


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit proof workspace sync contract paths.")
    parser.add_argument(
        "command",
        choices=("repo-sync-paths", "devstack-sync-paths", "devstack-root"),
    )
    args = parser.parse_args()

    if args.command == "repo-sync-paths":
        _emit(proof_workspace_sync_paths())
        return 0
    if args.command == "devstack-sync-paths":
        _emit(devstack_proof_sync_paths())
        return 0
    print(devstack_proof_root())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
