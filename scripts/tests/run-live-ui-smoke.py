#!/usr/bin/env python3
"""Run the live smoke suite across dashboard and shipped tenants."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(label: str, script: str, extra_args: list[str]) -> dict[str, object]:
    command = [sys.executable, str(ROOT / "scripts" / "tests" / script), *extra_args]
    completed = subprocess.run(command, capture_output=True, text=True)
    payload = {
        "label": label,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-base-url")
    parser.add_argument("--eoq-base-url")
    parser.add_argument("--ulrich-base-url")
    parser.add_argument("--exercise-eoq-generation", action="store_true")
    parser.add_argument("--allow-ulrich-mutations", action="store_true")
    args = parser.parse_args()

    jobs = [
        ("dashboard", "live-dashboard-smoke.py", ["--base-url", args.dashboard_base_url] if args.dashboard_base_url else []),
        ("eoq", "live-eoq-smoke.py", (["--base-url", args.eoq_base_url] if args.eoq_base_url else []) + (["--exercise-generation"] if args.exercise_eoq_generation else [])),
        ("ulrich", "live-ulrich-smoke.py", (["--base-url", args.ulrich_base_url] if args.ulrich_base_url else []) + (["--allow-mutations"] if args.allow_ulrich_mutations else [])),
    ]

    results = [run(label, script, extra_args) for label, script, extra_args in jobs]
    failures = [result["label"] for result in results if result["returncode"] != 0]
    print(json.dumps({"results": results, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
