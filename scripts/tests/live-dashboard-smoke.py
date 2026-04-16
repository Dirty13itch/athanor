#!/usr/bin/env python3
"""Smoke-test the live Athanor dashboard and its critical chat paths.

Evidence producer only; outputs from this harness are proof surfaces for UI verification, not runtime or queue authority.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

DEFAULT_BASE_URL = "https://athanor.local/"
ROOT = SCRIPT_DIR.parents[1]
COMPLETION_DIR = ROOT / "reports" / "completion-audit" / "latest" / "inventory"
UI_AUDIT_REGISTRY = ROOT / "tests" / "ui-audit" / "surface-registry.json"

FALLBACK_ROUTES = [
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
    "/workforce",
    "/pipeline",
    "/activity",
    "/conversations",
    "/gallery",
    "/home",
    "/insights",
    "/learning",
    "/media",
    "/monitoring",
    "/models",
    "/operator",
    "/outputs",
    "/personal-data",
    "/preferences",
    "/review",
    "/terminal",
]

FALLBACK_APIS = [
    "/api/overview",
    "/api/services",
    "/api/services/history",
    "/api/gpu",
    "/api/gpu/history",
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
    "/api/personal-data/search",
]

SAFE_OPERATOR_APIS = [
    "/api/operator/context",
    "/api/operator/session",
    "/api/operator/nav-attention",
    "/api/operator/ui-preferences",
]


class NextStaticAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.asset_paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key not in {"href", "src"} or not value:
                continue
            if value.startswith("/_next/static/"):
                self.asset_paths.append(value)


def load_routes() -> list[str]:
    if UI_AUDIT_REGISTRY.exists():
        payload = json.loads(UI_AUDIT_REGISTRY.read_text(encoding="utf-8"))
        routes = [
            str(record["routePath"])
            for record in payload.get("surfaces", [])
            if record.get("product") == "dashboard"
            and record.get("surfaceType") == "route"
            and record.get("coverageStatus") == "covered-live"
            and record.get("routePath")
        ]
        if routes:
            return routes

    path = COMPLETION_DIR / "dashboard-route-census.json"
    if not path.exists():
        return FALLBACK_ROUTES
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [record["routePath"] for record in payload if record.get("kind") == "route"]


def load_apis() -> list[str]:
    if UI_AUDIT_REGISTRY.exists():
        payload = json.loads(UI_AUDIT_REGISTRY.read_text(encoding="utf-8"))
        apis = [
            str(record["apiPath"])
            for record in payload.get("surfaces", [])
            if record.get("product") == "dashboard"
            and record.get("surfaceType") == "api"
            and record.get("coverageStatus") == "covered-live"
            and record.get("apiPath")
            and ":" not in str(record.get("apiPath"))
            and str(record.get("apiPath")) not in POST_APIS
        ]
        if apis:
            ordered = apis + SAFE_OPERATOR_APIS
            unique_paths: list[str] = []
            for path in ordered:
                if path not in unique_paths:
                    unique_paths.append(path)
            return unique_paths

    path = COMPLETION_DIR / "dashboard-api-census.json"
    if not path.exists():
        return FALLBACK_APIS + SAFE_OPERATOR_APIS
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        record["apiPath"]
        for record in payload
        if "GET" in record.get("methods", [])
        and record.get("consumerStatus") != "orphan-candidate"
        and ":" not in record.get("apiPath", "")
        and record.get("responseMode") != "sse"
    ]

POST_APIS = {"/api/personal-data/search": {"query": "EoBQ", "limit": 3}}

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


def sample_next_static_assets(root_html: str) -> list[str]:
    parser = NextStaticAssetParser()
    parser.feed(root_html)
    unique_paths: list[str] = []
    for asset_path in parser.asset_paths:
        if asset_path not in unique_paths:
            unique_paths.append(asset_path)
    return unique_paths[:6]


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
    parser.add_argument(
        "--skip-next-static-check",
        action="store_true",
        help="Skip validation of sampled /_next/static assets referenced by the root HTML.",
    )
    args = parser.parse_args()
    routes = load_routes()
    apis = load_apis()

    failures: list[str] = []
    summary: dict[str, Any] = {}
    api_shapes: dict[str, Any] = {}

    for path in routes:
        try:
            status, _, body = fetch(args.base_url, path)
            decoded_body = body.decode("utf-8", errors="replace")
            if status != 200 or "<html" not in decoded_body.lower():
                failures.append(f"route {path} unexpected status/content: {status}")
            else:
                summary[path] = "ok"
                if path == "/" and not args.skip_next_static_check:
                    asset_failures: list[str] = []
                    for asset_path in sample_next_static_assets(decoded_body):
                        try:
                            asset_status, _, _ = fetch(args.base_url, asset_path)
                            if asset_status != 200:
                                asset_failures.append(f"{asset_path} -> {asset_status}")
                        except Exception as exc:  # pragma: no cover - live smoke only
                            asset_failures.append(f"{asset_path} -> {exc}")
                    if asset_failures:
                        failures.append("root /_next/static assets failed: " + "; ".join(asset_failures))
                    else:
                        summary["/_next/static"] = "ok"
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
