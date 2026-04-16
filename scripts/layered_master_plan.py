from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / 'config' / 'automation-backbone'
DOCS_DIR = REPO_ROOT / 'docs' / 'operations'
REPORT_DIR = REPO_ROOT / 'reports' / 'truth-inventory'
DEVSTACK_ROOT = Path('/mnt/c/athanor-devstack')
CODEX_ROOT = Path('/mnt/c/Codex System Config')

SURFACE_OWNER_MATRIX_JSON_PATH = REPORT_DIR / 'surface-owner-matrix.json'
PUBLICATION_PROVENANCE_JSON_PATH = REPORT_DIR / 'publication-provenance-latest.json'

REQUIRED_LEASE_CLASS_IDS = {
    'read_only_inspection',
    'build_truth_mutation',
    'generated_truth_regeneration',
    'packet_and_registry_mutation',
    'tenant_repo_mutation',
    'runtime_packet_execution',
    'live_runtime_mutation',
    'operator_local_maintenance',
}
REQUIRED_OPERATOR_MODE_IDS = {'at_desk', 'away', 'low_energy', 'incident_mode', 'deep_build'}
REQUIRED_DATA_HANDLING_PROFILE_IDS = {
    'sovereign_adult',
    'sovereign_private',
    'regulated_health',
    'tax_financial',
    'business_confidential',
    'general_private',
    'cloud_safe',
}
REQUIRED_EXECUTION_MODE_IDS = {
    'active_program_managed',
    'governed_in_repo_project',
    'light_tenant_operator_managed',
    'incubating_tenant',
    'standalone_external_monitored',
    'shared_module_candidate',
    'operator_tooling_reference',
    'lineage_reference',
    'archive_only',
}
REQUIRED_CONTENT_CLASSES = {
    'startup_doctrine',
    'live_execution',
    'build_promotion',
    'ecosystem_governance',
    'operator_control',
    'strategic_reference',
    'archive_reference',
}
REQUIRED_LAYER_IDS = {
    'startup_doctrine',
    'live_execution',
    'build_promotion',
    'ecosystem_governance',
    'operator_control',
    'strategic_reference',
    'archive_reference',
}
REQUIRED_OWNER_MATRIX_PATHS = {
    'README.md',
    'AGENTS.md',
    'PROJECT.md',
    'STATUS.md',
    'docs/CODEX-NEXT-STEPS.md',
    'docs/MASTER-PLAN.md',
    'docs/operations/ATHANOR-OPERATING-SYSTEM.md',
    'docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md',
    'docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md',
    'docs/operations/ATHANOR-SHARED-EXTRACTION-QUEUE.md',
    'docs/operations/ATHANOR-TENANT-QUEUE.md',
    'docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md',
    'docs/operations/SURFACE-OWNER-MATRIX.md',
    'docs/operations/PUBLICATION-PROVENANCE-REPORT.md',
}
REQUIRED_SURFACE_FIELDS = {
    'layer',
    'authority_plane',
    'volatility',
    'generated',
    'generator',
    'validator',
    'allowed_content_class',
    'downstream_consumers',
    'deprecation_state',
    'replacement_surface',
}
REQUIRED_PUBLICATION_SLICE_FIELDS = {
    'included_packet_ids',
    'included_capability_ids',
    'validator_run_set',
    'generated_artifacts',
    'git_commit_range',
    'publication_artifact_refs',
    'working_tree_path_hints',
    'published_at',
    'rollback_reference',
}
REQUIRED_PUBLICATION_DEFERRED_FAMILY_FIELDS = {
    'title',
    'disposition',
    'scope',
    'owner_workstreams',
    'path_hints',
    'execution_rank',
    'execution_class',
    'next_action',
    'success_condition',
}
ALLOWED_PUBLICATION_DEFERRED_DISPOSITIONS = {
    'deferred_out_of_sequence',
    'archive_or_reference',
    'tenant_surface',
    'operator_tooling',
    'runtime_follow_on',
    'audit_artifact',
}
ALLOWED_PUBLICATION_DEFERRED_EXECUTION_CLASSES = {
    'cash_now',
    'bounded_follow_on',
    'program_slice',
    'tenant_lane',
}
REQUIRED_WORKSTREAM_BINDING_IDS = {
    'dispatch-and-work-economy-closure',
    'capacity-and-harvest-truth',
    'validation-and-publication',
    'provider-and-secret-remediation',
    'startup-docs-and-prune',
}
BINDING_FIELDS = {
    'execution_root',
    'branch_or_lane_ref',
    'worktree_path',
    'linked_packet_id',
    'linked_publication_slice_id',
    'lease_class_id',
}

