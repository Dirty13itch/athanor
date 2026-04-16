#!/usr/bin/env python3
"""Probe the live Athanor agent-server runtime without mutating state."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url


DEFAULT_BASE_URL = get_url("agent_server")

ENDPOINTS = [
    ("/health", "health"),
    ("/v1/models", "catalog"),
    ("/v1/agents", "catalog"),
    ("/v1/tasks", "task-engine"),
    ("/v1/tasks/stats", "task-engine"),
    ("/v1/workspace", "workspace"),
    ("/v1/workspace/stats", "workspace"),
    ("/v1/goals", "goals-workplan"),
    ("/v1/workplan", "goals-workplan"),
    ("/v1/notifications", "notifications"),
    ("/v1/preferences", "memory"),
    ("/v1/learning/metrics", "patterns-learning"),
    ("/v1/subscriptions/providers", "subscriptions"),
    ("/v1/subscriptions/policy", "subscriptions"),
    ("/v1/subscriptions/quotas", "subscriptions"),
    ("/v1/skills", "skills-research-consolidation"),
    ("/v1/research/jobs", "skills-research-consolidation"),
    ("/v1/consolidate/stats", "skills-research-consolidation"),
]


def fetch_json(base_url: str, path: str) -> dict:
    request = urllib.request.Request(f"{base_url}{path}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return {
            "status": response.status,
            "headers": dict(response.headers),
            "payload": json.loads(response.read().decode("utf-8")),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output")
    args = parser.parse_args()

    results = []
    failures = []
    for path, subsystem in ENDPOINTS:
        try:
            response = fetch_json(args.base_url, path)
            results.append(
                {
                    "path": path,
                    "subsystem": subsystem,
                    "status": response["status"],
                    "ok": response["status"] == 200,
                    "keys": sorted(response["payload"].keys())[:12] if isinstance(response["payload"], dict) else [],
                }
            )
        except urllib.error.HTTPError as exc:
            failures.append(f"{path}: HTTP {exc.code}")
            results.append({"path": path, "subsystem": subsystem, "status": exc.code, "ok": False, "keys": []})
        except Exception as exc:  # pragma: no cover - live probe only
            failures.append(f"{path}: {exc}")
            results.append({"path": path, "subsystem": subsystem, "status": 0, "ok": False, "keys": []})

    payload = {
        "baseUrl": args.base_url,
        "endpointCount": len(results),
        "reachableCount": sum(1 for result in results if result["ok"]),
        "results": results,
        "failures": failures,
    }
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
