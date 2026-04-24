from __future__ import annotations

import importlib.util
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch


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


def test_build_surface_plan_returns_dashboard_command_center_bundle() -> None:
    module = _load_module(
        f"run_dashboard_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_dashboard_value_proof.py",
    )

    plan = module.build_surface_plan("dashboard_overview")

    assert plan["commands"] == [
        [
            "npx",
            "vitest",
            "run",
            "src/features/overview/command-center.test.tsx",
            "src/app/api/operator/summary/route.test.ts",
        ]
    ]
    assert plan["artifacts"] == ["projects/dashboard/src/features/overview/command-center.tsx"]


def test_build_surface_plan_returns_builder_operator_bundle() -> None:
    module = _load_module(
        f"run_dashboard_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_dashboard_value_proof.py",
    )

    plan = module.build_surface_plan("builder_operator_surface")

    assert plan["commands"] == [
        [
            "npx",
            "vitest",
            "run",
            "src/features/operator/operator-console.test.tsx",
            "src/app/api/operator/summary/route.test.ts",
        ]
    ]
    assert plan["artifacts"] == ["projects/dashboard/src/features/operator/operator-console.tsx"]


def test_ensure_dashboard_runtime_bootstraps_dependencies_when_missing() -> None:
    module = _load_module(
        f"run_dashboard_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_dashboard_value_proof.py",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        dashboard_root = Path(temp_dir)
        (dashboard_root / "package-lock.json").write_text("{}", encoding="utf-8")

        with (
            patch.object(module.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            patch.object(module.subprocess, "run") as run_mock,
        ):
            module.ensure_dashboard_runtime(dashboard_root)

    run_mock.assert_called_once()
    assert run_mock.call_args.args[0] == ["npm", "ci", "--no-fund", "--no-audit"]
    assert run_mock.call_args.kwargs["cwd"] == str(dashboard_root)
    assert run_mock.call_args.kwargs["check"] is True


def test_ensure_dashboard_runtime_skips_bootstrap_when_vitest_exists() -> None:
    module = _load_module(
        f"run_dashboard_value_proof_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_dashboard_value_proof.py",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        dashboard_root = Path(temp_dir)
        (dashboard_root / "package-lock.json").write_text("{}", encoding="utf-8")
        vitest_path = dashboard_root / "node_modules" / ".bin" / "vitest"
        vitest_path.parent.mkdir(parents=True, exist_ok=True)
        vitest_path.write_text("", encoding="utf-8")

        with (
            patch.object(module.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"),
            patch.object(module.subprocess, "run") as run_mock,
        ):
            module.ensure_dashboard_runtime(dashboard_root)

    run_mock.assert_not_called()
