#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
DEFAULT_RUNTIME_BUDGET_SECONDS = 45 * 60
DEFAULT_POLL_INTERVAL_SECONDS = 3 * 60
POST_FINISH_REFRESH_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("scripts/write_runtime_parity.py", "--json"),
    ("scripts/write_result_evidence_ledger.py", "--json"),
    ("scripts/write_stable_operating_day.py", "--json"),
    ("scripts/run_continuity_control_pass.py", "status", "--json"),
    ("scripts/write_blocker_map.py", "--json"),
    ("scripts/write_blocker_execution_plan.py", "--json"),
    ("scripts/write_continuity_supervisor_health.py", "--json"),
    ("scripts/write_project_output_readiness.py", "--json"),
    ("scripts/write_project_output_candidates.py", "--json"),
    ("scripts/materialize_project_output_acceptance.py", "--all-pending", "--json"),
    ("scripts/write_project_output_candidates.py", "--json"),
    ("scripts/write_project_output_proof.py", "--json"),
    ("scripts/write_autonomy_failure_ledger.py", "--json"),
    ("scripts/write_controller_of_controllers.py", "--json"),
    ("scripts/write_steady_state_status.py", "--json"),
    ("scripts/write_operator_mobile_summary.py", "--json"),
    ("scripts/write_command_center_final_form_status.py", "--json"),
    ("scripts/write_system_capability_scorecard.py", "--json"),
    ("scripts/generate_truth_inventory_reports.py",),
    ("scripts/triage_publication_tranche.py", "--write", "docs/operations/PUBLICATION-TRIAGE-REPORT.md"),
    ("scripts/generate_publication_deferred_family_queue.py",),
    ("scripts/generate_ecosystem_master_plan.py",),
    ("scripts/generate_full_system_audit.py", "--skip-checks"),
    ("scripts/validate_platform_contract.py",),
    ("scripts/run_contract_healer.py",),
    ("scripts/write_blocker_map.py", "--json"),
    ("scripts/write_blocker_execution_plan.py", "--json"),
    ("scripts/write_continuity_supervisor_health.py", "--json"),
    ("scripts/write_autonomy_failure_ledger.py", "--json"),
    ("scripts/write_controller_of_controllers.py", "--json"),
    ("scripts/write_steady_state_status.py", "--json"),
    ("scripts/write_operator_mobile_summary.py", "--json"),
    ("scripts/write_command_center_final_form_status.py", "--json"),
    ("scripts/write_system_capability_scorecard.py", "--json"),
)
STATUS_REFRESH_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("scripts/run_continuity_control_pass.py", "status", "--json"),
    ("scripts/write_blocker_map.py", "--json"),
    ("scripts/write_blocker_execution_plan.py", "--json"),
    ("scripts/write_continuity_supervisor_health.py", "--json"),
    ("scripts/write_project_output_readiness.py", "--json"),
    ("scripts/write_project_output_candidates.py", "--json"),
    ("scripts/materialize_project_output_acceptance.py", "--all-pending", "--json"),
    ("scripts/write_project_output_candidates.py", "--json"),
    ("scripts/write_project_output_proof.py", "--json"),
    ("scripts/write_autonomy_failure_ledger.py", "--json"),
    ("scripts/write_controller_of_controllers.py", "--json"),
    ("scripts/write_steady_state_status.py", "--json"),
    ("scripts/write_operator_mobile_summary.py", "--json"),
    ("scripts/write_command_center_final_form_status.py", "--json"),
    ("scripts/write_system_capability_scorecard.py", "--json"),
)

RUNTIME_PROOF_CONTEXT_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("scripts/validate_platform_contract.py",),
    ("scripts/run_contract_healer.py",),
)


def _command_env(args: tuple[str, ...]) -> dict[str, str] | None:
    if args in RUNTIME_PROOF_CONTEXT_COMMANDS:
        env = os.environ.copy()
        env["ATHANOR_RUNTIME_PROOF_CONTEXT"] = "1"
        return env
    return None


def _run_json_command(*args: str, timeout_seconds: int | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        [PYTHON, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_command_env(tuple(args)),
        timeout=timeout_seconds or DEFAULT_RUNTIME_BUDGET_SECONDS,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"{' '.join(args)} failed")
    stdout = proc.stdout or ""
    if not stdout.strip():
        return {"success": True}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "success": True,
            "stdout": stdout,
            "stderr": proc.stderr,
        }
    if isinstance(payload, dict):
        return payload
    return {
        "success": True,
        "result": payload,
    }


