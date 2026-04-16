from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RALPH_LATEST_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"
DISPATCH_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "governed-dispatch-state.json"
CAPACITY_TELEMETRY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "capacity-telemetry.json"
PUBLICATION_DEFERRED_QUEUE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "publication-deferred-family-queue.json"
RALPH_CONTINUITY_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "ralph-continuity-state.json"
NEXT_ROTATION_PREFLIGHT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "next-rotation-preflight.json"
FINISH_SCOREBOARD_PATH = REPO_ROOT / "reports" / "truth-inventory" / "finish-scoreboard.json"
RUNTIME_PACKET_INBOX_PATH = REPO_ROOT / "reports" / "truth-inventory" / "runtime-packet-inbox.json"
STEADY_STATE_STATUS_PATH = REPO_ROOT / "reports" / "truth-inventory" / "steady-state-status.json"
ATLAS_LATEST_PATH = Path(r"C:\athanor-devstack\reports\master-atlas\latest.json")
CANONICAL_DOCS = [
    "STATUS.md",
    "docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md",
    "docs/operations/ATHANOR-OPERATING-SYSTEM.md",
    "docs/operations/REPO-STRUCTURE-RULES.md",
]
CONTROL_SURFACES = [
    "https://athanor.local/",
    "https://athanor.local/operator",
    "https://athanor.local/routing",
    "https://athanor.local/topology",
]
RALPH_LOOP_SCRIPT = REPO_ROOT / "scripts" / "run_ralph_loop_pass.py"


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _run_git(*args: str) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def _pick_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _pick_queue(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("ranked_autonomous_queue", "autonomous_queue"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _pick_queue_summary(ralph: dict[str, Any], dispatch: dict[str, Any], queue: list[dict[str, Any]]) -> tuple[Any, Any, Any]:
    summary = ralph.get("autonomous_queue_summary")
    if isinstance(summary, dict):
        total = summary.get("queue_count", summary.get("total_count", len(queue)))
        dispatchable = summary.get(
            "dispatchable_queue_count",
            summary.get(
                "dispatchable_count",
                dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False)),
            ),
        )
        blocked = summary.get("blocked_queue_count", summary.get("blocked_count", 0))
        return (total, dispatchable, blocked)
    summary = dispatch.get("autonomous_queue_summary")
    if isinstance(summary, dict):
        total = summary.get("queue_count", summary.get("total_count", len(queue)))
        dispatchable = summary.get(
            "dispatchable_queue_count",
            summary.get(
                "dispatchable_count",
                dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False)),
            ),
        )
        blocked = summary.get("blocked_queue_count", summary.get("blocked_count", 0))
        return (total, dispatchable, blocked)
    total = dispatch.get("eligible_queue_count", len(queue))
    dispatchable = dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False))
    blocked = max(0, int(total) - int(dispatchable))
    return (total, dispatchable, blocked)


def _pick_harvest_summary(dispatch: dict[str, Any], capacity: dict[str, Any]) -> dict[str, Any]:
    for key in ("capacity_harvest_summary", "capacity_signal"):
        value = dispatch.get(key)
        if isinstance(value, dict):
            return value
    summary = capacity.get("capacity_summary")
    if isinstance(summary, dict):
        return summary
    return {}


