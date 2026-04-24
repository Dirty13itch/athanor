from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

resolve_repo_root = repo_paths.resolve_repo_root
resolve_agents_project_root = repo_paths.resolve_agents_project_root
resolve_subscription_policy_path = repo_paths.resolve_subscription_policy_path


class RepoPathsContractTests(unittest.TestCase):
    def test_resolve_repo_root_prefers_workspace_when_anchor_is_site_packages(self) -> None:
        with TemporaryDirectory() as temp_dir:
            fake_module = (
                Path(temp_dir)
                / "usr"
                / "local"
                / "lib"
                / "python3.12"
                / "site-packages"
                / "athanor_agents"
                / "tasks.py"
            )
            fake_module.parent.mkdir(parents=True, exist_ok=True)
            fake_module.write_text("# test", encoding="utf-8")

            original_exists = Path.exists

            def fake_exists(path: Path) -> bool:
                if path.as_posix() in {
                    "/workspace/config/automation-backbone",
                    "/workspace/STATUS.md",
                }:
                    return True
                return original_exists(path)

            with patch("athanor_agents.repo_paths.Path.exists", fake_exists):
                self.assertEqual(Path("/workspace"), resolve_repo_root(fake_module))

    def test_resolve_subscription_policy_path_supports_workspace_agents_layout(self) -> None:
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            policy_path = repo_root / "agents" / "config" / "subscription-routing-policy.yaml"
            policy_path.parent.mkdir(parents=True, exist_ok=True)
            policy_path.write_text("providers: {}\n", encoding="utf-8")

            with patch.dict(os.environ, {"ATHANOR_REPO_ROOT": str(repo_root)}, clear=False):
                self.assertEqual(repo_root / "agents", resolve_agents_project_root())
                self.assertEqual(policy_path, resolve_subscription_policy_path())
