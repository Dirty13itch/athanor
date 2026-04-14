from __future__ import annotations

import importlib.util
import json
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


def test_load_scheduler_projection_prefers_freshest_scheduler_timestamp(tmp_path: Path) -> None:
    module = _load_module(
        f"collect_capacity_telemetry_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "collect_capacity_telemetry.py",
    )

    older = tmp_path / "gpu-scheduler-promotion-eval.json"
    older.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-12T18:42:00+00:00",
                "live_scheduler_state": {
                    "body": {
                        "timestamp": "2026-04-12T18:41:42.775209+00:00",
                        "gpus": {"F:TP4": {"state": "SLEEPING_L1"}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    newer = tmp_path / "gpu-scheduler-baseline-eval.json"
    newer.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-13T20:42:40.082140+00:00",
                "live_scheduler_state": {
                    "body": {
                        "timestamp": "2026-04-13T20:42:19.157848+00:00",
                        "gpus": {"W:1": {"state": "SLEEPING_L1"}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    module.REPO_ROOT = tmp_path
    module.SCHEDULER_EVAL_PATHS = [older, newer]

    payload, source = module._load_scheduler_projection()
    expected_source = newer.relative_to(tmp_path).as_posix()

    assert payload["timestamp"] == "2026-04-13T20:42:19.157848+00:00"
    assert source == expected_source


def test_load_scheduler_projection_accepts_baseline_live_runtime_shape(tmp_path: Path) -> None:
    module = _load_module(
        f"collect_capacity_telemetry_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "collect_capacity_telemetry.py",
    )

    baseline = tmp_path / "gpu-scheduler-baseline-eval.json"
    baseline.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-13T20:42:40.082140+00:00",
                "live_runtime": {
                    "scheduler_state": {
                        "body": {
                            "timestamp": "2026-04-13T20:42:19.157848+00:00",
                            "gpus": {"W:1": {"state": "SLEEPING_L1"}},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    module.REPO_ROOT = tmp_path
    module.SCHEDULER_EVAL_PATHS = [baseline]

    payload, source = module._load_scheduler_projection()

    assert payload["timestamp"] == "2026-04-13T20:42:19.157848+00:00"
    assert source == "gpu-scheduler-baseline-eval.json"
