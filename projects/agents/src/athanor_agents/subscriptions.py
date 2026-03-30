from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import settings

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


def _agent_meta(policy: dict[str, Any], requester: str) -> dict[str, Any]:
    return dict(policy.get("agents", {}).get(requester, {}))


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
    task_class = infer_task_class(requester, prompt, meta)
    classification: dict[str, Any] = {}
    try:
        from .command_hierarchy import classify_policy_class

        classification = classify_policy_class(prompt, meta, task_class=task_class)
    except Exception:
        classification = {}

    if classification:
        meta.setdefault("policy_class", classification["policy_class"])
        meta.setdefault("meta_lane", classification["meta_lane"])
        meta.setdefault("cloud_allowed", classification["cloud_allowed"])

    sensitivity_default = agent_meta.get("sensitivity_default", "repo_internal")
    if "sensitivity" in meta:
        sensitivity = str(meta["sensitivity"])
    elif classification.get("requires_sovereign"):
        sensitivity = "lan_only"
    else:
        sensitivity = str(sensitivity_default)

    interactive = bool(meta.get("interactive", False))
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
) -> tuple[int, list[str]]:
    score = 100 - (position * 10)
    reasons = [f"base_order={position + 1}"]
    provider_meta = _provider_meta(policy, provider_id)
    reserve = provider_meta.get("reserve", "")

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

    return score, reasons


def preview_execution_lease(request: LeaseRequest) -> ExecutionLease:
    policy = load_policy()
    task_class = request.task_class or infer_task_class(request.requester, metadata=request.metadata)
    candidates = _enabled_candidates(policy, task_class, request.requester)
    if not candidates:
        candidates = ["athanor_local"]

    scored = []
    for index, provider_id in enumerate(candidates):
        score, reasons = _score_provider(request, policy, provider_id, index)
        scored.append((score, provider_id, reasons))

    scored.sort(key=lambda item: item[0], reverse=True)
    _, provider_id, reasons = scored[0]
    fallback = [candidate for _, candidate, _ in scored[1:]]

    provider_meta = _provider_meta(policy, provider_id)
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
    return {
        "policy_source": load_policy().get("_policy_source", "unknown"),
        "providers": stats,
        "recent_events": events,
    }


def get_policy_snapshot() -> dict[str, Any]:
    policy = load_policy()
    return {
        "version": policy.get("version", 1),
        "updated": policy.get("updated", ""),
        "policy_source": policy.get("_policy_source", "unknown"),
        "providers": policy.get("providers", {}),
        "task_classes": policy.get("task_classes", {}),
        "agents": policy.get("agents", {}),
    }
