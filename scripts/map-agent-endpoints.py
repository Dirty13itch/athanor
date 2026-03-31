#!/usr/bin/env python3
"""Map live agent-server endpoints into runtime subsystems and dashboard touchpoints."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from fastapi.routing import APIRoute

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"
if str(AGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(AGENTS_SRC))

from athanor_agents.server import app  # noqa: E402

from completion_audit_common import (  # noqa: E402
    COMPLETION_AUDIT_DIR,
    load_navigation,
    load_runtime_subsystem_registry,
    slugify,
    write_json,
)


ENDPOINT_OUTPUT = COMPLETION_AUDIT_DIR / "agent-endpoint-census.json"
SUBSYSTEM_OUTPUT = COMPLETION_AUDIT_DIR / "runtime-subsystem-census.json"
EXCLUDED_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

SUBSYSTEM_RULES = [
    (
        "runtime.subsystem.model-governance",
        "Model governance and proving ground",
        ("/v1/models/governance", "/v1/models/proving-ground"),
    ),
    (
        "runtime.subsystem.subscriptions",
        "Subscription control layer",
        ("/v1/subscriptions",),
    ),
    (
        "runtime.subsystem.task-engine",
        "Task engine and governor posture",
        ("/v1/tasks", "/v1/scheduler", "/v1/scheduling", "/v1/governor", "/v1/emergency"),
    ),
    (
        "runtime.subsystem.workspace",
        "Workspace and competition state",
        ("/v1/workspace", "/v1/events", "/v1/cognitive"),
    ),
    (
        "runtime.subsystem.goals-workplan",
        "Goals, workplan, and projects",
        ("/v1/goals", "/v1/workplan", "/v1/projects", "/v1/plans", "/v1/pipeline", "/v1/steer", "/v1/react"),
    ),
    (
        "runtime.subsystem.notifications-escalation",
        "Notifications, trust, and escalation",
        ("/v1/notifications", "/v1/escalation", "/v1/alerts", "/v1/autonomy", "/v1/trust", "/v1/notification-budget", "/v1/feedback"),
    ),
    (
        "runtime.subsystem.patterns-learning",
        "Patterns, learning, and improvement",
        ("/v1/patterns", "/v1/learning", "/v1/metrics", "/v1/improvement", "/v1/briefing", "/v1/diagnosis"),
    ),
    (
        "runtime.subsystem.skills-research-consolidation",
        "Skills, research jobs, and consolidation",
        ("/v1/skills", "/v1/research/jobs", "/v1/consolidate", "/v1/workflows"),
    ),
    (
        "runtime.history-outputs",
        "History and outputs",
        ("/v1/activity", "/v1/conversations", "/v1/outputs", "/v1/digests"),
    ),
    (
        "runtime.memory",
        "Preferences and memory",
        ("/v1/preferences", "/v1/preferences/learning", "/v1/conventions", "/v1/core-memory"),
    ),
    (
        "runtime.routing-context",
        "Routing and context",
        ("/v1/context", "/v1/routing", "/v1/cache", "/v1/circuits"),
    ),
    (
        "runtime.chat",
        "Chat completions",
        ("/v1/chat/completions",),
    ),
    (
        "runtime.catalog",
        "Health and model inventory",
        ("/health", "/v1/system-map", "/v1/models", "/v1/agents"),
    ),
    (
        "runtime.status",
        "Service and operator status",
        ("/v1/status", "/v1/home", "/v1/operator", "/v1/gpu"),
    ),
]


def classify_subsystem(path: str) -> tuple[str, str]:
    for subsystem_id, title, prefixes in SUBSYSTEM_RULES:
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes):
            return subsystem_id, title
    return "runtime.misc", "Miscellaneous runtime"


def parse_endpoints() -> list[dict]:
    endpoints: list[dict] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        if path in EXCLUDED_PATHS:
            continue
        if not (path == "/health" or path.startswith("/v1/")):
            continue

        subsystem_id, subsystem_title = classify_subsystem(path)
        methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
        for method in methods:
            endpoints.append(
                {
                    "id": f"agent.endpoint.{slugify(method)}.{slugify(path)}",
                    "method": method,
                    "path": path,
                    "handler": route.endpoint.__name__,
                    "subsystemId": subsystem_id,
                    "subsystemTitle": subsystem_title,
                }
            )

    return sorted(endpoints, key=lambda item: (item["subsystemId"], item["path"], item["method"], item["handler"]))


def completion_from_status_tag(status_tag: str | None, touchpoints: list[str]) -> str:
    if status_tag == "implemented_not_live":
        return "implemented_not_live"
    if status_tag == "live":
        return "live_partial"
    if touchpoints:
        return "live_partial"
    return "implemented_not_live"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-output", default=str(ENDPOINT_OUTPUT))
    parser.add_argument("--subsystem-output", default=str(SUBSYSTEM_OUTPUT))
    args = parser.parse_args()

    endpoints = parse_endpoints()
    dashboard_routes = set(load_navigation().keys()) | {"/"}
    subsystem_registry = load_runtime_subsystem_registry()

    grouped: dict[str, list[dict]] = defaultdict(list)
    titles: dict[str, str] = {}
    for endpoint in endpoints:
        grouped[endpoint["subsystemId"]].append(
            {
                "method": endpoint["method"],
                "path": endpoint["path"],
                "handler": endpoint["handler"],
            }
        )
        titles[endpoint["subsystemId"]] = endpoint["subsystemTitle"]

    subsystem_records: list[dict] = []
    for subsystem_id, subsystem_endpoints in sorted(grouped.items()):
        registry_record = subsystem_registry.get(subsystem_id, {})
        touchpoints = sorted(
            route_path
            for route_path in registry_record.get("dashboard_touchpoints", [])
            if route_path in dashboard_routes
        )
        status_tag = str(registry_record.get("status_tag") or "") or ("live" if subsystem_id != "runtime.misc" else None)
        subsystem_records.append(
            {
                "id": subsystem_id,
                "title": str(registry_record.get("title") or titles[subsystem_id]),
                "dashboardTouchpoints": touchpoints,
                "endpointCount": len(subsystem_endpoints),
                "endpoints": subsystem_endpoints,
                "statusTag": status_tag,
                "completionStatus": completion_from_status_tag(status_tag, touchpoints),
                "notes": [
                    "Grouped from the live FastAPI route registry on athanor_agents.server.app.",
                    "Dashboard touchpoints and status tags come from config/automation-backbone/runtime-subsystem-registry.json.",
                ],
            }
        )

    endpoint_output = Path(args.endpoint_output)
    subsystem_output = Path(args.subsystem_output)
    write_json(endpoint_output, endpoints)
    write_json(subsystem_output, subsystem_records)
    print(
        json.dumps(
            {
                "endpointOutput": str(endpoint_output),
                "subsystemOutput": str(subsystem_output),
                "endpointCount": len(endpoints),
                "subsystemCount": len(subsystem_records),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
