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
STEADY_STATE_STATUS_JSON_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
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


def _attention_level(reopen_required: bool, closure_state: str, runtime_packet_count: int, stop_state: str) -> tuple[str, str]:
    if stop_state and stop_state != "none":
        return ("system_attention_required", f"Ralph surfaced stop_state={stop_state}.")
    if runtime_packet_count > 0:
        return ("approval_required", f"{runtime_packet_count} runtime packet(s) require approval or operator execution.")
    if reopen_required or closure_state not in {"repo_safe_complete", "typed_brakes_only"}:
        return ("review_recommended", "Closure debt or reopen conditions are active.")
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
    queue = _pick_queue(ralph)

    closure_state = str(finish.get("closure_state") or "unknown")
    cash_now_remaining_count = int(finish.get("cash_now_remaining_count") or 0)
    bounded_follow_on_remaining_count = int(finish.get("bounded_follow_on_remaining_count") or 0)
    program_slice_remaining_count = int(finish.get("program_slice_remaining_count") or 0)
    runtime_packet_count = int(runtime.get("packet_count") or 0)
    stop_state = _pick_string(snapshot.get("current_stop_state")) or "none"

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

    operator_mode = "steady_state_monitoring" if not reopen_reasons and closure_state == "repo_safe_complete" else "active_closure"
    reopen_required = operator_mode != "steady_state_monitoring"
    intervention_level, intervention_summary = _attention_level(
        reopen_required=reopen_required,
        closure_state=closure_state,
        runtime_packet_count=runtime_packet_count,
        stop_state=stop_state,
    )

    active_claim_task_id = _pick_string(ralph.get("active_claim_task_id"), snapshot.get("active_claim_task_id"))
    active_claim = _find_task(queue, active_claim_task_id)
    next_candidate = dict(ralph.get("next_unblocked_candidate") or snapshot.get("next_unblocked_candidate") or {})

    current_work = {
        "task_id": active_claim_task_id,
        "task_title": _pick_string(ralph.get("active_claim_task_title"), snapshot.get("active_claim_task_title")),
        "lane_family": _pick_string(ralph.get("active_claim_lane_family"), snapshot.get("active_claim_lane_family")),
        "provider_label": _pick_string(active_claim.get("selected_provider_label")),
        "provider_id": _pick_string(active_claim.get("selected_provider_id")),
        "dispatch_status": _pick_string(snapshot.get("dispatch_status"), active_claim.get("status")),
        "proof_surface": _pick_string(active_claim.get("proof_command_or_eval_surface")),
        "mutation_class": _pick_string(active_claim.get("approved_mutation_class")),
        "value_class": _pick_string(active_claim.get("value_class")),
        "max_concurrency": active_claim.get("max_concurrency"),
    }
    next_up = {
        "task_id": _pick_string(next_candidate.get("task_id"), next_candidate.get("id")),
        "task_title": _pick_string(next_candidate.get("title"), next_candidate.get("task_title"), finish.get("next_deferred_family_title"), finish.get("next_deferred_family_id")),
        "provider_label": _pick_string(next_candidate.get("selected_provider_label")),
        "lane_family": _pick_string(next_candidate.get("preferred_lane_family")),
    }

    if reopen_required:
        next_operator_action = "Re-enter closure work through `python scripts/session_restart_brief.py --refresh` and cash the next surfaced debt family or runtime packet."
    else:
        next_operator_action = "Run `python scripts/run_steady_state_control_plane.py` for a fresh pass. Intervene only if attention level rises above `No action needed`."

    artifacts = dict(snapshot.get("artifacts") or {})
    artifacts.update(
        {
            "steady_state_status_json": str(STEADY_STATE_STATUS_JSON_PATH),
            "steady_state_status_doc": str(STEADY_STATE_STATUS_DOC_PATH),
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
        "next_up": next_up,
        "queue_total": snapshot.get("queue_total"),
        "queue_dispatchable": snapshot.get("queue_dispatchable"),
        "queue_blocked": snapshot.get("queue_blocked"),
        "suppressed_task_count": finish.get("suppressed_queue_count", snapshot.get("suppressed_task_count")),
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
    current_work = dict(payload.get("current_work") or {})
    next_up = dict(payload.get("next_up") or {})
    artifacts = dict(payload.get("artifacts") or {})
    recent_activity = payload.get("recent_activity") if isinstance(payload.get("recent_activity"), list) else []
    lines = [
        "# Steady-State Status",
        "",
        "Do not edit manually.",
        "",
        "## At A Glance",
        "",
        f"- System state: `{payload.get('closure_state', 'unknown')}`",
        f"- Attention level: `{payload.get('intervention_label', 'unknown')}`",
        f"- Needs you: `{payload.get('needs_you', False)}`",
        f"- Why: {payload.get('intervention_summary', 'unknown')}",
        f"- Current work: `{_pick_string(current_work.get('task_title'), current_work.get('task_id')) or 'unknown'}`",
        f"- Current provider: `{_pick_string(current_work.get('provider_label'), current_work.get('provider_id')) or 'unknown'}`",
        f"- Current lane: `{_pick_string(current_work.get('lane_family')) or 'unknown'}`",
        f"- Dispatch status: `{_pick_string(current_work.get('dispatch_status')) or 'unknown'}`",
        f"- Next up: `{_pick_string(next_up.get('task_title'), next_up.get('task_id')) or 'unknown'}`",
        f"- Queue posture: total=`{payload.get('queue_total', 'unknown')}` | dispatchable=`{payload.get('queue_dispatchable', 'unknown')}` | blocked=`{payload.get('queue_blocked', 'unknown')}` | suppressed=`{payload.get('suppressed_task_count', 'unknown')}`",
        "",
        "## Current Work",
        "",
        f"- Strategic workstream: `{_pick_string(payload.get('selected_workstream_title'), payload.get('selected_workstream_id')) or 'unknown'}`",
        f"- Mutation class: `{_pick_string(current_work.get('mutation_class')) or 'unknown'}` | value class: `{_pick_string(current_work.get('value_class')) or 'unknown'}`",
        f"- Proof surface: `{_pick_string(current_work.get('proof_surface')) or 'unknown'}`",
        f"- Max concurrency: `{current_work.get('max_concurrency', 'unknown')}`",
        f"- Repo-safe debt: cash_now=`{payload.get('cash_now_remaining_count', 'unknown')}` | bounded_follow_on=`{payload.get('bounded_follow_on_remaining_count', 'unknown')}` | program_slice=`{payload.get('program_slice_remaining_count', 'unknown')}` | runtime_packets=`{payload.get('runtime_packet_count', 'unknown')}`",
        "",
        "## What Changed Recently",
        "",
    ]
    if recent_activity:
        seen: set[tuple[str, str, str]] = set()
        for item in recent_activity:
            signature = (
                str(item.get('task_title', 'unknown')),
                str(item.get('dispatch_outcome', 'unknown')),
                str(item.get('summary', 'No summary available.')),
            )
            if signature in seen:
                continue
            seen.add(signature)
            lines.append(
                f"- `{signature[0]}` | outcome=`{signature[1]}` | {signature[2]}"
            )
            if len(seen) >= 6:
                break
    else:
        lines.append("- No recent activity was materialized from the live Ralph record.")

    lines.extend([
        "",
        "## Operator Action",
        "",
        f"- {payload.get('next_operator_action', 'unknown')}",
    ])
    if _pick_string(next_up.get("provider_label"), next_up.get("lane_family"), next_up.get("task_title")):
        lines.append(
            f"- Prepared next handoff: `{_pick_string(next_up.get('task_title'), next_up.get('task_id')) or 'unknown'}` via `{_pick_string(next_up.get('provider_label'), next_up.get('lane_family')) or 'unknown'}`"
        )

    lines.extend([
        "",
        "## Reopen Triggers",
        "",
    ])
    lines.extend(f"- {item}" for item in payload.get("reopen_triggers", []))

    lines.extend([
        "",
        "## Active Reopen Reasons",
        "",
    ])
    if payload.get("reopen_reasons"):
        lines.extend(f"- {item}" for item in payload.get("reopen_reasons", []))
    else:
        lines.append("- None.")

    lines.extend([
        "",
        "## Evidence",
        "",
        f"- Ralph loop: `{artifacts.get('ralph_latest', '')}`",
        f"- Finish scoreboard: `{artifacts.get('finish_scoreboard', '')}`",
        f"- Runtime packet inbox: `{artifacts.get('runtime_packet_inbox', '')}`",
        f"- Session restart brief source: `python scripts/session_restart_brief.py --refresh`",
        f"- Steady-state JSON: `{artifacts.get('steady_state_status_json', '')}`",
        "- Cross-system read: `docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md`, `docs/operations/ATHANOR-OPERATOR-MODEL.md`, `docs/operations/ATHANOR-ECOSYSTEM-DEPENDENCY-MAP.md`",
        "",
    ])
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

    if args.check:
        stale = False
        existing_markdown = STEADY_STATE_STATUS_DOC_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_DOC_PATH.exists() else ""
        existing_json_payload = _load_existing_json_payload()
        if _normalized_payload(existing_json_payload or {}) != _normalized_payload(payload):
            print(f"{STEADY_STATE_STATUS_JSON_PATH} is stale")
            stale = True
        if existing_markdown != rendered_markdown:
            print(f"{STEADY_STATE_STATUS_DOC_PATH} is stale")
            stale = True
        return 1 if stale else 0

    STEADY_STATE_STATUS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    STEADY_STATE_STATUS_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    if (STEADY_STATE_STATUS_JSON_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_JSON_PATH.exists() else "") != rendered_json:
        STEADY_STATE_STATUS_JSON_PATH.write_text(rendered_json, encoding="utf-8")
    if (STEADY_STATE_STATUS_DOC_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_DOC_PATH.exists() else "") != rendered_markdown:
        STEADY_STATE_STATUS_DOC_PATH.write_text(rendered_markdown, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(STEADY_STATE_STATUS_DOC_PATH))
        print(str(STEADY_STATE_STATUS_JSON_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
