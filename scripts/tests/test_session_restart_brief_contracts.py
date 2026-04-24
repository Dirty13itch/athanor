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


def test_render_restart_brief_surfaces_current_queue_and_harvest_posture() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-14T20:05:17+00:00",
        "loop_mode": "governor_scheduling",
        "provider_gate_state": "completed",
        "work_economy_status": "ready",
        "top_task_title": "Dispatch and Work-Economy Closure",
        "queue_total": 4,
        "queue_dispatchable": 3,
        "dispatch_status": "claimed",
        "dispatch_phase_label": "governed_dispatch_shadow",
        "queue": [
            {
                "title": "Dispatch and Work-Economy Closure",
                "value_class": "dispatch_truth_drift",
                "approved_mutation_class": "auto_harvest",
                "preferred_lane_family": "dispatch_truth_repair",
                "proof_command_or_eval_surface": "python scripts/run_gpu_scheduler_baseline_eval.py",
            },
            {
                "title": "Capacity and Harvest Truth",
                "value_class": "capacity_truth_drift",
                "approved_mutation_class": "auto_harvest",
                "preferred_lane_family": "capacity_truth_repair",
                "proof_command_or_eval_surface": "python scripts/collect_capacity_telemetry.py",
            },
        ],
        "harvest_summary": {
            "admission_state": "open_harvest_window",
            "ready_for_harvest_now": True,
            "harvestable_scheduler_slot_count": 2,
            "harvestable_zone_ids": ["F", "W"],
            "open_harvest_slot_target_ids": ["foundry-bulk-pool", "workshop-batch-support"],
        },
        "advisory_blockers": ["agent_runtime_restart_recovered"],
        "recent_commits": ["abc1234 Example commit"],
        "status_lines": [" M STATUS.md"],
        "diff_stat_lines": [" STATUS.md | 2 +-"],
        "canonical_docs": ["STATUS.md"],
        "control_surfaces": ["https://athanor.local/"],
        "artifacts": {
            "ralph_latest": "C:/Athanor/reports/ralph-loop/latest.json",
            "dispatch_state": "C:/Athanor/reports/truth-inventory/governed-dispatch-state.json",
            "capacity_telemetry": "C:/Athanor/reports/truth-inventory/capacity-telemetry.json",
            "next_rotation_preflight": "C:/Athanor/reports/truth-inventory/next-rotation-preflight.json",
            "finish_scoreboard": "C:/Athanor/reports/truth-inventory/finish-scoreboard.json",
            "runtime_packet_inbox": "C:/Athanor/reports/truth-inventory/runtime-packet-inbox.json",
            "steady_state_status": "C:/Athanor/reports/truth-inventory/steady-state-status.json",
            "master_atlas_latest": "C:/athanor-devstack/reports/master-atlas/latest.json",
        },
        "finish_scoreboard": {
            "closure_state": "closure_in_progress",
            "cash_now_remaining_count": 3,
            "bounded_follow_on_remaining_count": 1,
            "program_slice_remaining_count": 2,
            "only_typed_brakes_remain": False,
            "approval_gated_runtime_packet_count": 2,
            "next_deferred_family_id": "reference-and-archive-prune",
            "next_deferred_family_title": "Reference and Archive Prune",
        },
        "runtime_packet_inbox": {
            "packet_count": 2,
            "packets": [
                {
                    "id": "dev-runtime-ssh-access-recovery-packet",
                    "label": "DEV Runtime SSH Access Recovery",
                    "host": "DEV",
                    "approval_type": "runtime_reconfiguration",
                    "readiness_state": "ready_for_approval",
                    "goal": "Restore governed SSH reachability for DEV.",
                    "next_operator_action": "Review packet and approve the bounded runtime mutation.",
                }
            ],
        },
        "steady_state_status": {
            "operator_mode": "active_closure",
            "reopen_required": True,
            "next_operator_action": "Re-enter closure work.",
            "reopen_reasons": ["cash_now repo-safe debt remains (`3`)"]
        },
    }

    rendered = module.render_restart_brief(snapshot)

    assert "# Athanor Session Restart Brief" in rendered
    assert "`governor_scheduling`" in rendered
    assert "Dispatch and Work-Economy Closure" in rendered
    assert "open_harvest_window" in rendered
    assert "foundry-bulk-pool" in rendered
    assert "agent_runtime_restart_recovered" in rendered
    assert "https://athanor.local/" in rendered
    assert "## Closure Scoreboard" in rendered
    assert "## Runtime Packet Inbox" in rendered
    assert "## Steady-State Status" in rendered
    assert "Reference and Archive Prune" in rendered


    assert "Premium Interactive" not in rendered


