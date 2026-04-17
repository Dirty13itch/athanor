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


def test_build_payload_reports_operator_front_door_state() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "burn_class:overnight_harvest",
        "active_claim_task_title": "Overnight Harvest",
        "active_claim_lane_family": "capacity_truth_repair",
        "queue_total": 12,
        "queue_dispatchable": 6,
        "queue_blocked": 0,
        "current_stop_state": "none",
        "next_unblocked_candidate": {
            "task_id": "burn_class:cheap_bulk_cloud",
            "title": "Cheap Bulk Cloud",
            "selected_provider_label": "DeepSeek API",
            "preferred_lane_family": "dispatch_truth_repair",
        },
        "finish_scoreboard": {
            "closure_state": "repo_safe_complete",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": False,
            "suppressed_queue_count": 7,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {
            "ralph_latest": "reports/ralph-loop/latest.json",
            "finish_scoreboard": "reports/truth-inventory/finish-scoreboard.json",
            "runtime_packet_inbox": "reports/truth-inventory/runtime-packet-inbox.json",
        },
    }
    module._load_optional_json = lambda path: {
        "active_claim_task_id": "burn_class:overnight_harvest",
        "active_claim_task_title": "Overnight Harvest",
        "active_claim_lane_family": "capacity_truth_repair",
        "autonomous_queue": [
            {
                "task_id": "burn_class:overnight_harvest",
                "title": "Overnight Harvest",
                "selected_provider_label": "Athanor Local",
                "selected_provider_id": "athanor_local",
                "status": "already_dispatched",
                "proof_command_or_eval_surface": "reports/truth-inventory/capacity-telemetry.json",
                "approved_mutation_class": "auto_harvest",
                "value_class": "capacity_truth_drift",
                "max_concurrency": 8,
            }
        ],
        "automation_feedback_summary": {
            "recent_dispatch_outcomes": [
                {
                    "completed_at": "1776373613.147440",
                    "task_id": "burn_class:overnight_harvest",
                    "task_title": "Overnight Harvest",
                    "dispatch_outcome": "claimed",
                    "summary": "Ralph loop selected Overnight Harvest.",
                }
            ]
        },
    }

    payload = module.build_payload()

    assert payload["operator_mode"] == "steady_state_monitoring"
    assert payload["intervention_level"] == "no_action_needed"
    assert payload["needs_you"] is False
    assert payload["current_work"]["task_title"] == "Overnight Harvest"
    assert payload["current_work"]["provider_label"] == "Athanor Local"
    assert payload["next_up"]["task_title"] == "Cheap Bulk Cloud"
    assert payload["recent_activity"][0]["task_title"] == "Overnight Harvest"


def test_render_markdown_surfaces_operator_sections() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    rendered = module.render_markdown(
        {
            "reopen_triggers": ["finish-scoreboard reports non-zero repo-safe debt"],
            "artifacts": {
                "ralph_latest": "reports/ralph-loop/latest.json",
                "finish_scoreboard": "reports/truth-inventory/finish-scoreboard.json",
                "runtime_packet_inbox": "reports/truth-inventory/runtime-packet-inbox.json",
                "steady_state_status_json": "reports/truth-inventory/steady-state-status.json",
                "steady_state_live_md": "reports/truth-inventory/steady-state-live.md",
            },
        }
    )

    assert "# Steady-State Status" in rendered
    assert "## Operating Contract" in rendered
    assert "This tracked document is durable by design." in rendered
    assert "steady-state-live.md" in rendered
    assert "No action needed" in rendered
    assert "Read `reports/truth-inventory/steady-state-status.json` for the current reopen reasons." in rendered


def test_render_markdown_is_stable_across_live_state_changes() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    shared_artifacts = {
        "ralph_latest": "reports/ralph-loop/latest.json",
        "finish_scoreboard": "reports/truth-inventory/finish-scoreboard.json",
        "runtime_packet_inbox": "reports/truth-inventory/runtime-packet-inbox.json",
        "steady_state_status_json": "reports/truth-inventory/steady-state-status.json",
        "steady_state_live_md": "reports/truth-inventory/steady-state-live.md",
    }

    quiet = {
        "closure_state": "repo_safe_complete",
        "intervention_label": "No action needed",
        "needs_you": False,
        "intervention_summary": "Core closure is complete and the live lane is running.",
        "queue_total": 12,
        "queue_dispatchable": 6,
        "queue_blocked": 0,
        "suppressed_task_count": 7,
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "reopen_triggers": ["finish-scoreboard reports non-zero repo-safe debt"],
        "reopen_reasons": [],
        "artifacts": shared_artifacts,
    }
    noisy = {
        "closure_state": "closure_in_progress",
        "intervention_label": "Review recommended",
        "needs_you": True,
        "intervention_summary": "Closure debt or reopen conditions are active.",
        "queue_total": 99,
        "queue_dispatchable": 1,
        "queue_blocked": 10,
        "suppressed_task_count": 42,
        "selected_workstream_title": "Reference and Archive Prune",
        "reopen_triggers": ["finish-scoreboard reports non-zero repo-safe debt"],
        "reopen_reasons": ["program-slice debt remains (`1`)"],
        "artifacts": shared_artifacts,
    }

    assert module.render_markdown(quiet) == module.render_markdown(noisy)


def test_render_live_markdown_surfaces_volatile_operator_feed() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    rendered = module.render_live_markdown(
        {
            "closure_state": "repo_safe_complete",
            "intervention_label": "No action needed",
            "needs_you": False,
            "intervention_summary": "Core closure is complete and the live lane is running.",
            "queue_total": 12,
            "queue_dispatchable": 6,
            "queue_blocked": 0,
            "suppressed_task_count": 7,
            "selected_workstream_title": "Dispatch and Work-Economy Closure",
            "current_work": {
                "task_title": "Overnight Harvest",
                "task_id": "burn_class:overnight_harvest",
                "provider_label": "Athanor Local",
                "lane_family": "capacity_truth_repair",
                "dispatch_status": "already_dispatched",
                "mutation_class": "auto_harvest",
                "value_class": "capacity_truth_drift",
                "proof_surface": "reports/truth-inventory/capacity-telemetry.json",
                "max_concurrency": 8,
            },
            "next_up": {
                "task_title": "Cheap Bulk Cloud",
                "provider_label": "DeepSeek API",
            },
            "reopen_reasons": [],
            "recent_activity": [
                {
                    "at": "2026-04-16 21:06 UTC",
                    "task_title": "Overnight Harvest",
                    "dispatch_outcome": "claimed",
                    "summary": "Ralph loop selected Overnight Harvest.",
                }
            ],
        }
    )

    assert "# Steady-State Live Operator Feed" in rendered
    assert "## Current Work" in rendered
    assert "## Reopen State" in rendered
    assert "## Recent Activity" in rendered
    assert "Overnight Harvest" in rendered
    assert "Cheap Bulk Cloud" in rendered
    assert "No action needed" in rendered
    assert "None." in rendered


def test_normalized_payload_ignores_generated_at() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    older = {"generated_at": "2026-04-16T20:00:00+00:00", "operator_mode": "steady_state_monitoring"}
    newer = {"generated_at": "2026-04-16T21:00:00+00:00", "operator_mode": "steady_state_monitoring"}

    assert module._normalized_payload(older) == module._normalized_payload(newer)
