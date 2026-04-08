from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from truth_inventory import (
    DASHBOARD_OPERATOR_SURFACES_PATH,
    PROVIDER_USAGE_EVIDENCE_PATH,
    REPO_ROOT,
    REPORT_PATHS,
    TRUTH_SNAPSHOT_PATH,
    VAULT_LITELLM_ENV_AUDIT_PATH,
    VAULT_REDIS_AUDIT_PATH,
    collect_known_drifts,
    load_json,
    load_optional_json,
    list_or_none,
    load_registry,
    render_link_list,
)


def _render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _short_hash(value: str | None) -> str:
    if not value:
        return "unset"
    return f"`{value[:12]}`"


GENERATED_LOCAL_GIT_IGNORE_PATHS = {
    path.relative_to(REPO_ROOT).as_posix()
    for path in [
        *REPORT_PATHS.values(),
        TRUTH_SNAPSHOT_PATH,
        PROVIDER_USAGE_EVIDENCE_PATH,
        VAULT_LITELLM_ENV_AUDIT_PATH,
        VAULT_REDIS_AUDIT_PATH,
        DASHBOARD_OPERATOR_SURFACES_PATH,
    ]
    if path.is_absolute() and REPO_ROOT in path.parents
}


def _status_line_paths(line: str) -> list[str]:
    payload = line[3:].strip()
    if not payload:
        return []
    if " -> " in payload:
        return [part.strip().replace("\\", "/") for part in payload.split(" -> ") if part.strip()]
    return [payload.replace("\\", "/")]


def _local_git_probe(path: str) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", path, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "-C", path, "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    status_lines = [line.rstrip() for line in status.stdout.splitlines() if line.strip()] if status.returncode == 0 else []
    try:
        probe_root = Path(path).resolve()
    except OSError:
        probe_root = None
    if probe_root == REPO_ROOT.resolve():
        status_lines = [
            line
            for line in status_lines
            if not (
                (paths := _status_line_paths(line))
                and all(candidate in GENERATED_LOCAL_GIT_IGNORE_PATHS for candidate in paths)
            )
        ]
    return {
        "head": head.stdout.strip() if head.returncode == 0 else "",
        "dirty_count": len(status_lines),
        "status_sample": status_lines[:10],
    }


def _fenced_block(language: str, lines: list[str]) -> list[str]:
    return [f"```{language}", *lines, "```"]


VOLATILE_REPORT_LINE_PREFIXES: dict[str, tuple[str, ...]] = {
    "providers": (
        "- Runtime env audit: missing ",
    ),
    "operator_surfaces": (
        "- Cached truth snapshot: `",
        "- Dashboard container status: `",
    ),
    "runtime_migrations": (
        "- Latest live content evidence snapshot: `",
        "- Live content evidence snapshot: `",
    ),
    "runtime_ownership": (
        "- Cached truth snapshot: `",
    ),
    "runtime_ownership_packets": (
        "- Cached truth snapshot: `",
    ),
    "runtime_cutover": (
        "- Cached truth snapshot: `",
    ),
    "vault_litellm_repair_packet": (
        "- Cached truth snapshot: `",
        "- Cached env audit: `",
    ),
    "vault_redis_repair_packet": (
        "- Cached truth snapshot: `",
        "- Cached redis audit: `",
        "- Latest temp-RDB no-space error: `",
        "- Latest background-save error: `",
        "- Latest cross-protocol warning: `",
        "- Temp-RDB no-space error count in audit tail: `",
        "- Background-save error count in audit tail: `",
        "- Cross-protocol warning count in audit tail: `",
        "- Redis data directory size: `",
        "- Filesystem size: `",
        "- Filesystem used: `",
        "- Filesystem available: `",
        "- Filesystem used percent: `",
        "- Btrfs device allocated: `",
        "- Btrfs device unallocated: `",
        "- Btrfs free estimate: `",
        "- `/mnt/appdatacache",
    ),
    "secret_surfaces": (
        "- VAULT LiteLLM env audit: `",
        "- Latest live env audit: `",
    ),
}


def _slash_path(value: str | None) -> str:
    if not value:
        return ""
    return str(value).replace("\\", "/")


def _vault_container_launch_command(vault_litellm_env_audit: dict[str, Any]) -> str:
    parts = [
        *[
            str(item).strip()
            for item in vault_litellm_env_audit.get("container_entrypoint", [])
            if str(item).strip()
        ],
        *[
            str(item).strip()
            for item in vault_litellm_env_audit.get("container_args", [])
            if str(item).strip()
        ],
    ]
    return " ".join(parts)


def _load_latest_truth_snapshot() -> dict[str, Any] | None:
    if not TRUTH_SNAPSHOT_PATH.exists():
        return None
    try:
        return load_json(TRUTH_SNAPSHOT_PATH)
    except Exception:
        return None


def _surface_node_label(node_id: str) -> str:
    return {
        "dev": "DEV",
        "vault": "VAULT",
        "workshop": "Workshop",
        "foundry": "Foundry",
    }.get(node_id, node_id.upper())


def _surface_category(operator_role: str) -> str:
    return {
        "observability": "monitoring",
        "chat": "ai",
        "knowledge": "knowledge",
        "home": "home",
        "creative": "creative",
        "media": "media",
        "domain_product": "project",
        "command_center": "portal",
    }.get(operator_role, "tool")


def _surface_description(surface: dict[str, Any]) -> str:
    operator_role = str(surface.get("operator_role") or "").strip()
    label = str(surface.get("label") or surface.get("id") or "Surface").strip()
    node_label = _surface_node_label(str(surface.get("node") or "").strip())
    notes = [str(note).strip() for note in surface.get("notes", []) if str(note).strip()]
    if notes:
        return notes[0]
    role_descriptions = {
        "observability": "Observability drill-down and metrics analysis.",
        "chat": "Direct chat surface outside the command center.",
        "knowledge": "Knowledge and memory specialist surface.",
        "home": "Home automation and state surface.",
        "creative": "Creative generation and workflow surface.",
        "media": "Media operations and library surface.",
        "domain_product": "First-class domain product outside the core portal.",
        "command_center": "Canonical operator front door.",
    }
    base = role_descriptions.get(operator_role)
    if base:
        return f"{base} Hosted on {node_label} as {label}."
    return f"{label} on {node_label}."


def _root_path_by_id(registry: dict[str, Any], root_id: str) -> str:
    for root in registry.get("roots", []):
        if str(root.get("id") or "") == root_id:
            return str(root.get("path") or "")
    return ""