def test_render_restart_brief_surfaces_on_deck_candidate_and_suppression_context() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-15T21:31:14+00:00",
        "loop_mode": "evidence_refresh",
        "selected_workstream": "Dispatch and Work-Economy Closure",
        "top_task_title": "Premium Async",
        "active_claim_task_title": "Premium Async",
        "continue_allowed": True,
        "current_stop_state": "none",
        "queue_total": 6,
        "queue_dispatchable": 2,
        "dispatch_status": "claimed",
        "dispatch_phase_label": "governed_dispatch_shadow",
        "queue": [],
        "next_unblocked_candidate": {
            "title": "Premium Interactive",
            "task_id": "burn_class:premium_interactive",
            "id": "burn_class:premium_interactive",
            "preferred_lane_family": "dispatch_truth_repair",
            "source_type": "burn_class",
        },
        "suppressed_task_ids": [
            "workstream:dispatch-and-work-economy-closure",
            "burn_class:overnight_harvest",
        ],
        "suppressed_task_count": 2,
        "next_rotation_preflight": {
            "preflight_available": True,
            "next_candidate_task_id": "burn_class:premium_interactive",
            "next_candidate_title": "Premium Interactive",
            "preflight": {
                "routing_chain": ["anthropic_claude_code"],
                "approved_task_families": ["interactive_architecture", "final_review"],
                "preferred_lane_family": "dispatch_truth_repair",
                "approved_mutation_class": "auto_harvest",
                "dispatchable": True,
                "max_concurrency": 1,
                "reserve_rule": "preserve_operator_spike_capacity",
                "selected_provider_label": "Claude Code",
                "proof_command_or_eval_surface": "reports/truth-inventory/quota-truth.json",
                "queue_dispatchable": 2,
                "queue_blocked": 0,
                "suppressed_task_count": 2,
            },
        },
        "canonical_docs": [],
        "control_surfaces": [],
        "artifacts": {},
    }

    rendered = module.render_restart_brief(snapshot)

    assert "Premium Interactive" in rendered
    assert "burn_class:premium_interactive" in rendered
    assert "preflight_burn_class.py premium_interactive --json" in rendered
    assert "Inspect burn-class readiness with `python scripts/preflight_burn_class.py premium_interactive --json` before the next rotation." in rendered
    assert "Next burn-class rotation on deck: `burn_class:premium_interactive`; preflight it with `python scripts/preflight_burn_class.py premium_interactive --json`." in rendered
    assert "dispatch_truth_repair" in rendered
    assert "## Next Rotation Preflight" in rendered
    assert "Routing chain: `anthropic_claude_code`" in rendered
    assert "Queue posture: dispatchable=`2` | blocked=`0` | suppressed=`2`" in rendered
    assert "Continuity suppressions" in rendered
    assert "workstream:dispatch-and-work-economy-closure" in rendered