REQUIRED_ANCHOR_CONTRACT_IDS = {
    'commitment_record',
    'counterparty_record',
    'promise_deadline_record',
    'followthrough_state_record',
    'deliverable_acceptance_record',
    'renegotiation_record',
    'externalization_gate_record',
    'assumption_register',
    'inference_boundary_record',
    'belief_revision_policy',
    'evidence_conflict_record',
    'supersession_record',
    'specialist_gate_class',
    'required_reviewer_role',
    'expert_routing_policy',
    'review_evidence_ref',
    'entity_boundary_class',
    'account_surface_class',
    'counterparty_sensitivity_class',
    'party_registry',
    'canonical_vocabulary_registry',
    'term_alias_record',
    'forbidden_alias_record',
    'portable_context_bundle',
    'session_handoff_bundle',
    'control_plane_ingest_bundle',
    'export_bundle_record',
    'interop_contract_record',
    'provider_exit_packet',
    'server_card_contract',
    'well_known_metadata_record',
    'session_resumption_policy',
    'task_retry_policy',
    'task_result_expiry_policy',
    'task_retention_class',
    'telemetry_semconv_profile',
    'telemetry_stability_pin_policy',
    'trace_context_propagation_policy',
    'mcp_trace_meta_contract',
    'compatibility_alias_record',
    'compatibility_alias_expiry',
    'compatibility_alias_owner',
    'compatibility_alias_removal_gate',
    'architecture_freeze_policy',
    'rewrite_budget_policy',
    'canon_change_gate',
}
REQUIRED_COMMITMENT_OUTPUT_CLASSES = {'draft', 'proposal', 'commitment', 'delivery', 'closed_with_proof', 'renegotiated', 'cancelled'}
REQUIRED_COMMITMENT_FIELDS = {'output_classes', 'followthrough_states', 'externalization_gate_classes', 'commitment_classes', 'required_external_item_fields', 'contracts'}
REQUIRED_CLAIM_TYPES = {'observed', 'derived', 'inferred', 'assumed', 'superseded'}
REQUIRED_ASSUMPTION_FIELDS = {'claim_types', 'supersession_precedence', 'required_claim_fields', 'contracts'}
REQUIRED_SPECIALIST_FIELDS = {'reviewer_roles', 'gate_classes', 'routing_policies', 'required_review_artifact_fields', 'contracts'}
REQUIRED_PARTY_BOUNDARY_FIELDS = {'entity_boundary_classes', 'account_surface_classes', 'counterparty_sensitivity_classes', 'party_registry_schema', 'required_project_fields', 'contracts'}
REQUIRED_CANONICAL_VOCAB_TERMS = {'adopted_truth', 'runtime_state_truth', 'data_knowledge_truth', 'operator_local_truth', 'strategy_only_truth', 'draft', 'proposal', 'commitment', 'delivery', 'closed_with_proof', 'observed', 'derived', 'inferred', 'assumed', 'superseded', 'obligation_commitment_compliance'}
REQUIRED_PROTOCOL_INTEROP_FIELDS = {'preferred_protocols', 'protocol_boundary_classes', 'server_card_contract', 'well_known_metadata_record', 'session_resumption_policies', 'task_retry_policies', 'task_result_expiry_policies', 'task_retention_classes', 'portable_bundle_classes', 'telemetry_semconv_profiles', 'trace_context_policies', 'mcp_trace_meta_contract', 'contracts'}
REQUIRED_COMPATIBILITY_FIELDS = {'alias_scope_classes', 'aliases', 'contracts'}
REQUIRED_ARCHITECTURE_FREEZE_FIELDS = {'architecture_freeze_policy', 'rewrite_budget_policy', 'canon_change_gate', 'contracts'}
REQUIRED_PROJECT_BOUNDARY_FIELDS = {'entity_boundary_class', 'account_surface_class', 'counterparty_sensitivity_class'}
REQUIRED_DATA_HANDLING_BOUNDARY_FIELDS = {'default_entity_boundary_class', 'default_account_surface_class', 'default_counterparty_sensitivity_class'}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _source_generated_at(path: Path, payload: dict[str, Any]) -> str:
    raw = payload.get('updated_at') or payload.get('generated_at')
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        '| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join('---' for _ in headers) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(row) + ' |')
    return lines


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    normalized = str(raw).replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _artifact_status(path_str: str) -> str:
    path = Path(path_str.replace('C:/', '/mnt/c/')) if path_str.startswith('C:/') else REPO_ROOT / path_str
    return 'present' if path.exists() else 'missing'


