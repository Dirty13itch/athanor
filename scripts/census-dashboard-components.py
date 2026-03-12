#!/usr/bin/env python3
"""Inventory dashboard components and feature modules for completion auditing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from completion_audit_common import (
    ATLAS_COMPLETION_DIR,
    DASHBOARD_COMPONENTS,
    DASHBOARD_FEATURES,
    DEPRECATED_UI_BASENAMES,
    PARTIAL_UI_BASENAMES,
    UNMOUNTED_UI_BASENAMES,
    humanize_slug,
    list_dashboard_ui_files,
    slugify,
    write_json,
)


OUTPUT_PATH = ATLAS_COMPLETION_DIR / "dashboard-component-census.json"

SHELL_COMPONENTS = {
    "app-shell.tsx",
    "command-palette.tsx",
    "sidebar-nav.tsx",
    "family-tabs.tsx",
    "page-header.tsx",
    "route-icon.tsx",
    "status-dot.tsx",
}


def classify_group(path: Path) -> str:
    if "/components/ui/" in path.as_posix():
        return "design-system"
    if "/components/gen-ui/" in path.as_posix() and path.name != "feedback-buttons.tsx":
        return "archived-reference"
    if path.parent == DASHBOARD_COMPONENTS and path.name in SHELL_COMPONENTS:
        return "shell"
    if path.parent == DASHBOARD_COMPONENTS and path.name in DEPRECATED_UI_BASENAMES:
        return "archived-reference"
    if path.parent == DASHBOARD_COMPONENTS and path.name in UNMOUNTED_UI_BASENAMES:
        return "ambient-dormant"
    if path.parent == DASHBOARD_COMPONENTS and path.name in PARTIAL_UI_BASENAMES:
        return "partial-shell"
    if path.parent == DASHBOARD_COMPONENTS:
        return "shared-component"
    if DASHBOARD_FEATURES in path.parents:
        feature = path.relative_to(DASHBOARD_FEATURES).parts[0]
        if "console" in path.stem:
            return f"feature-console:{feature}"
        return f"feature-module:{feature}"
    return "other"


def completion_status(group: str) -> str:
    if group == "archived-reference":
        return "deprecated"
    if group in {"ambient-dormant", "partial-shell"}:
        return "implemented_not_live"
    return "live_partial"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    records: list[dict] = []
    for file_path in sorted(list_dashboard_ui_files()):
        if file_path.suffix not in {".ts", ".tsx"}:
            continue
        if file_path.name in {"layout.tsx", "page.tsx", "loading.tsx", "error.tsx", "global-error.tsx", "not-found.tsx"}:
            continue
        if "/app/" in file_path.as_posix() and "/app/api/" not in file_path.as_posix():
            continue

        group = classify_group(file_path)
        story_file = file_path.with_name(file_path.stem + ".stories" + file_path.suffix)
        test_file = file_path.with_name(file_path.stem + ".test" + file_path.suffix)

        records.append(
            {
                "id": f"dashboard.component.{slugify(file_path.relative_to(DASHBOARD_COMPONENTS.parents[1]).as_posix())}",
                "title": humanize_slug(file_path.stem),
                "filePath": file_path.relative_to(DASHBOARD_COMPONENTS.parents[1]).as_posix(),
                "group": group,
                "hasStory": story_file.exists(),
                "hasTest": test_file.exists(),
                "completionStatus": completion_status(group),
                "notes": ["Discovered from dashboard component/feature census."],
            }
        )

    output_path = Path(args.output)
    write_json(output_path, records)
    print(
        json.dumps(
            {
                "output": str(output_path),
                "componentCount": len(records),
                "ambientDormantCount": sum(1 for record in records if record["group"] == "ambient-dormant"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
