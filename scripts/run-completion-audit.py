#!/usr/bin/env python3
"""Run the Athanor completion-audit program and build a readiness report."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from completion_audit_common import (
    COMPLETION_AUDIT_DIR,
    REPORTS_DIR,
    safe_json_load,
    write_json,
)


ROOT = Path(__file__).resolve().parent.parent
LATEST_DIR = REPORTS_DIR / "latest"


def npm_command() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


def repo_root_candidates() -> list[Path]:
    candidates = [ROOT]
    if ROOT.parent.name == ".worktrees":
        for sibling in sorted(ROOT.parent.iterdir()):
            if sibling == ROOT or not sibling.is_dir():
                continue
            candidates.append(sibling)
        candidates.append(ROOT.parent.parent)

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def agents_python_command() -> str:
    candidates: list[Path] = []
    for repo_root in repo_root_candidates():
        candidates.extend(
            [
                repo_root / "projects" / "agents" / ".venv" / "Scripts" / "python.exe",
                repo_root / "projects" / "agents" / ".venv" / "Scripts" / "python",
                repo_root / "projects" / "agents" / ".venv" / "bin" / "python",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def dashboard_install_valid(node_modules: Path) -> bool:
    return (
        (node_modules / "next" / "package.json").exists()
        and (node_modules / "@testing-library" / "jest-dom" / "vitest.js").exists()
    )


def dashboard_install_is_reparse(node_modules: Path) -> bool:
    try:
        return bool(getattr(node_modules.lstat(), "st_reparse_tag", 0))
    except OSError:
        return False


def dashboard_dependency_env() -> dict[str, str]:
    for repo_root in repo_root_candidates():
        node_modules = repo_root / "projects" / "dashboard" / "node_modules"
        bin_dir = node_modules / ".bin"
        if not dashboard_install_valid(node_modules) or not bin_dir.exists():
            continue
        path_entries = [str(bin_dir)]
        existing_path = os.environ.get("PATH", "")
        if existing_path:
            path_entries.append(existing_path)
        node_path_entries = [str(node_modules)]
        existing_node_path = os.environ.get("NODE_PATH", "")
        if existing_node_path:
            node_path_entries.append(existing_node_path)
        return {
            "PATH": os.pathsep.join(path_entries),
            "NODE_PATH": os.pathsep.join(node_path_entries),
        }
    return {}


def ensure_dashboard_node_modules() -> None:
    dashboard_root = ROOT / "projects" / "dashboard"
    target = dashboard_root / "node_modules"
    if dashboard_install_valid(target) and not dashboard_install_is_reparse(target):
        return
    if target.exists() or dashboard_install_is_reparse(target):
        if dashboard_install_is_reparse(target) and os.name == "nt":
            subprocess.run(["cmd", "/c", "rmdir", str(target)], check=True, capture_output=True, text=True)
        elif target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target, ignore_errors=True)

    subprocess.run(
        [npm_command(), "ci", "--no-audit", "--no-fund"],
        cwd=dashboard_root,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "CI": "1"},
    )


def find_free_local_port() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


def run_job(
    label: str,
    command: list[str],
    cwd: Path | None = None,
    *,
    extra_env: dict[str, str] | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, **(extra_env or {})},
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "label": label,
            "cwd": str(cwd or ROOT),
            "command": command,
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
        }
    return {
        "label": label,
        "cwd": str(cwd or ROOT),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
    }


def build_backlog(
    routes: list[dict],
    support_surfaces: list[dict],
    apis: list[dict],
    mounts: list[dict],
    runtime_subsystems: list[dict],
    envs: list[dict],
    deployments: list[dict],
    jobs: list[dict],
) -> list[dict]:
    backlog: list[dict] = []

    failed_jobs = [job["label"] for job in jobs if job["returncode"] != 0]
    if failed_jobs:
        backlog.append(
            {
                "batch": 1,
                "title": "Failed audit jobs",
                "layer": "audit-runner",
                "evidence": failed_jobs,
                "acceptanceCriteria": "All required fixture and live audit jobs return exit code 0.",
                "safeForAutonomousExecution": True,
                "needsUserApproval": False,
            }
        )

    broken_envs = [item["name"] for item in envs if item["completionStatus"] == "broken"]
    broken_deployments = [item["serviceId"] for item in deployments if item["completionStatus"] == "broken"]
    if broken_envs or broken_deployments:
        backlog.append(
            {
                "batch": 2,
                "title": "Broken runtime and deployment contracts",
                "layer": "deployment",
                "evidence": broken_envs + broken_deployments,
                "acceptanceCriteria": "Runtime-critical envs have repo-side export coverage and broken live services are reachable again.",
                "safeForAutonomousExecution": True,
                "needsUserApproval": False,
            }
        )

    partial_routes = [
        route["routePath"]
        for route in routes
        if route["completionStatus"] == "live_partial" and route["navigation"]["inPrimaryNavigation"]
    ]
    if partial_routes:
        backlog.append(
            {
                "batch": 3,
                "title": "Primary routes still only partially audited",
                "layer": "ui",
                "evidence": partial_routes,
                "acceptanceCriteria": "Primary routes have fixture and live completion evidence with no unresolved gaps.",
                "safeForAutonomousExecution": True,
                "needsUserApproval": False,
            }
        )

    uncovered_support = [surface["sourceFiles"]["primary"] for surface in support_surfaces if surface["completionStatus"] == "live_partial"]
    if uncovered_support:
        backlog.append(
            {
                "batch": 4,
                "title": "Support surfaces lack direct audit coverage",
                "layer": "ui-support",
                "evidence": uncovered_support,
                "acceptanceCriteria": "Loading, error, not-found, and related support surfaces are exercised deterministically.",
                "safeForAutonomousExecution": True,
                "needsUserApproval": False,
            }
        )

    orphan_apis = [api["apiPath"] for api in apis if api["consumerStatus"] == "orphan-candidate"]
    if orphan_apis:
        backlog.append(
            {
                "batch": 5,
                "title": "API routes without clear consumers",
                "layer": "api",
                "evidence": orphan_apis,
                "acceptanceCriteria": "Each API route is mapped to a UI, runtime, or explicit support-only purpose.",
                "safeForAutonomousExecution": True,
                "needsUserApproval": False,
            }
        )

    dormant_ui = [mount["filePath"] for mount in mounts if mount["mountStatus"] in {"partial", "unmounted"}]
    dormant_runtime = [item["id"] for item in runtime_subsystems if item["completionStatus"] == "implemented_not_live"]
    if dormant_ui or dormant_runtime:
        backlog.append(
            {
                "batch": 6,
                "title": "Dormant UI and runtime surfaces need promotion or deferral decisions",
                "layer": "ui-runtime",
                "evidence": dormant_ui[:20] + dormant_runtime,
                "acceptanceCriteria": "Implemented-but-unsurfaced features are either mounted intentionally or left explicitly deferred.",
                "safeForAutonomousExecution": False,
                "needsUserApproval": True,
            }
        )

    return backlog


def build_release_report(jobs: list[dict]) -> dict:
    routes = safe_json_load(COMPLETION_AUDIT_DIR / "dashboard-route-census.json", [])
    support_surfaces = safe_json_load(COMPLETION_AUDIT_DIR / "dashboard-support-surface-census.json", [])
    apis = safe_json_load(COMPLETION_AUDIT_DIR / "dashboard-api-census.json", [])
    mounts = safe_json_load(COMPLETION_AUDIT_DIR / "dashboard-mount-graph.json", [])
    runtime_subsystems = safe_json_load(COMPLETION_AUDIT_DIR / "runtime-subsystem-census.json", [])
    envs = safe_json_load(COMPLETION_AUDIT_DIR / "env-contract-census.json", [])
    deployments = safe_json_load(COMPLETION_AUDIT_DIR / "deployment-ownership-matrix.json", [])

    blockers = []
    warnings = []

    failed_jobs = [job["label"] for job in jobs if job["returncode"] != 0]
    blockers.extend(f"job:{label}" for label in failed_jobs)

    blockers.extend(f"env:{item['name']}" for item in envs if item["completionStatus"] == "broken")
    blockers.extend(f"deployment:{item['serviceId']}" for item in deployments if item["completionStatus"] == "broken")

    warnings.extend(
        f"support-surface:{surface['sourceFiles']['primary']}"
        for surface in support_surfaces
        if surface["completionStatus"] == "live_partial"
    )
    warnings.extend(
        f"api:{api['apiPath']}"
        for api in apis
        if api["consumerStatus"] == "orphan-candidate"
    )
    warnings.extend(
        f"mount:{mount['filePath']}"
        for mount in mounts
        if mount["mountStatus"] in {"partial", "unmounted"}
    )
    warnings.extend(
        f"runtime:{item['id']}"
        for item in runtime_subsystems
        if item["completionStatus"] == "implemented_not_live"
    )
    warnings.extend(
        f"deployment:{item['serviceId']}"
        for item in deployments
        if item["completionStatus"] == "live_partial"
    )

    backlog = build_backlog(
        routes,
        support_surfaces,
        apis,
        mounts,
        runtime_subsystems,
        envs,
        deployments,
        jobs,
    )

    summary = {
        "routeCount": len(routes),
        "supportSurfaceCount": len(support_surfaces),
        "apiCount": len(apis),
        "mountGraphCount": len(mounts),
        "runtimeSubsystemCount": len(runtime_subsystems),
        "envCount": len(envs),
        "deploymentCount": len(deployments),
        "failedJobCount": len(failed_jobs),
    }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blockers else "ready",
        "summary": summary,
        "blockers": sorted(blockers),
        "warnings": sorted(warnings),
        "jobs": jobs,
        "inventories": {
            "routes": str(COMPLETION_AUDIT_DIR / "dashboard-route-census.json"),
            "supportSurfaces": str(COMPLETION_AUDIT_DIR / "dashboard-support-surface-census.json"),
            "apis": str(COMPLETION_AUDIT_DIR / "dashboard-api-census.json"),
            "mountGraph": str(COMPLETION_AUDIT_DIR / "dashboard-mount-graph.json"),
            "runtimeSubsystems": str(COMPLETION_AUDIT_DIR / "runtime-subsystem-census.json"),
            "envContracts": str(COMPLETION_AUDIT_DIR / "env-contract-census.json"),
            "deploymentOwnership": str(COMPLETION_AUDIT_DIR / "deployment-ownership-matrix.json"),
        },
        "remediationBacklog": backlog,
    }


def write_markdown_summary(path: Path, report: dict) -> None:
    lines = [
        "# Completion Audit Summary",
        "",
        f"- Generated: `{report['generatedAt']}`",
        f"- Status: `{report['status']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blockers", ""])
    if report["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in report["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if report["warnings"]:
        lines.extend(f"- `{warning}`" for warning in report["warnings"][:50])
    else:
        lines.append("- none")
    lines.extend(["", "## Remediation Backlog", ""])
    for item in report["remediationBacklog"]:
        lines.append(f"- Batch {item['batch']}: {item['title']}")
        lines.append(f"  Evidence: {', '.join(item['evidence'][:8]) if item['evidence'] else 'none'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-live", action="store_true")
    args = parser.parse_args()

    npm = npm_command()
    agents_python = agents_python_command()
    ensure_dashboard_node_modules()
    dashboard_env = dashboard_dependency_env()
    dashboard_e2e_port = find_free_local_port()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPORTS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    LATEST_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [
        run_job("census-routes", [sys.executable, str(ROOT / "scripts" / "census-dashboard-routes.py")], ROOT),
        run_job("census-api", [sys.executable, str(ROOT / "scripts" / "census-dashboard-api.py")], ROOT),
        run_job("census-components", [sys.executable, str(ROOT / "scripts" / "census-dashboard-components.py")], ROOT),
        run_job("find-mounted-ui", [sys.executable, str(ROOT / "scripts" / "find-mounted-ui.py")], ROOT),
        run_job("map-agent-endpoints", [sys.executable, str(ROOT / "scripts" / "map-agent-endpoints.py")], ROOT),
        run_job("census-env-contracts", [sys.executable, str(ROOT / "scripts" / "census-env-contracts.py")], ROOT),
        run_job(
            "provider-usage-evidence",
            [sys.executable, str(ROOT / "scripts" / "probe_provider_usage_evidence.py"), "--all-vault-proxy"],
            ROOT,
            timeout_seconds=300,
        ),
        run_job(
            "dashboard:test",
            [npm, "run", "test"],
            ROOT / "projects" / "dashboard",
            extra_env=dashboard_env,
            timeout_seconds=300,
        ),
        run_job(
            "dashboard:e2e:audit",
            [npm, "run", "test:e2e:audit"],
            ROOT / "projects" / "dashboard",
            extra_env={**dashboard_env, "PLAYWRIGHT_PORT": dashboard_e2e_port},
            timeout_seconds=600,
        ),
        run_job("agents:tests", [agents_python, "-m", "pytest", "tests", "-q"], ROOT / "projects" / "agents", timeout_seconds=300),
        run_job("deployment-ownership", [sys.executable, str(ROOT / "scripts" / "audit-deployment-ownership.py")], ROOT, timeout_seconds=300),
    ]

    if not args.skip_live:
        jobs.extend(
            [
                run_job("live-dashboard-smoke", [sys.executable, str(ROOT / "scripts" / "tests" / "live-dashboard-smoke.py")], ROOT, timeout_seconds=300),
                run_job("agent-runtime-probe", [sys.executable, str(ROOT / "scripts" / "probe-agent-runtime.py"), "--output", str(run_dir / "agent-runtime-probe.json")], ROOT, timeout_seconds=300),
                run_job("endpoint-harness", [sys.executable, str(ROOT / "tests" / "harness.py"), "--json"], ROOT, timeout_seconds=300),
            ]
        )

    jobs_path = run_dir / "jobs.json"
    write_json(jobs_path, jobs)
    write_json(LATEST_DIR / "jobs.json", jobs)

    report = build_release_report(jobs)
    write_json(run_dir / "release-readiness.json", report)
    write_json(LATEST_DIR / "release-readiness.json", report)
    write_json(run_dir / "remediation-backlog.json", report["remediationBacklog"])
    write_json(LATEST_DIR / "remediation-backlog.json", report["remediationBacklog"])
    write_markdown_summary(run_dir / "summary.md", report)
    write_markdown_summary(LATEST_DIR / "summary.md", report)

    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