def _build_fallback_executive_brief(snapshot: dict[str, Any]) -> dict[str, Any]:
    next_candidate = dict(snapshot.get("next_unblocked_candidate") or {})
    risks: list[dict[str, Any]] = []
    stop_state = str(snapshot.get("current_stop_state") or "none")
    stop_reason = snapshot.get("current_stop_reason")
    if stop_state != "none":
        risks.append({"id": "typed_brake", "severity": "high", "summary": stop_reason or f"Stop state {stop_state} requires attention."})
    if snapshot.get("evidence_freshness") == "stale":
        risks.append({"id": "stale_evidence", "severity": "medium", "summary": "Evidence freshness is stale and should be refreshed before speculative work."})
    if snapshot.get("suppressed_task_count"):
        risks.append({"id": "continuity_pressure", "severity": "medium", "summary": f"{snapshot.get('suppressed_task_count')} tasks are continuity-suppressed right now."})

    next_moves = [
        f"Keep {_pick_string(snapshot.get('active_claim_task_title'), snapshot.get('selected_workstream_title'), snapshot.get('top_task_title')) or 'the current lane'} moving until it yields a typed brake or a verified no-delta outcome.",
    ]
    if next_candidate:
        next_moves.append(
            f"Rotate to {_pick_string(next_candidate.get('title'), next_candidate.get('task_id')) or 'the next candidate'} if the current claim yields no delta."
        )
    elif snapshot.get("publication_next_family_id"):
        next_moves.append(f"Cash deferred family {snapshot.get('publication_next_family_id')} when no unsuppressed workstream remains.")

    delegate_now = [
        f"Bounded verification for {_pick_string(next_candidate.get('title'), next_candidate.get('task_id')) or snapshot.get('publication_next_family_id') or 'the next feeder'} before the next rotation."
    ] if next_candidate or snapshot.get("publication_next_family_id") else []
    next_candidate_task_id = _pick_string(next_candidate.get("task_id"), next_candidate.get("id"))
    if next_candidate_task_id and next_candidate_task_id.startswith("burn_class:"):
        burn_class_id = next_candidate_task_id.split(":", 1)[1]
        delegate_now.append(
            f"Inspect burn-class readiness with `python scripts/preflight_burn_class.py {burn_class_id} --json` before the next rotation."
        )
        next_moves.append(
            f"Next burn-class rotation on deck: `{next_candidate_task_id}`; preflight it with `python scripts/preflight_burn_class.py {burn_class_id} --json`."
        )

    return {
        "program_state": {
            "loop_mode": snapshot.get("loop_mode"),
            "selected_workstream": snapshot.get("selected_workstream"),
            "selected_workstream_title": snapshot.get("selected_workstream_title"),
            "active_claim_task_id": snapshot.get("active_claim_task_id"),
            "active_claim_task_title": snapshot.get("active_claim_task_title"),
            "active_claim_lane_family": snapshot.get("active_claim_lane_family"),
            "next_action_family": snapshot.get("next_action_family"),
            "execution_posture": snapshot.get("execution_posture"),
            "continue_allowed": snapshot.get("continue_allowed"),
            "stop_state": stop_state,
        },
        "landed_or_delta": {
            "summary": f"Active claim {_pick_string(snapshot.get('active_claim_task_title'), snapshot.get('top_task_title')) or 'unknown'} is {_pick_string(snapshot.get('dispatch_status')) or 'unknown' }.",
        },
        "proof": {
            "validation_summary": "Refer to the latest Ralph validation block for exact command results.",
            "evidence_freshness": snapshot.get("evidence_freshness"),
            "dispatch_status": snapshot.get("dispatch_status"),
        },
        "risks": risks,
        "delegation": {
            "main_agent_focus": _pick_string(snapshot.get("active_claim_task_title"), snapshot.get("top_task_title")),
            "delegation_posture": "Keep truth arbitration and final integration local; delegate bounded read-only scans and feeder prep only.",
            "delegate_now": delegate_now,
        },
        "next_moves": next_moves[:4],
        "decision_needed": {"stop_state": stop_state, "reason": stop_reason} if stop_state != "none" else None,
    }


