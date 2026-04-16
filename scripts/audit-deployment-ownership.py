#!/usr/bin/env python3
"""Audit deployment ownership and live reachability for core Athanor services."""

from __future__ import annotations

import argparse
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from completion_audit_common import COMPLETION_AUDIT_DIR, DEPLOYMENT_SERVICE_MATRIX, write_json


OUTPUT_PATH = COMPLETION_AUDIT_DIR / "deployment-ownership-matrix.json"


def probe_endpoint(endpoint: str) -> str:
    if endpoint.startswith("redis://"):
        parsed = urllib.parse.urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        try:
            with socket.create_connection((host, port), timeout=5):
                return "reachable"
        except OSError:
            return "unreachable"

    request = urllib.request.Request(endpoint, headers={"Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return "reachable" if response.status < 500 else "unreachable"
    except urllib.error.HTTPError as exc:
        return "reachable" if exc.code < 500 else "unreachable"
    except Exception:
        return "unreachable"


def completion_status(live_status: str, drift_status: str) -> str:
    if live_status != "reachable":
        return "broken"
    if drift_status in {"mixed", "diverged"}:
        return "live_partial"
    return "live_complete"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    records = []
    for service in DEPLOYMENT_SERVICE_MATRIX:
        live_status = probe_endpoint(service["liveEndpoint"])
        records.append(
            {
                **service,
                "liveStatus": live_status,
                "completionStatus": completion_status(live_status, service["driftStatus"]),
            }
        )

    output_path = Path(args.output)
    write_json(output_path, records)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "serviceCount": len(records),
                "reachableCount": sum(1 for record in records if record["liveStatus"] == "reachable"),
                "partialOrBrokenCount": sum(
                    1
                    for record in records
                    if record["completionStatus"] in {"live_partial", "broken"}
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
