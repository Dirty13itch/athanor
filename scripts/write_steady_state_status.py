#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from session_restart_brief import build_restart_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
STEADY_STATE_STATUS_JSON_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
STEADY_STATE_STATUS_DOC_PATH = REPO_ROOT / "docs" / "operations" / "STEADY-STATE-STATUS.md"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_payload() -> dict[str, Any]:
    snapshot = build_restart_snapshot()
    finish = dict(snapshot.get("finish_scoreboard") or {})
    runtime = dict(snapshot.get("runtime_packet_inbox") or {})

    closure_state = str(finish.get("closure_state") or "unknown")
    cash_now_remaining_count = int(finish.get("cash_now_remaining_count") or 0)
    bounded_follow_on_remaining_count = int(finish.get("bounded_follow_on_remaining_count") or 0)
    program_slice_remaining_count = int(finish.get("program_slice_remaining_count") or 0)
    runtime_packet_count = int(runtime.get("packet_count") or 0)

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

    operator_mode = "steady_state_monitoring" if not reopen_reasons and closure_state == "repo_safe_complete" else "active_closure"
    reopen_required = operator_mode != "steady_state_monitoring"

    if reopen_required:
        next_operator_action = (
            "Re-enter closure work through `python scripts/session_restart_brief.py --refresh` and cash the next surfaced debt family or runtime packet."
        )
    else:
        next_operator_action = (
            "Monitor with `python scripts/run_steady_state_control_plane.py`; reopen only when finish-scoreboard debt reappears, runtime packets return, or a typed brake lands in live artifacts."
        )

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
        "active_claim_task_id": snapshot.get("active_claim_task_id"),
        "active_claim_task_title": snapshot.get("active_claim_task_title"),
        "queue_total": snapshot.get("queue_total"),
        "queue_dispatchable": snapshot.get("queue_dispatchable"),
        "queue_blocked": snapshot.get("queue_blocked"),
        "next_deferred_family_id": finish.get("next_deferred_family_id"),
        "next_deferred_family_title": finish.get("next_deferred_family_title"),
        "next_operator_action": next_operator_action,
        "reopen_triggers": [
            "finish-scoreboard reports non-zero repo-safe debt",
            "runtime-packet-inbox packet_count rises above zero",
            "session restart brief or Ralph artifacts surface a typed brake",
            "live validation/probe evidence materially reopens Athanor core truth",
        ],
        "artifacts": artifacts,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Steady-State Status",
        "",
        "Do not edit manually.",
        "",
        f"- Operator mode: `{payload.get('operator_mode', 'unknown')}`",
        f"- Closure state: `{payload.get('closure_state', 'unknown')}`",
        f"- Reopen required: `{payload.get('reopen_required', False)}`",
        f"- Repo-safe debt: cash_now=`{payload.get('cash_now_remaining_count', 'unknown')}` | bounded_follow_on=`{payload.get('bounded_follow_on_remaining_count', 'unknown')}` | program_slice=`{payload.get('program_slice_remaining_count', 'unknown')}`",
        f"- Runtime packet count: `{payload.get('runtime_packet_count', 'unknown')}`",
        f"- Queue posture: total=`{payload.get('queue_total', 'unknown')}` | dispatchable=`{payload.get('queue_dispatchable', 'unknown')}` | blocked=`{payload.get('queue_blocked', 'unknown')}`",
    ]
    if _pick_string(payload.get("active_claim_task_title"), payload.get("active_claim_task_id")):
        lines.append(
            f"- Active claim: `{_pick_string(payload.get('active_claim_task_title'), payload.get('active_claim_task_id'))}`"
        )
    if _pick_string(payload.get("selected_workstream_title"), payload.get("selected_workstream_id")):
        lines.append(
            f"- Strategic workstream: `{_pick_string(payload.get('selected_workstream_title'), payload.get('selected_workstream_id'))}`"
        )
    next_deferred_family = _pick_string(payload.get("next_deferred_family_title"), payload.get("next_deferred_family_id"))
    if next_deferred_family:
        lines.append(f"- Next deferred family if reopened: `{next_deferred_family}`")
    lines.extend([
        "",
        "## Next Operator Action",
        "",
        f"- {payload.get('next_operator_action', 'unknown')}",
        "",
        "## Reopen Triggers",
        "",
    ])
    lines.extend(f"- {item}" for item in payload.get("reopen_triggers", []))
    if payload.get("reopen_reasons"):
        lines.extend(["", "## Active Reopen Reasons", ""])
        lines.extend(f"- {item}" for item in payload.get("reopen_reasons", []))
    artifacts = payload.get("artifacts") or {}
    lines.extend([
        "",
        "## Artifacts",
        "",
        f"- Finish scoreboard: `{artifacts.get('finish_scoreboard', '')}`",
        f"- Runtime packet inbox: `{artifacts.get('runtime_packet_inbox', '')}`",
        f"- Session restart brief source: `python scripts/session_restart_brief.py --refresh`",
        f"- Steady-state JSON: `{artifacts.get('steady_state_status_json', '')}`",
    ])
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

    if args.check:
        stale = False
        existing_json = STEADY_STATE_STATUS_JSON_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_JSON_PATH.exists() else ""
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
    if STEADY_STATE_STATUS_JSON_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_JSON_PATH.exists() else "" != rendered_json:
        STEADY_STATE_STATUS_JSON_PATH.write_text(rendered_json, encoding="utf-8")
    if STEADY_STATE_STATUS_DOC_PATH.read_text(encoding="utf-8") if STEADY_STATE_STATUS_DOC_PATH.exists() else "" != rendered_markdown:
        STEADY_STATE_STATUS_DOC_PATH.write_text(rendered_markdown, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(STEADY_STATE_STATUS_DOC_PATH))
        print(str(STEADY_STATE_STATUS_JSON_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
