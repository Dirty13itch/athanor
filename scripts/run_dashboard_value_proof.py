#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_ROOT = REPO_ROOT / "projects" / "dashboard"

SURFACE_PLANS = {
    "dashboard_overview": {
        "label": "dashboard_overview",
        "commands": [
            [
                "npx",
                "vitest",
                "run",
                "src/features/overview/command-center.test.tsx",
                "src/app/api/operator/summary/route.test.ts",
            ],
        ],
        "artifacts": [
            "projects/dashboard/src/features/overview/command-center.tsx",
        ],
    },
    "builder_operator_surface": {
        "label": "builder_operator_surface",
        "commands": [
            [
                "npx",
                "vitest",
                "run",
                "src/features/operator/operator-console.test.tsx",
                "src/app/api/operator/summary/route.test.ts",
            ],
        ],
        "artifacts": [
            "projects/dashboard/src/features/operator/operator-console.tsx",
        ],
    },
}


def build_surface_plan(surface: str) -> dict[str, object]:
    plan = SURFACE_PLANS.get(str(surface or "").strip())
    if plan is None:
        raise ValueError(f"Unsupported dashboard proof surface: {surface}")
    return plan


def _dashboard_dependencies_ready(root: Path = DASHBOARD_ROOT) -> bool:
    return (root / "node_modules" / ".bin" / "vitest").exists()


def ensure_dashboard_runtime(root: Path = DASHBOARD_ROOT) -> None:
    if shutil.which("node") is None or shutil.which("npm") is None:
        raise RuntimeError("Dashboard value proof requires node and npm in the runtime.")
    if not (root / "package-lock.json").exists():
        raise RuntimeError(f"Dashboard value proof requires {root / 'package-lock.json'}")
    if _dashboard_dependencies_ready(root):
        return
    subprocess.run(
        ["npm", "ci", "--no-fund", "--no-audit"],
        cwd=str(root),
        env={**os.environ, "CI": "1"},
        check=True,
    )


def run_surface(surface: str) -> int:
    plan = build_surface_plan(surface)
    ensure_dashboard_runtime(DASHBOARD_ROOT)
    for command in plan["commands"]:
        completed = subprocess.run(
            command,
            cwd=str(DASHBOARD_ROOT),
            check=False,
        )
        if completed.returncode != 0:
            return completed.returncode
    print(f"{plan['label']} proof passed")
    for artifact in plan["artifacts"]:
        print(artifact)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed proof bundle for dashboard or builder product-value surfaces.")
    parser.add_argument(
        "--surface",
        required=True,
        choices=sorted(SURFACE_PLANS),
        help="Dashboard surface proof bundle to execute.",
    )
    args = parser.parse_args()
    return run_surface(args.surface)


if __name__ == "__main__":
    raise SystemExit(main())
