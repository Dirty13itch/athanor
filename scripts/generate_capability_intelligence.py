from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"

if str(AGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(AGENTS_SRC))

from athanor_agents.capability_intelligence import build_capability_intelligence_snapshot


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Athanor capability-intelligence truth artifacts.",
    )
    parser.add_argument(
        "--write-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "truth-inventory",
        help="Directory that should receive the capability artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.write_dir
    snapshot = build_capability_intelligence_snapshot()

    capability_path = output_dir / "capability-intelligence.json"
    local_endpoint_path = output_dir / "local-endpoint-capability.json"
    refresh_history_path = output_dir / "capability-refresh-history.json"

    local_endpoint_payload = {
        "version": snapshot.get("version", "unknown"),
        "generated_at": snapshot.get("generated_at"),
        "source_of_truth": "reports/truth-inventory/local-endpoint-capability.json",
        "local_endpoints": list(snapshot.get("local_endpoints", [])),
    }
    refresh_history_payload = {
        "version": snapshot.get("version", "unknown"),
        "updated_at": snapshot.get("generated_at"),
        "history": [
            {
                "generated_at": snapshot.get("generated_at"),
                "provider_count": int(snapshot.get("provider_count", len(snapshot.get("providers", [])))),
                "local_endpoint_count": int(
                    snapshot.get("local_endpoint_count", len(snapshot.get("local_endpoints", [])))
                ),
                "degraded_subject_count": len(snapshot.get("degraded_subjects", [])),
            }
        ],
    }

    _write_json(capability_path, snapshot)
    _write_json(local_endpoint_path, local_endpoint_payload)
    _write_json(refresh_history_path, refresh_history_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
