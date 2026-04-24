#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
DEFAULT_COMMAND_TIMEOUT_SECONDS = 120
COMMAND_TIMEOUT_OVERRIDES: dict[tuple[str, ...], int] = {
    ('scripts/collect_truth_inventory.py',): 180,
    ('scripts/run_ralph_loop_pass.py', '--skip-refresh'): 300,
    ('scripts/validate_platform_contract.py',): 90,
}

RUNTIME_PROOF_CONTEXT_COMMANDS: tuple[tuple[str, ...], ...] = (
    ('scripts/validate_platform_contract.py',),
    ('scripts/run_contract_healer.py',),
)


def build_commands(include_restart_brief: bool = True) -> List[List[str]]:
    commands: List[List[str]] = [
        [PYTHON, 'scripts/generate_documentation_index.py'],
        [PYTHON, 'scripts/collect_capacity_telemetry.py'],
        [PYTHON, 'scripts/write_quota_truth_snapshot.py'],
        [PYTHON, 'scripts/run_ralph_loop_pass.py', '--skip-refresh'],
        [PYTHON, 'scripts/collect_truth_inventory.py'],
        [PYTHON, 'scripts/generate_truth_inventory_reports.py'],
        [PYTHON, 'scripts/write_next_rotation_preflight.py', '--json'],
        [PYTHON, 'scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        [PYTHON, 'scripts/generate_publication_deferred_family_queue.py'],
        [PYTHON, 'scripts/write_finish_scoreboard.py', '--json'],
        [PYTHON, 'scripts/write_runtime_packet_inbox.py', '--json'],
        [PYTHON, 'scripts/write_runtime_parity.py', '--json'],
        [PYTHON, 'scripts/write_result_evidence_ledger.py', '--json'],
        [PYTHON, 'scripts/write_autonomous_value_proof.py', '--json'],
        [PYTHON, 'scripts/write_stable_operating_day.py', '--json'],
        [PYTHON, 'scripts/run_continuity_control_pass.py', 'status', '--json'],
        [PYTHON, 'scripts/write_blocker_map.py', '--json'],
        [PYTHON, 'scripts/write_blocker_execution_plan.py', '--json'],
        [PYTHON, 'scripts/write_continuity_supervisor_health.py', '--json'],
        [PYTHON, 'scripts/write_project_output_readiness.py', '--json'],
        [PYTHON, 'scripts/write_project_output_candidates.py', '--json'],
        [PYTHON, 'scripts/materialize_project_output_acceptance.py', '--all-pending', '--json'],
        [PYTHON, 'scripts/write_project_output_candidates.py', '--json'],
        [PYTHON, 'scripts/write_project_output_proof.py', '--json'],
        [PYTHON, 'scripts/write_autonomy_failure_ledger.py', '--json'],
        [PYTHON, 'scripts/write_controller_of_controllers.py', '--json'],
        [PYTHON, 'scripts/write_steady_state_status.py', '--json'],
        [PYTHON, 'scripts/write_operator_mobile_summary.py', '--json'],
        [PYTHON, 'scripts/refresh_master_atlas_dashboard_feed.py'],
        [PYTHON, 'scripts/write_command_center_final_form_status.py', '--json'],
        [PYTHON, 'scripts/write_system_capability_scorecard.py', '--json'],
        [PYTHON, 'scripts/generate_ecosystem_master_plan.py'],
        [PYTHON, 'scripts/generate_full_system_audit.py', '--skip-checks'],
        [PYTHON, 'scripts/validate_platform_contract.py'],
        [PYTHON, 'scripts/run_contract_healer.py'],
    ]
    if include_restart_brief:
        commands.append([PYTHON, 'scripts/session_restart_brief.py', '--json'])
    return commands


def command_timeout_seconds(command: List[str]) -> int:
    script_and_args = tuple(command[1:])
    return COMMAND_TIMEOUT_OVERRIDES.get(script_and_args, DEFAULT_COMMAND_TIMEOUT_SECONDS)


def command_env(command: List[str]) -> dict[str, str] | None:
    script_and_args = tuple(command[1:])
    if script_and_args in RUNTIME_PROOF_CONTEXT_COMMANDS:
        env = os.environ.copy()
        env['ATHANOR_RUNTIME_PROOF_CONTEXT'] = '1'
        return env
    return None


def run_commands(commands: Iterable[List[str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for command in commands:
        timeout_seconds = command_timeout_seconds(command)
        try:
            proc = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                env=command_env(command),
                timeout=timeout_seconds,
            )
            result = {
                'command': command,
                'returncode': proc.returncode,
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'timeout_seconds': timeout_seconds,
                'timed_out': False,
            }
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode() if exc.stdout else '')
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode() if exc.stderr else '')
            result = {
                'command': command,
                'returncode': 124,
                'stdout': stdout,
                'stderr': stderr or f'Timed out after {timeout_seconds}s',
                'timeout_seconds': timeout_seconds,
                'timed_out': True,
            }
        results.append(result)
        if int(result['returncode']) != 0:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the Athanor steady-state control-plane pass in fixed-point order.')
    parser.add_argument('--skip-restart-brief', action='store_true', help='Do not include scripts/session_restart_brief.py --json in the pass.')
    parser.add_argument('--json', action='store_true', help='Print machine-readable results.')
    args = parser.parse_args()

    commands = build_commands(include_restart_brief=not args.skip_restart_brief)
    results = run_commands(commands)
    success = all(int(item['returncode']) == 0 for item in results) and len(results) == len(commands)
    payload = {
        'success': success,
        'command_count': len(commands),
        'completed_count': len(results),
        'results': results,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for item in results:
            print(f"[{item['returncode']}] {' '.join(item['command'])}")
        print('success=' + ('true' if success else 'false'))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
