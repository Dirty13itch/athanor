#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTACK_ROOT = REPO_ROOT.parent / "athanor-devstack"
GENERATOR_PATH = DEVSTACK_ROOT / "scripts" / "generate_devstack_reference_surfaces.py"


def main() -> int:
    if not GENERATOR_PATH.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "detail": f"Missing generator at {GENERATOR_PATH}",
                },
                indent=2,
            )
        )
        return 1

    completed = subprocess.run(
        [sys.executable, str(GENERATOR_PATH)],
        cwd=DEVSTACK_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
