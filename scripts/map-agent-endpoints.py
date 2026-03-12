#!/usr/bin/env python3
"""Map agent-server endpoints into runtime subsystems and dashboard touchpoints."""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path

from completion_audit_common import (
    AGENT_SERVER,
    ATLAS_COMPLETION_DIR,
    load_runtime_inventory,
    read_text,
    slugify,
    write_json,
)


ENDPOINT_OUTPUT = ATLAS_COMPLETION_DIR / "agent-endpoint-census.json"
SUBSYSTEM_OUTPUT = ATLAS_COMPLETION_DIR / "runtime-subsystem-census.json"

SUBSYSTEM_RULES = [
    ("runtime.subsystem.subscriptions", "Subscription control layer", lambda path: path.startswith("/v1/subscriptions")),
    ("runtime.subsystem.task-engine", "Task engine", lambda path: path.startswith("/v1/tasks")),
    ("runtime.subsystem.workspace", "Workspace and CST", lambda path: path.startswith("/v1/workspace") or path.startswith("/v1/events") or path.startswith("/v1/cognitive") or path.startswith("/v1/conventions")),
    ("runtime.subsystem.goals-workplan", "Goals and workplan", lambda path: path.startswith("/v1/goals") or path.startswith("/v1/workplan") or path.startswith("/v1/projects") or path.startswith("/v1/scheduling")),
    ("runtime.subsystem.notifications-escalation", "Notifications and trust", lambda path: path.startswith("/v1/notifications") or path.startswith("/v1/escalation") or path.startswith("/v1/trust") or path.startswith("/v1/autonomy") or path.startswith("/v1/alerts") or path.startswith("/v1/feedback") or path.startswith("/v1/notification-budget")),
    ("runtime.subsystem.patterns-learning", "Patterns and learning", lambda path: path.startswith("/v1/patterns") or path.startswith("/v1/learning") or path.startswith("/v1/briefing") or path.startswith("/v1/metrics")),
    ("runtime.subsystem.skills-research-consolidation", "Skills, research jobs, and consolidation", lambda path: path.startswith("/v1/skills") or path.startswith("/v1/research/jobs") or path.startswith("/v1/consolidate")),
    ("runtime.history-outputs", "History and outputs", lambda path: path.startswith("/v1/activity") or path.startswith("/v1/conversations") or path.startswith("/v1/outputs")),
    ("runtime.memory", "Preferences and memory", lambda path: path.startswith("/v1/preferences")),
    ("runtime.routing-context", "Routing and context", lambda path: path.startswith("/v1/context") or path.startswith("/v1/routing")),
    ("runtime.chat", "Chat completions", lambda path: path == "/v1/chat/completions"),
    ("runtime.status", "Service and media status", lambda path: path.startswith("/v1/status")),
    ("runtime.catalog", "Health and model inventory", lambda path: path in {"/health", "/v1/models", "/v1/agents", "/v1/agents/registry"}),
]

SUBSYSTEM_TOUCHPOINTS = {
    "runtime.subsystem.subscriptions": ["/agents", "/tasks", "/workspace"],
    "runtime.subsystem.task-engine": ["/tasks", "/review", "/workplanner"],
    "runtime.subsystem.workspace": ["/workspace", "/activity", "/review"],
    "runtime.subsystem.goals-workplan": ["/goals", "/workplanner", "/tasks"],
    "runtime.subsystem.notifications-escalation": ["/notifications", "/review", "/tasks"],
    "runtime.subsystem.patterns-learning": ["/insights", "/learning", "/review"],
    "runtime.subsystem.skills-research-consolidation": ["/learning", "/workplanner", "/personal-data"],
    "runtime.history-outputs": ["/activity", "/conversations", "/outputs"],
    "runtime.memory": ["/preferences", "/personal-data"],
    "runtime.routing-context": ["/chat", "/agents"],
    "runtime.chat": ["/chat", "/agents"],
    "runtime.status": ["/services", "/media"],
    "runtime.catalog": ["/", "/chat", "/agents"],
}


def classify_subsystem(path: str) -> tuple[str, str]:
    for subsystem_id, title, predicate in SUBSYSTEM_RULES:
        if predicate(path):
            return subsystem_id, title
    return "runtime.misc", "Miscellaneous runtime"


def parse_endpoints() -> list[dict]:
    tree = ast.parse(read_text(AGENT_SERVER))
    endpoints: list[dict] = []
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if not isinstance(decorator.func.value, ast.Name) or decorator.func.value.id != "app":
                continue
            if not decorator.args:
                continue
            if not isinstance(decorator.args[0], ast.Constant) or not isinstance(decorator.args[0].value, str):
                continue
            method = decorator.func.attr.upper()
            path = decorator.args[0].value
            subsystem_id, subsystem_title = classify_subsystem(path)
            endpoints.append(
                {
                    "id": f"agent.endpoint.{slugify(method)}.{slugify(path)}",
                    "method": method,
                    "path": path,
                    "handler": node.name,
                    "subsystemId": subsystem_id,
                    "subsystemTitle": subsystem_title,
                }
            )
    return sorted(endpoints, key=lambda item: (item["subsystemId"], item["path"], item["method"]))


def completion_from_status_tag(status_tag: str | None, touchpoints: list[str]) -> str:
    if status_tag == "implemented_not_live":
        return "implemented_not_live"
    if not touchpoints:
        return "implemented_not_live"
    if status_tag == "live":
        return "live_partial"
    return "live_partial"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-output", default=str(ENDPOINT_OUTPUT))
    parser.add_argument("--subsystem-output", default=str(SUBSYSTEM_OUTPUT))
    args = parser.parse_args()

    endpoints = parse_endpoints()
    runtime_inventory = load_runtime_inventory()

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
        runtime_record = runtime_inventory.get(subsystem_id)
        status_tag = runtime_record.get("status_tag") if runtime_record else None
        touchpoints = SUBSYSTEM_TOUCHPOINTS.get(subsystem_id, [])
        subsystem_records.append(
            {
                "id": subsystem_id,
                "title": titles[subsystem_id],
                "dashboardTouchpoints": touchpoints,
                "endpointCount": len(subsystem_endpoints),
                "endpoints": subsystem_endpoints,
                "statusTag": status_tag,
                "completionStatus": completion_from_status_tag(status_tag, touchpoints),
                "notes": [
                    "Grouped from FastAPI route decorators in server.py.",
                    "Dashboard touchpoints are inferred from the current atlas/runtime model.",
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
