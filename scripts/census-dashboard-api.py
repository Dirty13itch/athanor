#!/usr/bin/env python3
"""Derive the canonical dashboard API census from filesystem and consumer evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from completion_audit_common import (
    COMPLETION_AUDIT_DIR,
    DASHBOARD_APP,
    DASHBOARD_SRC,
    detect_response_mode,
    extract_imports,
    list_dashboard_source_files,
    load_surface_registry,
    match_surface_api,
    normalize_api_path,
    parse_http_methods,
    read_text,
    slugify,
    write_json,
)


OUTPUT_PATH = COMPLETION_AUDIT_DIR / "dashboard-api-census.json"


SUPPORT_ONLY_PREFIXES = (
    "/api/stream",
    "/api/feedback",
    "/api/tts",
    "/api/push",
)
SUPPORT_ONLY_PATHS = {
    "/api/agents/proxy",
    "/api/governor/tool-permissions",
    "/api/gpu/swap",
    "/api/operator/session",
    "/api/stash/stats",
}
ACTION_WILDCARD_SEGMENTS = {
    "advance",
    "approve",
    "cancel",
    "confirm",
    "endorse",
    "execute",
    "hold",
    "reject",
    "resolve",
    "rollback",
    "run",
}


def detect_access_class(route_file: Path) -> str:
    text = read_text(route_file)
    if "requireSameOriginOperatorSessionAccess" in text:
        return "same-origin-operator-session"
    if "requireOperatorSessionAccess" in text:
        return "operator-session"
    if "requireOperatorMutationAccess" in text:
        return "operator-mutation"
    return "public"


def api_dir_to_api_path(directory: Path) -> str:
    relative = directory.relative_to(DASHBOARD_APP / "api")
    if not relative.parts:
        return "/api"
    parts = []
    for part in relative.parts:
        if part.startswith("[...") and part.endswith("]"):
            parts.append(f":{part[4:-1]}*")
        elif part.startswith("[") and part.endswith("]"):
            parts.append(f":{part[1:-1]}")
        else:
            parts.append(part)
    return "/api/" + "/".join(parts)


def family_for_api_path(api_path: str) -> str:
    parts = [part for part in api_path.split("/") if part]
    if len(parts) < 2:
        return "root"
    return parts[1]


def source_consumers(api_path: str) -> list[str]:
    consumers: set[str] = set()
    source_patterns = [
        re.compile(pattern)
        for pattern in _api_path_to_source_patterns(api_path)
    ]
    for file_path in list_dashboard_source_files():
        if "/app/api/" in file_path.as_posix():
            continue
        text = read_text(file_path)
        if api_path in text or any(pattern.search(text) for pattern in source_patterns):
            consumers.add(file_path.relative_to(DASHBOARD_SRC.parents[1]).as_posix())
    return sorted(consumers)


def _api_path_to_source_patterns(api_path: str) -> list[str]:
    pattern = re.escape(api_path)
    pattern = re.sub(
        r"/:([A-Za-z0-9_]+)\*",
        r"/(?:\\$\\{[^}]+\\}|[^/`\"'\\s)]+(?:/[^`\"'\\s)]*)*)",
        pattern,
    )
    pattern = re.sub(
        r"/:([A-Za-z0-9_]+)",
        r"/(?:\\$\\{[^}]+\\}|[^/`\"'\\s)]+)",
        pattern,
    )
    patterns = [pattern]

    parts = [part for part in api_path.split("/") if part]
    if len(parts) >= 2 and parts[-1] in ACTION_WILDCARD_SEGMENTS and any(part.startswith(":") for part in parts):
        action_wildcard = re.escape(api_path)
        action_wildcard = re.sub(
            r"/:([A-Za-z0-9_]+)\*",
            r"/(?:\\$\\{[^}]+\\}|[^/`\"'\\s)]+(?:/[^`\"'\\s)]*)*)",
            action_wildcard,
        )
        action_wildcard = re.sub(
            r"/:([A-Za-z0-9_]+)",
            r"/(?:\\$\\{[^}]+\\}|[^/`\"'\\s)]+)",
            action_wildcard,
        )
        action_wildcard = re.sub(
            rf"/{parts[-1]}$",
            r"/(?:\\$\\{[^}]+\\}|[^/`\"'\\s)]+)",
            action_wildcard,
        )
        patterns.append(action_wildcard)

    return patterns


def completion_status(consumer_status: str, coverage_status: str | None) -> str:
    if consumer_status == "consumed" and coverage_status == "covered-live":
        return "live_complete"
    if consumer_status == "consumed":
        return "live_partial"
    if consumer_status == "support-only":
        return "implemented_not_live"
    return "implemented_not_live"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    surface_registry = load_surface_registry()
    route_surfaces = surface_registry["routes"]
    api_surfaces = surface_registry["apis"]

    records: list[dict] = []
    for route_file in sorted((DASHBOARD_APP / "api").rglob("route.ts")):
        api_path = normalize_api_path(api_dir_to_api_path(route_file.parent))
        access_class = detect_access_class(route_file)
        title = api_path.replace("/api/", "").replace("/", " ").replace(":", "").replace("*", " wildcard ").strip()
        consumer_surfaces = [
            surface
            for surface in route_surfaces.values()
            if any(match_surface_api(owned_api, api_path) for owned_api in surface.get("ownedApis", []))
        ]
        consumer_surface_ids = sorted(surface["id"] for surface in consumer_surfaces if surface.get("id"))
        source_files = source_consumers(api_path)
        api_surface = next(
            (surface for path, surface in api_surfaces.items() if match_surface_api(path, api_path)),
            None,
        )

        if consumer_surface_ids or source_files:
            consumer_status = "consumed"
        elif api_surface:
            consumer_status = "support-only"
        elif api_path in SUPPORT_ONLY_PATHS:
            consumer_status = "support-only"
        elif api_path.startswith(SUPPORT_ONLY_PREFIXES):
            consumer_status = "support-only"
        else:
            consumer_status = "orphan-candidate"

        coverage_status = api_surface.get("coverageStatus") if api_surface else None
        local_checks = sorted(
            {
                check
                for check in (api_surface.get("localChecks", []) if api_surface else [])
            }
            | {
                check
                for surface in consumer_surfaces
                for check in surface.get("localChecks", [])
            }
        )
        live_checks = sorted(
            {
                check
                for check in (api_surface.get("liveChecks", []) if api_surface else [])
            }
            | {
                check
                for surface in consumer_surfaces
                for check in surface.get("liveChecks", [])
            }
        )
        notes = ["Discovered from filesystem API route census."]
        if consumer_status == "support-only":
            notes.append("Support-only, test-harness, or ambient API surface.")
        if consumer_status == "orphan-candidate":
            notes.append("No direct consumer evidence found in dashboard source or curated registry.")

        records.append(
            {
                "id": f"dashboard.api.{slugify(api_path)}",
                "title": (api_surface.get("title") if api_surface else None) or title.title() or api_path,
                "apiPath": api_path,
                "family": family_for_api_path(api_path),
                "sourceFile": route_file.relative_to(DASHBOARD_SRC.parents[1]).as_posix(),
                "methods": parse_http_methods(route_file),
                "responseMode": detect_response_mode(route_file),
                "accessClass": access_class,
                "consumerStatus": consumer_status,
                "likelyConsumers": sorted(set(consumer_surface_ids + source_files)),
                "coverage": {
                    "coverageStatus": coverage_status,
                    "localChecks": local_checks,
                    "liveChecks": live_checks,
                },
                "completionStatus": completion_status(consumer_status, coverage_status),
                "notes": notes,
            }
        )

    output_path = Path(args.output)
    write_json(output_path, records)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "apiCount": len(records),
                "orphanCandidateCount": sum(1 for record in records if record["consumerStatus"] == "orphan-candidate"),
                "supportOnlyCount": sum(1 for record in records if record["consumerStatus"] == "support-only"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
