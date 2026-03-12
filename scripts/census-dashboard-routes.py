#!/usr/bin/env python3
"""Derive the canonical dashboard route and support-surface census from source files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from completion_audit_common import (
    ATLAS_COMPLETION_DIR,
    DASHBOARD_APP,
    ROUTE_PAGE_FILES,
    app_dir_to_route_path,
    humanize_slug,
    load_navigation,
    load_surface_registry,
    read_text,
    safe_json_load,
    scan_route_headings,
    slugify,
    write_json,
)


ROUTE_OUTPUT = ATLAS_COMPLETION_DIR / "dashboard-route-census.json"
SUPPORT_OUTPUT = ATLAS_COMPLETION_DIR / "dashboard-support-surface-census.json"
SUPPORT_SURFACE_TEST = "projects/dashboard/src/app/support-surfaces.test.tsx"
SUPPORT_COMPLETE_STATUSES = {"covered-automated", "covered-manual", "covered-live"}
AUTOMATED_SUPPORT_ROUTE_PATHS = {"/offline"}


def infer_feature_module(page_file: Path) -> str | None:
    text = read_text(page_file)
    import_match = None
    for pattern in (r'from\s+"(@/features/[^"]+)"', r"from\s+'(@/features/[^']+)'"):
        import_match = re.search(pattern, text)
        if import_match:
            return import_match.group(1)
    return None


def completion_from_coverage(kind: str, coverage_status: str | None, route_path: str) -> str:
    if kind == "support_surface":
        return "live_complete" if coverage_status in SUPPORT_COMPLETE_STATUSES else "live_partial"
    if coverage_status == "covered-live":
        return "live_complete"
    if route_path in AUTOMATED_SUPPORT_ROUTE_PATHS and coverage_status in SUPPORT_COMPLETE_STATUSES:
        return "live_complete"
    if coverage_status in {"covered-automated", "covered-manual"}:
        return "live_partial"
    if route_path in load_navigation():
        return "live_partial"
    return "implemented_not_live"


def support_title(kind: str, route_path: str) -> str:
    if route_path == "/":
        route_label = "Root"
    else:
        route_label = route_path.strip("/").replace("/", " ")
    return f"{humanize_slug(kind.replace('.tsx', '').replace('-', ' '))} ({route_label.title()})"


def support_coverage() -> dict[str, object]:
    if (DASHBOARD_APP / "support-surfaces.test.tsx").exists():
        return {
            "coverageStatus": "covered-automated",
            "localChecks": [SUPPORT_SURFACE_TEST],
            "liveChecks": [],
            "primaryControls": ["support surface render"],
        }
    return {
        "coverageStatus": None,
        "localChecks": [],
        "liveChecks": [],
        "primaryControls": [],
    }


def build_route_records() -> tuple[list[dict], list[dict]]:
    navigation = load_navigation()
    surface_registry = load_surface_registry()["routes"]
    headings = scan_route_headings()

    route_records: list[dict] = []
    support_records: list[dict] = []
    seen_support_files: set[str] = set()
    shared_support_coverage = support_coverage()

    for page_file in sorted(DASHBOARD_APP.rglob("page.tsx")):
        if "/app/api/" in page_file.as_posix():
            continue
        route_path = app_dir_to_route_path(page_file.parent)
        if route_path is None:
            continue

        nav = navigation.get(route_path, {})
        coverage = surface_registry.get(route_path, {})
        support_files = [
            child.name
            for child in sorted(page_file.parent.iterdir())
            if child.is_file() and child.name in ROUTE_PAGE_FILES and child.name != "page.tsx"
        ]
        title = headings.get(route_path) or nav.get("label") or ("Command Center" if route_path == "/" else humanize_slug(page_file.parent.name))

        route_records.append(
            {
                "id": f"dashboard.route.{slugify(route_path)}",
                "title": title,
                "kind": "route",
                "routePath": route_path,
                "owner": {
                    "pageModule": page_file.relative_to(DASHBOARD_APP.parents[1]).as_posix(),
                    "featureModule": infer_feature_module(page_file),
                },
                "navigation": {
                    "inPrimaryNavigation": route_path in navigation,
                    "family": nav.get("family"),
                    "label": nav.get("label"),
                    "primary": nav.get("primary"),
                    "mobile": nav.get("mobile"),
                },
                "sourceFiles": {
                    "primary": page_file.relative_to(DASHBOARD_APP.parents[1]).as_posix(),
                    "supporting": [
                        (page_file.parent / name).relative_to(DASHBOARD_APP.parents[1]).as_posix()
                        for name in support_files
                    ],
                },
                "coverage": {
                    "coverageStatus": coverage.get("coverageStatus"),
                    "localChecks": coverage.get("localChecks", []),
                    "liveChecks": coverage.get("liveChecks", []),
                    "primaryControls": coverage.get("primaryControls", []),
                },
                "completionStatus": completion_from_coverage("route", coverage.get("coverageStatus"), route_path),
                "notes": [
                    "Discovered from filesystem route census.",
                    "Backed by navigation metadata." if route_path in navigation else "Direct URL or support route only.",
                ],
            }
        )

        for support_name in support_files:
            support_file = page_file.parent / support_name
            support_file_key = support_file.relative_to(DASHBOARD_APP.parents[1]).as_posix()
            if support_file_key in seen_support_files:
                continue
            seen_support_files.add(support_file_key)
            coverage = dict(shared_support_coverage)
            support_records.append(
                {
                    "id": f"dashboard.support.{slugify(route_path)}.{slugify(support_name)}",
                    "title": support_title(support_name, route_path),
                    "kind": "support_surface",
                    "routePath": route_path,
                    "owner": {
                        "pageModule": support_file.relative_to(DASHBOARD_APP.parents[1]).as_posix(),
                        "featureModule": infer_feature_module(page_file),
                    },
                    "navigation": {
                        "inPrimaryNavigation": route_path in navigation,
                        "family": nav.get("family"),
                        "label": nav.get("label"),
                        "primary": nav.get("primary"),
                        "mobile": nav.get("mobile"),
                    },
                    "sourceFiles": {
                        "primary": support_file_key,
                        "supporting": [],
                    },
                    "coverage": coverage,
                    "completionStatus": completion_from_coverage("support_surface", coverage["coverageStatus"], route_path),
                    "notes": [
                        "Support surface discovered from route-local app file census.",
                        "Covered by the dedicated support-surface render harness."
                        if coverage["coverageStatus"]
                        else "No dedicated automated coverage is registered yet.",
                    ],
                }
            )

    global_support_names = [
        "layout.tsx",
        "loading.tsx",
        "error.tsx",
        "global-error.tsx",
        "not-found.tsx",
        "manifest.ts",
    ]
    for support_name in global_support_names:
        support_file = DASHBOARD_APP / support_name
        if not support_file.exists():
            continue
        support_file_key = support_file.relative_to(DASHBOARD_APP.parents[1]).as_posix()
        if support_file_key in seen_support_files:
            continue
        seen_support_files.add(support_file_key)
        coverage = dict(shared_support_coverage)
        support_records.append(
            {
                "id": f"dashboard.support.root.{slugify(support_name)}",
                "title": support_title(support_name, "/"),
                "kind": "support_surface",
                "routePath": "/",
                "owner": {
                    "pageModule": support_file.relative_to(DASHBOARD_APP.parents[1]).as_posix(),
                    "featureModule": None,
                },
                "navigation": {
                    "inPrimaryNavigation": True,
                    "family": "core",
                    "label": "Command Center",
                    "primary": True,
                    "mobile": True,
                },
                "sourceFiles": {
                    "primary": support_file_key,
                    "supporting": [],
                },
                "coverage": coverage,
                "completionStatus": completion_from_coverage("support_surface", coverage["coverageStatus"], "/"),
                "notes": [
                    "Global app support surface.",
                    "Covered by the dedicated support-surface render harness."
                    if coverage["coverageStatus"]
                    else "Requires dedicated support-surface probing for full completion coverage.",
                ],
            }
        )

    return route_records, support_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route-output", default=str(ROUTE_OUTPUT))
    parser.add_argument("--support-output", default=str(SUPPORT_OUTPUT))
    args = parser.parse_args()

    route_records, support_records = build_route_records()
    route_output = Path(args.route_output)
    support_output = Path(args.support_output)
    write_json(route_output, route_records)
    write_json(support_output, support_records)

    print(
        json.dumps(
            {
                "routeOutput": str(route_output),
                "supportOutput": str(support_output),
                "routeCount": len(route_records),
                "supportSurfaceCount": len(support_records),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
