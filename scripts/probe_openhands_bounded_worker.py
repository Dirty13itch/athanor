#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "PROMPTFOO_OPENHANDS_CMD",
    "PROMPTFOO_OPENHANDS_ARGS_JSON",
]


def main() -> int:
    uv = shutil.which("uv")
    if not uv:
        print("Missing UV")
        return 1

    probe_cmd = [
        uv,
        "run",
        "--with",
        "openhands-ai",
        "python",
        "-m",
        "openhands.agent_server.__main__",
        "--help",
    ]
    completed = subprocess.run(
        probe_cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        env={**os.environ, "OPENHANDS_SUPPRESS_BANNER": "1"},
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "substrate probe failed").strip()
        print(f"Substrate probe failed: {detail}")
        return 1

    for env_name in REQUIRED_ENV_VARS:
        if not os.environ.get(env_name):
            print(f"Missing {env_name}")
            return 1

    summary = {
        "status": "ready",
        "uv": uv,
        "probe_command": probe_cmd,
    }
    print("READY")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
