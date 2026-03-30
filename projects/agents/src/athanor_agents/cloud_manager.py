"""Cloud Manager — scheduled CLI sessions and multi-CLI dispatch coordination.

Manages the three-tier command hierarchy:
- Tier 1: Meta-orchestrator (local Qwen3.5-27B for real-time, Claude Code CLI for planning)
- Tier 2: Subscription CLIs (Codex, Gemini, Aider) for review/debug/audit
- Tier 3: Local workforce (9 agents via LiteLLM)

All cloud interaction is via headless CLI dispatch (subscription-covered).
No per-token API calls. LiteLLM stays local-only.
"""

import json
import logging
import time
from typing import Any
from dataclasses import asdict, dataclass, field

from .model_governance import (
    get_provider_catalog_registry,
    get_subscription_burn_registry,
    get_tooling_inventory_registry,
)

logger = logging.getLogger(__name__)

# Redis keys
DISPATCH_STATS_KEY = "athanor:dispatch:cli_stats"
DISPATCH_QUEUE_KEY = "athanor:dispatch:queue"
DISPATCH_RESULTS_KEY = "athanor:dispatch:results"
MANAGER_SESSIONS_KEY = "athanor:manager:sessions"

RESULTS_MAX = 200
SESSIONS_MAX = 50


@dataclass
class CLIDispatchRequest:
    """A request to dispatch work to a headless CLI tool."""
    id: str = ""
    task_id: str = ""
    cli_target: str = ""          # claude_code | codex_cli | gemini_cli | aider
    prompt: str = ""
    pattern: str = "direct"       # direct | quality_gate | consensus | auto_debug
    sandbox_mode: str = "read-only"  # read-only | workspace-write | full-auto
    priority: str = "normal"
    created_at: float = 0.0
    status: str = "pending"       # pending | dispatched | completed | failed
    result: str = ""
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ManagerSession:
    """Record of a scheduled manager session (morning/evening)."""
    id: str = ""
    session_type: str = ""        # morning | evening | escalation
    cli_tool: str = "claude_code"
    model: str = "opus"           # opus | sonnet
    started_at: float = 0.0
    completed_at: float | None = None
    tasks_reviewed: int = 0
    plans_approved: int = 0
    plans_rejected: int = 0
    decisions: list[dict] = field(default_factory=list)
    status: str = "pending"       # pending | running | completed | failed
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


COMPAT_CLI_ALIAS_BY_COMMAND = {
    "claude": "claude_code",
    "codex": "codex_cli",
    "gemini": "gemini_cli",
    "kimi": "kimi_code",
    "glm": "glm_coding",
    "zai": "glm_coding",
    "aider": "aider",
}


def _optional_int(value: Any) -> int | None:
    try:
        if value in ("", None):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _provider_catalog_index() -> dict[str, dict[str, Any]]:
    from . import model_governance

    providers = model_governance.get_provider_catalog_registry().get("providers", [])
    if not isinstance(providers, list):
        return {}
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in providers
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }


def _tooling_index() -> list[dict[str, Any]]:
    from . import model_governance

    indexed: list[dict[str, Any]] = []
    for host in model_governance.get_tooling_inventory_registry().get("hosts", []):
        if not isinstance(host, dict):
            continue
        host_id = str(host.get("id") or host.get("host") or "unknown").strip().lower()
        for tool in host.get("tools", []):
            if not isinstance(tool, dict):
                continue
            indexed.append(
                {
                    "host": host_id,
                    "provider_id": str(tool.get("provider_id") or "").strip(),
                    "command": str(tool.get("command") or "").strip(),
                    "status": str(tool.get("status") or "unknown").strip(),
                    "tool_id": str(tool.get("tool_id") or "").strip(),
                }
            )
    return indexed


def _burn_subscriptions() -> list[dict[str, Any]]:
    from . import model_governance

    subscriptions = model_governance.get_subscription_burn_registry().get("subscriptions", [])
    return [dict(entry) for entry in subscriptions if isinstance(entry, dict)]


def _stats_aliases_for_provider(provider_id: str) -> list[str]:
    aliases: list[str] = []
    provider = _provider_catalog_index().get(provider_id, {})
    for subscription in _burn_subscriptions():
        if str(subscription.get("provider_id") or "").strip() != provider_id:
            continue
        stats_key = str(subscription.get("stats_key") or "").strip()
        if stats_key and stats_key not in aliases:
            aliases.append(stats_key)
    for command in provider.get("cli_commands", []) or []:
        alias = COMPAT_CLI_ALIAS_BY_COMMAND.get(str(command).strip())
        if alias and alias not in aliases:
            aliases.append(alias)
    return aliases


