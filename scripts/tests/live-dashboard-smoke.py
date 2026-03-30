#!/usr/bin/env python3
"""Smoke-test the live Athanor dashboard and its critical chat paths."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BASE_URL = (
    os.environ.get("ATHANOR_COMMAND_CENTER_URL")
    or os.environ.get("ATHANOR_DASHBOARD_URL")
    or "https://athanor.local"
).rstrip("/")
ROOT = Path(__file__).resolve().parents[2]
COMPLETION_DIR = ROOT / "docs" / "atlas" / "inventory" / "completion"
UI_AUDIT_REGISTRY = ROOT / "tests" / "ui-audit" / "surface-registry.json"


def load_routes() -> list[str]:
    if UI_AUDIT_REGISTRY.exists():
        payload = json.loads(UI_AUDIT_REGISTRY.read_text(encoding="utf-8"))
        routes = [
            record["routePath"]
            for record in payload.get("surfaces", [])
            if record.get("product") == "dashboard"
            and record.get("surfaceType") == "route"
            and record.get("routePath")
        ]
        if routes:
            return routes

    path = COMPLETION_DIR / "dashboard-route-census.json"
    if not path.exists():
        return [
            "/",
            "/services",
            "/gpu",
            "/chat",
            "/agents",
            "/tasks",
            "/goals",
            "/notifications",
            "/workplanner",
            "/workspace",
            "/activity",
            "/conversations",
            "/gallery",
            "/home",
            "/insights",
            "/learning",
            "/media",
            "/monitoring",
            "/more",
            "/outputs",
            "/personal-data",
            "/preferences",
            "/review",
            "/terminal",
            "/offline",
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [record["routePath"] for record in payload if record.get("kind") == "route"]


def load_apis() -> list[str]:
    if UI_AUDIT_REGISTRY.exists():
        payload = json.loads(UI_AUDIT_REGISTRY.read_text(encoding="utf-8"))
        owned_api_paths = {
            path
            for record in payload.get("surfaces", [])
            if record.get("product") == "dashboard" and record.get("surfaceType") == "route"
            for path in (record.get("ownedApis", []) or [])
        }
        path = COMPLETION_DIR / "dashboard-api-census.json"
        if path.exists():
            census = json.loads(path.read_text(encoding="utf-8"))
            api_paths: list[str] = ["/api/operator/session"]
            seen = {"/api/operator/session"}
            for record in census:
                api_path = record.get("apiPath", "")
                if api_path not in owned_api_paths:
                    continue
                if "GET" not in record.get("methods", []):
                    continue
                if record.get("responseMode") == "sse":
                    continue
                if ":" in api_path or "[" in api_path:
                    continue
                if api_path in seen:
                    continue
                seen.add(api_path)
                api_paths.append(api_path)
            if api_paths:
                return api_paths

    path = COMPLETION_DIR / "dashboard-api-census.json"
    if not path.exists():
        return [
            "/api/overview",
            "/api/services",
            "/api/gpu",
            "/api/models",
            "/api/projects",
            "/api/workforce",
            "/api/history",
            "/api/intelligence",
            "/api/memory",
            "/api/monitoring",
            "/api/media/overview",
            "/api/gallery/overview",
            "/api/home/overview",
            "/api/activity",
            "/api/conversations",
            "/api/outputs",
            "/api/preferences",
            "/api/personal-data/stats",
            "/api/insights",
            "/api/learning/metrics",
            "/api/learning/improvement",
            "/api/stash/stats",
            "/api/services/history",
            "/api/gpu/history",
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        record["apiPath"]
        for record in payload
        if "GET" in record.get("methods", [])
        and record.get("consumerStatus") != "orphan-candidate"
        and ":" not in record.get("apiPath", "")
        and record.get("responseMode") != "sse"
    ]

POST_APIS = {
    "/api/personal-data/search": {"query": "EoBQ", "limit": 3},
}

CHAT_PAYLOADS = [
    (
        "workshop-worker",
        {
            "target": "workshop-worker",
            "messages": [{"role": "user", "content": "Reply with OK only."}],
        },
    ),
    (
        "litellm-proxy",
        {
            "target": "litellm-proxy",
            "model": "reasoning",
            "messages": [{"role": "user", "content": "Reply with OK only."}],
        },
    ),
    (
        "agent-server",
        {
            "target": "agent-server",
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "threadId": "live-smoke-thread",
        },
    ),
]


def fetch(base_url: str, path: str, method: str = "GET", payload: Any = None, headers: dict[str, str] | None = None):
    request_headers = {"Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    if headers:
        request_headers.update(headers)

    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers=request_headers,
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.status, dict(response.headers), response.read()


def read_sse(base_url: str, path: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )

    events: list[dict[str, Any]] = []
    with urllib.request.urlopen(request, timeout=90) as response:
        buffer = ""
        while True:
            chunk = response.read(1024)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                data_lines = [line[5:].lstrip() for line in block.split("\n") if line.startswith("data:")]
                if not data_lines:
                    continue
                data = "\n".join(data_lines)
                if data == "[DONE]":
                    return events
                try:
                    events.append(json.loads(data))
                except json.JSONDecodeError:
                    events.append({"type": "malformed", "raw": data})
                if any(event.get("type") in {"done", "error"} for event in events):
                    return events
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Dashboard base URL.")
    args = parser.parse_args()
    routes = load_routes()
    apis = load_apis()

    failures: list[str] = []
    summary: dict[str, Any] = {}
    api_shapes: dict[str, Any] = {}

    for path in routes:
        try:
            status, _, body = fetch(args.base_url, path)
            if status != 200 or "<html" not in body.decode("utf-8", errors="replace").lower():
                failures.append(f"route {path} unexpected status/content: {status}")
            else:
                summary[path] = "ok"
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"route {path} failed: {exc}")

    for path in apis:
        try:
            status, _, body = fetch(args.base_url, path)
            payload = json.loads(body.decode("utf-8"))
            if status != 200:
                failures.append(f"api {path} unexpected status: {status}")
            elif isinstance(payload, dict):
                api_shapes[path] = sorted(payload.keys())[:8]
            elif isinstance(payload, list):
                api_shapes[path] = f"list[{len(payload)}]"
            else:
                api_shapes[path] = type(payload).__name__
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"api {path} failed: {exc}")

    for path, payload in POST_APIS.items():
        try:
            status, _, body = fetch(args.base_url, path, method="POST", payload=payload)
            parsed = json.loads(body.decode("utf-8"))
            if status != 200:
                failures.append(f"post api {path} unexpected status: {status}")
            elif isinstance(parsed, dict):
                api_shapes[path] = sorted(parsed.keys())[:8]
            else:
                api_shapes[path] = type(parsed).__name__
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"post api {path} failed: {exc}")

    try:
        _, _, body = fetch(args.base_url, "/api/models")
        models = json.loads(body.decode("utf-8"))
        backends = {backend.get("id"): backend for backend in models.get("backends", [])}
        for backend_id in ("litellm-proxy", "workshop-worker"):
            backend = backends.get(backend_id)
            if not backend:
                failures.append(f"models missing {backend_id} backend")
                continue
            if not backend.get("reachable"):
                failures.append(f"{backend_id} backend not reachable in live models snapshot")
            if int(backend.get("modelCount") or 0) <= 0:
                failures.append(f"{backend_id} modelCount not populated in live models snapshot")
            summary[backend_id] = {
                "reachable": backend.get("reachable"),
                "modelCount": backend.get("modelCount"),
            }
    except Exception as exc:  # pragma: no cover - live smoke only
        failures.append(f"model snapshot validation failed: {exc}")

    chat_results: dict[str, list[str]] = {}
    for label, payload in CHAT_PAYLOADS:
        try:
            events = read_sse(args.base_url, "/api/chat", payload)
            if not events:
                failures.append(f"chat {label} produced no events")
                continue
            if any(event.get("type") == "error" for event in events):
                failures.append(f"chat {label} returned error event: {events}")
                continue
            if not any(event.get("type") in {"assistant_delta", "done"} for event in events):
                failures.append(f"chat {label} missing assistant/done events: {events}")
                continue
            chat_results[label] = [event.get("type", "unknown") for event in events]
        except urllib.error.HTTPError as exc:  # pragma: no cover - live smoke only
            failures.append(f"chat {label} failed: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"chat {label} failed: {exc}")

    print(
        json.dumps(
            {
                "baseUrl": args.base_url,
                "routeCount": len(routes),
                "apiCount": len(apis) + len(POST_APIS),
                "apiShapesSample": api_shapes,
                "chatResults": chat_results,
                "summary": summary,
                "failures": failures,
            },
            indent=2,
        )
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
