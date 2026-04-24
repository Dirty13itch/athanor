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
    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {
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
        if path == module.VALUE_THROUGHPUT_SCORECARD_PATH:
            return {
                "reconciliation": {"issue_count": 0},
                "stale_claim_count": 0,
                "degraded_sections": [],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {
                    "cash_now": 0,
                    "bounded_follow_on": 0,
                    "program_slice": 0,
                    "family_count": 0,
                    "family_ids": [],
                },
                "queue": {
                    "total": 12,
                    "dispatchable": 6,
                    "blocked": 0,
                    "suppressed": 7,
                },
                "runtime_packets": {"count": 0},
                "proof_gate": {"open": False, "status": "closed", "blocking_check_ids": ["stable_operating_day"]},
                "auto_mutation": {"state": "repo_safe_only_runtime_and_provider_mutations_gated", "proof_gate_open": False},
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["operator_mode"] == "steady_state_monitoring"
    assert payload["intervention_level"] == "no_action_needed"
    assert payload["needs_you"] is False
    assert payload["current_work"]["task_title"] == "Overnight Harvest"
    assert payload["current_work"]["provider_label"] == "Athanor Local"
    assert payload["next_up"]["task_title"] == "Cheap Bulk Cloud"
    assert payload["recent_activity"][0]["task_title"] == "Overnight Harvest"
    assert payload["blocker_map"]["proof_gate"]["status"] == "closed"
    assert payload["proof_gate"]["status"] == "closed"
    assert payload["continuity"]["controller_status"] == "unknown"


def test_build_payload_escalates_stale_dispatch_truth_even_when_finish_scoreboard_is_green() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "dispatch_truth_repair",
        "queue_total": 4,
        "queue_dispatchable": 2,
        "queue_blocked": 1,
        "current_stop_state": "none",
        "dispatch_status": "stale_dispatched_task",
        "next_unblocked_candidate": {
            "task_id": "burn_class:premium_interactive",
            "title": "Premium Interactive",
            "selected_provider_label": "Claude Code",
            "preferred_lane_family": "interactive_architecture",
        },
        "finish_scoreboard": {
            "closure_state": "repo_safe_complete",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": False,
            "suppressed_queue_count": 1,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {},
    }
    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {
                "active_claim_task_id": "workstream:validation-and-publication",
                "active_claim_task_title": "Validation and Publication",
                "active_claim_lane_family": "dispatch_truth_repair",
                "autonomous_queue": [
                    {
                        "task_id": "workstream:validation-and-publication",
                        "title": "Validation and Publication",
                        "selected_provider_label": "Claude Code",
                        "selected_provider_id": "claude_code",
                        "status": "already_dispatched",
                        "proof_command_or_eval_surface": "python scripts/run_ralph_loop_pass.py --skip-refresh --skip-validation",
                        "approved_mutation_class": "auto_harvest",
                        "value_class": "dispatch_truth_drift",
                        "max_concurrency": 1,
                    }
                ],
                "automation_feedback_summary": {
                    "recent_dispatch_outcomes": [
                        {
                            "completed_at": "2026-04-18T23:22:44+00:00",
                            "task_id": "workstream:validation-and-publication",
                            "task_title": "Validation and Publication",
                            "dispatch_outcome": "failed",
                            "summary": "Active claim Validation and Publication is stale_dispatched_task.",
                        }
                    ]
                },
            }
        if path == module.VALUE_THROUGHPUT_SCORECARD_PATH:
            return {
                "reconciliation": {"issue_count": 0},
                "stale_claim_count": 0,
                "degraded_sections": [],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {
                    "cash_now": 0,
                    "bounded_follow_on": 0,
                    "program_slice": 0,
                    "family_count": 0,
                    "family_ids": [],
                },
                "queue": {
                    "total": 4,
                    "dispatchable": 2,
                    "blocked": 1,
                    "suppressed": 1,
                },
                "runtime_packets": {"count": 0},
                "proof_gate": {"open": False, "status": "closed", "blocking_check_ids": ["stale_claim_failures"]},
                "auto_mutation": {"state": "repo_safe_only_runtime_and_provider_mutations_gated", "proof_gate_open": False},
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["intervention_level"] == "system_attention_required"
    assert payload["needs_you"] is True
    assert payload["current_work"]["dispatch_status"] == "stale_dispatched_task"
    assert "governed dispatch is `stale_dispatched_task`" in payload["reopen_reasons"]


def test_build_payload_describes_bounded_backoff_when_continuity_is_skipped() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:capacity-and-harvest-truth",
        "active_claim_task_title": "Capacity and Harvest Truth",
        "active_claim_lane_family": "capacity_truth_repair",
        "queue_total": 12,
        "queue_dispatchable": 9,
        "queue_blocked": 2,
        "current_stop_state": "none",
        "dispatch_status": "success",
        "next_unblocked_candidate": {
            "task_id": "builder:queue-backed",
            "title": "Builder",
            "preferred_lane_family": "builder",
        },
        "finish_scoreboard": {
            "closure_state": "repo_safe_complete",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": False,
            "suppressed_queue_count": 1,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {},
    }

    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {
                "active_claim_task_id": "workstream:capacity-and-harvest-truth",
                "active_claim_task_title": "Capacity and Harvest Truth",
                "active_claim_lane_family": "capacity_truth_repair",
                "autonomous_queue": [
                    {
                        "task_id": "workstream:capacity-and-harvest-truth",
                        "title": "Capacity and Harvest Truth",
                        "dispatchable": True,
                    }
                ],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {
                    "cash_now": 0,
                    "bounded_follow_on": 0,
                    "program_slice": 0,
                    "family_count": 0,
                    "family_ids": [],
                },
                "queue": {"total": 12, "dispatchable": 9, "blocked": 2, "suppressed": 1},
                "runtime_packets": {"count": 0},
                "proof_gate": {
                    "open": False,
                    "status": "closed",
                    "blocking_check_ids": ["stable_operating_day", "result_backed_threshold"],
                },
                "auto_mutation": {
                    "state": "repo_safe_only_runtime_and_provider_mutations_gated",
                    "proof_gate_open": False,
                },
            }
        if path == module.BLOCKER_EXECUTION_PLAN_PATH:
            return {
                "next_target": {
                    "family_id": "builder",
                    "family_title": "Builder",
                    "kind": "queue_backed_throughput",
                    "subtranche_id": "unscoped",
                    "subtranche_title": None,
                }
            }
        if path == module.CONTINUITY_CONTROLLER_STATE_PATH:
            return {
                "controller_status": "skipped",
                "controller_host": "dev",
                "controller_mode": "proof_hold",
                "last_skip_reason": "backoff_active",
                "backoff_until": "2026-04-19T17:38:32.783745+00:00",
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["intervention_level"] == "no_action_needed"
    assert payload["continuity"]["controller_status"] == "skipped"
    assert payload["intervention_summary"] == "Core closure is complete and the live lane is in bounded backoff."


def test_build_payload_surfaces_runtime_packet_as_effective_next_target() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:capacity-and-harvest-truth",
        "active_claim_task_title": "Capacity and Harvest Truth",
        "active_claim_lane_family": "capacity_truth_repair",
        "queue_total": 12,
        "queue_dispatchable": 9,
        "queue_blocked": 2,
        "current_stop_state": "none",
        "dispatch_status": "claimed",
        "next_unblocked_candidate": {
            "task_id": "builder:queue-backed",
            "title": "Builder",
            "preferred_lane_family": "builder",
        },
        "finish_scoreboard": {
            "closure_state": "typed_brakes_only",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": True,
            "suppressed_queue_count": 1,
        },
        "runtime_packet_inbox": {
            "packet_count": 1,
            "packets": [
                {
                    "id": "workshop-ulrich-energy-retirement-packet",
                    "label": "WORKSHOP retired ulrich-energy runtime retirement packet",
                    "host": "workshop",
                    "approval_type": "runtime_host_reconfiguration",
                    "goal": "Retire the remaining Workshop ulrich-energy runtime lineage.",
                    "readiness_state": "ready_for_approval",
                    "next_operator_action": "Create a timestamped backup root before any mutation.",
                }
            ],
        },
        "artifacts": {},
    }

    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {
                "active_claim_task_id": "workstream:capacity-and-harvest-truth",
                "active_claim_task_title": "Capacity and Harvest Truth",
                "active_claim_lane_family": "capacity_truth_repair",
                "autonomous_queue": [
                    {"task_id": "workstream:capacity-and-harvest-truth", "title": "Capacity and Harvest Truth", "dispatchable": True}
                ],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {"cash_now": 0, "bounded_follow_on": 0, "program_slice": 0, "family_count": 0, "family_ids": []},
                "queue": {"total": 12, "dispatchable": 9, "blocked": 2, "suppressed": 1},
                "runtime_packets": {"count": 1},
                "proof_gate": {"open": False, "status": "closed", "blocking_check_ids": ["stable_operating_day"]},
                "auto_mutation": {"state": "repo_safe_only_runtime_and_provider_mutations_gated", "proof_gate_open": False},
            }
        if path == module.BLOCKER_EXECUTION_PLAN_PATH:
            return {
                "next_target": {
                    "family_id": "builder",
                    "family_title": "Builder",
                    "kind": "queue_backed_throughput",
                    "subtranche_id": "unscoped",
                    "subtranche_title": None,
                }
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["next_target"]["kind"] == "runtime_packet"
    assert payload["next_target"]["family_id"] == "runtime-packet-inbox"
    assert payload["next_target"]["approval_gated"] is True
    assert payload["runtime_packet_next"]["subtranche_id"] == "workshop-ulrich-energy-retirement-packet"
    assert payload["next_up"]["task_title"] == "WORKSHOP retired ulrich-energy runtime retirement packet"
    assert payload["continuity_controller"]["next_target"]["family_id"] == "runtime-packet-inbox"


def test_build_payload_surfaces_value_throughput_drift_even_when_dispatch_is_green() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "queue_total": 12,
        "queue_dispatchable": 8,
        "queue_blocked": 2,
        "current_stop_state": "none",
        "dispatch_status": "success",
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
            "suppressed_queue_count": 2,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {},
    }

    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {
                "active_claim_task_id": "workstream:validation-and-publication",
                "active_claim_task_title": "Validation and Publication",
                "active_claim_lane_family": "validation_and_checkpoint",
                "autonomous_queue": [
                    {
                        "task_id": "workstream:validation-and-publication",
                        "title": "Validation and Publication",
                        "selected_provider_label": "Claude Code",
                        "selected_provider_id": "claude_code",
                        "status": "dispatched",
                        "proof_command_or_eval_surface": "python scripts/validate_platform_contract.py",
                        "approved_mutation_class": "auto_read_only",
                        "value_class": "failing_eval_or_validator",
                        "max_concurrency": 1,
                    }
                ],
                "automation_feedback_summary": {
                    "recent_dispatch_outcomes": [
                        {
                            "completed_at": "2026-04-18T23:43:06+00:00",
                            "task_id": "workstream:validation-and-publication",
                            "task_title": "Validation and Publication",
                            "dispatch_outcome": "success",
                            "summary": "Validation and Publication redispatched successfully.",
                        }
                    ]
                },
            }
        if path == module.VALUE_THROUGHPUT_SCORECARD_PATH:
            return {
                "reconciliation": {"issue_count": 2},
                "stale_claim_count": 0,
                "degraded_sections": ["backlog:fallback_to_ralph_queue_truth"],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {
                    "cash_now": 0,
                    "bounded_follow_on": 0,
                    "program_slice": 0,
                    "family_count": 0,
                    "family_ids": [],
                },
                "queue": {
                    "total": 12,
                    "dispatchable": 8,
                    "blocked": 2,
                    "suppressed": 2,
                },
                "runtime_packets": {"count": 0},
                "proof_gate": {"open": False, "status": "closed", "blocking_check_ids": ["result_backed_threshold"]},
                "auto_mutation": {"state": "repo_safe_only_runtime_and_provider_mutations_gated", "proof_gate_open": False},
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["intervention_level"] == "review_recommended"
    assert payload["needs_you"] is True
    assert payload["operator_mode"] == "active_closure"
    assert "value-throughput reconciliation reports `2` repairable issue(s)" in payload["reopen_reasons"]
    assert "value-throughput scorecard is degraded (`1` section(s))" in payload["reopen_reasons"]
    assert payload["value_throughput"]["reconciliation_issue_count"] == 2
    assert payload["value_throughput"]["degraded_sections"] == ["backlog:fallback_to_ralph_queue_truth"]


def test_build_payload_prefers_blocker_map_for_remaining_family_counts_and_next_tranche() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "queue_total": 1,
        "queue_dispatchable": 1,
        "queue_blocked": 0,
        "current_stop_state": "none",
        "dispatch_status": "success",
        "next_unblocked_candidate": {},
        "finish_scoreboard": {
            "closure_state": "closure_in_progress",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 9,
            "only_typed_brakes_remain": False,
            "suppressed_queue_count": 0,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {},
    }

    def _load_optional_json(path: Path):
        if path == module.RALPH_LATEST_PATH:
            return {}
        if path == module.VALUE_THROUGHPUT_SCORECARD_PATH:
            return {
                "reconciliation": {"issue_count": 0},
                "stale_claim_count": 0,
                "degraded_sections": [],
            }
        if path == module.BLOCKER_MAP_PATH:
            return {
                "remaining": {
                    "cash_now": 0,
                    "bounded_follow_on": 0,
                    "program_slice": 4,
                    "family_count": 4,
                    "family_ids": [
                        "control-plane-registry-and-routing",
                        "agent-execution-kernel-follow-on",
                        "agent-route-contract-follow-on",
                        "control-plane-proof-and-ops-follow-on",
                    ],
                },
                "next_tranche": {
                    "id": "control-plane-registry-and-routing",
                    "title": "Control-Plane Registry and Routing",
                    "match_count": 10,
                    "decomposition_required": False,
                },
                "queue": {
                    "total": 12,
                    "dispatchable": 8,
                    "blocked": 2,
                    "suppressed": 2,
                },
                "runtime_packets": {"count": 0},
                "proof_gate": {"open": False, "status": "closed", "blocking_check_ids": ["stable_operating_day"]},
                "auto_mutation": {"state": "repo_safe_only_runtime_and_provider_mutations_gated", "proof_gate_open": False},
            }
        return {}

    module._load_optional_json = _load_optional_json

    payload = module.build_payload()

    assert payload["program_slice_remaining_count"] == 4
    assert payload["queue_total"] == 12
    assert payload["queue_dispatchable"] == 8
    assert payload["queue_blocked"] == 2
    assert payload["suppressed_task_count"] == 2
    assert payload["next_up"]["task_title"] == "Control-Plane Registry and Routing"
    assert payload["blocker_map"]["remaining_family_ids"][0] == "control-plane-registry-and-routing"


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
                "blocker_map": "reports/truth-inventory/blocker-map.json",
            },
        }
    )

    assert "# Steady-State Status" in rendered
    assert "## Operating Contract" in rendered
    assert "This tracked document is durable by design." in rendered
    assert "steady-state-live.md" in rendered
    assert "blocker-map.json" in rendered
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


def test_build_payload_prefers_specific_next_operator_action_for_proof_brake() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    module.build_restart_snapshot = lambda: {
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": None,
        "active_claim_task_title": None,
        "active_claim_lane_family": None,
        "queue_total": 1,
        "queue_dispatchable": 0,
        "queue_blocked": 1,
        "current_stop_state": "proof_required",
        "next_unblocked_candidate": {},
        "finish_scoreboard": {
            "closure_state": "repo_safe_complete",
            "cash_now_remaining_count": 0,
            "bounded_follow_on_remaining_count": 0,
            "program_slice_remaining_count": 0,
            "only_typed_brakes_remain": False,
            "suppressed_queue_count": 0,
        },
        "runtime_packet_inbox": {"packet_count": 0, "packets": []},
        "artifacts": {},
    }
    module._load_optional_json = lambda path: {
        "active_claim_task_id": None,
        "active_claim_task_title": None,
        "active_claim_lane_family": None,
        "autonomous_queue": [
            {
                "task_id": "capability:agent-governance-toolkit-policy-plane",
                "title": "Agent Governance Toolkit Policy Plane",
                "dispatchable": False,
                "suppressed_by_continuity": False,
                "blocking_reason": "proof_required",
                "pilot_blocker_class": "non_duplicative_value_unproven",
            }
        ],
        "automation_feedback_summary": {"recent_dispatch_outcomes": []},
    }

    payload = module.build_payload()

    assert payload["intervention_level"] == "system_attention_required"
    assert payload["next_operator_action"].startswith("Capture a bounded non-duplicative proof slice for Agent Governance Toolkit Policy Plane")


def test_normalized_payload_ignores_generated_at() -> None:
    module = _load_module(
        f"write_steady_state_status_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_steady_state_status.py",
    )

    older = {"generated_at": "2026-04-16T20:00:00+00:00", "operator_mode": "steady_state_monitoring"}
    newer = {"generated_at": "2026-04-16T21:00:00+00:00", "operator_mode": "steady_state_monitoring"}

    assert module._normalized_payload(older) == module._normalized_payload(newer)
