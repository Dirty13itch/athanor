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


def test_persist_finish_artifacts_updates_report_and_writes_both_sidecars(tmp_path: Path) -> None:
    module = _load_module(
        f"run_ralph_finish_artifacts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    written: dict[str, dict] = {}
    finish_path = tmp_path / "finish-scoreboard.json"
    runtime_path = tmp_path / "runtime-packet-inbox.json"

    module.build_runtime_packet_inbox = lambda payload: {
        "generated_at": "2026-04-19T03:33:57+00:00",
        "packet_count": 0,
        "packets": [],
    }
    module.build_finish_scoreboard = lambda report, publication_queue, runtime_inbox: {
        "generated_at": "2026-04-19T03:33:57+00:00",
        "cash_now_remaining_count": 0,
        "program_slice_remaining_count": 4,
        "next_deferred_family_id": "control-plane-registry-and-routing",
    }
    module.RUNTIME_PACKET_INBOX_PATH = runtime_path
    module.FINISH_SCOREBOARD_PATH = finish_path
    module._write_json = lambda path, payload: written.__setitem__(str(path), dict(payload))

    report = {"selected_workstream_id": "dispatch-and-work-economy-closure"}
    module._persist_finish_artifacts(
        report,
        {"families": []},
        {"packets": []},
    )

    assert report["runtime_packet_inbox"]["packet_count"] == 0
    assert report["finish_scoreboard"]["program_slice_remaining_count"] == 4
    assert written[str(runtime_path)]["packet_count"] == 0
    assert written[str(finish_path)]["next_deferred_family_id"] == "control-plane-registry-and-routing"