def build_restart_snapshot() -> dict[str, Any]:
    ralph = _load_optional_json(RALPH_LATEST_PATH)
    dispatch = _load_optional_json(DISPATCH_STATE_PATH)
    capacity = _load_optional_json(CAPACITY_TELEMETRY_PATH)
    publication_queue = _load_optional_json(PUBLICATION_DEFERRED_QUEUE_PATH)
    continuity = _load_optional_json(RALPH_CONTINUITY_STATE_PATH)
    next_rotation_preflight = _load_optional_json(NEXT_ROTATION_PREFLIGHT_PATH)
    finish_scoreboard = _load_optional_json(FINISH_SCOREBOARD_PATH)
    runtime_packet_inbox = _load_optional_json(RUNTIME_PACKET_INBOX_PATH)
    steady_state_status = _load_optional_json(STEADY_STATE_STATUS_PATH)
    atlas = _load_optional_json(ATLAS_LATEST_PATH)
    queue = _pick_queue(ralph)
    queue_total, queue_dispatchable, queue_blocked = _pick_queue_summary(ralph, dispatch, queue)
    harvest = _pick_harvest_summary(dispatch, capacity)
    loop_state = dict(ralph.get("loop_state") or {})
    top_task = dict(ralph.get("top_task") or {})
    publication_next = dict(publication_queue.get("next_recommended_family") or {})
    next_unblocked_candidate = dict(ralph.get("next_unblocked_candidate") or continuity.get("next_unblocked_candidate") or {})
    suppressed_task_ids = continuity.get("recent_no_delta_task_ids") if isinstance(continuity.get("recent_no_delta_task_ids"), list) else []

    snapshot = {
        "repo_root": str(REPO_ROOT),
        "generated_at": _pick_string(
            ralph.get("generated_at"),
            dispatch.get("generated_at"),
            atlas.get("generated_at"),
        ),
        "loop_mode": _pick_string(ralph.get("loop_mode"), ralph.get("current_loop_family"), loop_state.get("current_loop_family")),
        "selected_workstream": _pick_string(ralph.get("selected_workstream"), loop_state.get("selected_workstream")),
        "selected_workstream_id": _pick_string(ralph.get("selected_workstream_id"), ralph.get("selected_workstream"), loop_state.get("selected_workstream_id"), loop_state.get("selected_workstream")),
        "selected_workstream_title": _pick_string(ralph.get("selected_workstream_title"), loop_state.get("selected_workstream_title"), ralph.get("selected_workstream"), loop_state.get("selected_workstream")),
        "next_action_family": _pick_string(ralph.get("next_action_family"), loop_state.get("next_action_family")),
        "execution_posture": _pick_string(ralph.get("execution_posture"), loop_state.get("execution_posture")),
        "evidence_freshness": _pick_string(ralph.get("evidence_freshness"), loop_state.get("evidence_freshness")),
        "provider_gate_state": _pick_string(ralph.get("provider_gate_state")),
        "work_economy_status": _pick_string(ralph.get("work_economy_status")),
        "active_claim_task_title": _pick_string(
            ralph.get("active_claim_task_title"),
            dispatch.get("current_task_title"),
            top_task.get("title"),
        ),
        "active_claim_task_id": _pick_string(
            ralph.get("active_claim_task_id"),
            dispatch.get("current_task_id"),
            top_task.get("id"),
            top_task.get("task_id"),
        ),
        "active_claim_lane_family": _pick_string(
            ralph.get("active_claim_lane_family"),
            dispatch.get("current_lane_family"),
            top_task.get("preferred_lane_family"),
        ),
        "repo_side_no_delta": bool(ralph.get("repo_side_no_delta")),
        "rotation_ready": bool(ralph.get("rotation_ready")),
        "reopen_reason_scope": _pick_string(ralph.get("reopen_reason_scope")),
        "no_delta_evidence_refs": [
            _pick_string(item)
            for item in ralph.get("no_delta_evidence_refs", [])
            if _pick_string(item)
        ],
        "continue_allowed": bool(ralph.get("continue_allowed", continuity.get("continue_allowed"))),
        "current_stop_state": _pick_string(
            ralph.get("stop_state"),
            loop_state.get("stop_state"),
            continuity.get("current_stop_state"),
        ) or "none",
        "current_stop_reason": _pick_string(
            ralph.get("stop_reason"),
            loop_state.get("stop_reason"),
            continuity.get("current_stop_reason"),
        ),
        "top_task_title": _pick_string(
            ralph.get("active_claim_task_title"),
            dispatch.get("current_task_title"),
            top_task.get("title"),
            loop_state.get("selected_workstream_title"),
        ),
        "top_task_id": _pick_string(
            ralph.get("active_claim_task_id"),
            dispatch.get("current_task_id"),
            top_task.get("id"),
            top_task.get("task_id"),
            loop_state.get("selected_workstream"),
        ),
        "queue_total": queue_total,
        "queue_dispatchable": queue_dispatchable,
        "queue_blocked": queue_blocked,
        "queue": queue,
        "dispatch_status": _pick_string(
            dispatch.get("dispatch_outcome"),
            dispatch.get("execution", {}).get("status") if isinstance(dispatch.get("execution"), dict) else None,
            dispatch.get("governed_dispatch_claim", {}).get("status")
            if isinstance(dispatch.get("governed_dispatch_claim"), dict)
            else None,
        ),
        "dispatch_phase_label": _pick_string(dispatch.get("dispatch_phase_label")),
        "dispatch_ready": bool(dispatch.get("governed_dispatch_ready")),
        "advisory_blockers": dispatch.get("advisory_blockers") if isinstance(dispatch.get("advisory_blockers"), list) else [],
        "next_checkpoint_slice_id": _pick_string(
            ralph.get("next_checkpoint_slice_id"),
            ralph.get("publication_debt", {}).get("next_checkpoint_slice_id") if isinstance(ralph.get("publication_debt"), dict) else None,
        ),
        "next_checkpoint_slice_title": _pick_string(
            ralph.get("next_checkpoint_slice_title"),
            ralph.get("publication_debt", {}).get("next_checkpoint_slice_title") if isinstance(ralph.get("publication_debt"), dict) else None,
        ),
        "publication_next_family_id": _pick_string(ralph.get("next_deferred_family_id"), publication_next.get("id")),
        "publication_next_family_title": _pick_string(ralph.get("next_deferred_family_title"), publication_next.get("title")),
        "publication_next_family_class": _pick_string(publication_next.get("execution_class")),
        "publication_next_family_matches": publication_next.get("match_count"),
        "next_unblocked_candidate": next_unblocked_candidate,
        "suppressed_task_ids": suppressed_task_ids,
        "suppressed_task_count": len(suppressed_task_ids),
        "next_rotation_preflight": next_rotation_preflight if isinstance(next_rotation_preflight, dict) else {},
        "finish_scoreboard": finish_scoreboard if isinstance(finish_scoreboard, dict) else {},
        "runtime_packet_inbox": runtime_packet_inbox if isinstance(runtime_packet_inbox, dict) else {},
        "steady_state_status": steady_state_status if isinstance(steady_state_status, dict) else {},
        "harvest_summary": harvest,
        "recent_commits": _run_git("log", "--oneline", "-5"),
        "status_lines": _run_git("status", "--short"),
        "diff_stat_lines": _run_git("diff", "--stat"),
        "canonical_docs": CANONICAL_DOCS,
        "control_surfaces": CONTROL_SURFACES,
        "artifacts": {
            "ralph_latest": str(RALPH_LATEST_PATH),
            "dispatch_state": str(DISPATCH_STATE_PATH),
            "capacity_telemetry": str(CAPACITY_TELEMETRY_PATH),
            "publication_deferred_queue": str(PUBLICATION_DEFERRED_QUEUE_PATH),
            "ralph_continuity_state": str(RALPH_CONTINUITY_STATE_PATH),
            "next_rotation_preflight": str(NEXT_ROTATION_PREFLIGHT_PATH),
            "finish_scoreboard": str(FINISH_SCOREBOARD_PATH),
            "runtime_packet_inbox": str(RUNTIME_PACKET_INBOX_PATH),
            "steady_state_status": str(STEADY_STATE_STATUS_PATH),
            "master_atlas_latest": str(ATLAS_LATEST_PATH),
        },
    }
    executive_brief = ralph.get("executive_brief")
    snapshot["executive_brief"] = executive_brief if isinstance(executive_brief, dict) else _build_fallback_executive_brief(snapshot)
    return snapshot


