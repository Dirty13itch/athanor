from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'run_steady_state_control_plane.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('run_steady_state_control_plane', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_commands_runs_fixed_point_order_with_steady_state_writer():
    module = _load_module()
    commands = module.build_commands()
    assert commands[0][1:] == ['scripts/generate_documentation_index.py']
    assert commands[1][1:] == ['scripts/collect_capacity_telemetry.py']
    assert commands[2][1:] == ['scripts/write_quota_truth_snapshot.py']
    assert commands[3][1:] == ['scripts/run_ralph_loop_pass.py', '--skip-refresh']
    assert commands[4][1:] == ['scripts/generate_truth_inventory_reports.py']
    assert commands[5][1:] == ['scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md']
    assert commands[6][1:] == ['scripts/generate_publication_deferred_family_queue.py']
    assert commands[7][1:] == ['scripts/write_next_rotation_preflight.py', '--json']
    assert commands[8][1:] == ['scripts/write_finish_scoreboard.py', '--json']
    assert commands[9][1:] == ['scripts/write_runtime_packet_inbox.py', '--json']
    assert commands[10][1:] == ['scripts/write_steady_state_status.py', '--json']
    assert commands[11][1:] == ['scripts/session_restart_brief.py', '--json']
    assert commands[-1][1:] == ['scripts/validate_platform_contract.py']


def test_build_commands_can_skip_restart_brief():
    module = _load_module()
    commands = module.build_commands(include_restart_brief=False)
    assert all(cmd[1] != 'scripts/session_restart_brief.py' for cmd in commands)
    assert commands[-1][1:] == ['scripts/validate_platform_contract.py']
