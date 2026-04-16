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


def test_build_payload_reports_repo_safe_completion() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "queue_total": 7,
        "queue_dispatchable": 7,
        "queue_blocked": 0,
        "finish_scoreboard": {
            "closure_state": "repo_safe_complete",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": False,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {
            "finish_scoreboard": "reports/truth-inventory/finish-scoreboard.json",
            "runtime_packet_inbox": "reports/truth-inventory/runtime-packet-inbox.json",
        },
    }

    payload = module.build_payload()

    assert payload["operator_mode"] == "steady_state_monitoring"
    assert payload["reopen_required"] is False
    assert payload["runtime_packet_count"] == 0
    assert "run_steady_state_control_plane.py" in payload["next_operator_action"]


def test_render_markdown_surfaces_reopen_reasons() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    rendered = module.render_markdown(
        {
            "operator_mode": "active_closure",
            "closure_state": "closure_in_progress",
            "reopen_required": True,
            "cash_now_remaining_count": 2,
            "bounded_follow_on_remaining_count": 1,
            "program_slice_remaining_count": 0,
            "runtime_packet_count": 1,
            "queue_total": 4,
            "queue_dispatchable": 2,
            "queue_blocked": 0,
            "active_claim_task_title": "Validation and Publication",
            "selected_workstream_title": "Dispatch and Work-Economy Closure",
            "next_deferred_family_title": "Reference and Archive Prune",
            "next_operator_action": "Re-enter closure work.",
            "reopen_triggers": ["finish-scoreboard reports non-zero repo-safe debt"],
            "reopen_reasons": ["cash_now repo-safe debt remains (`2`)", "runtime packet inbox still has `1` packets"],
            "artifacts": {
                "finish_scoreboard": "reports/truth-inventory/finish-scoreboard.json",
                "runtime_packet_inbox": "reports/truth-inventory/runtime-packet-inbox.json",
                "steady_state_status_json": "reports/truth-inventory/steady-state-status.json",
            },
        }
    )

    assert "# Steady-State Status" in rendered
    assert "Validation and Publication" in rendered
    assert "Reference and Archive Prune" in rendered
    assert "Active Reopen Reasons" in rendered
    assert "runtime packet inbox still has `1` packets" in rendered