def _daily_reset_config_by_stats_key() -> dict[str, dict[str, Any]]:
    config: dict[str, dict[str, Any]] = {}
    for subscription in _burn_subscriptions():
        stats_key = str(subscription.get("stats_key") or "").strip()
        if not stats_key:
            continue
        config[stats_key] = {
            "provider_id": str(subscription.get("provider_id") or "").strip(),
            "type": str(subscription.get("type") or "").strip(),
            "daily_limit": _optional_int(subscription.get("daily_limit")),
        }
    return config


def _compat_cli_defaults() -> dict[str, dict[str, Any]]:
    defaults: dict[str, dict[str, Any]] = {}

    def ensure(alias: str) -> dict[str, Any]:
        return defaults.setdefault(alias, {"available": False, "tasks_today": 0, "last_used": None})

    for subscription in _burn_subscriptions():
        stats_key = str(subscription.get("stats_key") or "").strip()
        if stats_key:
            ensure(stats_key)

    for provider_id, provider in _provider_catalog_index().items():
        if str(provider.get("access_mode") or "") != "cli":
            continue
        for alias in _stats_aliases_for_provider(provider_id):
            ensure(alias)

    for tool in _tooling_index():
        alias = COMPAT_CLI_ALIAS_BY_COMMAND.get(str(tool.get("command") or "").strip())
        if not alias:
            continue
        row = ensure(alias)
        if tool.get("status") == "installed":
            row["available"] = True

    return defaults


# ── CLI Status & Quota Tracking ──────────────────────────────────────

async def get_cli_status() -> dict:
    """Get CLI reachability and usage stats from Redis."""
    r = await _get_redis()
    raw = await r.hgetall(DISPATCH_STATS_KEY)
    stats = _compat_cli_defaults()
    observed_keys: set[str] = set()
    for k, v in raw.items():
        key = k if isinstance(k, str) else k.decode()
        observed_keys.add(key)
        val = v if isinstance(v, str) else v.decode()
        try:
            parsed = json.loads(val)
            base = dict(stats.get(key, {"available": False, "tasks_today": 0, "last_used": None}))
            if isinstance(parsed, dict):
                base.update(parsed)
                stats[key] = base
            else:
                stats[key] = parsed
        except (json.JSONDecodeError, TypeError):
            stats[key] = val
    for stats_key, config in _daily_reset_config_by_stats_key().items():
        if str(config.get("type") or "") != "daily_reset":
            continue
        row = stats.get(stats_key)
        if not isinstance(row, dict):
            continue
        daily_limit = _optional_int(config.get("daily_limit"))
        tasks_today = _optional_int(row.get("tasks_today"))
        if daily_limit is None or tasks_today is None:
            continue
        row["tasks_today"] = tasks_today
        if stats_key in observed_keys and row.get("quota_remaining") in ("", None):
            row["quota_remaining"] = max(daily_limit - tasks_today, 0)
    return stats


async def update_cli_stat(cli_name: str, field: str, value) -> None:
    """Update a CLI stat field in Redis."""
    r = await _get_redis()
    current = await r.hget(DISPATCH_STATS_KEY, cli_name)
    if current:
        data = json.loads(current if isinstance(current, str) else current.decode())
    else:
        data = dict(_compat_cli_defaults().get(cli_name, {"available": False, "tasks_today": 0, "last_used": None}))
    data[field] = value
    await r.hset(DISPATCH_STATS_KEY, cli_name, json.dumps(data))


async def record_cli_usage(cli_name: str, success: bool = True) -> None:
    """Record a CLI task execution."""
    r = await _get_redis()
    current = await r.hget(DISPATCH_STATS_KEY, cli_name)
    if current:
        data = json.loads(current if isinstance(current, str) else current.decode())
    else:
        data = dict(_compat_cli_defaults().get(cli_name, {"available": False, "tasks_today": 0, "last_used": None}))
    data["tasks_today"] = data.get("tasks_today", 0) + 1
    data["last_used"] = time.time()
    data["available"] = True
    burn_config = _daily_reset_config_by_stats_key().get(cli_name, {})
    if str(burn_config.get("type") or "") == "daily_reset":
        daily_limit = _optional_int(burn_config.get("daily_limit"))
        if daily_limit is not None:
            data["quota_remaining"] = max(daily_limit - _optional_int(data.get("tasks_today") or 0), 0)
    await r.hset(DISPATCH_STATS_KEY, cli_name, json.dumps(data))


