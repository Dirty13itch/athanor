#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEVSTACK_ROOT = Path('/mnt/c/athanor-devstack')
CODEX_CONFIG_ROOT = Path('/mnt/c/Codex System Config')
SAFE_SURFACE_ROOT = Path('/mnt/c/Users/Shaun/.codex/control')

MASTER_PLAN_PATH = REPO_ROOT / 'docs' / 'operations' / 'ATHANOR-ECOSYSTEM-MASTER-PLAN.md'
SYSTEM_BIBLE_PATH = REPO_ROOT / 'docs' / 'architecture' / 'ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md'
DEPENDENCY_MAP_PATH = REPO_ROOT / 'docs' / 'operations' / 'ATHANOR-ECOSYSTEM-DEPENDENCY-MAP.md'
OPERATOR_MODEL_PATH = REPO_ROOT / 'docs' / 'operations' / 'ATHANOR-OPERATOR-MODEL.md'
JSON_PATH = REPO_ROOT / 'reports' / 'truth-inventory' / 'ecosystem-master-plan.json'

SOURCE_LAYERS = {
    'athanor_status': REPO_ROOT / 'STATUS.md',
    'athanor_backlog': REPO_ROOT / 'docs' / 'operations' / 'CONTINUOUS-COMPLETION-BACKLOG.md',
    'layered_plan': REPO_ROOT / 'docs' / 'operations' / 'ATHANOR-LAYERED-MASTER-PLAN.md',
    'steady_state_status': REPO_ROOT / 'reports' / 'truth-inventory' / 'steady-state-status.json',
    'finish_scoreboard': REPO_ROOT / 'reports' / 'truth-inventory' / 'finish-scoreboard.json',
    'runtime_packet_inbox': REPO_ROOT / 'reports' / 'truth-inventory' / 'runtime-packet-inbox.json',
    'ralph_latest': REPO_ROOT / 'reports' / 'ralph-loop' / 'latest.json',
    'platform_topology': REPO_ROOT / 'config' / 'automation-backbone' / 'platform-topology.json',
    'operator_surface_registry': REPO_ROOT / 'config' / 'automation-backbone' / 'operator-surface-registry.json',
    'project_packet_registry': REPO_ROOT / 'config' / 'automation-backbone' / 'project-packet-registry.json',
    'reconciliation_source_registry': REPO_ROOT / 'config' / 'automation-backbone' / 'reconciliation-source-registry.json',
    'provider_usage_evidence': REPO_ROOT / 'reports' / 'truth-inventory' / 'provider-usage-evidence.json',
    'planned_subscription_evidence': REPO_ROOT / 'reports' / 'truth-inventory' / 'planned-subscription-evidence.json',
    'quota_truth': REPO_ROOT / 'reports' / 'truth-inventory' / 'quota-truth.json',
    'capacity_telemetry': REPO_ROOT / 'reports' / 'truth-inventory' / 'capacity-telemetry.json',
    'devstack_status': DEVSTACK_ROOT / 'STATUS.md',
    'devstack_master_plan': DEVSTACK_ROOT / 'MASTER-PLAN.md',
    'devstack_forge_board': DEVSTACK_ROOT / 'docs' / 'operations' / 'DEVSTACK-FORGE-BOARD.json',
    'devstack_forge_board_md': DEVSTACK_ROOT / 'docs' / 'operations' / 'DEVSTACK-FORGE-BOARD.md',
    'devstack_master_atlas': DEVSTACK_ROOT / 'reports' / 'master-atlas' / 'latest.json',
    'devstack_master_atlas_md': DEVSTACK_ROOT / 'docs' / 'operations' / 'MASTER-ATLAS-REPORT.md',
    'devstack_lane_registry': DEVSTACK_ROOT / 'configs' / 'devstack-capability-lane-registry.json',
    'codex_status': CODEX_CONFIG_ROOT / 'STATUS.md',
    'codex_project': CODEX_CONFIG_ROOT / 'PROJECT.md',
    'codex_next_steps': CODEX_CONFIG_ROOT / 'docs' / 'CODEX-NEXT-STEPS.md',
    'safe_surface_scope': SAFE_SURFACE_ROOT / 'safe-surface-scope.md',
    'safe_surface_policy': SAFE_SURFACE_ROOT / 'safe-surface-policy.md',
    'safe_surface_queue': SAFE_SURFACE_ROOT / 'safe-surface-queue.json',
    'safe_surface_state': SAFE_SURFACE_ROOT / 'safe-surface-state.json',
}

