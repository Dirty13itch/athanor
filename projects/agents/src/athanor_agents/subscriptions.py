from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import settings
from .model_governance import (
    get_credential_surface_registry,
    get_provider_catalog_registry,
    get_provider_usage_evidence_artifact,
    get_routing_taxonomy_map,
    get_subscription_burn_registry,
    get_tooling_inventory_registry,
)

LEASES_KEY = "athanor:subscriptions:leases"
PROVIDER_STATS_KEY = "athanor:subscriptions:provider-stats"
EVENTS_KEY = "athanor:subscriptions:events"
EVENT_LIMIT = 250

_POLICY_CACHE: dict[str, Any] | None = None
_POLICY_CACHE_MTIME_NS: int | None = None
_POLICY_CACHE_PATH: str | None = None

PROVIDER_SURFACES = {
    "athanor_local": "local_inference",
    "anthropic_claude_code": "claude_code",
    "openai_codex": "cloud_task",
    "google_gemini": "gemini_cli",
    "moonshot_kimi": "kimi_code",
    "zai_glm_coding": "glm_coding",
}

PRIVATE_SENSITIVITY = {"private", "secret", "lan_only"}


def _policy_path() -> Path:
    if settings.subscription_policy_path:
        return Path(settings.subscription_policy_path)
    return Path(__file__).resolve().parents[2] / "config" / "subscription-routing-policy.yaml"


def load_policy() -> dict[str, Any]:
    global _POLICY_CACHE
    global _POLICY_CACHE_MTIME_NS
    global _POLICY_CACHE_PATH

    path = _policy_path()
    if not path.exists():
        raise FileNotFoundError(f"Subscription policy not found at {path}")

    stat = path.stat()
    path_str = str(path)
    if (
        _POLICY_CACHE is not None
        and _POLICY_CACHE_PATH == path_str
        and _POLICY_CACHE_MTIME_NS == stat.st_mtime_ns
    ):
        return _POLICY_CACHE

    with path.open("r", encoding="utf-8") as handle:
        policy = yaml.safe_load(handle) or {}

    if not isinstance(policy, dict):
        raise ValueError(f"Subscription policy at {path} must be a mapping")

    policy.setdefault("providers", {})
    policy.setdefault("task_classes", {})
    policy.setdefault("agents", {})
    policy["_policy_source"] = path_str

    _POLICY_CACHE = policy
    _POLICY_CACHE_MTIME_NS = stat.st_mtime_ns
    _POLICY_CACHE_PATH = path_str
    return policy


@dataclass
class LeaseRequest:
    requester: str
    task_class: str
    sensitivity: str = "repo_internal"
    interactive: bool = False
    expected_context: str = "medium"
    parallelism: str = "low"
    priority: str = "normal"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionLease:
    id: str
    requester: str
    task_class: str
    provider: str
    surface: str
    privacy: str
    interactive: bool
    fallback: list[str]
    max_parallel_children: int
    reason: str
    created_at: float
    expires_at: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        ordered.append(item)
        seen.add(item)
    return ordered


def _provider_meta(policy: dict[str, Any], provider_id: str) -> dict[str, Any]:
    return dict(policy.get("providers", {}).get(provider_id, {}))


def _provider_catalog_index() -> dict[str, dict[str, Any]]:
    catalog = get_provider_catalog_registry()
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in catalog.get("providers", [])
        if str(entry.get("id") or "").strip()
    }


def _tooling_provider_index() -> dict[str, list[dict[str, str]]]:
    tooling = get_tooling_inventory_registry()
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


def _credential_env_names() -> set[str]:
    return {
        str(env_name)
        for surface in get_credential_surface_registry().get("surfaces", [])
        for env_name in surface.get("env_var_names", [])
        if str(env_name).strip()
    }


def _provider_usage_capture_index() -> dict[str, dict[str, Any]]:
    evidence_artifact = get_provider_usage_evidence_artifact()
    captures = evidence_artifact.get("captures", [])
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


