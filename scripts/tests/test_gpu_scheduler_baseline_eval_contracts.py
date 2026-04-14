from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

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


def test_capacity_truth_check_passes_when_scheduler_and_telemetry_align() -> None:
    module = _load_module(
        f"gpu_scheduler_baseline_eval_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_gpu_scheduler_baseline_eval.py",
    )

    capacity_telemetry = {
        "generated_at": "2026-04-13T18:26:57.985852+00:00",
        "capacity_summary": {
            "sample_posture": "scheduler_projection_backed",
            "scheduler_queue_depth": 0,
            "scheduler_slot_count": 2,
            "harvestable_scheduler_slot_count": 1,
        },
        "scheduler_slot_samples": [
            {"scheduler_slot_id": "F:TP4", "idle_window_open": True},
            {"scheduler_slot_id": "W:1", "idle_window_open": False},
        ],
    }
    scheduler_state = {
        "body": {
            "queue_depth": 0,
            "gpus": {
                "F:TP4": {"state": "SLEEPING_L1"},
                "W:1": {"state": "ACTIVE"},
            },
        }
    }

    check = module._build_capacity_truth_check(capacity_telemetry, scheduler_state)

    assert check["status"] == "passed"
    assert check["mismatches"] == []
    assert check["telemetry_harvestable_slot_ids"] == ["F:TP4"]


def test_capacity_truth_check_blocks_when_slot_inventory_drifts() -> None:
    module = _load_module(
        f"gpu_scheduler_baseline_eval_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_gpu_scheduler_baseline_eval.py",
    )

    capacity_telemetry = {
        "generated_at": "2026-04-13T18:26:57.985852+00:00",
        "capacity_summary": {
            "sample_posture": "scheduler_projection_backed",
            "scheduler_queue_depth": 0,
            "scheduler_slot_count": 1,
            "harvestable_scheduler_slot_count": 1,
        },
        "scheduler_slot_samples": [
            {"scheduler_slot_id": "F:TP4", "idle_window_open": True},
        ],
    }
    scheduler_state = {
        "body": {
            "queue_depth": 2,
            "gpus": {
                "F:TP4": {"state": "SLEEPING_L1"},
                "W:1": {"state": "SLEEPING_L1"},
            },
        }
    }

    check = module._build_capacity_truth_check(capacity_telemetry, scheduler_state)

    assert check["status"] == "blocked"
    assert "scheduler_queue_depth_matches" in check["mismatches"]
    assert "scheduler_slot_count_matches" in check["mismatches"]
    assert "scheduler_slot_inventory_matches" in check["mismatches"]
