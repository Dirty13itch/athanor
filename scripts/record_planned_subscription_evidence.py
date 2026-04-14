from __future__ import annotations

import argparse
from pathlib import Path

from planned_subscription_evidence import (
    ALLOWED_STATUSES,
    append_capture,
    load_catalog_provider,
    load_planned_subscription,
    utc_now,
)
from routing_contract_support import append_history
from truth_inventory import PLANNED_SUBSCRIPTION_EVIDENCE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Record planned-subscription activation evidence.")
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    parser.add_argument("--source", required=True)
    parser.add_argument("--observed-at", default=utc_now())
    parser.add_argument("--tool-name")
    parser.add_argument("--request-surface", default="local evidence record")
    parser.add_argument("--required-command", action="append", default=[])
    parser.add_argument("--available-command", action="append", default=[])
    parser.add_argument("--required-env-contract", action="append", default=[])
    parser.add_argument("--present-env-contract", action="append", default=[])
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--write", type=Path, default=PLANNED_SUBSCRIPTION_EVIDENCE_PATH)
    args = parser.parse_args()

    family = load_planned_subscription(args.family_id)
    provider_id = str(family.get("provider_id") or "").strip()
    provider = load_catalog_provider(provider_id)

    capture = {
        "family_id": args.family_id,
        "provider_id": provider_id,
        "status": args.status,
        "activation_gate": str(family.get("activation_gate") or "").strip() or None,
        "tool_name": str(args.tool_name or "").strip() or None,
        "request_surface": str(args.request_surface or "").strip() or None,
        "required_commands": [str(item).strip() for item in args.required_command if str(item).strip()],
        "available_commands": [str(item).strip() for item in args.available_command if str(item).strip()],
        "required_env_contracts": [str(item).strip() for item in args.required_env_contract if str(item).strip()],
        "present_env_contracts": [str(item).strip() for item in args.present_env_contract if str(item).strip()],
        "source": args.source,
        "observed_at": args.observed_at,
        "notes": [str(note).strip() for note in args.note if str(note).strip()],
        "provider_label": str(provider.get("label") or provider_id),
    }
    append_capture(capture, path=args.write)
    append_history(
        "planned-subscription-evidence",
        {
            "generated_at": utc_now(),
            "source_of_truth": "reports/truth-inventory/planned-subscription-evidence.json",
            "capture": capture,
        },
    )
    print(f"Wrote {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

