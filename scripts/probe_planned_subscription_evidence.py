from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from planned_subscription_evidence import (
    append_capture,
    load_catalog_provider,
    load_planned_subscription,
    utc_now,
)
from routing_contract_support import append_history
from truth_inventory import PLANNED_SUBSCRIPTION_EVIDENCE_PATH


def _tooling_probe(provider: dict[str, object]) -> dict[str, object]:
    evidence = dict(provider.get("evidence") or {})
    tooling_probe = dict(evidence.get("tooling_probe") or {})
    supported_commands = [
        str(item).strip()
        for item in tooling_probe.get("supported_commands", [])
        if str(item).strip()
    ]
    available_commands = [command for command in supported_commands if shutil.which(command)]
    env_contracts = [str(item).strip() for item in provider.get("env_contracts", []) if str(item).strip()]
    present_envs = [name for name in env_contracts if os.environ.get(name, "").strip()]
    observed_runtime = dict(provider.get("observed_runtime") or {})
    catalog_api_configured = bool(observed_runtime.get("api_configured"))
    tooling_status = str(tooling_probe.get("status") or "").strip()
    return {
        "required_commands": supported_commands,
        "available_commands": available_commands,
        "required_env_contracts": env_contracts,
        "present_env_contracts": present_envs,
        "catalog_api_configured": catalog_api_configured,
        "tooling_status": tooling_status,
    }


def _status_from_probe(probe: dict[str, object]) -> str:
    available_commands = list(probe.get("available_commands") or [])
    present_envs = list(probe.get("present_env_contracts") or [])
    catalog_api_configured = bool(probe.get("catalog_api_configured"))
    tooling_status = str(probe.get("tooling_status") or "")
    if not available_commands and tooling_status != "supported_tools_present":
        return "missing_tooling"
    if present_envs or catalog_api_configured:
        return "tooling_ready"
    if available_commands or tooling_status == "supported_tools_present":
        return "tooling_present"
    return "activation_blocked"


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe planned-subscription activation readiness.")
    parser.add_argument("--family-id", action="append", default=[], help="Planned subscription family id; can be repeated.")
    parser.add_argument("--write", type=Path, default=PLANNED_SUBSCRIPTION_EVIDENCE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    family_ids = [str(item).strip() for item in args.family_id if str(item).strip()]
    if not family_ids:
        raise SystemExit("No family ids selected. Use --family-id.")

    captures: list[dict[str, object]] = []
    for family_id in sorted(set(family_ids)):
        family = load_planned_subscription(family_id)
        provider_id = str(family.get("provider_id") or "").strip()
        provider = load_catalog_provider(provider_id)
        probe = _tooling_probe(provider)
        status = _status_from_probe(probe)
        capture = {
            "family_id": family_id,
            "provider_id": provider_id,
            "provider_label": str(provider.get("label") or provider_id),
            "status": status,
            "activation_gate": str(family.get("activation_gate") or "").strip() or None,
            "tool_name": None,
            "request_surface": "local command probe + provider-catalog runtime evidence",
            "required_commands": probe["required_commands"],
            "available_commands": probe["available_commands"],
            "required_env_contracts": probe["required_env_contracts"],
            "present_env_contracts": probe["present_env_contracts"],
            "source": "planned-subscription-tooling-probe",
            "observed_at": utc_now(),
            "notes": [
                f"tooling_probe_status={probe['tooling_status'] or 'missing'}",
                f"catalog_api_configured={str(probe['catalog_api_configured']).lower()}",
            ],
        }
        captures.append(capture)
        if not args.dry_run:
            append_capture(capture, path=args.write)
            append_history(
                "planned-subscription-evidence",
                {
                    "generated_at": utc_now(),
                    "source_of_truth": "reports/truth-inventory/planned-subscription-evidence.json",
                    "capture": capture,
                },
            )
        print(json.dumps(capture, indent=2, sort_keys=True))

    statuses = sorted({str(capture.get("status") or "") for capture in captures})
    print(f"Recorded planned-subscription statuses: {statuses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