def build_surface_owner_matrix_bundle() -> dict[str, Any]:
    registry_path = CONFIG_DIR / 'docs-lifecycle-registry.json'
    registry = load_json(registry_path)
    docs = [dict(item) for item in registry.get('documents', []) if isinstance(item, dict)]
    records: list[dict[str, Any]] = []
    for doc in sorted(docs, key=lambda item: str(item.get('path') or '')):
        records.append(
            {
                'path': str(doc.get('path') or ''),
                'class': str(doc.get('class') or ''),
                'owner': str(doc.get('owner') or ''),
                'layer': str(doc.get('layer') or ''),
                'authority_plane': str(doc.get('authority_plane') or ''),
                'volatility': str(doc.get('volatility') or ''),
                'generated': bool(doc.get('generated')),
                'generator': doc.get('generator'),
                'validator': doc.get('validator'),
                'allowed_content_class': str(doc.get('allowed_content_class') or ''),
                'downstream_consumers': list(doc.get('downstream_consumers') or []),
                'deprecation_state': str(doc.get('deprecation_state') or ''),
                'replacement_surface': doc.get('replacement_surface'),
            }
        )
    return {
        'generated_at': _source_generated_at(registry_path, registry),
        'source_of_truth': 'config/automation-backbone/docs-lifecycle-registry.json',
        'version': str(registry.get('version') or ''),
        'status': str(registry.get('status') or ''),
        'summary': {
            'total_documents': len(records),
            'layer_counts': dict(Counter(record['layer'] or 'unspecified' for record in records)),
            'content_class_counts': dict(Counter(record['allowed_content_class'] or 'unspecified' for record in records)),
            'generated_count': sum(1 for record in records if record['generated']),
        },
        'records': records,
    }


def render_surface_owner_matrix_report() -> str:
    bundle = build_surface_owner_matrix_bundle()
    records = bundle['records']
    lines = [
        '# Surface Owner Matrix',
        '',
        'Generated from `config/automation-backbone/docs-lifecycle-registry.json` by `scripts/generate_truth_inventory_reports.py`.',
        'Do not edit manually.',
        '',
        '## Summary',
        '',
        f"- Registry version: `{bundle['version']}`",
        f"- Total tracked surfaces: `{bundle['summary']['total_documents']}`",
        f"- Generated surfaces: `{bundle['summary']['generated_count']}`",
        '',
        '## Layer Counts',
        '',
        *_render_table(
            ['Layer', 'Count'],
            [[f"`{layer}`", str(count)] for layer, count in sorted(bundle['summary']['layer_counts'].items())],
        ),
        '',
        '## Top-entry and Plan Surfaces',
        '',
        *_render_table(
            ['Path', 'Layer', 'Authority', 'Volatility', 'Content class', 'Generated', 'Validator'],
            [
                [
                    f"`{record['path']}`",
                    f"`{record['layer'] or 'unspecified'}`",
                    f"`{record['authority_plane'] or 'unspecified'}`",
                    f"`{record['volatility'] or 'unspecified'}`",
                    f"`{record['allowed_content_class'] or 'unspecified'}`",
                    'yes' if record['generated'] else 'no',
                    f"`{record['validator'] or 'unset'}`",
                ]
                for record in records
                if record['path'] in REQUIRED_OWNER_MATRIX_PATHS
            ],
        ),
        '',
    ]
    return '\n'.join(lines)


def build_publication_provenance_bundle() -> dict[str, Any]:
    completion_path = CONFIG_DIR / 'completion-program-registry.json'
    completion = load_json(completion_path)
    publication = dict(completion.get('publication_slices') or {})
    slices = [dict(entry) for entry in publication.get('slices', []) if isinstance(entry, dict)]
    ready_count = sum(1 for entry in slices if str(entry.get('status') or '') == 'ready_for_checkpoint')
    debt_policy = dict(completion.get('publication_debt_policy') or {})
    return {
        'generated_at': _source_generated_at(completion_path, completion),
        'source_of_truth': 'config/automation-backbone/completion-program-registry.json',
        'version': str(completion.get('version') or ''),
        'status': str(completion.get('status') or ''),
        'sequence_id': str(publication.get('active_sequence_id') or ''),
        'owner_workstream_id': str(publication.get('owner_workstream_id') or ''),
        'checkpoint_id': str(publication.get('checkpoint_id') or ''),
        'publication_debt_policy': debt_policy,
        'summary': {
            'total_slices': len(slices),
            'ready_for_checkpoint': ready_count,
            'blocking_threshold': int(debt_policy.get('ready_for_checkpoint_blocking_threshold') or 0),
            'blocking_debt': ready_count >= int(debt_policy.get('ready_for_checkpoint_blocking_threshold') or 0),
        },
        'slices': slices,
    }