def test_build_restart_snapshot_reads_git_and_live_artifacts(tmp_path: Path) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    ralph_path = tmp_path / "ralph.json"
    dispatch_path = tmp_path / "dispatch.json"
    capacity_path = tmp_path / "capacity.json"
    atlas_path = tmp_path / "atlas.json"
    next_rotation_preflight_path = tmp_path / "next-rotation-preflight.json"
    finish_scoreboard_path = tmp_path / "finish-scoreboard.json"
    runtime_packet_inbox_path = tmp_path / "runtime-packet-inbox.json"
    steady_state_status_path = tmp_path / "steady-state-status.json"

    ralph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14T20:05:17+00:00",
                "loop_mode": "governor_scheduling",
                "provider_gate_state": "completed",
                "work_economy_status": "ready",
                "selected_workstream_id": "dispatch-and-work-economy-closure",
                "selected_workstream": "dispatch-and-work-economy-closure",
                "selected_workstream_title": "Dispatch and Work-Economy Closure",
                "top_task": {"title": "Dispatch and Work-Economy Closure", "task_id": "workstream:dispatch"},
                "ranked_autonomous_queue": [
                    {"title": "Dispatch and Work-Economy Closure", "id": "workstream:dispatch"}
                ],
                "autonomous_queue_summary": {"total_count": 9, "dispatchable_count": 7},
            }
        ),
        encoding="utf-8",
    )
    dispatch_path.write_text(
        json.dumps(
            {
                "dispatch_outcome": "claimed",
                "dispatch_phase_label": "governed_dispatch_shadow",
                "governed_dispatch_ready": True,
                "advisory_blockers": ["agent_runtime_restart_recovered"],
                "capacity_harvest_summary": {
                    "admission_state": "open_harvest_window",
                    "ready_for_harvest_now": True,
                    "harvestable_scheduler_slot_count": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    capacity_path.write_text(json.dumps({"capacity_summary": {"scheduler_slot_count": 5}}), encoding="utf-8")
    atlas_path.write_text(json.dumps({"generated_at": "2026-04-14T20:05:17+00:00"}), encoding="utf-8")
    next_rotation_preflight_path.write_text(
        json.dumps({
            "preflight_available": True,
            "next_candidate_task_id": "burn_class:local_bulk_sovereign",
            "preflight": {"dispatchable": True}
        }),
        encoding="utf-8",
    )
    finish_scoreboard_path.write_text(
        json.dumps({
            "closure_state": "closure_in_progress",
            "cash_now_remaining_count": 3,
            "approval_gated_runtime_packet_count": 2,
        }),
        encoding="utf-8",
    )
    runtime_packet_inbox_path.write_text(
        json.dumps({
            "packet_count": 2,
            "packets": [{"id": "dev-runtime-ssh-access-recovery-packet"}],
        }),
        encoding="utf-8",
    )
    steady_state_status_path.write_text(
        json.dumps({
            "operator_mode": "active_closure",
            "reopen_required": True,
            "next_operator_action": "Re-enter closure work.",
        }),
        encoding="utf-8",
    )

    module.RALPH_LATEST_PATH = ralph_path
    module.DISPATCH_STATE_PATH = dispatch_path
    module.CAPACITY_TELEMETRY_PATH = capacity_path
    module.NEXT_ROTATION_PREFLIGHT_PATH = next_rotation_preflight_path
    module.FINISH_SCOREBOARD_PATH = finish_scoreboard_path
    module.RUNTIME_PACKET_INBOX_PATH = runtime_packet_inbox_path
    module.STEADY_STATE_STATUS_PATH = steady_state_status_path
    module.ATLAS_LATEST_PATH = atlas_path
    module._run_git = lambda *args: {
        ("status", "--short"): [" M STATUS.md"],
        ("diff", "--stat"): [" STATUS.md | 2 +-"],
        ("log", "--oneline", "-5"): ["abc1234 Example commit"],
    }.get(tuple(args), [])

    snapshot = module.build_restart_snapshot()

    assert snapshot["loop_mode"] == "governor_scheduling"
    assert snapshot["provider_gate_state"] == "completed"
    assert snapshot["work_economy_status"] == "ready"
    assert snapshot["queue_total"] == 9
    assert snapshot["queue_dispatchable"] == 7
    assert snapshot["queue_blocked"] == 0
    assert snapshot["selected_workstream_id"] == "dispatch-and-work-economy-closure"
    assert snapshot["next_rotation_preflight"]["next_candidate_task_id"] == "burn_class:local_bulk_sovereign"
    assert snapshot["finish_scoreboard"]["closure_state"] == "closure_in_progress"
    assert snapshot["runtime_packet_inbox"]["packet_count"] == 2
    assert snapshot["steady_state_status"]["operator_mode"] == "active_closure"
    assert snapshot["dispatch_status"] == "claimed"
    assert snapshot["advisory_blockers"] == ["agent_runtime_restart_recovered"]
    assert snapshot["status_lines"] == [" M STATUS.md"]


def test_run_refresh_uses_current_python_and_ralph_loop_script(monkeypatch) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    recorded: dict[str, object] = {}

    class Completed:
        returncode = 0

    def fake_run(command, cwd=None, capture_output=None, text=None, encoding=None, errors=None, check=None):  # noqa: ANN001
        recorded["command"] = command
        recorded["cwd"] = cwd
        recorded["capture_output"] = capture_output
        recorded["text"] = text
        recorded["encoding"] = encoding
        recorded["errors"] = errors
        recorded["check"] = check
        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_refresh()

    assert recorded["command"] == [module.sys.executable, str(module.RALPH_LOOP_SCRIPT), "--skip-validation"]
    assert recorded["cwd"] == module.REPO_ROOT
    assert recorded["capture_output"] is True
    assert recorded["text"] is True
    assert recorded["encoding"] == "utf-8"
    assert recorded["errors"] == "replace"
    assert recorded["check"] is False


def test_render_restart_brief_surfaces_executive_brief_contract() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-16T03:40:28+00:00",
        "loop_mode": "evidence_refresh",
        "selected_workstream": "dispatch-and-work-economy-closure",
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "burn_class:promotion_eval",
        "active_claim_task_title": "Promotion Eval",
        "active_claim_lane_family": "promotion_wave_closure",
        "next_action_family": "dispatch_truth_and_queue_replenishment",
        "execution_posture": "steady_state",
        "evidence_freshness": "stale",
        "next_checkpoint_slice_id": "backbone-contracts-and-truth-writers",
        "next_checkpoint_slice_title": "Backbone Contracts and Truth Writers",
        "continue_allowed": True,
        "current_stop_state": "none",
        "dispatch_status": "dispatched",
        "queue_total": 12,
        "queue_dispatchable": 1,
        "queue_blocked": 11,
        "queue": [],
        "canonical_docs": [],
        "control_surfaces": [],
        "artifacts": {},
        "executive_brief": {
            "program_state": {
                "selected_workstream_title": "Dispatch and Work-Economy Closure",
                "active_claim_task_title": "Promotion Eval",
                "loop_mode": "evidence_refresh",
                "execution_posture": "steady_state",
                "continue_allowed": True,
                "stop_state": "none",
                "next_checkpoint_slice_id": "backbone-contracts-and-truth-writers",
                "next_checkpoint_slice_title": "Backbone Contracts and Truth Writers",
                "next_action_family": "dispatch_truth_and_queue_replenishment",
            },
            "landed_or_delta": {
                "summary": "Active claim Promotion Eval is dispatched. Validators stayed green on this pass.",
                "dispatch_status": "dispatched",
                "rotation_reason": "recent_no_delta_suppressed",
            },
            "proof": {
                "validation_summary": "4/4 validation checks passed.",
                "evidence_freshness": "stale",
                "dispatch_status": "dispatched",
            },
            "risks": [
                {"id": "queue_pressure", "severity": "medium", "summary": "11 queue items remain blocked while 1 is dispatchable."},
                {"id": "suppressed_queue_items", "severity": "low", "summary": "2 queue items are continuity-suppressed rather than blocked."},
            ],
            "delegation": {
                "main_agent_focus": "Promotion Eval (burn_class:promotion_eval)",
                "delegation_posture": "Keep truth arbitration local.",
                "delegate_now": ["Bounded read-only verification for Reference and Archive Prune."],
            },
            "next_moves": [
                "Keep Promotion Eval active until it yields a typed brake or a verified no-delta outcome.",
            ],
            "decision_needed": None,
        },
    }

    rendered = module.render_restart_brief(snapshot)

    assert "## Executive Brief" in rendered
    assert "### Program State" in rendered
    assert "### Landed / Delta" in rendered
    assert "### Proof" in rendered
    assert "### Risks" in rendered
    assert "### Delegation" in rendered
    assert "### Next Moves" in rendered
    assert "### Decision Needed" in rendered
    assert "Promotion Eval" in rendered
    assert "`12` total / `1` dispatchable / `11` blocked" in rendered
    assert "`dispatch-and-work-economy-closure`" in rendered
    assert "queue_pressure" in rendered
    assert "4/4 validation checks passed." in rendered
    assert "Backbone Contracts and Truth Writers" in rendered


def test_render_restart_brief_surfaces_repo_side_no_delta_contract() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-16T05:10:00+00:00",
        "loop_mode": "governor_scheduling",
        "selected_workstream": "dispatch-and-work-economy-closure",
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "active_claim_lane_family": "validation_and_checkpoint",
        "next_action_family": "validation_and_checkpoint",
        "execution_posture": "active_remediation",
        "evidence_freshness": "fresh",
        "repo_side_no_delta": True,
        "rotation_ready": True,
        "reopen_reason_scope": "dispatch_evidence_chain_only",
        "no_delta_evidence_refs": [
            "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
        ],
        "continue_allowed": True,
        "current_stop_state": "none",
        "dispatch_status": "claimed",
        "queue_total": 5,
        "queue_dispatchable": 2,
        "queue": [],
        "canonical_docs": [],
        "control_surfaces": [],
        "artifacts": {},
        "executive_brief": {
            "program_state": {
                "selected_workstream_title": "Dispatch and Work-Economy Closure",
                "active_claim_task_title": "Validation and Publication",
                "loop_mode": "governor_scheduling",
                "execution_posture": "active_remediation",
                "continue_allowed": True,
                "stop_state": "none",
                "repo_side_no_delta": True,
                "rotation_ready": True,
                "reopen_reason_scope": "dispatch_evidence_chain_only",
                "next_action_family": "validation_and_checkpoint",
            },
            "landed_or_delta": {
                "summary": "Dispatch and Work-Economy Closure is verified repo-side no-delta.",
                "dispatch_status": "claimed",
                "rotation_reason": "recent_no_delta_suppressed",
            },
            "proof": {
                "validation_summary": "4/4 validation checks passed.",
                "evidence_freshness": "fresh",
                "dispatch_status": "claimed",
                "no_delta_evidence_refs": [
                    "reports/truth-inventory/gpu-scheduler-baseline-eval.json",
                ],
            },
            "risks": [],
            "delegation": {
                "main_agent_focus": "Validation and Publication",
                "delegation_posture": "Keep truth arbitration local.",
                "delegate_now": [],
            },
            "next_moves": [
                "Rotate from Dispatch and Work-Economy Closure to Validation and Publication because repo-side no-delta is already verified.",
            ],
            "decision_needed": None,
        },
    }

    rendered = module.render_restart_brief(snapshot)

    assert "Repo-side no-delta" in rendered
    assert "dispatch_evidence_chain_only" in rendered
    assert "reports/truth-inventory/gpu-scheduler-baseline-eval.json" in rendered


def test_render_restart_brief_surfaces_finish_scoreboard_and_runtime_packet_inbox() -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    snapshot = {
        "repo_root": "C:/Athanor",
        "generated_at": "2026-04-16T08:15:00+00:00",
        "loop_mode": "governor_scheduling",
        "selected_workstream_id": "dispatch-and-work-economy-closure",
        "selected_workstream_title": "Dispatch and Work-Economy Closure",
        "active_claim_task_id": "workstream:validation-and-publication",
        "active_claim_task_title": "Validation and Publication",
        "continue_allowed": True,
        "current_stop_state": "none",
        "queue_total": 9,
        "queue_dispatchable": 7,
        "queue_blocked": 0,
        "queue": [],
        "canonical_docs": [],
        "control_surfaces": [],
        "artifacts": {},
        "finish_scoreboard": {
            "closure_state": "closure_in_progress",
            "cash_now_remaining_count": 3,
            "bounded_follow_on_remaining_count": 1,
            "program_slice_remaining_count": 2,
            "only_typed_brakes_remain": False,
            "approval_gated_runtime_packet_count": 2,
            "next_deferred_family_id": "reference-and-archive-prune",
            "next_deferred_family_title": "Reference and Archive Prune",
        },
        "runtime_packet_inbox": {
            "packet_count": 2,
            "packets": [
                {
                    "id": "dev-runtime-ssh-access-recovery-packet",
                    "label": "DEV Runtime SSH Access Recovery",
                    "host": "DEV",
                    "approval_type": "runtime_reconfiguration",
                    "readiness_state": "ready_for_approval",
                    "goal": "Restore governed SSH reachability for DEV.",
                    "next_operator_action": "Review packet and approve the bounded runtime mutation.",
                }
            ],
        },
        "steady_state_status": {
            "operator_mode": "active_closure",
            "reopen_required": True,
            "next_operator_action": "Re-enter closure work.",
            "reopen_reasons": ["cash_now repo-safe debt remains (`3`)"]
        },
    }

    rendered = module.render_restart_brief(snapshot)

    assert "## Closure Scoreboard" in rendered
    assert "cash_now=`3`" in rendered
    assert "approval-gated runtime packets=`2`" in rendered
    assert "## Runtime Packet Inbox" in rendered
    assert "DEV Runtime SSH Access Recovery" in rendered
    assert "Restore governed SSH reachability for DEV." in rendered


def test_build_restart_snapshot_prefers_live_suppressed_queue_count_over_continuity_history(tmp_path: Path) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    ralph_path = tmp_path / "ralph.json"
    dispatch_path = tmp_path / "dispatch.json"
    capacity_path = tmp_path / "capacity.json"
    atlas_path = tmp_path / "atlas.json"
    next_rotation_preflight_path = tmp_path / "next-rotation-preflight.json"
    finish_scoreboard_path = tmp_path / "finish-scoreboard.json"
    runtime_packet_inbox_path = tmp_path / "runtime-packet-inbox.json"
    steady_state_status_path = tmp_path / "steady-state-status.json"
    continuity_path = tmp_path / "continuity.json"
    publication_queue_path = tmp_path / "publication.json"

    ralph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-16T21:06:52+00:00",
                "active_claim_task_id": "burn_class:overnight_harvest",
                "active_claim_task_title": "Overnight Harvest",
                "autonomous_queue_summary": {
                    "queue_count": 12,
                    "dispatchable_queue_count": 5,
                    "blocked_queue_count": 0,
                    "suppressed_queue_count": 7,
                },
                "next_unblocked_candidate": {"task_id": "burn_class:cheap_bulk_cloud", "title": "Cheap Bulk Cloud"},
            }
        ),
        encoding="utf-8",
    )
    dispatch_path.write_text(json.dumps({"dispatchable_queue_count": 5, "eligible_queue_count": 5}), encoding="utf-8")
    capacity_path.write_text(json.dumps({}), encoding="utf-8")
    atlas_path.write_text(json.dumps({}), encoding="utf-8")
    next_rotation_preflight_path.write_text(json.dumps({}), encoding="utf-8")
    finish_scoreboard_path.write_text(json.dumps({}), encoding="utf-8")
    runtime_packet_inbox_path.write_text(json.dumps({"packet_count": 0, "packets": []}), encoding="utf-8")
    steady_state_status_path.write_text(json.dumps({}), encoding="utf-8")
    continuity_path.write_text(
        json.dumps(
            {
                "recent_no_delta_task_ids": [
                    "a","b","c","d","e","f","g","h"
                ],
                "continue_allowed": True,
                "current_stop_state": "none",
            }
        ),
        encoding="utf-8",
    )
    publication_queue_path.write_text(json.dumps({}), encoding="utf-8")

    module.RALPH_LATEST_PATH = ralph_path
    module.DISPATCH_STATE_PATH = dispatch_path
    module.CAPACITY_TELEMETRY_PATH = capacity_path
    module.ATLAS_LATEST_PATH = atlas_path
    module.NEXT_ROTATION_PREFLIGHT_PATH = next_rotation_preflight_path
    module.FINISH_SCOREBOARD_PATH = finish_scoreboard_path
    module.RUNTIME_PACKET_INBOX_PATH = runtime_packet_inbox_path
    module.STEADY_STATE_STATUS_PATH = steady_state_status_path
    module.RALPH_CONTINUITY_STATE_PATH = continuity_path
    module.PUBLICATION_DEFERRED_QUEUE_PATH = publication_queue_path
    module._run_git = lambda *args: []

    snapshot = module.build_restart_snapshot()

    assert snapshot["suppressed_task_count"] == 7
    assert len(snapshot["suppressed_task_ids"]) == 8


