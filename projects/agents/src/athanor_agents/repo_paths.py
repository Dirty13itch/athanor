from __future__ import annotations

import os
from pathlib import Path


def _looks_like_repo_root(candidate: Path) -> bool:
    return candidate.joinpath("config", "automation-backbone").exists()


def resolve_repo_root(anchor_file: str | Path | None = None) -> Path:
    env_root = str(
        os.getenv("ATHANOR_REPO_ROOT")
        or os.getenv("ATHANOR_WORKSPACE_ROOT")
        or ""
    ).strip()
    if env_root:
        candidate = Path(env_root)
        if candidate.exists():
            return candidate

    workspace_root = Path("/workspace")
    if _looks_like_repo_root(workspace_root):
        return workspace_root

    anchor = Path(anchor_file) if anchor_file is not None else Path(__file__)
    preferred: Path | None = None
    for base in anchor.resolve().parents:
        if _looks_like_repo_root(base):
            if base.joinpath("STATUS.md").exists():
                return base
            preferred = preferred or base
    if preferred is not None:
        return preferred

    cwd = Path.cwd()
    if _looks_like_repo_root(cwd):
        return cwd

    return workspace_root if workspace_root.exists() else cwd


def resolve_agents_project_root(anchor_file: str | Path | None = None) -> Path:
    repo_root = resolve_repo_root(anchor_file)
    candidates = [
        repo_root / "projects" / "agents",
        repo_root / "agents",
    ]
    for candidate in candidates:
        if candidate.joinpath("config", "subscription-routing-policy.yaml").exists():
            return candidate
        if candidate.joinpath("src", "athanor_agents").exists():
            return candidate
    return candidates[0]


def resolve_subscription_policy_path(anchor_file: str | Path | None = None) -> Path:
    env_path = str(os.getenv("ATHANOR_SUBSCRIPTION_POLICY_PATH") or "").strip()
    if env_path:
        return Path(env_path)

    repo_root = resolve_repo_root(anchor_file)
    candidates = [
        resolve_agents_project_root(anchor_file) / "config" / "subscription-routing-policy.yaml",
        repo_root / "config" / "subscription-routing-policy.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
