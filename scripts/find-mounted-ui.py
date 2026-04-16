#!/usr/bin/env python3
"""Build the dashboard mount graph and classify mounted vs dormant UI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from completion_audit_common import (
    COMPLETION_AUDIT_DIR,
    DASHBOARD_COMPONENTS,
    DASHBOARD_FEATURES,
    REPO_ROOT,
    build_dashboard_import_graph,
    classify_mount_status,
    collect_reachable_files,
    discover_page_roots,
    humanize_slug,
    list_dashboard_ui_files,
    slugify,
    write_json,
)


OUTPUT_PATH = COMPLETION_AUDIT_DIR / "dashboard-mount-graph.json"


def classify_kind(file_path: Path) -> str:
    if DASHBOARD_COMPONENTS in file_path.parents:
        return "component"
    if DASHBOARD_FEATURES in file_path.parents:
        return "feature"
    if "/hooks/" in file_path.as_posix():
        return "hook"
    if "/lib/" in file_path.as_posix():
        return "lib"
    return "other"


def completion_status(mount_status: str) -> str:
    if mount_status == "mounted":
        return "live_partial"
    if mount_status == "deprecated":
        return "deprecated"
    if mount_status == "partial":
        return "implemented_not_live"
    return "implemented_not_live"


def route_from_root(root: str) -> str:
    if root.endswith("/app/page.tsx"):
        return "/"
    if "/src/app/api/" in root and root.endswith("/route.ts"):
        route = root.split("/src/app", 1)[1][:-len("/route.ts")]
        return route
    if "/src/app/" in root and root.endswith("/page.tsx"):
        route = root.split("/src/app/", 1)[1][:-len("/page.tsx")]
        return "/" + route
    if "/src/app/" in root and root.endswith("/loading.tsx"):
        route = root.split("/src/app/", 1)[1][:-len("/loading.tsx")]
        return "/" + route
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    graph, reverse_graph = build_dashboard_import_graph()
    roots = discover_page_roots()
    reachable = collect_reachable_files(graph, roots)

    records: list[dict] = []
    for file_path in sorted(list_dashboard_ui_files()):
        if "/src/app/" in file_path.as_posix():
            continue
        relative = file_path.relative_to(REPO_ROOT).as_posix()
        importers = sorted(reverse_graph.get(relative, set()))
        reachable_roots = sorted(reachable.get(relative, set()))
        mount_status = classify_mount_status(file_path, set(reachable_roots))

        records.append(
            {
                "id": f"dashboard.mount.{slugify(relative)}",
                "title": humanize_slug(file_path.stem),
                "filePath": relative,
                "kind": classify_kind(file_path),
                "mountStatus": mount_status,
                "importers": importers,
                "reachableFromRoots": reachable_roots,
                "reachableFromRoutes": sorted({route_from_root(root) for root in reachable_roots}),
                "completionStatus": completion_status(mount_status),
                "notes": ["Derived from static import-graph reachability."],
            }
        )

    output_path = Path(args.output)
    write_json(output_path, records)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "fileCount": len(records),
                "mountedCount": sum(1 for record in records if record["mountStatus"] == "mounted"),
                "deprecatedCount": sum(1 for record in records if record["mountStatus"] == "deprecated"),
                "partialCount": sum(1 for record in records if record["mountStatus"] == "partial"),
                "unmountedCount": sum(1 for record in records if record["mountStatus"] == "unmounted"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
