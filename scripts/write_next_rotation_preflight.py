#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from preflight_burn_class import (
    BURN_REGISTRY_PATH,
    CAPACITY_PATH,
    QUOTA_PATH,
    build_burn_class_preflight,
    load_restart_snapshot,
    _load_json,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "next-rotation-preflight.json"


def build_next_rotation_preflight() -> dict:
    snapshot = load_restart_snapshot()
    next_candidate = snapshot.get("next_unblocked_candidate") if isinstance(snapshot.get("next_unblocked_candidate"), dict) else {}
    task_id = str(next_candidate.get("task_id") or next_candidate.get("id") or "").strip()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "next_candidate_task_id": task_id or None,
        "next_candidate_title": str(next_candidate.get("title") or "").strip() or None,
        "next_candidate_source_type": str(next_candidate.get("source_type") or "").strip() or None,
        "preflight_available": False,
        "preflight": None,
    }
    if task_id.startswith("burn_class:"):
        burn_class_id = task_id.split(":", 1)[1]
        payload["preflight_available"] = True
        payload["preflight"] = build_burn_class_preflight(
            burn_class_id,
            snapshot,
            _load_json(BURN_REGISTRY_PATH),
            _load_json(CAPACITY_PATH),
            _load_json(QUOTA_PATH),
        )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the next rotation preflight artifact for the current on-deck candidate.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    args = parser.parse_args()

    payload = build_next_rotation_preflight()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(OUTPUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
