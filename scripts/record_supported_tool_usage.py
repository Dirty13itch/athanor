from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a supported-tool usage proof for a planned subscription family."
    )
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--tool-name", required=True)
    parser.add_argument("--source", default="operator_supported_tool_run")
    parser.add_argument("--request-surface", required=True)
    parser.add_argument("--observed-at", default=utc_now())
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--present-env-contract", action="append", default=[])
    parser.add_argument("--skip-command-check", action="store_true")
    parser.add_argument("--write", type=Path, default=PLANNED_SUBSCRIPTION_EVIDENCE_PATH)
    args = parser.parse_args()

    family = load_planned_subscription(args.family_id)
    provider_id = str(family.get("provider_id") or "").strip()
    provider = load_catalog_provider(provider_id)

    tool_name = str(args.tool_name or "").strip()
    preferred_tools = [
        str(item).strip()
        for item in family.get("preferred_supported_tools", [])
        if str(item).strip()
    ]
    if preferred_tools and tool_name not in preferred_tools:
        raise SystemExit(
            f"Tool {tool_name!r} is not listed as a preferred supported tool for {args.family_id}: {preferred_tools}"
        )

    command_path = shutil.which(tool_name)
    if command_path is None and not args.skip_command_check:
        raise SystemExit(f"Command not found on PATH: {tool_name}")

    required_env_contracts = [
        str(item).strip()
        for item in (family.get("required_env_contracts") or provider.get("env_contracts") or [])
        if str(item).strip()
    ]
    present_env_contracts = [
        str(item).strip()
        for item in args.present_env_contract
        if str(item).strip()
    ] or required_env_contracts

    notes = [str(note).strip() for note in args.note if str(note).strip()]
    if command_path:
        notes.append(f"command_path={command_path}")
    if required_env_contracts and not args.present_env_contract:
        notes.append("present_env_contracts defaulted from required_env_contracts after successful supported-tool execution")

    capture = {
        "family_id": args.family_id,
        "provider_id": provider_id,
        "provider_label": str(provider.get("label") or provider_id),
        "status": "supported_tool_usage_observed",
        "activation_gate": str(family.get("activation_gate") or "").strip() or None,
        "tool_name": tool_name,
        "request_surface": str(args.request_surface or "").strip(),
        "required_commands": [tool_name],
        "available_commands": [tool_name] if command_path or args.skip_command_check else [],
        "required_env_contracts": required_env_contracts,
        "present_env_contracts": present_env_contracts,
        "source": str(args.source or "").strip() or "operator_supported_tool_run",
        "observed_at": args.observed_at,
        "notes": notes,
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
