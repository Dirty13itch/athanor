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
        )
    except OSError:
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


def _pick_queue_summary(ralph: dict[str, Any], dispatch: dict[str, Any], queue: list[dict[str, Any]]) -> tuple[Any, Any]:
    summary = ralph.get("autonomous_queue_summary")
    if isinstance(summary, dict):
        return (
            summary.get("total_count", len(queue)),
            summary.get(
                "dispatchable_count",
                dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False)),
            ),
        )
    summary = dispatch.get("autonomous_queue_summary")
    if isinstance(summary, dict):
        return (
            summary.get("total_count", len(queue)),
            summary.get(
                "dispatchable_count",
                dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False)),
            ),
        )
    return (
        dispatch.get("eligible_queue_count", len(queue)),
        dispatch.get("dispatchable_queue_count", sum(1 for item in queue if item.get("dispatchable") is not False)),
    )


def _pick_harvest_summary(dispatch: dict[str, Any], capacity: dict[str, Any]) -> dict[str, Any]:
    for key in ("capacity_harvest_summary", "capacity_signal"):
        value = dispatch.get(key)
        if isinstance(value, dict):
            return value
    summary = capacity.get("capacity_summary")
    if isinstance(summary, dict):
        return summary
    return {}


def build_restart_snapshot() -> dict[str, Any]:
    ralph = _load_optional_json(RALPH_LATEST_PATH)
    dispatch = _load_optional_json(DISPATCH_STATE_PATH)
    capacity = _load_optional_json(CAPACITY_TELEMETRY_PATH)
    atlas = _load_optional_json(ATLAS_LATEST_PATH)
    queue = _pick_queue(ralph)
    queue_total, queue_dispatchable = _pick_queue_summary(ralph, dispatch, queue)
    harvest = _pick_harvest_summary(dispatch, capacity)

    return {
        "repo_root": str(REPO_ROOT),
        "generated_at": _pick_string(
            ralph.get("generated_at"),
            dispatch.get("generated_at"),
            atlas.get("generated_at"),
        ),
        "loop_mode": _pick_string(ralph.get("loop_mode"), ralph.get("loop_state")),
        "provider_gate_state": _pick_string(ralph.get("provider_gate_state")),
        "work_economy_status": _pick_string(ralph.get("work_economy_status")),
        "top_task_title": _pick_string(
            ralph.get("top_task", {}).get("title") if isinstance(ralph.get("top_task"), dict) else None,
            dispatch.get("current_task_title"),
        ),
        "top_task_id": _pick_string(
            ralph.get("top_task", {}).get("task_id") if isinstance(ralph.get("top_task"), dict) else None,
            dispatch.get("current_task_id"),
        ),
        "queue_total": queue_total,
        "queue_dispatchable": queue_dispatchable,
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
            "master_atlas_latest": str(ATLAS_LATEST_PATH),
        },
    }


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
    lines = [
        "# Athanor Session Restart Brief",
        "",
        f"- Repo root: `{snapshot.get('repo_root', str(REPO_ROOT))}`",
        f"- Generated at: `{snapshot.get('generated_at', 'unknown')}`",
        f"- Loop mode: `{snapshot.get('loop_mode', 'unknown')}`",
        f"- Provider gate: `{snapshot.get('provider_gate_state', 'unknown')}`",
        f"- Work economy: `{snapshot.get('work_economy_status', 'unknown')}`",
        f"- Top task: `{snapshot.get('top_task_title', 'unknown')}`",
        f"- Queue: `{snapshot.get('queue_total', len(queue))}` total / `{snapshot.get('queue_dispatchable', 'unknown')}` dispatchable",
        f"- Dispatch status: `{snapshot.get('dispatch_status', 'unknown')}`",
        f"- Dispatch phase: `{snapshot.get('dispatch_phase_label', 'unknown')}`",
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
    lines.extend(f"- `{doc}`" for doc in docs)
    lines.extend(
        [
            "",
            "## Live Artifacts",
            "",
            f"- Ralph loop: `{artifacts.get('ralph_latest', str(RALPH_LATEST_PATH))}`",
            f"- Governed dispatch: `{artifacts.get('dispatch_state', str(DISPATCH_STATE_PATH))}`",
            f"- Capacity telemetry: `{artifacts.get('capacity_telemetry', str(CAPACITY_TELEMETRY_PATH))}`",
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
            lines.append(
                f"- `{title}` | value=`{value_class}` | mutation=`{mutation_class}` | lane=`{lane}` | proof=`{proof}`"
            )
    else:
        lines.append("- No ranked autonomous queue was available.")
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
