#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_inventory import resolve_external_path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "controller-of-controllers.json"
BLOCKER_MAP_PATH = REPO_ROOT / "reports" / "truth-inventory" / "blocker-map.json"
CONTINUITY_CONTROLLER_STATE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "continuity-controller-state.json"
STABLE_OPERATING_DAY_PATH = REPO_ROOT / "reports" / "truth-inventory" / "stable-operating-day.json"
RESULT_EVIDENCE_LEDGER_PATH = REPO_ROOT / "reports" / "truth-inventory" / "result-evidence-ledger.json"
SAFE_SURFACE_STATE_PATH = resolve_external_path("C:/Users/Shaun/.codex/control/safe-surface-state.json")
SAFE_SURFACE_QUEUE_PATH = resolve_external_path("C:/Users/Shaun/.codex/control/safe-surface-queue.json")
DEVSTACK_FORGE_BOARD_PATH = resolve_external_path("C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json")


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_payload() -> dict[str, Any]:
    blocker_map = _load_optional_json(BLOCKER_MAP_PATH)
    continuity = _load_optional_json(CONTINUITY_CONTROLLER_STATE_PATH)
    stable_day = _load_optional_json(STABLE_OPERATING_DAY_PATH)
    result_evidence = _load_optional_json(RESULT_EVIDENCE_LEDGER_PATH)
    safe_state = _load_optional_json(SAFE_SURFACE_STATE_PATH)
    safe_queue = _load_optional_json(SAFE_SURFACE_QUEUE_PATH)
    forge_board = _load_optional_json(DEVSTACK_FORGE_BOARD_PATH)

    safe_items = [dict(item) for item in safe_queue.get("items", []) if isinstance(item, dict)]
    safe_open_count = sum(1 for item in safe_items if str(item.get("status") or "") not in {"done", "closed"})
    summary = dict(forge_board.get("summary") or {})
    primary_lane = (
        "athanor_core_closure"
        if int((blocker_map.get("remaining") or {}).get("family_count") or 0) > 0
        else "athanor_core_throughput"
        if bool((blocker_map.get("proof_gate") or {}).get("open"))
        else "proof_gate_holding_pattern"
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_lane": primary_lane,
        "athanor": {
            "remaining_family_count": int((blocker_map.get("remaining") or {}).get("family_count") or 0),
            "next_tranche_id": ((blocker_map.get("next_tranche") or {}).get("id")),
            "proof_gate_open": bool((blocker_map.get("proof_gate") or {}).get("open")),
            "continuity_status": continuity.get("controller_status"),
            "stable_day_met": bool(stable_day.get("met")),
            "stable_day_covered_window_hours": float(stable_day.get("covered_window_hours") or 0.0),
            "result_evidence_progress": int(result_evidence.get("threshold_progress") or 0),
            "result_evidence_required": int(result_evidence.get("threshold_required") or 5),
        },
        "safe_surface": {
            "last_outcome": safe_state.get("last_outcome"),
            "current_task_id": safe_state.get("current_task_id"),
            "last_blocker": safe_state.get("last_blocker"),
            "open_item_count": safe_open_count,
        },
        "devstack": {
            "top_priority_lane": summary.get("top_priority_lane"),
            "ready_for_review_count": int(summary.get("ready_for_review_count") or 0),
            "drafting_packet_count": int(summary.get("drafting_packet_count") or 0),
            "hygiene_count": int(summary.get("hygiene_count") or 0),
            "dirty_file_count": int(summary.get("dirty_file_count") or 0),
        },
        "source_artifacts": {
            "blocker_map": str(BLOCKER_MAP_PATH),
            "continuity_controller_state": str(CONTINUITY_CONTROLLER_STATE_PATH),
            "stable_operating_day": str(STABLE_OPERATING_DAY_PATH),
            "result_evidence_ledger": str(RESULT_EVIDENCE_LEDGER_PATH),
            "safe_surface_state": str(SAFE_SURFACE_STATE_PATH),
            "safe_surface_queue": str(SAFE_SURFACE_QUEUE_PATH),
            "devstack_forge_board": str(DEVSTACK_FORGE_BOARD_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the cross-lane controller-of-controllers summary artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero when controller-of-controllers.json is stale.")
    args = parser.parse_args()

    payload = build_payload()
    rendered = _json_render(payload)
    current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if args.check:
        if current != rendered:
            print(f"{OUTPUT_PATH} is stale")
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if current != rendered:
        OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
