#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
DEFAULT_COMMAND_TIMEOUT_SECONDS = 120
COMMAND_TIMEOUT_OVERRIDES: dict[tuple[str, ...], int] = {
    ('scripts/validate_platform_contract.py',): 90,
}


def build_commands(include_ralph: bool = True, include_restart_brief: bool = False) -> List[List[str]]:
    commands: List[List[str]] = [[PYTHON, 'scripts/generate_documentation_index.py']]
    if include_ralph:
        commands.extend([
            [PYTHON, 'scripts/collect_capacity_telemetry.py'],
            [PYTHON, 'scripts/write_quota_truth_snapshot.py'],
            [PYTHON, 'scripts/run_ralph_loop_pass.py', '--skip-refresh', '--skip-validation'],
        ])
    commands.extend([
        [PYTHON, 'scripts/collect_truth_inventory.py'],
        [PYTHON, 'scripts/generate_truth_inventory_reports.py'],
    ])
    if include_ralph:
        commands.extend([
            [PYTHON, 'scripts/write_next_rotation_preflight.py', '--json'],
            [PYTHON, 'scripts/write_finish_scoreboard.py', '--json'],
            [PYTHON, 'scripts/write_runtime_packet_inbox.py', '--json'],
            [PYTHON, 'scripts/write_steady_state_status.py', '--json'],
        ])
    if include_restart_brief:
        commands.append([PYTHON, 'scripts/session_restart_brief.py', '--json'])
    commands.extend([
        [PYTHON, 'scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        [PYTHON, 'scripts/generate_publication_deferred_family_queue.py'],
        [PYTHON, 'scripts/validate_platform_contract.py'],
    ])
    return commands


def command_timeout_seconds(command: List[str]) -> int:
    script_and_args = tuple(command[1:])
    return COMMAND_TIMEOUT_OVERRIDES.get(script_and_args, DEFAULT_COMMAND_TIMEOUT_SECONDS)


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
    parser = argparse.ArgumentParser(description='Refresh validation and publication control-plane surfaces in one pass.')
    parser.add_argument('--skip-ralph', action='store_true', help='Do not run scripts/run_ralph_loop_pass.py --skip-refresh.')
    parser.add_argument('--include-restart-brief', action='store_true', help='Append scripts/session_restart_brief.py --json to the pass.')
    parser.add_argument('--json', action='store_true', help='Print machine-readable results.')
    args = parser.parse_args()

    commands = build_commands(include_ralph=not args.skip_ralph, include_restart_brief=args.include_restart_brief)
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
            cmd = ' '.join(item['command'])
            print(f"[{item['returncode']}] {cmd}")
        print('success=' + ('true' if success else 'false'))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
