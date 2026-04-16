from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLICATION_DEFERRED_QUEUE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "publication-deferred-family-queue.json"
RUNTIME_OWNERSHIP_PACKETS_PATH = REPO_ROOT / "config" / "automation-backbone" / "runtime-ownership-packets.json"
FINISH_SCOREBOARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "finish-scoreboard.json"
RUNTIME_PACKET_INBOX_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-packet-inbox.json"
DISPATCH_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"


def _clean_str(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_publication_deferred_queue() -> dict[str, Any]:
    return _load_json(PUBLICATION_DEFERRED_QUEUE_PATH)


def load_runtime_packets() -> dict[str, Any]:
    return _load_json(RUNTIME_OWNERSHIP_PACKETS_PATH)


def load_dispatch_state() -> dict[str, Any]:
    return _load_json(DISPATCH_STATE_PATH)


def _pick_queue_counts(ralph_report: dict[str, Any], dispatch_state: dict[str, Any]) -> tuple[int, int, int, int]:
    queue_summary = dict(ralph_report.get("autonomous_queue_summary") or {})
    dispatch_summary = dict(dispatch_state.get("autonomous_queue_summary") or {})

    dispatchable = int(
        dispatch_state.get("dispatchable_queue_count")
        or dispatch_summary.get("dispatchable_queue_count")
        or dispatch_summary.get("dispatchable_count")
        or queue_summary.get("dispatchable_queue_count")
        or queue_summary.get("dispatchable_count")
        or 0
    )
    blocked = int(
        dispatch_summary.get("blocked_queue_count")
        or dispatch_summary.get("blocked_count")
        or queue_summary.get("blocked_queue_count")
        or queue_summary.get("blocked_count")
        or max(0, int(dispatch_state.get("eligible_queue_count") or 0) - dispatchable)
    )
    total = int(
        dispatch_state.get("eligible_queue_count")
        or dispatch_summary.get("queue_count")
        or dispatch_summary.get("total_count")
        or queue_summary.get("queue_count")
        or queue_summary.get("total_count")
        or dispatchable + blocked
    )
    suppressed = int(
        dispatch_summary.get("suppressed_queue_count")
        or dispatch_summary.get("suppressed_count")
        or queue_summary.get("suppressed_queue_count")
        or queue_summary.get("suppressed_count")
        or 0
    )
    return total, dispatchable, blocked, suppressed


def _families_by_class(publication_queue: dict[str, Any], execution_class: str) -> list[dict[str, Any]]:
    families = publication_queue.get("families")
    if not isinstance(families, list):
        return []
    return [
        dict(item)
        for item in families
        if isinstance(item, dict)
        and str(item.get("execution_class") or "").strip() == execution_class
        and int(item.get("match_count") or 0) > 0
    ]


def build_runtime_packet_inbox(runtime_packets_payload: dict[str, Any]) -> dict[str, Any]:
    packets = runtime_packets_payload.get("packets")
    ready_packets = [
        dict(packet)
        for packet in packets
        if isinstance(packets, list)
        and isinstance(packet, dict)
        and str(packet.get("status") or "").strip() == "ready_for_approval"
    ]
    inbox_packets = []
    for packet in ready_packets:
        exact_steps = packet.get("exact_steps") if isinstance(packet.get("exact_steps"), list) else []
        inbox_packets.append(
            {
                "id": _clean_str(packet.get("id")),
                "label": _clean_str(packet.get("label")),
                "lane_id": _clean_str(packet.get("lane_id")),
                "host": _clean_str(packet.get("host")),
                "approval_type": _clean_str(packet.get("approval_packet_type")),
                "goal": _clean_str(packet.get("goal")),
                "readiness_state": _clean_str(packet.get("status")) or "unknown",
                "required_preflight": [
                    str(item).strip()
                    for item in packet.get("preflight_commands", [])
                    if str(item).strip()
                ],
                "rollback_path": [
                    str(item).strip()
                    for item in packet.get("rollback_steps", [])
                    if str(item).strip()
                ],
                "post_mutation_verification": [
                    str(item).strip()
                    for item in packet.get("verification_commands", [])
                    if str(item).strip()
                ],
                "next_operator_action": (
                    str(exact_steps[0]).strip()
                    if exact_steps
                    else "Review packet and approve the bounded runtime mutation."
                ),
                "evidence_paths": [
                    str(item).strip()
                    for item in packet.get("evidence_paths", [])
                    if str(item).strip()
                ],
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_count": len(inbox_packets),
        "packets": inbox_packets,
    }


def build_finish_scoreboard(
    ralph_report: dict[str, Any],
    publication_queue: dict[str, Any],
    runtime_packet_inbox: dict[str, Any],
    dispatch_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cash_now = _families_by_class(publication_queue, "cash_now")
    bounded_follow_on = _families_by_class(publication_queue, "bounded_follow_on")
    program_slice = _families_by_class(publication_queue, "program_slice")
    tenant_lane = _families_by_class(publication_queue, "tenant_lane")

    dispatch_state = dict(dispatch_state or {})
    queue_summary = dict(ralph_report.get("autonomous_queue_summary") or {})
    next_candidate = dict(ralph_report.get("next_unblocked_candidate") or {})
    next_deferred_family = dict(publication_queue.get("next_recommended_family") or {})
    queue_total_count, dispatchable_queue_count, blocked_queue_count, suppressed_queue_count = _pick_queue_counts(ralph_report, dispatch_state)
    approval_gated_runtime_packet_count = int(runtime_packet_inbox.get("packet_count") or 0)
    repo_safe_debt_remaining = bool(cash_now or bounded_follow_on or program_slice)
    only_typed_brakes_remain = (
        not repo_safe_debt_remaining
        and approval_gated_runtime_packet_count > 0
    )
    if repo_safe_debt_remaining:
        closure_state = "closure_in_progress"
    elif approval_gated_runtime_packet_count > 0:
        closure_state = "typed_brakes_only"
    else:
        closure_state = "repo_safe_complete"

    include_next_candidate = repo_safe_debt_remaining

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_claim_task_id": _clean_str(dispatch_state.get("current_task_id") or ralph_report.get("active_claim_task_id")),
        "active_claim_task_title": _clean_str(dispatch_state.get("current_task_title") or ralph_report.get("active_claim_task_title")),
        "selected_workstream_id": _clean_str(
            ralph_report.get("selected_workstream_id") or ralph_report.get("selected_workstream")
        ),
        "repo_side_no_delta": bool(ralph_report.get("repo_side_no_delta")),
        "rotation_ready": bool(ralph_report.get("rotation_ready")),
        "closure_state": closure_state,
        "only_typed_brakes_remain": only_typed_brakes_remain,
        "cash_now_remaining_count": len(cash_now),
        "cash_now_remaining_family_ids": [
            _clean_str(item.get("id")) for item in cash_now if _clean_str(item.get("id"))
        ],
        "bounded_follow_on_remaining_count": len(bounded_follow_on),
        "bounded_follow_on_remaining_family_ids": [
            _clean_str(item.get("id")) for item in bounded_follow_on if _clean_str(item.get("id"))
        ],
        "program_slice_remaining_count": len(program_slice),
        "program_slice_remaining_family_ids": [
            _clean_str(item.get("id")) for item in program_slice if _clean_str(item.get("id"))
        ],
        "tenant_lane_remaining_count": len(tenant_lane),
        "tenant_lane_remaining_family_ids": [
            _clean_str(item.get("id")) for item in tenant_lane if _clean_str(item.get("id"))
        ],
        "approval_gated_runtime_packet_count": approval_gated_runtime_packet_count,
        "approval_gated_runtime_packet_ids": [
            _clean_str(item.get("id"))
            for item in runtime_packet_inbox.get("packets", [])
            if isinstance(item, dict) and _clean_str(item.get("id"))
        ],
        "queue_total_count": queue_total_count,
        "queue_dispatchable_count": dispatchable_queue_count,
        "queue_blocked_count": blocked_queue_count,
        "suppressed_queue_count": suppressed_queue_count,
        "next_deferred_family_id": (
            _clean_str(next_deferred_family.get("id")) if include_next_candidate else None
        ),
        "next_deferred_family_title": (
            _clean_str(next_deferred_family.get("title")) if include_next_candidate else None
        ),
        "next_unblocked_candidate_task_id": (
            _clean_str(next_candidate.get("task_id") or next_candidate.get("id"))
            if include_next_candidate
            else None
        ),
        "next_unblocked_candidate_title": (
            _clean_str(next_candidate.get("title")) if include_next_candidate else None
        ),
    }
