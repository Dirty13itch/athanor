#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from session_restart_brief import build_restart_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
RALPH_LATEST_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
VALUE_THROUGHPUT_SCORECARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "value-throughput-scorecard.json"
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
BLOCKER_EXECUTION_PLAN_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-execution-plan.json"
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
STEADY_STATE_STATUS_JSON_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
STEADY_STATE_LIVE_MD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-live.md"
STEADY_STATE_STATUS_DOC_PATH = REPO_ROOT / "docs" / "operations" / "STEADY-STATE-STATUS.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pick_int(*values: Any, default: int = 0) -> int:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and value.strip():
            try:
                return int(value.strip())
            except ValueError:
                continue
    return default


def _runtime_packet_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    packets = payload.get("packets")
    if not isinstance(packets, list):
        return []
    return [dict(item) for item in packets if isinstance(item, dict)]


def _runtime_packet_target(runtime_packets: dict[str, Any]) -> dict[str, Any]:
    packets = _runtime_packet_list(runtime_packets)
    if not packets:
        return {}
    packet = packets[0]
    return {
        "kind": "runtime_packet",
        "family_id": "runtime-packet-inbox",
        "family_title": "Runtime Packet Inbox",
        "subtranche_id": _pick_string(packet.get("id")),
        "subtranche_title": _pick_string(packet.get("label"), packet.get("id")),
        "execution_class": "approval_gated_runtime_packet",
        "approval_gated": True,
        "external_blocked": False,
        "host": _pick_string(packet.get("host")),
        "approval_type": _pick_string(packet.get("approval_type")),
        "readiness_state": _pick_string(packet.get("readiness_state")) or "unknown",
        "detail": _pick_string(packet.get("goal")),
        "next_operator_action": _pick_string(packet.get("next_operator_action")),
    }


