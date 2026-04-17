from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "run_steady_state_control_plane.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_steady_state_control_plane", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_commands_runs_fixed_point_order_with_steady_state_writer():
    module = _load_module()
    commands = module.build_commands()
    expected = [
        ['scripts/generate_documentation_index.py'],
        ['scripts/collect_capacity_telemetry.py'],
        ['scripts/write_quota_truth_snapshot.py'],
        ['scripts/run_ralph_loop_pass.py', '--skip-refresh', '--skip-validation'],
        ['scripts/collect_truth_inventory.py'],
        ['scripts/generate_truth_inventory_reports.py'],
        ['scripts/write_next_rotation_preflight.py', '--json'],
        ['scripts/write_finish_scoreboard.py', '--json'],
        ['scripts/write_runtime_packet_inbox.py', '--json'],
        ['scripts/write_steady_state_status.py', '--json'],
        ['scripts/generate_ecosystem_master_plan.py'],
        ['scripts/generate_full_system_audit.py', '--skip-checks'],
        ['scripts/session_restart_brief.py', '--json'],
        ['scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        ['scripts/generate_publication_deferred_family_queue.py'],
        ['scripts/validate_platform_contract.py'],
    ]
    assert [cmd[1:] for cmd in commands] == expected


def test_build_commands_can_skip_restart_brief():
    module = _load_module()
    commands = module.build_commands(include_restart_brief=False)
    assert all(cmd[1] != "scripts/session_restart_brief.py" for cmd in commands)
    assert commands[-1][1:] == ["scripts/validate_platform_contract.py"]


def test_run_commands_records_timeout_and_stops(monkeypatch):
    module = _load_module()
    commands = [
        [module.PYTHON, 'scripts/generate_documentation_index.py'],
        [module.PYTHON, 'scripts/validate_platform_contract.py'],
        [module.PYTHON, 'scripts/write_finish_scoreboard.py', '--json'],
    ]
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1:] == ['scripts/validate_platform_contract.py']:
            raise subprocess.TimeoutExpired(command, timeout=kwargs['timeout'], output=b'partial', stderr=b'')
        return subprocess.CompletedProcess(command, 0, stdout='ok', stderr='')

    monkeypatch.setattr(module.subprocess, 'run', fake_run)

    results = module.run_commands(commands)

    assert calls == commands[:2]
    assert results[0]['returncode'] == 0
    assert results[0]['timed_out'] is False
    assert results[1]['returncode'] == 124
    assert results[1]['timed_out'] is True
    assert results[1]['timeout_seconds'] == 90
    assert results[1]['stdout'] == 'partial'
    assert 'Timed out after 90s' in str(results[1]['stderr'])
