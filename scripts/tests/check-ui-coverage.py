#!/usr/bin/env python3
"""Validate the UI surface registry coverage state and summarize manual/open surfaces."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

VALID_STATES = {
    "covered-automated",
    "covered-live",
    "covered-manual",
    "uncovered",
}

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "tests" / "ui-audit" / "surface-registry.json"
UNCOVERED_PATH = ROOT / "tests" / "ui-audit" / "uncovered-surfaces.json"


def main() -> int:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"Missing registry: {REGISTRY_PATH}")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    surfaces = registry.get("surfaces", [])
    invalid = [surface for surface in surfaces if surface.get("coverageStatus") not in VALID_STATES]
    uncovered = [surface for surface in surfaces if surface.get("coverageStatus") == "uncovered"]
    manual = [surface for surface in surfaces if surface.get("coverageStatus") == "covered-manual"]
    counts = Counter(surface.get("coverageStatus") for surface in surfaces)

    summary = {
        "surfaceCount": len(surfaces),
        "statusCounts": dict(sorted(counts.items())),
        "manualSurfaceCount": len(manual),
        "uncoveredSurfaceCount": len(uncovered),
        "manualSurfaceIds": [surface["id"] for surface in manual],
        "uncoveredSurfaceIds": [surface["id"] for surface in uncovered],
        "invalidSurfaceIds": [surface["id"] for surface in invalid],
    }
    UNCOVERED_PATH.write_text(
        json.dumps(
            {
                "generatedAt": registry.get("generatedAt"),
                "count": len(uncovered),
                "surfaces": uncovered,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 1 if invalid or uncovered else 0


if __name__ == "__main__":
    raise SystemExit(main())
