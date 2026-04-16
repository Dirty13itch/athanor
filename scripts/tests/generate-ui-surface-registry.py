#!/usr/bin/env python3
"""Generate the canonical UI surface registry and uncovered-surface list.

Evidence producer only; generated JSON from this script is proof surfaces for UI audit coverage, not runtime or queue authority.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ui_audit_data import SURFACES

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "tests" / "ui-audit"
REGISTRY_PATH = OUTPUT_DIR / "surface-registry.json"
UNCOVERED_PATH = OUTPUT_DIR / "uncovered-surfaces.json"
def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    registry = {
        "generatedAt": generated_at,
        "coverageStates": [
            "covered-automated",
            "covered-live",
            "covered-manual",
            "uncovered",
        ],
        "surfaceCount": len(SURFACES),
        "surfaces": SURFACES,
    }
    uncovered = [surface for surface in SURFACES if surface["coverageStatus"] == "uncovered"]
    uncovered_payload = {
        "generatedAt": generated_at,
        "count": len(uncovered),
        "surfaces": uncovered,
    }

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    UNCOVERED_PATH.write_text(json.dumps(uncovered_payload, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "registryPath": str(REGISTRY_PATH),
                "uncoveredPath": str(UNCOVERED_PATH),
                "surfaceCount": len(SURFACES),
                "uncoveredCount": len(uncovered),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
