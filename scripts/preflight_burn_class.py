#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BURN_REGISTRY_PATH = REPO_ROOT / 'config/automation-backbone/subscription-burn-registry.json'
CAPACITY_PATH = REPO_ROOT / 'reports/truth-inventory/capacity-telemetry.json'
QUOTA_PATH = REPO_ROOT / 'reports/truth-inventory/quota-truth.json'


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def load_restart_snapshot() -> dict[str, Any]:
    proc = subprocess.run(
        [PYTHON, 'scripts/session_restart_brief.py', '--json'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'session_restart_brief failed')
    return json.loads(proc.stdout)


def build_burn_class_preflight(burn_class_id: str, snapshot: dict[str, Any], registry: dict[str, Any], capacity: dict[str, Any], quota: dict[str, Any]) -> dict[str, Any]:
    burn_defs = {
        str(item.get('id') or '').strip(): item
        for item in registry.get('burn_classes', [])
        if isinstance(item, dict) and str(item.get('id') or '').strip()
    }
    burn_def = dict(burn_defs.get(burn_class_id) or {})
    queue_items = snapshot.get('queue') if isinstance(snapshot.get('queue'), list) else []
    queue_item = next((item for item in queue_items if str(item.get('burn_class_id') or '') == burn_class_id or str(item.get('task_id') or '') == f'burn_class:{burn_class_id}'), {})
    quota_records = quota.get('records') if isinstance(quota.get('records'), list) else []
    local_compute = next((item for item in quota_records if str(item.get('family_id') or '') == 'athanor_local_compute'), {})
    return {
        'burn_class_id': burn_class_id,
        'label': str(burn_def.get('label') or queue_item.get('title') or burn_class_id),
        'routing_chain': [str(item).strip() for item in burn_def.get('routing_chain', []) if str(item).strip()],
        'approved_task_families': [str(item).strip() for item in burn_def.get('approved_task_families', []) if str(item).strip()],
        'reserve_rule': str(burn_def.get('reserve_rule') or '').strip() or None,
        'max_concurrency': int(burn_def.get('max_concurrency') or 0) or None,
        'dispatchable': bool(queue_item.get('dispatchable')),
        'status': str(queue_item.get('status') or '').strip() or None,
        'preferred_lane_family': str(queue_item.get('preferred_lane_family') or '').strip() or None,
        'approved_mutation_class': str(queue_item.get('approved_mutation_class') or '').strip() or None,
        'proof_command_or_eval_surface': str(queue_item.get('proof_command_or_eval_surface') or '').strip() or None,
        'selected_provider_id': str(queue_item.get('selected_provider_id') or '').strip() or None,
        'selected_provider_label': str(queue_item.get('selected_provider_label') or '').strip() or None,
        'queue_top_task_id': snapshot.get('top_task_id'),
        'queue_dispatchable': snapshot.get('queue_dispatchable'),
        'queue_blocked': snapshot.get('queue_blocked'),
        'suppressed_task_count': snapshot.get('suppressed_task_count'),
        'capacity_signal': queue_item.get('capacity_signal') if isinstance(queue_item.get('capacity_signal'), dict) else capacity,
        'quota_family': local_compute,
        'next_action_family': snapshot.get('next_action_family'),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Show current queue/registy preflight state for a burn class.')
    parser.add_argument('burn_class_id', help='Burn class id from subscription-burn-registry.json')
    parser.add_argument('--json', action='store_true', help='Print JSON output')
    args = parser.parse_args()

    snapshot = load_restart_snapshot()
    registry = _load_json(BURN_REGISTRY_PATH)
    capacity = _load_json(CAPACITY_PATH)
    quota = _load_json(QUOTA_PATH)
    payload = build_burn_class_preflight(args.burn_class_id, snapshot, registry, capacity, quota)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for key, value in payload.items():
            print(f'{key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