async def reset_daily_stats() -> None:
    """Reset daily CLI usage counters (called at midnight)."""
    r = await _get_redis()
    burn_configs = _daily_reset_config_by_stats_key()
    cli_names = sorted(set(_compat_cli_defaults()) | set(burn_configs))
    for cli in cli_names:
        current = await r.hget(DISPATCH_STATS_KEY, cli)
        if current:
            data = json.loads(current if isinstance(current, str) else current.decode())
            data["tasks_today"] = 0
            burn_config = burn_configs.get(cli, {})
            daily_limit = _optional_int(burn_config.get("daily_limit"))
            if daily_limit is not None:
                data["quota_remaining"] = daily_limit
            elif "quota_remaining" in data:
                data.pop("quota_remaining", None)
            await r.hset(DISPATCH_STATS_KEY, cli, json.dumps(data))


# ── Dispatch Queue ───────────────────────────────────────────────────

async def enqueue_dispatch(request: CLIDispatchRequest) -> str:
    """Add a CLI dispatch request to the queue."""
    import uuid as _uuid
    if not request.id:
        request.id = f"disp-{_uuid.uuid4().hex[:8]}"
    request.created_at = time.time()
    request.status = "pending"

    r = await _get_redis()
    await r.lpush(DISPATCH_QUEUE_KEY, json.dumps(request.to_dict()))
    logger.info("Dispatch enqueued: %s → %s pattern=%s", request.id, request.cli_target, request.pattern)
    return request.id


async def get_dispatch_queue(limit: int = 20) -> list[dict]:
    """Get pending dispatch requests."""
    r = await _get_redis()
    items = await r.lrange(DISPATCH_QUEUE_KEY, 0, limit - 1)
    return [json.loads(i if isinstance(i, str) else i.decode()) for i in items]


async def record_dispatch_result(dispatch_id: str, result: str, success: bool) -> None:
    """Record a completed dispatch result."""
    r = await _get_redis()
    entry = {
        "dispatch_id": dispatch_id,
        "result": result[:2000],
        "success": success,
        "completed_at": time.time(),
    }
    await r.lpush(DISPATCH_RESULTS_KEY, json.dumps(entry))
    await r.ltrim(DISPATCH_RESULTS_KEY, 0, RESULTS_MAX - 1)


async def get_routing_log(limit: int = 30) -> list[dict]:
    """Get recent dispatch/routing decisions for the routing console."""
    r = await _get_redis()
    items = await r.lrange(DISPATCH_RESULTS_KEY, 0, limit - 1)
    return [json.loads(i if isinstance(i, str) else i.decode()) for i in items]


# ── Manager Sessions ─────────────────────────────────────────────────

async def record_session(session: ManagerSession) -> None:
    """Record a completed manager session."""
    r = await _get_redis()
    await r.lpush(MANAGER_SESSIONS_KEY, json.dumps(session.to_dict()))
    await r.ltrim(MANAGER_SESSIONS_KEY, 0, SESSIONS_MAX - 1)


async def get_recent_sessions(limit: int = 10) -> list[dict]:
    """Get recent manager sessions."""
    r = await _get_redis()
    items = await r.lrange(MANAGER_SESSIONS_KEY, 0, limit - 1)
    return [json.loads(i if isinstance(i, str) else i.decode()) for i in items]


# ── Quality Gate (Pattern 5) ────────────────────────────────────────

async def trigger_quality_gate(task_id: str, agent: str, output: str) -> str | None:
    """Enqueue a Gemini CLI quality review for a completed task.

    Returns dispatch ID if enqueued, None if not eligible.
    """
    from .policy_router import classify_policy
    policy = classify_policy(agent, "")

    if policy != "reviewable":
        return None

    request = CLIDispatchRequest(
        task_id=task_id,
        cli_target="gemini_cli",
        prompt=f"Review this agent output for quality, correctness, and completeness. "
               f"Score 0.0-1.0. Agent: {agent}. Output:\n\n{output[:4000]}",
        pattern="quality_gate",
        sandbox_mode="read-only",
        priority="normal",
    )
    return await enqueue_dispatch(request)


# ── Auto-Debug (Pattern 7) ──────────────────────────────────────────