def _load_vault_litellm_env_audit(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(snapshot, dict):
        embedded = snapshot.get("vault_litellm_env_audit")
        if isinstance(embedded, dict) and embedded:
            return embedded
    if VAULT_LITELLM_ENV_AUDIT_PATH.exists():
        try:
            return load_json(VAULT_LITELLM_ENV_AUDIT_PATH)
        except Exception:
            return {}
    return {}


def _load_vault_redis_audit(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(snapshot, dict):
        embedded = snapshot.get("vault_redis_audit")
        if isinstance(embedded, dict) and embedded:
            return embedded
    if VAULT_REDIS_AUDIT_PATH.exists():
        try:
            return load_json(VAULT_REDIS_AUDIT_PATH)
        except Exception:
            return {}
    return {}


def _format_bytes(value: Any) -> str:
    if not isinstance(value, int) or value < 0:
        return "unknown"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(value)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if amount < 1024.0 or candidate == units[-1]:
            break
        amount /= 1024.0
    if unit == "B":
        return f"{int(amount)} {unit}"
    return f"{amount:.2f} {unit}"


def _render_size_rankings(entries: list[dict[str, Any]], *, empty_text: str) -> list[str]:
    if not entries:
        return [f"- {empty_text}"]
    lines: list[str] = []
    for entry in entries:
        path = str(entry.get("path") or "").strip()
        size_bytes = entry.get("size_bytes")
        if not path:
            continue
        lines.append(f"- `{path}`: `{_format_bytes(size_bytes)}`")
    return lines or [f"- {empty_text}"]


def _snapshot_governor_facade(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    dev_runtime_probe = snapshot.get("dev_runtime_probe")
    if not isinstance(dev_runtime_probe, dict):
        return {}
    detail = dev_runtime_probe.get("detail")
    if not isinstance(detail, dict):
        return {}
    governor_facade = detail.get("governor_facade")
    return governor_facade if isinstance(governor_facade, dict) else {}


def _normalize_report_for_check(report_id: str, text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    volatile_prefixes = VOLATILE_REPORT_LINE_PREFIXES.get(report_id)
    if not volatile_prefixes:
        return normalized
    lines = normalized.split("\n")
    for index, line in enumerate(lines):
        for prefix in volatile_prefixes:
            if line.startswith(prefix) and line.endswith("`"):
                lines[index] = f"{prefix}<volatile>`"
                break
    return "\n".join(lines)


def _report_is_stale(report_id: str, *, existing: str, rendered: str) -> bool:
    return _normalize_report_for_check(report_id, existing) != _normalize_report_for_check(report_id, rendered)


def _tooling_provider_index(tooling: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    indexed: dict[str, list[dict[str, str]]] = {}
    for host in tooling.get("hosts", []):
        host_id = str(host.get("id") or host.get("host") or "unknown")
        for tool in host.get("tools", []):
            provider_id = str(tool.get("provider_id") or "").strip()
            if not provider_id:
                continue
            indexed.setdefault(provider_id, []).append(
                {
                    "host": host_id,
                    "tool_id": str(tool.get("tool_id") or tool.get("command") or "unknown"),
                    "status": str(tool.get("status") or "unknown"),
                    "version": str(tool.get("version") or ""),
                }
            )
    return indexed


def _tooling_summary(entries: list[dict[str, str]]) -> str:
    if not entries:
        return "none"
    parts = []
    for entry in entries:
        version = f" {entry['version']}" if entry.get("version") else ""
        parts.append(f"`{entry['host']}:{entry['tool_id']}:{entry['status']}{version}`")
    return ", ".join(parts)


def _credential_env_names(credential_surfaces: dict[str, Any]) -> set[str]:
    return {
        str(env_name)
        for surface in credential_surfaces.get("surfaces", [])
        for env_name in surface.get("env_var_names", [])
        if str(env_name).strip()
    }


def _provider_evidence_posture(
    provider: dict[str, Any],
    *,
    tooling_entries: list[dict[str, str]],
    credential_env_names: set[str],
    provider_usage_capture: dict[str, Any] | None = None,
) -> str:
    observed_runtime = dict(provider.get("observed_runtime") or {})
    evidence = dict(provider.get("evidence") or {})
    access_mode = str(provider.get("access_mode") or "")
    active_burn_observed = bool(observed_runtime.get("active_burn_observed"))
    routing_policy_enabled = bool(observed_runtime.get("routing_policy_enabled"))
    api_configured = bool(observed_runtime.get("api_configured"))
    observed_hosts = [str(host) for host in provider.get("observed_hosts", []) if str(host).strip()]
    pricing_status = str(provider.get("official_pricing_status") or "")
    monthly_cost_usd = provider.get("monthly_cost_usd")
    evidence_kind = str(evidence.get("kind") or "")
    cli_probe = dict(evidence.get("cli_probe") or {})
    tooling_probe = dict(evidence.get("tooling_probe") or {})
    billing = dict(evidence.get("billing") or {})
    proxy_evidence = dict(evidence.get("proxy") or {})
    provider_specific_usage = dict(evidence.get("provider_specific_usage") or {})
    provider_usage_capture = dict(provider_usage_capture or {})
    cli_probe_status = str(cli_probe.get("status") or "")
    billing_status = str(billing.get("status") or "")
    provider_specific_status = str(provider_specific_usage.get("status") or "")
    capture_status = str(provider_usage_capture.get("status") or "")
    installed_tools = [entry for entry in tooling_entries if entry.get("status") == "installed"]
    degraded_tools = [entry for entry in tooling_entries if entry.get("status") == "degraded"]
    provider_envs = {str(item) for item in provider.get("env_contracts", []) if str(item).strip()}
    credential_surface_present = bool(provider_envs & credential_env_names)
    execution_modes = {str(item) for item in provider.get("execution_modes", []) if str(item).strip()}
    proxy_activity_observed = bool(observed_runtime.get("proxy_activity_observed"))
    provider_specific_usage_observed = bool(observed_runtime.get("provider_specific_usage_observed"))

    if evidence_kind == "coding_tool_subscription":
        integration_status = str(tooling_probe.get("integration_status") or evidence.get("integration_status") or "")
        if integration_status in {"verified", "observed"}:
            return "tool_installed_no_recent_burn"
        return "supported_tool_subscription_unverified"
    if access_mode == "local" and routing_policy_enabled:
        return "local_runtime_available"
    if active_burn_observed:
        if monthly_cost_usd is None and (
            "cost-unverified" in pricing_status
            or billing_status in {"operator_visible_tier_unverified", "published_tiers_known_subscribed_tier_unverified"}
        ):
            return "live_burn_observed_cost_unverified"
        return "live_burn_observed"
    if routing_policy_enabled and installed_tools:
        return "routing_enabled_cli_ready"
    if routing_policy_enabled and evidence_kind == "cli_subscription" and cli_probe_status == "installed":
        return "routing_enabled_cli_ready"
    if access_mode == "cli" and routing_policy_enabled:
        return "routing_enabled_without_observed_tool"
    if access_mode == "cli" and installed_tools:
        return "tool_installed_no_recent_burn"
    if access_mode == "cli" and evidence_kind == "cli_subscription" and cli_probe_status == "installed":
        return "tool_installed_no_recent_burn"
    if access_mode == "cli" and degraded_tools:
        return "tool_degraded_no_recent_burn"
    if access_mode == "cli" and evidence_kind == "cli_subscription" and cli_probe_status == "degraded":
        return "tool_degraded_no_recent_burn"
    if access_mode == "cli" and credential_surface_present:
        return "cli_configured_without_observed_tool"
    if (
        access_mode == "api"
        and api_configured
        and "litellm_proxy" in execution_modes
        and "vault" in {host.lower() for host in observed_hosts}
    ):
        if (
            provider_specific_usage_observed
            or provider_specific_status in {"observed", "verified"}
            or capture_status in {"observed", "verified"}
        ):
            return "vault_provider_specific_api_observed"
        if capture_status == "auth_failed":
            return "vault_provider_specific_auth_failed"
        if capture_status == "request_failed":
            return "vault_provider_specific_request_failed"
        if capture_status == "not_supported":
            return "vault_provider_specific_not_supported"
        if proxy_activity_observed or str(proxy_evidence.get("last_verified_at") or "").strip():
            return "vault_proxy_active_no_provider_specific_evidence"
        return "vault_litellm_configured_no_recent_proxy_activity"
    if access_mode == "api" and api_configured and "litellm_proxy" in execution_modes and credential_surface_present:
        return "litellm_proxy_configured_no_recent_burn"
    if access_mode == "api" and api_configured and "litellm_proxy" in execution_modes:
        return "litellm_proxy_configured_no_credential_surface"
    if api_configured and credential_surface_present:
        return "api_configured_no_recent_burn"
    if api_configured:
        return "api_configured_no_credential_surface"
    if credential_surface_present:
        return "credential_surface_present_no_runtime_observation"
    return "catalog_only"


def _provider_pricing_truth_label(provider: dict[str, Any]) -> str:
    pricing_status = str(provider.get("official_pricing_status") or "")
    monthly_cost_usd = provider.get("monthly_cost_usd")
    if pricing_status == "not_applicable":
        return "not_applicable"
    if pricing_status == "metered":
        return "metered_api"
    if pricing_status == "official_verified" and monthly_cost_usd is not None:
        return "verified_flat_rate"
    if pricing_status == "official-source-present-cost-unverified":
        return "flat_rate_unverified"
    if monthly_cost_usd is None:
        return "unverified_or_metered"
    return pricing_status or "unknown"


def _provider_evidence_summary(provider: dict[str, Any], provider_usage_capture: dict[str, Any] | None = None) -> str:
    evidence = dict(provider.get("evidence") or {})
    if not evidence:
        return "none"
    kind = str(evidence.get("kind") or "unknown")
    parts = [f"`kind={kind}`"]
    provider_usage_capture = dict(provider_usage_capture or {})
    if kind == "coding_tool_subscription":
        billing = dict(evidence.get("billing") or {})
        tooling_probe = dict(evidence.get("tooling_probe") or {})
        tooling_status = str(tooling_probe.get("status") or evidence.get("tooling_status") or "")
        expected_hosts = [
            str(host)
            for host in tooling_probe.get("expected_hosts", []) or evidence.get("expected_hosts", [])
            if str(host).strip()
        ]
        supported_tools = [
            str(tool)
            for tool in tooling_probe.get("supported_commands", []) or evidence.get("supported_tools", [])
            if str(tool).strip()
        ]
        integration_status = str(tooling_probe.get("integration_status") or evidence.get("integration_status") or "")
        if tooling_status:
            parts.append(f"`tooling_status={tooling_status}`")
        if expected_hosts:
            parts.append(f"`hosts={','.join(expected_hosts)}`")
        if supported_tools:
            parts.append(f"`supported_tools={','.join(supported_tools)}`")
        if integration_status:
            parts.append(f"`integration_status={integration_status}`")
        billing_status = str(billing.get("status") or "")
        if billing_status:
            parts.append(f"`billing_status={billing_status}`")
        public_plan_prices = dict(billing.get("public_plan_prices_usd") or {})
        if public_plan_prices:
            rendered_prices = ",".join(
                f"{plan}:{price}"
                for plan, price in sorted((str(plan), price) for plan, price in public_plan_prices.items())
            )
            parts.append(f"`public_prices={rendered_prices}`")
    elif kind == "cli_subscription":
        cli_probe = dict(evidence.get("cli_probe") or {})
        billing = dict(evidence.get("billing") or {})
        cli_status = str(cli_probe.get("status") or "")
        if cli_status:
            parts.append(f"`cli_status={cli_status}`")
        expected_hosts = [str(host) for host in cli_probe.get("expected_hosts", []) if str(host).strip()]
        if expected_hosts:
            parts.append(f"`hosts={','.join(expected_hosts)}`")
        required_commands = [str(command) for command in cli_probe.get("required_commands", []) if str(command).strip()]
        if required_commands:
            parts.append(f"`commands={','.join(required_commands)}`")
        billing_status = str(billing.get("status") or "")
        if billing_status:
            parts.append(f"`billing_status={billing_status}`")
        pricing_scope = str(billing.get("pricing_scope") or "")
        if pricing_scope:
            parts.append(f"`pricing_scope={pricing_scope}`")
        quota_refresh_cycle = str(billing.get("quota_refresh_cycle") or "")
        if quota_refresh_cycle:
            parts.append(f"`quota_cycle={quota_refresh_cycle}`")
        public_plan_prices = dict(billing.get("public_plan_prices_usd") or {})
        if public_plan_prices:
            rendered_prices = ",".join(
                f"{plan}:{price}"
                for plan, price in sorted((str(plan), price) for plan, price in public_plan_prices.items())
            )
            parts.append(f"`public_prices={rendered_prices}`")
    elif kind == "vault_litellm_proxy":
        proxy = dict(evidence.get("proxy") or {})
        provider_specific_usage = dict(evidence.get("provider_specific_usage") or {})
        alias = str(proxy.get("alias") or "")
        host = str(proxy.get("host") or "")
        preferred_models = [str(model).strip() for model in proxy.get("preferred_models", []) if str(model).strip()]
        provider_specific_status = str(provider_specific_usage.get("status") or "")
        capture_status = str(provider_usage_capture.get("status") or "")
        capture_observed_at = str(provider_usage_capture.get("observed_at") or "")
        requested_model = str(provider_usage_capture.get("requested_model") or "")
        response_model = str(provider_usage_capture.get("response_model") or "")
        matched_by = str(provider_usage_capture.get("matched_by") or "")
        if alias:
            parts.append(f"`alias={alias}`")
        if host:
            parts.append(f"`host={host}`")
        if preferred_models:
            parts.append(f"`preferred_model={preferred_models[0]}`")
        if provider_specific_status:
            parts.append(f"`provider_specific_status={provider_specific_status}`")
        if capture_status:
            parts.append(f"`capture_status={capture_status}`")
        if capture_observed_at:
            parts.append(f"`captured_at={capture_observed_at}`")
        if requested_model:
            parts.append(f"`requested_model={requested_model}`")
        if response_model:
            parts.append(f"`response_model={response_model}`")
        if matched_by:
            parts.append(f"`matched_by={matched_by}`")
    return ", ".join(parts)


def _provider_verification_steps(
    provider: dict[str, Any],
    evidence_posture: str,
    provider_usage_capture: dict[str, Any] | None = None,
    vault_litellm_env_audit: dict[str, Any] | None = None,
) -> list[str]:
    explicit_steps = [str(step).strip() for step in provider.get("verification_steps", []) if str(step).strip()]
    provider_usage_capture = dict(provider_usage_capture or {})
    evidence = dict(provider.get("evidence") or {})
    cli_probe = dict(evidence.get("cli_probe") or {})
    cli_probe_status = str(cli_probe.get("status") or "")
    if evidence_posture == "vault_provider_specific_api_observed" and provider_usage_capture:
        return ["No immediate verification gap recorded."]
    provider_label = str(provider.get("label") or provider.get("id") or "provider")
    cli_commands = [str(command).strip() for command in provider.get("cli_commands", []) if str(command).strip()]
    observed_hosts = [str(host).strip() for host in provider.get("observed_hosts", []) if str(host).strip()]
    litellm_aliases = [str(alias).strip() for alias in provider.get("litellm_aliases", []) if str(alias).strip()]
    host_summary = " and ".join(observed_hosts) if observed_hosts else "the expected host"
    cli_summary = " or ".join(f"`{command} --version`" for command in cli_commands) if cli_commands else "the expected CLI"
    alias = litellm_aliases[0] if litellm_aliases else provider_label.lower().replace(" ", "_")
    if evidence_posture == "vault_provider_specific_auth_failed":
        classification = _classify_vault_auth_failure(
            provider,
            provider_usage_capture,
            dict(vault_litellm_env_audit or {}),
        )
        requested_model = str(provider_usage_capture.get("requested_model") or alias)
        missing_names = _vault_env_names_for_provider(
            provider,
            dict(vault_litellm_env_audit or {}),
            "container_missing_env_names",
        )
        missing_suffix = f" Missing env names: {list_or_none(missing_names)}." if missing_names else ""
        if classification["code"] != "auth_mode_mismatch":
            return [
                f"Use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) to repair `{provider_label}` on VAULT, then re-probe served model `{requested_model}`.{missing_suffix}",
                "Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.",
            ]
        return [
            classification["next_action"],
            "Do not treat this lane as provider-specifically proven until the auth failure is gone and a successful completion is recorded.",
        ]
    if evidence_posture == "vault_provider_specific_request_failed":
        requested_model = str(provider_usage_capture.get("requested_model") or alias)
        return [
            f"Debug the failed provider-specific VAULT LiteLLM request for served model `{requested_model}`.",
            "Capture one successful completion or demote the lane to configured-only if the request path is not actually usable.",
        ]
    if evidence_posture == "vault_provider_specific_not_supported":
        return [
            f"Update the provider evidence contract for `{provider_label}` to match a currently served LiteLLM model id, or demote the lane.",
            "Do not mark this lane active-api until a provider-specific served model is actually callable.",
        ]
    if explicit_steps:
        if evidence_posture in {
            "vault_proxy_active_no_provider_specific_evidence",
        }:
            provider_id = str(provider.get("id") or provider.get("label") or "provider")
            alias = str((dict(provider.get("evidence") or {}).get("proxy") or {}).get("alias") or provider_id)
            capture_command = f"python scripts/probe_provider_usage_evidence.py --provider-id {provider_id}"
            explicit_steps[0] = (
                f"{explicit_steps[0]} Current probe alias: `{alias}`. "
                f"Then record or refresh the proof with `{capture_command}`."
            )
        return explicit_steps

    if evidence_posture == "live_burn_observed_cost_unverified":
        steps = [
            f"Verify the subscribed monthly tier or billing surface for `{provider_label}` from a current operator-visible source.",
            "Keep this lane cost-unverified until the billing tier is proven from a current runtime-visible or operator-visible surface.",
        ]
        if cli_probe_status != "installed":
            steps.insert(1, f"Confirm a working {cli_summary} result on {host_summary}.")
        return steps
    if evidence_posture == "routing_enabled_without_observed_tool":
        return [
            f"Restore or verify {cli_summary} on {host_summary}.",
            f"Do not leave `{provider_label}` in live routing unless tool evidence exists again.",
        ]
    if evidence_posture == "cli_configured_without_observed_tool":
        return [
            f"Restore or verify {cli_summary} on {host_summary} before promoting `{provider_label}` back into live routing.",
            "If the CLI cannot be restored, keep this lane configured-unused and out of ordinary auto-routing.",
        ]
    if evidence_posture == "supported_tool_subscription_unverified":
        return [
            f"Verify {provider_label} execution through a supported coding tool on DESK or DEV before promoting `{provider_label}` back into live routing.",
            f"Verify which public {provider.get('subscription_product') or provider_label} tier is actually subscribed before treating any published USD price as this lane's monthly cost.",
            "Until supported-tool integration is proven, keep this lane configured-unused and out of ordinary auto-routing.",
        ]
    if evidence_posture == "vault_provider_specific_api_observed":
        return ["No immediate verification gap recorded."]
    if evidence_posture == "vault_proxy_active_no_provider_specific_evidence":
        return [
            f"Run a provider-specific request through the VAULT LiteLLM served model `{alias}` and record the timestamp.",
            f"Capture evidence that the request exercised `{provider_label}` upstream specifically, not just generic proxy activity.",
            "If provider-specific evidence cannot be captured, demote the lane to configured-only.",
        ]
    if evidence_posture == "vault_litellm_configured_no_recent_proxy_activity":
        return [
            f"Verify the VAULT LiteLLM alias `{alias}` is still configured and reachable.",
            "Capture recent successful proxy traffic before treating the lane as active-api.",
        ]
    if evidence_posture == "litellm_proxy_configured_no_recent_burn":
        return [f"Verify the LiteLLM proxy path for `{provider_label}` and capture a recent successful request."]
    if evidence_posture == "litellm_proxy_configured_no_credential_surface":
        return [f"Confirm the expected LiteLLM credential env contract for `{provider_label}` on the proxy host."]
    if evidence_posture == "api_configured_no_recent_burn":
        return [f"Capture a recent successful API request for `{provider_label}` or demote the lane to configured-only."]
    if evidence_posture == "api_configured_no_credential_surface":
        return [f"Confirm the expected credential env contract for `{provider_label}`."]
    if evidence_posture == "tool_installed_no_recent_burn":
        return [f"Capture a recent successful `{provider_label}` CLI execution or demote the lane to configured-only."]
    if evidence_posture == "tool_degraded_no_recent_burn":
        return [f"Repair the degraded `{provider_label}` CLI installation and capture a successful run."]
    if evidence_posture == "credential_surface_present_no_runtime_observation":
        return [f"Verify the runtime surface that should consume `{provider_label}` credentials."]
    if evidence_posture == "catalog_only":
        return [f"Either add runtime evidence for `{provider_label}` or demote it to historical/reference status."]
    return ["No immediate verification gap recorded."]


def _provider_next_verification(
    provider: dict[str, Any],
    evidence_posture: str,
    provider_usage_capture: dict[str, Any] | None = None,
    vault_litellm_env_audit: dict[str, Any] | None = None,
) -> str:
    return _provider_verification_steps(provider, evidence_posture, provider_usage_capture, vault_litellm_env_audit)[0]


def _provider_verification_priority(evidence_posture: str, pricing_truth_label: str) -> int:
    if evidence_posture == "live_burn_observed_cost_unverified":
        return 0
    if evidence_posture == "cli_configured_without_observed_tool":
        return 1
    if evidence_posture == "supported_tool_subscription_unverified":
        return 1
    if evidence_posture == "routing_enabled_without_observed_tool":
        return 2
    if evidence_posture == "vault_proxy_active_no_provider_specific_evidence":
        return 3
    if evidence_posture in {"vault_provider_specific_auth_failed", "vault_provider_specific_request_failed"}:
        return 2
    if evidence_posture == "vault_provider_specific_not_supported":
        return 3
    if evidence_posture in {
        "vault_litellm_configured_no_recent_proxy_activity",
        "litellm_proxy_configured_no_recent_burn",
        "api_configured_no_recent_burn",
    }:
        return 4
    if pricing_truth_label == "flat_rate_unverified":
        return 5
    if evidence_posture in {
        "tool_installed_no_recent_burn",
        "tool_degraded_no_recent_burn",
        "credential_surface_present_no_runtime_observation",
        "catalog_only",
        "api_configured_no_credential_surface",
        "litellm_proxy_configured_no_credential_surface",
    }:
        return 6
    return 99


def _observed_runtime_summary(observed_runtime: dict[str, Any], provider_usage_capture: dict[str, Any] | None = None) -> str:
    ordered_keys = [
        "routing_policy_enabled",
        "active_burn_observed",
        "api_configured",
        "proxy_activity_observed",
        "provider_specific_usage_observed",
        "last_verified_at",
    ]
    parts: list[str] = []
    for key in ordered_keys:
        if key not in observed_runtime:
            continue
        parts.append(f"`{key}={observed_runtime.get(key)}`")
    for key in sorted(observed_runtime):
        if key in ordered_keys:
            continue
        parts.append(f"`{key}={observed_runtime.get(key)}`")
    provider_usage_capture = dict(provider_usage_capture or {})
    capture_status = str(provider_usage_capture.get("status") or "")
    capture_observed_at = str(provider_usage_capture.get("observed_at") or "")
    capture_source = str(provider_usage_capture.get("source") or "")
    if capture_status:
        parts.append(f"`provider_usage_capture_status={capture_status}`")
    if capture_observed_at:
        parts.append(f"`provider_usage_capture_at={capture_observed_at}`")
    if capture_source:
        parts.append(f"`provider_usage_capture_source={capture_source}`")
    return ", ".join(parts) if parts else "none"


def _provider_usage_capture_index(evidence_document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    captures = evidence_document.get("captures", [])
    if not isinstance(captures, list):
        return {}
    latest_by_provider: dict[str, dict[str, Any]] = {}
    for capture in captures:
        if not isinstance(capture, dict):
            continue
        provider_id = str(capture.get("provider_id") or "").strip()
        observed_at = str(capture.get("observed_at") or "").strip()
        if not provider_id or not observed_at:
            continue
        current = latest_by_provider.get(provider_id)
        current_observed_at = str((current or {}).get("observed_at") or "")
        if not current or observed_at >= current_observed_at:
            latest_by_provider[provider_id] = dict(capture)
    return latest_by_provider


def _vault_env_names_for_provider(provider: dict[str, Any], audit: dict[str, Any], field_name: str) -> list[str]:
    provider_envs = {
        str(name).strip()
        for name in provider.get("env_contracts", [])
        if str(name).strip()
    }
    if not provider_envs:
        return []
    return sorted(
        str(name).strip()
        for name in audit.get(field_name, [])
        if str(name).strip() and str(name).strip() in provider_envs
    )


def _classify_vault_auth_failure(
    provider: dict[str, Any],
    capture: dict[str, Any] | None,
    audit: dict[str, Any] | None,
) -> dict[str, str]:
    capture = dict(capture or {})
    audit = dict(audit or {})
    provider_label = str(provider.get("label") or provider.get("id") or "provider")
    requested_model = str(
        capture.get("requested_model")
        or (dict(dict(provider.get("evidence") or {}).get("proxy") or {}).get("alias") or provider_label)
    )
    error_snippet = str(capture.get("error_snippet") or "").strip()
    lowered_error = error_snippet.lower()
    missing_names = _vault_env_names_for_provider(provider, audit, "container_missing_env_names")
    present_names = _vault_env_names_for_provider(provider, audit, "container_present_env_names")
    required_envs = sorted(
        {
            str(rule.get("name") or "").strip()
            for rule in dict(provider.get("vault_runtime_contract") or {}).get("env_rules", [])
            if str(rule.get("name") or "").strip() and str(rule.get("role") or "").strip() == "required"
        }
    )
    if not missing_names and required_envs:
        missing_names = [name for name in required_envs if name not in present_names]
    if not present_names and required_envs:
        present_names = [name for name in required_envs if name not in missing_names]

    if "cookie auth" in lowered_error:
        env_names = missing_names or required_envs or list(present_names)
        env_suffix = f" Ensure {list_or_none(env_names)} is delivered to `litellm`." if env_names else ""
        return {
            "code": "auth_mode_mismatch",
            "next_action": (
                f"Verify the upstream auth mode for served model `{requested_model}` before re-probing `{provider_label}`."
                f"{env_suffix}"
            ),
        }
    if missing_names and any(
        marker in lowered_error
        for marker in (
            "missing",
            "no key is set",
            "api key",
            "auth token",
        )
    ):
        return {
            "code": "missing_required_env",
            "next_action": (
                f"Restore {list_or_none(missing_names)} in the managed VAULT secret source, recreate or redeploy `litellm`, "
                f"then re-probe served model `{requested_model}`."
            ),
        }
    if present_names and any(
        marker in lowered_error
        for marker in (
            "incorrect api key",
            "invalid api key",
            "authenticationerror",
            "unauthorized",
            "invalid x-api-key",
        )
    ):
        return {
            "code": "present_key_invalid",
            "next_action": (
                f"Rotate {list_or_none(present_names)} in the managed VAULT secret source, recreate or redeploy `litellm`, "
                f"then re-probe served model `{requested_model}`."
            ),
        }
    env_names = missing_names or present_names or required_envs
    env_suffix = f" Check {list_or_none(env_names)} while reconciling the auth path." if env_names else ""
    return {
        "code": "auth_failed_unknown",
        "next_action": f"Inspect the latest auth failure for served model `{requested_model}` and reconcile `{provider_label}` on VAULT.{env_suffix}",
    }


def render_hardware_report() -> str:
    inventory = load_registry("hardware-inventory.json")
    nodes = list(inventory.get("nodes", []))
    rows: list[list[str]] = []
    for node in nodes:
        gpu_summary = ", ".join(
            f"{gpu.get('model')} ({gpu.get('vram_gb')} GB)"
            for gpu in node.get("gpus", [])
            if gpu.get("model")
        )
        storage_summary = ", ".join(
            (
                f"{entry.get('count')} x {entry.get('size_tb_each')} TB {entry.get('kind')}"
                if entry.get("count") and entry.get("size_tb_each")
                else f"{entry.get('size_tb', entry.get('raw_tb', '?'))} TB {entry.get('kind')}"
            )
            for entry in node.get("storage", [])
        )
        link_summary = ", ".join(
            f"{link.get('speed_gbps')} Gbps {link.get('interface')}" for link in node.get("network_links", [])
        )
        rows.append(
            [
                f"`{node.get('id')}`",
                str(node.get("host") or ""),
                str(node.get("role") or ""),
                str(node.get("cpu", {}).get("model") or ""),
                f"{node.get('ram_gb')} GB",
                gpu_summary or "none",
                storage_summary or "unknown",
                link_summary or "unknown",
            ]
        )

    lines = [
        "# Hardware Report",
        "",
        "Generated from `config/automation-backbone/hardware-inventory.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{inventory.get('version', 'unknown')}`",
        f"- Nodes tracked: `{len(nodes)}`",
        "",
        *_render_table(
            ["Node", "Host", "Role", "CPU", "RAM", "GPUs", "Storage", "Links"],
            rows,
        ),
    ]
    for node in nodes:
        lines.extend(
            [
                "",
                f"## {node.get('host')} (`{node.get('id')}`)",
                "",
                f"- Role: {node.get('role')}",
                f"- Last verified: `{node.get('last_verified_at')}`",
                f"- Evidence sources: {list_or_none(list(node.get('evidence_sources', [])))}",
                f"- Notes: {list_or_none(list(node.get('notes', [])))}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_model_report() -> str:
    registry = load_registry("model-deployment-registry.json")
    lanes = list(registry.get("lanes", []))
    artifacts = list(registry.get("artifacts", []))
    lines = [
        "# Model Deployment Report",
        "",
        "Generated from `config/automation-backbone/model-deployment-registry.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Deployment lanes tracked: `{len(lanes)}`",
        f"- Stored artifacts tracked: `{len(artifacts)}`",
        "",
        *_render_table(
            ["Lane", "Service", "Node", "State", "Expected", "Observed", "Drift"],
            [
                [
                    f"`{lane.get('id')}`",
                    f"`{lane.get('service_id')}`",
                    f"`{lane.get('node_id')}`",
                    f"`{lane.get('state_class')}`",
                    f"`{lane.get('expected_model_id')}`" if lane.get("expected_model_id") else "unset",
                    f"`{lane.get('observed_model_id')}`" if lane.get("observed_model_id") else "unset",
                    f"`{lane.get('drift_status')}`",
                ]
                for lane in lanes
            ],
        ),
        "",
        "## Stored Model Artifacts",
        "",
        *_render_table(
            ["Artifact", "Node", "State", "Verified", "Evidence"],
            [
                [
                    f"`{item.get('model_id')}`",
                    f"`{item.get('node_id')}`",
                    f"`{item.get('state_class')}`",
                    f"`{item.get('verified_at')}`",
                    str(item.get("evidence_source") or ""),
                ]
                for item in artifacts
            ],
        ),
    ]
    active_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "active") == "active"
    ]
    retired_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "") == "retired"
    ]
    if active_drifts:
        lines.extend(["", "## Known Drift", ""])
        for drift in active_drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    if retired_drifts:
        lines.extend(["", "## Retired Drift", ""])
        for drift in retired_drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    lines.append("")
    return "\n".join(lines)


def render_provider_report() -> str:
    catalog = load_registry("provider-catalog.json")
    burn_registry = load_registry("subscription-burn-registry.json")
    tooling = load_registry("tooling-inventory.json")
    credential_surfaces = load_registry("credential-surface-registry.json")
    provider_usage_evidence = load_optional_json(PROVIDER_USAGE_EVIDENCE_PATH)
    latest_snapshot = _load_latest_truth_snapshot()
    vault_litellm_env_audit = _load_vault_litellm_env_audit(latest_snapshot)
    provider_usage_capture_index = _provider_usage_capture_index(provider_usage_evidence)
    providers = list(catalog.get("providers", []))
    burn_subscriptions = [dict(entry) for entry in burn_registry.get("subscriptions", []) if isinstance(entry, dict)]
    burn_windows = [dict(entry) for entry in burn_registry.get("windows", []) if isinstance(entry, dict)]
    burn_by_provider: dict[str, list[dict[str, Any]]] = {}
    window_labels_by_subscription: dict[str, list[str]] = {}
    for window in burn_windows:
        label = str(window.get("label") or window.get("id") or "unknown")
        for subscription_id in [str(item) for item in window.get("subscriptions", []) if str(item).strip()]:
            window_labels_by_subscription.setdefault(subscription_id, []).append(label)
    for subscription in burn_subscriptions:
        provider_id = str(subscription.get("provider_id") or "").strip()
        if provider_id:
            burn_by_provider.setdefault(provider_id, []).append(subscription)
    tooling_by_provider = _tooling_provider_index(tooling)
    credential_env_names = _credential_env_names(credential_surfaces)
    state_counts = Counter(state for provider in providers for state in list(provider.get("state_classes", [])))
    evidence_counts: Counter[str] = Counter()
    verification_queue: list[tuple[int, str, str, str, str]] = []
    for provider in providers:
        provider_id = str(provider.get("id") or "")
        tooling_entries = tooling_by_provider.get(provider_id, [])
        provider_usage_capture = provider_usage_capture_index.get(provider_id, {})
        evidence_posture = _provider_evidence_posture(
            provider,
            tooling_entries=tooling_entries,
            credential_env_names=credential_env_names,
            provider_usage_capture=provider_usage_capture,
        )
        evidence_counts[evidence_posture] += 1
        pricing_truth_label = _provider_pricing_truth_label(provider)
        next_verification = _provider_next_verification(
            provider,
            evidence_posture,
            provider_usage_capture,
            vault_litellm_env_audit,
        )
        if next_verification == "No immediate verification gap recorded.":
            continue
        verification_queue.append(
            (
                _provider_verification_priority(evidence_posture, pricing_truth_label),
                provider_id,
                evidence_posture,
                pricing_truth_label,
                next_verification,
            )
        )
    lines = [
        "# Provider Catalog Report",
        "",
        "Generated from `config/automation-backbone/provider-catalog.json` and `config/automation-backbone/subscription-burn-registry.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{catalog.get('version', 'unknown')}`",
        f"- Burn registry version: `{burn_registry.get('version', 'unknown')}`",
        f"- Providers tracked: `{len(providers)}`",
        f"- Burn-enabled lanes tracked: `{len(burn_subscriptions)}`",
        f"- Burn schedule windows tracked: `{len(burn_windows)}`",
        f"- Official verification date: `{catalog.get('official_verified_at', 'unknown')}`",
        f"- Provider usage captures tracked: `{len(provider_usage_capture_index)}`",
        "",
        *_render_table(
            ["State class", "Count"],
            [[f"`{state}`", str(count)] for state, count in sorted(state_counts.items())],
        ),
    ]
    if evidence_counts:
        lines.extend(
            [
                "",
                "## Evidence Posture",
                "",
                *_render_table(
                    ["Evidence posture", "Count"],
                    [[f"`{state}`", str(count)] for state, count in sorted(evidence_counts.items())],
                ),
            ]
        )
    if verification_queue:
        lines.extend(
            [
                "",
                "## Verification Queue",
                "",
                *_render_table(
                    ["Provider", "Evidence posture", "Pricing truth", "Next verification"],
                    [
                        [
                            f"`{provider_id}`",
                            f"`{evidence_posture}`",
                            f"`{pricing_truth}`",
                            next_verification,
                        ]
                        for _, provider_id, evidence_posture, pricing_truth, next_verification in sorted(
                            verification_queue,
                            key=lambda item: (item[0], item[1]),
                        )
                    ],
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Providers",
            "",
            *_render_table(
                [
                    "Provider",
                    "Category",
                    "Access",
                    "States",
                    "Burn lane",
                    "Monthly cost",
                    "Pricing status",
                    "Evidence posture",
                ],
                [
                    [
                        f"`{provider.get('id')}`",
                        str(provider.get("category") or ""),
                        str(provider.get("access_mode") or ""),
                        list_or_none(list(provider.get("state_classes", []))),
                        list_or_none(
                            [
                                str(subscription.get("id") or "")
                                for subscription in burn_by_provider.get(str(provider.get("id") or ""), [])
                                if str(subscription.get("id") or "").strip()
                            ]
                        ),
                        (
                            f"${provider.get('monthly_cost_usd')}"
                            if provider.get("monthly_cost_usd") is not None
                            else "unverified or metered"
                        ),
                        str(provider.get("official_pricing_status") or ""),
                        _provider_evidence_posture(
                            provider,
                            tooling_entries=tooling_by_provider.get(str(provider.get("id") or ""), []),
                            credential_env_names=credential_env_names,
                            provider_usage_capture=provider_usage_capture_index.get(str(provider.get("id") or ""), {}),
                        ),
                    ]
                    for provider in providers
                ],
            ),
        ]
    )
    for provider in providers:
        provider_id = str(provider.get("id") or "")
        observed_runtime = dict(provider.get("observed_runtime") or {})
        tooling_entries = tooling_by_provider.get(provider_id, [])
        provider_usage_capture = provider_usage_capture_index.get(provider_id, {})
        burn_entries = burn_by_provider.get(provider_id, [])
        burn_labels = [str(entry.get("id") or "") for entry in burn_entries if str(entry.get("id") or "").strip()]
        burn_windows_for_provider = sorted(
            {
                label
                for entry in burn_entries
                for label in window_labels_by_subscription.get(str(entry.get("id") or ""), [])
                if label
            }
        )
        evidence_posture = _provider_evidence_posture(
            provider,
            tooling_entries=tooling_entries,
            credential_env_names=credential_env_names,
            provider_usage_capture=provider_usage_capture,
        )
        runtime_env_audit_line = None
        if str(dict(provider.get("evidence") or {}).get("kind") or "") == "vault_litellm_proxy" and vault_litellm_env_audit:
            runtime_env_audit_line = (
                f"- Runtime env audit: missing "
                f"{list_or_none(_vault_env_names_for_provider(provider, vault_litellm_env_audit, 'container_missing_env_names'))}, "
                f"present {list_or_none(_vault_env_names_for_provider(provider, vault_litellm_env_audit, 'container_present_env_names'))}, "
                f"audit `{vault_litellm_env_audit.get('collected_at', 'unknown')}`"
            )
        lines.extend(
            [
                "",
                f"## {provider.get('label')} (`{provider_id}`)",
                "",
                f"- Product: {provider.get('subscription_product')}",
                (
                    f"- Pricing truth: `{_provider_pricing_truth_label(provider)}`"
                    + (
                        f", `${provider.get('monthly_cost_usd')}/mo`"
                        if provider.get("monthly_cost_usd") is not None
                        else ", `unverified or metered`"
                    )
                ),
                f"- Execution modes: {list_or_none(list(provider.get('execution_modes', [])))}",
                f"- State classes: {list_or_none(list(provider.get('state_classes', [])))}",
                f"- Evidence posture: `{evidence_posture}`",
                f"- Burn lanes: {list_or_none(burn_labels)}",
                f"- Burn windows: {list_or_none(burn_windows_for_provider)}",
                f"- Observed hosts: {list_or_none(list(provider.get('observed_hosts', [])))}",
                f"- Observed runtime: {_observed_runtime_summary(observed_runtime, provider_usage_capture)}",
                f"- Evidence contract: {_provider_evidence_summary(provider, provider_usage_capture)}",
                *( [runtime_env_audit_line] if runtime_env_audit_line else [] ),
                f"- Tool evidence: {_tooling_summary(tooling_entries)}",
                f"- Next verification: {_provider_next_verification(provider, evidence_posture, provider_usage_capture, vault_litellm_env_audit)}",
                f"- Verification steps: {list_or_none(_provider_verification_steps(provider, evidence_posture, provider_usage_capture, vault_litellm_env_audit))}",
                f"- Official sources: {render_link_list(list(provider.get('official_sources', [])))}",
                f"- Env contracts: {list_or_none(list(provider.get('env_contracts', [])))}",
                f"- CLI commands: {list_or_none(list(provider.get('cli_commands', [])))}",
                f"- Notes: {list_or_none(list(provider.get('notes', [])))}",
            ]
        )
    drifts = list(catalog.get("known_drifts", []))
    if drifts:
        lines.extend(["", "## Known Drift", ""])
        for drift in drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    lines.append("")
    return "\n".join(lines)


def _legacy_render_operator_surface_report() -> str:
    registry = load_registry("operator-surface-registry.json")
    latest_snapshot = _load_latest_truth_snapshot() or {}
    probe_payload = dict(latest_snapshot.get("operator_surface_probe") or {})
    probed_surfaces = {
        str(surface.get("id") or ""): dict(surface)
        for surface in probe_payload.get("surfaces", [])
        if isinstance(surface, dict) and str(surface.get("id") or "").strip()
    }
    surfaces = [dict(entry) for entry in registry.get("surfaces", []) if isinstance(entry, dict)]
    canonical_front_door = dict(registry.get("canonical_front_door") or {})

    def probe_status(probe: dict[str, Any] | None) -> str:
        if not probe:
            return "unprobed"
        if "status_code" in probe:
            detail = f" {probe.get('status_code')}"
            if probe.get("ok") is False:
                detail += " fail"
            return detail.strip()
        if probe.get("detail"):
            return str(probe.get("detail"))
        return "ok" if probe.get("ok") else "failed"

    def next_static_summary(probe: dict[str, Any] | None) -> str:
        if not probe:
            return "n/a"
        asset_count = int(probe.get("asset_count") or 0)
        if asset_count == 0:
            return "no assets found"
        failures = sum(1 for entry in probe.get("asset_results", []) if not bool(entry.get("ok")))
        return f"{asset_count - failures}/{asset_count} ok"

    portal_rows: list[list[str]] = []
    inventory_rows: list[list[str]] = []
    launchpad_rows: list[list[str]] = []
    for surface in sorted(surfaces, key=lambda entry: (str(entry.get("surface_kind") or ""), str(entry.get("node") or ""), str(entry.get("id") or ""))):
        surface_id = str(surface.get("id") or "")
        probe = probed_surfaces.get(surface_id, {})
        if str(surface.get("surface_kind") or "") == "portal":
            portal_rows.append(
                [
                    f"`{surface_id}`",
                    str(surface.get("node") or ""),
                    f"`{surface.get('status')}`",
                    probe_status(dict(probe.get("runtime_probe") or {})),
                    next_static_summary(dict(probe.get("next_static_probe") or {})),
                    f"`{surface.get('retirement_state')}`",
                ]
            )
        inventory_rows.append(
            [
                f"`{surface_id}`",
                f"`{surface.get('surface_kind')}`",
                str(surface.get("node") or ""),
                f"`{surface.get('status')}`",
                f"`{surface.get('operator_role')}`",
                probe_status(dict(probe.get("runtime_probe") or {})),
            ]
        )
        if str(surface.get("navigation_role") or "") in {"launchpad", "domain_surface", "front_door"}:
            launchpad_rows.append(
                [
                    str(surface.get("label") or surface_id),
                    f"`{surface.get('node')}`",
                    f"`{surface.get('navigation_role')}`",
                    str(surface.get("canonical_url") or ""),
                    str(surface.get("runtime_url") or ""),
                ]
            )

    runtime_duplicate_groups = [
        dict(entry)
        for entry in probe_payload.get("runtime_duplicate_groups", [])
        if isinstance(entry, dict)
    ]
    known_drifts = [dict(entry) for entry in registry.get("known_drifts", []) if isinstance(entry, dict)]
    status_counts = Counter(str(surface.get("status") or "unknown") for surface in surfaces)
    lines = [
        "# Operator Surface Report",
        "",
        "Generated from `config/automation-backbone/operator-surface-registry.json` and the latest truth snapshot.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Canonical front door: `{canonical_front_door.get('canonical_url', 'unknown')}`",
        f"- Runtime target: `{canonical_front_door.get('runtime_target', 'unknown')}`",
        f"- Operator surfaces tracked: `{len(surfaces)}`",
        f"- Runtime duplicate groups: `{len(runtime_duplicate_groups)}`",
        f"- Known surface drifts: `{len(known_drifts)}`",
        "",
        *_render_table(
            ["Status", "Count"],
            [[f"`{status}`", str(count)] for status, count in sorted(status_counts.items())],
        ),
        "",
        "## Front Door Contract",
        "",
        f"- Surface id: `{canonical_front_door.get('surface_id', 'unknown')}`",
        f"- Canonical URL: `{canonical_front_door.get('canonical_url', 'unknown')}`",
        f"- Runtime target: `{canonical_front_door.get('runtime_target', 'unknown')}`",
        f"- Reverse proxy plan: `{canonical_front_door.get('reverse_proxy', 'unknown')}` on `{canonical_front_door.get('node', 'unknown')}`",
        f"- Deployment goal: `{canonical_front_door.get('deployment_goal', 'unknown')}`",
        "",
        "## Portal Surfaces",
        "",
        *_render_table(
            ["Surface", "Node", "Registry Status", "Runtime Probe", "Next Static", "Retirement State"],
            portal_rows or [["none", "-", "-", "-", "-", "-"]],
        ),
        "",
        "## Launchpad Surfaces",
        "",
        *_render_table(
            ["Label", "Node", "Nav Role", "Canonical URL", "Runtime URL"],
            launchpad_rows or [["none", "-", "-", "-", "-"]],
        ),
        "",
        "## Inventory",
        "",
        *_render_table(
            ["Surface", "Kind", "Node", "Status", "Operator Role", "Runtime Probe"],
            inventory_rows or [["none", "-", "-", "-", "-", "-"]],
        ),
        "",
        "## Runtime Findings",
        "",
    ]
    if runtime_duplicate_groups:
        for finding in runtime_duplicate_groups:
            surface_group = str(finding.get("surface_group") or "unknown")
            ids = list_or_none(list(finding.get("reachable_surface_ids", [])))
            lines.append(f"- `{surface_group}` has multiple reachable runtime surfaces: {ids}")
    else:
        lines.append("- No duplicate reachable surface groups were observed in the latest snapshot.")

    dev_runtime = dict(probe_payload.get("dev_command_center_runtime") or {})
    workshop_runtime = dict(probe_payload.get("workshop_shadow_runtime") or {})
    lines.extend(
        [
            "",
            "### Live Runtime Ownership Evidence",
            "",
            f"- DEV command center service present: `{dev_runtime.get('service_present', False)}`",
            f"- DEV command center active state: `{dev_runtime.get('active_state', 'unknown')}/{dev_runtime.get('sub_state', 'unknown')}`",
            f"- DEV command center working directory: `{dev_runtime.get('working_directory', 'unknown')}`",
            f"- DEV command center exec start: `{dev_runtime.get('exec_start', 'unknown')}`",
            f"- WORKSHOP shadow container running: `{workshop_runtime.get('running', False)}`",
            f"- WORKSHOP shadow image: `{workshop_runtime.get('image', 'unknown')}`",
            f"- WORKSHOP shadow ports: `{workshop_runtime.get('ports', 'unknown')}`",
            "",
            "## Known Drift",
            "",
        ]
    )
    if known_drifts:
        for drift in known_drifts:
            lines.append(
                f"- `{drift.get('id')}` ({drift.get('severity')} on `{drift.get('surface')}`): {drift.get('description')}"
            )
    else:
        lines.append("- No active operator-surface drift is recorded.")
    lines.append("")
    return "\n".join(lines)


def render_tooling_report() -> str:
    registry = load_registry("tooling-inventory.json")
    hosts = list(registry.get("hosts", []))
    lines = [
        "# Tooling Inventory Report",
        "",
        "Generated from `config/automation-backbone/tooling-inventory.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Hosts tracked: `{len(hosts)}`",
        f"- Tool entries tracked: `{sum(len(host.get('tools', [])) for host in hosts)}`",
        "",
    ]
    for host in hosts:
        tools = list(host.get("tools", []))
        lines.extend(
            [
                f"## {host.get('host')} (`{host.get('id')}`)",
                "",
                f"- Last verified: `{host.get('verified_at')}`",
                "",
                *_render_table(
                    ["Tool", "Provider", "Command", "Status", "Version"],
                    [
                        [
                            f"`{tool.get('tool_id')}`",
                            f"`{tool.get('provider_id')}`" if tool.get("provider_id") else "none",
                            f"`{tool.get('command')}`",
                            f"`{tool.get('status')}`",
                            f"`{tool.get('version')}`" if tool.get("version") else "unset",
                        ]
                        for tool in tools
                    ],
                ),
                "",
            ]
        )
    return "\n".join(lines)


def render_repo_roots_report() -> str:
    registry = load_registry("repo-roots-registry.json")
    latest_snapshot = _load_latest_truth_snapshot() or {}
    dev_runtime_probe = dict(latest_snapshot.get("dev_runtime_probe") or {})
    dev_runtime_detail = dict(dev_runtime_probe.get("detail") or {}) if isinstance(dev_runtime_probe.get("detail"), dict) else {}
    foundry_agents_runtime_probe = dict(latest_snapshot.get("foundry_agents_runtime_probe") or {})
    foundry_agents_runtime_detail = (
        dict(foundry_agents_runtime_probe.get("detail") or {})
        if isinstance(foundry_agents_runtime_probe.get("detail"), dict)
        else {}
    )
    local_repo_probe = _local_git_probe(str(REPO_ROOT))
    roots = list(registry.get("roots", []))
    lines = [
        "# Repo Roots Report",
        "",
        "Generated from `config/automation-backbone/repo-roots-registry.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Roots tracked: `{len(roots)}`",
        "",
        *_render_table(
            ["Root", "Host", "Authority", "Status", "Scope"],
            [
                [
                    f"`{root.get('id')}`",
                    f"`{root.get('host')}`",
                    f"`{root.get('authority_level')}`",
                    f"`{root.get('status')}`",
                    str(root.get("runtime_scope") or ""),
                ]
                for root in roots
            ],
        ),
    ]
    for root in roots:
        extra_lines: list[str] = []
        if str(root.get("id") or "") == "desk-main":
            extra_lines.extend(
                [
                    f"- Local dirty file count: `{local_repo_probe.get('dirty_count', 0)}`",
                    f"- Local dirty sample: {list_or_none(list(local_repo_probe.get('status_sample', [])))}",
                ]
            )
        elif str(root.get("id") or "") == "dev-runtime-repo" and dev_runtime_probe.get("ok"):
            extra_lines.extend(
                [
                    f"- Runtime dirty file count: `{dev_runtime_detail.get('repo_dirty_count', 0)}`",
                    f"- Runtime dirty sample: {list_or_none(list(dev_runtime_detail.get('repo_status_sample', [])))}",
                ]
            )
        elif str(root.get("id") or "") == "foundry-opt-athanor" and foundry_agents_runtime_probe.get("ok"):
            deployment_root = (
                dict(foundry_agents_runtime_detail.get("deployment_root") or {})
                if isinstance(foundry_agents_runtime_detail.get("deployment_root"), dict)
                else {}
            )
            container = (
                dict(foundry_agents_runtime_detail.get("container") or {})
                if isinstance(foundry_agents_runtime_detail.get("container"), dict)
                else {}
            )
            extra_lines.extend(
                [
                    f"- Compose root matches expected: `{deployment_root.get('compose_root_matches_expected', False)}`",
                    f"- Build root clean: `{deployment_root.get('build_root_clean', False)}`",
                    f"- Container running: `{container.get('running', False)}`",
                    f"- Runtime import path: `{container.get('module_file') or 'unknown'}`",
                ]
            )
        lines.extend(
            [
                "",
                f"## {root.get('id')}",
                "",
                f"- Path: `{root.get('path')}`",
                f"- Host: `{root.get('host')}`",
                f"- Authority: `{root.get('authority_level')}`",
                f"- Notes: {list_or_none(list(root.get('notes', [])))}",
                *extra_lines,
            ]
        )
    active_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "active") == "active"
    ]
    retired_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "") == "retired"
    ]
    if active_drifts:
        lines.extend(["", "## Known Drift", ""])
        for drift in active_drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    if retired_drifts:
        lines.extend(["", "## Retired Drift", ""])
        for drift in retired_drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    lines.append("")
    return "\n".join(lines)


def render_runtime_ownership_report() -> str:
    contract = load_registry("runtime-ownership-contract.json")
    ownership_packets = load_registry("runtime-ownership-packets.json")
    repo_roots = load_registry("repo-roots-registry.json")
    latest_snapshot = _load_latest_truth_snapshot() or {}
    dev_runtime_probe = dict(latest_snapshot.get("dev_runtime_probe") or {})
    dev_runtime_detail = (
        dict(dev_runtime_probe.get("detail") or {})
        if isinstance(dev_runtime_probe.get("detail"), dict)
        else {}
    )
    foundry_agents_runtime_probe = dict(latest_snapshot.get("foundry_agents_runtime_probe") or {})
    foundry_agents_runtime_detail = (
        dict(foundry_agents_runtime_probe.get("detail") or {})
        if isinstance(foundry_agents_runtime_probe.get("detail"), dict)
        else {}
    )
    operator_surface_probe = dict(latest_snapshot.get("operator_surface_probe") or {})
    dev_command_center_runtime = dict(operator_surface_probe.get("dev_command_center_runtime") or {})
    dev_command_center_detail = (
        dict(dev_command_center_runtime.get("detail") or {})
        if isinstance(dev_command_center_runtime.get("detail"), dict)
        else {}
    )
    local_repo_probe = _local_git_probe(str(REPO_ROOT))
    lanes = [dict(entry) for entry in contract.get("lanes", []) if isinstance(entry, dict)]
    packets = [
        dict(entry) for entry in ownership_packets.get("packets", []) if isinstance(entry, dict)
    ]
    packet_by_id = {str(entry.get("id") or ""): entry for entry in packets}
    promotion_criteria = [
        dict(entry) for entry in contract.get("promotion_criteria", []) if isinstance(entry, dict)
    ]
    known_gaps = [dict(entry) for entry in contract.get("known_gaps", []) if isinstance(entry, dict)]
    criteria_counts = Counter(str(entry.get("status") or "unknown") for entry in promotion_criteria)

    lines = [
        "# Runtime Ownership Report",
        "",
        "Generated from `config/automation-backbone/runtime-ownership-contract.json` plus the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{contract.get('version', 'unknown')}`",
        f"- Cached truth snapshot: `{latest_snapshot.get('collected_at', 'not available') if isinstance(latest_snapshot, dict) else 'not available'}`",
        f"- Promotion gate: `{contract.get('promotion_gate_id', 'unknown')}`",
        f"- Goal: {contract.get('goal', 'unset')}",
        f"- Implementation authority: `{contract.get('implementation_authority_root_id', 'unknown')}` -> `{_root_path_by_id(repo_roots, str(contract.get('implementation_authority_root_id') or '')) or 'unknown'}`",
        f"- Runtime authority: `{contract.get('runtime_authority_root_id', 'unknown')}` -> `{_root_path_by_id(repo_roots, str(contract.get('runtime_authority_root_id') or '')) or 'unknown'}`",
        f"- Runtime state roots: {list_or_none([str(item) for item in contract.get('runtime_state_root_ids', [])])}",
        f"- Ownership lanes tracked: `{len(lanes)}`",
        f"- Execution packets tracked: `{len(packets)}`",
        "",
        *_render_table(
            ["Criterion status", "Count"],
            [[f"`{status}`", str(count)] for status, count in sorted(criteria_counts.items())],
        ),
        "",
        "## Repo Evidence",
        "",
        f"- Implementation dirty file count: `{local_repo_probe.get('dirty_count', 0)}`",
    ]
    if dev_runtime_probe.get("ok"):
        lines.extend(
            [
                f"- DEV runtime dirty file count: `{dev_runtime_detail.get('repo_dirty_count', 0)}`",
            ]
        )
    else:
        lines.append(f"- DEV runtime probe: `{dev_runtime_probe.get('detail') or 'unavailable'}`")
    if foundry_agents_runtime_probe.get("ok"):
        foundry_container = (
            dict(foundry_agents_runtime_detail.get("container") or {})
            if isinstance(foundry_agents_runtime_detail.get("container"), dict)
            else {}
        )
        foundry_deployment_root = (
            dict(foundry_agents_runtime_detail.get("deployment_root") or {})
            if isinstance(foundry_agents_runtime_detail.get("deployment_root"), dict)
            else {}
        )
        lines.extend(
            [
                f"- FOUNDRY compose root matches expected: `{foundry_deployment_root.get('compose_root_matches_expected', False)}`",
                f"- FOUNDRY build root clean: `{foundry_deployment_root.get('build_root_clean', False)}`",
                f"- FOUNDRY runtime import path: `{foundry_container.get('module_file') or 'unknown'}`",
            ]
        )
    else:
        lines.append(f"- FOUNDRY agents runtime probe: `{foundry_agents_runtime_probe.get('detail') or 'unavailable'}`")

    lane_rows = [
        [
            f"`{lane.get('id', 'unknown')}`",
            f"`{lane.get('host', 'unknown')}`",
            f"`{lane.get('deployment_mode', 'unknown')}`",
            f"`{lane.get('status', 'unknown')}`",
            list_or_none([str(item) for item in lane.get("owner_root_ids", [])]),
            f"`{lane.get('execution_packet_id', 'none')}`",
            str(lane.get("next_action") or ""),
        ]
        for lane in lanes
    ]
    lines.extend(
        [
            "",
            "## Ownership Lanes",
            "",
            *_render_table(
                ["Lane", "Host", "Mode", "Status", "Owner roots", "Packet", "Next action"],
                lane_rows or [["none", "-", "-", "-", "-", "-"]],
            ),
        ]
    )

    systemd_units = {
        str(entry.get("unit") or ""): dict(entry)
        for entry in dev_runtime_detail.get("systemd_units", [])
        if isinstance(entry, dict)
    }
    for lane in lanes:
        owner_roots = [
            f"{root_id} -> {_root_path_by_id(repo_roots, str(root_id)) or 'unknown'}"
            for root_id in lane.get("owner_root_ids", [])
        ]
        lines.extend(
            [
                "",
                f"## {lane.get('id', 'unknown')}",
                "",
                f"- Label: `{lane.get('label', 'unknown')}`",
                f"- Host: `{lane.get('host', 'unknown')}`",
                f"- Status: `{lane.get('status', 'unknown')}`",
                f"- Mode: `{lane.get('deployment_mode', 'unknown')}`",
                f"- Owner roots: {list_or_none(owner_roots)}",
                f"- Source root: `{lane.get('source_root_id', 'none')}`",
                f"- Runtime scope: {lane.get('runtime_scope', 'unset')}",
                f"- Source paths: {list_or_none([str(item) for item in lane.get('source_paths', [])])}",
                f"- Runtime paths: {list_or_none([str(item) for item in lane.get('runtime_paths', [])])}",
                f"- Active surfaces: {list_or_none([str(item) for item in lane.get('active_surfaces', [])])}",
                f"- Execution packet: `{lane.get('execution_packet_id', 'none')}`",
                f"- Evidence: {list_or_none([str(item) for item in lane.get('evidence_paths', [])])}",
                f"- Verification commands: {list_or_none([str(item) for item in lane.get('verification_commands', [])])}",
                f"- Rollback contract: {lane.get('rollback_contract', 'unset')}",
                f"- Approval boundary: {lane.get('approval_boundary', 'unset')}",
                f"- Next action: {lane.get('next_action', 'unset')}",
            ]
        )
        lane_id = str(lane.get("id") or "")
        packet = packet_by_id.get(str(lane.get("execution_packet_id") or ""))
        if packet:
            lines.extend(
                [
                    f"- Packet status: `{packet.get('status', 'unknown')}`",
                    f"- Packet approval type: `{packet.get('approval_packet_type', 'unknown')}`",
                ]
            )
        if lane_id == "dev-dashboard-compose":
            container = dict(dev_command_center_detail.get("container") or {})
            deployment_root = dict(dev_command_center_detail.get("deployment_root") or {})
            legacy_service = dict(dev_command_center_detail.get("legacy_service") or {})
            control_files = [
                dict(entry)
                for entry in dev_command_center_detail.get("control_files", [])
                if isinstance(entry, dict)
            ]
            lines.extend(
                [
                    "",
                    "### Live dashboard evidence",
                    "",
                    f"- Deployment mode: `{dev_command_center_detail.get('deployment_mode', 'unknown')}`",
                    f"- Active root: `{deployment_root.get('observed_active_root') or 'unknown'}`",
                    f"- Runtime repo compose controls container: `{deployment_root.get('runtime_repo_compose_controls_container', False)}`",
                    f"- Container running: `{container.get('running', False)}`",
                    f"- Container status: `{container.get('status') or 'unknown'}`",
                    f"- Compose working dir: `{container.get('compose_working_dir') or 'unknown'}`",
                    f"- Legacy service state: `{legacy_service.get('active_state') or 'unknown'}` / `{legacy_service.get('sub_state') or 'unknown'}`",
                    f"- Legacy unit file state: `{legacy_service.get('unit_file_state') or 'unknown'}`",
                    f"- Legacy service root-cause hint: `{legacy_service.get('root_cause_hint') or 'none'}`",
                    f"- Runtime probe status: `{dev_command_center_detail.get('local_runtime_status_code') or 'unknown'}`",
                    f"- Canonical probe status: `{dev_command_center_detail.get('local_canonical_status_code') or 'unknown'}`",
                ]
            )
            if control_files:
                lines.extend(
                    [
                        "",
                        *_render_table(
                            [
                                "Control file",
                                "Impl -> runtime repo",
                                "Impl -> deploy root",
                                "Runtime repo -> deploy root",
                            ],
                            [
                                [
                                    f"`{entry.get('relative_path', 'unknown')}`",
                                    f"`{entry.get('implementation_matches_runtime_repo', False)}`",
                                    f"`{entry.get('implementation_matches_deploy_root', False)}`",
                                    f"`{entry.get('deploy_matches_runtime_repo', False)}`",
                                ]
                                for entry in control_files
                            ],
                        ),
                    ]
                )
        elif lane_id == "dev-runtime-repo-systemd":
            rows = []
            for surface in lane.get("active_surfaces", []):
                unit = systemd_units.get(str(surface), {})
                rows.append(
                    [
                        f"`{surface}`",
                        list_or_none([str(item) for item in unit.get("working_directories", [])]),
                        list_or_none([str(item) for item in unit.get("exec_starts", [])]),
                        str(unit.get("environment_file_count", 0)),
                    ]
                )
            lines.extend(
                [
                    "",
                    "### Live systemd evidence",
                    "",
                    *_render_table(
                        ["Unit", "Working directories", "ExecStart", "EnvFiles"],
                        rows or [["none", "-", "-", "-"]],
                    ),
                ]
            )
        elif lane_id == "dev-heartbeat-opt":
            heartbeat_unit = systemd_units.get("athanor-heartbeat.service", {})
            heartbeat_bundle = (
                dict(dev_runtime_detail.get("heartbeat_bundle") or {})
                if isinstance(dev_runtime_detail.get("heartbeat_bundle"), dict)
                else {}
            )
            lines.extend(
                [
                    "",
                    "### Live heartbeat evidence",
                    "",
                    f"- Unit file state: `{heartbeat_unit.get('unit_file_state') or 'unknown'}`",
                    f"- Working directories: {list_or_none([str(item) for item in heartbeat_unit.get('working_directories', [])])}",
                    f"- ExecStart: {list_or_none([str(item) for item in heartbeat_unit.get('exec_starts', [])])}",
                    f"- EnvFiles: `{heartbeat_unit.get('environment_file_count', 0)}`",
                    f"- Deployed script exists: `{heartbeat_bundle.get('script_exists', False)}`",
                    f"- Host-local env exists: `{heartbeat_bundle.get('env_exists', False)}`",
                    f"- Runtime venv exists: `{heartbeat_bundle.get('venv_python_exists', False)}`",
                    f"- Implementation matches deploy root: `{heartbeat_bundle.get('implementation_matches_deploy_root', False)}`",
                ]
            )
        elif lane_id == "dev-runtime-state":
            lines.extend(
                [
                    "",
                    "### Live runtime-state evidence",
                    "",
                    f"- /opt entries: {list_or_none([str(item) for item in dev_runtime_detail.get('opt_entries', [])])}",
                    f"- /home/shaun/.athanor entries: {list_or_none([str(item) for item in dev_runtime_detail.get('state_entries', [])])}",
                    f"- Cron files: {list_or_none([str(item) for item in dev_runtime_detail.get('cron_files', [])])}",
                ]
            )
        elif lane_id == "foundry-agents-compose":
            container = (
                dict(foundry_agents_runtime_detail.get("container") or {})
                if isinstance(foundry_agents_runtime_detail.get("container"), dict)
                else {}
            )
            deployment_root = (
                dict(foundry_agents_runtime_detail.get("deployment_root") or {})
                if isinstance(foundry_agents_runtime_detail.get("deployment_root"), dict)
                else {}
            )
            control_files = [
                dict(entry)
                for entry in foundry_agents_runtime_detail.get("control_files", [])
                if isinstance(entry, dict)
            ]
            source_mirrors = [
                dict(entry)
                for entry in foundry_agents_runtime_detail.get("source_mirrors", [])
                if isinstance(entry, dict)
            ]
            lines.extend(
                [
                    "",
                    "### Live FOUNDRY agents evidence",
                    "",
                    f"- Expected root exists: `{deployment_root.get('expected_exists', False)}`",
                    f"- Compose root matches expected: `{deployment_root.get('compose_root_matches_expected', False)}`",
                    f"- Build root clean: `{deployment_root.get('build_root_clean', False)}`",
                    f"- Nested source dir present: `{deployment_root.get('nested_source_dir_exists', False)}`",
                    f"- bak-codex files: {list_or_none([str(item) for item in deployment_root.get('bak_codex_files', [])])}",
                    f"- Container running: `{container.get('running', False)}`",
                    f"- Container status: `{container.get('status') or 'unknown'}`",
                    f"- Compose working dir: `{container.get('compose_working_dir') or 'unknown'}`",
                    f"- Compose config files: `{container.get('compose_config_files') or 'unknown'}`",
                    f"- Runtime import path: `{container.get('module_file') or 'unknown'}`",
                    f"- Site-packages import: `{container.get('site_packages_import', False)}`",
                    f"- Source mirrors: {list_or_none([str(entry.get('path') or '') for entry in source_mirrors])}",
                ]
            )
            if control_files:
                lines.extend(
                    [
                        "",
                        *_render_table(
                            ["Control path", "Kind", "Impl exists", "Runtime exists", "Impl -> runtime"],
                            [
                                [
                                    f"`{entry.get('relative_path', 'unknown')}`",
                                    f"`{entry.get('kind', 'unknown')}`",
                                    f"`{entry.get('implementation_exists', False)}`",
                                    f"`{entry.get('runtime_exists', False)}`",
                                    f"`{entry.get('implementation_matches_runtime', False)}`",
                                ]
                                for entry in control_files
                            ],
                        ),
                    ]
                )

    if promotion_criteria:
        lines.extend(["", "## Promotion Criteria", ""])
        lines.extend(
            _render_table(
                ["Criterion", "Status", "Requirement", "Evidence"],
                [
                    [
                        f"`{entry.get('id', 'unknown')}`",
                        f"`{entry.get('status', 'unknown')}`",
                        str(entry.get("requirement") or ""),
                        list_or_none([str(item) for item in entry.get("evidence_paths", [])]),
                    ]
                    for entry in promotion_criteria
                ],
            )
        )
    if packets:
        lines.extend(["", "## Execution Packets", ""])
        lines.extend(
            _render_table(
                ["Packet", "Status", "Lane", "Approval type", "Goal"],
                [
                    [
                        f"`{entry.get('id', 'unknown')}`",
                        f"`{entry.get('status', 'unknown')}`",
                        f"`{entry.get('lane_id', 'unknown')}`",
                        f"`{entry.get('approval_packet_type', 'unknown')}`",
                        str(entry.get("goal") or ""),
                    ]
                    for entry in packets
                ],
            )
        )
    if known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(
            _render_table(
                ["Gap", "Status", "Severity", "Surface", "Description"],
                [
                    [
                        f"`{entry.get('id', 'unknown')}`",
                        f"`{entry.get('status', 'unknown')}`",
                        f"`{entry.get('severity', 'unknown')}`",
                        str(entry.get("surface") or ""),
                        str(entry.get("description") or ""),
                    ]
                    for entry in known_gaps
                ],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_runtime_ownership_packets_report() -> str:
    packets_registry = load_registry("runtime-ownership-packets.json")
    contract = load_registry("runtime-ownership-contract.json")
    approval_packets = load_registry("approval-packet-registry.json")
    latest_snapshot = _load_latest_truth_snapshot() or {}
    dev_runtime_probe = dict(latest_snapshot.get("dev_runtime_probe") or {})
    dev_runtime_detail = (
        dict(dev_runtime_probe.get("detail") or {})
        if isinstance(dev_runtime_probe.get("detail"), dict)
        else {}
    )
    foundry_agents_runtime_probe = dict(latest_snapshot.get("foundry_agents_runtime_probe") or {})
    foundry_agents_runtime_detail = (
        dict(foundry_agents_runtime_probe.get("detail") or {})
        if isinstance(foundry_agents_runtime_probe.get("detail"), dict)
        else {}
    )
    operator_surface_probe = dict(latest_snapshot.get("operator_surface_probe") or {})
    dev_command_center_runtime = dict(operator_surface_probe.get("dev_command_center_runtime") or {})
    dev_command_center_detail = (
        dict(dev_command_center_runtime.get("detail") or {})
        if isinstance(dev_command_center_runtime.get("detail"), dict)
        else {}
    )
    lanes = {
        str(entry.get("id") or ""): dict(entry)
        for entry in contract.get("lanes", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    approval_packet_labels = {
        str(entry.get("id") or ""): str(entry.get("label") or "")
        for entry in approval_packets.get("packet_types", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    packets = [
        dict(entry)
        for entry in packets_registry.get("packets", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]

    lines = [
        "# Runtime Ownership Packets",
        "",
        "Generated from `config/automation-backbone/runtime-ownership-packets.json`, `config/automation-backbone/runtime-ownership-contract.json`, and the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        f"- Registry version: `{packets_registry.get('version', 'unknown')}`",
        f"- Cached truth snapshot: `{latest_snapshot.get('collected_at', 'not available') if isinstance(latest_snapshot, dict) else 'not available'}`",
        f"- Packets tracked: `{len(packets)}`",
    ]

    if packets:
        lines.extend(
            [
                "",
                *_render_table(
                    ["Packet", "Status", "Lane", "Approval type", "Goal"],
                    [
                        [
                            f"`{packet.get('id', 'unknown')}`",
                            f"`{packet.get('status', 'unknown')}`",
                            f"`{packet.get('lane_id', 'unknown')}`",
                            f"`{packet.get('approval_packet_type', 'unknown')}`",
                            str(packet.get("goal") or ""),
                        ]
                        for packet in packets
                    ],
                ),
            ]
        )

    for packet in packets:
        lane = lanes.get(str(packet.get("lane_id") or ""), {})
        lines.extend(
            [
                "",
                f"## {packet.get('id', 'unknown')}",
                "",
                f"- Label: `{packet.get('label', 'unknown')}`",
                f"- Status: `{packet.get('status', 'unknown')}`",
                f"- Lane: `{packet.get('lane_id', 'unknown')}`",
                f"- Approval type: `{packet.get('approval_packet_type', 'unknown')}` ({approval_packet_labels.get(str(packet.get('approval_packet_type') or ''), 'unknown')})",
                f"- Host: `{packet.get('host', 'unknown')}`",
                f"- Goal: {packet.get('goal', 'unset')}",
                f"- Lane next action: {lane.get('next_action', 'unset')}",
                f"- Backup root: `{packet.get('backup_root', 'unset')}`",
                f"- Evidence: {list_or_none([str(item) for item in packet.get('evidence_paths', [])])}",
            ]
        )
        path_mappings = [dict(entry) for entry in packet.get("path_mappings", []) if isinstance(entry, dict)]
        if path_mappings:
            lines.extend(
                [
                    "",
                    *_render_table(
                        ["Source path", "Runtime path", "Restart units"],
                        [
                            [
                                f"`{entry.get('source_path', 'unknown')}`",
                                f"`{entry.get('runtime_path', 'unknown')}`",
                                list_or_none([str(item) for item in entry.get("restart_units", [])]),
                            ]
                            for entry in path_mappings
                        ],
                    ),
                ]
            )
        target_units = [str(item) for item in packet.get("target_units", []) if str(item).strip()]
        if target_units:
            lines.extend(["", f"- Target units: {list_or_none(target_units)}"])

        packet_id = str(packet.get("id") or "")
        if packet_id == "dev-runtime-repo-sync-packet":
            lines.extend(
                [
                    "",
                    "### Live evidence",
                    "",
                    f"- DEV runtime dirty file count: `{dev_runtime_detail.get('repo_dirty_count', 0)}`",
                ]
            )
        elif packet_id == "dev-dashboard-shadow-retirement-packet":
            legacy_service = dict(dev_command_center_detail.get("legacy_service") or {})
            container = dict(dev_command_center_detail.get("container") or {})
            lines.extend(
                [
                    "",
                    "### Live evidence",
                    "",
                    f"- Legacy service state: `{legacy_service.get('active_state') or 'unknown'}` / `{legacy_service.get('sub_state') or 'unknown'}`",
                    f"- Legacy unit file state: `{legacy_service.get('unit_file_state') or 'unknown'}`",
                    f"- Legacy fragment path: `{legacy_service.get('fragment_path') or 'unknown'}`",
                    f"- Container running: `{container.get('running', False)}`",
                    f"- Canonical probe status: `{dev_command_center_detail.get('local_canonical_status_code') or 'unknown'}`",
                ]
            )
        elif packet_id == "dev-heartbeat-opt-deploy-packet":
            heartbeat_bundle = (
                dict(dev_runtime_detail.get("heartbeat_bundle") or {})
                if isinstance(dev_runtime_detail.get("heartbeat_bundle"), dict)
                else {}
            )
            lines.extend(
                [
                    "",
                    "### Live evidence",
                    "",
                    f"- Deployed script exists: `{heartbeat_bundle.get('script_exists', False)}`",
                    f"- Implementation matches deploy root: `{heartbeat_bundle.get('implementation_matches_deploy_root', False)}`",
                    f"- Host-local env exists: `{heartbeat_bundle.get('env_exists', False)}`",
                    f"- Runtime venv exists: `{heartbeat_bundle.get('venv_python_exists', False)}`",
                ]
            )
        elif packet_id == "foundry-agents-compose-deploy-packet":
            container = (
                dict(foundry_agents_runtime_detail.get("container") or {})
                if isinstance(foundry_agents_runtime_detail.get("container"), dict)
                else {}
            )
            deployment_root = (
                dict(foundry_agents_runtime_detail.get("deployment_root") or {})
                if isinstance(foundry_agents_runtime_detail.get("deployment_root"), dict)
                else {}
            )
            lines.extend(
                [
                    "",
                    "### Live evidence",
                    "",
                    f"- Compose root matches expected: `{deployment_root.get('compose_root_matches_expected', False)}`",
                    f"- Build root clean: `{deployment_root.get('build_root_clean', False)}`",
                    f"- Nested source dir present: `{deployment_root.get('nested_source_dir_exists', False)}`",
                    f"- bak-codex files: {list_or_none([str(item) for item in deployment_root.get('bak_codex_files', [])])}",
                    f"- Container running: `{container.get('running', False)}`",
                    f"- Container status: `{container.get('status') or 'unknown'}`",
                    f"- Runtime import path: `{container.get('module_file') or 'unknown'}`",
                ]
            )

        for heading, field in (
            ("Preflight Commands", "preflight_commands"),
            ("Exact Steps", "exact_steps"),
            ("Verification Commands", "verification_commands"),
            ("Rollback Steps", "rollback_steps"),
        ):
            entries = [str(item) for item in packet.get(field, []) if str(item).strip()]
            if not entries:
                continue
            lines.extend(["", f"### {heading}", ""])
            lines.extend([f"- {entry}" for entry in entries])

    lines.append("")
    return "\n".join(lines)


def _operator_surface_probe_summary(probe: dict[str, Any] | None) -> str:
    if not isinstance(probe, dict):
        return "`not_probed`"
    if not probe:
        return "`not_probed`"
    if probe.get("status_code") is not None:
        return f"`{probe.get('status_code')}`"
    if probe.get("ok"):
        return "`ok`"
    detail = str(probe.get("detail") or "failed").strip()
    return f"`{detail[:48]}`"


def render_operator_surface_report() -> str:
    registry = load_registry("operator-surface-registry.json")
    latest_snapshot = _load_latest_truth_snapshot()
    operator_surface_probe = (
        dict(latest_snapshot.get("operator_surface_probe") or {})
        if isinstance(latest_snapshot, dict)
        else {}
    )
    front_door_contract = dict(registry.get("front_door_contract") or {})
    surfaces = [
        dict(entry)
        for entry in registry.get("surfaces", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]
    surface_rows = [
        dict(entry)
        for entry in operator_surface_probe.get("surfaces", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]
    surface_probe_index = {str(entry.get("id") or ""): entry for entry in surface_rows}
    surface_kind_counts = Counter(str(entry.get("surface_kind") or "unknown") for entry in surfaces)
    status_counts = Counter(str(entry.get("status") or "unknown") for entry in surfaces)
    launchpad_surfaces = [
        entry for entry in surfaces if str(entry.get("navigation_role") or "") == "launchpad"
    ]
    active_portals = [
        entry
        for entry in surfaces
        if str(entry.get("surface_kind") or "") == "portal"
        and str(entry.get("status") or "") in {"active_production", "degraded_production"}
    ]
    shadow_portals = [entry for entry in surfaces if str(entry.get("status") or "") == "shadow"]
    active_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "active") == "active"
    ]
    retired_drifts = [
        dict(entry)
        for entry in registry.get("known_drifts", [])
        if isinstance(entry, dict) and str(entry.get("status") or "") == "retired"
    ]
    lines = [
        "# Operator Surface Report",
        "",
        "Generated from `config/automation-backbone/operator-surface-registry.json` plus the cached operator-surface live probe in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Front Door Contract",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Cached truth snapshot: `{latest_snapshot.get('collected_at', 'not available') if isinstance(latest_snapshot, dict) else 'not available'}`",
        f"- Canonical portal id: `{front_door_contract.get('canonical_portal_id', 'unknown')}`",
        f"- Canonical operator URL: `{front_door_contract.get('canonical_url', 'unknown')}`",
        f"- Canonical node: `{front_door_contract.get('canonical_node', 'unknown')}`",
        f"- Runtime service id: `{front_door_contract.get('runtime_service_id', 'unknown')}`",
        f"- Current runtime mode: `{front_door_contract.get('current_runtime_mode', 'unknown')}`",
        f"- Target runtime mode: `{front_door_contract.get('target_runtime_mode', 'unknown')}`",
        f"- Multiple active portals allowed: `{front_door_contract.get('allow_multiple_active_portals', False)}`",
        f"- Promotion gate: {front_door_contract.get('phase_promotion_gate', 'unset')}",
        "",
        "## Summary",
        "",
        f"- Human-facing surfaces tracked: `{len(surfaces)}`",
        f"- Launchpad-approved surfaces: `{len(launchpad_surfaces)}`",
        f"- Active production portal count: `{len(active_portals)}`",
        f"- Shadow portal count: `{len(shadow_portals)}`",
        f"- Duplicate active production portals observed: {list_or_none(list(operator_surface_probe.get('duplicate_active_production_portal_ids', [])))}",
        "",
        "### Surface kinds",
        "",
        *_render_table(
            ["Kind", "Count"],
            [[f"`{kind}`", str(count)] for kind, count in sorted(surface_kind_counts.items())],
        ),
        "",
        "### Statuses",
        "",
        *_render_table(
            ["Status", "Count"],
            [[f"`{status}`", str(count)] for status, count in sorted(status_counts.items())],
        ),
        "",
        "## Canonical Portal",
        "",
    ]

    canonical_portal = next(
        (entry for entry in surfaces if str(entry.get("id") or "") == str(front_door_contract.get("canonical_portal_id") or "")),
        {},
    )
    canonical_probe = surface_probe_index.get(str(canonical_portal.get("id") or ""), {})
    lines.extend(
        [
            f"- Label: `{canonical_portal.get('label', 'unknown')}`",
            f"- Status: `{canonical_portal.get('status', 'unknown')}`",
            f"- Canonical URL: `{canonical_portal.get('canonical_url', 'unknown')}`",
            f"- Runtime URL: `{canonical_portal.get('runtime_url', 'unknown')}`",
            f"- Deployment mode: `{canonical_portal.get('deployment_mode', 'unknown')}`",
            f"- Target deployment mode: `{canonical_portal.get('target_deployment_mode', 'unknown')}`",
            f"- Canonical probe: {_operator_surface_probe_summary(canonical_probe.get('canonical_probe'))}",
            f"- Runtime probe: {_operator_surface_probe_summary(canonical_probe.get('runtime_probe'))}",
        ]
    )
    next_static_probe = dict(canonical_probe.get("next_static_probe") or {})
    if next_static_probe:
        failing_assets = [
            dict(entry)
            for entry in next_static_probe.get("asset_results", [])
            if isinstance(entry, dict) and not bool(entry.get("ok"))
        ]
        lines.extend(
            [
                f"- Runtime Next.js asset probe: `{next_static_probe.get('status_code', 'unknown')}` root, `{len(failing_assets)}` failing sampled asset(s)",
                (
                    "- Sampled failing assets: "
                    + ", ".join(
                        f"`{item.get('path')}` -> `{item.get('status_code', item.get('detail', 'failed'))}`"
                        for item in failing_assets[:4]
                    )
                    if failing_assets
                    else "- Sampled failing assets: none"
                ),
            ]
        )
    dev_runtime = dict(operator_surface_probe.get("dev_command_center_runtime") or {})
    dev_runtime_detail = dict(dev_runtime.get("detail") or {}) if isinstance(dev_runtime.get("detail"), dict) else {}
    if dev_runtime_detail:
        if str(dev_runtime_detail.get("deployment_mode") or "") == "containerized_service_behind_caddy":
            container = dict(dev_runtime_detail.get("container") or {})
            caddy = dict(dev_runtime_detail.get("caddy") or {})
            legacy = dict(dev_runtime_detail.get("legacy_service") or {})
            deployment_root = dict(dev_runtime_detail.get("deployment_root") or {})
            lines.extend(
                [
                    f"- DEV runtime probe target: `{dev_runtime.get('target', 'unknown')}`",
                    f"- DEV deployment mode observed: `{dev_runtime_detail.get('deployment_mode', 'unknown')}`",
                    f"- Dashboard container running: `{container.get('running', False)}`",
                    f"- Dashboard container status: `{container.get('status', 'unknown')}`",
                    f"- Dashboard container image: `{container.get('image', 'unknown')}`",
                    f"- Dashboard container ports: `{container.get('ports', 'unknown')}`",
                    f"- Dashboard compose working dir: `{container.get('compose_working_dir', 'unknown') or 'unknown'}`",
                    f"- Dashboard compose config file(s): `{container.get('compose_config_files', 'unknown') or 'unknown'}`",
                    f"- Expected dashboard deploy root: `{deployment_root.get('expected_path', 'unknown')}`",
                    f"- Observed active dashboard root: `{deployment_root.get('observed_active_root', 'unknown') or 'unknown'}`",
                    f"- Observed compose config file(s): `{deployment_root.get('observed_compose_config_files', 'unknown') or 'unknown'}`",
                    f"- Dashboard deploy-root drift: `{deployment_root.get('drift', False)}`",
                    f"- DEV local runtime probe from host: `{dev_runtime_detail.get('local_runtime_status_code', 'unknown')}`",
                    f"- DEV local canonical probe from host: `{dev_runtime_detail.get('local_canonical_status_code', 'unknown')}`",
                    f"- Caddy service state: `{caddy.get('active_state', 'unknown')}` / `{caddy.get('sub_state', 'unknown')}`",
                    f"- Legacy dashboard systemd state: `{legacy.get('active_state', 'unknown')}` / `{legacy.get('sub_state', 'unknown')}`",
                    f"- Legacy dashboard working directory: `{dev_runtime_detail.get('working_directory', 'unknown')}`",
                ]
            )
        else:
            lines.extend(
                [
                    f"- DEV runtime probe target: `{dev_runtime.get('target', 'unknown')}`",
                    f"- DEV service active state: `{dev_runtime_detail.get('active_state', 'unknown')}` / `{dev_runtime_detail.get('sub_state', 'unknown')}`",
                    f"- DEV working directory: `{dev_runtime_detail.get('working_directory', 'unknown')}`",
                    f"- DEV exec start: `{dev_runtime_detail.get('exec_start', 'unknown')}`",
                    f"- DEV standalone root: `{dev_runtime_detail.get('standalone_root', 'unknown')}`",
                    "- DEV standalone asset copy: "
                    + f"`public={dev_runtime_detail.get('standalone_public_present', False)}` "
                    + f"`static={dev_runtime_detail.get('standalone_static_present', False)}`",
                    "- DEV project-root asset copy: "
                    + f"`public={dev_runtime_detail.get('project_public_present', False)}` "
                    + f"`static={dev_runtime_detail.get('project_static_present', False)}`",
                    f"- DEV root cause hint: `{dev_runtime_detail.get('root_cause_hint', 'unset') or 'unset'}`",
                ]
            )
    lines.append("")

    lines.extend(["## Shadow Portal", ""])
    if shadow_portals:
        shadow_rows = []
        workshop_runtime = dict(operator_surface_probe.get("workshop_shadow_runtime") or {})
        workshop_runtime_detail = (
            dict(workshop_runtime.get("detail") or {})
            if isinstance(workshop_runtime.get("detail"), dict)
            else {}
        )
        for shadow in shadow_portals:
            probe = surface_probe_index.get(str(shadow.get("id") or ""), {})
            shadow_rows.append(
                [
                    f"`{shadow.get('id', 'unknown')}`",
                    f"`{shadow.get('runtime_url', 'unknown')}`",
                    f"`{shadow.get('status', 'unknown')}`",
                    f"`{shadow.get('retirement_state', 'unknown')}`",
                    _operator_surface_probe_summary(probe.get("runtime_probe")),
                    f"`{workshop_runtime_detail.get('status', 'unknown')}`" if workshop_runtime_detail else "`unknown`",
                ]
            )
        lines.extend(
            _render_table(
                ["Surface", "Runtime URL", "Status", "Retirement", "Runtime probe", "Container state"],
                shadow_rows,
            )
        )
        lines.append("")
    else:
        lines.extend(["No shadow portals are currently registered.", ""])

    lines.extend(["## Launchpad Surfaces", ""])
    if launchpad_surfaces:
        launchpad_rows = []
        for surface in launchpad_surfaces:
            probe = surface_probe_index.get(str(surface.get("id") or ""), {})
            launchpad_rows.append(
                [
                    f"`{surface.get('label', surface.get('id', 'unknown'))}`",
                    f"`{surface.get('node', 'unknown')}`",
                    f"`{surface.get('surface_kind', 'unknown')}`",
                    f"`{surface.get('canonical_url', 'unknown')}`",
                    f"`{surface.get('operator_role', 'unknown')}`",
                    _operator_surface_probe_summary(probe.get("canonical_probe")),
                ]
            )
        lines.extend(
            _render_table(
                ["Surface", "Node", "Kind", "Canonical URL", "Operator role", "Canonical probe"],
                launchpad_rows,
            )
        )
        lines.append("")
    else:
        lines.extend(["No launchpad surfaces are currently registered.", ""])

    lines.extend(["## Full Surface Matrix", ""])
    rows = []
    for surface in surfaces:
        probe = surface_probe_index.get(str(surface.get("id") or ""), {})
        rows.append(
            [
                f"`{surface.get('id', 'unknown')}`",
                f"`{surface.get('surface_kind', 'unknown')}`",
                f"`{surface.get('node', 'unknown')}`",
                f"`{surface.get('status', 'unknown')}`",
                f"`{surface.get('navigation_role', 'unknown')}`",
                f"`{surface.get('canonical_url', '') or 'n/a'}`",
                f"`{surface.get('runtime_url', '') or 'n/a'}`",
                _operator_surface_probe_summary(probe.get("runtime_probe")),
            ]
        )
    lines.extend(
        _render_table(
            ["Surface", "Kind", "Node", "Status", "Navigation", "Canonical URL", "Runtime URL", "Runtime probe"],
            rows,
        )
    )
    lines.append("")

    lines.extend(["## Known Drift", ""])
    if active_drifts:
        for drift in active_drifts:
            lines.append(
                f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')} Remediation: {drift.get('remediation')}"
            )
    else:
        lines.append("No active operator-surface drift items are currently registered.")
    if retired_drifts:
        lines.extend(["", "## Resolved Front-Door Drift", ""])
        for drift in retired_drifts:
            lines.append(
                f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}"
            )
    lines.append("")
    return "\n".join(lines)


def render_runtime_migration_report() -> str:
    registry = load_registry("runtime-migration-registry.json")
    latest_snapshot = _load_latest_truth_snapshot()
    snapshot_collected_at = str(latest_snapshot.get("collected_at") or "") if isinstance(latest_snapshot, dict) else ""
    snapshot_governor_facade = _snapshot_governor_facade(latest_snapshot)
    migrations = list(registry.get("migrations", []))
    status_counts = Counter(str(entry.get("status") or "unknown") for entry in migrations)
    implementation_counts = Counter(
        str(caller.get("implementation_state") or "unknown")
        for migration in migrations
        for caller in migration.get("callers", [])
    )
    cutover_counts = Counter(
        str(caller.get("runtime_cutover_state") or "unknown")
        for migration in migrations
        for caller in migration.get("callers", [])
    )
    total_callers = sum(len(list(migration.get("callers", []))) for migration in migrations)
    lines = [
        "# Runtime Migration Report",
        "",
        "Generated from `config/automation-backbone/runtime-migration-registry.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Migration seams tracked: `{len(migrations)}`",
        f"- Runtime-owned callers tracked: `{total_callers}`",
        "",
        *_render_table(
            ["Status", "Count"],
            [[f"`{status}`", str(count)] for status, count in sorted(status_counts.items())],
        ),
        "",
        *_render_table(
            ["Implementation state", "Count"],
            [[f"`{state}`", str(count)] for state, count in sorted(implementation_counts.items())],
        ),
        "",
        *_render_table(
            ["Runtime cutover state", "Count"],
            [[f"`{state}`", str(count)] for state, count in sorted(cutover_counts.items())],
        ),
    ]
    content_state_counts = Counter(
        str(record.get("content_state") or "unknown")
        for record in snapshot_governor_facade.get("caller_content_records", [])
        if isinstance(record, dict)
    )
    if content_state_counts:
        lines.extend(
            [
                "",
                f"- Latest live content evidence snapshot: `{snapshot_collected_at or 'unknown'}`",
                f"- Observed live `:8760` references: `{snapshot_governor_facade.get('observed_runtime_reference_count', 0)}`",
                f"- Planned callers no longer observed in the live runtime grep scan: `{snapshot_governor_facade.get('not_observed_runtime_reference_count', 0)}`",
                f"- Sync-required callers: `{snapshot_governor_facade.get('sync_required_count', 0)}`",
                f"- Already-synced callers: `{snapshot_governor_facade.get('already_synced_count', 0)}`",
                f"- Blocked callers: `{snapshot_governor_facade.get('blocked_sync_count', 0)}`",
                "",
                *_render_table(
                    ["Live content state", "Count"],
                    [[f"`{state}`", str(count)] for state, count in sorted(content_state_counts.items())],
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                f"- Latest live content evidence snapshot: `{snapshot_collected_at or 'not available'}`",
                "- Live content sync detail is unavailable until `python scripts/collect_truth_inventory.py` refreshes the cached truth snapshot.",
            ]
        )

    for migration in migrations:
        migration_status = str(migration.get("status") or "unknown")
        migration_retired = migration_status == "retired"
        callers = sorted(
            list(migration.get("callers", [])),
            key=lambda caller: (int(caller.get("sync_order") or 9999), str(caller.get("path") or "")),
        )
        runtime_backup_root = str(migration.get("runtime_backup_root") or "")
        systemd_backup_target = str(migration.get("systemd_backup_target") or "")
        live_content_records = {
            str(record.get("path") or ""): record
            for record in snapshot_governor_facade.get("caller_content_records", [])
            if isinstance(record, dict) and str(record.get("path") or "").strip()
        }
        lines.extend(
            [
                "",
                f"## {migration.get('id')}",
                "",
                f"- Status: `{migration_status}`",
                f"- Severity: `{migration.get('severity')}`",
                f"- Runtime surface: `{migration.get('runtime_surface')}`",
                f"- Runtime owner: `{migration.get('runtime_owner')}`",
                f"- Canonical owner: `{migration.get('canonical_owner')}`",
                f"- Runtime listener: `{migration.get('runtime_listener')}`",
                f"- Runtime backup root: `{runtime_backup_root}`" if runtime_backup_root else "- Runtime backup root: `unset`",
                f"- Systemd backup target: `{systemd_backup_target}`" if systemd_backup_target else "- Systemd backup target: `unset`",
                f"- Canonical successor surfaces: {list_or_none(list(migration.get('canonical_successor_surfaces', [])))}",
                f"- Maintenance window required: `{migration.get('maintenance_window_required')}`",
                f"- Observed at: `{migration.get('observed_at')}`",
                f"- Observed runtime repo head: `{migration.get('observed_runtime_repo_head')}`",
                f"- Runbook: [`{migration.get('runbook_path')}`](/C:/Athanor/{migration.get('runbook_path')})",
                f"- Live content evidence snapshot: `{snapshot_collected_at or 'not available'}`",
                f"- Live observed `:8760` references: `{snapshot_governor_facade.get('observed_runtime_reference_count', 0)}`",
                "",
                "### Acceptance Criteria",
                "",
            ]
        )
        for criterion in migration.get("acceptance_criteria", []):
            lines.append(f"- {criterion}")

        delete_gate = list(migration.get("delete_gate", []))
        if delete_gate:
            lines.extend(["", "### Delete Gate", ""])
            for criterion in delete_gate:
                lines.append(f"- {criterion}")

        lines.extend(
            [
                "",
                "### Runtime-Owned Caller Map",
                "",
                *_render_table(
                    [
                        "Order",
                        "Caller",
                        "Implementation",
                        "Runtime cutover",
                        "Sync strategy",
                        "Runtime target",
                        "Content sync",
                        "Rollback target",
                        "Observed `:8760` ref",
                        "Ask-first",
                    ],
                    [
                        [
                            f"`{caller.get('sync_order') or 'unknown'}`",
                            f"`{caller.get('path')}`",
                            f"`{caller.get('implementation_state') or 'unknown'}`",
                            f"`{caller.get('runtime_cutover_state') or 'unknown'}`",
                            f"`{caller.get('sync_strategy') or 'unknown'}`",
                            f"`{caller.get('runtime_owner_path')}`" if caller.get("runtime_owner_path") else "unset",
                            f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('content_state') or 'unknown'}`",
                            f"`{caller.get('rollback_target')}`" if caller.get("rollback_target") else "unset",
                            f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('observed_in_runtime_probe')}`",
                            f"`{caller.get('ask_first_required')}`",
                        ]
                        for caller in callers
                    ],
                ),
            ]
        )
        lines.extend(
            [
                "",
                "### Runtime Sync Verification Checklist",
                "",
                *_render_table(
                    [
                        "Order",
                        "Caller",
                        "Sync decision",
                        "Implementation source",
                        "Runtime target",
                        "Backup target",
                        "Rollback ready",
                    ],
                    [
                        [
                            f"`{caller.get('sync_order') or 'unknown'}`",
                            f"`{caller.get('path')}`",
                            f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('sync_decision') or 'unknown'}`",
                            (
                                f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('implementation_path')}`"
                                if live_content_records.get(str(caller.get("path") or ""), {}).get("implementation_path")
                                else "unset"
                            ),
                            (
                                f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('runtime_owner_path')}`"
                                if live_content_records.get(str(caller.get("path") or ""), {}).get("runtime_owner_path")
                                else "unset"
                            ),
                            (
                                f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('rollback_target')}`"
                                if live_content_records.get(str(caller.get("path") or ""), {}).get("rollback_target")
                                else "unset"
                            ),
                            f"`{live_content_records.get(str(caller.get('path') or ''), {}).get('rollback_ready')}`",
                        ]
                        for caller in callers
                    ],
                ),
            ]
        )

        for caller in callers:
            live_record = live_content_records.get(str(caller.get("path") or ""), {})
            runtime_owner_path = str(caller.get("runtime_owner_path") or "")
            rollback_target = str(caller.get("rollback_target") or "")
            content_state = str(live_record.get("content_state") or "unknown")
            if content_state == "content_drift":
                next_action = (
                    "Unexpected post-cutover drift; resync the runtime-owned file from implementation authority and reopen the migration seam."
                    if migration_retired
                    else "Back up the runtime-owned file, replace it from implementation authority, then rerun the live grep and journal checks."
                )
            elif content_state == "content_match":
                next_action = (
                    "Cutover is verified; no further runtime file action is required unless drift reappears."
                    if migration_retired
                    else "Content is already synced; verify the caller stops producing live :8760 traffic before disabling the facade."
                )
            elif content_state == "missing_runtime_file":
                next_action = (
                    "Confirm the runtime-owned file was intentionally removed as part of the retired seam."
                    if migration_retired
                    else "Confirm the runtime-owned file is intentionally absent before removing this caller from the migration seam."
                )
            elif content_state == "missing_implementation_file":
                next_action = "Confirm the implementation-authority file was intentionally retired before touching runtime state."
            else:
                next_action = (
                    "Refresh collector evidence and reopen the seam only if post-cutover drift is real."
                    if migration_retired
                    else "Refresh collector evidence, then decide whether to sync, retire, or remap this runtime caller."
                )
            lines.extend(
                [
                    "",
                    f"#### {caller.get('path')}",
                    "",
                    f"- Current purpose: {caller.get('current_purpose')}",
                    f"- Sync order: `{caller.get('sync_order')}`" if caller.get("sync_order") is not None else "- Sync order: `unset`",
                    f"- Canonical targets: {list_or_none(list(caller.get('canonical_targets', [])))}",
                    f"- Replacement owner paths: {list_or_none(list(caller.get('replacement_owner_paths', [])))}",
                    f"- Expected runtime owner path: `{runtime_owner_path}`" if runtime_owner_path else "- Expected runtime owner path: `unset`",
                    f"- Canonical replacement: {caller.get('canonical_replacement')}",
                    f"- Sync strategy: `{caller.get('sync_strategy') or 'unknown'}`",
                    f"- Sync decision: `{live_record.get('sync_decision') or 'unknown'}`",
                    f"- Rollback target: `{rollback_target}`" if rollback_target else "- Rollback target: `unset`",
                    f"- Rollback ready: `{live_record.get('rollback_ready')}`",
                    f"- Next action: {next_action}",
                    f"- Cutover check: {caller.get('cutover_check')}",
                    f"- Repo-side gates: {list_or_none(list(caller.get('repo_side_gates', [])))}",
                    f"- Runtime file: `{live_record.get('runtime_path')}`" if live_record.get("runtime_path") else "- Runtime file: `unset`",
                    f"- Runtime file exists: `{live_record.get('runtime_exists')}`",
                    f"- Runtime target matches registry: `{live_record.get('runtime_path_matches_registry')}`",
                    f"- Implementation file: `{live_record.get('implementation_path')}`" if live_record.get("implementation_path") else "- Implementation file: `unset`",
                    f"- Implementation file exists: `{live_record.get('implementation_exists')}`",
                    f"- Live content sync: `{live_record.get('content_state') or 'unknown'}`",
                    f"- Live `:8760` reference observed: `{live_record.get('observed_in_runtime_probe')}`",
                    f"- Runtime hash: {_short_hash(live_record.get('runtime_sha256'))}",
                    f"- Runtime size: `{live_record.get('runtime_size_bytes')}` bytes" if live_record.get("runtime_size_bytes") is not None else "- Runtime size: `unset`",
                    f"- Runtime lines: `{live_record.get('runtime_line_count')}`" if live_record.get("runtime_line_count") is not None else "- Runtime lines: `unset`",
                    f"- Implementation hash: {_short_hash(live_record.get('implementation_sha256'))}",
                    f"- Implementation size: `{live_record.get('implementation_size_bytes')}` bytes" if live_record.get("implementation_size_bytes") is not None else "- Implementation size: `unset`",
                    f"- Implementation lines: `{live_record.get('implementation_line_count')}`" if live_record.get("implementation_line_count") is not None else "- Implementation lines: `unset`",
                    f"- Notes: {list_or_none(list(caller.get('notes', [])))}",
                ]
            )
    lines.append("")
    return "\n".join(lines)


def render_runtime_cutover_packet() -> str:
    registry = load_registry("runtime-migration-registry.json")
    latest_snapshot = _load_latest_truth_snapshot()
    snapshot_collected_at = str(latest_snapshot.get("collected_at") or "") if isinstance(latest_snapshot, dict) else ""
    snapshot_governor_facade = _snapshot_governor_facade(latest_snapshot)
    migrations = sorted(
        list(registry.get("migrations", [])),
        key=lambda entry: (str(entry.get("status") or ""), str(entry.get("id") or "")),
    )
    all_retired = bool(migrations) and all(str(entry.get("status") or "") == "retired" for entry in migrations)
    lines = [
        "# Governor Facade Cutover Packet",
        "",
        "Generated from `config/automation-backbone/runtime-migration-registry.json` and the cached truth snapshot by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        (
            "This packet is retained as the verified record of the completed DEV `:8760` cutover. Use it to audit what was backed up, replaced, and verified, and only rerun the commands if drift reopens the seam."
            if all_retired
            else "This packet is the repo-safe execution guide for the DEV `:8760` maintenance window. It intentionally covers backup, replace, and verify steps only; use the retirement runbook for the actual stop or disable decision on `athanor-governor.service`."
        ),
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Cached truth snapshot: `{snapshot_collected_at or 'not available'}`",
        f"- Migrations included: `{len(migrations)}`",
        "",
    ]
    if not migrations:
        lines.extend(["No runtime migration seams are currently registered.", ""])
        return "\n".join(lines)

    live_content_records = {
        str(record.get("path") or ""): record
        for record in snapshot_governor_facade.get("caller_content_records", [])
        if isinstance(record, dict) and str(record.get("path") or "").strip()
    }
    journal_backup_target = None
    systemd_unit_name = "athanor-governor.service"
    if snapshot_governor_facade:
        systemd_matches = []
        for unit in snapshot_governor_facade.get("unit_matches", []):
            if isinstance(unit, dict):
                unit_name = str(unit.get("unit") or "").strip()
                if unit_name:
                    systemd_matches.append(unit_name)
                    continue
            unit_name = str(unit).strip()
            if unit_name:
                systemd_matches.append(unit_name)
        if systemd_matches:
            systemd_unit_name = systemd_matches[0]

    for migration in migrations:
        migration_retired = str(migration.get("status") or "") == "retired"
        runtime_backup_root = str(migration.get("runtime_backup_root") or "")
        systemd_backup_target = str(migration.get("systemd_backup_target") or "")
        journal_backup_target = (
            f"{runtime_backup_root.rstrip('/')}/{systemd_unit_name}.pre-cutover.journal.log"
            if runtime_backup_root
            else None
        )
        callers = sorted(
            list(migration.get("callers", [])),
            key=lambda caller: (int(caller.get("sync_order") or 9999), str(caller.get("path") or "")),
        )
        def packet_sync_decision(caller: dict[str, Any], live_record: dict[str, Any]) -> str:
            if migration_retired and str(caller.get("runtime_cutover_state") or "") == "cutover_verified":
                return "already_synced"
            return str(live_record.get("sync_decision") or "unknown")

        sync_required = sum(
            1
            for caller in callers
            if packet_sync_decision(
                caller,
                live_content_records.get(str(caller.get("path") or ""), {}),
            ).startswith(("backup_", "create_"))
        )
        lines.extend(
            [
                f"## {migration.get('id')}",
                "",
                f"- Status: `{migration.get('status')}`",
                f"- Runtime surface: `{migration.get('runtime_surface')}`",
                f"- Runtime owner: `{migration.get('runtime_owner')}`",
                f"- Runtime listener: `{migration.get('runtime_listener')}`",
                f"- Observed runtime repo head: `{migration.get('observed_runtime_repo_head')}`",
                f"- Sync-required callers: `{sync_required}`",
                f"- Runbook: [`{migration.get('runbook_path')}`](/C:/Athanor/{migration.get('runbook_path')})",
                f"- Companion report: [`{migration.get('generated_report_path')}`](/C:/Athanor/{migration.get('generated_report_path')})",
                "",
                "### Recorded Preflight Commands" if migration_retired else "### Preflight Commands",
                "",
                *_fenced_block(
                    "bash",
                    [
                        "python scripts/collect_truth_inventory.py",
                        "python scripts/generate_truth_inventory_reports.py --report runtime_migrations --report runtime_cutover --check",
                        "python scripts/validate_platform_contract.py",
                        f"ssh dev 'mkdir -p \"{runtime_backup_root}\"'" if runtime_backup_root else "# runtime backup root is unset in the registry",
                        (
                            f"ssh dev 'mkdir -p \"{PurePosixPath(systemd_backup_target).parent.as_posix()}\" && "
                            f"systemctl cat {systemd_unit_name} > \"{systemd_backup_target}\"'"
                            if systemd_backup_target
                            else "# systemd backup target is unset in the registry"
                        ),
                        (
                            f"ssh dev 'journalctl -u {systemd_unit_name} -n 400 --no-pager > \"{journal_backup_target}\"'"
                            if journal_backup_target
                            else "# journal backup target is unset because runtime backup root is missing"
                        ),
                    ],
                ),
                "",
                "### Recorded Caller Sync Commands" if migration_retired else "### Caller Sync Commands",
                "",
            ]
        )

        for caller in callers:
            caller_path = str(caller.get("path") or "")
            live_record = live_content_records.get(caller_path, {})
            sync_decision = packet_sync_decision(caller, live_record)
            runtime_target = str(live_record.get("runtime_owner_path") or caller.get("runtime_owner_path") or "")
            implementation_source = _slash_path(str(live_record.get("implementation_path") or (REPO_ROOT / caller_path)))
            rollback_target = str(live_record.get("rollback_target") or caller.get("rollback_target") or "")
            backup_dir = PurePosixPath(rollback_target).parent.as_posix() if rollback_target else runtime_backup_root
            replace_commands = []
            if backup_dir:
                replace_commands.append(f"ssh dev 'mkdir -p \"{backup_dir}\"'")
            if sync_decision == "backup_then_replace_runtime_copy":
                replace_commands.append(f"ssh dev 'cp \"{runtime_target}\" \"{rollback_target}\"'")
                replace_commands.append(f"scp \"{implementation_source}\" \"dev:{runtime_target}\"")
            elif sync_decision == "create_runtime_copy_after_backup_root_check":
                replace_commands.append(f"scp \"{implementation_source}\" \"dev:{runtime_target}\"")
            elif sync_decision == "already_synced":
                replace_commands.append(f"# {caller_path} already matches implementation authority; no file copy required.")
            else:
                replace_commands.append(f"# {caller_path} is blocked until implementation authority provides a valid replacement.")
            replace_commands.append(
                "ssh dev 'python3 - <<'\"'\"'PY'\"'\"'\n"
                "from pathlib import Path\n"
                f"path = Path(\"{runtime_target}\")\n"
                "text = path.read_text(encoding=\"utf-8\") if path.exists() else \"\"\n"
                "tokens = [\"127.0.0.1:8760\", \"localhost:8760\", \"/queue\", \"/dispatch-and-run\", \"ATHANOR_GOVERNOR_URL\"]\n"
                "hits = [token for token in tokens if token in text]\n"
                "print(hits if hits else \"clean\")\n"
                "PY'"
            )
            lines.extend(
                [
                    f"#### {caller_path}",
                    "",
                    f"- Sync order: `{caller.get('sync_order')}`",
                    f"- Sync decision: `{sync_decision}`",
                    f"- Runtime target: `{runtime_target}`" if runtime_target else "- Runtime target: `unset`",
                    f"- Backup target: `{rollback_target}`" if rollback_target else "- Backup target: `unset`",
                    f"- Rollback ready: `{live_record.get('rollback_ready')}`",
                    f"- Cutover check: {caller.get('cutover_check')}",
                    "",
                    *_fenced_block("bash", replace_commands),
                    "",
                ]
            )

        lines.extend(
            [
                "### Post-Cutover Verification Record" if migration_retired else "### Post-Sync Verification",
                "",
                *_fenced_block(
                    "bash",
                    [
                        "ssh dev 'grep -R \"127.0.0.1:8760\\|localhost:8760\\|/queue\\|/dispatch-and-run\\|ATHANOR_GOVERNOR_URL\" -n /home/shaun/repos/athanor/scripts /home/shaun/repos/athanor/services || true'",
                        f"ssh dev 'journalctl -u {systemd_unit_name} -n 200 --no-pager'",
                        f"ssh dev 'ss -ltnp | grep {migration.get('runtime_listener', '8760').rsplit(':', 1)[-1]} || true'",
                        "python scripts/collect_truth_inventory.py",
                        "python scripts/generate_truth_inventory_reports.py --report runtime_migrations --report runtime_cutover",
                        "python scripts/validate_platform_contract.py",
                    ],
                ),
                "",
                "### Runtime Retirement Status" if migration_retired else "### Service Stop Or Disable Decision",
                "",
                (
                    "The DEV runtime cutover is complete: `athanor-governor.service` is removed and no `:8760` listener remains. Use the retirement runbook only if drift reopens the seam and a rollback or re-cutover becomes necessary."
                    if migration_retired
                    else "Do not stop or disable `athanor-governor.service` from this packet alone. Use the acceptance checks and rollback sequence in [`docs/runbooks/governor-facade-retirement.md`](/C:/Athanor/docs/runbooks/governor-facade-retirement.md) after the file-sync phase is verified clean."
                ),
                "",
            ]
        )
    return "\n".join(lines)


def render_autonomy_activation_report() -> str:
    registry = load_registry("autonomy-activation-registry.json")
    latest_snapshot = _load_latest_truth_snapshot() or {}
    dev_runtime_probe = dict(latest_snapshot.get("dev_runtime_probe") or {})
    dev_runtime_detail = dict(dev_runtime_probe.get("detail") or {}) if isinstance(dev_runtime_probe.get("detail"), dict) else {}
    local_repo_probe = _local_git_probe(str(REPO_ROOT))
    current_phase_id = str(registry.get("current_phase_id") or "")
    phases = [
        dict(item)
        for item in registry.get("phases", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    phase_order = [str(item.get("id") or "").strip() for item in phases if str(item.get("id") or "").strip()]
    phase_index = {str(item.get("id")): item for item in phases}
    current_phase = dict(phase_index.get(current_phase_id) or {})
    try:
        current_phase_index = phase_order.index(current_phase_id)
    except ValueError:
        current_phase_index = -1
    next_phase = dict(phases[current_phase_index + 1]) if 0 <= current_phase_index < len(phases) - 1 else {}
    next_phase_id = str(next_phase.get("id") or "").strip()
    phase_rank = {phase_id: index for index, phase_id in enumerate(phase_order)}
    next_phase_index = phase_rank.get(next_phase_id)
    next_phase_blockers = []
    for item in registry.get("prerequisites", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").strip() == "verified":
            continue
        scope = str(item.get("phase_scope") or "").strip()
        if next_phase_index is None:
            continue
        if not scope:
            next_phase_blockers.append(dict(item))
            continue
        scope_index = phase_rank.get(scope)
        if scope_index is None or scope_index <= next_phase_index:
            next_phase_blockers.append(dict(item))
    lines = [
        "# Autonomy Activation Report",
        "",
        "Generated from `config/automation-backbone/autonomy-activation-registry.json` by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Status: `{registry.get('status', 'unknown')}`",
        f"- Activation state: `{registry.get('activation_state', 'unknown')}`",
        f"- Current phase: `{current_phase_id or 'unset'}`",
        f"- Current phase status: `{current_phase.get('status', 'unknown')}`",
        f"- Current phase scope: `{current_phase.get('scope', 'unknown')}`",
        f"- Next phase: `{next_phase_id or 'none'}`",
        f"- Next phase status: `{next_phase.get('status', 'complete') if next_phase_id else 'none'}`",
        f"- Next phase scope: `{next_phase.get('scope', 'n/a') if next_phase_id else 'n/a'}`",
        f"- Next phase blocker count: `{len(next_phase_blockers)}`",
        f"- Next phase blocker ids: {list_or_none([str(item.get('id') or '').strip() for item in next_phase_blockers if str(item.get('id') or '').strip()])}",
        f"- Broad autonomy enabled: `{registry.get('broad_autonomy_enabled', False)}`",
        f"- Runtime mutations approval gated: `{registry.get('runtime_mutations_approval_gated', True)}`",
        "",
    ]

    lines.extend(["## Next Promotion Boundary", ""])
    if next_phase_id:
        lines.extend(
            [
                f"- Next phase id: `{next_phase_id}`",
                f"- Label: `{next_phase.get('label', next_phase_id)}`",
                f"- Status: `{next_phase.get('status', 'unknown')}`",
                f"- Scope: `{next_phase.get('scope', 'unknown')}`",
                f"- Remaining blocker count: `{len(next_phase_blockers)}`",
                "",
            ]
        )
        if next_phase_blockers:
            blocker_rows = []
            for item in next_phase_blockers:
                blocker_rows.append(
                    [
                        f"`{item.get('id', 'unknown')}`",
                        f"`{item.get('status', 'unknown')}`",
                        f"`{item.get('phase_scope', 'unknown')}`",
                        list_or_none(list(item.get("evidence_paths", []))),
                    ]
                )
            lines.extend(_render_table(["Blocker", "Status", "Phase Scope", "Evidence"], blocker_rows))
            lines.append("")
            for item in next_phase_blockers:
                notes = [str(note).strip() for note in item.get("notes", []) if str(note).strip()]
                if not notes and str(item.get("id") or "") != "runtime_ownership_maturity":
                    continue
                lines.append(f"### {item.get('id', 'unknown')} detail")
                lines.append("")
                for note in notes:
                    lines.append(f"- {note}")
                if str(item.get("id") or "") == "runtime_ownership_maturity":
                    lines.append(f"- Implementation dirty file count: `{local_repo_probe.get('dirty_count', 0)}`")
                    if dev_runtime_probe.get("ok"):
                        lines.append(f"- DEV runtime dirty file count: `{dev_runtime_detail.get('repo_dirty_count', 0)}`")
                    else:
                        lines.append(f"- DEV runtime probe: `{dev_runtime_probe.get('detail') or 'unavailable'}`")
                lines.append("")
        else:
            lines.extend(["No remaining blockers are registered for the next phase.", ""])
    else:
        lines.extend(["No next phase is registered beyond the current active scope.", ""])

    prerequisites = [dict(item) for item in registry.get("prerequisites", []) if isinstance(item, dict)]
    lines.extend(["## Prerequisites", ""])
    if prerequisites:
        rows = []
        for item in prerequisites:
            rows.append(
                [
                    f"`{item.get('id', 'unknown')}`",
                    f"`{item.get('status', 'unknown')}`",
                    f"`{item.get('phase_scope', 'unknown')}`",
                    list_or_none(list(item.get("evidence_paths", []))),
                ]
            )
        lines.extend(_render_table(["Prerequisite", "Status", "Phase Scope", "Evidence"], rows))
        lines.append("")
    else:
        lines.extend(["No prerequisites are registered.", ""])

    approval_gates = [dict(item) for item in registry.get("approval_gates", []) if isinstance(item, dict)]
    lines.extend(["## Approval Gates", ""])
    if approval_gates:
        for gate in approval_gates:
            lines.extend(
                [
                    f"### {gate.get('label') or gate.get('id')}",
                    "",
                    f"- Gate id: `{gate.get('id', 'unknown')}`",
                    f"- Approval required: `{gate.get('approval_required', False)}`",
                    f"- Blocked actions: {list_or_none(list(gate.get('blocked_actions', [])))}",
                    "",
                ]
            )
    else:
        lines.extend(["No approval gates are registered.", ""])

    lines.extend(["## Phase Matrix", ""])
    if phases:
        rows = []
        for phase in phases:
            rows.append(
                [
                    f"`{phase.get('id', 'unknown')}`",
                    f"`{phase.get('status', 'unknown')}`",
                    f"`{phase.get('scope', 'unknown')}`",
                    list_or_none(list(phase.get("enabled_agents", []))),
                    list_or_none(list(phase.get("allowed_workload_classes", []))),
                ]
            )
        lines.extend(
            _render_table(
                ["Phase", "Status", "Scope", "Enabled Agents", "Allowed Workloads"],
                rows,
            )
        )
        lines.append("")
        for phase in phases:
            lines.extend(
                [
                    f"### {phase.get('label') or phase.get('id')}",
                    "",
                    f"- Phase id: `{phase.get('id', 'unknown')}`",
                    f"- Status: `{phase.get('status', 'unknown')}`",
                    f"- Scope: `{phase.get('scope', 'unknown')}`",
                    f"- Enabled agents: {list_or_none(list(phase.get('enabled_agents', [])))}",
                    f"- Allowed workload classes: {list_or_none(list(phase.get('allowed_workload_classes', [])))}",
                    f"- Blocked workload classes: {list_or_none(list(phase.get('blocked_workload_classes', [])))}",
                    f"- Allowed loop families: {list_or_none(list(phase.get('allowed_loop_families', [])))}",
                    f"- Blocked without approval: {list_or_none(list(phase.get('blocked_without_approval', [])))}",
                    f"- Entry criteria: {list_or_none(list(phase.get('entry_criteria', [])))}",
                    f"- Success criteria: {list_or_none(list(phase.get('success_criteria', [])))}",
                    "",
                ]
            )
    else:
        lines.extend(["No autonomy phases are registered.", ""])

    return "\n".join(lines)


def render_truth_drift_report() -> str:
    hardware = load_registry("hardware-inventory.json")
    models = load_registry("model-deployment-registry.json")
    providers = load_registry("provider-catalog.json")
    operator_surfaces = load_registry("operator-surface-registry.json")
    repo_roots = load_registry("repo-roots-registry.json")
    credential_surfaces = load_registry("credential-surface-registry.json")
    runtime_subsystems = load_registry("runtime-subsystem-registry.json")
    runtime_migrations = load_registry("runtime-migration-registry.json")
    drifts = collect_known_drifts(
        hardware,
        models,
        providers,
        operator_surfaces,
        repo_roots,
        credential_surfaces,
        runtime_subsystems,
        runtime_migrations,
    )
    deduped_drifts: list[dict[str, Any]] = []
    seen_drift_keys: set[tuple[str, str, str]] = set()
    for drift in drifts:
        key = (
            str(drift.get("id") or ""),
            str(drift.get("surface") or ""),
            str(drift.get("description") or ""),
        )
        if key in seen_drift_keys:
            continue
        seen_drift_keys.add(key)
        deduped_drifts.append(drift)
    drifts = deduped_drifts
    severity_counts = Counter(str(entry.get("severity") or "unknown") for entry in drifts)
    lines = [
        "# Truth Drift Report",
        "",
        "Generated from the truth-layer registries by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Drift items tracked: `{len(drifts)}`",
        "",
        *_render_table(
            ["Severity", "Count"],
            [[f"`{severity}`", str(count)] for severity, count in sorted(severity_counts.items())],
        ),
        "",
        "## Drift Items",
        "",
    ]
    if drifts:
        for drift in drifts:
            lines.append(f"- `{drift.get('id')}` on `{drift.get('surface')}`: {drift.get('description')}")
    else:
        lines.append("- No active drift items are currently recorded.")
    active_runtime_migrations = [
        migration for migration in runtime_migrations.get("migrations", []) if str(migration.get("status") or "") != "retired"
    ]
    retired_runtime_migrations = [
        migration for migration in runtime_migrations.get("migrations", []) if str(migration.get("status") or "") == "retired"
    ]
    if active_runtime_migrations:
        lines.extend(
            [
                "",
                "## Active Runtime Migration Seams",
                "",
                "Use [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) for the caller-by-caller cutover map.",
            ]
        )
    elif retired_runtime_migrations:
        lines.extend(
            [
                "",
                "## Retired Runtime Migration Seams",
                "",
                "The DEV governor-facade cutover is verified. Keep [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) as the audit trail and reopen the seam only if live drift reappears.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_vault_litellm_repair_packet() -> str:
    credential_surfaces = load_registry("credential-surface-registry.json")
    provider_catalog = load_registry("provider-catalog.json")
    latest_snapshot = _load_latest_truth_snapshot()
    snapshot_collected_at = str(latest_snapshot.get("collected_at") or "") if isinstance(latest_snapshot, dict) else ""
    vault_litellm_env_audit = _load_vault_litellm_env_audit(latest_snapshot)
    provider_usage_capture_index = _provider_usage_capture_index(load_optional_json(PROVIDER_USAGE_EVIDENCE_PATH))
    credential_env_names = _credential_env_names(credential_surfaces)
    vault_surface = next(
        (
            dict(surface)
            for surface in credential_surfaces.get("surfaces", [])
            if isinstance(surface, dict) and str(surface.get("id") or "") == "vault-litellm-container-env"
        ),
        {},
    )
    providers = [
        dict(provider)
        for provider in provider_catalog.get("providers", [])
        if isinstance(provider, dict) and str((dict(provider.get("evidence") or {}).get("kind") or "")) == "vault_litellm_proxy"
    ]
    launch_command = _vault_container_launch_command(vault_litellm_env_audit)
    auth_failed_rows: list[list[str]] = []
    partial_contract_rows: list[list[str]] = []
    observed_rows: list[list[str]] = []
    for provider in sorted(providers, key=lambda entry: str(entry.get("id") or "")):
        provider_id = str(provider.get("id") or "")
        provider_usage_capture = provider_usage_capture_index.get(provider_id, {})
        evidence_posture = _provider_evidence_posture(
            provider,
            tooling_entries=[],
            credential_env_names=credential_env_names,
            provider_usage_capture=provider_usage_capture,
        )
        proxy = dict(dict(provider.get("evidence") or {}).get("proxy") or {})
        alias = str(
            proxy.get("alias")
            or next((item for item in provider.get("litellm_aliases", []) if str(item).strip()), "")
            or provider_id
        )
        missing_names = _vault_env_names_for_provider(provider, vault_litellm_env_audit, "container_missing_env_names")
        present_names = _vault_env_names_for_provider(provider, vault_litellm_env_audit, "container_present_env_names")
        capture_observed_at = str(provider_usage_capture.get("observed_at") or provider_usage_capture.get("last_verified_at") or "")
        provider_verified_at = str(dict(provider.get("observed_runtime") or {}).get("last_verified_at") or "")
        latest_activity = capture_observed_at or provider_verified_at or "unknown"
        if evidence_posture == "vault_provider_specific_auth_failed":
            classification = _classify_vault_auth_failure(
                provider,
                provider_usage_capture,
                vault_litellm_env_audit,
            )
            auth_failed_rows.append(
                [
                    f"`{provider_id}`",
                    f"`{alias}`",
                    list_or_none(missing_names),
                    f"`{latest_activity}`",
                    classification["next_action"],
                ]
            )
            continue
        if missing_names:
            partial_contract_rows.append(
                [
                    f"`{provider_id}`",
                    f"`{alias}`",
                    list_or_none(present_names),
                    list_or_none(missing_names),
                    f"`{evidence_posture}`",
                    f"`{latest_activity}`",
                ]
            )
        if evidence_posture == "vault_provider_specific_api_observed":
            observed_rows.append(
                [
                    f"`{provider_id}`",
                    f"`{alias}`",
                    list_or_none(present_names),
                    f"`{latest_activity}`",
                ]
            )

    lines = [
        "# VAULT LiteLLM Auth Repair Packet",
        "",
        "Generated from `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/provider-catalog.json`, and the cached VAULT env-audit plus provider-usage artifacts by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "This packet is the repo-safe execution guide for an approved VAULT LiteLLM provider-auth maintenance window. It scopes the live work to the `litellm` container env surface only and keeps runtime mutation approval-gated.",
        "",
        f"- Credential surface version: `{credential_surfaces.get('version', 'unknown')}`",
        f"- Provider catalog version: `{provider_catalog.get('version', 'unknown')}`",
        f"- Cached truth snapshot: `{snapshot_collected_at or 'not available'}`",
        f"- Cached env audit: `{vault_litellm_env_audit.get('observed_at', 'not available')}`",
        f"- Surface id: `{vault_surface.get('id', 'vault-litellm-container-env')}`",
        f"- Host: `{vault_surface.get('host', 'vault')}`",
        f"- Runtime owner surface: `{vault_litellm_env_audit.get('runtime_owner_surface', 'unknown')}`",
        f"- Container: `{vault_litellm_env_audit.get('container_name', 'litellm')}`",
        f"- Container image: `{vault_litellm_env_audit.get('container_image', 'unknown')}`",
        f"- Restart policy: `{vault_litellm_env_audit.get('container_restart_policy', 'unknown')}`",
        f"- Env-change boundary: `{vault_litellm_env_audit.get('env_change_boundary', 'unknown')}`",
        f"- Config-only boundary: `{vault_litellm_env_audit.get('config_only_boundary', 'unknown')}`",
        f"- Launch command: `{launch_command}`" if launch_command else "- Launch command: `unknown`",
        f"- Managed source matches: docker template {list_or_none(vault_litellm_env_audit.get('docker_template_matches', []))}, compose manager {list_or_none(vault_litellm_env_audit.get('compose_manager_matches', []))}",
        f"- docker.config.json template mapping: `{vault_litellm_env_audit.get('docker_config_template_mapping')}`"
        if vault_litellm_env_audit.get("docker_config_template_mapping") is not None
        else "- docker.config.json template mapping: `none`",
        f"- container-watchdog monitors litellm: `{str(bool(vault_litellm_env_audit.get('container_watchdog_monitored'))).lower()}`",
        f"- Boot-config references: {list_or_none(vault_litellm_env_audit.get('boot_config_reference_files', []))}",
        f"- Detailed runbook: [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md)",
        f"- Companion reports: [PROVIDER-CATALOG-REPORT.md](/C:/Athanor/docs/operations/PROVIDER-CATALOG-REPORT.md), [SECRET-SURFACE-REPORT.md](/C:/Athanor/docs/operations/SECRET-SURFACE-REPORT.md)",
        "",
        "## Current Runtime Truth",
        "",
        f"- Container envs present: {list_or_none(vault_litellm_env_audit.get('container_present_env_names', []))}",
        f"- Container envs missing: {list_or_none(vault_litellm_env_audit.get('container_missing_env_names', []))}",
        f"- Host shell envs present: {list_or_none(vault_litellm_env_audit.get('host_shell_present_env_names', []))}",
        f"- Host shell envs missing: {list_or_none(vault_litellm_env_audit.get('host_shell_missing_env_names', []))}",
        f"- Runtime appdata files: {list_or_none(vault_litellm_env_audit.get('appdata_files', []))}",
        (
            "- Historical inspect backups: "
            + "; ".join(
                f"`{entry.get('path', 'unknown')}` -> {list_or_none(entry.get('env_names', []))}"
                for entry in vault_litellm_env_audit.get("historical_backup_env_snapshots", [])
                if isinstance(entry, dict)
            )
            if vault_litellm_env_audit.get("historical_backup_env_snapshots")
            else "- Historical inspect backups: none"
        ),
        "",
        "## Auth-Failed Provider Lanes",
        "",
    ]
    if auth_failed_rows:
        lines.extend(
            _render_table(
                ["Provider", "Served alias", "Missing env names", "Latest auth failure", "Next live action"],
                auth_failed_rows,
            )
        )
    else:
        lines.append("No VAULT LiteLLM providers are currently classified as `vault_provider_specific_auth_failed`.")

    lines.extend(["", "## Partial Contract Gaps Without Current Auth Failure", ""])
    if partial_contract_rows:
        lines.extend(
            _render_table(
                ["Provider", "Served alias", "Present env names", "Missing env names", "Current posture", "Latest verification"],
                partial_contract_rows,
            )
        )
    else:
        lines.append("No additional provider lanes currently show partial env-contract gaps.")

    lines.extend(["", "## Already Proven Provider Lanes", ""])
    if observed_rows:
        lines.extend(_render_table(["Provider", "Served alias", "Present env names", "Latest proof"], observed_rows))
    else:
        lines.append("No VAULT LiteLLM providers are currently classified as provider-specifically observed.")

    lines.extend(
        [
            "",
            "## Approved Maintenance Sequence",
            "",
            "1. Refresh the live env audit and confirm the current missing env-name set before touching VAULT runtime state.",
            "2. Use the `Auth-Failed Provider Lanes` table to limit changes to the exact missing provider env names instead of changing unrelated LiteLLM settings.",
            "3. Back up the live `litellm` container metadata and the current config bind-mount file before editing the runtime-managed env surface.",
            "4. Add or restore only the missing provider env names in the managed VAULT secret source. Do not print values to shell history or tracked files.",
            "5. Recreate or redeploy only the `litellm` container so the updated env set is applied. Use `docker restart litellm` only when the config file changed and the env set did not.",
            "6. Re-run the env audit, provider-specific probe, truth collector, and generated reports so the provider and secret-surface reports reflect the new posture immediately.",
            "",
            "## Backup Commands",
            "",
            *_fenced_block(
                "powershell",
                [
                    "python scripts/vault-ssh.py \"mkdir -p /mnt/user/appdata/litellm/backups\"",
                    "python scripts/vault-ssh.py \"docker inspect litellm > /mnt/user/appdata/litellm/backups/litellm.inspect.$(date +%Y%m%d-%H%M%S).json\"",
                    "python scripts/vault-ssh.py \"cp /mnt/user/appdata/litellm/config.yaml /mnt/user/appdata/litellm/backups/config.yaml.$(date +%Y%m%d-%H%M%S).bak\"",
                ],
            ),
            "",
            "## Read-Only Verification Commands",
            "",
            *_fenced_block(
                "powershell",
                [
                    "python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json",
                    "python scripts/probe_provider_usage_evidence.py --all-vault-proxy",
                    "python scripts/collect_truth_inventory.py",
                    "python scripts/generate_truth_inventory_reports.py --report providers --report secret_surfaces --report vault_litellm_repair_packet",
                    "python scripts/validate_platform_contract.py",
                ],
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_vault_redis_repair_packet() -> str:
    latest_snapshot = _load_latest_truth_snapshot()
    snapshot_collected_at = str(latest_snapshot.get("collected_at") or "") if isinstance(latest_snapshot, dict) else ""
    vault_redis_audit = _load_vault_redis_audit(latest_snapshot)
    filesystem = dict(vault_redis_audit.get("filesystem") or {})
    btrfs_usage = dict(vault_redis_audit.get("btrfs_usage") or {})
    appdatacache_top_consumers = [
        item for item in vault_redis_audit.get("appdatacache_top_consumers", []) if isinstance(item, dict)
    ]
    appdata_top_consumers = [item for item in vault_redis_audit.get("appdata_top_consumers", []) if isinstance(item, dict)]
    backup_file_top_consumers = [
        item for item in vault_redis_audit.get("backup_file_top_consumers", []) if isinstance(item, dict)
    ]
    stash_generated_top_consumers = [
        item for item in vault_redis_audit.get("stash_generated_top_consumers", []) if isinstance(item, dict)
    ]
    comfyui_model_top_consumers = [
        item for item in vault_redis_audit.get("comfyui_model_top_consumers", []) if isinstance(item, dict)
    ]
    lines = [
        "# VAULT Redis Repair Packet",
        "",
        "Generated from the cached truth snapshot plus the read-only VAULT Redis audit by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        f"- Cached truth snapshot: `{snapshot_collected_at or 'not available'}`",
        f"- Cached redis audit: `{vault_redis_audit.get('observed_at', 'not available')}`",
        f"- Surface id: `{vault_redis_audit.get('surface_id', 'vault-redis-persistence')}`",
        f"- Host: `{vault_redis_audit.get('host', 'vault')}`",
        f"- Runtime owner surface: `{vault_redis_audit.get('runtime_owner_surface', 'unknown')}`",
        f"- Container: `{vault_redis_audit.get('container_name', 'redis')}`",
        f"- Container image: `{vault_redis_audit.get('container_image', 'unknown')}`",
        f"- Restart policy: `{vault_redis_audit.get('container_restart_policy', 'unknown')}`",
        f"- Data mount source: `{vault_redis_audit.get('data_mount_source', 'unknown')}`",
        f"- Data mount destination: `{vault_redis_audit.get('data_mount_destination', '/data')}`",
        f"- Reconciliation runbook: [redis-reconciliation.md](/C:/Athanor/docs/runbooks/redis-reconciliation.md)",
        f"- Companion snapshot: [latest.json](/C:/Athanor/reports/truth-inventory/latest.json)",
        "",
        "## Current Runtime Truth",
        "",
        f"- Persistence blocker code: `{vault_redis_audit.get('persistence_blocker_code', 'unknown')}`",
        f"- Persistence blocker detail: {vault_redis_audit.get('persistence_blocker_detail', 'unknown')}",
        f"- Latest temp-RDB no-space error: `{vault_redis_audit.get('latest_no_space_error_at', 'unknown')}`",
        f"- Latest background-save error: `{vault_redis_audit.get('latest_background_save_error_at', 'unknown')}`",
        f"- Latest cross-protocol warning: `{vault_redis_audit.get('latest_security_attack_at', 'none')}`",
        f"- Temp-RDB no-space error count in audit tail: `{vault_redis_audit.get('no_space_error_count', 0)}`",
        f"- Background-save error count in audit tail: `{vault_redis_audit.get('background_save_error_count', 0)}`",
        f"- Cross-protocol warning count in audit tail: `{vault_redis_audit.get('security_attack_count', 0)}`",
        f"- Redis data directory size: `{_format_bytes(vault_redis_audit.get('redis_data_dir_size_bytes'))}`",
        f"- Filesystem device: `{filesystem.get('filesystem', 'unknown')}`",
        f"- Filesystem size: `{_format_bytes(filesystem.get('size_bytes'))}`",
        f"- Filesystem used: `{_format_bytes(filesystem.get('used_bytes'))}`",
        f"- Filesystem available: `{_format_bytes(filesystem.get('available_bytes'))}`",
        f"- Filesystem used percent: `{filesystem.get('used_percent', 'unknown')}`",
        f"- Filesystem mountpoint: `{filesystem.get('mountpoint', 'unknown')}`",
        f"- Btrfs device allocated: `{btrfs_usage.get('device_allocated', 'unknown')}`",
        f"- Btrfs device unallocated: `{btrfs_usage.get('device_unallocated', 'unknown')}`",
        f"- Btrfs free estimate: `{btrfs_usage.get('free_estimated', 'unknown')}`",
        f"- Next live action: {vault_redis_audit.get('operator_next_action', 'unknown')}",
        "",
        "## Largest Consumers On The Backing Filesystem",
        "",
        "### /mnt/appdatacache",
        "",
        *_render_size_rankings(
            appdatacache_top_consumers,
            empty_text="No appdatacache consumer census is available in the current audit.",
        ),
        "",
        "### /mnt/appdatacache/appdata",
        "",
        *_render_size_rankings(
            appdata_top_consumers,
            empty_text="No appdata consumer census is available in the current audit.",
        ),
        "",
        "### /mnt/appdatacache/backups (top files)",
        "",
        *_render_size_rankings(
            backup_file_top_consumers,
            empty_text="No backup-file census is available in the current audit.",
        ),
        "",
        "### /mnt/appdatacache/appdata/stash/generated",
        "",
        *_render_size_rankings(
            stash_generated_top_consumers,
            empty_text="No stash/generated consumer census is available in the current audit.",
        ),
        "",
        "### /mnt/appdatacache/models/comfyui",
        "",
        *_render_size_rankings(
            comfyui_model_top_consumers,
            empty_text="No ComfyUI model census is available in the current audit.",
        ),
        "",
        "## Interpretation",
        "",
        "The live blocker is not Redis logical drift. It is Redis persistence failure on VAULT: Redis cannot create temporary RDB files on the current `/data` backing store.",
        "The new storage census shows the pressure is not coming from Redis itself. Redis is roughly tens of megabytes, while the backing volume is dominated by `appdata`, `models`, `backups`, and `system`, and within `appdata` the largest paths are `stash`, `plex`, `tdarr`, `loki`, and `prometheus`.",
        "The current lowest-risk recovery candidates are the dated `backups` tarballs, especially the large `stash_*` and `plex_*` archives, because they can be moved or pruned before touching live `stash/generated` artifacts or live ComfyUI model weights.",
        "The repeated `Possible SECURITY ATTACK` warnings from FOUNDRY were a separate health-probe bug. Those warnings stopped after the agent health probe was changed to use a real Redis `PING`, so they are no longer the primary blocker.",
        "",
        "## Approved Maintenance Sequence",
        "",
        "1. Re-run the read-only Redis audit and confirm the blocker is still `rdb_temp_file_no_space` before touching VAULT runtime state.",
        "2. Confirm the `/data` bind mount and backing filesystem posture on VAULT, including current filesystem availability and Btrfs allocation state.",
        "3. Recover or expand allocatable space on the backing appdatacache filesystem. Start with the least disruptive high-yield targets in `/mnt/appdatacache/backups`, especially the dated `stash_*` and `plex_*` tarballs, before touching live `stash/generated` artifacts or live ComfyUI model weights.",
        "4. Once space has been recovered, verify Redis can create temp RDB files again and that `BGSAVE` or the next automatic save completes without `MISCONF`.",
        "5. Only if persistence remains blocked after space recovery, treat container relocation, bind-mount change, or Redis data-path reconfiguration as a separate approved maintenance step.",
        "6. Re-run the Redis audit, truth collector, generated reports, and live health probe so the dependency blocker clears from evidence instead of operator memory.",
        "",
        "## Read-Only Verification Commands",
        "",
        *_fenced_block(
            "powershell",
            [
                "python scripts/vault_redis_audit.py --write reports/truth-inventory/vault-redis-audit.json",
                "python scripts/collect_truth_inventory.py",
                "python scripts/generate_truth_inventory_reports.py --report vault_redis_repair_packet",
                "python scripts/validate_platform_contract.py",
                "ssh foundry \"curl -sS http://localhost:9000/health\"",
            ],
        ),
        "",
        "## Live Repair Commands To Use During The Approved Maintenance Window",
        "",
        *_fenced_block(
            "powershell",
            [
                "python scripts/vault-ssh.py \"docker inspect redis > /mnt/user/appdata/redis/redis.inspect.$(date +%Y%m%d-%H%M%S).json\"",
                "python scripts/vault-ssh.py \"df -h /mnt/appdatacache /mnt/appdatacache/appdata/redis\"",
                "python scripts/vault-ssh.py \"btrfs filesystem usage /mnt/appdatacache\"",
                "python scripts/vault-ssh.py \"du -x -B1 -d1 /mnt/appdatacache 2>/dev/null | sort -n | tail -12\"",
                "python scripts/vault-ssh.py \"du -x -B1 -d1 /mnt/appdatacache/appdata 2>/dev/null | sort -n | tail -15\"",
                "python scripts/vault-ssh.py \"du -sh /mnt/appdatacache/appdata/redis\"",
                "python scripts/vault-ssh.py \"docker exec redis redis-cli LASTSAVE\"",
                "python scripts/vault-ssh.py \"docker exec redis redis-cli INFO persistence\"",
            ],
        ),
        "",
    ]
    return "\n".join(lines)


def render_secret_surface_report() -> str:
    registry = load_registry("credential-surface-registry.json")
    latest_snapshot = _load_latest_truth_snapshot()
    vault_litellm_env_audit = _load_vault_litellm_env_audit(latest_snapshot)
    launch_command = _vault_container_launch_command(vault_litellm_env_audit)
    surfaces = list(registry.get("surfaces", []))
    remediation_counts = Counter(str(surface.get("remediation_state") or "unknown") for surface in surfaces)
    lines = [
        "# Secret Surface Report",
        "",
        "Generated from `config/automation-backbone/credential-surface-registry.json` plus the cached VAULT env audit artifact by `scripts/generate_truth_inventory_reports.py`.",
        "Do not edit manually.",
        "",
        "## Summary",
        "",
        f"- Registry version: `{registry.get('version', 'unknown')}`",
        f"- Surfaces tracked: `{len(surfaces)}`",
        (
            f"- VAULT LiteLLM env audit: `{vault_litellm_env_audit.get('collected_at', 'not available')}`"
            if vault_litellm_env_audit
            else "- VAULT LiteLLM env audit: `not available`"
        ),
        "",
        "### Remediation states",
        "",
        *_render_table(
            ["Remediation state", "Count"],
            [[f"`{state}`", str(count)] for state, count in sorted(remediation_counts.items())],
        ),
        "",
        *_render_table(
            ["Surface", "Host", "Delivery", "Target", "Risk", "Remediation"],
            [
                [
                    f"`{surface.get('id')}`",
                    f"`{surface.get('host')}`",
                    f"`{surface.get('delivery_method')}`",
                    f"`{surface.get('target_delivery_method')}`",
                    f"`{surface.get('risk_status')}`",
                    f"`{surface.get('remediation_state')}`",
                ]
                for surface in surfaces
            ],
        ),
    ]
    for surface in surfaces:
        surface_lines = [
            "",
            f"## {surface.get('id')}",
            "",
            f"- Path: `{surface.get('path')}`",
            f"- Owner surface: {surface.get('owner_surface')}",
            f"- Env contracts: {list_or_none(list(surface.get('env_var_names', [])))}",
            f"- Observed state: `{surface.get('observed_state')}`",
            f"- Target delivery: `{surface.get('target_delivery_method')}`",
            f"- Remediation state: `{surface.get('remediation_state')}`",
            f"- Ask-first required: `{surface.get('ask_first_required')}`",
            f"- Managed by: `{surface.get('managed_by')}`",
            f"- Evidence sources: {list_or_none(list(surface.get('evidence_sources', [])))}",
            f"- Recommended actions: {list_or_none(list(surface.get('recommended_actions', [])))}",
            f"- Notes: {list_or_none(list(surface.get('notes', [])))}",
        ]
        if str(surface.get("id") or "") == "vault-litellm-container-env" and vault_litellm_env_audit:
            surface_lines.extend(
                [
                    f"- Latest live env audit: `{vault_litellm_env_audit.get('collected_at', 'unknown')}`",
                    f"- Audit status: `{'ok' if vault_litellm_env_audit.get('ok') else 'failed'}`",
                    (
                        f"- Runtime owner surface: `{vault_litellm_env_audit.get('runtime_owner_surface')}`"
                        if vault_litellm_env_audit.get("runtime_owner_surface")
                        else "- Runtime owner surface: `unknown`"
                    ),
                    (
                        f"- Container image: `{vault_litellm_env_audit.get('container_image')}`"
                        if vault_litellm_env_audit.get("container_image")
                        else "- Container image: `unknown`"
                    ),
                    (
                        f"- Restart policy: `{vault_litellm_env_audit.get('container_restart_policy')}`"
                        if vault_litellm_env_audit.get("container_restart_policy")
                        else "- Restart policy: `unknown`"
                    ),
                    f"- Env-change boundary: `{vault_litellm_env_audit.get('env_change_boundary', 'unknown')}`",
                    f"- Config-only boundary: `{vault_litellm_env_audit.get('config_only_boundary', 'unknown')}`",
                    f"- Container envs present: {list_or_none(list(vault_litellm_env_audit.get('container_present_env_names', [])))}",
                    f"- Container envs missing: {list_or_none(list(vault_litellm_env_audit.get('container_missing_env_names', [])))}",
                    f"- Host shell envs present: {list_or_none(list(vault_litellm_env_audit.get('host_shell_present_env_names', [])))}",
                    f"- Host shell envs missing: {list_or_none(list(vault_litellm_env_audit.get('host_shell_missing_env_names', [])))}",
                    f"- dockerMan template matches: {list_or_none(list(vault_litellm_env_audit.get('docker_template_matches', [])))}",
                    f"- Compose-manager matches: {list_or_none(list(vault_litellm_env_audit.get('compose_manager_matches', [])))}",
                    (
                        f"- docker.config.json template mapping: `{vault_litellm_env_audit.get('docker_config_template_mapping')}`"
                        if vault_litellm_env_audit.get("docker_config_template_mapping") is not None
                        else "- docker.config.json template mapping: `none`"
                    ),
                    f"- container-watchdog monitors litellm: `{str(bool(vault_litellm_env_audit.get('container_watchdog_monitored'))).lower()}`",
                    f"- Boot-config references: {list_or_none(list(vault_litellm_env_audit.get('boot_config_reference_files', [])))}",
                    f"- Container launch command: `{launch_command}`" if launch_command else "- Container launch command: `unknown`",
                    f"- Appdata files: {list_or_none(list(vault_litellm_env_audit.get('appdata_files', [])))}",
                    (
                        "- Historical inspect backups: "
                        + "; ".join(
                            f"`{entry.get('path', 'unknown')}` -> {list_or_none(entry.get('env_names', []))}"
                            for entry in vault_litellm_env_audit.get("historical_backup_env_snapshots", [])
                            if isinstance(entry, dict)
                        )
                        if vault_litellm_env_audit.get("historical_backup_env_snapshots")
                        else "- Historical inspect backups: none"
                    ),
                    "- Repair packet: [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md)",
                ]
            )
            if vault_litellm_env_audit.get("error"):
                surface_lines.append(f"- Audit error: `{vault_litellm_env_audit.get('error')}`")
        lines.extend(
            surface_lines
        )
    drifts = list(registry.get("known_drifts", []))
    if drifts:
        lines.extend(["", "## Known Drift", ""])
        for drift in drifts:
            lines.append(f"- `{drift.get('id')}` ({drift.get('severity')}): {drift.get('description')}")
    lines.append("")
    return "\n".join(lines)


def render_dashboard_operator_surfaces() -> str:
    registry = load_registry("operator-surface-registry.json")
    surfaces = [dict(entry) for entry in registry.get("surfaces", []) if isinstance(entry, dict)]
    front_door = next(
        (
            entry
            for entry in surfaces
            if str(entry.get("id") or "").strip() == str(registry.get("front_door_contract", {}).get("canonical_portal_id") or "").strip()
        ),
        {},
    )
    launchpad_surfaces = [
        entry
        for entry in surfaces
        if str(entry.get("navigation_role") or "").strip() == "launchpad"
        and str(entry.get("surface_kind") or "").strip() in {"specialist_tool", "domain_app"}
        and str(entry.get("status") or "").strip() in {"active_specialist", "active_domain"}
    ]
    launchpad_surfaces.sort(key=lambda entry: (str(entry.get("operator_role") or ""), str(entry.get("label") or "")))
    external_tools = [
        {
            "id": str(entry.get("id") or "").strip(),
            "label": str(entry.get("label") or "").strip(),
            "description": _surface_description(entry),
            "url": str(entry.get("canonical_url") or "").strip(),
            "node": _surface_node_label(str(entry.get("node") or "").strip()),
            "category": _surface_category(str(entry.get("operator_role") or "").strip()),
            "operatorRole": str(entry.get("operator_role") or "").strip(),
            "status": str(entry.get("status") or "").strip(),
        }
        for entry in launchpad_surfaces
        if str(entry.get("id") or "").strip() and str(entry.get("canonical_url") or "").strip()
    ]
    quick_links = [
        {
            "name": str(entry["label"]),
            "url": str(entry["url"]),
            "node": str(entry["node"]),
            "category": str(entry["category"]),
        }
        for entry in external_tools
    ]
    payload = {
        "generatedAt": str(registry.get("updated_at") or ""),
        "sourceOfTruth": "config/automation-backbone/operator-surface-registry.json",
        "frontDoor": {
            "id": str(front_door.get("id") or "").strip(),
            "label": str(front_door.get("label") or "").strip(),
            "canonicalUrl": str(front_door.get("canonical_url") or "").strip(),
            "runtimeUrl": str(front_door.get("runtime_url") or "").strip(),
            "node": _surface_node_label(str(front_door.get("node") or "").strip()),
            "status": str(front_door.get("status") or "").strip(),
            "deploymentMode": str(front_door.get("deployment_mode") or "").strip(),
            "targetDeploymentMode": str(front_door.get("target_deployment_mode") or "").strip(),
            "description": _surface_description(front_door),
        },
        "externalTools": external_tools,
        "quickLinks": quick_links,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


REPORT_RENDERERS = {
    "hardware": render_hardware_report,
    "models": render_model_report,
    "providers": render_provider_report,
    "operator_surfaces": render_operator_surface_report,
    "tooling": render_tooling_report,
    "repo_roots": render_repo_roots_report,
    "runtime_ownership": render_runtime_ownership_report,
    "runtime_ownership_packets": render_runtime_ownership_packets_report,
    "runtime_migrations": render_runtime_migration_report,
    "runtime_cutover": render_runtime_cutover_packet,
    "vault_litellm_repair_packet": render_vault_litellm_repair_packet,
    "vault_redis_repair_packet": render_vault_redis_repair_packet,
    "autonomy_activation": render_autonomy_activation_report,
    "drift": render_truth_drift_report,
    "secret_surfaces": render_secret_surface_report,
}

GENERATED_ARTIFACT_RENDERERS = {
    "operator_surfaces": (DASHBOARD_OPERATOR_SURFACES_PATH, render_dashboard_operator_surfaces),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        action="append",
        choices=sorted(REPORT_RENDERERS.keys()),
        help="Report id to generate. Defaults to all reports.",
    )
    parser.add_argument("--check", action="store_true", help="Fail if generated output is stale.")
    args = parser.parse_args()

    report_ids = args.report or list(REPORT_RENDERERS.keys())
    stale: list[str] = []
    for report_id in report_ids:
        output_path = REPORT_PATHS[report_id]
        rendered = REPORT_RENDERERS[report_id]()
        if args.check:
            existing = (
                output_path.read_text(encoding="utf-8").replace("\r\n", "\n")
                if output_path.exists()
                else ""
            )
            if _report_is_stale(report_id, existing=existing, rendered=rendered):
                stale.append(output_path.relative_to(REPO_ROOT).as_posix())
        else:
            output_path.write_text(rendered, encoding="utf-8", newline="\n")
            print(f"Wrote {output_path.relative_to(REPO_ROOT).as_posix()}")

        artifact_renderer = GENERATED_ARTIFACT_RENDERERS.get(report_id)
        if artifact_renderer is None:
            continue
        artifact_path, render_artifact = artifact_renderer
        rendered_artifact = render_artifact()
        if args.check:
            existing_artifact = (
                artifact_path.read_text(encoding="utf-8").replace("\r\n", "\n")
                if artifact_path.exists()
                else ""
            )
            if existing_artifact != rendered_artifact:
                stale.append(artifact_path.relative_to(REPO_ROOT).as_posix())
            continue
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(rendered_artifact, encoding="utf-8", newline="\n")
        print(f"Wrote {artifact_path.relative_to(REPO_ROOT).as_posix()}")

    if stale:
        for path in stale:
            print(f"{path} is stale")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
