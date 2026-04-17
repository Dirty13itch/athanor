from __future__ import annotations

import importlib.util
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
        ['scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        ['scripts/generate_publication_deferred_family_queue.py'],
        ['scripts/write_next_rotation_preflight.py', '--json'],
        ['scripts/write_finish_scoreboard.py', '--json'],
        ['scripts/write_runtime_packet_inbox.py', '--json'],
        ['scripts/write_steady_state_status.py', '--json'],
        ['scripts/generate_ecosystem_master_plan.py'],
        ['scripts/generate_full_system_audit.py', '--skip-checks'],
        ['scripts/generate_truth_inventory_reports.py'],
        ['scripts/triage_publication_tranche.py', '--write', 'docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
        ['scripts/generate_publication_deferred_family_queue.py'],
        ['scripts/write_finish_scoreboard.py', '--json'],
        ['scripts/write_steady_state_status.py', '--json'],
        ['scripts/generate_ecosystem_master_plan.py'],
        ['scripts/generate_full_system_audit.py', '--skip-checks'],
        ['scripts/session_restart_brief.py', '--json'],
        ['scripts/validate_platform_contract.py'],
    ]
    assert [cmd[1:] for cmd in commands] == expected


def test_build_commands_can_skip_restart_brief():
    module = _load_module()
    commands = module.build_commands(include_restart_brief=False)
    assert all(cmd[1] != "scripts/session_restart_brief.py" for cmd in commands)
    assert commands[-1][1:] == ["scripts/validate_platform_contract.py"]