DOMAIN_ORDER = [
    'athanor_core_adopted_system',
    'devstack_forge',
    'cluster_and_host_substrate',
    'operator_local_systems',
    'external_providers_and_saas',
    'artifact_and_evidence_systems',
    'tenant_and_product_systems',
    'human_approval_and_decision_gates',
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_event_time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        except ValueError:
            return text
    return None


def _node_rows(topology: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for node in _safe_list(topology.get('nodes')):
        if not isinstance(node, dict):
            continue
        rows.append(
            {
                'id': _pick_string(node.get('label'), node.get('id')) or 'unknown',
                'role': _pick_string(node.get('role')) or 'unknown',
                'ip': _pick_string(node.get('default_host'), node.get('ip')) or 'unknown',
            }
        )
    return rows


def _front_door(surface_registry: dict[str, Any]) -> dict[str, str]:
    for surface in _safe_list(surface_registry.get('surfaces')):
        if not isinstance(surface, dict):
            continue
        if surface.get('navigation_role') == 'front_door':
            return {
                'label': _pick_string(surface.get('label')) or 'Athanor Command Center',
                'canonical_url': _pick_string(surface.get('canonical_url')) or 'unknown',
                'runtime_url': _pick_string(surface.get('runtime_url')) or 'unknown',
            }
    canonical = _safe_dict(surface_registry.get('canonical_front_door'))
    return {
        'label': _pick_string(canonical.get('label')) or 'Athanor Command Center',
        'canonical_url': _pick_string(canonical.get('canonical_url')) or 'unknown',
        'runtime_url': _pick_string(canonical.get('runtime_url')) or 'unknown',
    }


def _deferred_operator_inputs(forge_board: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in _safe_list(forge_board.get('deferred_operator_inputs')):
        if not isinstance(item, dict):
            continue
        items.append(
            {
                'id': _pick_string(item.get('id')) or 'unknown',
                'label': _pick_string(item.get('label')) or 'unknown',
                'next_step': _pick_string(item.get('next_step')) or 'No next step recorded.',
            }
        )
    return items


def _concept_lanes(master_atlas: dict[str, Any], forge_board: dict[str, Any]) -> list[dict[str, Any]]:
    records = {
        _pick_string(record.get('capability_id'), record.get('id')): record
        for record in _safe_list(_safe_dict(master_atlas.get('readiness_ledger')).get('records'))
        if isinstance(record, dict) and _pick_string(record.get('capability_id'), record.get('id'))
    }
    lanes: list[dict[str, Any]] = []
    for item in _safe_list(forge_board.get('drafting_packet')):
        if not isinstance(item, dict):
            continue
        lane_id = _pick_string(item.get('id')) or 'unknown'
        record = _safe_dict(records.get(lane_id))
        blockers = [str(blocker).strip() for blocker in _safe_list(record.get('missing_proof')) if str(blocker).strip()]
        blocking_gate = _pick_string(record.get('blocking_gate'))
        if blocking_gate:
            blockers.insert(0, blocking_gate)
        lanes.append(
            {
                'id': lane_id,
                'title': _pick_string(item.get('title'), record.get('label'), record.get('title')) or lane_id,
                'priority': item.get('priority'),
                'next_action': _pick_string(item.get('next_action')) or 'No next action recorded.',
                'packet_path': _pick_string(item.get('packet_path')) or 'unknown',
                'landing_repo': _pick_string(item.get('landing_repo')) or 'C:/Athanor',
                'landing_workspace': _pick_string(item.get('landing_workspace')) or 'unknown',
                'workspace_mode': _pick_string(item.get('workspace_mode')) or 'unknown',
                'blocking_gate': blocking_gate or 'none',
                'blockers': blockers,
                'runtime_target': _pick_string(record.get('runtime_target')) or 'Athanor adopted system',
                'rollback_or_disable_path': _pick_string(record.get('rollback_or_disable_path')) or 'Disable the pilot and fall back to current Athanor behavior.',
                'approval_state': _pick_string(record.get('approval_state')) or 'operator_review_required_before_adoption',
            }
        )
    return sorted(lanes, key=lambda lane: (lane.get('priority') is None, lane.get('priority') or 999))


def _recent_activity(ralph_latest: dict[str, Any], master_atlas: dict[str, Any]) -> list[dict[str, str]]:
    activity: list[dict[str, str]] = []
    claim = _safe_dict(_safe_dict(_safe_dict(master_atlas.get('autonomous_queue_summary')).get('governed_dispatch_claim')))
    if claim:
        activity.append(
            {
                'at': _parse_event_time(claim.get('claimed_at')) or 'unknown',
                'title': _pick_string(claim.get('current_task_title'), claim.get('current_task_id')) or 'unknown',
                'lane_family': _pick_string(claim.get('current_lane_family')) or 'unknown',
                'summary': 'Current governed dispatch claim.',
            }
        )
    feedback = _safe_dict(ralph_latest.get('automation_feedback_summary'))
    for item in _safe_list(feedback.get('recent_dispatch_outcomes'))[:5]:
        if not isinstance(item, dict):
            continue
        activity.append(
            {
                'at': _parse_event_time(item.get('completed_at')) or 'unknown',
                'title': _pick_string(item.get('task_title'), item.get('task_id')) or 'unknown',
                'lane_family': _pick_string(item.get('lane')) or 'unknown',
                'summary': _pick_string(item.get('summary')) or 'No summary available.',
            }
        )
    return activity[:6]


def _tenant_sources(reconciliation_sources: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for source in _safe_list(reconciliation_sources.get('sources')):
        if not isinstance(source, dict):
            continue
        if _pick_string(source.get('ecosystem_role')) != 'tenant':
            continue
        items.append(_pick_string(source.get('id')) or 'unknown')
    return sorted(items)


def build_payload() -> dict[str, Any]:
    finish = _load_json(SOURCE_LAYERS['finish_scoreboard'])
    steady = _load_json(SOURCE_LAYERS['steady_state_status'])
    runtime_inbox = _load_json(SOURCE_LAYERS['runtime_packet_inbox'])
    ralph_latest = _load_json(SOURCE_LAYERS['ralph_latest'])
    topology = _load_json(SOURCE_LAYERS['platform_topology'])
    operator_surface_registry = _load_json(SOURCE_LAYERS['operator_surface_registry'])
    project_registry = _load_json(SOURCE_LAYERS['project_packet_registry'])
    reconciliation_sources = _load_json(SOURCE_LAYERS['reconciliation_source_registry'])
    provider_usage = _load_json(SOURCE_LAYERS['provider_usage_evidence'])
    planned_subscription = _load_json(SOURCE_LAYERS['planned_subscription_evidence'])
    quota_truth = _load_json(SOURCE_LAYERS['quota_truth'])
    capacity_telemetry = _load_json(SOURCE_LAYERS['capacity_telemetry'])
    devstack_forge_board = _load_json(SOURCE_LAYERS['devstack_forge_board'])
    devstack_master_atlas = _load_json(SOURCE_LAYERS['devstack_master_atlas'])
    safe_surface_queue = _load_json(SOURCE_LAYERS['safe_surface_queue'])
    safe_surface_state = _load_json(SOURCE_LAYERS['safe_surface_state'])

    front_door = _front_door(operator_surface_registry)
    deferred_inputs = _deferred_operator_inputs(devstack_forge_board)
    concept_lanes = _concept_lanes(devstack_master_atlas, devstack_forge_board)
    nodes = _node_rows(topology)
    tenant_ids = _tenant_sources(reconciliation_sources)

    readiness_records = _safe_list(_safe_dict(devstack_master_atlas.get('readiness_ledger')).get('records'))
    readiness_counter = Counter(
        _pick_string(record.get('stage')) or 'unknown'
        for record in readiness_records
        if isinstance(record, dict)
    )
    adopted_titles = [
        _pick_string(record.get('label'), record.get('title'), record.get('capability_id'), record.get('id')) or 'unknown'
        for record in readiness_records
        if isinstance(record, dict) and _pick_string(record.get('stage')) == 'adopted'
    ]

    current_work = _safe_dict(steady.get('current_work'))
    next_up = _safe_dict(steady.get('next_up'))
    closure_state = _pick_string(finish.get('closure_state')) or 'unknown'
    current_work_title = _pick_string(current_work.get('task_title'), current_work.get('task_id'), finish.get('active_claim_task_id')) or 'unknown'
    next_up_title = _pick_string(next_up.get('task_title'), next_up.get('task_id'), finish.get('next_deferred_family_id')) or 'unknown'
    operator_mode = _pick_string(steady.get('operator_mode')) or 'unknown'
    intervention_label = _pick_string(steady.get('intervention_label')) or 'unknown'
    runtime_packets = int(runtime_inbox.get('packet_count') or 0)

    atlas_summary = _safe_dict(devstack_master_atlas.get('summary'))
    turnover = _safe_dict(devstack_master_atlas.get('turnover_readiness'))
    queue_summary = _safe_dict(devstack_master_atlas.get('autonomous_queue_summary'))
    safe_queue_items = _safe_list(safe_surface_queue.get('items'))

    current_truth = {
        'live': [
            f"Athanor adopted system is `{closure_state}` with operator mode `{operator_mode}`.",
            f"Current governed work is `{current_work_title}` and the next staged handoff is `{next_up_title}`.",
            f"Runtime packet inbox currently holds `{runtime_packets}` packets.",
            f"The canonical command center is `{front_door['canonical_url']}`.",
        ],
        'proved': [
            f"Devstack turnover status is `{_pick_string(turnover.get('autonomous_turnover_status'), atlas_summary.get('turnover_status')) or 'unknown'}`.",
            f"Devstack top packet-drafting lane is `{_pick_string(devstack_forge_board.get('top_priority_lane'), atlas_summary.get('top_priority_lane')) or 'unknown'}`.",
            f"Atlas tracks `{len(readiness_records)}` capabilities with `{readiness_counter.get('adopted', 0)}` adopted and `{readiness_counter.get('concept', 0)}` concept lanes.",
        ],
        'adopted': [
            f"Athanor core closure is `{closure_state}`.",
            f"Atlas-adopted capability set currently includes `{', '.join(adopted_titles[:6]) if adopted_titles else 'none recorded'}`.",
        ],
        'local_only': [
            'Codex System Config remains the operator-local control plane for machine defaults, worktrees, and rollout audits.',
            f"Safe-surface executive loop currently tracks `{len(safe_queue_items)}` non-Athanor queue items and keeps Athanor-adjacent paths denied by default.",
        ],
        'external_only': [
            f"Provider usage evidence currently records `{len(_safe_list(provider_usage.get('captures')))}` provider capture rows.",
            f"Planned subscription evidence currently records `{len(_safe_list(planned_subscription.get('captures')))}` subscription evidence rows.",
            'External provider auth, billing, and SaaS uptime remain outside Athanor authority even when they affect execution.',
        ],
        'blocked_by_operator_input': [
            f"{item['label']}: {item['next_step']}" for item in deferred_inputs
        ] or ['No explicit operator-input blockers are currently recorded.'],
    }

    domains = [
        {
            'id': 'athanor_core_adopted_system',
            'title': 'Athanor core adopted system',
            'owner': 'C:/Athanor',
            'state_class': 'adopted',
            'source_of_truth': [
                'reports/truth-inventory/steady-state-status.json',
                'reports/truth-inventory/finish-scoreboard.json',
                'reports/ralph-loop/latest.json',
                'docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md',
            ],
            'current_state': f"Core posture is `{closure_state}` with `{operator_mode}`; current governed claim is `{current_work_title}` and the runtime inbox is `{runtime_packets}`.",
            'blockers': [] if runtime_packets == 0 else [f'{runtime_packets} runtime packet(s) remain open.'],
            'next_maturity_move': 'Keep the steady-state control-plane pass green and reopen only on typed debt, packet, or validator evidence.',
            'why_in_scope': 'This is the adopted implementation and operator authority that all other ecosystem layers ultimately support or feed.',
            'dependencies': ['cluster_and_host_substrate', 'external_providers_and_saas', 'artifact_and_evidence_systems', 'human_approval_and_decision_gates'],
            'failure_mode': 'If this layer drifts, the system loses authoritative state, operator visibility, and safe execution ordering.',
        },
        {
            'id': 'devstack_forge',
            'title': 'devstack forge',
            'owner': 'C:/athanor-devstack',
            'state_class': 'proving',
            'source_of_truth': [
                'C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md',
                'C:/athanor-devstack/reports/master-atlas/latest.json',
                'C:/athanor-devstack/MASTER-PLAN.md',
            ],
            'current_state': f"Turnover is `{_pick_string(turnover.get('autonomous_turnover_status'), atlas_summary.get('turnover_status')) or 'unknown'}`, top lane is `{_pick_string(devstack_forge_board.get('top_priority_lane')) or 'unknown'}`, and packet drafting lanes total `{len(concept_lanes)}`.",
            'blockers': [item['label'] for item in deferred_inputs],
            'next_maturity_move': 'Advance the next bounded promotion lane through proof, packet, and Athanor landing surfaces without leaking build truth into runtime truth.',
            'why_in_scope': 'Devstack owns concept, prototype, and proved capability work that directly determines what can graduate into Athanor next.',
            'dependencies': ['athanor_core_adopted_system', 'operator_local_systems', 'external_providers_and_saas', 'human_approval_and_decision_gates'],
            'failure_mode': 'If build truth is stale or overruns its boundary, shadow authority leaks into Athanor and pilot work becomes ambiguous.',
        },
        {
            'id': 'cluster_and_host_substrate',
            'title': 'cluster and host substrate',
            'owner': 'FOUNDRY / WORKSHOP / VAULT / DEV / DESK',
            'state_class': 'runtime',
            'source_of_truth': [
                'config/automation-backbone/platform-topology.json',
                'docs/operations/RUNTIME-OWNERSHIP-REPORT.md',
                'docs/operations/RUNTIME-OWNERSHIP-PACKETS.md',
                'reports/truth-inventory/capacity-telemetry.json',
            ],
            'current_state': f"Topology tracks `{len(nodes)}` nodes; atlas harvest posture is `{_pick_string(_safe_dict(turnover.get('capacity_harvest_summary')).get('admission_state')) or 'unknown'}` and work-economy posture is `{_pick_string(turnover.get('work_economy_status')) or 'unknown'}`.",
            'blockers': ['OpenHands substrate readiness on DESK'] if any(item['id'] == 'openhands-substrate' for item in deferred_inputs) else [],
            'next_maturity_move': 'Keep runtime mutations packet-backed, preserve host-role clarity, and only widen pilot substrate work when a specific activation lane needs it.',
            'why_in_scope': 'Athanor only works if the nodes, runtime ownership, and host-specific constraints are current and governable.',
            'dependencies': ['external_providers_and_saas', 'human_approval_and_decision_gates'],
            'failure_mode': 'Host drift or ambiguous runtime ownership can reopen deployment debt and invalidate operator truth.',
        },
        {
            'id': 'operator_local_systems',
            'title': 'operator-local systems',
            'owner': 'C:/Users/Shaun/.codex and C:/Codex System Config',
            'state_class': 'local_only',
            'source_of_truth': [
                'C:/Codex System Config/STATUS.md',
                'C:/Codex System Config/docs/CODEX-NEXT-STEPS.md',
                'C:/Users/Shaun/.codex/control/safe-surface-scope.md',
                'C:/Users/Shaun/.codex/control/safe-surface-policy.md',
            ],
            'current_state': 'Codex System Config is the machine-level control plane, WSL-first execution is the default, and the safe-surface loop remains explicitly non-Athanor by policy.',
            'blockers': [],
            'next_maturity_move': 'Keep worktree audits, WSL tooling parity, and machine-level control proof current without letting global defaults absorb repo-local truth.',
            'why_in_scope': 'The operator-local layer determines how Shaun sees and drives the system, especially on DESK and in Codex.',
            'dependencies': ['athanor_core_adopted_system', 'devstack_forge'],
            'failure_mode': 'If local control surfaces drift, the user loses visibility and starts operating from stale or split control planes.',
        },
        {
            'id': 'external_providers_and_saas',
            'title': 'external providers and SaaS',
            'owner': 'External APIs, billing systems, and SaaS control planes',
            'state_class': 'external',
            'source_of_truth': [
                'docs/operations/PROVIDER-CATALOG-REPORT.md',
                'reports/truth-inventory/provider-usage-evidence.json',
                'reports/truth-inventory/planned-subscription-evidence.json',
                'reports/truth-inventory/quota-truth.json',
            ],
            'current_state': f"Provider evidence is explicit with `{len(_safe_list(provider_usage.get('captures')))}` usage captures and `{len(_safe_list(planned_subscription.get('captures')))}` planned-subscription captures; optional elasticity maintenance remains externalized rather than core-blocking.",
            'blockers': ['Provider secret repair'] if any(item['id'] == 'provider-secret-repair' for item in deferred_inputs) else [],
            'next_maturity_move': 'Keep provider proof current, rotate or repair keys only when a live lane or pilot actually requires the expanded surface, and avoid treating optional elasticity as core blockage.',
            'why_in_scope': 'Model routing, billing posture, gateway auth, and SaaS observability are external but can still block real work.',
            'dependencies': ['human_approval_and_decision_gates'],
            'failure_mode': 'If provider posture is implicit or stale, routing decisions and pilot readiness become misleading.',
        },
        {
            'id': 'artifact_and_evidence_systems',
            'title': 'artifact and evidence systems',
            'owner': 'Generated reports, docs, local artifacts, and audit traces',
            'state_class': 'evidence',
            'source_of_truth': [
                'docs/operations/STEADY-STATE-STATUS.md',
                'docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md',
                'C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md',
                'reports/truth-inventory/',
            ],
            'current_state': f"Generated evidence covers capacity (`{_pick_string(capacity_telemetry.get('version')) or 'unknown version'}`), quota (`{_pick_string(quota_truth.get('version')) or 'unknown version'}`), audit, steady-state, forge, and atlas surfaces.",
            'blockers': [],
            'next_maturity_move': 'Keep evidence regenerated in canonical order and make stale generated docs a hard trust signal rather than background noise.',
            'why_in_scope': 'The ecosystem depends on reviewable proof, not memory or ad hoc narration.',
            'dependencies': ['athanor_core_adopted_system', 'devstack_forge', 'operator_local_systems'],
            'failure_mode': 'If generated evidence goes stale, operators and agents make decisions from contradictory surfaces.',
        },
        {
            'id': 'tenant_and_product_systems',
            'title': 'tenant and product systems',
            'owner': 'Registry-backed tenant roots and adjacent products',
            'state_class': 'segregated',
            'source_of_truth': [
                'config/automation-backbone/project-packet-registry.json',
                'config/automation-backbone/reconciliation-source-registry.json',
                'docs/operations/ATHANOR-TENANT-QUEUE.md',
                'docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md',
            ],
            'current_state': f"Registry-backed tenant and adjacent roots remain segregated; current tenant source ids include `{', '.join(tenant_ids[:6]) if tenant_ids else 'none recorded'}`.",
            'blockers': [],
            'next_maturity_move': 'Keep tenant lanes visible but non-blocking unless they leak back into Athanor startup, runtime, queue, or operator surfaces.',
            'why_in_scope': 'Adjacent products affect the ecosystem boundary even when they should not block Athanor core operation.',
            'dependencies': ['athanor_core_adopted_system', 'human_approval_and_decision_gates'],
            'failure_mode': 'If tenant roots are not bounded, product work reopens core control-plane ambiguity.',
        },
        {
            'id': 'human_approval_and_decision_gates',
            'title': 'human approval and decision gates',
            'owner': 'Shaun',
            'state_class': 'approval',
            'source_of_truth': [
                'reports/truth-inventory/runtime-packet-inbox.json',
                'C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md',
                'docs/operations/STEADY-STATE-STATUS.md',
            ],
            'current_state': f"Core Athanor does not currently need intervention (`{intervention_label}`), but explicit approval and operator-input gates remain on future activation lanes.",
            'blockers': [item['label'] for item in deferred_inputs],
            'next_maturity_move': 'Keep approvals explicit and lane-specific: only elevate them when a bounded runtime mutation, credential gate, or pilot activation is intentionally being executed.',
            'why_in_scope': 'Some work should remain paused until Shaun explicitly chooses to spend trust, credentials, or runtime mutation budget.',
            'dependencies': ['athanor_core_adopted_system', 'devstack_forge', 'external_providers_and_saas', 'cluster_and_host_substrate'],
            'failure_mode': 'If approval gates are vague, the system either stalls invisibly or mutates live runtime without clear consent.',
        },
    ]
    domains_by_id = {domain['id']: domain for domain in domains}

    dependency_edges = [
        {
            'upstream': 'cluster_and_host_substrate',
            'downstream': 'athanor_core_adopted_system',
            'type': 'runtime input',
            'status': 'healthy',
            'why': 'Athanor runtime truth, service reachability, and host-role ownership depend on the cluster substrate.',
            'next_action': 'Keep runtime mutations packet-backed and host truth current.',
        },
        {
            'upstream': 'external_providers_and_saas',
            'downstream': 'athanor_core_adopted_system',
            'type': 'external dependency',
            'status': 'managed',
            'why': 'Provider auth, billing posture, and external SaaS uptime can degrade routing or pilot breadth.',
            'next_action': 'Treat provider maintenance as explicit follow-on, not ambient assumption.',
        },
        {
            'upstream': 'artifact_and_evidence_systems',
            'downstream': 'athanor_core_adopted_system',
            'type': 'soft blocker',
            'status': 'healthy',
            'why': 'Generated evidence is required to keep operator truth and validator posture coherent.',
            'next_action': 'Refresh generated surfaces in canonical order whenever repo-tracked truth changes.',
        },
        {
            'upstream': 'operator_local_systems',
            'downstream': 'athanor_core_adopted_system',
            'type': 'soft blocker',
            'status': 'healthy',
            'why': 'DESK/Codex-local control surfaces are how Shaun actually sees and operates the system.',
            'next_action': 'Keep WSL-first tool parity and machine-level audits current.',
        },
        {
            'upstream': 'devstack_forge',
            'downstream': 'athanor_core_adopted_system',
            'type': 'hard blocker',
            'status': 'governed',
            'why': 'Capabilities must graduate through packets and Athanor landing surfaces instead of leaking directly from devstack.',
            'next_action': 'Promote only through explicit packets, proof, and adoption surfaces.',
        },
        {
            'upstream': 'human_approval_and_decision_gates',
            'downstream': 'devstack_forge',
            'type': 'operator input',
            'status': 'active',
            'why': 'Future pilot activation depends on explicit operator inputs and approval posture.',
            'next_action': 'Keep pending inputs explicit on the forge board and activation program.',
        },
        {
            'upstream': 'external_providers_and_saas',
            'downstream': 'devstack_forge',
            'type': 'operator input',
            'status': 'active',
            'why': 'Letta and related pilots require real external credentials before proof can progress.',
            'next_action': 'Provide LETTA_API_KEY only when the Letta lane is intentionally activated.',
        },
        {
            'upstream': 'cluster_and_host_substrate',
            'downstream': 'devstack_forge',
            'type': 'runtime input',
            'status': 'active',
            'why': 'OpenHands depends on DESK substrate readiness before the bounded worker lane can run.',
            'next_action': 'Repair DESK substrate only when the OpenHands pilot is intentionally activated.',
        },
        {
            'upstream': 'tenant_and_product_systems',
            'downstream': 'athanor_core_adopted_system',
            'type': 'non-blocking follow-on',
            'status': 'segregated',
            'why': 'Tenant lanes stay visible but should not block Athanor core unless they leak authority back into it.',
            'next_action': 'Keep tenant/product work packeted and segregated.',
        },
        {
            'upstream': 'operator_local_systems',
            'downstream': 'devstack_forge',
            'type': 'soft blocker',
            'status': 'healthy',
            'why': 'The current devstack posture assumes WSL-first Codex execution and worktree-aware tooling.',
            'next_action': 'Keep worktree lanes and Codex platform audits current.',
        },
    ]

    activation_program = [
        {
            'order': 1,
            'lane_id': concept_lanes[0]['id'] if concept_lanes else 'letta-memory-plane',
            'title': concept_lanes[0]['title'] if concept_lanes else 'Letta Memory Plane',
            'why_now': 'It is the top devstack packet-drafting lane and the clearest next memory-plane expansion path.',
            'prerequisites': concept_lanes[0]['blockers'] if concept_lanes else ['LETTA_API_KEY', 'bounded continuity benchmark'],
            'proof_surfaces': [
                concept_lanes[0]['packet_path'] if concept_lanes else 'C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md',
                'C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md',
                'C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md',
            ],
            'acceptance': 'Credential is present, bounded continuity benchmark passes, packet proof is updated, and the Athanor landing surfaces remain explicit and replayable.',
            'rollback': concept_lanes[0]['rollback_or_disable_path'] if concept_lanes else 'Disable the Letta lane and fall back to the current Athanor memory posture.',
        },
        {
            'order': 2,
            'lane_id': concept_lanes[1]['id'] if len(concept_lanes) > 1 else 'agent-governance-toolkit-policy-plane',
            'title': concept_lanes[1]['title'] if len(concept_lanes) > 1 else 'Agent Governance Toolkit Policy Plane',
            'why_now': 'It is the next governance-plane candidate, but it should remain below adapter work until it proves unique value.',
            'prerequisites': concept_lanes[1]['blockers'] if len(concept_lanes) > 1 else ['second protocol-boundary scenario', 'formal eval progression'],
            'proof_surfaces': [
                concept_lanes[1]['packet_path'] if len(concept_lanes) > 1 else 'C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md',
                'C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md',
            ],
            'acceptance': 'A second protocol-boundary scenario demonstrates non-duplicative value, proof artifacts are updated, and a bounded Athanor landing plan exists.',
            'rollback': concept_lanes[1]['rollback_or_disable_path'] if len(concept_lanes) > 1 else 'Do not land a live adapter; keep governance in native Athanor policy.',
        },
        {
            'order': 3,
            'lane_id': concept_lanes[2]['id'] if len(concept_lanes) > 2 else 'openhands-bounded-worker-lane',
            'title': concept_lanes[2]['title'] if len(concept_lanes) > 2 else 'OpenHands Bounded Worker Lane',
            'why_now': 'It is the next worker-plane candidate but remains substrate-blocked until DESK can host the bounded worker path cleanly.',
            'prerequisites': concept_lanes[2]['blockers'] if len(concept_lanes) > 2 else ['OpenHands command on DESK', 'worker env wiring', 'bounded worker eval'],
            'proof_surfaces': [
                concept_lanes[2]['packet_path'] if len(concept_lanes) > 2 else 'C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md',
                'C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md',
            ],
            'acceptance': 'DESK substrate is ready, the bounded-worker eval passes, and the lane can be disabled cleanly if it misbehaves.',
            'rollback': concept_lanes[2]['rollback_or_disable_path'] if len(concept_lanes) > 2 else 'Disable the worker lane and fall back to the existing manual/operator workflow.',
        },
    ]

    front_door_sequence = [
        {
            'order': 1,
            'surface': '/mnt/c/Athanor/docs/operations/STEADY-STATE-STATUS.md',
            'purpose': 'Current adopted-system status, current work, next up, and whether Shaun needs to care.',
            'use_when': 'First read for daily operation.',
        },
        {
            'order': 2,
            'surface': '/mnt/c/Athanor/docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md',
            'purpose': 'Cross-system execution spine covering Athanor, devstack, substrate, operator-local, providers, and approval gates.',
            'use_when': 'You need the full ecosystem picture without dropping into raw JSON.',
        },
        {
            'order': 3,
            'surface': '/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md',
            'purpose': 'Current build/proving queue and explicit deferred operator inputs.',
            'use_when': 'You want to know what the next promotion or activation lane is.',
        },
        {
            'order': 4,
            'surface': '/mnt/c/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md',
            'purpose': 'Detailed proving-readiness, turnover posture, and pilot evidence.',
            'use_when': 'You need readiness detail before a pilot or promotion move.',
        },
        {
            'order': 5,
            'surface': '/mnt/c/Codex System Config/docs/CORE-ROLLOUT-STATUS.md',
            'purpose': 'Operator-local Codex control-plane health across the mandatory rollout set.',
            'use_when': 'Local workstation or Codex control-plane posture may be the blocker.',
        },
        {
            'order': 6,
            'surface': '/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json',
            'purpose': 'Machine proof for closure state and repo-safe debt counts.',
            'use_when': 'You need proof rather than summary.',
        },
        {
            'order': 7,
            'surface': '/mnt/c/Athanor/reports/ralph-loop/latest.json',
            'purpose': 'Machine proof for the current claim, queue state, and Ralph loop posture.',
            'use_when': 'You are debugging the control loop itself.',
        },
    ]

    operator_model = {
        'front_door_url': front_door['canonical_url'],
        'front_door_label': front_door['label'],
        'front_door_sequence': front_door_sequence,
        'attention_levels': [
            {
                'level': 'No action needed',
                'meaning': 'Athanor core is green and the system can continue without intervention.',
                'operator_expectation': 'Read the front door only; no action unless you are intentionally activating a new lane.',
            },
            {
                'level': 'Review recommended',
                'meaning': 'Something reopened or drifted, but it is not yet a hard stop.',
                'operator_expectation': 'Review the current work and next handoff before approving new breadth.',
            },
            {
                'level': 'Approval required',
                'meaning': 'A packet, credential gate, or bounded runtime mutation explicitly needs Shaun.',
                'operator_expectation': 'Approve or deny the specific gate; do not treat it as generic system uncertainty.',
            },
            {
                'level': 'System attention required',
                'meaning': 'A typed stop, validator break, or runtime breakage surfaced.',
                'operator_expectation': 'Pause expansion, work the active fault, then regenerate truth surfaces.',
            },
        ],
        'intervention_triggers': [
            'runtime-packet inbox rises above zero',
            'finish-scoreboard leaves repo_safe_complete or typed_brakes_only',
            'Ralph surfaces a typed stop state',
            'provider or host posture invalidates an active lane',
            'a deferred operator input is intentionally being activated',
        ],
        'ambient_rules': [
            'Current work, next up, and whether Shaun is needed must be visible without reading raw JSON.',
            'Outside-system blockers must surface on the operator-facing docs, not only in machine artifacts.',
            'Recent changes should be summarized from Ralph or atlas activity rather than requiring forensic digging.',
        ],
        'deep_proof_surfaces': [
            '/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json',
            '/mnt/c/Athanor/reports/ralph-loop/latest.json',
            '/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json',
            '/mnt/c/athanor-devstack/reports/master-atlas/latest.json',
        ],
        'review_ritual': [
            'Read steady-state status first.',
            'Read the ecosystem master plan when work spans more than Athanor core.',
            'Check the forge board before treating a devstack lane as next.',
            'Use atlas and machine JSON only when you need proof or to resolve contradiction.',
        ],
    }

    longer_horizon = [
        {
            'plane': 'memory plane',
            'current_posture': 'Letta remains the next memory-plane candidate but is still operator-input gated.',
            'next_move': 'Prove bounded continuity gain with explicit pruning and replayability.',
        },
        {
            'plane': 'governance plane',
            'current_posture': 'Native Athanor governance remains primary; AGT is still a proving-only candidate.',
            'next_move': 'Reopen only if a second protocol-boundary scenario proves non-duplicative value.',
        },
        {
            'plane': 'worker plane',
            'current_posture': 'Bounded worker expansion is still substrate-blocked on DESK.',
            'next_move': 'Repair OpenHands substrate only when the lane is intentionally activated.',
        },
        {
            'plane': 'creative/runtime maturity',
            'current_posture': 'Cluster substrate and harvest posture are healthy enough to support broader proving work.',
            'next_move': 'Protect runtime ownership clarity while widening only packet-backed lanes.',
        },
        {
            'plane': 'provider/routing maturity',
            'current_posture': 'Provider evidence is explicit; optional elasticity maintenance remains separated from core health.',
            'next_move': 'Keep billing and auth posture explicit and avoid hidden provider assumptions.',
        },
        {
            'plane': 'tenant/product governance',
            'current_posture': 'Tenant and product roots are visible and segregated rather than merged into Athanor core.',
            'next_move': 'Advance only bounded extractions or packet-backed reopenings.',
        },
        {
            'plane': 'cluster/hardware evolution',
            'current_posture': 'Node roles and scheduler posture are explicit enough for current operation.',
            'next_move': 'Change hardware or runtime posture only through topology truth, runtime packets, and explicit proof.',
        },
    ]

    return {
        'generated_at': _iso_now(),
        'source_layers': {name: str(path) for name, path in SOURCE_LAYERS.items()},
        'front_door': front_door,
        'current_truth': current_truth,
        'domains': domains,
        'domains_by_id': domains_by_id,
        'concept_lanes': concept_lanes,
        'activation_program': activation_program,
        'dependency_edges': dependency_edges,
        'operator_model': operator_model,
        'longer_horizon': longer_horizon,
        'recent_activity': _recent_activity(ralph_latest, devstack_master_atlas),
        'node_rows': nodes,
        'project_count': len(_safe_list(project_registry.get('projects'))),
        'tenant_source_ids': tenant_ids,
        'deferred_operator_inputs': deferred_inputs,
        'queue_summary': {
            'athanor_current_work': current_work_title,
            'athanor_next_up': next_up_title,
            'devstack_top_lane': _pick_string(devstack_forge_board.get('top_priority_lane'), atlas_summary.get('top_priority_lane')) or 'unknown',
            'devstack_dispatchable_queue_count': queue_summary.get('dispatchable_queue_count'),
            'safe_surface_queue_count': len(safe_queue_items),
            'safe_surface_last_outcome': _pick_string(safe_surface_state.get('last_outcome')) or 'unknown',
        },
    }


def _render_domain_sources(domain: dict[str, Any]) -> list[str]:
    return [f"- `{item}`" for item in domain.get('source_of_truth', [])]


def render_master_plan(payload: dict[str, Any]) -> str:
    current_truth = _safe_dict(payload.get('current_truth'))
    domains = [payload['domains_by_id'][domain_id] for domain_id in DOMAIN_ORDER]
    activation_program = _safe_list(payload.get('activation_program'))
    recent_activity = _safe_list(payload.get('recent_activity'))
    lines = [
        '# Athanor Ecosystem Master Plan',
        '',
        'Do not edit manually.',
        '',
        f"Generated: `{payload.get('generated_at', 'unknown')}`",
        '',
        '## Current Ecosystem Truth',
        '',
        '### Live',
        '',
    ]
    lines.extend(f"- {item}" for item in current_truth.get('live', []))
    lines.extend(['', '### Proved', ''])
    lines.extend(f"- {item}" for item in current_truth.get('proved', []))
    lines.extend(['', '### Adopted', ''])
    lines.extend(f"- {item}" for item in current_truth.get('adopted', []))
    lines.extend(['', '### Local-Only', ''])
    lines.extend(f"- {item}" for item in current_truth.get('local_only', []))
    lines.extend(['', '### External-Only', ''])
    lines.extend(f"- {item}" for item in current_truth.get('external_only', []))
    lines.extend(['', '### Blocked By Human or Operator Input', ''])
    lines.extend(f"- {item}" for item in current_truth.get('blocked_by_operator_input', []))

    lines.extend([
        '',
        '## Ownership Model',
        '',
        '| Domain | Owner | State Class | Current State | Blockers | Next Maturity Move |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for domain in domains:
        blockers = ', '.join(domain.get('blockers') or ['none'])
        lines.append(
            f"| `{domain['title']}` | `{domain['owner']}` | `{domain['state_class']}` | {domain['current_state']} | {blockers} | {domain['next_maturity_move']} |"
        )

    queue_summary = _safe_dict(payload.get('queue_summary'))
    lines.extend([
        '',
        '## Active Execution Lanes',
        '',
        f"- Running now: Athanor is on `{queue_summary.get('athanor_current_work', 'unknown')}`.",
        f"- Next in Athanor: `{queue_summary.get('athanor_next_up', 'unknown')}`.",
        f"- Next in devstack: `{queue_summary.get('devstack_top_lane', 'unknown')}`.",
        f"- Safe-surface queue count: `{queue_summary.get('safe_surface_queue_count', 'unknown')}` with last outcome `{queue_summary.get('safe_surface_last_outcome', 'unknown')}`.",
        '',
        '### Recent Activity',
        '',
    ])
    if recent_activity:
        for item in recent_activity:
            lines.append(
                f"- `{item.get('at', 'unknown')}` | `{item.get('title', 'unknown')}` | `{item.get('lane_family', 'unknown')}` | {item.get('summary', 'No summary available.')}"
            )
    else:
        lines.append('- No recent cross-system activity was materialized.')

    lines.extend([
        '',
        '## Activation Program',
        '',
        '| Order | Lane | Why Now | Prerequisites | Proof Surfaces | Acceptance | Rollback |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for item in activation_program:
        prerequisites = ', '.join(item.get('prerequisites') or ['none'])
        proofs = ', '.join(f"`{surface}`" for surface in item.get('proof_surfaces', []))
        lines.append(
            f"| `{item['order']}` | `{item['title']}` | {item['why_now']} | {prerequisites} | {proofs} | {item['acceptance']} | {item['rollback']} |"
        )

    operator_model = _safe_dict(payload.get('operator_model'))
    lines.extend([
        '',
        '## Operator Model',
        '',
        f"- Front door: `{operator_model.get('front_door_label', 'unknown')}` at `{operator_model.get('front_door_url', 'unknown')}`.",
        '- First read: `docs/operations/STEADY-STATE-STATUS.md`.',
        '- Cross-system read: `docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md`.',
        '- Build/proving read: `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` and `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`.',
        '- Deep proof: drop to the JSON artifacts only when summary surfaces contradict or you need exact evidence.',
        '',
        '## Longer-Horizon Ecosystem Maturation',
        '',
    ])
    for item in _safe_list(payload.get('longer_horizon')):
        lines.append(
            f"- `{item.get('plane', 'unknown')}`: {item.get('current_posture', 'unknown')} Next move: {item.get('next_move', 'unknown')}"
        )

    lines.extend([
        '',
        '## Source Layers',
        '',
    ])
    for name, path in payload.get('source_layers', {}).items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append('')
    return '\n'.join(lines)


def render_system_bible(payload: dict[str, Any]) -> str:
    domains = [payload['domains_by_id'][domain_id] for domain_id in DOMAIN_ORDER]
    lines = [
        '# Athanor Ecosystem System Bible',
        '',
        'Do not edit manually.',
        '',
        f"Generated: `{payload.get('generated_at', 'unknown')}`",
        '',
        '## Scope',
        '',
        'This appendix is exhaustive by subsystem. It exists to make every ecosystem domain explicit without overloading the daily execution spine.',
        '',
        '## Cluster Substrate Inventory',
        '',
        '| Node | Role | IP |',
        '| --- | --- | --- |',
    ]
    for row in _safe_list(payload.get('node_rows')):
        lines.append(f"| `{row.get('id', 'unknown')}` | `{row.get('role', 'unknown')}` | `{row.get('ip', 'unknown')}` |")

    for domain in domains:
        lines.extend([
            '',
            f"## {domain['title']}",
            '',
            f"- Owner: `{domain['owner']}`",
            f"- State class: `{domain['state_class']}`",
            f"- Why it is part of the ecosystem: {domain['why_in_scope']}",
            '- Source of truth:',
        ])
        lines.extend(_render_domain_sources(domain))
        lines.extend([
            f"- Current state: {domain['current_state']}",
            f"- Blockers: {', '.join(domain.get('blockers') or ['none'])}",
            f"- Failure mode: {domain['failure_mode']}",
            f"- Next maturity move: {domain['next_maturity_move']}",
            f"- Dependencies: {', '.join(domain.get('dependencies') or ['none'])}",
        ])

    lines.extend([
        '',
        '## Activation Lane Appendix',
        '',
        '| Lane | Landing Repo | Landing Workspace | Approval State | Blocking Gate | Next Action |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for lane in _safe_list(payload.get('concept_lanes')):
        lines.append(
            f"| `{lane['title']}` | `{lane['landing_repo']}` | `{lane['landing_workspace']}` | `{lane['approval_state']}` | `{lane['blocking_gate']}` | {lane['next_action']} |"
        )

    lines.extend([
        '',
        '## Tenant and Product Boundary',
        '',
        f"- Project registry count: `{payload.get('project_count', 'unknown')}`",
        f"- Tenant source ids: `{', '.join(payload.get('tenant_source_ids', [])) or 'none recorded'}`",
        '- Rule: tenant and adjacent product systems remain visible but non-blocking unless they leak authority back into Athanor startup, queue, runtime, or operator surfaces.',
        '',
    ])
    return '\n'.join(lines)


def render_dependency_map(payload: dict[str, Any]) -> str:
    lines = [
        '# Athanor Ecosystem Dependency Map',
        '',
        'Do not edit manually.',
        '',
        f"Generated: `{payload.get('generated_at', 'unknown')}`",
        '',
        '## Current Sequence',
        '',
    ]
    for item in _safe_list(payload.get('activation_program')):
        lines.append(f"{item.get('order', '?')}. `{item.get('title', 'unknown')}`")

    deferred_inputs = _safe_list(payload.get('deferred_operator_inputs'))
    lines.extend([
        '',
        '## Typed Blockers',
        '',
        '### Operator Input',
        '',
    ])
    if deferred_inputs:
        for item in deferred_inputs:
            lines.append(f"- `{item.get('label', 'unknown')}`: {item.get('next_step', 'No next step recorded.')}")
    else:
        lines.append('- None.')

    lines.extend([
        '',
        '### Runtime Input',
        '',
        '- `OpenHands substrate readiness`: DESK substrate must be ready before the bounded worker lane activates.',
        '- `Runtime mutation packets`: any future live runtime change still goes through explicit packet-backed execution.',
        '',
        '### External Dependency',
        '',
        '- Provider auth, billing posture, and SaaS health remain external even when they influence active lanes.',
        '',
        '### Soft Blocker',
        '',
        '- Stale generated reports reduce trust immediately even when the system is still nominally up.',
        '- AGT stays below adapter work until it proves unique value over native Athanor policy.',
        '',
        '### Non-Blocking Follow-On',
        '',
        '- Tenant and product lanes remain segregated unless they leak back into Athanor core authority.',
        '- Safe-surface work remains active but explicitly non-Athanor.',
        '',
        '## Dependency Edges',
        '',
        '| Upstream | Downstream | Type | Status | Why It Matters | Next Action |',
        '| --- | --- | --- | --- | --- | --- |',
    ])
    for edge in _safe_list(payload.get('dependency_edges')):
        lines.append(
            f"| `{edge['upstream']}` | `{edge['downstream']}` | `{edge['type']}` | `{edge['status']}` | {edge['why']} | {edge['next_action']} |"
        )

    lines.extend([
        '',
        '## Evidence Paths',
        '',
        '- `/mnt/c/Athanor/docs/operations/STEADY-STATE-STATUS.md`',
        '- `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`',
        '- `/mnt/c/Athanor/reports/ralph-loop/latest.json`',
        '- `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`',
        '- `/mnt/c/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`',
        '- `/mnt/c/Codex System Config/docs/CORE-ROLLOUT-STATUS.md`',
        '',
    ])
    return '\n'.join(lines)


def render_operator_model(payload: dict[str, Any]) -> str:
    operator_model = _safe_dict(payload.get('operator_model'))
    lines = [
        '# Athanor Operator Model',
        '',
        'Do not edit manually.',
        '',
        f"Generated: `{payload.get('generated_at', 'unknown')}`",
        '',
        '## Front Door Sequence',
        '',
        '| Order | Surface | Purpose | Use When |',
        '| --- | --- | --- | --- |',
    ]
    for item in _safe_list(operator_model.get('front_door_sequence')):
        lines.append(
            f"| `{item.get('order', '?')}` | `{item.get('surface', 'unknown')}` | {item.get('purpose', 'unknown')} | {item.get('use_when', 'unknown')} |"
        )

    lines.extend([
        '',
        '## Attention Levels',
        '',
        '| Level | Meaning | Operator Expectation |',
        '| --- | --- | --- |',
    ])
    for item in _safe_list(operator_model.get('attention_levels')):
        lines.append(
            f"| `{item.get('level', 'unknown')}` | {item.get('meaning', 'unknown')} | {item.get('operator_expectation', 'unknown')} |"
        )

    lines.extend([
        '',
        '## Intervention Triggers',
        '',
    ])
    lines.extend(f"- {item}" for item in operator_model.get('intervention_triggers', []))

    lines.extend([
        '',
        '## Ambient Rules',
        '',
    ])
    lines.extend(f"- {item}" for item in operator_model.get('ambient_rules', []))

    lines.extend([
        '',
        '## Deep Proof Surfaces',
        '',
    ])
    lines.extend(f"- `{item}`" for item in operator_model.get('deep_proof_surfaces', []))

    lines.extend([
        '',
        '## Review Ritual',
        '',
    ])
    lines.extend(f"- {item}" for item in operator_model.get('review_ritual', []))
    lines.append('')
    return '\n'.join(lines)


def _json_render(payload: dict[str, Any]) -> str:
    serializable = dict(payload)
    serializable.pop('domains_by_id', None)
    return json.dumps(serializable, indent=2, sort_keys=True) + '\n'


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.pop('generated_at', None)
    normalized.pop('domains_by_id', None)
    return normalized


def _load_existing_json_payload() -> dict[str, Any] | None:
    if not JSON_PATH.exists():
        return None
    try:
        loaded = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate the Athanor ecosystem master planning surfaces.')
    parser.add_argument('--json', action='store_true', help='Print the payload after writing artifacts.')
    parser.add_argument('--check', action='store_true', help='Exit non-zero when generated planning artifacts are stale.')
    args = parser.parse_args()

    payload = build_payload()
    existing_payload = _load_existing_json_payload()
    if existing_payload and _normalized_payload(existing_payload) == _normalized_payload(payload):
        payload['generated_at'] = str(existing_payload.get('generated_at') or payload['generated_at'])

    rendered = {
        MASTER_PLAN_PATH: render_master_plan(payload),
        SYSTEM_BIBLE_PATH: render_system_bible(payload),
        DEPENDENCY_MAP_PATH: render_dependency_map(payload),
        OPERATOR_MODEL_PATH: render_operator_model(payload),
    }
    rendered_json = _json_render(payload)

    if args.check:
        stale = False
        existing_payload = _load_existing_json_payload()
        if _normalized_payload(existing_payload or {}) != _normalized_payload(payload):
            print(f'{JSON_PATH} is stale')
            stale = True
        for path, content in rendered.items():
            existing = path.read_text(encoding='utf-8') if path.exists() else ''
            if existing != content:
                print(f'{path} is stale')
                stale = True
        return 1 if stale else 0

    for path in rendered:
        path.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    if (JSON_PATH.read_text(encoding='utf-8') if JSON_PATH.exists() else '') != rendered_json:
        JSON_PATH.write_text(rendered_json, encoding='utf-8')
    for path, content in rendered.items():
        if (path.read_text(encoding='utf-8') if path.exists() else '') != content:
            path.write_text(content, encoding='utf-8')

    if args.json:
        print(json.dumps(_normalized_payload(payload), indent=2, sort_keys=True))
    else:
        for path in (MASTER_PLAN_PATH, SYSTEM_BIBLE_PATH, DEPENDENCY_MAP_PATH, OPERATOR_MODEL_PATH, JSON_PATH):
            print(str(path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
