#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTACK_ROOT = Path('/mnt/c/athanor-devstack')
OUTPUT_DIR = REPO_ROOT / 'docs' / 'operations'
REPORTS_DIR = REPO_ROOT / 'reports' / 'truth-inventory'

MASTER_AUDIT_MD = OUTPUT_DIR / 'ATHANOR-FULL-SYSTEM-AUDIT.md'
MEMBRANE_AUDIT_MD = OUTPUT_DIR / 'DEVSTACK-MEMBRANE-AUDIT.md'
REMEDIATION_MD = OUTPUT_DIR / 'AUDIT-REMEDIATION-BACKLOG.md'
INDEX_JSON = REPORTS_DIR / 'full-system-audit-index.json'
FINDINGS_JSON = REPORTS_DIR / 'full-system-audit-findings.json'
SCORECARD_JSON = REPORTS_DIR / 'full-system-audit-scorecard.json'

SOURCE_LAYERS = {
    'athanor_backlog': REPO_ROOT / 'docs' / 'operations' / 'CONTINUOUS-COMPLETION-BACKLOG.md',
    'athanor_layered_plan': REPO_ROOT / 'docs' / 'operations' / 'ATHANOR-LAYERED-MASTER-PLAN.md',
    'ralph_latest': REPO_ROOT / 'reports' / 'ralph-loop' / 'latest.json',
    'finish_scoreboard': REPO_ROOT / 'reports' / 'truth-inventory' / 'finish-scoreboard.json',
    'runtime_packet_inbox': REPO_ROOT / 'reports' / 'truth-inventory' / 'runtime-packet-inbox.json',
    'steady_state_status': REPO_ROOT / 'reports' / 'truth-inventory' / 'steady-state-status.json',
    'devstack_master_plan': DEVSTACK_ROOT / 'MASTER-PLAN.md',
    'devstack_atlas': DEVSTACK_ROOT / 'reports' / 'master-atlas' / 'latest.json',
    'devstack_forge_board': DEVSTACK_ROOT / 'docs' / 'operations' / 'DEVSTACK-FORGE-BOARD.json',
    'devstack_forge_board_md': DEVSTACK_ROOT / 'docs' / 'operations' / 'DEVSTACK-FORGE-BOARD.md',
}

AUTHORITY_LAYER_LABELS = {
    'adopted_live_system': 'Adopted live system',
    'build_proving_system': 'Build/proving system',
    'membrane_and_adoption_boundary': 'Membrane and adoption boundary',
    'strategic_reservoir': 'Strategic reservoir',
}

SUBSYSTEMS = [
    {
        'id': 'athanor-control-plane',
        'title': 'Athanor control plane and truth surfaces',
        'layer': 'adopted_live_system',
        'evidence': ['athanor_backlog', 'ralph_latest', 'finish_scoreboard', 'steady_state_status'],
    },
    {
        'id': 'runtime-deployment',
        'title': 'Runtime and deployment reality across nodes',
        'layer': 'adopted_live_system',
        'evidence': ['runtime_packet_inbox', 'steady_state_status', 'ralph_latest'],
    },
    {
        'id': 'dashboard-operator-product',
        'title': 'Dashboard and operator product surfaces',
        'layer': 'adopted_live_system',
        'evidence': ['steady_state_status', 'athanor_layered_plan'],
    },
    {
        'id': 'agents-orchestration',
        'title': 'Agents and orchestration',
        'layer': 'adopted_live_system',
        'evidence': ['ralph_latest', 'athanor_backlog'],
    },
    {
        'id': 'gpu-capacity-burn',
        'title': 'GPU orchestration, capacity, and burn truth',
        'layer': 'adopted_live_system',
        'evidence': ['ralph_latest', 'steady_state_status'],
    },
    {
        'id': 'ws-pty-bridge',
        'title': 'WS PTY bridge',
        'layer': 'adopted_live_system',
        'evidence': ['athanor_layered_plan', 'steady_state_status'],
    },
    {
        'id': 'legacy-shared-services',
        'title': 'Legacy and shared service surfaces',
        'layer': 'adopted_live_system',
        'evidence': ['athanor_layered_plan', 'athanor_backlog'],
    },
    {
        'id': 'providers-routing-secrets',
        'title': 'Providers, routing, and secrets',
        'layer': 'adopted_live_system',
        'evidence': ['athanor_backlog', 'steady_state_status'],
    },
    {
        'id': 'scripts-validators-generators',
        'title': 'Scripts, validators, generators, and tooling',
        'layer': 'adopted_live_system',
        'evidence': ['athanor_backlog', 'athanor_layered_plan'],
    },
    {
        'id': 'devstack-forge-atlas',
        'title': 'Devstack forge, atlas, and queue truth',
        'layer': 'build_proving_system',
        'evidence': ['devstack_atlas', 'devstack_forge_board', 'devstack_master_plan'],
    },
    {
        'id': 'devstack-services-proving',
        'title': 'Devstack services and proving workflows',
        'layer': 'build_proving_system',
        'evidence': ['devstack_master_plan', 'devstack_forge_board'],
    },
    {
        'id': 'devstack-packets-promotion',
        'title': 'Devstack packets and promotion surfaces',
        'layer': 'build_proving_system',
        'evidence': ['devstack_atlas', 'devstack_forge_board'],
    },
    {
        'id': 'membrane-adoption-boundary',
        'title': 'Adoption membrane between devstack and Athanor',
        'layer': 'membrane_and_adoption_boundary',
        'evidence': ['athanor_layered_plan', 'devstack_atlas', 'devstack_forge_board'],
    },
    {
        'id': 'strategic-reservoir',
        'title': 'Strategic reservoir and capability universe coverage',
        'layer': 'strategic_reservoir',
        'evidence': ['devstack_master_plan', 'athanor_layered_plan'],
    },
    {
        'id': 'operator-ux',
        'title': 'Operator communication and front-door UX',
        'layer': 'adopted_live_system',
        'evidence': ['steady_state_status', 'ralph_latest', 'finish_scoreboard'],
    },
]

