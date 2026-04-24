from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / 'scripts'

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_audit_covers_required_layers_and_subsystems() -> None:
    module = _load_module(
        f'generate_full_system_audit_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_full_system_audit.py',
    )

    def fake_run_command(cwd, command, timeout=90):
        cmd = ' '.join(command)
        if 'validate_platform_contract.py' in cmd:
            return {'command': command, 'cwd': str(cwd), 'returncode': 1, 'stdout': '', 'stderr': 'stale Athanor docs'}
        if 'validate_devstack_contract.py' in cmd:
            return {'command': command, 'cwd': str(cwd), 'returncode': 1, 'stdout': '', 'stderr': 'stale forge board'}
        return {'command': command, 'cwd': str(cwd), 'returncode': 0, 'stdout': '', 'stderr': ''}

    def fake_run_json_command(cwd, command, timeout=90):
        return {
            'active_claim_task_id': 'burn_class:overnight_harvest',
            'active_claim_task_title': 'Overnight Harvest',
            'queue_dispatchable': 5,
            'suppressed_task_count': 4,
        }

    def fake_git_status(repo, ignored_paths=None):
        if str(repo).endswith('athanor-devstack'):
            return {
                'lines': [' M MASTER-PLAN.md', '?? docs/operations/DEVSTACK-FORGE-BOARD.md'] * 20,
                'counts': {'modified': 20, 'untracked': 20},
                'total': 40,
            }
        return {
            'lines': [' M docs/operations/PUBLICATION-TRIAGE-REPORT.md'],
            'counts': {'modified': 1},
            'total': 1,
        }

    fake_json = {
        'ralph_latest': {
            'active_claim_task_id': 'burn_class:overnight_harvest',
            'active_claim_task_title': 'Overnight Harvest',
            'suppressed_task_count': 2,
            'automation_feedback_summary': {'feedback_state': 'degraded', 'failure_count': 8, 'last_outcome': 'claimed'},
        },
        'finish_scoreboard': {
            'closure_state': 'repo_safe_complete',
            'active_claim_task_id': 'burn_class:local_bulk_sovereign',
            'queue_dispatchable_count': 6,
            'suppressed_queue_count': 7,
        },
        'runtime_packet_inbox': {'packet_count': 0},
        'steady_state_status': {
            'intervention_label': 'No action needed',
            'queue_dispatchable': 5,
            'suppressed_task_count': 4,
            'current_work': {'task_id': 'burn_class:overnight_harvest'},
        },
        'devstack_atlas': {
            'summary': {
                'turnover_status': 'ready_for_low_touch_execution',
                'top_priority_lane': 'codex_cloudsafe',
            },
            'readiness_ledger': {'records': [{'stage': 'adopted'}, {'stage': 'concept'}]},
        },
        'devstack_forge_board': {
            'top_priority_lane': 'letta-memory-plane',
        },
    }

    module._run_command = fake_run_command
    module._run_json_command = fake_run_json_command
    module._git_status = fake_git_status
    module._discover_manifests = lambda repo: ['projects/dashboard/package.json'] if str(repo).endswith('Athanor') else ['services/watchdog/docker-compose.yml']
    module._top_level_counts = lambda repo, folders: {folder: 1 for folder in folders}
    module._path_exists_map = lambda root, mapping: {name: True for name in mapping}
    module._load_json = lambda path: fake_json.get(path.stem.replace('-', '_'), fake_json.get(path.parent.name + '_' + path.stem.replace('-', '_'), {}))
    module._load_text = lambda path: f'text from {path.name}'

    audit = module.build_audit(run_checks=True)

    assert audit['coverage']['required_subsystems_covered'] is True
    assert set(audit['coverage']['authority_layers']) == {
        'adopted_live_system',
        'build_proving_system',
        'membrane_and_adoption_boundary',
        'strategic_reservoir',
    }
    assert 'ws-pty-bridge' in audit['coverage']['subsystem_ids']
    assert 'devstack-packets-promotion' in audit['coverage']['subsystem_ids']
    assert 'strategic-reservoir' in audit['coverage']['subsystem_ids']

    finding = next(item for item in audit['findings'] if item['id'] == 'audit.athanor.surface_divergence.active_claim')
    assert finding['source_of_truth_layer'] == 'adopted_live_system'
    assert finding['blocking_status'] == 'trust'
    assert finding['recommended_fix']

    subsystem = next(item for item in audit['scorecard'] if item['id'] == 'devstack-forge-atlas')
    assert subsystem['finding_count'] >= 1
    assert subsystem['remediation_priority'] in {'medium', 'high'}

    athanor_control = next(item for item in audit['scorecard'] if item['id'] == 'athanor-control-plane')
    assert athanor_control['summary'].startswith('The Athanor platform validator is currently red.')


