from __future__ import annotations

import importlib.util
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock, patch


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


def test_ssh_probe_handles_missing_ssh_binary_without_crashing() -> None:
    module = _load_module(
        f"gpu_scheduler_baseline_eval_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_gpu_scheduler_baseline_eval.py",
    )

    with patch.object(module.subprocess, "run", side_effect=FileNotFoundError("ssh")):
        result = module._ssh_probe("192.168.1.244", "echo test")

    assert result["ok"] is False
    assert result["returncode"] is None
    assert result["error"].startswith("FileNotFoundError:")


def test_ssh_probe_uses_batch_mode_options() -> None:
    module = _load_module(
        f"gpu_scheduler_baseline_eval_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_gpu_scheduler_baseline_eval.py",
    )

    completed = subprocess.CompletedProcess(
        args=["ssh"],
        returncode=0,
        stdout="ok\n",
        stderr="",
    )
    runner = Mock(return_value=completed)
    with patch.object(module.subprocess, "run", runner):
        result = module._ssh_probe("192.168.1.244", "echo test")

    command = runner.call_args.args[0]
    assert command[:3] == ["ssh", "-o", "BatchMode=yes"]
    assert "StrictHostKeyChecking=no" in command
    assert command[-2:] == ["192.168.1.244", "echo test"]
    assert result["ok"] is True