def test_build_restart_snapshot_prefers_fresher_finish_scoreboard_from_ralph(tmp_path: Path) -> None:
    module = _load_module(
        f"session_restart_brief_contracts_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "session_restart_brief.py",
    )

    ralph_path = tmp_path / "ralph.json"
    dispatch_path = tmp_path / "dispatch.json"
    capacity_path = tmp_path / "capacity.json"
    atlas_path = tmp_path / "atlas.json"
    next_rotation_preflight_path = tmp_path / "next-rotation-preflight.json"
    finish_scoreboard_path = tmp_path / "finish-scoreboard.json"
    runtime_packet_inbox_path = tmp_path / "runtime-packet-inbox.json"
    steady_state_status_path = tmp_path / "steady-state-status.json"
    continuity_path = tmp_path / "continuity.json"
    publication_queue_path = tmp_path / "publication.json"

    ralph_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T03:18:21+00:00",
                "finish_scoreboard": {
                    "generated_at": "2026-04-19T03:18:24+00:00",
                    "closure_state": "closure_in_progress",
                    "cash_now_remaining_count": 0,
                    "bounded_follow_on_remaining_count": 0,
                    "program_slice_remaining_count": 1,
                    "next_deferred_family_id": "control-plane-registry-and-routing",
                },
            }
        ),
        encoding="utf-8",
    )
    dispatch_path.write_text(json.dumps({}), encoding="utf-8")
    capacity_path.write_text(json.dumps({}), encoding="utf-8")
    atlas_path.write_text(json.dumps({}), encoding="utf-8")
    next_rotation_preflight_path.write_text(json.dumps({}), encoding="utf-8")
    finish_scoreboard_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T02:32:20+00:00",
                "closure_state": "closure_in_progress",
                "cash_now_remaining_count": 1,
                "bounded_follow_on_remaining_count": 0,
                "program_slice_remaining_count": 1,
                "next_deferred_family_id": "audit-and-eval-artifacts",
            }
        ),
        encoding="utf-8",
    )
    runtime_packet_inbox_path.write_text(json.dumps({"packet_count": 0, "packets": []}), encoding="utf-8")
    steady_state_status_path.write_text(json.dumps({}), encoding="utf-8")
    continuity_path.write_text(json.dumps({}), encoding="utf-8")
    publication_queue_path.write_text(json.dumps({}), encoding="utf-8")

    module.RALPH_LATEST_PATH = ralph_path
    module.DISPATCH_STATE_PATH = dispatch_path
    module.CAPACITY_TELEMETRY_PATH = capacity_path
    module.ATLAS_LATEST_PATH = atlas_path
    module.NEXT_ROTATION_PREFLIGHT_PATH = next_rotation_preflight_path
    module.FINISH_SCOREBOARD_PATH = finish_scoreboard_path
    module.RUNTIME_PACKET_INBOX_PATH = runtime_packet_inbox_path
    module.STEADY_STATE_STATUS_PATH = steady_state_status_path
    module.RALPH_CONTINUITY_STATE_PATH = continuity_path
    module.PUBLICATION_DEFERRED_QUEUE_PATH = publication_queue_path
    module._run_git = lambda *_args: []

    snapshot = module.build_restart_snapshot()

    assert snapshot["finish_scoreboard"]["cash_now_remaining_count"] == 0
    assert snapshot["finish_scoreboard"]["next_deferred_family_id"] == "control-plane-registry-and-routing"