def test_git_status_ignores_self_generated_audit_paths() -> None:
    module = _load_module(
        f'generate_full_system_audit_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_full_system_audit.py',
    )

    module._run_command = lambda cwd, command, timeout=20: {
        'command': command,
        'cwd': str(cwd),
        'returncode': 0,
        'stdout': 'M docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md\n M docs/operations/STEADY-STATE-STATUS.md\n?? reports/truth-inventory/tmp.json\n',
        'stderr': '',
    }

    status = module._git_status(
        Path('/mnt/c/Athanor'),
        ignored_paths={
            'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md',
        },
    )

    assert status['lines'] == [' M docs/operations/STEADY-STATE-STATUS.md', '?? reports/truth-inventory/tmp.json']
    assert status['counts'] == {'modified': 1, 'untracked': 1}
    assert status['total'] == 2


def test_with_ignored_generated_docs_appends_audit_targets() -> None:
    module = _load_module(
        f'generate_full_system_audit_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_full_system_audit.py',
    )

    athanor_validator_command = module._with_ignored_generated_docs(['python3', 'scripts/validate_platform_contract.py'])

    assert athanor_validator_command == [
        'python3', 'scripts/validate_platform_contract.py',
        '--ignore-generated-doc', 'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md',
        '--ignore-generated-doc', 'docs/operations/DEVSTACK-MEMBRANE-AUDIT.md',
        '--ignore-generated-doc', 'docs/operations/AUDIT-REMEDIATION-BACKLOG.md',
    ]


def test_top_level_counts_skips_dependency_and_build_dirs(tmp_path: Path) -> None:
    module = _load_module(
        f'generate_full_system_audit_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_full_system_audit.py',
    )
    repo = tmp_path / 'repo'
    source_file = repo / 'projects' / 'eoq' / 'src' / 'index.ts'
    dependency_file = repo / 'projects' / 'eoq' / 'node_modules' / '.bin' / 'acorn'
    build_file = repo / 'projects' / 'dashboard' / '.next' / 'server.js'
    source_file.parent.mkdir(parents=True)
    dependency_file.parent.mkdir(parents=True)
    build_file.parent.mkdir(parents=True)
    source_file.write_text('export {};\n', encoding='utf-8')
    dependency_file.write_text('ignored\n', encoding='utf-8')
    build_file.write_text('ignored\n', encoding='utf-8')
    module._rg_files = lambda repo, scope=None: []

    assert module._top_level_counts(repo, ['projects']) == {'projects': 1}


def test_build_audit_ignores_non_ralph_failures_when_feedback_state_is_healthy() -> None:
    module = _load_module(
        f'generate_full_system_audit_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_full_system_audit.py',
    )

    def fake_run_command(cwd, command, timeout=90):
        return {'command': command, 'cwd': str(cwd), 'returncode': 0, 'stdout': '', 'stderr': ''}

    def fake_run_json_command(cwd, command, timeout=90):
        return {
            'active_claim_task_id': 'deferred_family:operator-tooling-and-helper-surfaces',
            'active_claim_task_title': 'Operator Tooling and Helper Surfaces',
            'queue_dispatchable': 3,
            'suppressed_task_count': 9,
        }

    fake_json = {
        'ralph_latest': {
            'active_claim_task_id': 'deferred_family:operator-tooling-and-helper-surfaces',
            'active_claim_task_title': 'Operator Tooling and Helper Surfaces',
            'automation_feedback_summary': {
                'feedback_state': 'healthy',
                'feedback_scope': 'ralph_loop',
                'failure_count': 1,
                'last_outcome': 'success',
            },
        },
        'finish_scoreboard': {
            'closure_state': 'closure_in_progress',
            'active_claim_task_id': 'deferred_family:operator-tooling-and-helper-surfaces',
            'queue_dispatchable_count': 3,
            'suppressed_queue_count': 9,
        },
        'runtime_packet_inbox': {'packet_count': 0},
        'steady_state_status': {
            'intervention_label': 'Review recommended',
            'queue_dispatchable': 3,
            'suppressed_task_count': 9,
            'current_work': {'task_id': 'deferred_family:operator-tooling-and-helper-surfaces'},
        },
        'devstack_atlas': {
            'summary': {
                'turnover_status': 'ready_for_low_touch_execution',
                'top_priority_lane': 'protocol-first-builder-kernel',
            },
            'readiness_ledger': {'records': [{'stage': 'adopted'}]},
        },
        'devstack_forge_board': {
            'top_priority_lane': 'protocol-first-builder-kernel',
        },
    }

    module._run_command = fake_run_command
    module._run_json_command = fake_run_json_command
    module._git_status = lambda repo, ignored_paths=None: {'lines': [], 'counts': {}, 'total': 0}
    module._discover_manifests = lambda repo: []
    module._top_level_counts = lambda repo, folders: {folder: 0 for folder in folders}
    module._path_exists_map = lambda root, mapping: {name: True for name in mapping}
    module._load_json = lambda path: fake_json.get(path.stem.replace('-', '_'), fake_json.get(path.parent.name + '_' + path.stem.replace('-', '_'), {}))
    module._load_text = lambda path: f'text from {path.name}'

    audit = module.build_audit(run_checks=True)

    finding_ids = {item['id'] for item in audit['findings']}
    assert 'audit.athanor.automation_feedback.degraded' not in finding_ids

    athanor_control = next(item for item in audit['scorecard'] if item['id'] == 'athanor-control-plane')
    assert athanor_control['summary'] == 'Current control-plane truth surfaces are aligned and internally consistent.'