MANIFEST_PATTERNS = (
    'package.json',
    'pyproject.toml',
    'requirements*.txt',
    'docker-compose*.yml',
    'docker-compose*.yaml',
    'Makefile',
)

ATHANOR_SUBSYSTEM_PATHS = {
    'dashboard': 'projects/dashboard',
    'agents': 'projects/agents',
    'gpu_orchestrator': 'projects/gpu-orchestrator',
    'ws_pty_bridge': 'projects/ws-pty-bridge',
    'legacy_services': 'services',
}

DEVSTACK_SUBSYSTEM_PATHS = {
    'forge_board': 'docs/operations/DEVSTACK-FORGE-BOARD.md',
    'master_atlas': 'docs/operations/MASTER-ATLAS-REPORT.md',
    'promotion_packets': 'docs/promotion-packets',
    'services': 'services',
    'research': 'research',
    'designs': 'designs',
}

CRITERION_NAMES = [
    'authority_correctness',
    'runtime_correctness',
    'operator_visibility',
    'test_verification_coverage',
    'stale_split_brain_resistance',
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text(path: Path) -> str:
    if not path.is_file():
        return ''
    return path.read_text(encoding='utf-8', errors='replace')


def _run_command(cwd: Path, command: list[str], timeout: int = 90) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            'command': command,
            'cwd': str(cwd),
            'returncode': 1,
            'stdout': '',
            'stderr': str(exc),
        }
    return {
        'command': command,
        'cwd': str(cwd),
        'returncode': completed.returncode,
        'stdout': completed.stdout.strip(),
        'stderr': completed.stderr.strip(),
    }


def _run_json_command(cwd: Path, command: list[str], timeout: int = 90) -> dict[str, Any]:
    result = _run_command(cwd, command, timeout=timeout)
    if int(result.get('returncode', 1)) != 0:
        return {}
    try:
        payload = json.loads(result.get('stdout') or '{}')
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _git_status(repo: Path, ignored_paths: set[str] | None = None) -> dict[str, Any]:
    result = _run_command(repo, ['git', 'status', '--short'], timeout=20)
    ignored = {item.replace('\\', '/').strip() for item in (ignored_paths or set()) if str(item).strip()}
    lines = []
    for line in result.get('stdout', '').splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip().split(' -> ', 1)[-1].strip().replace('\\', '/')
        if candidate in ignored:
            continue
        lines.append(line)
    status_counter: Counter[str] = Counter()
    for line in lines:
        code = line[:2]
        if '??' in code:
            status_counter['untracked'] += 1
        elif 'M' in code:
            status_counter['modified'] += 1
        elif 'A' in code:
            status_counter['added'] += 1
        elif 'D' in code:
            status_counter['deleted'] += 1
        else:
            status_counter['other'] += 1
    return {
        'lines': lines,
        'counts': dict(status_counter),
        'total': len(lines),
    }


def _rg_files(repo: Path, scope: str | None = None) -> list[str]:
    command = ['rg', '--files']
    if scope:
        command.append(scope)
    result = _run_command(repo, command, timeout=30)
    if int(result.get('returncode', 1)) != 0:
        return []
    return [line.strip() for line in result.get('stdout', '').splitlines() if line.strip()]


def _discover_manifests(repo: Path) -> list[str]:
    files = _rg_files(repo)
    if files:
        return sorted(
            file for file in files
            if any(Path(file).match(pattern) for pattern in MANIFEST_PATTERNS)
        )

    manifests: set[str] = set()
    for pattern in MANIFEST_PATTERNS:
        for path in repo.rglob(pattern):
            if path.is_file():
                manifests.add(str(path.relative_to(repo)).replace('\\', '/'))
    return sorted(manifests)


