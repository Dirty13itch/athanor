from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "wan2gp-remote-only-watch-latest.json"
TARGET_REPO = "Dirty13itch/Wan2GP"


def _load_wan2gp_entry() -> dict[str, Any]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    github_portfolio = dict(payload.get("github_portfolio") or {})
    for entry in github_portfolio.get("repos", []):
        if isinstance(entry, dict) and str(entry.get("github_repo") or "") == TARGET_REPO:
            return dict(entry)
    raise RuntimeError(f"Unable to find {TARGET_REPO} in github_portfolio")


def main() -> int:
    entry = _load_wan2gp_entry()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "github_repo": TARGET_REPO,
        "url": str(entry.get("url") or ""),
        "ecosystem_role": str(entry.get("ecosystem_role") or ""),
        "likely_tenant_status": str(entry.get("likely_tenant_status") or ""),
        "shaun_decision": str(entry.get("shaun_decision") or ""),
        "has_confirmed_local_clone": bool(entry.get("has_confirmed_local_clone")),
        "working_clone": str(entry.get("working_clone") or ""),
        "current_maturity": str(entry.get("current_maturity") or ""),
        "execution_posture": "watch_remote_only_until_clone_exists",
        "rules": [
            "Do not invent or register a local implementation root for Wan2GP until a real working clone exists.",
            "Keep Wan2GP governed as a remote-only standalone-external repo while no confirmed local clone is present.",
            "If a local clone appears later, add it to reconciliation-source-registry.json and rerun the portfolio sync plus validator.",
        ],
        "completion_condition": [
            "Wan2GP remains explicitly governed as remote-only while no local clone exists.",
            "If a local clone appears, it is registered and classified before any further Athanor reconciliation work depends on it.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
