from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "write_next_rotation_preflight.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("write_next_rotation_preflight", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_next_rotation_preflight_materializes_burn_class_payload(monkeypatch) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "load_restart_snapshot", lambda: {
        "next_unblocked_candidate": {
            "task_id": "burn_class:local_bulk_sovereign",
            "title": "Local Bulk Sovereign",
            "source_type": "burn_class",
        },
        "queue": [
            {
                "task_id": "burn_class:local_bulk_sovereign",
                "title": "Local Bulk Sovereign",
                "dispatchable": True,
                "preferred_lane_family": "capacity_truth_repair",
                "approved_mutation_class": "auto_harvest",
            }
        ],
        "queue_dispatchable": 7,
        "queue_blocked": 0,
        "suppressed_task_count": 2,
        "next_action_family": "dispatch_truth_and_queue_replenishment",
        "top_task_id": "workstream:validation-and-publication",
    })
    monkeypatch.setattr(module, "_load_json", lambda _path: {
        "burn_classes": [
            {
                "id": "local_bulk_sovereign",
                "label": "Local Bulk Sovereign",
                "routing_chain": ["athanor_local"],
                "approved_task_families": ["async_backlog_execution"],
                "reserve_rule": "burn_idle_local_capacity_first_then_use_cheap_overflow",
                "max_concurrency": 6,
            }
        ],
        "records": [{"family_id": "athanor_local_compute", "status": "ready"}],
    })

    payload = module.build_next_rotation_preflight()

    assert payload["preflight_available"] is True
    assert payload["next_candidate_task_id"] == "burn_class:local_bulk_sovereign"
    assert payload["preflight"]["burn_class_id"] == "local_bulk_sovereign"
    assert payload["preflight"]["dispatchable"] is True


def test_build_next_rotation_preflight_stays_empty_for_non_burn_class(monkeypatch) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "load_restart_snapshot", lambda: {
        "next_unblocked_candidate": {
            "task_id": "workstream:validation-and-publication",
            "title": "Validation and Publication",
            "source_type": "workstream",
        }
    })

    payload = module.build_next_rotation_preflight()

    assert payload["preflight_available"] is False
    assert payload["preflight"] is None