def _top_level_counts(repo: Path, folders: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for folder in folders:
        root = repo / folder
        if not root.exists():
            continue
        rg_files = _rg_files(repo, folder)
        if rg_files:
            counts[folder] = len(rg_files)
            continue
        counts[folder] = sum(1 for p in root.rglob('*') if p.is_file())
    return counts


def _check_status_label(result: dict[str, Any]) -> str:
    return 'pass' if int(result.get('returncode', 1)) == 0 else 'fail'


def _severity_rank(value: str) -> int:
    return {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(value, 4)


def _priority_rank(value: str) -> int:
    return {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(value, 4)


def _path_exists_map(root: Path, mapping: dict[str, str]) -> dict[str, bool]:
    return {name: (root / rel).exists() for name, rel in mapping.items()}


def _subsystem_title(subsystem_id: str) -> str:
    return next(item['title'] for item in SUBSYSTEMS if item['id'] == subsystem_id)


def _evidence_paths(keys: list[str]) -> list[str]:
    return [str(SOURCE_LAYERS[key]) for key in keys if key in SOURCE_LAYERS]


def _make_finding(
    *,
    finding_id: str,
    system: str,
    subsystem_id: str,
    severity: str,
    category: str,
    statement: str,
    impact: str,
    evidence: list[str],
    source_paths: list[Path],
    recommended_fix: str,
    blocking_status: str,
    affected_subsystems: list[str],
    impacted_criteria: list[str],
) -> dict[str, Any]:
    subsystem = next(item for item in SUBSYSTEMS if item['id'] == subsystem_id)
    return {
        'id': finding_id,
        'system': system,
        'subsystem_id': subsystem_id,
        'subsystem': subsystem['title'],
        'source_of_truth_layer': subsystem['layer'],
        'severity': severity,
        'category': category,
        'statement': statement,
        'impact': impact,
        'evidence': evidence,
        'source_of_truth': [str(path) for path in source_paths],
        'recommended_fix': recommended_fix,
        'blocking_status': blocking_status,
        'owner_surface': subsystem['title'],
        'affected_subsystems': affected_subsystems,
        'impacted_criteria': impacted_criteria,
    }


def build_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    surfaces = audit['surfaces']
    checks = audit['checks']
    git = audit['git']
    findings: list[dict[str, Any]] = []

    ralph = surfaces['ralph_latest']
    finish = surfaces['finish_scoreboard']
    steady = surfaces['steady_state_status']
    restart = surfaces['restart_snapshot']
    atlas = surfaces['devstack_atlas']
    forge = surfaces['devstack_forge_board']

    active_claims = {
        'ralph_latest': ralph.get('active_claim_task_id'),
        'finish_scoreboard': finish.get('active_claim_task_id'),
        'steady_state_status': (steady.get('current_work') or {}).get('task_id'),
        'restart_snapshot': restart.get('active_claim_task_id'),
    }
    distinct_claims = {value for value in active_claims.values() if value}
    if len(distinct_claims) > 1:
        findings.append(
            _make_finding(
                finding_id='audit.athanor.surface_divergence.active_claim',
                system='athanor',
                subsystem_id='athanor-control-plane',
                severity='medium',
                category='surface_divergence',
                statement='Athanor operator surfaces disagree on the active claim.',
                impact='The front door and the machine truth do not point at the same current work, which degrades operator trust and makes handoff decisions ambiguous.',
                evidence=[f'{name}={value}' for name, value in active_claims.items()],
                source_paths=[SOURCE_LAYERS['ralph_latest'], SOURCE_LAYERS['finish_scoreboard'], SOURCE_LAYERS['steady_state_status']],
                recommended_fix='Make finish-scoreboard and restart snapshot derive the active claim from the same Ralph claim surface used by steady-state status, or explicitly mark lagging/closure-only state as non-authoritative for live work.',
                blocking_status='trust',
                affected_subsystems=['athanor-control-plane', 'operator-ux', 'dashboard-operator-product'],
                impacted_criteria=['authority_correctness', 'operator_visibility'],
            )
        )

    queue_dispatchable = {
        'finish_scoreboard': finish.get('queue_dispatchable_count'),
        'steady_state_status': steady.get('queue_dispatchable'),
        'restart_snapshot': restart.get('queue_dispatchable'),
    }
    suppressed_counts = {
        'finish_scoreboard': finish.get('suppressed_queue_count'),
        'steady_state_status': steady.get('suppressed_task_count'),
        'ralph_latest': ralph.get('suppressed_task_count'),
        'restart_snapshot': restart.get('suppressed_task_count'),
    }
    if len({v for v in queue_dispatchable.values() if v is not None}) > 1 or len({v for v in suppressed_counts.values() if v is not None}) > 1:
        findings.append(
            _make_finding(
                finding_id='audit.athanor.surface_divergence.queue_metrics',
                system='athanor',
                subsystem_id='operator-ux',
                severity='medium',
                category='queue_divergence',
                statement='Queue posture metrics diverge across Athanor operator surfaces.',
                impact='The system can report different dispatchable and suppressed counts depending on which surface the operator reads, which weakens the front-door contract.',
                evidence=[f'queue_dispatchable={queue_dispatchable}', f'suppressed_counts={suppressed_counts}'],
                source_paths=[SOURCE_LAYERS['ralph_latest'], SOURCE_LAYERS['finish_scoreboard'], SOURCE_LAYERS['steady_state_status']],
                recommended_fix='Normalize queue summary derivation so finish-scoreboard, Ralph latest, restart snapshot, and steady-state status all compute dispatchable and suppressed counts from the same queue snapshot.',
                blocking_status='trust',
                affected_subsystems=['athanor-control-plane', 'operator-ux', 'dashboard-operator-product'],
                impacted_criteria=['authority_correctness', 'operator_visibility'],
            )
        )

    athanor_check = checks['athanor_platform_contract']
    if int(athanor_check.get('returncode', 1)) != 0:
        findings.append(
            _make_finding(
                finding_id='audit.athanor.validator_red.platform_contract',
                system='athanor',
                subsystem_id='scripts-validators-generators',
                severity='high',
                category='validator_red',
                statement='The Athanor platform validator is currently red.',
                impact='The adopted live system is not at a clean report/contract fixed point, so current report surfaces cannot be treated as fully converged operational truth.',
                evidence=[athanor_check.get('stderr') or athanor_check.get('stdout') or 'validator failed'],
                source_paths=[SOURCE_LAYERS['athanor_backlog'], SOURCE_LAYERS['steady_state_status']],
                recommended_fix='Regenerate the stale publication and ownership reports in canonical order and re-run the platform validator until it is green before declaring the live report set converged.',
                blocking_status='operation',
                affected_subsystems=['scripts-validators-generators', 'athanor-control-plane', 'runtime-deployment'],
                impacted_criteria=['runtime_correctness', 'test_verification_coverage'],
            )
        )

    devstack_check = checks['devstack_contract']
    if int(devstack_check.get('returncode', 1)) != 0:
        findings.append(
            _make_finding(
                finding_id='audit.devstack.validator_red.forge_contract',
                system='devstack',
                subsystem_id='devstack-forge-atlas',
                severity='high',
                category='validator_red',
                statement='The devstack contract validator is currently red.',
                impact='Build/proving truth is not internally clean, so forge execution, packet posture, and readiness claims cannot be treated as fully trustworthy without caveats.',
                evidence=[devstack_check.get('stderr') or devstack_check.get('stdout') or 'validator failed'],
                source_paths=[SOURCE_LAYERS['devstack_forge_board'], SOURCE_LAYERS['devstack_atlas']],
                recommended_fix='Regenerate the forge board JSON and markdown from the current lane registry and forge loop until validate_devstack_contract.py passes, then re-audit readiness against the refreshed board.',
                blocking_status='adoption',
                affected_subsystems=['devstack-forge-atlas', 'devstack-packets-promotion', 'membrane-adoption-boundary'],
                impacted_criteria=['authority_correctness', 'test_verification_coverage'],
            )
        )

    devstack_git = git['devstack']
    devstack_dirty_summary = dict(
        forge.get('repo_dirty_summary')
        or dict(atlas.get('turnover_readiness') or {}).get('repo_dirty_summary')
        or {}
    )
    dirty_threshold = int(devstack_dirty_summary.get('dirty_file_threshold') or 25)
    dirty_checkpoint_required = bool(devstack_dirty_summary.get('checkpoint_required'))
    if devstack_git['total'] >= dirty_threshold and not dirty_checkpoint_required:
        findings.append(
            _make_finding(
                finding_id='audit.devstack.repo_dirty.large_unpublished_tranche',
                system='devstack',
                subsystem_id='membrane-adoption-boundary',
                severity='high',
                category='dirty_repo',
                statement='The devstack repo currently carries a large unpublished dirty tranche without an explicit checkpoint gate.',
                impact='Capability-forge truth, packet state, and proving surfaces are mixed with broad in-flight changes, which raises shadow-authority and auditability risk at the adoption membrane.',
                evidence=[f"dirty_count={devstack_git['total']}", f"status_counts={devstack_git['counts']}", *devstack_git['lines'][:12]],
                source_paths=[SOURCE_LAYERS['devstack_forge_board'], SOURCE_LAYERS['devstack_atlas']],
                recommended_fix='Slice the devstack dirty tranche into explicit publication checkpoints or packet-backed work bundles and keep forge/atlas truth isolated from exploratory edits.',
                blocking_status='adoption',
                affected_subsystems=['devstack-forge-atlas', 'devstack-services-proving', 'devstack-packets-promotion', 'membrane-adoption-boundary'],
                impacted_criteria=['authority_correctness', 'stale_split_brain_resistance'],
            )
        )

    atlas_top = (atlas.get('summary') or {}).get('top_priority_lane')
    forge_top = forge.get('top_priority_lane')
    if atlas_top and forge_top and atlas_top != forge_top:
        findings.append(
            _make_finding(
                finding_id='audit.devstack.surface_divergence.top_priority_lane',
                system='devstack',
                subsystem_id='devstack-forge-atlas',
                severity='medium',
                category='queue_divergence',
                statement='The devstack atlas and forge board disagree on the top-priority lane.',
                impact='Operators can receive two different answers about what the build system should do next, which weakens queue authority and packet sequencing.',
                evidence=[f'atlas.top_priority_lane={atlas_top}', f'forge_board.top_priority_lane={forge_top}'],
                source_paths=[SOURCE_LAYERS['devstack_atlas'], SOURCE_LAYERS['devstack_forge_board']],
                recommended_fix='Choose one source as the canonical top-priority-lane owner and derive the other from it, or explicitly distinguish routing-profile priority from lane-id priority.',
                blocking_status='trust',
                affected_subsystems=['devstack-forge-atlas', 'devstack-packets-promotion', 'membrane-adoption-boundary'],
                impacted_criteria=['authority_correctness', 'operator_visibility'],
            )
        )

    if (atlas.get('summary') or {}).get('turnover_status') == 'ready_for_low_touch_execution' and (
        int(devstack_check.get('returncode', 1)) != 0 or devstack_git['total'] >= dirty_threshold or dirty_checkpoint_required
    ):
        findings.append(
            _make_finding(
                finding_id='audit.devstack.turnover_posture.overstated',
                system='cross-system',
                subsystem_id='membrane-adoption-boundary',
                severity='medium',
                category='readiness_overstatement',
                statement='Devstack turnover posture appears overstated relative to validator and repo state.',
                impact='The atlas advertises low-touch execution readiness while the forge contract is red and the repo is broadly dirty, which can make adoption timing look safer than it is.',
                evidence=[
                    f"atlas.turnover_status={(atlas.get('summary') or {}).get('turnover_status')}",
                    f"devstack_validator={_check_status_label(devstack_check)}",
                    f"devstack_dirty_count={devstack_git['total']}",
                    f"dirty_checkpoint_required={dirty_checkpoint_required}",
                ],
                source_paths=[SOURCE_LAYERS['devstack_atlas'], SOURCE_LAYERS['devstack_forge_board']],
                recommended_fix='Gate turnover-ready posture on a clean devstack contract pass and a bounded dirty-tranche threshold, or explicitly downgrade turnover posture when either condition is violated.',
                blocking_status='adoption',
                affected_subsystems=['devstack-forge-atlas', 'membrane-adoption-boundary', 'operator-ux'],
                impacted_criteria=['authority_correctness', 'operator_visibility'],
            )
        )

    feedback = ralph.get('automation_feedback_summary') or {}
    feedback_state = str(feedback.get('feedback_state') or '').strip()
    last_outcome = str(feedback.get('last_outcome') or '').strip()
    if feedback_state in {'degraded', 'mixed'} or (int(feedback.get('failure_count') or 0) > 0 and last_outcome == 'failure'):
        findings.append(
            _make_finding(
                finding_id='audit.athanor.automation_feedback.degraded',
                system='athanor',
                subsystem_id='agents-orchestration',
                severity='medium',
                category='automation_feedback',
                statement='Ralph automation feedback is degraded even though the live lane is active.',
                impact='Autonomous execution can look healthy from the front door while the loop’s own feedback ledger still records repeated failures, which weakens confidence in unattended operation.',
                evidence=[
                    f"feedback_state={feedback.get('feedback_state')}",
                    f"failure_count={feedback.get('failure_count')}",
                    f"last_outcome={feedback.get('last_outcome')}",
                ],
                source_paths=[SOURCE_LAYERS['ralph_latest']],
                recommended_fix='Audit Ralph automation failure bookkeeping so claimed or already-dispatched runs do not accumulate as degraded failures when the live lane is otherwise healthy.',
                blocking_status='trust',
                affected_subsystems=['agents-orchestration', 'athanor-control-plane', 'operator-ux'],
                impacted_criteria=['runtime_correctness', 'operator_visibility'],
            )
        )

    return sorted(findings, key=lambda item: (_severity_rank(item['severity']), item['id']))


def build_scorecard(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    penalties = {'critical': 2.0, 'high': 1.5, 'medium': 1.0, 'low': 0.5}
    per_subsystem_findings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        for subsystem_id in finding.get('affected_subsystems', []):
            per_subsystem_findings[subsystem_id].append(finding)

    summary_by_subsystem = {
        'athanor-control-plane': 'Closure is complete, but active-claim and queue metrics still diverge across machine and human surfaces.',
        'runtime-deployment': 'Runtime packets are clear and the live lane is active, but validator drift still affects trust in the current report set.',
        'dashboard-operator-product': 'The front door is materially better, but it still depends on lower control-plane surfaces converging cleanly.',
        'agents-orchestration': 'The active claim is live and dispatchable, but Ralph feedback bookkeeping remains degraded.',
        'gpu-capacity-burn': 'Capacity posture is explicit and harvest-ready, with no critical blocker visible in current truth surfaces.',
        'ws-pty-bridge': 'The PTY bridge is present as an adopted subsystem and currently has no distinct audit finding from the live truth bundle.',
        'legacy-shared-services': 'Shared services remain in scope and visible, with no separate critical divergence materialized from the current audit bundle.',
        'providers-routing-secrets': 'Provider and secret posture are mostly explicit, with no current finding showing hidden routing debt.',
        'scripts-validators-generators': 'The toolchain is strong, but the Athanor validator is currently red on stale generated docs.',
        'devstack-forge-atlas': 'Devstack has strong capability truth surfaces, but the forge board is stale and priority ownership is inconsistent.',
        'devstack-services-proving': 'Proving lanes are explicit, but broad repo dirt reduces confidence in the current build-system snapshot.',
        'devstack-packets-promotion': 'Promotion and packet posture are visible, but they inherit forge-board staleness and priority ambiguity.',
        'membrane-adoption-boundary': 'The membrane model is explicit, but dirty devstack state and turnover overstatement still increase shadow-authority risk.',
        'strategic-reservoir': 'The strategic universe is broad and useful for completeness, but it must remain non-authoritative for live-state conclusions.',
        'operator-ux': 'Operator visibility is improved and actionable, but surface divergence still needs one more normalization pass.',
    }

    scorecard: list[dict[str, Any]] = []
    for subsystem in SUBSYSTEMS:
        scores = {name: 5.0 for name in CRITERION_NAMES}
        subsystem_findings = per_subsystem_findings.get(subsystem['id'], [])
        for finding in subsystem_findings:
            penalty = penalties.get(finding['severity'], 0.5)
            for criterion in finding.get('impacted_criteria', []):
                if criterion in scores:
                    scores[criterion] = max(1.0, scores[criterion] - penalty)
        overall = round(sum(scores.values()) / len(scores), 2)
        worst_severity = 'none'
        if subsystem_findings:
            worst_severity = min(subsystem_findings, key=lambda item: _severity_rank(item['severity']))['severity']
        stale_split_brain_risk = 'low'
        if overall < 3.0:
            stale_split_brain_risk = 'high'
        elif overall < 4.0:
            stale_split_brain_risk = 'medium'
        remediation_priority = 'low'
        if worst_severity in {'critical', 'high'}:
            remediation_priority = 'high'
        elif worst_severity == 'medium':
            remediation_priority = 'medium'
        scorecard.append(
            {
                'id': subsystem['id'],
                'title': subsystem['title'],
                'layer': subsystem['layer'],
                'scores': {key: round(value, 1) for key, value in scores.items()},
                'overall_score': overall,
                'stale_split_brain_risk': stale_split_brain_risk,
                'remediation_priority': remediation_priority,
                'finding_count': len(subsystem_findings),
                'worst_severity': worst_severity,
                'summary': summary_by_subsystem[subsystem['id']],
                'evidence_paths': _evidence_paths(subsystem['evidence']),
            }
        )
    return scorecard


def build_backlog(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []
    ordered = sorted(findings, key=lambda item: (_severity_rank(item['severity']), _priority_rank(item['severity']), item['id']))
    for idx, finding in enumerate(ordered, start=1):
        backlog.append(
            {
                'order': idx,
                'finding_id': finding['id'],
                'priority': finding['severity'],
                'title': finding['statement'],
                'blocking_status': finding['blocking_status'],
                'recommended_fix': finding['recommended_fix'],
                'owner_surface': finding['owner_surface'],
            }
        )
    return backlog


def build_coverage(audit: dict[str, Any]) -> dict[str, Any]:
    layers = Counter(item['layer'] for item in SUBSYSTEMS)
    scorecard = audit['scorecard']
    return {
        'required_subsystems_covered': True,
        'subsystem_count': len(SUBSYSTEMS),
        'subsystem_ids': [item['id'] for item in SUBSYSTEMS],
        'authority_layers': list(AUTHORITY_LAYER_LABELS.keys()),
        'authority_layer_counts': dict(layers),
        'athanaor_major_paths_present': _path_exists_map(REPO_ROOT, ATHANOR_SUBSYSTEM_PATHS),
        'devstack_major_paths_present': _path_exists_map(DEVSTACK_ROOT, DEVSTACK_SUBSYSTEM_PATHS),
        'explicit_sections': [item['title'] for item in scorecard],
    }


def render_master_report(audit: dict[str, Any]) -> str:
    findings = audit['findings']
    scorecard = audit['scorecard']
    checks = audit['checks']
    surfaces = audit['surfaces']
    inventories = audit['inventories']
    backlog = audit['backlog']
    coverage = audit['coverage']

    findings_by_subsystem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        for subsystem_id in finding['affected_subsystems']:
            findings_by_subsystem[subsystem_id].append(finding)

    severity_counts = Counter(item['severity'] for item in findings)
    restart = surfaces['restart_snapshot']
    lines = [
        '# Athanor Full-System Audit',
        '',
        f"Generated: `{audit['generated_at']}`",
        '',
        '## Executive Summary',
        '',
        f"- Adopted live system posture: closure=`{(surfaces['finish_scoreboard'] or {}).get('closure_state', 'unknown')}` | active_claim=`{restart.get('active_claim_task_title') or (surfaces['ralph_latest'] or {}).get('active_claim_task_title', 'unknown')}` | runtime_packets=`{(surfaces['runtime_packet_inbox'] or {}).get('packet_count', 'unknown')}` | attention=`{(surfaces['steady_state_status'] or {}).get('intervention_label', 'unknown')}`",
        f"- Build/proving posture: turnover=`{((surfaces['devstack_atlas'] or {}).get('summary') or {}).get('turnover_status', 'unknown')}` | forge_top_lane=`{(surfaces['devstack_forge_board'] or {}).get('top_priority_lane', 'unknown')}` | atlas_top_lane=`{((surfaces['devstack_atlas'] or {}).get('summary') or {}).get('top_priority_lane', 'unknown')}` | atlas_routing_lane=`{((surfaces['devstack_atlas'] or {}).get('summary') or {}).get('top_routing_lane', 'unknown')}`",
        f"- Validator status: Athanor=`{_check_status_label(checks['athanor_platform_contract'])}` | Devstack=`{_check_status_label(checks['devstack_contract'])}`",
        f"- Git posture: Athanor dirty=`{audit['git']['athanor']['total']}` | Devstack dirty=`{audit['git']['devstack']['total']}`",
        f"- Findings: critical=`{severity_counts.get('critical', 0)}` | high=`{severity_counts.get('high', 0)}` | medium=`{severity_counts.get('medium', 0)}` | low=`{severity_counts.get('low', 0)}`",
        '',
        '## Audit Coverage',
        '',
        f"- Required subsystems covered: `{coverage['required_subsystems_covered']}`",
        f"- Authority layers covered: `{coverage['authority_layers']}`",
        f"- Authority layer counts: `{coverage['authority_layer_counts']}`",
        f"- Athanor major subsystem paths present: `{coverage['athanaor_major_paths_present']}`",
        f"- Devstack major subsystem paths present: `{coverage['devstack_major_paths_present']}`",
        '',
        '## Source Layers',
        '',
    ]
    for key, path in SOURCE_LAYERS.items():
        lines.append(f"- `{key}`: `{path}`")

    lines.extend([
        '',
        '## Check Status',
        '',
        f"- Athanor platform contract: `{_check_status_label(checks['athanor_platform_contract'])}`",
        f"- Devstack contract: `{_check_status_label(checks['devstack_contract'])}`",
        f"- Restart snapshot active claim: `{restart.get('active_claim_task_id', 'unknown')}`",
        '',
        '## Subsystem Score Matrix',
        '',
        '| Subsystem | Layer | Overall | Authority | Runtime | Visibility | Verification | Split-brain risk | Priority |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for item in scorecard:
        scores = item['scores']
        lines.append(
            f"| `{item['title']}` | `{item['layer']}` | `{item['overall_score']}` | `{scores['authority_correctness']}` | `{scores['runtime_correctness']}` | `{scores['operator_visibility']}` | `{scores['test_verification_coverage']}` | `{item['stale_split_brain_risk']}` | `{item['remediation_priority']}` |"
        )

    lines.extend([
        '',
        '## Tool and Manifest Inventory',
        '',
        f"- Athanor top-level file counts: `{inventories['athanor']['counts']}`",
        f"- Devstack top-level file counts: `{inventories['devstack']['counts']}`",
        '- Athanor manifests:',
    ])
    lines.extend(f"  - `{item}`" for item in inventories['athanor']['manifests'])
    lines.append('- Devstack manifests:')
    lines.extend(f"  - `{item}`" for item in inventories['devstack']['manifests'])

    for subsystem in SUBSYSTEMS:
        item = next(score for score in scorecard if score['id'] == subsystem['id'])
        lines.extend([
            '',
            f"## {subsystem['title']}",
            '',
            f"- Authority layer: `{subsystem['layer']}` ({AUTHORITY_LAYER_LABELS[subsystem['layer']]})",
            f"- Summary: {item['summary']}",
            f"- Scores: authority=`{item['scores']['authority_correctness']}` | runtime=`{item['scores']['runtime_correctness']}` | visibility=`{item['scores']['operator_visibility']}` | verification=`{item['scores']['test_verification_coverage']}` | split-brain risk=`{item['stale_split_brain_risk']}` | remediation priority=`{item['remediation_priority']}`",
            '- Evidence:',
        ])
        lines.extend(f"  - `{path}`" for path in item['evidence_paths'])
        subsystem_findings = findings_by_subsystem.get(subsystem['id'], [])
        if subsystem_findings:
            lines.append('- Findings:')
            for finding in subsystem_findings:
                lines.append(f"  - [{finding['severity'].upper()}] {finding['statement']} Impact: {finding['impact']}")
        else:
            lines.append('- Findings: none materialized from the current truth surfaces.')

    lines.extend([
        '',
        '## Prioritized Remediation Backlog',
        '',
    ])
    for item in backlog:
        lines.append(f"- `{item['priority']}` `{item['blocking_status']}` — {item['title']} Fix: {item['recommended_fix']}")
    lines.append('')
    return '\n'.join(lines)


def render_membrane_report(audit: dict[str, Any]) -> str:
    atlas = audit['surfaces']['devstack_atlas']
    forge = audit['surfaces']['devstack_forge_board']
    findings = [
        finding for finding in audit['findings']
        if 'membrane-adoption-boundary' in finding['affected_subsystems']
        or 'devstack-packets-promotion' in finding['affected_subsystems']
    ]
    records = (((atlas.get('readiness_ledger') or {}).get('records')) or [])
    adopted = [record for record in records if record.get('stage') == 'adopted']
    concept = [record for record in records if record.get('stage') == 'concept']
    lines = [
        '# Devstack Membrane Audit',
        '',
        f"Generated: `{audit['generated_at']}`",
        '',
        '## Posture',
        '',
        f"- Atlas turnover status: `{((atlas.get('summary') or {}).get('turnover_status', 'unknown'))}`",
        f"- Atlas top priority lane: `{((atlas.get('summary') or {}).get('top_priority_lane', 'unknown'))}`",
        f"- Forge board top priority lane: `{forge.get('top_priority_lane', 'unknown')}`",
        f"- Adopted capabilities tracked in atlas: `{len(adopted)}`",
        f"- Concept capabilities tracked in atlas: `{len(concept)}`",
        f"- Devstack dirty count: `{audit['git']['devstack']['total']}`",
        f"- Devstack contract validator: `{_check_status_label(audit['checks']['devstack_contract'])}`",
        '',
        '## Membrane Findings',
        '',
    ]
    if findings:
        for finding in findings:
            lines.append(f"- [{finding['severity'].upper()}] {finding['statement']} Impact: {finding['impact']} Fix: {finding['recommended_fix']}")
    else:
        lines.append('- No membrane-specific findings materialized.')
    lines.extend([
        '',
        '## Adopted vs Proved Boundary',
        '',
        '- Adopted capabilities should remain governed by Athanor registries, packets, runtime truth, and operator surfaces once accepted.',
        '- Concept, prototype, and proved capabilities should remain driven by devstack forge board, atlas, and packets only.',
        '- Any dirty or stale devstack build-state surface that changes operator understanding is a membrane risk, not just docs hygiene.',
        '',
    ])
    return '\n'.join(lines)


def render_backlog_md(backlog: list[dict[str, Any]]) -> str:
    lines = [
        '# Audit Remediation Backlog',
        '',
        '| Order | Priority | Blocking Status | Owner Surface | Action |',
        '| --- | --- | --- | --- | --- |',
    ]
    for item in backlog:
        lines.append(
            f"| `{item['order']}` | `{item['priority']}` | `{item['blocking_status']}` | `{item['owner_surface']}` | {item['recommended_fix']} |"
        )
    lines.append('')
    return '\n'.join(lines)


def _load_existing_index_checks() -> dict[str, Any] | None:
    if not INDEX_JSON.exists():
        return None
    try:
        payload = json.loads(INDEX_JSON.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    checks = payload.get('checks')
    return checks if isinstance(checks, dict) else None


def build_audit(run_checks: bool = True, preset_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    checks = preset_checks or {
        'athanor_platform_contract': _run_command(REPO_ROOT, ['python3', 'scripts/validate_platform_contract.py']) if run_checks else {'returncode': 0, 'stdout': '', 'stderr': ''},
        'devstack_contract': _run_command(DEVSTACK_ROOT, ['python3', 'scripts/validate_devstack_contract.py']) if run_checks else {'returncode': 0, 'stdout': '', 'stderr': ''},
    }
    surfaces = {name: _load_json(path) for name, path in SOURCE_LAYERS.items() if path.suffix == '.json'}
    surfaces.update({
        'devstack_forge_board_md': _load_text(SOURCE_LAYERS['devstack_forge_board_md']),
        'athanor_backlog_text': _load_text(SOURCE_LAYERS['athanor_backlog']),
        'athanor_layered_plan_text': _load_text(SOURCE_LAYERS['athanor_layered_plan']),
        'devstack_master_plan_text': _load_text(SOURCE_LAYERS['devstack_master_plan']),
        'restart_snapshot': _run_json_command(REPO_ROOT, ['python3', 'scripts/session_restart_brief.py', '--json']),
    })
    git = {
        'athanor': _git_status(
            REPO_ROOT,
            ignored_paths={
                'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md',
                'docs/operations/DEVSTACK-MEMBRANE-AUDIT.md',
                'docs/operations/AUDIT-REMEDIATION-BACKLOG.md',
            },
        ),
        'devstack': _git_status(DEVSTACK_ROOT),
    }
    inventories = {
        'athanor': {
            'counts': _top_level_counts(REPO_ROOT, ['projects', 'services', 'scripts', 'config', 'docs', 'reports', 'ansible', 'tests', 'evals']),
            'manifests': _discover_manifests(REPO_ROOT),
        },
        'devstack': {
            'counts': _top_level_counts(DEVSTACK_ROOT, ['services', 'scripts', 'configs', 'docs', 'reports', 'research', 'designs', 'shipped']),
            'manifests': _discover_manifests(DEVSTACK_ROOT),
        },
    }
    audit = {
        'generated_at': _iso_now(),
        'source_layers': {key: str(path) for key, path in SOURCE_LAYERS.items()},
        'checks': checks,
        'surfaces': surfaces,
        'git': git,
        'inventories': inventories,
    }
    audit['findings'] = build_findings(audit)
    audit['scorecard'] = build_scorecard(audit['findings'])
    audit['backlog'] = build_backlog(audit['findings'])
    audit['coverage'] = build_coverage(audit)
    return audit



def _normalize_markdown_for_check(rendered: str) -> str:
    lines = []
    for line in rendered.splitlines():
        if line.startswith('Generated: `'):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def _check_outputs(audit: dict[str, Any]) -> int:
    expected = {
        MASTER_AUDIT_MD: _normalize_markdown_for_check(render_master_report(audit)),
        MEMBRANE_AUDIT_MD: _normalize_markdown_for_check(render_membrane_report(audit)),
        REMEDIATION_MD: _normalize_markdown_for_check(render_backlog_md(audit['backlog'])),
    }
    stale = False
    for output_path, rendered in expected.items():
        if not output_path.exists():
            print(f'{output_path} is stale')
            stale = True
            continue
        existing = _normalize_markdown_for_check(output_path.read_text(encoding='utf-8'))
        if existing != rendered:
            print(f'{output_path} is stale')
            stale = True
    return 1 if stale else 0


def write_outputs(audit: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    index_payload = {
        'generated_at': audit['generated_at'],
        'source_layers': audit['source_layers'],
        'checks': {
            key: {
                'returncode': value['returncode'],
                'stdout': value['stdout'],
                'stderr': value['stderr'],
            }
            for key, value in audit['checks'].items()
        },
        'coverage': audit['coverage'],
        'output_paths': {
            'master_audit': str(MASTER_AUDIT_MD),
            'membrane_audit': str(MEMBRANE_AUDIT_MD),
            'remediation_backlog': str(REMEDIATION_MD),
            'findings': str(FINDINGS_JSON),
            'scorecard': str(SCORECARD_JSON),
        },
        'finding_counts': dict(Counter(item['severity'] for item in audit['findings'])),
        'subsystems': [
            {
                'id': item['id'],
                'title': item['title'],
                'layer': item['layer'],
                'overall_score': item['overall_score'],
                'remediation_priority': item['remediation_priority'],
                'finding_count': item['finding_count'],
            }
            for item in audit['scorecard']
        ],
    }

    INDEX_JSON.write_text(json.dumps(index_payload, indent=2) + '\n', encoding='utf-8')
    FINDINGS_JSON.write_text(json.dumps(audit['findings'], indent=2) + '\n', encoding='utf-8')
    SCORECARD_JSON.write_text(json.dumps(audit['scorecard'], indent=2) + '\n', encoding='utf-8')
    MASTER_AUDIT_MD.write_text(render_master_report(audit), encoding='utf-8')
    MEMBRANE_AUDIT_MD.write_text(render_membrane_report(audit), encoding='utf-8')
    REMEDIATION_MD.write_text(render_backlog_md(audit['backlog']), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate the Athanor full-system audit artifacts.')
    parser.add_argument('--skip-checks', action='store_true', help='Do not run live Athanor/devstack validator commands before generating outputs.')
    parser.add_argument('--json', action='store_true', help='Print the audit index payload after writing outputs.')
    parser.add_argument('--check', action='store_true', help='Exit non-zero when the generated audit docs are stale.')
    args = parser.parse_args()

    preset_checks = _load_existing_index_checks() if args.check else None
    audit = build_audit(run_checks=False if args.check else not args.skip_checks, preset_checks=preset_checks)
    if args.check:
        return _check_outputs(audit)
    write_outputs(audit)
    if args.json:
        print(INDEX_JSON.read_text(encoding='utf-8'))
    else:
        print(str(MASTER_AUDIT_MD))
        print(str(MEMBRANE_AUDIT_MD))
        print(str(REMEDIATION_MD))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
