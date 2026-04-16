#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from closure_finish_common import (
    FINISH_SCOREBOARD_PATH,
    build_finish_scoreboard,
    build_runtime_packet_inbox,
    load_publication_deferred_queue,
    load_runtime_packets,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
RALPH_LATEST_PATH = REPO_ROOT / "reports" / "ralph-loop" / "latest.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_payload() -> dict:
    ralph_report = _load_json(RALPH_LATEST_PATH)
    publication_queue = load_publication_deferred_queue()
    runtime_inbox = build_runtime_packet_inbox(load_runtime_packets())
    return build_finish_scoreboard(ralph_report, publication_queue, runtime_inbox)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the machine-readable Athanor finish scoreboard.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    args = parser.parse_args()

    payload = build_payload()
    FINISH_SCOREBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINISH_SCOREBOARD_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(FINISH_SCOREBOARD_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
