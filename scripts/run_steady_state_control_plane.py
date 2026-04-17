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


def build_commands(include_restart_brief: bool = True) -> List[List[str]]:
    commands: List[List[str]] = [
        [PYTHON, 'scripts/generate_documentation_index.py'],
        [PYTHON, 'scripts/collect_capacity_telemetry.py'],
        [PYTHON, 'scripts/write_quota_truth_snapshot.py'],
        [PYTHON, 'scripts/run_ralph_loop_pass.py', '--skip-refresh', '--skip-validation'],
        [PYTHON, 'scripts/generate_truth_inventory_reports.py'],
        [PYTHON, 'scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        [PYTHON, 'scripts/generate_publication_deferred_family_queue.py'],
        [PYTHON, 'scripts/write_next_rotation_preflight.py', '--json'],
        [PYTHON, 'scripts/write_finish_scoreboard.py', '--json'],
        [PYTHON, 'scripts/write_runtime_packet_inbox.py', '--json'],
        [PYTHON, 'scripts/write_steady_state_status.py', '--json'],
        [PYTHON, 'scripts/generate_ecosystem_master_plan.py'],
        [PYTHON, 'scripts/generate_full_system_audit.py', '--skip-checks'],
    ]
    if include_restart_brief:
        commands.append([PYTHON, 'scripts/session_restart_brief.py', '--json'])
    commands.append([PYTHON, 'scripts/validate_platform_contract.py'])
    return commands


def run_commands(commands: Iterable[List[str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for command in commands:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
        results.append({
            'command': command,
            'returncode': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
        })
        if proc.returncode != 0:
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
