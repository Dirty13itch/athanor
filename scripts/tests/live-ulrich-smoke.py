#!/usr/bin/env python3
"""Smoke-test the live Ulrich Energy tenant with read-only validation by default."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from typing import Any
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BASE_URL = (
    os.environ.get("ATHANOR_ULRICH_LINK_URL")
    or "http://interface.athanor.local:3003/"
).rstrip("/")
ROUTES = ["/", "/analytics", "/clients", "/inspections", "/inspections/new", "/projects", "/reports"]


def fetch(base_url: str, path: str, method: str = "GET", payload: Any = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.status, dict(response.headers), response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--allow-mutations", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    summary: dict[str, Any] = {}

    for path in ROUTES:
        try:
            status, _, body = fetch(args.base_url, path)
            if status != 200 or "<html" not in body.decode("utf-8", errors="replace").lower():
                failures.append(f"route {path} unexpected status/content: {status}")
            else:
                summary[path] = "ok"
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"route {path} failed: {exc}")

    try:
        _, _, body = fetch(args.base_url, "/api/analytics/dashboard")
        analytics = json.loads(body.decode("utf-8"))
        if "data" not in analytics:
            failures.append("analytics endpoint returned unexpected shape")
        else:
            summary["analytics"] = sorted(analytics["data"].keys())[:5]
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"analytics failed: {exc}")

    inspection_id = None
    report_id = None
    for path, label in [
        ("/api/clients", "clients"),
        ("/api/inspections", "inspections"),
        ("/api/projects", "projects"),
        ("/api/reports", "reports"),
    ]:
        try:
            _, _, body = fetch(args.base_url, path)
            parsed = json.loads(body.decode("utf-8"))
            if path == "/api/clients":
                items = parsed.get("data")
            elif path == "/api/inspections":
                items = parsed.get("inspections")
                inspection_id = items[0]["id"] if items else None
            elif path == "/api/projects":
                items = parsed.get("projects")
            else:
                items = parsed.get("reports")
                report_id = items[0]["id"] if items else None
            if not isinstance(items, list):
                failures.append(f"{label} endpoint returned unexpected shape")
            else:
                summary[label] = len(items)
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"{label} failed: {exc}")

    if inspection_id:
        try:
            status, _, _ = fetch(args.base_url, f"/api/inspections/{inspection_id}")
            if status != 200:
                failures.append(f"inspection detail {inspection_id} returned {status}")
            else:
                summary["inspectionDetail"] = inspection_id
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"inspection detail failed: {exc}")

    if report_id:
        try:
            status, _, _ = fetch(args.base_url, f"/api/reports/{report_id}")
            if status != 200:
                failures.append(f"report detail {report_id} returned {status}")
            else:
                summary["reportDetail"] = report_id
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"report detail failed: {exc}")

    if args.allow_mutations and inspection_id:
        try:
            _, _, body = fetch(
                args.base_url,
                "/api/reports/generate",
                method="POST",
                payload={"inspectionId": inspection_id},
            )
            generated = json.loads(body.decode("utf-8"))
            if not generated.get("report", {}).get("id"):
                failures.append("report generation returned no report id")
            else:
                summary["generatedReport"] = generated["report"]["id"]
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"report generation failed: {exc}")

    print(json.dumps({"baseUrl": args.base_url, "summary": summary, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
