#!/usr/bin/env python3
"""Smoke-test the live Athanor dashboard and its critical chat paths.

Evidence producer only; outputs from this harness are proof surfaces for UI verification, not runtime or queue authority.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

DEFAULT_BASE_URL = "https://athanor.local/"
ROOT = SCRIPT_DIR.parents[1]
COMPLETION_DIR = ROOT / "reports" / "completion-audit" / "latest" / "inventory"
UI_AUDIT_REGISTRY = ROOT / "tests" / "ui-audit" / "surface-registry.json"
LAST_OUTPUT_PATH = ROOT / "tests" / "ui-audit" / "live-dashboard-smoke-last.json"
COMMAND_CENTER_FINAL_FORM_ROUTES = [
    "/",
    "/operator",
    "/projects",
]
COMMAND_CENTER_FINAL_FORM_APIS = [
    "/api/master-atlas",
    "/api/operator/mobile-summary",
    "/api/operator/summary",
    "/api/projects/factory",
]
COMMAND_CENTER_API_FRESHNESS_BUDGET = timedelta(minutes=20)
COMMAND_CENTER_ROUTE_PLACEHOLDERS = {
    "Loading local operator digest.": "placeholder_operator_digest",
    "No governed work published.": "placeholder_current_work",
    "Steady-state queue posture unavailable.": "placeholder_queue_posture",
}
COMMAND_CENTER_REQUIRED_ROUTE_MARKERS = {
    "/": ["Command Center", "Next governed move"],
    "/operator": ["Operator Console", "Project-output review"],
    "/projects": ["Governed Projects", "First-class governed lanes"],
}

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
    "/projects",
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
    "/api/master-atlas",
    "/api/operator/context",
    "/api/operator/mobile-summary",
    "/api/operator/session",
    "/api/operator/nav-attention",
    "/api/operator/summary",
    "/api/operator/ui-preferences",
    "/api/projects/factory",
]


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_command_center_timestamp(path: str, payload: dict[str, Any]) -> datetime | None:
    if path == "/api/master-atlas":
        return _parse_iso_timestamp(payload.get("generated_at"))

    if path == "/api/operator/mobile-summary":
        summary = payload.get("summary")
        if isinstance(summary, dict):
            return _parse_iso_timestamp(summary.get("generatedAt") or summary.get("generated_at"))
        return None

    if path == "/api/projects/factory":
        return _parse_iso_timestamp(payload.get("generatedAt") or payload.get("generated_at"))

    if path == "/api/operator/summary":
        steady_state = payload.get("steadyState")
        if isinstance(steady_state, dict):
            return _parse_iso_timestamp(steady_state.get("generatedAt") or steady_state.get("generated_at"))
        blocker_map = payload.get("blockerMap")
        if isinstance(blocker_map, dict):
            return _parse_iso_timestamp(blocker_map.get("generated_at"))
        return None

    return None


def evaluate_command_center_api_semantics(path: str, payload: Any) -> tuple[str, str | None]:
    if not isinstance(payload, dict):
        return ("invalid_payload", "API did not return a JSON object payload.")

    if path == "/api/operator/mobile-summary":
        summary = payload.get("summary")
        status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
        if not isinstance(summary, dict):
            return ("missing_summary", "Operator mobile summary returned no canonical summary payload.")
        if status.get("available") is False or status.get("degraded") is True:
            return ("degraded_summary", str(status.get("detail") or "Operator mobile summary is degraded."))
        if not isinstance(summary.get("proofGate"), dict) or not isinstance(summary.get("projectFactory"), dict):
            return ("incomplete_summary", "Operator mobile summary is missing proof-gate or project-factory state.")
        return ("ok", None)

    if path == "/api/projects/factory":
        if payload.get("available") is False or payload.get("degraded") is True:
            return ("degraded_summary", str(payload.get("detail") or "Project factory snapshot is degraded."))
        if not isinstance(payload.get("summary"), dict):
            return ("missing_summary", "Project factory snapshot returned no summary payload.")
        if not isinstance(payload.get("finalFormStatus"), dict):
            return ("missing_final_form_status", "Project factory snapshot is missing final-form status.")
        first_class = payload.get("firstClassProjects")
        if not isinstance(first_class, list):
            return ("missing_project_records", "Project factory snapshot is missing first-class project records.")
        return ("ok", None)

    if path == "/api/operator/summary":
        if not isinstance(payload.get("projectFactory"), dict):
            return ("missing_project_factory", "Operator summary is missing project-factory state.")
        if not isinstance(payload.get("steadyState"), dict):
            return ("missing_steady_state", "Operator summary is missing steady-state posture.")
        if not isinstance(payload.get("blockerMap"), dict):
            return ("missing_blocker_map", "Operator summary is missing blocker-map posture.")
        return ("ok", None)

    if path == "/api/master-atlas":
        if payload.get("available") is False or payload.get("degraded") is True:
            return ("degraded_summary", str(payload.get("detail") or "Master atlas feed is degraded."))
        if not isinstance(payload.get("summary"), dict):
            return ("missing_summary", "Master atlas is missing summary projection.")
    timestamp = _extract_command_center_timestamp(path, payload)
    if timestamp is not None:
        age = datetime.now(timezone.utc) - timestamp
        if age > COMMAND_CENTER_API_FRESHNESS_BUDGET:
            rounded_minutes = int(age.total_seconds() // 60)
            return (
                "stale_payload",
                f"Command-center API payload is stale by {rounded_minutes} minute(s).",
            )

    return ("ok", None)


def evaluate_command_center_route_semantics(path: str, body: str) -> tuple[str, str | None]:
    lowered_body = body.lower()
    for placeholder, code in COMMAND_CENTER_ROUTE_PLACEHOLDERS.items():
        if placeholder.lower() in lowered_body:
            return (code, f"Route HTML still contains placeholder posture: {placeholder}")

    for marker in COMMAND_CENTER_REQUIRED_ROUTE_MARKERS.get(path, []):
        if marker.lower() not in lowered_body:
            return ("missing_server_truth", f"Route HTML is missing required first-paint marker: {marker}")

    return ("ok", None)


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
COMMAND_CENTER_FINAL_FORM_POST_APIS: dict[str, dict[str, Any]] = {}

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


def _build_ssl_context(*, insecure: bool):
    if not insecure:
        return None
    return ssl._create_unverified_context()


def fetch(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Any = None,
    headers: dict[str, str] | None = None,
    *,
    insecure: bool = False,
):
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
    with urllib.request.urlopen(request, timeout=45, context=_build_ssl_context(insecure=insecure)) as response:
        return response.status, dict(response.headers), response.read()


def sample_next_static_assets(root_html: str) -> list[str]:
    parser = NextStaticAssetParser()
    parser.feed(root_html)
    unique_paths: list[str] = []
    for asset_path in parser.asset_paths:
        if asset_path not in unique_paths:
            unique_paths.append(asset_path)
    return unique_paths[:6]


def read_sse(base_url: str, path: str, payload: dict[str, Any], *, insecure: bool = False) -> list[dict[str, Any]]:
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
    with urllib.request.urlopen(request, timeout=90, context=_build_ssl_context(insecure=insecure)) as response:
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
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification for internal self-signed dashboard HTTPS.")
    parser.add_argument("--skip-chat", action="store_true", help="Skip chat SSE validation and only probe routes/APIs.")
    parser.add_argument(
        "--scope",
        choices=("full", "command-center-final-form"),
        default="full",
        help="Limit the smoke run to a specific verification scope.",
    )
    parser.add_argument(
        "--skip-next-static-check",
        action="store_true",
        help="Skip validation of sampled /_next/static assets referenced by the root HTML.",
    )
    args = parser.parse_args()
    if args.scope == "command-center-final-form":
        routes = COMMAND_CENTER_FINAL_FORM_ROUTES
        apis = COMMAND_CENTER_FINAL_FORM_APIS
    else:
        routes = load_routes()
        apis = load_apis()

    failures: list[str] = []
    summary: dict[str, Any] = {}
    api_shapes: dict[str, Any] = {}
    api_runtime_status: dict[str, Any] = {}
    route_runtime_status: dict[str, Any] = {}

    for path in routes:
        try:
            status, _, body = fetch(args.base_url, path, insecure=args.insecure)
            decoded_body = body.decode("utf-8", errors="replace")
            if status != 200 or "<html" not in decoded_body.lower():
                failures.append(f"route {path} unexpected status/content: {status}")
            else:
                summary[path] = "ok"
                if args.scope == "command-center-final-form":
                    semantic_status, semantic_detail = evaluate_command_center_route_semantics(path, decoded_body)
                    route_runtime_status[path] = {
                        "semanticStatus": semantic_status,
                        "detail": semantic_detail,
                    }
                    if semantic_status != "ok":
                        failures.append(f"route {path} semantic failure: {semantic_status}: {semantic_detail}")
                if path == "/" and not args.skip_next_static_check:
                    asset_failures: list[str] = []
                    for asset_path in sample_next_static_assets(decoded_body):
                        try:
                            asset_status, _, _ = fetch(args.base_url, asset_path, insecure=args.insecure)
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
            status, _, body = fetch(args.base_url, path, insecure=args.insecure)
            payload = json.loads(body.decode("utf-8"))
            if status != 200:
                failures.append(f"api {path} unexpected status: {status}")
            elif isinstance(payload, dict):
                api_shapes[path] = sorted(payload.keys())[:8]
                semantic_status, semantic_detail = evaluate_command_center_api_semantics(path, payload)
                api_runtime_status[path] = {
                    "semanticStatus": semantic_status,
                    "detail": semantic_detail,
                }
                if args.scope == "command-center-final-form" and semantic_status != "ok":
                    failures.append(f"api {path} semantic failure: {semantic_status}: {semantic_detail}")
            elif isinstance(payload, list):
                api_shapes[path] = f"list[{len(payload)}]"
                api_runtime_status[path] = {
                    "semanticStatus": "unexpected_list",
                    "detail": "API returned a JSON list instead of an object payload.",
                }
                if args.scope == "command-center-final-form":
                    failures.append(f"api {path} semantic failure: unexpected_list: API returned a JSON list instead of an object payload.")
            else:
                api_shapes[path] = type(payload).__name__
                api_runtime_status[path] = {
                    "semanticStatus": "unexpected_payload_type",
                    "detail": f"API returned {type(payload).__name__} instead of a JSON object payload.",
                }
                if args.scope == "command-center-final-form":
                    failures.append(
                        f"api {path} semantic failure: unexpected_payload_type: API returned {type(payload).__name__} instead of a JSON object payload."
                    )
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"api {path} failed: {exc}")
            api_runtime_status[path] = {
                "semanticStatus": "request_failed",
                "detail": str(exc),
            }

    post_apis = COMMAND_CENTER_FINAL_FORM_POST_APIS if args.scope == "command-center-final-form" else POST_APIS

    for path, payload in post_apis.items():
        try:
            status, _, body = fetch(args.base_url, path, method="POST", payload=payload, insecure=args.insecure)
            parsed = json.loads(body.decode("utf-8"))
            if status != 200:
                failures.append(f"post api {path} unexpected status: {status}")
            elif isinstance(parsed, dict):
                api_shapes[path] = sorted(parsed.keys())[:8]
            else:
                api_shapes[path] = type(parsed).__name__
        except Exception as exc:  # pragma: no cover - live smoke only
            failures.append(f"post api {path} failed: {exc}")

    if args.scope == "full":
        try:
            _, _, body = fetch(args.base_url, "/api/models", insecure=args.insecure)
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
    if not args.skip_chat:
        for label, payload in CHAT_PAYLOADS:
            try:
                events = read_sse(args.base_url, "/api/chat", payload, insecure=args.insecure)
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

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseUrl": args.base_url,
        "routeCount": len(routes),
        "apiCount": len(apis) + len(post_apis),
        "apiShapesSample": api_shapes,
        "apiRuntimeStatus": api_runtime_status,
        "routeRuntimeStatus": route_runtime_status,
        "chatResults": chat_results,
        "summary": summary,
        "failures": failures,
    }
    LAST_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            payload,
            indent=2,
        )
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