def render_publication_provenance_report() -> str:
    bundle = build_publication_provenance_bundle()
    lines = [
        '# Publication Provenance Report',
        '',
        'Generated from `config/automation-backbone/completion-program-registry.json` by `scripts/generate_truth_inventory_reports.py`.',
        'Do not edit manually.',
        '',
        '## Summary',
        '',
        f"- Completion registry version: `{bundle['version']}`",
        f"- Active sequence: `{bundle['sequence_id']}`",
        f"- Owner workstream: `{bundle['owner_workstream_id']}`",
        f"- Checkpoint id: `{bundle['checkpoint_id']}`",
        f"- Ready-for-checkpoint slices: `{bundle['summary']['ready_for_checkpoint']}`",
        f"- Blocking debt posture: `{bundle['summary']['blocking_debt']}`",
        '',
        '## Slices',
        '',
        *_render_table(
            ['Slice', 'Status', 'Publication artifacts', 'Packets', 'Capabilities', 'Validators', 'Generated artifacts', 'Rollback'],
            [
                [
                    f"`{entry.get('id')}`",
                    f"`{entry.get('status')}`",
                    ', '.join(f"`{item}`" for item in entry.get('publication_artifact_refs', [])) or 'none',
                    ', '.join(f"`{item}`" for item in entry.get('included_packet_ids', [])) or 'none',
                    ', '.join(f"`{item}`" for item in entry.get('included_capability_ids', [])) or 'none',
                    ', '.join(f"`{item}`" for item in entry.get('validator_run_set', [])) or 'none',
                    ', '.join(f"`{item}`" for item in entry.get('generated_artifacts', [])) or 'none',
                    f"`{entry.get('rollback_reference')}`" if entry.get('rollback_reference') else 'unset',
                ]
                for entry in bundle['slices']
            ],
        ),
        '',
    ]
    return '\n'.join(lines)


def build_publication_debt_summary(completion_program: dict[str, Any]) -> dict[str, Any]:
    publication = dict(completion_program.get('publication_slices') or {})
    slices = [dict(entry) for entry in publication.get('slices', []) if isinstance(entry, dict)]
    debt_policy = dict(completion_program.get('publication_debt_policy') or {})
    ready_count = sum(1 for entry in slices if str(entry.get('status') or '') == 'ready_for_checkpoint')
    next_slice_entry = next((entry for entry in slices if str(entry.get('status') or '') != 'published'), {})
    next_slice = str(next_slice_entry.get('id') or '') or None
    threshold = int(debt_policy.get('ready_for_checkpoint_blocking_threshold') or 0)
    return {
        'sequence_id': str(publication.get('active_sequence_id') or ''),
        'ready_for_checkpoint': ready_count,
        'total': len(slices),
        'blocking_threshold': threshold,
        'blocking_debt': ready_count >= threshold if threshold else False,
        'escalation_after_days': int(debt_policy.get('escalation_after_days') or 0),
        'blocking_after_days': int(debt_policy.get('blocking_after_days') or 0),
        'blocking_workstream_id': str(debt_policy.get('blocking_workstream_id') or ''),
        'next_checkpoint_slice_id': next_slice,
        'next_checkpoint_slice_title': str(next_slice_entry.get('title') or '') or None,
        'next_checkpoint_slice_status': str(next_slice_entry.get('status') or '') or None,
    }


def build_recovery_drill_summary() -> dict[str, Any]:
    completion_path = CONFIG_DIR / 'completion-program-registry.json'
    completion = load_json(completion_path)
    governance = load_json(CONFIG_DIR / 'governance-drill-registry.json')
    registry_drills = {str(item.get('drill_id') or ''): dict(item) for item in governance.get('drills', []) if isinstance(item, dict)}
    records: list[dict[str, Any]] = []
    for drill in completion.get('recovery_drills', []):
        drill_id = str(drill.get('drill_id') or '')
        artifact_path = str(drill.get('artifact_path') or '')
        resolved = Path(artifact_path.replace('C:/', '/mnt/c/')) if artifact_path.startswith('C:/') else REPO_ROOT / artifact_path
        last_run_at = None
        status = 'missing'
        if resolved.exists():
            if resolved.suffix == '.json':
                try:
                    payload = load_json(resolved)
                    last_run_at = payload.get('trigger_time') or payload.get('generated_at')
                    status = str(payload.get('status') or 'present')
                except Exception:
                    status = 'unreadable'
            else:
                status = 'present'
                last_run_at = datetime.fromtimestamp(resolved.stat().st_mtime, tz=timezone.utc).isoformat()
        cadence = str(drill.get('next_due_rule') or '')
        last_dt = _parse_dt(last_run_at)
        next_due_at = None
        if last_dt and cadence in {'monthly', 'monthly_review'}:
            next_due_at = (last_dt + timedelta(days=30)).isoformat()
        elif last_dt and cadence == 'weekly_review':
            next_due_at = (last_dt + timedelta(days=7)).isoformat()
        records.append(
            {
                'drill_id': drill_id,
                'artifact_path': artifact_path,
                'registry_runbook_id': registry_drills.get(drill_id, {}).get('runbook_id'),
                'status': status,
                'last_run_at': last_run_at,
                'next_due_at': next_due_at,
                'evidence_present': resolved.exists(),
            }
        )
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_of_truth': 'config/automation-backbone/completion-program-registry.json + config/automation-backbone/governance-drill-registry.json',
        'records': records,
        'due_count': sum(1 for record in records if record.get('next_due_at') and _parse_dt(record['next_due_at']) and _parse_dt(record['next_due_at']) <= datetime.now(timezone.utc)),
    }