def _run_refresh_commands(
    *,
    commands: tuple[tuple[str, ...], ...],
    command_runner: Callable[..., dict[str, Any]],
) -> list[dict[str, Any]]:
    refresh_results: list[dict[str, Any]] = []
    for command in commands:
        try:
            refresh_results.append(command_runner(*command))
        except Exception as exc:
            refresh_results.append(
                {
                    "success": False,
                    "command": list(command),
                    "error": str(exc),
                }
            )
    return refresh_results


def run_cycle(
    *,
    command_runner: Callable[..., dict[str, Any]] = _run_json_command,
) -> dict[str, Any]:
    begin = command_runner("scripts/run_continuity_control_pass.py", "begin", "--json")
    controller_status = str(begin.get("controller_status") or "")
    if controller_status != "running":
        status_refresh = _run_refresh_commands(
            commands=STATUS_REFRESH_COMMANDS,
            command_runner=command_runner,
        )
        return {
            "status": "blocked" if controller_status == "blocked" else "skipped",
            "reason": begin.get("last_skip_reason"),
            "pass_id": begin.get("active_pass_id"),
            "status_refresh": status_refresh,
        }

    pass_id = str(begin.get("active_pass_id") or "")
    fixed_point: dict[str, Any] | None = None
    finish: dict[str, Any] | None = None
    post_finish_refresh: list[dict[str, Any]] = []
    status = "failed"
    error: str | None = None
    finish_error: str | None = None

    try:
        fixed_point = command_runner("scripts/run_steady_state_control_plane.py", "--skip-restart-brief", "--json")
        status = "completed" if bool(fixed_point.get("success")) else "failed"
    except Exception as exc:
        error = str(exc)
    finally:
        try:
            finish = command_runner(
                "scripts/run_continuity_control_pass.py",
                "finish",
                "--pass-id",
                pass_id,
                "--json",
            )
        except Exception as exc:
            finish_error = str(exc)
            status = "failed"

    if finish_error is None:
        post_finish_refresh = _run_refresh_commands(
            commands=POST_FINISH_REFRESH_COMMANDS,
            command_runner=command_runner,
        )
        if any(not refresh.get("success", True) for refresh in post_finish_refresh):
            status = "failed"

    outcome = {
        "status": status,
        "pass_id": pass_id,
        "fixed_point": fixed_point,
        "finish": finish,
        "post_finish_refresh": post_finish_refresh,
    }
    if error is not None:
        outcome["error"] = error
    if finish_error is not None:
        outcome["finish_error"] = finish_error
    return outcome


def run_supervisor(
    *,
    loop: bool,
    runtime_budget_seconds: int,
    poll_interval_seconds: int,
    cycle_runner: Callable[[], dict[str, Any]] | None = None,
    command_runner: Callable[..., dict[str, Any]] = _run_json_command,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    deadline = monotonic() + max(runtime_budget_seconds, 1)
    history: list[dict[str, Any]] = []
    while monotonic() < deadline:
        if cycle_runner is None:
            def _budgeted_command_runner(*args: str) -> dict[str, Any]:
                remaining = max(int(deadline - monotonic()), 1)
                return command_runner(*args, timeout_seconds=remaining)

            outcome = run_cycle(command_runner=_budgeted_command_runner)
        else:
            outcome = cycle_runner()
        history.append(outcome)
        if not loop:
            break
        if outcome["status"] in {"completed", "failed", "blocked"}:
            break
        if outcome["status"] == "skipped" and outcome.get("reason") in {"recent_pass_no_new_evidence", "backoff_active"}:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleeper(min(poll_interval_seconds, max(int(remaining), 1)))
            continue
        break

    return {
        "success": bool(history and history[-1]["status"] == "completed"),
        "run_count": len(history),
        "history": history,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the repo-owned continuity supervisor loop.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument(
        "--runtime-budget-seconds",
        type=int,
        default=DEFAULT_RUNTIME_BUDGET_SECONDS,
        help="Maximum runtime budget for this supervisor invocation.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Polling interval between skipped passes.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep polling for additional inner cycles instead of exiting after one bounded wake.",
    )
    args = parser.parse_args()

    payload = run_supervisor(
        loop=args.loop,
        runtime_budget_seconds=args.runtime_budget_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"success={'true' if payload['success'] else 'false'}")
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
