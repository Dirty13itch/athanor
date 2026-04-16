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


def test_build_payload_reports_closure_progress_and_runtime_packets(tmp_path: Path) -> None:
    module = _load_module(
        f"write_finish_scoreboard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_finish_scoreboard.py",
    )

    ralph_path = tmp_path / "latest.json"
    ralph_path.write_text(
        json.dumps(
            {
                "active_claim_task_id": "workstream:validation-and-publication",
                "active_claim_task_title": "Validation and Publication",
                "selected_workstream_id": "dispatch-and-work-economy-closure",
                "repo_side_no_delta": False,
                "rotation_ready": False,
                "autonomous_queue_summary": {
                    "dispatchable_queue_count": 7,
                    "blocked_queue_count": 0,
                    "suppressed_queue_count": 2,
                },
                "next_unblocked_candidate": {
                    "task_id": "burn_class:local_bulk_sovereign",
                    "title": "Local Bulk Sovereign",
                },
            }
        ),
        encoding="utf-8",
    )
    module.RALPH_LATEST_PATH = ralph_path
    module.load_publication_deferred_queue = lambda: {
        "families": [
            {"id": "reference-and-archive-prune", "execution_class": "cash_now", "match_count": 5},
            {"id": "deployment-authority-follow-on", "execution_class": "bounded_follow_on", "match_count": 1},
            {"id": "control-plane-follow-on", "execution_class": "program_slice", "match_count": 2},
        ],
        "next_recommended_family": {"id": "reference-and-archive-prune", "title": "Reference and Archive Prune"},
    }
    module.load_runtime_packets = lambda: {
        "packets": [
            {
                "id": "dev-runtime-ssh-access-recovery-packet",
                "label": "DEV Runtime SSH Access Recovery",
                "status": "ready_for_approval",
                "lane_id": "runtime_ownership",
                "host": "DEV",
                "approval_packet_type": "runtime_reconfiguration",
                "goal": "Restore SSH access.",
                "preflight_commands": ["ssh dev true"],
                "verification_commands": ["ssh dev hostname"],
                "rollback_steps": ["Revert SSH config change."],
                "exact_steps": ["Approve and apply bounded SSH repair."],
            }
        ]
    }

    payload = module.build_payload()

    assert payload["closure_state"] == "closure_in_progress"
    assert payload["cash_now_remaining_count"] == 1
    assert payload["bounded_follow_on_remaining_count"] == 1
    assert payload["program_slice_remaining_count"] == 1
    assert payload["approval_gated_runtime_packet_count"] == 1
    assert payload["next_deferred_family_id"] == "reference-and-archive-prune"


def test_build_payload_reports_repo_safe_complete_when_only_background_queue_remains(tmp_path: Path) -> None:
    module = _load_module(
        f"write_finish_scoreboard_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_finish_scoreboard.py",
    )

    ralph_path = tmp_path / "latest.json"
    ralph_path.write_text(
        json.dumps(
            {
                "active_claim_task_id": "workstream:validation-and-publication",
                "active_claim_task_title": "Validation and Publication",
                "selected_workstream_id": "dispatch-and-work-economy-closure",
                "repo_side_no_delta": True,
                "rotation_ready": True,
                "autonomous_queue_summary": {
                    "dispatchable_queue_count": 10,
                    "blocked_queue_count": 0,
                    "suppressed_queue_count": 2,
                },
                "next_unblocked_candidate": {
                    "task_id": "deferred_family:reference-and-archive-prune",
                    "title": "Reference and Archive Prune",
                },
            }
        ),
        encoding="utf-8",
    )
    module.RALPH_LATEST_PATH = ralph_path
    module.load_publication_deferred_queue = lambda: {
        "families": [
            {"id": "reference-and-archive-prune", "execution_class": "cash_now", "match_count": 0},
            {"id": "deployment-authority-follow-on", "execution_class": "bounded_follow_on", "match_count": 0},
            {"id": "control-plane-follow-on", "execution_class": "program_slice", "match_count": 0},
        ],
        "next_recommended_family": {"id": "reference-and-archive-prune", "title": "Reference and Archive Prune"},
    }
    module.load_runtime_packets = lambda: {"packets": []}

    payload = module.build_payload()

    assert payload["closure_state"] == "repo_safe_complete"
    assert payload["only_typed_brakes_remain"] is False
    assert payload["cash_now_remaining_count"] == 0
    assert payload["bounded_follow_on_remaining_count"] == 0
    assert payload["program_slice_remaining_count"] == 0
    assert payload["approval_gated_runtime_packet_count"] == 0
    assert payload["next_deferred_family_id"] is None
    assert payload["next_unblocked_candidate_task_id"] is None