def validate_layered_master_plan_contract() -> list[str]:
    errors: list[str] = []
    docs = load_json(CONFIG_DIR / 'docs-lifecycle-registry.json')
    lease_policy = load_json(CONFIG_DIR / 'execution-lease-policy.json')
    operator_modes = load_json(CONFIG_DIR / 'operator-mode-policy.json')
    data_policy = load_json(CONFIG_DIR / 'data-handling-policy.json')
    retention = load_json(CONFIG_DIR / 'retention-policy-registry.json')
    completion_path = CONFIG_DIR / 'completion-program-registry.json'
    completion = load_json(completion_path)
    projects = load_json(CONFIG_DIR / 'project-packet-registry.json')
    capabilities = load_json(CONFIG_DIR / 'capability-adoption-registry.json')
    governance = load_json(CONFIG_DIR / 'governance-drill-registry.json')
    contract_registry = load_json(CONFIG_DIR / 'contract-registry.json')
    commitment_governance = load_json(CONFIG_DIR / 'commitment-governance.json')
    assumption_governance = load_json(CONFIG_DIR / 'assumption-governance.json')
    specialist_review = load_json(CONFIG_DIR / 'specialist-review-gates.json')
    party_boundaries = load_json(CONFIG_DIR / 'party-boundary-registry.json')
    canonical_vocabulary = load_json(CONFIG_DIR / 'canonical-vocabulary-registry.json')
    protocol_interop = load_json(CONFIG_DIR / 'protocol-interop-registry.json')
    compatibility_aliases = load_json(CONFIG_DIR / 'compatibility-alias-policy.json')
    architecture_freeze = load_json(CONFIG_DIR / 'architecture-freeze-policy.json')

    layer_ids = {str(item.get('id') or '') for item in docs.get('layers', []) if isinstance(item, dict)}
    if layer_ids != REQUIRED_LAYER_IDS:
        errors.append('docs-lifecycle-registry.json layers must match the layered master-plan contract')
    content_classes = {str(item) for item in docs.get('allowed_content_classes', [])}
    if content_classes != REQUIRED_CONTENT_CLASSES:
        errors.append('docs-lifecycle-registry.json allowed_content_classes must match the layered master-plan contract')

    docs_by_path = {str(item.get('path') or ''): dict(item) for item in docs.get('documents', []) if isinstance(item, dict)}
    missing_owner_matrix = sorted(path for path in REQUIRED_OWNER_MATRIX_PATHS if path not in docs_by_path)
    if missing_owner_matrix:
        errors.append('docs-lifecycle-registry.json is missing owner-matrix surfaces: ' + ', '.join(missing_owner_matrix))
    for path in REQUIRED_OWNER_MATRIX_PATHS & docs_by_path.keys():
        document = docs_by_path[path]
        missing_fields = sorted(field for field in REQUIRED_SURFACE_FIELDS if field not in document)
        if missing_fields:
            errors.append(f'docs-lifecycle-registry.json surface {path} is missing fields: ' + ', '.join(missing_fields))
        elif str(document.get('allowed_content_class') or '') not in REQUIRED_CONTENT_CLASSES:
            errors.append(f'docs-lifecycle-registry.json surface {path} has invalid allowed_content_class')

    lease_entries = [dict(item) for item in lease_policy.get('lease_classes', []) if isinstance(item, dict)]
    if {str(item.get('lease_class_id') or '') for item in lease_entries} != REQUIRED_LEASE_CLASS_IDS:
        errors.append('execution-lease-policy.json lease_class_id set is incomplete or mismatched')
    for lease in lease_entries:
        missing = sorted(field for field in {'lease_class_id', 'allowed_authority_planes', 'allowed_mutation_classes', 'approval_band_default', 'allowed_targets', 'allowed_runtime_scopes', 'allowed_repo_scopes', 'allowed_data_handling_profiles', 'allowed_operator_modes', 'requires_packet_linkage', 'requires_publication_linkage', 'requires_worktree_binding', 'max_duration', 'escalation_path'} if field not in lease)
        if missing:
            errors.append(f"execution-lease-policy.json lease {lease.get('lease_class_id')} is missing fields: {', '.join(missing)}")

    mode_entries = [dict(item) for item in operator_modes.get('modes', []) if isinstance(item, dict)]
    if {str(item.get('id') or '') for item in mode_entries} != REQUIRED_OPERATOR_MODE_IDS:
        errors.append('operator-mode-policy.json mode ids must match the layered master-plan contract')
    for mode in mode_entries:
        missing = sorted(field for field in {'allowed_lease_classes', 'allowed_mutation_classes', 'autonomy_ceiling', 'notification_posture', 'pilot_eligibility', 'publication_expectation', 'runtime_mutation_policy', 'cloud_elasticity_policy', 'worktree_policy'} if field not in mode)
        if missing:
            errors.append(f"operator-mode-policy.json mode {mode.get('id')} is missing fields: {', '.join(missing)}")

    retention_ids = {str(item.get('retention_policy_id') or '') for item in retention.get('policies', []) if isinstance(item, dict)}
    profile_entries = [dict(item) for item in data_policy.get('profiles', []) if isinstance(item, dict)]
    if {str(item.get('profile_id') or '') for item in profile_entries} != REQUIRED_DATA_HANDLING_PROFILE_IDS:
        errors.append('data-handling-policy.json profile ids must match the layered master-plan contract')
    for profile in profile_entries:
        missing = sorted(field for field in {'allowed_model_classes', 'allowed_provider_families', 'allowed_storage_roots', 'allowed_log_classes', 'allowed_export_targets', 'allowed_runtime_surfaces', 'retention_policy_id', 'secret_handling_contract'} if field not in profile)
        if missing:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} is missing fields: {', '.join(missing)}")
        if str(profile.get('retention_policy_id') or '') not in retention_ids:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} references unknown retention policy")

    execution_modes = {str(item.get('id') or '') for item in projects.get('execution_modes', []) if isinstance(item, dict)}
    if execution_modes != REQUIRED_EXECUTION_MODE_IDS:
        errors.append('project-packet-registry.json execution_modes must match the layered master-plan contract')
    for project in projects.get('projects', []):
        if not isinstance(project, dict):
            continue
        if str(project.get('execution_mode') or '') not in execution_modes:
            errors.append(f"project-packet-registry.json project {project.get('id')} has invalid execution_mode")
        if str(project.get('data_handling_profile_id') or '') not in REQUIRED_DATA_HANDLING_PROFILE_IDS:
            errors.append(f"project-packet-registry.json project {project.get('id')} has invalid data_handling_profile_id")

    for capability in capabilities.get('capabilities', []):
        if not isinstance(capability, dict):
            continue
        if str(capability.get('data_handling_profile_id') or '') not in REQUIRED_DATA_HANDLING_PROFILE_IDS:
            errors.append(f"capability-adoption-registry.json capability {capability.get('id')} has invalid data_handling_profile_id")

    for field in {'cross_layer_arbitration', 'state_transition_contracts', 'automation_anti_spin_policy', 'publication_debt_policy', 'budget_guardrails', 'recovery_drills', 'workstream_execution_bindings'}:
        if field not in completion:
            errors.append(f'completion-program-registry.json is missing {field}')
    bindings = dict(completion.get('workstream_execution_bindings') or {})
    missing_bindings = sorted(item for item in REQUIRED_WORKSTREAM_BINDING_IDS if item not in bindings)
    if missing_bindings:
        errors.append('completion-program-registry.json workstream_execution_bindings missing: ' + ', '.join(missing_bindings))
    for workstream_id, binding in bindings.items():
        missing = sorted(field for field in BINDING_FIELDS if field not in binding)
        if missing:
            errors.append(f'completion-program-registry.json binding {workstream_id} is missing fields: ' + ', '.join(missing))
        if binding.get('lease_class_id') not in REQUIRED_LEASE_CLASS_IDS:
            errors.append(f'completion-program-registry.json binding {workstream_id} has invalid lease_class_id')

    publication = dict(completion.get('publication_slices') or {})
    for slice_entry in publication.get('slices', []):
        if not isinstance(slice_entry, dict):
            continue
        missing = sorted(field for field in REQUIRED_PUBLICATION_SLICE_FIELDS if field not in slice_entry)
        if missing:
            errors.append(f"completion-program-registry.json publication slice {slice_entry.get('id')} is missing fields: {', '.join(missing)}")
            continue
        for list_field in ('publication_artifact_refs', 'generated_artifacts', 'validator_run_set', 'working_tree_path_hints'):
            values = slice_entry.get(list_field, [])
            if not isinstance(values, list) or not all(str(item).strip() for item in values):
                errors.append(
                    f"completion-program-registry.json publication slice {slice_entry.get('id')} has invalid {list_field}; expected a non-empty string list"
                )
            elif list_field in {'publication_artifact_refs', 'working_tree_path_hints'} and not values:
                errors.append(
                    f"completion-program-registry.json publication slice {slice_entry.get('id')} must declare {list_field}"
                )

    deferred_families = publication.get('deferred_families', [])
    if not isinstance(deferred_families, list) or not deferred_families:
        errors.append('completion-program-registry.json publication_slices.deferred_families must be a non-empty list')
    else:
        seen_deferred_ids: set[str] = set()
        for family in deferred_families:
            if not isinstance(family, dict):
                errors.append('completion-program-registry.json publication_slices.deferred_families must contain only objects')
                continue
            family_id = str(family.get('id') or '').strip()
            if not family_id:
                errors.append('completion-program-registry.json publication_slices.deferred_families contains an entry without id')
                continue
            if family_id in seen_deferred_ids:
                errors.append(f'completion-program-registry.json publication_slices.deferred_families contains duplicate id {family_id}')
            seen_deferred_ids.add(family_id)
            missing = sorted(field for field in REQUIRED_PUBLICATION_DEFERRED_FAMILY_FIELDS if field not in family)
            if missing:
                errors.append(f"completion-program-registry.json publication deferred family {family_id} is missing fields: {', '.join(missing)}")
                continue
            if str(family.get('disposition') or '') not in ALLOWED_PUBLICATION_DEFERRED_DISPOSITIONS:
                errors.append(f"completion-program-registry.json publication deferred family {family_id} has invalid disposition")
            if int(family.get('execution_rank') or 0) <= 0:
                errors.append(f"completion-program-registry.json publication deferred family {family_id} must declare a positive execution_rank")
            if str(family.get('execution_class') or '') not in ALLOWED_PUBLICATION_DEFERRED_EXECUTION_CLASSES:
                errors.append(f"completion-program-registry.json publication deferred family {family_id} has invalid execution_class")
            owner_workstreams = family.get('owner_workstreams', [])
            if not isinstance(owner_workstreams, list) or not owner_workstreams or not all(str(item).strip() for item in owner_workstreams):
                errors.append(f"completion-program-registry.json publication deferred family {family_id} owner_workstreams must be a non-empty string list")
            path_hints = family.get('path_hints', [])
            if not isinstance(path_hints, list) or not path_hints or not all(str(item).strip() for item in path_hints):
                errors.append(f"completion-program-registry.json publication deferred family {family_id} path_hints must be a non-empty string list")

    governance_ids = {str(item.get('drill_id') or '') for item in governance.get('drills', []) if isinstance(item, dict)}
    for drill in completion.get('recovery_drills', []):
        if not isinstance(drill, dict):
            continue
        drill_id = str(drill.get('drill_id') or '')
        artifact_path = str(drill.get('artifact_path') or '')
        if drill_id in governance_ids:
            continue
        if not artifact_path:
            errors.append(f'completion-program-registry.json recovery drill {drill_id} is missing artifact_path')

    contract_ids = {
        str(item.get('id') or '').strip()
        for item in contract_registry.get('contracts', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    missing_anchor_contracts = sorted(REQUIRED_ANCHOR_CONTRACT_IDS - contract_ids)
    if missing_anchor_contracts:
        errors.append('contract-registry.json is missing required vAnchor contracts: ' + ', '.join(missing_anchor_contracts))

    missing_commitment_fields = sorted(field for field in REQUIRED_COMMITMENT_FIELDS if field not in commitment_governance)
    if missing_commitment_fields:
        errors.append('commitment-governance.json is missing fields: ' + ', '.join(missing_commitment_fields))
    output_classes = {str(item) for item in commitment_governance.get('output_classes', [])}
    if output_classes != REQUIRED_COMMITMENT_OUTPUT_CLASSES:
        errors.append('commitment-governance.json output_classes must match the vAnchor contract')
    commitment_contracts = {str(item) for item in commitment_governance.get('contracts', [])}
    if not commitment_contracts.issubset(REQUIRED_ANCHOR_CONTRACT_IDS):
        errors.append('commitment-governance.json contracts must use registered vAnchor contract ids')

    missing_assumption_fields = sorted(field for field in REQUIRED_ASSUMPTION_FIELDS if field not in assumption_governance)
    if missing_assumption_fields:
        errors.append('assumption-governance.json is missing fields: ' + ', '.join(missing_assumption_fields))
    claim_types = {
        str(item.get('id') or '').strip()
        for item in assumption_governance.get('claim_types', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    if claim_types != REQUIRED_CLAIM_TYPES:
        errors.append('assumption-governance.json claim_types must match the vAnchor contract')

    missing_specialist_fields = sorted(field for field in REQUIRED_SPECIALIST_FIELDS if field not in specialist_review)
    if missing_specialist_fields:
        errors.append('specialist-review-gates.json is missing fields: ' + ', '.join(missing_specialist_fields))
    gate_ids = {
        str(item.get('id') or '').strip()
        for item in specialist_review.get('gate_classes', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    if not gate_ids:
        errors.append('specialist-review-gates.json must declare at least one gate class')

    missing_party_fields = sorted(field for field in REQUIRED_PARTY_BOUNDARY_FIELDS if field not in party_boundaries)
    if missing_party_fields:
        errors.append('party-boundary-registry.json is missing fields: ' + ', '.join(missing_party_fields))
    entity_boundary_ids = {
        str(item.get('id') or '').strip()
        for item in party_boundaries.get('entity_boundary_classes', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    account_surface_ids = {
        str(item.get('id') or '').strip()
        for item in party_boundaries.get('account_surface_classes', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    counterparty_sensitivity_ids = {
        str(item.get('id') or '').strip()
        for item in party_boundaries.get('counterparty_sensitivity_classes', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    for profile in profile_entries:
        missing = sorted(field for field in REQUIRED_DATA_HANDLING_BOUNDARY_FIELDS if field not in profile)
        if missing:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} is missing boundary fields: {', '.join(missing)}")
        if str(profile.get('default_entity_boundary_class') or '') not in entity_boundary_ids:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} has invalid default_entity_boundary_class")
        if str(profile.get('default_account_surface_class') or '') not in account_surface_ids:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} has invalid default_account_surface_class")
        if str(profile.get('default_counterparty_sensitivity_class') or '') not in counterparty_sensitivity_ids:
            errors.append(f"data-handling-policy.json profile {profile.get('profile_id')} has invalid default_counterparty_sensitivity_class")
    for project in projects.get('projects', []):
        if not isinstance(project, dict):
            continue
        missing = sorted(field for field in REQUIRED_PROJECT_BOUNDARY_FIELDS if field not in project)
        if missing:
            errors.append(f"project-packet-registry.json project {project.get('id')} is missing boundary fields: {', '.join(missing)}")
        if str(project.get('entity_boundary_class') or '') not in entity_boundary_ids:
            errors.append(f"project-packet-registry.json project {project.get('id')} has invalid entity_boundary_class")
        if str(project.get('account_surface_class') or '') not in account_surface_ids:
            errors.append(f"project-packet-registry.json project {project.get('id')} has invalid account_surface_class")
        if str(project.get('counterparty_sensitivity_class') or '') not in counterparty_sensitivity_ids:
            errors.append(f"project-packet-registry.json project {project.get('id')} has invalid counterparty_sensitivity_class")

    missing_vocab_terms = REQUIRED_CANONICAL_VOCAB_TERMS - {
        str(item.get('canonical_term_id') or '').strip()
        for item in canonical_vocabulary.get('canonical_terms', [])
        if isinstance(item, dict) and str(item.get('canonical_term_id') or '').strip()
    }
    if missing_vocab_terms:
        errors.append('canonical-vocabulary-registry.json is missing canonical terms: ' + ', '.join(sorted(missing_vocab_terms)))

    missing_protocol_fields = sorted(field for field in REQUIRED_PROTOCOL_INTEROP_FIELDS if field not in protocol_interop)
    if missing_protocol_fields:
        errors.append('protocol-interop-registry.json is missing fields: ' + ', '.join(missing_protocol_fields))
    protocol_contracts = {str(item) for item in protocol_interop.get('contracts', [])}
    if not protocol_contracts.issubset(REQUIRED_ANCHOR_CONTRACT_IDS):
        errors.append('protocol-interop-registry.json contracts must use registered vAnchor contract ids')
    if not protocol_interop.get('telemetry_semconv_profiles'):
        errors.append('protocol-interop-registry.json must declare telemetry_semconv_profiles')

    missing_compatibility_fields = sorted(field for field in REQUIRED_COMPATIBILITY_FIELDS if field not in compatibility_aliases)
    if missing_compatibility_fields:
        errors.append('compatibility-alias-policy.json is missing fields: ' + ', '.join(missing_compatibility_fields))
    for alias in compatibility_aliases.get('aliases', []):
        if not isinstance(alias, dict):
            continue
        for field in ('id', 'alias_scope', 'canonical_target', 'reason', 'introduced_at', 'expiry_at', 'owner', 'removal_condition'):
            if field not in alias or not str(alias.get(field) or '').strip():
                errors.append(f"compatibility-alias-policy.json alias {alias.get('id') or '<unknown>'} is missing required field {field}")

    missing_freeze_fields = sorted(field for field in REQUIRED_ARCHITECTURE_FREEZE_FIELDS if field not in architecture_freeze)
    if missing_freeze_fields:
        errors.append('architecture-freeze-policy.json is missing fields: ' + ', '.join(missing_freeze_fields))
    freeze_threshold = int(dict(architecture_freeze.get('architecture_freeze_policy') or {}).get('activate_when_ready_for_checkpoint_gte') or 0)
    completion_threshold = int(dict(completion.get('publication_debt_policy') or {}).get('ready_for_checkpoint_blocking_threshold') or 0)
    if freeze_threshold != completion_threshold:
        errors.append('architecture-freeze-policy.json threshold must match completion-program-registry publication debt threshold')
    return errors
