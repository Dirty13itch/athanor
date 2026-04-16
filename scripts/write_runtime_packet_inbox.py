#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from closure_finish_common import (
    RUNTIME_PACKET_INBOX_PATH,
    build_runtime_packet_inbox,
    load_runtime_packets,
)


def build_payload() -> dict:
    return build_runtime_packet_inbox(load_runtime_packets())


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the approval-gated runtime packet inbox artifact.")
    parser.add_argument("--json", action="store_true", help="Print JSON output after writing the artifact.")
    args = parser.parse_args()

    payload = build_payload()
    RUNTIME_PACKET_INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_PACKET_INBOX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(str(RUNTIME_PACKET_INBOX_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
