#!/usr/bin/env python3
"""Run the Athanor UI audit loop across dashboard and tenants.

Evidence producer only; generated JSON from this script is proof surfaces for UI audit coverage, not runtime or queue authority.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "tests" / "ui-audit"
LAST_RUN_PATH = AUDIT_DIR / "last-run.json"
RETRYABLE_LABELS = {
    "dashboard:e2e": 1,
    "live-smoke": 1,
    "dashboard:e2e:audit": 1,
    "dashboard:live-smoke": 1,
}


def npm_command() -> str:
    if os.name != "nt":
        return shutil.which("npm") or shutil.which("npm.cmd") or "npm"
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


def npx_command() -> str:
    if os.name != "nt":
        return shutil.which("npx") or shutil.which("npx.cmd") or "npx"
    return shutil.which("npx.cmd") or shutil.which("npx") or "npx"


def run_command(label: str, command: list[str], cwd: Path | None = None) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "label": label,
        "cwd": str(cwd) if cwd else str(ROOT),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_job(label: str, command: list[str], cwd: Path | None = None) -> dict[str, object]:
    max_attempts = 1 + RETRYABLE_LABELS.get(label, 0)
    result: dict[str, object] | None = None
    for attempt in range(1, max_attempts + 1):
        result = run_command(label, command, cwd)
        result["attempt"] = attempt
        result["maxAttempts"] = max_attempts
        if result["returncode"] == 0:
            return result
    assert result is not None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--live-only", action="store_true")
    parser.add_argument("--dashboard-final-form", action="store_true")
    parser.add_argument("--dashboard-base-url")
    args = parser.parse_args()

    npm = npm_command()
    npx = npx_command()
    jobs: list[tuple[str, list[str], Path | None]] = []

    if args.dashboard_final_form:
        jobs.extend(
            [
                ("generate-registry", [sys.executable, str(ROOT / "scripts" / "tests" / "generate-ui-surface-registry.py")], ROOT),
                ("check-coverage", [sys.executable, str(ROOT / "scripts" / "tests" / "check-ui-coverage.py")], ROOT),
                ("dashboard:typecheck", [npm, "run", "typecheck"], ROOT / "projects" / "dashboard"),
                (
                    "dashboard:command-center-focused",
                    [
                        npm,
                        "test",
                        "--",
                        "src/app/api/projects/factory/route.test.ts",
                        "src/app/api/operator/mobile-summary/route.test.ts",
                        "src/app/api/operator/summary/route.test.ts",
                        "src/features/projects/projects-console.test.tsx",
                        "src/features/operator/operator-console.test.tsx",
                        "src/features/overview/command-center.test.tsx",
                    ],
                    ROOT / "projects" / "dashboard",
                ),
            ]
        )
        if not args.skip_live:
            live_command = [sys.executable, str(ROOT / "scripts" / "tests" / "live-dashboard-smoke.py")]
            if args.dashboard_base_url:
                live_command.extend(["--base-url", args.dashboard_base_url])
            dashboard_live_base_url = args.dashboard_base_url or "https://athanor.local/"
            if dashboard_live_base_url.startswith("https://"):
                live_command.append("--insecure")
            live_command.extend(["--skip-chat", "--scope", "command-center-final-form"])
            jobs.append(("dashboard:live-smoke", live_command, ROOT))
    else:
        jobs.extend(
            [
                ("generate-registry", [sys.executable, str(ROOT / "scripts" / "tests" / "generate-ui-surface-registry.py")], ROOT),
                ("check-coverage", [sys.executable, str(ROOT / "scripts" / "tests" / "check-ui-coverage.py")], ROOT),
            ]
        )

    if not args.live_only and not args.dashboard_final_form:
        jobs.extend(
            [
                ("dashboard:lint", [npm, "run", "lint"], ROOT / "projects" / "dashboard"),
                ("dashboard:test", [npm, "run", "test"], ROOT / "projects" / "dashboard"),
                ("dashboard:build", [npm, "run", "build"], ROOT / "projects" / "dashboard"),
                ("dashboard:e2e", [npm, "run", "test:e2e"], ROOT / "projects" / "dashboard"),
                ("dashboard:storybook", [npm, "run", "storybook:build"], ROOT / "projects" / "dashboard"),
                ("dashboard:lighthouse", [npm, "run", "lighthouse"], ROOT / "projects" / "dashboard"),
                ("eoq:lint", [npm, "run", "lint"], ROOT / "projects" / "eoq"),
                ("eoq:build", [npm, "run", "build"], ROOT / "projects" / "eoq"),
                ("eoq:e2e", [npm, "run", "test:e2e"], ROOT / "projects" / "eoq"),
            ]
        )

    if not args.skip_live and not args.dashboard_final_form:
        jobs.append(("live-smoke", [sys.executable, str(ROOT / "scripts" / "tests" / "run-live-ui-smoke.py")], ROOT))

    results = [run_job(label, command, cwd) for label, command, cwd in jobs]
    failures = [result["label"] for result in results if result["returncode"] != 0]

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "failures": failures,
        "results": results,
    }
    LAST_RUN_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