def _provider_evidence_posture(
    provider: dict[str, Any],
    *,
    tooling_entries: list[dict[str, str]] | None = None,
    credential_env_names: set[str] | None = None,
    provider_usage_capture: dict[str, Any] | None = None,
) -> str:
    observed_runtime = dict(provider.get("observed_runtime") or {})
    evidence = dict(provider.get("evidence") or {})
    access_mode = str(provider.get("access_mode") or "")
    active_burn_observed = bool(observed_runtime.get("active_burn_observed"))
    routing_policy_enabled = bool(observed_runtime.get("routing_policy_enabled"))
    api_configured = bool(observed_runtime.get("api_configured"))
    pricing_status = str(provider.get("official_pricing_status") or "")
    monthly_cost = provider.get("monthly_cost_usd")
    evidence_kind = str(evidence.get("kind") or "")
    cli_probe = dict(evidence.get("cli_probe") or {})
    billing = dict(evidence.get("billing") or {})
    proxy_evidence = dict(evidence.get("proxy") or {})
    provider_specific_usage = dict(evidence.get("provider_specific_usage") or {})
    provider_usage_capture = dict(provider_usage_capture or {})
    cli_probe_status = str(cli_probe.get("status") or "")
    billing_status = str(billing.get("status") or "")
    provider_specific_status = str(provider_specific_usage.get("status") or "")
    capture_status = str(provider_usage_capture.get("status") or "")
    installed_tools = [
        entry for entry in (tooling_entries or []) if str(entry.get("status") or "") == "installed"
    ]
    degraded_tools = [
        entry for entry in (tooling_entries or []) if str(entry.get("status") or "") == "degraded"
    ]
    provider_envs = {str(item) for item in provider.get("env_contracts", []) if str(item).strip()}
    credential_surface_present = bool(provider_envs & (credential_env_names or set()))
    observed_hosts = {
        str(host).strip().lower()
        for host in provider.get("observed_hosts", [])
        if str(host).strip()
    }
    execution_modes = {
        str(item).strip()
        for item in provider.get("execution_modes", [])
        if str(item).strip()
    }
    proxy_activity_observed = bool(observed_runtime.get("proxy_activity_observed"))
    provider_specific_usage_observed = bool(observed_runtime.get("provider_specific_usage_observed"))

    if access_mode == "local" and routing_policy_enabled:
        return "local_runtime_available"
    if active_burn_observed:
        if monthly_cost is None and (
            "cost-unverified" in pricing_status
            or billing_status in {"operator_visible_tier_unverified", "official_docs_only_cost_unverified"}
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
    if access_mode == "api" and api_configured and "litellm_proxy" in execution_modes and "vault" in observed_hosts:
        if provider_specific_usage_observed or provider_specific_status in {"observed", "verified"} or capture_status in {"observed", "verified"}:
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
    monthly_cost = provider.get("monthly_cost_usd")
    if pricing_status == "not_applicable":
        return "not_applicable"
    if pricing_status == "metered":
        return "metered_api"
    if pricing_status == "official_verified" and monthly_cost is not None:
        return "verified_flat_rate"
    if pricing_status == "official-source-present-cost-unverified":
        return "flat_rate_unverified"
    if monthly_cost is None:
        return "unverified_or_metered"
    return pricing_status or "unknown"


def _enrich_provider_catalog_entry(
    provider: dict[str, Any],
    *,
    tooling_entries: list[dict[str, str]] | None = None,
    credential_env_names: set[str] | None = None,
    provider_usage_capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched = dict(provider)
    enriched["evidence_posture"] = _provider_evidence_posture(
        provider,
        tooling_entries=tooling_entries,
        credential_env_names=credential_env_names,
        provider_usage_capture=provider_usage_capture,
    )
    enriched["pricing_truth_label"] = _provider_pricing_truth_label(provider)
    if provider_usage_capture:
        enriched["provider_usage_capture"] = dict(provider_usage_capture)
    return enriched


def _agent_meta(policy: dict[str, Any], requester: str) -> dict[str, Any]:
    return dict(policy.get("agents", {}).get(requester, {}))


def _provider_selection_context(
    provider_id: str,
    *,
    provider_meta: dict[str, Any],
    provider_catalog_index: dict[str, dict[str, Any]],
    tooling_by_provider: dict[str, list[dict[str, str]]],
    credential_env_names: set[str],
) -> dict[str, Any]:
    catalog_entry = dict(provider_catalog_index.get(provider_id) or {})
    tooling_entries = tooling_by_provider.get(provider_id, [])
    enriched = (
        _enrich_provider_catalog_entry(
            catalog_entry,
            tooling_entries=tooling_entries,
            credential_env_names=credential_env_names,
        )
        if catalog_entry
        else {}
    )
    evidence_posture = str(enriched.get("evidence_posture") or "")
    execution_modes = {
        str(item).strip()
        for item in list(catalog_entry.get("execution_modes") or [])
        if str(item).strip()
    }
    routing_posture = str(provider_meta.get("routing_posture") or "ordinary_auto")
    routing_reason = str(provider_meta.get("routing_reason") or "")
    ordinary_routing_ready = evidence_posture in {
        "local_runtime_available",
        "live_burn_observed",
        "live_burn_observed_cost_unverified",
        "routing_enabled_cli_ready",
        "tool_installed_no_recent_burn",
    } and routing_posture == "ordinary_auto"
    return {
        "catalog": catalog_entry,
        "enriched": enriched,
        "evidence_posture": evidence_posture,
        "pricing_truth_label": str(enriched.get("pricing_truth_label") or ""),
        "routing_posture": routing_posture,
        "routing_reason": routing_reason,
        "policy_handoff_only": routing_posture == "governed_handoff_only",
        "ordinary_routing_ready": ordinary_routing_ready,
        "governed_handoff_ready": routing_posture in {"ordinary_auto", "governed_handoff_only"}
        and "handoff_bundle" in execution_modes,
    }


def _is_cloud_provider(policy: dict[str, Any], provider_id: str) -> bool:
    return _provider_meta(policy, provider_id).get("privacy", "cloud") == "cloud"


def _enabled_candidates(policy: dict[str, Any], task_class: str, requester: str) -> list[str]:
    task_meta = policy.get("task_classes", {}).get(task_class, {})
    ordered = _unique(list(task_meta.get("primary", [])) + list(task_meta.get("fallback", [])))
    allowed = set(_agent_meta(policy, requester).get("allowed_providers", ordered))
    candidates = []
    for provider_id in ordered:
        provider_meta = _provider_meta(policy, provider_id)
        if not provider_meta.get("enabled", True):
            continue
        if allowed and provider_id not in allowed:
            continue
        candidates.append(provider_id)
    return candidates


def infer_task_class(requester: str, prompt: str = "", metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    explicit = meta.get("task_class")
    if explicit:
        return str(explicit)

    lowered = prompt.lower()
    if requester == "research-agent":
        if any(term in lowered for term in ("repo audit", "codebase", "entire repo", "whole repo", "inventory", "diff all")):
            return "repo_wide_audit"
        return "search_heavy_planning"

    if requester == "coding-agent":
        if any(term in lowered for term in ("backlog", "queue", "ticket", "pull request", "pr-sized", "parallel")):
            return "async_backlog_execution"
        if any(term in lowered for term in ("bulk rename", "codemod", "mass edit", "transform all", "format all", "bulk transform")):
            return "cheap_bulk_transform"
        if any(term in lowered for term in ("design", "architecture", "adr", "tradeoff")):
            return "interactive_architecture"
        return "multi_file_implementation"

    return _agent_meta(load_policy(), requester).get("default_task_class", "private_internal_automation")


def _infer_expected_context(prompt: str, metadata: dict[str, Any]) -> str:
    explicit = metadata.get("expected_context")
    if explicit:
        return str(explicit)

    lowered = prompt.lower()
    if len(prompt) > 1200 or any(term in lowered for term in ("entire repo", "whole codebase", "across all files", "broad audit")):
        return "large"
    if len(prompt) > 400:
        return "medium"
    return "small"


def _infer_parallelism(priority: str, metadata: dict[str, Any]) -> str:
    explicit = metadata.get("parallelism")
    if explicit:
        return str(explicit)
    if priority in {"critical", "high"}:
        return "medium"
    return "low"


def build_task_lease_request(
    requester: str,
    prompt: str,
    priority: str = "normal",
    metadata: dict[str, Any] | None = None,
) -> LeaseRequest:
    policy = load_policy()
    meta = dict(metadata or {})
    agent_meta = _agent_meta(policy, requester)
    sensitivity = str(meta.get("sensitivity", agent_meta.get("sensitivity_default", "repo_internal")))
    interactive = bool(meta.get("interactive", False))
    task_class = infer_task_class(requester, prompt, meta)
    if "policy_class" not in meta or "meta_lane" not in meta:
        # Keep request metadata aligned with the command hierarchy so preview flows,
        # operator tests, and downstream routing all read the same governance hints.
        from .command_hierarchy import classify_policy_class

        classification = classify_policy_class(prompt, meta, task_class=task_class)
        meta.setdefault("policy_class", str(classification.get("policy_class") or "cloud_safe"))
        meta.setdefault("meta_lane", str(classification.get("meta_lane") or "frontier_cloud"))
    expected_context = _infer_expected_context(prompt, meta)
    parallelism = _infer_parallelism(priority, meta)
    return LeaseRequest(
        requester=requester,
        task_class=task_class,
        sensitivity=sensitivity,
        interactive=interactive,
        expected_context=expected_context,
        parallelism=parallelism,
        priority=priority,
        metadata=meta,
    )


def _score_provider(
    request: LeaseRequest,
    policy: dict[str, Any],
    provider_id: str,
    position: int,
    selection_context: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    score = 100 - (position * 10)
    reasons = [f"base_order={position + 1}"]
    provider_meta = _provider_meta(policy, provider_id)
    reserve = provider_meta.get("reserve", "")
    context = dict(selection_context or {})
    evidence_posture = str(context.get("evidence_posture") or "")
    ordinary_routing_ready = bool(context.get("ordinary_routing_ready"))
    governed_handoff_ready = bool(context.get("governed_handoff_ready"))

    if request.sensitivity in PRIVATE_SENSITIVITY:
        if _is_cloud_provider(policy, provider_id):
            score -= 200
            reasons.append("private_sensitivity_penalty")
        else:
            score += 40
            reasons.append("private_local_bonus")

    if not request.interactive and reserve == "premium_interactive":
        score -= 18
        reasons.append("preserve_interactive_quota")

    if request.interactive and provider_id == "anthropic_claude_code":
        score += 15
        reasons.append("interactive_lead_bonus")

    if request.expected_context == "large" and provider_id == "google_gemini":
        score += 18
        reasons.append("large_context_bonus")

    if request.parallelism in {"medium", "high"} and provider_id == "openai_codex":
        score += 12
        reasons.append("parallel_cloud_bonus")

    if request.task_class == "cheap_bulk_transform" and provider_id == "zai_glm_coding":
        score += 12
        reasons.append("bulk_transform_bonus")

    if request.task_class == "async_backlog_execution" and provider_id == "openai_codex":
        score += 16
        reasons.append("async_backlog_bonus")

    if request.task_class == "repo_wide_audit" and provider_id == "google_gemini":
        score += 12
        reasons.append("repo_audit_bonus")

    if request.requester == "research-agent" and provider_id == "moonshot_kimi":
        score += 6
        reasons.append("research_planning_bonus")

    if request.requester == "coding-agent" and not request.interactive and provider_id == "openai_codex":
        score += 8
        reasons.append("coding_background_bonus")

    if provider_id == "athanor_local":
        score += 4
        reasons.append("local_safety_bonus")

    if not ordinary_routing_ready:
        if governed_handoff_ready:
            score -= 30
            reasons.append("handoff_only_penalty")
        else:
            score -= 120
            reasons.append("no_verified_execution_path_penalty")
    elif evidence_posture in {"live_burn_observed", "live_burn_observed_cost_unverified"}:
        score += 6
        reasons.append("observed_lane_bonus")
    elif evidence_posture == "tool_installed_no_recent_burn":
        score += 2
        reasons.append("installed_tool_bonus")

    return score, reasons


def preview_execution_lease(request: LeaseRequest) -> ExecutionLease:
    policy = load_policy()
    task_class = request.task_class or infer_task_class(request.requester, metadata=request.metadata)
    candidates = _enabled_candidates(policy, task_class, request.requester)
    if not candidates:
        candidates = ["athanor_local"]

    provider_catalog_index = _provider_catalog_index()
    tooling_by_provider = _tooling_provider_index()
    credential_env_names = _credential_env_names()
    selection_contexts = {
        provider_id: _provider_selection_context(
            provider_id,
            provider_meta=_provider_meta(policy, provider_id),
            provider_catalog_index=provider_catalog_index,
            tooling_by_provider=tooling_by_provider,
            credential_env_names=credential_env_names,
        )
        for provider_id in candidates
    }
    allow_handoff_only = bool((request.metadata or {}).get("allow_handoff_only"))
    policy_handoff_only_candidates = [
        provider_id
        for provider_id, context in selection_contexts.items()
        if bool(context.get("policy_handoff_only"))
    ]
    evidence_unready_candidates = [
        provider_id
        for provider_id, context in selection_contexts.items()
        if not bool(context.get("ordinary_routing_ready")) and not bool(context.get("governed_handoff_ready"))
    ]
    excluded_candidates = [
        provider_id
        for provider_id, context in selection_contexts.items()
        if (
            (bool(context.get("policy_handoff_only")) and not allow_handoff_only)
            or (
                not bool(context.get("ordinary_routing_ready"))
                and not allow_handoff_only
                and not bool(context.get("policy_handoff_only"))
            )
            or (
                allow_handoff_only
                and not bool(context.get("ordinary_routing_ready"))
                and not bool(context.get("governed_handoff_ready"))
            )
        )
    ]
    eligible_candidates = [provider_id for provider_id in candidates if provider_id not in excluded_candidates]
    if eligible_candidates:
        candidates = eligible_candidates
    else:
        excluded_candidates = []

    scored = []
    for index, provider_id in enumerate(candidates):
        score, reasons = _score_provider(
            request,
            policy,
            provider_id,
            index,
            selection_context=selection_contexts.get(provider_id),
        )
        scored.append((score, provider_id, reasons))

    scored.sort(key=lambda item: item[0], reverse=True)
    _, provider_id, reasons = scored[0]
    fallback = [candidate for _, candidate, _ in scored[1:]]

    provider_meta = _provider_meta(policy, provider_id)
    selected_context = dict(selection_contexts.get(provider_id) or {})
    created_at = time.time()
    max_parallel_children = 1
    if request.parallelism == "medium":
        max_parallel_children = 3
    elif request.parallelism == "high":
        max_parallel_children = 5

    reason = (
        f"task_class={task_class}; requester={request.requester}; "
        f"selected={provider_id}; factors={', '.join(reasons[:4])}"
    )

    return ExecutionLease(
        id=f"lease-{uuid.uuid4().hex[:12]}",
        requester=request.requester,
        task_class=task_class,
        provider=provider_id,
        surface=PROVIDER_SURFACES.get(provider_id, "unknown"),
        privacy=str(provider_meta.get("privacy", "cloud")),
        interactive=request.interactive,
        fallback=fallback,
        max_parallel_children=max_parallel_children,
        reason=reason,
        created_at=created_at,
        expires_at=created_at + 3600,
        metadata={
            "priority": request.priority,
            "expected_context": request.expected_context,
            "parallelism": request.parallelism,
            "policy_source": policy.get("_policy_source", "unknown"),
            "provider_evidence_posture": str(selected_context.get("evidence_posture") or ""),
            "provider_pricing_truth_label": str(selected_context.get("pricing_truth_label") or ""),
            "provider_routing_posture": str(selected_context.get("routing_posture") or ""),
            "provider_routing_reason": str(selected_context.get("routing_reason") or ""),
            "provider_governed_handoff_ready": bool(selected_context.get("governed_handoff_ready")),
            "provider_ordinary_routing_ready": bool(selected_context.get("ordinary_routing_ready")),
            "excluded_handoff_only_providers": policy_handoff_only_candidates if not allow_handoff_only else [],
            "excluded_unready_providers": evidence_unready_candidates,
        },
    )


async def _get_redis():
    from .workspace import get_redis

    return await get_redis()


async def _record_provider_event(event: dict[str, Any]) -> None:
    redis = await _get_redis()
    await redis.lpush(EVENTS_KEY, json.dumps(event))
    await redis.ltrim(EVENTS_KEY, 0, EVENT_LIMIT - 1)


async def _update_provider_stats(provider_id: str, updater) -> None:
    redis = await _get_redis()
    raw = await redis.hget(PROVIDER_STATS_KEY, provider_id)
    stats = json.loads(raw) if raw else {
        "provider": provider_id,
        "leases_issued": 0,
        "outcomes": {},
        "throttle_events": 0,
        "last_issued_at": 0.0,
        "last_outcome_at": 0.0,
    }
    updater(stats)
    await redis.hset(PROVIDER_STATS_KEY, provider_id, json.dumps(stats))


async def issue_execution_lease(request: LeaseRequest) -> ExecutionLease:
    lease = preview_execution_lease(request)
    redis = await _get_redis()
    await redis.hset(LEASES_KEY, lease.id, json.dumps(lease.to_dict()))

    def mutate(stats: dict[str, Any]) -> None:
        stats["leases_issued"] = int(stats.get("leases_issued", 0)) + 1
        stats["last_issued_at"] = lease.created_at
        stats["last_task_class"] = lease.task_class

    await _update_provider_stats(lease.provider, mutate)
    await _record_provider_event(
        {
            "event": "lease_issued",
            "lease_id": lease.id,
            "provider": lease.provider,
            "requester": lease.requester,
            "task_class": lease.task_class,
            "timestamp": lease.created_at,
        }
    )
    return lease


async def attach_task_execution_lease(
    requester: str,
    prompt: str,
    priority: str = "normal",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(metadata or {})
    if meta.get("execution_lease"):
        return meta
    if requester not in {"coding-agent", "research-agent"}:
        return meta

    lease_request = build_task_lease_request(
        requester=requester,
        prompt=prompt,
        priority=priority,
        metadata=meta,
    )
    lease = await issue_execution_lease(lease_request)
    meta["execution_lease"] = lease.to_dict()
    return meta


async def list_execution_leases(requester: str = "", limit: int = 50) -> list[dict[str, Any]]:
    redis = await _get_redis()
    raw = await redis.hgetall(LEASES_KEY)
    leases = [json.loads(value) for value in raw.values()]
    if requester:
        leases = [lease for lease in leases if lease.get("requester") == requester]
    leases.sort(key=lambda lease: float(lease.get("created_at", 0.0)), reverse=True)
    return leases[:limit]


async def record_execution_outcome(
    lease_id: str,
    outcome: str,
    throttled: bool = False,
    notes: str = "",
    quality_score: float | None = None,
    latency_ms: int | None = None,
) -> dict[str, Any] | None:
    redis = await _get_redis()
    raw = await redis.hget(LEASES_KEY, lease_id)
    if not raw:
        return None

    lease = json.loads(raw)
    lease["outcome"] = outcome
    lease["throttled"] = throttled
    lease["notes"] = notes
    lease["quality_score"] = quality_score
    lease["latency_ms"] = latency_ms
    lease["completed_at"] = time.time()
    await redis.hset(LEASES_KEY, lease_id, json.dumps(lease))

    provider_id = lease["provider"]

    def mutate(stats: dict[str, Any]) -> None:
        outcomes = dict(stats.get("outcomes", {}))
        outcomes[outcome] = int(outcomes.get(outcome, 0)) + 1
        stats["outcomes"] = outcomes
        if throttled:
            stats["throttle_events"] = int(stats.get("throttle_events", 0)) + 1
        stats["last_outcome_at"] = lease["completed_at"]

    await _update_provider_stats(provider_id, mutate)
    await _record_provider_event(
        {
            "event": "lease_outcome",
            "lease_id": lease_id,
            "provider": provider_id,
            "outcome": outcome,
            "throttled": throttled,
            "timestamp": lease["completed_at"],
        }
    )
    return lease


async def get_quota_summary() -> dict[str, Any]:
    redis = await _get_redis()
    raw_stats = await redis.hgetall(PROVIDER_STATS_KEY)
    stats = {provider: json.loads(value) for provider, value in raw_stats.items()}
    raw_events = await redis.lrange(EVENTS_KEY, 0, 49)
    events = [json.loads(item) for item in raw_events]
    burn_registry = get_subscription_burn_registry()
    return {
        "policy_source": load_policy().get("_policy_source", "unknown"),
        "burn_registry_version": str(burn_registry.get("version") or ""),
        "burn_registry_source": str(burn_registry.get("source_of_truth") or ""),
        "providers": stats,
        "recent_events": events,
    }


def get_provider_catalog_snapshot(*, policy_only: bool = False) -> dict[str, Any]:
    catalog = get_provider_catalog_registry()
    tooling_by_provider = _tooling_provider_index()
    credential_env_names = _credential_env_names()
    provider_usage_capture_index = _provider_usage_capture_index()
    providers = [
        _enrich_provider_catalog_entry(
            dict(entry),
            tooling_entries=tooling_by_provider.get(str(entry.get("id") or ""), []),
            credential_env_names=credential_env_names,
            provider_usage_capture=provider_usage_capture_index.get(str(entry.get("id") or "")),
        )
        for entry in catalog.get("providers", [])
        if isinstance(entry, dict)
    ]
    if policy_only:
        allowed = {str(item) for item in dict(load_policy().get("providers") or {}).keys()}
        providers = [entry for entry in providers if str(entry.get("id") or "") in allowed]
    return {
        "version": str(catalog.get("version") or ""),
        "official_verified_at": str(catalog.get("official_verified_at") or ""),
        "providers": providers,
        "count": len(providers),
        "source_of_truth": str(catalog.get("source_of_truth") or ""),
    }


def get_policy_snapshot() -> dict[str, Any]:
    policy = load_policy()
    provider_catalog = get_provider_catalog_registry()
    routing_taxonomy = get_routing_taxonomy_map()
    return {
        "version": policy.get("version", 1),
        "updated": policy.get("updated", ""),
        "policy_source": policy.get("_policy_source", "unknown"),
        "provider_catalog_version": provider_catalog.get("version", ""),
        "routing_taxonomy_version": routing_taxonomy.get("version", ""),
        "providers": policy.get("providers", {}),
        "task_classes": policy.get("task_classes", {}),
        "agents": policy.get("agents", {}),
    }