def run_refresh() -> None:
    completed = subprocess.run(
        [sys.executable, str(RALPH_LOOP_SCRIPT), "--skip-validation"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        if completed.stdout.strip():
            print(completed.stdout.rstrip())
        if completed.stderr.strip():
            print(completed.stderr.rstrip())
        raise SystemExit(completed.returncode)


def render_restart_brief(snapshot: dict[str, Any]) -> str:
    queue = snapshot.get("queue") or []
    harvest = snapshot.get("harvest_summary") or {}
    docs = snapshot.get("canonical_docs") or []
    surfaces = snapshot.get("control_surfaces") or []
    artifacts = snapshot.get("artifacts") or {}
    executive_brief = snapshot.get("executive_brief") or {}
    finish_scoreboard = snapshot.get("finish_scoreboard") or {}
    runtime_packet_inbox = snapshot.get("runtime_packet_inbox") or {}
    steady_state_status = snapshot.get("steady_state_status") or {}

    lines = [
        "# Athanor Session Restart Brief",
        "",
        f"- Repo root: `{snapshot.get('repo_root', str(REPO_ROOT))}`",
        f"- Generated at: `{snapshot.get('generated_at', 'unknown')}`",
        f"- Loop mode: `{snapshot.get('loop_mode', 'unknown')}`",
        f"- Selected workstream: `{snapshot.get('selected_workstream_id') or snapshot.get('selected_workstream', 'unknown')}`",
        f"- Next action family: `{snapshot.get('next_action_family', 'unknown')}`",
        f"- Execution posture: `{snapshot.get('execution_posture', 'unknown')}`",
        f"- Evidence freshness: `{snapshot.get('evidence_freshness', 'unknown')}`",
        f"- Provider gate: `{snapshot.get('provider_gate_state', 'unknown')}`",
        f"- Work economy: `{snapshot.get('work_economy_status', 'unknown')}`",
        f"- Top task: `{snapshot.get('top_task_title', 'unknown')}`",
        f"- Active claim: `{snapshot.get('active_claim_task_title', 'unknown')}`",
        f"- Continue allowed: `{snapshot.get('continue_allowed', False)}`",
        f"- Stop state: `{snapshot.get('current_stop_state', 'none')}`",
        f"- Repo-side no-delta: `{snapshot.get('repo_side_no_delta', False)}` | rotation ready: `{snapshot.get('rotation_ready', False)}`",
        f"- Reopen scope: `{snapshot.get('reopen_reason_scope', 'unknown')}`",
        f"- Queue: `{snapshot.get('queue_total', len(queue))}` total / `{snapshot.get('queue_dispatchable', 'unknown')}` dispatchable / `{snapshot.get('queue_blocked', 'unknown')}` blocked",
        f"- Continuity suppressions: `{snapshot.get('suppressed_task_count', 0)}`",
        f"- Dispatch status: `{snapshot.get('dispatch_status', 'unknown')}`",
        f"- Dispatch phase: `{snapshot.get('dispatch_phase_label', 'unknown')}`",
    ]
    if snapshot.get('next_checkpoint_slice_id'):
        lines.append(
            f"- Next checkpoint slice: `{snapshot.get('next_checkpoint_slice_title') or snapshot.get('next_checkpoint_slice_id')}`"
        )

    if isinstance(executive_brief, dict) and executive_brief:
        program_state = dict(executive_brief.get("program_state") or {})
        landed_or_delta = dict(executive_brief.get("landed_or_delta") or {})
        proof_block = dict(executive_brief.get("proof") or {})
        risks = executive_brief.get("risks") if isinstance(executive_brief.get("risks"), list) else []
        delegation = dict(executive_brief.get("delegation") or {})
        next_moves = executive_brief.get("next_moves") if isinstance(executive_brief.get("next_moves"), list) else []
        decision_needed = executive_brief.get("decision_needed")

        lines.extend(["", "## Executive Brief", "", "### Program State", ""])
        lines.append(f"- Selected workstream: `{_pick_string(program_state.get('selected_workstream_title'), program_state.get('selected_workstream')) or 'unknown'}`")
        lines.append(f"- Active claim: `{_pick_string(program_state.get('active_claim_task_title'), program_state.get('active_claim_task_id')) or 'unknown'}`")
        lines.append(f"- Loop mode: `{program_state.get('loop_mode', 'unknown')}`")
        lines.append(f"- Execution posture: `{program_state.get('execution_posture', 'unknown')}`")
        lines.append(f"- Continue allowed: `{program_state.get('continue_allowed', False)}` | stop state: `{program_state.get('stop_state', 'none')}`")
        if program_state.get("repo_side_no_delta") is not None:
            lines.append(
                f"- Repo-side no-delta: `{program_state.get('repo_side_no_delta', False)}` | rotation ready: `{program_state.get('rotation_ready', False)}`"
            )
        if program_state.get("reopen_reason_scope"):
            lines.append(f"- Reopen scope: `{program_state.get('reopen_reason_scope')}`")
        if program_state.get("next_checkpoint_slice_id"):
            lines.append(
                f"- Next checkpoint slice: `{program_state.get('next_checkpoint_slice_title') or program_state.get('next_checkpoint_slice_id')}`"
            )
        if program_state.get("next_action_family"):
            lines.append(f"- Next action family: `{program_state.get('next_action_family')}`")

        lines.extend(["", "### Landed / Delta", ""])
        lines.append(f"- {_pick_string(landed_or_delta.get('summary')) or 'No material delta summary was available.'}")
        if landed_or_delta.get("dispatch_status"):
            lines.append(f"- Dispatch status: `{landed_or_delta.get('dispatch_status')}`")
        if landed_or_delta.get("rotation_reason"):
            lines.append(f"- Rotation reason: `{landed_or_delta.get('rotation_reason')}`")

        lines.extend(["", "### Proof", ""])
        lines.append(f"- Validation: `{proof_block.get('validation_summary', 'unknown')}`")
        lines.append(f"- Evidence freshness: `{proof_block.get('evidence_freshness', 'unknown')}`")
        if proof_block.get("dispatch_status"):
            lines.append(f"- Governed dispatch: `{proof_block.get('dispatch_status')}`")
        no_delta_refs = proof_block.get("no_delta_evidence_refs") if isinstance(proof_block.get("no_delta_evidence_refs"), list) else []
        if no_delta_refs:
            lines.append(f"- No-delta evidence refs: `{', '.join(no_delta_refs[:4])}`")

        lines.extend(["", "### Risks", ""])
        if risks:
            for risk in risks[:5]:
                if isinstance(risk, dict):
                    lines.append(
                        f"- `{_pick_string(risk.get('id')) or 'risk'}` ({_pick_string(risk.get('severity')) or 'unknown'}): {_pick_string(risk.get('summary')) or 'unknown'}"
                    )
        else:
            lines.append("- No active top-risk entries were materialized for this pass.")

        lines.extend(["", "### Delegation", ""])
        lines.append(f"- Main-agent focus: `{_pick_string(delegation.get('main_agent_focus')) or 'unknown'}`")
        lines.append(f"- Posture: {_pick_string(delegation.get('delegation_posture')) or 'unknown'}")
        delegate_now = delegation.get("delegate_now") if isinstance(delegation.get("delegate_now"), list) else []
        if delegate_now:
            for item in delegate_now[:3]:
                lines.append(f"- Delegate now: {item}")
        else:
            lines.append("- Delegate now: none materialized.")

        lines.extend(["", "### Next Moves", ""])
        if next_moves:
            for item in next_moves[:4]:
                lines.append(f"- {item}")
        else:
            lines.append("- No next moves were materialized.")

        lines.extend(["", "### Decision Needed", ""])
        if isinstance(decision_needed, dict) and decision_needed:
            lines.append(
                f"- `{_pick_string(decision_needed.get('stop_state')) or 'decision'}`: {_pick_string(decision_needed.get('reason')) or 'Operator attention required.'}"
            )
        else:
            lines.append("- None.")

    lines.extend(
        [
            "",
            "## Fast Restart",
            "",
            "1. Run `python scripts/session_restart_brief.py --refresh`.",
            "2. Trust the canonical docs below before any older narrative, archive, or chat memory.",
            "3. If you are changing source truth, run `python scripts/validate_platform_contract.py` before and after the slice.",
            "4. If you are resuming autonomous work, trust Ralph and governed dispatch before choosing the next lane.",
            "",
            "## Canonical Docs",
            "",
        ]
    )
    lines.extend(f"- `{doc}`" for doc in docs)
    lines.extend(
        [
            "",
            "## Live Artifacts",
            "",
            f"- Ralph loop: `{artifacts.get('ralph_latest', str(RALPH_LATEST_PATH))}`",
            f"- Governed dispatch: `{artifacts.get('dispatch_state', str(DISPATCH_STATE_PATH))}`",
            f"- Capacity telemetry: `{artifacts.get('capacity_telemetry', str(CAPACITY_TELEMETRY_PATH))}`",
            f"- Ralph continuity state: `{artifacts.get('ralph_continuity_state', str(RALPH_CONTINUITY_STATE_PATH))}`",
            f"- Next rotation preflight: `{artifacts.get('next_rotation_preflight', str(NEXT_ROTATION_PREFLIGHT_PATH))}`",
            f"- Finish scoreboard: `{artifacts.get('finish_scoreboard', str(FINISH_SCOREBOARD_PATH))}`",
            f"- Runtime packet inbox: `{artifacts.get('runtime_packet_inbox', str(RUNTIME_PACKET_INBOX_PATH))}`",
            f"- Steady-state status: `{artifacts.get('steady_state_status', str(STEADY_STATE_STATUS_PATH))}`",
            f"- Master atlas: `{artifacts.get('master_atlas_latest', str(ATLAS_LATEST_PATH))}`",
            "",
            "## Control Surfaces",
            "",
        ]
    )
    lines.extend(f"- `{surface}`" for surface in surfaces)
    lines.extend(["", "## Priority Queue", ""])
    if queue:
        for item in queue[:3]:
            title = _pick_string(item.get("title"), item.get("task_title"), item.get("id")) or "unknown"
            value_class = _pick_string(item.get("value_class")) or "unknown"
            mutation_class = _pick_string(item.get("approved_mutation_class")) or "unknown"
            lane = _pick_string(item.get("preferred_lane_family")) or "unknown"
            proof = _pick_string(item.get("proof_command_or_eval_surface")) or "none"
            suppressed = item.get("suppressed_by_continuity")
            lines.append(
                f"- `{title}` | value=`{value_class}` | mutation=`{mutation_class}` | lane=`{lane}` | proof=`{proof}` | suppressed=`{suppressed}`"
            )
    else:
        lines.append("- No ranked autonomous queue was available.")

    publication_next_family_id = snapshot.get("publication_next_family_id")
    next_candidate = snapshot.get("next_unblocked_candidate") or {}
    if next_candidate or snapshot.get("current_stop_reason") or snapshot.get("suppressed_task_count"):
        lines.extend(["", "## Continuity", ""])
        if next_candidate:
            lines.append(
                f"- On deck: `{_pick_string(next_candidate.get('title'), next_candidate.get('task_id')) or 'unknown'}` | task=`{_pick_string(next_candidate.get('task_id')) or 'unknown'}` | lane=`{_pick_string(next_candidate.get('preferred_lane_family')) or 'unknown'}` | source=`{_pick_string(next_candidate.get('source_type')) or 'unknown'}`"
            )
        if snapshot.get("current_stop_reason"):
            lines.append(f"- Stop reason: `{snapshot.get('current_stop_reason', 'unknown')}`")
        suppressed_task_ids = snapshot.get("suppressed_task_ids") or []
        if suppressed_task_ids:
            lines.append(f"- Recently suppressed: `{', '.join(str(task_id) for task_id in suppressed_task_ids[:6])}`")

    next_rotation_preflight = snapshot.get("next_rotation_preflight") or {}
    preflight_detail = next_rotation_preflight.get("preflight") if isinstance(next_rotation_preflight.get("preflight"), dict) else {}
    if next_rotation_preflight.get("preflight_available") and preflight_detail:
        lines.extend(["", "## Next Rotation Preflight", ""])
        lines.append(
            f"- On-deck task: `{_pick_string(next_rotation_preflight.get('next_candidate_title'), next_rotation_preflight.get('next_candidate_task_id')) or 'unknown'}` | task=`{_pick_string(next_rotation_preflight.get('next_candidate_task_id')) or 'unknown'}`"
        )
        routing_chain = preflight_detail.get("routing_chain")
        if isinstance(routing_chain, list) and routing_chain:
            lines.append(f"- Routing chain: `{', '.join(str(item) for item in routing_chain)}`")
        approved_families = preflight_detail.get("approved_task_families")
        if isinstance(approved_families, list) and approved_families:
            lines.append(f"- Approved task families: `{', '.join(str(item) for item in approved_families)}`")
        lines.append(
            f"- Lane: `{_pick_string(preflight_detail.get('preferred_lane_family')) or 'unknown'}` | mutation=`{_pick_string(preflight_detail.get('approved_mutation_class')) or 'unknown'}` | dispatchable=`{preflight_detail.get('dispatchable', 'unknown')}`"
        )
        lines.append(
            f"- Concurrency: `{preflight_detail.get('max_concurrency', 'unknown')}` | reserve=`{_pick_string(preflight_detail.get('reserve_rule')) or 'unknown'}`"
        )
        lines.append(
            f"- Provider: `{_pick_string(preflight_detail.get('selected_provider_label'), preflight_detail.get('selected_provider_id')) or 'unknown'}` | proof=`{_pick_string(preflight_detail.get('proof_command_or_eval_surface')) or 'unknown'}`"
        )
        lines.append(
            f"- Queue posture: dispatchable=`{preflight_detail.get('queue_dispatchable', 'unknown')}` | blocked=`{preflight_detail.get('queue_blocked', 'unknown')}` | suppressed=`{preflight_detail.get('suppressed_task_count', 'unknown')}`"
        )

    if finish_scoreboard:
        lines.extend(["", "## Closure Scoreboard", ""])
        lines.append(f"- Closure state: `{finish_scoreboard.get('closure_state', 'unknown')}`")
        lines.append(
            f"- Repo-safe debt: cash_now=`{finish_scoreboard.get('cash_now_remaining_count', 'unknown')}` | bounded_follow_on=`{finish_scoreboard.get('bounded_follow_on_remaining_count', 'unknown')}` | program_slice=`{finish_scoreboard.get('program_slice_remaining_count', 'unknown')}`"
        )
        lines.append(
            f"- Typed brakes only: `{finish_scoreboard.get('only_typed_brakes_remain', False)}` | approval-gated runtime packets=`{finish_scoreboard.get('approval_gated_runtime_packet_count', 'unknown')}`"
        )
        if finish_scoreboard.get("next_deferred_family_id"):
            lines.append(
                f"- Next deferred family: `{finish_scoreboard.get('next_deferred_family_title') or finish_scoreboard.get('next_deferred_family_id')}`"
            )

    packets = runtime_packet_inbox.get("packets") if isinstance(runtime_packet_inbox.get("packets"), list) else []
    if runtime_packet_inbox:
        lines.extend(["", "## Runtime Packet Inbox", ""])
        lines.append(f"- Approval-gated packets: `{runtime_packet_inbox.get('packet_count', len(packets))}`")
        if packets:
            for packet in packets[:3]:
                if not isinstance(packet, dict):
                    continue
                lines.append(
                    f"- `{_pick_string(packet.get('label'), packet.get('id')) or 'unknown'}` | host=`{_pick_string(packet.get('host')) or 'unknown'}` | approval=`{_pick_string(packet.get('approval_type')) or 'unknown'}` | state=`{_pick_string(packet.get('readiness_state')) or 'unknown'}`"
                )
                lines.append(
                    f"- Goal: {_pick_string(packet.get('goal')) or 'unknown'} | next action: {_pick_string(packet.get('next_operator_action')) or 'Review packet and approve bounded mutation.'}"
                )
        else:
            lines.append("- No approval-gated runtime packets are currently queued.")

    if steady_state_status:
        lines.extend(["", "## Steady-State Status", ""])
        lines.append(f"- Operator mode: `{steady_state_status.get('operator_mode', 'unknown')}`")
        lines.append(f"- Reopen required: `{steady_state_status.get('reopen_required', False)}`")
        lines.append(f"- Next operator action: {steady_state_status.get('next_operator_action', 'unknown')}")
        reopen_reasons = steady_state_status.get("reopen_reasons") if isinstance(steady_state_status.get("reopen_reasons"), list) else []
        if reopen_reasons:
            lines.append("- Active reopen reasons: " + "; ".join(str(item) for item in reopen_reasons[:3]))

    if publication_next_family_id:
        lines.extend(["", "## Publication Follow-On", ""])
        lines.append(
            f"- Next deferred family: `{publication_next_family_id}` ({snapshot.get('publication_next_family_class', 'unknown')}, `{snapshot.get('publication_next_family_matches', 'unknown')}` dirty matches)"
        )
        lines.append(f"- Title: {snapshot.get('publication_next_family_title', 'unknown')}")

    lines.extend(["", "## Harvest Posture", ""])
    lines.append(
        f"- Admission state: `{_pick_string(harvest.get('admission_state'), harvest.get('slot_pressure_state')) or 'unknown'}`"
    )
    lines.append(
        f"- Ready for harvest now: `{harvest.get('ready_for_harvest_now', harvest.get('idle_harvest_slots_open', 'unknown'))}`"
    )
    lines.append(f"- Harvestable scheduler slots: `{harvest.get('harvestable_scheduler_slot_count', 'unknown')}`")
    zone_ids = harvest.get("harvestable_zone_ids")
    if isinstance(zone_ids, list) and zone_ids:
        lines.append(f"- Harvestable zones: `{', '.join(str(zone_id) for zone_id in zone_ids)}`")
    target_ids = harvest.get("open_harvest_slot_target_ids")
    if isinstance(target_ids, list) and target_ids:
        lines.append(f"- Open slot targets: `{', '.join(str(target_id) for target_id in target_ids)}`")

    lines.extend(["", "## Advisory Blockers", ""])
    blockers = snapshot.get("advisory_blockers") or []
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None recorded in governed dispatch state.")

    lines.extend(["", "## Git State", ""])
    status_lines = snapshot.get("status_lines") or []
    diff_stat_lines = snapshot.get("diff_stat_lines") or []
    recent_commits = snapshot.get("recent_commits") or []
    lines.append(f"- Dirty entries: `{len(status_lines)}`")
    if recent_commits:
        lines.append("- Recent commits:")
        lines.extend(f"  - `{line}`" for line in recent_commits)
    if status_lines:
        lines.append("- Status sample:")
        lines.extend(f"  - `{line}`" for line in status_lines[:12])
    if diff_stat_lines:
        lines.append("- Diff stat sample:")
        lines.extend(f"  - `{line}`" for line in diff_stat_lines[:12])

    lines.extend(
        [
            "",
            "## Restart Rules",
            "",
            "- Do not start from `MEMORY.md`, archived docs, or chat recap if live artifacts disagree.",
            "- Do not treat `services/` as a growth path; use `projects/`, `config/automation-backbone/`, `reports/`, and `docs/operations/` by contract.",
            "- If the queue, dispatch artifact, and atlas disagree, that disagreement is the first bug to close.",
            "",
            "## Deep Restart",
            "",
            "1. Read `STATUS.md` for current posture.",
            "2. Read `docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md` for current order.",
            "3. Read `docs/operations/ATHANOR-OPERATING-SYSTEM.md` for authority and execution rules.",
            "4. Read `docs/operations/REPO-STRUCTURE-RULES.md` before moving or creating files.",
            "5. Run `python scripts/validate_platform_contract.py` if you are about to land a real tranche.",
            "6. Open the command center and the routing view if the session is runtime- or autonomy-heavy.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a concise Athanor session-restart brief from live control-plane artifacts."
    )
    parser.add_argument("--refresh", action="store_true", help="Refresh Ralph-loop control-plane truth before rendering the brief.")
    parser.add_argument("--json", action="store_true", help="Emit the underlying snapshot as JSON.")
    parser.add_argument("--write", type=Path, help="Optional output path for the rendered brief.")
    args = parser.parse_args()

    if args.refresh:
        run_refresh()

    snapshot = build_restart_snapshot()
    rendered = json.dumps(snapshot, indent=2, sort_keys=True) if args.json else render_restart_brief(snapshot)

    if args.write:
        output_path = args.write if args.write.is_absolute() else REPO_ROOT / args.write
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote {output_path}")
        return 0

    print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