async def trigger_auto_debug(task_id: str, error_msg: str, agent: str) -> str | None:
    """Enqueue a Codex CLI debug session for a failed task."""
    from .policy_router import classify_policy
    policy = classify_policy(agent, "")

    if policy != "reviewable":
        return None

    request = CLIDispatchRequest(
        task_id=task_id,
        cli_target="codex_cli",
        prompt=f"Debug this task failure. Agent: {agent}. Error:\n{error_msg[:2000]}\n\n"
               f"Diagnose root cause, suggest fix. Return JSON: "
               f'{{\"root_cause\": \"...\", \"suggested_fix\": \"...\", \"confidence\": 0.0-1.0}}',
        pattern="auto_debug",
        sandbox_mode="workspace-write",
        priority="high",
    )
    return await enqueue_dispatch(request)


# ── Consensus Review (Pattern 6) ────────────────────────────────────

async def trigger_consensus_review(task_id: str, description: str, files_changed: int) -> str | None:
    """Enqueue a 3-way CLI consensus review for significant changes."""
    if files_changed < 5:
        return None

    request = CLIDispatchRequest(
        task_id=task_id,
        cli_target="all_cli",
        prompt=f"Multi-model consensus review. Changes: {files_changed} files. "
               f"Description: {description[:1000]}. "
               f"Review for correctness, architecture alignment, and security.",
        pattern="consensus",
        sandbox_mode="read-only",
        priority="high",
    )
    return await enqueue_dispatch(request)


# ── Provider Status (for routing console) ───────────────────────────

async def get_provider_status() -> list[dict]:
    """Get provider status for the routing/models dashboard.

    This is a compatibility surface over the canonical provider-posture builder.
    Older UI surfaces still expect `status`, `tasks_today`, and `avg_latency_ms`,
    but the authoritative execution/cost/evidence fields come from the
    subscription summary and provider-execution posture.
    """
    from .provider_execution import build_provider_posture_records
    from .subscriptions import get_policy_snapshot

    cli_stats = await get_cli_status()
    policy = get_policy_snapshot()
    policy_providers = dict(policy.get("providers") or {})
    catalog_index = _provider_catalog_index()
    providers: list[dict[str, Any]] = []
    posture_records = await build_provider_posture_records(limit=25)

    for provider in posture_records:
        provider_id = str(provider.get("provider") or "")
        catalog_entry = catalog_index.get(provider_id, {})
        provider_meta = dict(policy_providers.get(provider_id) or {})
        stats_key = next(iter(_stats_aliases_for_provider(provider_id)), "")
        stats = dict(cli_stats.get(stats_key, {}))
        provider_state = str(provider.get("provider_state") or provider.get("availability") or "unknown")
        direct_execution_ready = bool(provider.get("direct_execution_ready"))
        governed_handoff_ready = bool(provider.get("governed_handoff_ready"))
        providers.append(
            {
                "id": provider_id,
                "name": str(provider.get("label") or catalog_entry.get("label") or provider_id),
                "status": provider_state,
                "subscription": str(provider.get("subscription_product") or catalog_entry.get("subscription_product") or ""),
                "monthly_cost": provider.get("catalog_monthly_cost_usd", catalog_entry.get("monthly_cost_usd")),
                "role": str(provider.get("reserve_state") or provider_meta.get("role") or provider.get("lane") or ""),
                "available": direct_execution_ready or governed_handoff_ready,
                "tasks_today": _optional_int(stats.get("tasks_today")),
                "avg_latency_ms": _optional_int(stats.get("avg_latency_ms")) or _optional_int(provider.get("avg_latency_ms")),
                "quota_remaining": _optional_int(stats.get("quota_remaining")),
                "last_used": stats.get("last_used"),
                "pricing_status": str(provider.get("catalog_pricing_status") or catalog_entry.get("official_pricing_status") or ""),
                "state_classes": list(provider.get("catalog_state_classes", catalog_entry.get("state_classes", [])) or []),
                "provider_state": provider_state,
                "routing_posture": str(provider.get("routing_posture") or ""),
                "routing_reason": str(provider.get("routing_reason") or ""),
                "state_reasons": list(provider.get("state_reasons", [])),
                "execution_mode": str(provider.get("execution_mode") or ""),
                "direct_execution_ready": direct_execution_ready,
                "governed_handoff_ready": governed_handoff_ready,
                "recent_execution_state": str(provider.get("recent_execution_state") or ""),
                "recent_execution_detail": str(provider.get("recent_execution_detail") or ""),
                "next_action": str(provider.get("next_action") or ""),
                "category": str(catalog_entry.get("category") or provider_meta.get("category") or ""),
            }
        )

    return providers
