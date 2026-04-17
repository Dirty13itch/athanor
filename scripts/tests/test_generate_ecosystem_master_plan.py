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


def test_build_payload_covers_full_ecosystem_scope() -> None:
    module = _load_module(
        f'generate_ecosystem_master_plan_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_ecosystem_master_plan.py',
    )

    fake_json = {
        'finish_scoreboard': {
            'closure_state': 'repo_safe_complete',
            'active_claim_task_id': 'workstream:validation-and-publication',
            'next_deferred_family_id': 'deferred_family:reference-and-archive-prune',
        },
        'steady_state_status': {
            'operator_mode': 'steady_state_monitoring',
            'intervention_label': 'No action needed',
            'current_work': {'task_title': 'Validation and Publication', 'task_id': 'workstream:validation-and-publication'},
            'next_up': {'task_title': 'Reference and Archive Prune', 'task_id': 'deferred_family:reference-and-archive-prune'},
        },
        'runtime_packet_inbox': {'packet_count': 0},
        'ralph_latest': {
            'automation_feedback_summary': {
                'recent_dispatch_outcomes': [
                    {
                        'completed_at': '1776377956.911315',
                        'task_title': 'Validation and Publication',
                        'lane': 'ralph_loop',
                        'summary': 'Ralph selected validation and publication.',
                    }
                ]
            }
        },
        'platform_topology': {
            'nodes': [
                {'id': 'dev', 'role': 'ops_center', 'ip': '192.168.1.189'},
                {'id': 'foundry', 'role': 'heavy_compute', 'ip': '192.168.1.244'},
                {'id': 'workshop', 'role': 'creative_compute', 'ip': '192.168.1.225'},
                {'id': 'vault', 'role': 'storage_observability', 'ip': '192.168.1.203'},
                {'id': 'desk', 'role': 'workstation', 'ip': '192.168.1.50'},
            ]
        },
        'operator_surface_registry': {
            'surfaces': [
                {
                    'navigation_role': 'front_door',
                    'label': 'Athanor Command Center',
                    'canonical_url': 'https://athanor.local/',
                    'runtime_url': 'http://dev.athanor.local:3001/',
                }
            ]
        },
        'project_packet_registry': {'projects': [{'id': 'athanor'}, {'id': 'field-inspect'}]},
        'reconciliation_source_registry': {
            'sources': [
                {'id': 'field-inspect-root', 'ecosystem_role': 'tenant'},
                {'id': 'athanor-devstack-build-root', 'ecosystem_role': 'core'},
            ]
        },
        'provider_usage_evidence': {'captures': [{'provider_id': 'anthropic_api'}]},
        'planned_subscription_evidence': {'captures': [{'provider_id': 'kimi'}]},
        'quota_truth': {'version': '2026-04-16.1'},
        'capacity_telemetry': {'version': '2026-04-16.1'},
        'devstack_forge_board': {
            'top_priority_lane': 'letta-memory-plane',
            'drafting_packet': [
                {
                    'id': 'letta-memory-plane',
                    'title': 'Letta Memory Plane',
                    'priority': 7,
                    'next_action': 'Wire LETTA_API_KEY and run the continuity benchmark.',
                    'packet_path': 'C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md',
                    'landing_repo': 'C:/Athanor',
                    'landing_workspace': 'config/automation-backbone',
                    'workspace_mode': 'repo_worktree',
                },
                {
                    'id': 'agent-governance-toolkit-policy-plane',
                    'title': 'Agent Governance Toolkit Policy Plane',
                    'priority': 8,
                    'next_action': 'Hold AGT below adapter work unless unique value is proven.',
                    'packet_path': 'C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md',
                    'landing_repo': 'C:/Athanor',
                    'landing_workspace': 'config/automation-backbone',
                    'workspace_mode': 'repo_worktree',
                },
                {
                    'id': 'openhands-bounded-worker-lane',
                    'title': 'OpenHands Bounded Worker Lane',
                    'priority': 9,
                    'next_action': 'Expose OpenHands on DESK and run the bounded worker eval.',
                    'packet_path': 'C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md',
                    'landing_repo': 'C:/Athanor',
                    'landing_workspace': 'config/automation-backbone',
                    'workspace_mode': 'repo_worktree',
                },
            ],
            'deferred_operator_inputs': [
                {'id': 'letta-api-key', 'label': 'LETTA_API_KEY', 'next_step': 'Wire it when the Letta pilot is reactivated.'},
                {'id': 'openhands-substrate', 'label': 'OpenHands substrate readiness', 'next_step': 'Repair DESK substrate when the worker lane is reactivated.'},
            ],
        },
        'devstack_master_atlas': {
            'summary': {
                'top_priority_lane': 'letta-memory-plane',
                'turnover_status': 'ready_for_low_touch_execution',
            },
            'turnover_readiness': {
                'autonomous_turnover_status': 'ready_for_low_touch_execution',
                'capacity_harvest_summary': {'admission_state': 'open_harvest_window'},
                'work_economy_status': 'ready',
            },
            'autonomous_queue_summary': {
                'dispatchable_queue_count': 12,
                'governed_dispatch_claim': {
                    'claimed_at': '2026-04-16T22:18:42+00:00',
                    'current_task_title': 'Validation and Publication',
                    'current_lane_family': 'validation_and_checkpoint',
                },
            },
            'readiness_ledger': {
                'records': [
                    {'id': 'creative-identity-pipeline', 'title': 'Creative Identity Pipeline', 'stage': 'adopted'},
                    {
                        'id': 'letta-memory-plane',
                        'title': 'Letta Memory Plane',
                        'stage': 'concept',
                        'blocking_gate': 'continuity-gain-unproven',
                        'missing_proof': ['formal_eval_run'],
                        'runtime_target': 'Athanor memory namespace',
                        'rollback_or_disable_path': 'Disable Letta and fall back to native Athanor memory.',
                        'approval_state': 'operator_review_required_before_adoption',
                    },
                    {
                        'id': 'agent-governance-toolkit-policy-plane',
                        'title': 'Agent Governance Toolkit Policy Plane',
                        'stage': 'concept',
                        'blocking_gate': 'policy-bridge-slice-unproven',
                        'missing_proof': ['formal_eval_run'],
                        'runtime_target': 'Athanor policy bridge',
                        'rollback_or_disable_path': 'Keep governance in native Athanor policy.',
                        'approval_state': 'operator_review_required_before_adoption',
                    },
                    {
                        'id': 'openhands-bounded-worker-lane',
                        'title': 'OpenHands Bounded Worker Lane',
                        'stage': 'concept',
                        'blocking_gate': 'bounded-worker-value-unproven',
                        'missing_proof': ['formal_eval_run'],
                        'runtime_target': 'Athanor bounded worker lane',
                        'rollback_or_disable_path': 'Disable the worker lane and fall back to manual execution.',
                        'approval_state': 'operator_review_required_before_adoption',
                    },
                ]
            },
        },
        'safe_surface_queue': {'items': [{'id': 'one'}, {'id': 'two'}]},
        'safe_surface_state': {'last_outcome': 'idle'},
    }

    def fake_load_json(path):
        stem = path.stem.replace('-', '_').lower()
        parent_key = f"{path.parent.name}_{stem}".lower()
        return fake_json.get(stem, fake_json.get(parent_key, {}))

    module._load_json = fake_load_json

    payload = module.build_payload()

    assert payload['front_door']['canonical_url'] == 'https://athanor.local/'
    assert {domain['id'] for domain in payload['domains']} == {
        'athanor_core_adopted_system',
        'devstack_forge',
        'cluster_and_host_substrate',
        'operator_local_systems',
        'external_providers_and_saas',
        'artifact_and_evidence_systems',
        'tenant_and_product_systems',
        'human_approval_and_decision_gates',
    }
    assert payload['activation_program'][0]['title'] == 'Letta Memory Plane'
    assert payload['operator_model']['front_door_sequence'][0]['surface'].endswith('reports/truth-inventory/steady-state-live.md')
    assert any(edge['type'] == 'hard blocker' for edge in payload['dependency_edges'])
    assert any(edge['type'] == 'operator input' for edge in payload['dependency_edges'])
    assert any('LETTA_API_KEY' in item for item in payload['current_truth']['blocked_by_operator_input'])