def _pick_queue(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("ranked_autonomous_queue", "autonomous_queue"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _find_task(queue: list[dict[str, Any]], task_id: str | None) -> dict[str, Any]:
    if not task_id:
        return {}
    for item in queue:
        if _pick_string(item.get("task_id"), item.get("id")) == task_id:
            return item
    return {}


def _first_blocked_task(queue: list[dict[str, Any]]) -> dict[str, Any]:
    for item in queue:
        if not bool(item.get("dispatchable")) and not bool(item.get("suppressed_by_continuity")):
            return item
    return {}


def _parse_event_time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            return text
    return None


def _attention_level(
    reopen_required: bool,
    closure_state: str,
    runtime_packet_count: int,
    stop_state: str,
    dispatch_status: str,
    continuity_status: str,
    continuity_skip_reason: str | None,
) -> tuple[str, str]:
    if stop_state and stop_state != "none":
        return ("system_attention_required", f"Ralph surfaced stop_state={stop_state}.")
    if dispatch_status in {"failed", "stale_dispatched_task", "spin_detected"}:
        return ("system_attention_required", f"Governed dispatch is currently `{dispatch_status}`.")
    if runtime_packet_count > 0:
        return ("approval_required", f"{runtime_packet_count} runtime packet(s) require approval or operator execution.")
    if reopen_required or closure_state not in {"repo_safe_complete", "typed_brakes_only"}:
        return ("review_recommended", "Closure debt or reopen conditions are active.")
    if continuity_status == "skipped":
        if continuity_skip_reason == "backoff_active":
            return ("no_action_needed", "Core closure is complete and the live lane is in bounded backoff.")
        return ("no_action_needed", "Core closure is complete and the live lane is paused.")
    if continuity_status == "idle":
        return ("no_action_needed", "Core closure is complete and the live lane is idle.")
    return ("no_action_needed", "Core closure is complete and the live lane is running.")


def _attention_label(level: str) -> str:
    return {
        "no_action_needed": "No action needed",
        "review_recommended": "Review recommended",
        "approval_required": "Approval required",
        "system_attention_required": "System attention required",
    }.get(level, level)


def _recent_activity(ralph: dict[str, Any], limit: int = 8) -> list[dict[str, str]]:
    summary = dict(ralph.get("automation_feedback_summary") or {})
    outcomes = summary.get("recent_dispatch_outcomes")
    if not isinstance(outcomes, list):
        return []
    items: list[dict[str, str]] = []
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        items.append(
            {
                "at": _parse_event_time(outcome.get("completed_at")) or "unknown",
                "task_id": _pick_string(outcome.get("task_id")) or "unknown",
                "task_title": _pick_string(outcome.get("task_title"), outcome.get("task_id")) or "unknown",
                "dispatch_outcome": _pick_string(outcome.get("dispatch_outcome")) or "unknown",
                "summary": _pick_string(outcome.get("summary")) or "No summary available.",
            }
        )
        if len(items) >= limit:
            break
    return items


def build_payload() -> dict[str, Any]:
    snapshot = build_restart_snapshot()
    finish = dict(snapshot.get("finish_scoreboard") or {})
    runtime = dict(snapshot.get("runtime_packet_inbox") or {})
    ralph = _load_optional_json(RALPH_LATEST_PATH)
    value_throughput = _load_optional_json(VALUE_THROUGHPUT_SCORECARD_PATH)
    blocker_map = _load_optional_json(BLOCKER_MAP_PATH)
    blocker_execution_plan = _load_optional_json(BLOCKER_EXECUTION_PLAN_PATH)
    continuity_controller = _load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH)
    queue = _pick_queue(ralph)

    closure_state = str(finish.get("closure_state") or "unknown")
    remaining = dict(blocker_map.get("remaining") or {})
    blocker_next_tranche = dict(blocker_map.get("next_tranche") or {})
    blocker_queue = dict(blocker_map.get("queue") or {})
    blocker_runtime_packets = dict(blocker_map.get("runtime_packets") or {})
    proof_gate = dict(blocker_map.get("proof_gate") or {})
    auto_mutation = dict(blocker_map.get("auto_mutation") or {})
    execution_plan_next_target = dict(blocker_execution_plan.get("next_target") or {})
    continuity_status = _pick_string(continuity_controller.get("controller_status")) or "unknown"
    continuity_skip_reason = _pick_string(continuity_controller.get("last_skip_reason"))
    cash_now_remaining_count = _pick_int(remaining.get("cash_now"), finish.get("cash_now_remaining_count"))
    bounded_follow_on_remaining_count = _pick_int(
        remaining.get("bounded_follow_on"),
        finish.get("bounded_follow_on_remaining_count"),
    )
    program_slice_remaining_count = _pick_int(
        remaining.get("program_slice"),
        finish.get("program_slice_remaining_count"),
    )
    runtime_packet_count = _pick_int(blocker_runtime_packets.get("count"), runtime.get("packet_count"))
    stop_state = _pick_string(snapshot.get("current_stop_state")) or "none"
    dispatch_status = _pick_string(snapshot.get("dispatch_status")) or "unknown"
    value_throughput_reconciliation = dict(value_throughput.get("reconciliation") or {})
    value_throughput_issue_count = int(value_throughput_reconciliation.get("issue_count") or 0)
    value_throughput_stale_claim_count = int(value_throughput.get("stale_claim_count") or 0)
    value_throughput_degraded_sections = [
        str(item).strip()
        for item in value_throughput.get("degraded_sections", [])
        if isinstance(item, str) and item.strip()
    ]

    reopen_reasons: list[str] = []
    if cash_now_remaining_count > 0:
        reopen_reasons.append(f"cash_now repo-safe debt remains (`{cash_now_remaining_count}`)")
    if bounded_follow_on_remaining_count > 0:
        reopen_reasons.append(f"bounded follow-on debt remains (`{bounded_follow_on_remaining_count}`)")
    if program_slice_remaining_count > 0:
        reopen_reasons.append(f"program-slice debt remains (`{program_slice_remaining_count}`)")
    if runtime_packet_count > 0:
        reopen_reasons.append(f"runtime packet inbox still has `{runtime_packet_count}` packets")
    if closure_state not in {"repo_safe_complete", "typed_brakes_only"}:
        reopen_reasons.append(f"finish scoreboard closure_state is `{closure_state}`")
    if stop_state != "none":
        reopen_reasons.append(f"Ralph stop_state is `{stop_state}`")
    if dispatch_status in {"failed", "stale_dispatched_task", "spin_detected"}:
        reopen_reasons.append(f"governed dispatch is `{dispatch_status}`")
    if value_throughput_issue_count > 0:
        reopen_reasons.append(
            f"value-throughput reconciliation reports `{value_throughput_issue_count}` repairable issue(s)"
        )
    if value_throughput_stale_claim_count > 0:
        reopen_reasons.append(
            f"value-throughput still reports `{value_throughput_stale_claim_count}` stale claim(s)"
        )
    if value_throughput_degraded_sections:
        reopen_reasons.append(
            f"value-throughput scorecard is degraded (`{len(value_throughput_degraded_sections)}` section(s))"
        )

    operator_mode = "steady_state_monitoring" if not reopen_reasons and closure_state == "repo_safe_complete" else "active_closure"
    reopen_required = operator_mode != "steady_state_monitoring"
    intervention_level, intervention_summary = _attention_level(
        reopen_required=reopen_required,
        closure_state=closure_state,
        runtime_packet_count=runtime_packet_count,
        stop_state=stop_state,
        dispatch_status=dispatch_status,
        continuity_status=continuity_status,
        continuity_skip_reason=continuity_skip_reason,
    )

    active_claim_task_id = _pick_string(ralph.get("active_claim_task_id"), snapshot.get("active_claim_task_id"))
    active_claim = _find_task(queue, active_claim_task_id)
    blocked_candidate = _first_blocked_task(queue)
    next_candidate = dict(ralph.get("next_unblocked_candidate") or snapshot.get("next_unblocked_candidate") or {})
    runtime_packet_next = _runtime_packet_target(runtime)
    effective_next_target = runtime_packet_next or execution_plan_next_target

    current_work = {
        "task_id": active_claim_task_id,
        "task_title": _pick_string(ralph.get("active_claim_task_title"), snapshot.get("active_claim_task_title")),
        "lane_family": _pick_string(ralph.get("active_claim_lane_family"), snapshot.get("active_claim_lane_family")),
        "provider_label": _pick_string(active_claim.get("selected_provider_label")),
        "provider_id": _pick_string(active_claim.get("selected_provider_id")),
        "dispatch_status": _pick_string(dispatch_status, active_claim.get("status")),
        "proof_surface": _pick_string(active_claim.get("proof_command_or_eval_surface")),
        "mutation_class": _pick_string(active_claim.get("approved_mutation_class")),
        "value_class": _pick_string(active_claim.get("value_class")),
        "max_concurrency": active_claim.get("max_concurrency"),
    }
    next_up = {
        "task_id": _pick_string(
            runtime_packet_next.get("subtranche_id"),
            next_candidate.get("task_id"),
            next_candidate.get("id"),
        ),
        "task_title": _pick_string(
            runtime_packet_next.get("subtranche_title"),
            next_candidate.get("title"),
            next_candidate.get("task_title"),
            execution_plan_next_target.get("subtranche_title"),
            execution_plan_next_target.get("family_title"),
            blocker_next_tranche.get("title"),
            finish.get("next_deferred_family_title"),
            finish.get("next_deferred_family_id"),
        ),
        "provider_label": _pick_string(next_candidate.get("selected_provider_label")),
        "lane_family": _pick_string(next_candidate.get("preferred_lane_family")),
    }

    if reopen_required:
        blocked_title = _pick_string(blocked_candidate.get("title"), blocked_candidate.get("task_id")) or "the next blocked lane"
        if stop_state == "proof_required":
            next_operator_action = (
                f"Capture a bounded non-duplicative proof slice for {blocked_title} before reopening autonomous continuation."
            )
        elif stop_state == "external_block":
            next_operator_action = (
                f"Clear the recorded external blocker on {blocked_title} before reopening autonomous continuation."
            )
        elif runtime_packet_count > 0:
            next_operator_action = "Review the runtime packet inbox and execute or approve the next bounded mutation packet."
        elif dispatch_status in {"failed", "stale_dispatched_task", "spin_detected"}:
            next_operator_action = (
                "Re-enter closure work through `python scripts/session_restart_brief.py --refresh` and repair the governed dispatch failure before trusting steady-state posture."
            )
        else:
            next_operator_action = "Re-enter closure work through `python scripts/session_restart_brief.py --refresh` and cash the next surfaced debt family or runtime packet."
    else:
        next_operator_action = "Run `python scripts/run_steady_state_control_plane.py` for a fresh pass. Intervene only if attention level rises above `No action needed`."

    artifacts = dict(snapshot.get("artifacts") or {})
    artifacts.update(
        {
            "steady_state_status_json": str(STEADY_STATE_STATUS_JSON_PATH),
            "steady_state_live_md": str(STEADY_STATE_LIVE_MD_PATH),
            "steady_state_status_doc": str(STEADY_STATE_STATUS_DOC_PATH),
            "blocker_map": str(BLOCKER_MAP_PATH),
            "blocker_execution_plan": str(BLOCKER_EXECUTION_PLAN_PATH),
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
        }
    )

    return {
        "generated_at": _iso_now(),
        "operator_mode": operator_mode,
        "intervention_level": intervention_level,
        "intervention_label": _attention_label(intervention_level),
        "intervention_summary": intervention_summary,
        "needs_you": intervention_level != "no_action_needed",
        "reopen_required": reopen_required,
        "reopen_reasons": reopen_reasons,
        "closure_state": closure_state,
        "cash_now_remaining_count": cash_now_remaining_count,
        "bounded_follow_on_remaining_count": bounded_follow_on_remaining_count,
        "program_slice_remaining_count": program_slice_remaining_count,
        "runtime_packet_count": runtime_packet_count,
        "only_typed_brakes_remain": bool(finish.get("only_typed_brakes_remain")),
        "selected_workstream_id": snapshot.get("selected_workstream_id"),
        "selected_workstream_title": snapshot.get("selected_workstream_title"),
        "current_work": current_work,
        "next_target": effective_next_target,
        "next_up": next_up,
        "queue_total": _pick_int(blocker_queue.get("total"), snapshot.get("queue_total")),
        "queue_dispatchable": _pick_int(blocker_queue.get("dispatchable"), snapshot.get("queue_dispatchable")),
        "queue_blocked": _pick_int(blocker_queue.get("blocked"), snapshot.get("queue_blocked")),
        "suppressed_task_count": _pick_int(
            blocker_queue.get("suppressed"),
            finish.get("suppressed_queue_count"),
            snapshot.get("suppressed_task_count"),
        ),
        "value_throughput": {
            "reconciliation_issue_count": value_throughput_issue_count,
            "stale_claim_count": value_throughput_stale_claim_count,
            "degraded_sections": value_throughput_degraded_sections,
        },
        "blocker_map": {
            "remaining_family_count": _pick_int(remaining.get("family_count"), default=0),
            "remaining_family_ids": remaining.get("family_ids", []),
            "next_tranche": {
                "id": blocker_next_tranche.get("id"),
                "title": blocker_next_tranche.get("title"),
                "match_count": _pick_int(blocker_next_tranche.get("match_count"), default=0),
                "decomposition_required": bool(blocker_next_tranche.get("decomposition_required")),
            },
            "proof_gate": {
                "open": bool(proof_gate.get("open")),
                "status": _pick_string(proof_gate.get("status")) or "unknown",
                "blocking_check_ids": proof_gate.get("blocking_check_ids", []),
            },
            "auto_mutation": {
                "state": _pick_string(auto_mutation.get("state")) or "unknown",
                "proof_gate_open": bool(auto_mutation.get("proof_gate_open")),
            },
        },
        "proof_gate": {
            "open": bool(proof_gate.get("open")),
            "status": _pick_string(proof_gate.get("status")) or "unknown",
            "blocking_check_ids": proof_gate.get("blocking_check_ids", []),
        },
        "continuity_controller": {
            "status": _pick_string(continuity_controller.get("controller_status")) or "unknown",
            "active_pass_id": _pick_string(continuity_controller.get("active_pass_id")),
            "active_family_id": _pick_string(continuity_controller.get("active_family_id")),
            "active_subtranche_id": _pick_string(continuity_controller.get("active_subtranche_id")),
            "last_skip_reason": _pick_string(continuity_controller.get("last_skip_reason")),
            "backoff_until": _pick_string(continuity_controller.get("backoff_until")),
            "next_target": {
                "kind": _pick_string(effective_next_target.get("kind")) or "unknown",
                "family_id": _pick_string(effective_next_target.get("family_id")),
                "family_title": _pick_string(effective_next_target.get("family_title")),
                "subtranche_id": _pick_string(effective_next_target.get("subtranche_id")),
                "subtranche_title": _pick_string(effective_next_target.get("subtranche_title")),
                "approval_gated": bool(effective_next_target.get("approval_gated")),
            },
        },
        "continuity": {
            "controller_status": _pick_string(continuity_controller.get("controller_status")) or "unknown",
            "controller_host": _pick_string(continuity_controller.get("controller_host")) or "dev",
            "controller_mode": _pick_string(continuity_controller.get("controller_mode")) or "unknown",
            "typed_brake": _pick_string(continuity_controller.get("typed_brake")),
            "last_skip_reason": _pick_string(continuity_controller.get("last_skip_reason")),
            "backoff_until": _pick_string(continuity_controller.get("backoff_until")),
        },
        "runtime_packet_next": runtime_packet_next,
        "next_operator_action": next_operator_action,
        "reopen_triggers": [
            "finish-scoreboard reports non-zero repo-safe debt",
            "runtime-packet-inbox packet_count rises above zero",
            "session restart brief or Ralph artifacts surface a typed brake",
            "live validation/probe evidence materially reopens Athanor core truth",
        ],
        "recent_activity": _recent_activity(ralph),
        "artifacts": artifacts,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    artifacts = dict(payload.get("artifacts") or {})
    lines = [
        "# Steady-State Status",
        "",
        "Do not edit manually.",
        "",
        "## Purpose",
        "",
        "- This tracked document is the durable operator contract for steady-state monitoring and reopen handling.",
        "- Live claim rotation, provider routing, queue posture, and recent activity belong in the ignored live feed and machine JSON, not in repo-tracked markdown.",
        "- Read the live feed first when you need to know what Athanor is doing right now.",
        f"- Live operator feed: `{artifacts.get('steady_state_live_md', '')}`",
        f"- Machine proof: `{artifacts.get('steady_state_status_json', '')}`",
        f"- Canonical blocker map: `{artifacts.get('blocker_map', '')}`",
        f"- Blocker execution plan: `{artifacts.get('blocker_execution_plan', '')}`",
        f"- Continuity controller state: `{artifacts.get('continuity_controller_state', '')}`",
        "",
        "## Operating Contract",
        "",
        "- This tracked document is durable by design.",
        "- `docs/operations/STEADY-STATE-STATUS.md` should only change when the operator contract or proof paths change.",
        "- `reports/truth-inventory/steady-state-live.md` is the volatile front door for current work, next up, queue posture, and recent activity.",
        "- `reports/truth-inventory/steady-state-status.json` is the machine-readable source for intervention level, reopen state, and queue counts.",
        "- `reports/truth-inventory/blocker-map.json` is the canonical remaining-work source for family counts, next tranche selection, proof-gate posture, and auto-mutation state.",
        "- `reports/truth-inventory/blocker-execution-plan.json` is the canonical bounded sub-tranche plan when a family requires decomposition.",
        "- `reports/truth-inventory/continuity-controller-state.json` is the machine-readable controller lock, skip, and backoff state for the thread heartbeat lane.",
        "- `reports/ralph-loop/latest.json` remains the deeper live dispatch proof when operator surfaces need forensic confirmation.",
        "",
        "## Operator Action",
        "",
        "- Start with the live operator feed to see the current lane, provider, and next handoff.",
        "- If the JSON or live feed raises attention above `No action needed`, re-enter through `python scripts/session_restart_brief.py --refresh`.",
        "- Use the finish scoreboard and runtime packet inbox before making closure or reopen claims.",
        "",
        "## Reopen Triggers",
        "",
    ]
    lines.extend(f"- {item}" for item in payload.get("reopen_triggers", []))

    lines.extend([
        "",
        "## Active Reopen Reasons",
        "",
    ])
    lines.append("- Read `reports/truth-inventory/steady-state-status.json` for the current reopen reasons.")

    lines.extend([
        "",
        "## Evidence",
        "",
        f"- Ralph loop: `{artifacts.get('ralph_latest', '')}`",
        f"- Finish scoreboard: `{artifacts.get('finish_scoreboard', '')}`",
        f"- Runtime packet inbox: `{artifacts.get('runtime_packet_inbox', '')}`",
        f"- Blocker map: `{artifacts.get('blocker_map', '')}`",
        f"- Blocker execution plan: `{artifacts.get('blocker_execution_plan', '')}`",
        f"- Continuity controller state: `{artifacts.get('continuity_controller_state', '')}`",
        f"- Session restart brief source: `python scripts/session_restart_brief.py --refresh`",
        f"- Live operator feed: `{artifacts.get('steady_state_live_md', '')}`",
        f"- Steady-state JSON: `{artifacts.get('steady_state_status_json', '')}`",
        "- Cross-system read: `docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md`, `docs/operations/ATHANOR-OPERATOR-MODEL.md`, `docs/operations/ATHANOR-ECOSYSTEM-DEPENDENCY-MAP.md`",
        "",
    ])
    return "\n".join(lines)


def render_live_markdown(payload: dict[str, Any]) -> str:
    current_work = dict(payload.get("current_work") or {})
    next_up = dict(payload.get("next_up") or {})
    recent_activity = payload.get("recent_activity") if isinstance(payload.get("recent_activity"), list) else []
    reopen_reasons = payload.get("reopen_reasons") if isinstance(payload.get("reopen_reasons"), list) else []
    blocker_map = dict(payload.get("blocker_map") or {})
    continuity_controller = dict(payload.get("continuity_controller") or {})
    next_tranche = dict(blocker_map.get("next_tranche") or {})
    proof_gate = dict(blocker_map.get("proof_gate") or {})
    auto_mutation = dict(blocker_map.get("auto_mutation") or {})
    continuity_next_target = dict(payload.get("next_target") or continuity_controller.get("next_target") or {})
    runtime_packet_next = dict(payload.get("runtime_packet_next") or {})
    lines = [
        "# Steady-State Live Operator Feed",
        "",
        "Volatile live surface. Generated from current Athanor runtime truth.",
        "",
        "## At A Glance",
        "",
        f"- System state: `{payload.get('closure_state', 'unknown')}`",
        f"- Attention level: `{payload.get('intervention_label', 'unknown')}`",
        f"- Current work: `{_pick_string(current_work.get('task_title'), current_work.get('task_id')) or 'unknown'}`",
        f"- Current provider: `{_pick_string(current_work.get('provider_label'), current_work.get('provider_id')) or 'unknown'}`",
        f"- Current lane: `{_pick_string(current_work.get('lane_family')) or 'unknown'}`",
        f"- Dispatch status: `{_pick_string(current_work.get('dispatch_status')) or 'unknown'}`",
        f"- Next up: `{_pick_string(next_up.get('task_title'), next_up.get('task_id')) or 'unknown'}`",
        f"- Queue posture: total=`{payload.get('queue_total', 'unknown')}` | dispatchable=`{payload.get('queue_dispatchable', 'unknown')}` | blocked=`{payload.get('queue_blocked', 'unknown')}` | suppressed=`{payload.get('suppressed_task_count', 'unknown')}`",
        f"- Remaining blocker families: `{blocker_map.get('remaining_family_count', 'unknown')}`",
        f"- Next tranche: `{_pick_string(next_tranche.get('title'), next_tranche.get('id')) or 'unknown'}`",
        f"- Continuity controller: `{_pick_string(continuity_controller.get('status')) or 'unknown'}`",
        f"- Active continuity family: `{_pick_string(continuity_controller.get('active_family_id')) or 'none'}` | sub-tranche: `{_pick_string(continuity_controller.get('active_subtranche_id')) or 'none'}`",
        f"- Continuity skip/backoff: skip=`{_pick_string(continuity_controller.get('last_skip_reason')) or 'none'}` | backoff_until=`{_pick_string(continuity_controller.get('backoff_until')) or 'none'}`",
        f"- Next bounded target: `{_pick_string(continuity_next_target.get('subtranche_title'), continuity_next_target.get('family_title')) or 'unknown'}`",
        f"- Proof gate: `{_pick_string(proof_gate.get('status')) or 'unknown'}` | auto-mutation: `{_pick_string(auto_mutation.get('state')) or 'unknown'}`",
        f"- Needs you: `{payload.get('needs_you', 'unknown')}`",
        f"- Why: `{_pick_string(payload.get('intervention_summary')) or 'unknown'}`",
        "",
        "## Current Work",
        "",
        f"- Strategic workstream: `{_pick_string(payload.get('selected_workstream_title'), payload.get('selected_workstream_id')) or 'unknown'}`",
        f"- Mutation class: `{_pick_string(current_work.get('mutation_class')) or 'unknown'}` | value class: `{_pick_string(current_work.get('value_class')) or 'unknown'}`",
        f"- Proof surface: `{_pick_string(current_work.get('proof_surface')) or 'unknown'}`",
        f"- Max concurrency: `{current_work.get('max_concurrency', 'unknown')}`",
        "",
    ]
    if runtime_packet_next:
        lines.extend(
            [
                "## Runtime Packet Ready",
                "",
                f"- Packet: `{_pick_string(runtime_packet_next.get('subtranche_title'), runtime_packet_next.get('subtranche_id')) or 'unknown'}`",
                f"- Host: `{_pick_string(runtime_packet_next.get('host')) or 'unknown'}` | approval type: `{_pick_string(runtime_packet_next.get('approval_type')) or 'unknown'}` | state: `{_pick_string(runtime_packet_next.get('readiness_state')) or 'unknown'}`",
                f"- Goal: `{_pick_string(runtime_packet_next.get('detail')) or 'unknown'}`",
                f"- Next operator action: `{_pick_string(runtime_packet_next.get('next_operator_action')) or 'Review the runtime packet inbox and execute or approve the next bounded mutation packet.'}`",
                "",
            ]
        )
    lines.extend([
        "## Reopen State",
        "",
    ])
    if reopen_reasons:
        lines.extend(f"- {item}" for item in reopen_reasons)
    else:
        lines.append("- None.")
    lines.extend([
        "",
        "## Recent Activity",
        "",
    ])
    if recent_activity:
        seen: set[tuple[str, str, str]] = set()
        for item in recent_activity:
            signature = (
                str(item.get("task_title", "unknown")),
                str(item.get("dispatch_outcome", "unknown")),
                str(item.get("summary", "No summary available.")),
            )
            if signature in seen:
                continue
            seen.add(signature)
            lines.append(f"- `{signature[0]}` | outcome=`{signature[1]}` | {signature[2]}")
            if len(seen) >= 6:
                break
    else:
        lines.append("- No recent activity was materialized from the live Ralph record.")
    lines.append("")
    return "\n".join(lines)


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.pop("generated_at", None)
    return normalized


def _load_existing_json_payload() -> dict[str, Any] | None:
    if not STEADY_STATE_STATUS_JSON_PATH.exists():
        return None
    try:
        loaded = json.loads(STEADY_STATE_STATUS_JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Athanor steady-state operator status surfaces.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifacts.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when the tracked markdown or JSON artifact is stale.")
    args = parser.parse_args()

    payload = build_payload()
    existing_json_payload = _load_existing_json_payload()
    if existing_json_payload and _normalized_payload(existing_json_payload) == _normalized_payload(payload):
        payload["generated_at"] = str(existing_json_payload.get("generated_at") or payload["generated_at"])
    rendered_json = _json_render(payload)
    rendered_markdown = render_markdown(payload)
    rendered_live_markdown = render_live_markdown(payload)

    if args.check:
        stale = False
        existing_markdown = STEADY_STATE_STATUS_DOC_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_DOC_PATH.exists() else ""
        existing_live_markdown = STEADY_STATE_LIVE_MD_PATH.read_text(encoding="utf-8") if STEADY_STATE_LIVE_MD_PATH.exists() else ""
        existing_json_payload = _load_existing_json_payload()
        if _normalized_payload(existing_json_payload or {}) != _normalized_payload(payload):
            print(f"{STEADY_STATE_STATUS_JSON_PATH} is stale")
            stale = True
        if existing_markdown != rendered_markdown:
            print(f"{STEADY_STATE_STATUS_DOC_PATH} is stale")
            stale = True
        if existing_live_markdown != rendered_live_markdown:
            print(f"{STEADY_STATE_LIVE_MD_PATH} is stale")
            stale = True
        return 1 if stale else 0

    STEADY_STATE_STATUS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    STEADY_STATE_STATUS_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    STEADY_STATE_LIVE_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    if (STEADY_STATE_STATUS_JSON_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_JSON_PATH.exists() else "") != rendered_json:
        STEADY_STATE_STATUS_JSON_PATH.write_text(rendered_json, encoding="utf-8")
    if (STEADY_STATE_STATUS_DOC_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_DOC_PATH.exists() else "") != rendered_markdown:
        STEADY_STATE_STATUS_DOC_PATH.write_text(rendered_markdown, encoding="utf-8")
    if (STEADY_STATE_LIVE_MD_PATH.read_text(encoding="utf-8") if STEADY_STATE_LIVE_MD_PATH.exists() else "") != rendered_live_markdown:
        STEADY_STATE_LIVE_MD_PATH.write_text(rendered_live_markdown, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(STEADY_STATE_STATUS_DOC_PATH))
        print(str(STEADY_STATE_LIVE_MD_PATH))
        print(str(STEADY_STATE_STATUS_JSON_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
