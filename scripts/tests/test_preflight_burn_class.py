from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / 'scripts' / 'preflight_burn_class.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('preflight_burn_class', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_burn_class_preflight_merges_registry_queue_and_quota_state():
    module = _load_module()
    snapshot = {
        'top_task_id': 'workstream:validation-and-publication',
        'queue_dispatchable': 7,
        'queue_blocked': 0,
        'suppressed_task_count': 2,
        'next_action_family': 'dispatch_truth_and_queue_replenishment',
        'queue': [{
            'task_id': 'burn_class:local_bulk_sovereign',
            'burn_class_id': 'local_bulk_sovereign',
            'title': 'Local Bulk Sovereign',
            'dispatchable': True,
            'status': 'ready',
            'preferred_lane_family': 'capacity_truth_repair',
            'approved_mutation_class': 'auto_harvest',
            'proof_command_or_eval_surface': 'reports/truth-inventory/capacity-telemetry.json',
            'selected_provider_id': 'athanor_local',
            'selected_provider_label': 'Athanor Local',
            'capacity_signal': {'harvestable_scheduler_slot_count': 2},
        }],
    }
    registry = {
        'burn_classes': [{
            'id': 'local_bulk_sovereign',
            'label': 'Local Bulk Sovereign',
            'routing_chain': ['athanor_local'],
            'approved_task_families': ['repo_audit', 'background_transform'],
            'reserve_rule': 'protect_interactive_reserve_then_harvest_idle_slots',
            'max_concurrency': 6,
        }]
    }
    quota = {
        'records': [{
            'family_id': 'athanor_local_compute',
            'harvestable_scheduler_slot_count': 2,
        }]
    }
    payload = module.build_burn_class_preflight('local_bulk_sovereign', snapshot, registry, {}, quota)
    assert payload['burn_class_id'] == 'local_bulk_sovereign'
    assert payload['dispatchable'] is True
    assert payload['routing_chain'] == ['athanor_local']
    assert payload['reserve_rule'] == 'protect_interactive_reserve_then_harvest_idle_slots'
    assert payload['queue_blocked'] == 0
    assert payload['quota_family']['family_id'] == 'athanor_local_compute'