def test_rendered_docs_include_required_sections() -> None:
    module = _load_module(
        f'generate_ecosystem_master_plan_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_ecosystem_master_plan.py',
    )

    payload = {
        'generated_at': '2026-04-16T23:30:00+00:00',
        'current_truth': {
            'live': ['Athanor is live.'],
            'proved': ['Devstack is ready.'],
            'adopted': ['Athanor core is adopted.'],
            'local_only': ['Codex control plane is local-only.'],
            'external_only': ['Providers are external.'],
            'blocked_by_operator_input': ['LETTA_API_KEY: wire it on activation.'],
        },
        'domains_by_id': {},
        'activation_program': [
            {
                'order': 1,
                'title': 'Letta Memory Plane',
                'why_now': 'Top lane.',
                'prerequisites': ['LETTA_API_KEY'],
                'proof_surfaces': ['C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md'],
                'acceptance': 'Formal proof is present.',
                'rollback': 'Disable Letta.',
            }
        ],
        'operator_model': {
            'front_door_label': 'Athanor Command Center',
            'front_door_url': 'https://athanor.local/',
            'front_door_sequence': [
                {
                    'order': 1,
                    'surface': '/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md',
                    'purpose': 'Live status.',
                    'use_when': 'Daily.',
                }
            ],
            'attention_levels': [
                {
                    'level': 'No action needed',
                    'meaning': 'Core is green.',
                    'operator_expectation': 'Do nothing.',
                }
            ],
            'intervention_triggers': ['runtime-packet inbox rises above zero'],
            'ambient_rules': ['Do not require raw JSON first.'],
            'deep_proof_surfaces': ['/mnt/c/Athanor/reports/ralph-loop/latest.json'],
            'review_ritual': ['Read steady-state first.'],
        },
        'longer_horizon': [
            {'plane': 'memory plane', 'current_posture': 'Letta next.', 'next_move': 'Prove it.'}
        ],
        'recent_activity': [{'at': '2026-04-16 23:00 UTC', 'title': 'Validation and Publication', 'lane_family': 'ralph_loop', 'summary': 'Recent change.'}],
        'source_layers': {'steady_state_status': '/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json'},
        'queue_summary': {
            'athanor_current_work': 'Validation and Publication',
            'athanor_next_up': 'Reference and Archive Prune',
            'devstack_top_lane': 'Letta Memory Plane',
            'safe_surface_queue_count': 2,
            'safe_surface_last_outcome': 'idle',
        },
        'deferred_operator_inputs': [{'label': 'LETTA_API_KEY', 'next_step': 'Wire it on activation.'}],
        'dependency_edges': [
            {
                'upstream': 'devstack_forge',
                'downstream': 'athanor_core_adopted_system',
                'type': 'hard blocker',
                'status': 'governed',
                'why': 'Promotion boundary.',
                'next_action': 'Use packets.',
            }
        ],
        'node_rows': [{'id': 'dev', 'role': 'ops_center', 'ip': '192.168.1.189'}],
        'project_count': 2,
        'tenant_source_ids': ['field-inspect-root'],
        'concept_lanes': [
            {
                'title': 'Letta Memory Plane',
                'landing_repo': 'C:/Athanor',
                'landing_workspace': 'config/automation-backbone',
                'approval_state': 'operator_review_required_before_adoption',
                'blocking_gate': 'continuity-gain-unproven',
                'next_action': 'Wire LETTA_API_KEY.',
            }
        ],
    }
    minimal_domains = {
        'athanor_core_adopted_system': {
            'id': 'athanor_core_adopted_system',
            'title': 'Athanor core adopted system',
            'owner': 'C:/Athanor',
            'state_class': 'adopted',
            'source_of_truth': ['reports/truth-inventory/steady-state-status.json'],
            'current_state': 'Repo-safe complete.',
            'blockers': [],
            'next_maturity_move': 'Keep steady-state green.',
            'why_in_scope': 'It is the adopted core.',
            'dependencies': ['cluster_and_host_substrate'],
            'failure_mode': 'Operator truth drifts.',
        },
        'devstack_forge': {
            'id': 'devstack_forge',
            'title': 'devstack forge',
            'owner': 'C:/athanor-devstack',
            'state_class': 'proving',
            'source_of_truth': ['C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md'],
            'current_state': 'Top lane Letta.',
            'blockers': ['LETTA_API_KEY'],
            'next_maturity_move': 'Promote bounded lanes.',
            'why_in_scope': 'It owns proving work.',
            'dependencies': ['athanor_core_adopted_system'],
            'failure_mode': 'Shadow authority leaks.',
        },
        'cluster_and_host_substrate': {
            'id': 'cluster_and_host_substrate',
            'title': 'cluster and host substrate',
            'owner': 'cluster',
            'state_class': 'runtime',
            'source_of_truth': ['config/automation-backbone/platform-topology.json'],
            'current_state': 'Five nodes.',
            'blockers': [],
            'next_maturity_move': 'Keep packet-backed runtime truth.',
            'why_in_scope': 'It hosts the system.',
            'dependencies': [],
            'failure_mode': 'Runtime drift.',
        },
        'operator_local_systems': {
            'id': 'operator_local_systems',
            'title': 'operator-local systems',
            'owner': 'Codex',
            'state_class': 'local_only',
            'source_of_truth': ['C:/Codex System Config/STATUS.md'],
            'current_state': 'WSL-first.',
            'blockers': [],
            'next_maturity_move': 'Keep audits current.',
            'why_in_scope': 'It is the local control plane.',
            'dependencies': [],
            'failure_mode': 'Operator blind spots.',
        },
        'external_providers_and_saas': {
            'id': 'external_providers_and_saas',
            'title': 'external providers and SaaS',
            'owner': 'external',
            'state_class': 'external',
            'source_of_truth': ['docs/operations/PROVIDER-CATALOG-REPORT.md'],
            'current_state': 'External provider surface.',
            'blockers': [],
            'next_maturity_move': 'Keep proof current.',
            'why_in_scope': 'Providers affect runtime.',
            'dependencies': [],
            'failure_mode': 'Routing ambiguity.',
        },
        'artifact_and_evidence_systems': {
            'id': 'artifact_and_evidence_systems',
            'title': 'artifact and evidence systems',
            'owner': 'reports',
            'state_class': 'evidence',
            'source_of_truth': ['reports/truth-inventory/latest.json'],
            'current_state': 'Generated evidence.',
            'blockers': [],
            'next_maturity_move': 'Keep reports fresh.',
            'why_in_scope': 'Evidence drives trust.',
            'dependencies': [],
            'failure_mode': 'Stale docs.',
        },
        'tenant_and_product_systems': {
            'id': 'tenant_and_product_systems',
            'title': 'tenant and product systems',
            'owner': 'tenant roots',
            'state_class': 'segregated',
            'source_of_truth': ['docs/operations/ATHANOR-TENANT-QUEUE.md'],
            'current_state': 'Segregated.',
            'blockers': [],
            'next_maturity_move': 'Keep them bounded.',
            'why_in_scope': 'They are part of the ecosystem boundary.',
            'dependencies': [],
            'failure_mode': 'Scope bleed.',
        },
        'human_approval_and_decision_gates': {
            'id': 'human_approval_and_decision_gates',
            'title': 'human approval and decision gates',
            'owner': 'Shaun',
            'state_class': 'approval',
            'source_of_truth': ['reports/truth-inventory/runtime-packet-inbox.json'],
            'current_state': 'Explicit gates only.',
            'blockers': ['LETTA_API_KEY'],
            'next_maturity_move': 'Keep gates explicit.',
            'why_in_scope': 'Approvals gate activations.',
            'dependencies': [],
            'failure_mode': 'Invisible stalls.',
        },
    }
    payload['domains_by_id'] = minimal_domains

    master = module.render_master_plan(payload)
    bible = module.render_system_bible(payload)
    dependency = module.render_dependency_map(payload)
    operator = module.render_operator_model(payload)

    assert '# Athanor Ecosystem Master Plan' in master
    assert '## Current Ecosystem Truth' in master
    assert 'steady-state-live.md' in master
    assert 'Letta Memory Plane' in master
    assert '# Athanor Ecosystem System Bible' in bible
    assert '## Cluster Substrate Inventory' in bible
    assert '# Athanor Ecosystem Dependency Map' in dependency
    assert '## Dependency Edges' in dependency
    assert '# Athanor Operator Model' in operator
    assert '## Front Door Sequence' in operator


def test_normalized_payload_ignores_generated_at() -> None:
    module = _load_module(
        f'generate_ecosystem_master_plan_{uuid.uuid4().hex}',
        SCRIPTS_DIR / 'generate_ecosystem_master_plan.py',
    )

    older = {'generated_at': '2026-04-16T20:00:00+00:00', 'current_truth': {'live': ['x']}}
    newer = {'generated_at': '2026-04-16T21:00:00+00:00', 'current_truth': {'live': ['x']}}

    assert module._normalized_payload(older) == module._normalized_payload(newer)
