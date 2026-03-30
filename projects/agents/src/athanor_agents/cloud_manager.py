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
from dataclasses import asdict, dataclass, field

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


# ── CLI Status & Quota Tracking ──────────────────────────────────────

async def get_cli_status() -> dict:
    """Get CLI reachability and usage stats from Redis."""
    r = await _get_redis()
    raw = await r.hgetall(DISPATCH_STATS_KEY)
    if not raw:
        return {
            "claude_code": {"available": False, "tasks_today": 0, "last_used": None},
            "codex_cli": {"available": False, "tasks_today": 0, "last_used": None},
            "gemini_cli": {"available": False, "tasks_today": 0, "quota_remaining": 1000, "last_used": None},
            "aider": {"available": True, "tasks_today": 0, "last_used": None},
        }
    stats = {}
    for k, v in raw.items():
        key = k if isinstance(k, str) else k.decode()
        val = v if isinstance(v, str) else v.decode()
        try:
            stats[key] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            stats[key] = val
    return stats


async def update_cli_stat(cli_name: str, field: str, value) -> None:
    """Update a CLI stat field in Redis."""
    r = await _get_redis()
    current = await r.hget(DISPATCH_STATS_KEY, cli_name)
    if current:
        data = json.loads(current if isinstance(current, str) else current.decode())
    else:
        data = {"available": False, "tasks_today": 0, "last_used": None}
    data[field] = value
    await r.hset(DISPATCH_STATS_KEY, cli_name, json.dumps(data))


async def record_cli_usage(cli_name: str, success: bool = True) -> None:
    """Record a CLI task execution."""
    r = await _get_redis()
    current = await r.hget(DISPATCH_STATS_KEY, cli_name)
    if current:
        data = json.loads(current if isinstance(current, str) else current.decode())
    else:
        data = {"available": True, "tasks_today": 0, "last_used": None}
    data["tasks_today"] = data.get("tasks_today", 0) + 1
    data["last_used"] = time.time()
    data["available"] = True
    if cli_name == "gemini_cli":
        data["quota_remaining"] = max(0, data.get("quota_remaining", 1000) - 1)
    await r.hset(DISPATCH_STATS_KEY, cli_name, json.dumps(data))


async def reset_daily_stats() -> None:
    """Reset daily CLI usage counters (called at midnight)."""
    r = await _get_redis()
    for cli in ["claude_code", "codex_cli", "gemini_cli", "aider"]:
        current = await r.hget(DISPATCH_STATS_KEY, cli)
        if current:
            data = json.loads(current if isinstance(current, str) else current.decode())
            data["tasks_today"] = 0
            if cli == "gemini_cli":
                data["quota_remaining"] = 1000
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
    """Get provider status for the routing/models dashboard."""
    from .model_governance import get_provider_catalog_registry
    from .provider_execution import build_provider_posture_records
    from .subscriptions import get_policy_snapshot

    cli_stats = await get_cli_status()
    policy = get_policy_snapshot()
    provider_catalog = get_provider_catalog_registry()
    catalog_index = {
        str(entry.get("id") or "").strip(): dict(entry)
        for entry in provider_catalog.get("providers", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }
    posture_records = {
        str(entry.get("provider") or "").strip(): dict(entry)
        for entry in await build_provider_posture_records(limit=max(len(policy.get("providers", {})), 10))
        if isinstance(entry, dict)
    }
    cli_stat_keys = {
        "anthropic_claude_code": "claude_code",
        "openai_codex": "codex_cli",
        "google_gemini": "gemini_cli",
        "moonshot_kimi": "moonshot_kimi",
        "zai_glm_coding": "zai_glm_coding",
    }
    providers = []
    for provider_id, provider_meta in dict(policy.get("providers") or {}).items():
        catalog_entry = catalog_index.get(provider_id, {})
        posture = posture_records.get(provider_id, {})
        stats = cli_stats.get(cli_stat_keys.get(provider_id, provider_id), {})
        providers.append({
            "id": provider_id,
            "name": str(catalog_entry.get("label") or provider_id),
            "subscription": str(catalog_entry.get("subscription_product") or ""),
            "monthly_cost": catalog_entry.get("monthly_cost_usd"),
            "pricing_status": str(catalog_entry.get("official_pricing_status") or "unknown"),
            "role": str(provider_meta.get("role") or posture.get("lane") or ""),
            "category": str(catalog_entry.get("category") or provider_meta.get("category") or ""),
            "status": str(posture.get("provider_state") or posture.get("availability") or "unknown"),
            "provider_state": str(posture.get("provider_state") or posture.get("availability") or "unknown"),
            "state_reasons": list(posture.get("state_reasons") or []),
            "execution_mode": str(posture.get("execution_mode") or ""),
            "direct_execution_ready": bool(posture.get("direct_execution_ready")),
            "governed_handoff_ready": bool(posture.get("governed_handoff_ready")),
            "available": str(posture.get("provider_state") or posture.get("availability") or "") == "available",
            "tasks_today": stats.get("tasks_today", 0),
            "quota_remaining": stats.get("quota_remaining"),
            "last_used": stats.get("last_used"),
            "avg_latency_ms": None,
        })
    providers.sort(key=lambda item: str(item.get("name") or item.get("id") or ""))
    return providers
