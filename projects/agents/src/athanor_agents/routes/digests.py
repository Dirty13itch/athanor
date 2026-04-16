"""Digest endpoints â€” auto-generated summaries from proactive task results."""

import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)
from ..task_store import read_task_records_by_statuses
from ..workspace import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["digests"])

DIGESTS_KEY = "athanor:digests"
MAX_DIGESTS = 30
TERMINAL_DIGEST_STATUSES = ("completed", "failed")


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    candidate = build_operator_action(body, default_reason=default_reason)
    try:
        action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service="agent-server",
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


@router.get("/digests")
async def list_digests(limit: int = 10):
    """List stored digests (most recent first)."""
    r = await get_redis()
    raw = await r.lrange(DIGESTS_KEY, 0, limit - 1)
    digests = [json.loads(item if isinstance(item, str) else item.decode()) for item in raw]
    return {"digests": digests, "count": len(digests)}


async def load_latest_digest_snapshot() -> dict:
    """Load the latest stored digest or derive one from recent task results."""
    r = await get_redis()
    raw = await r.lrange(DIGESTS_KEY, 0, 0)
    if raw:
        return json.loads(raw[0] if isinstance(raw[0], str) else raw[0].decode())
    return await _generate_digest_from_tasks(r)


@router.get("/digests/latest")
async def latest_digest():
    """Get the most recent digest, or generate one from recent tasks if none stored."""
    return await load_latest_digest_snapshot()


@router.post("/digests/generate")
async def generate_digest(request: Request):
    """Generate and store a digest from recent completed tasks."""
    body, action, denial = await _load_operator_body(
        request,
        route="/v1/digests/generate",
        action_class="operator",
        default_reason="Generated digest",
    )
    if denial:
        return denial

    r = await get_redis()
    digest = await _generate_digest_from_tasks(r)
    if digest.get("task_count", 0) > 0:
        await r.lpush(DIGESTS_KEY, json.dumps(digest))
        await r.ltrim(DIGESTS_KEY, 0, MAX_DIGESTS - 1)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/digests/generate",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Generated digest",
        metadata={"task_count": digest.get("task_count", 0), "requested_period": body.get("period", "24h")},
    )
    return digest


async def _generate_digest_from_tasks(r) -> dict:
    """Build a digest from completed tasks in the last 24 hours."""
    now = time.time()
    cutoff = now - 86400

    completed = []
    failed = []
    agents = Counter()
    categories = Counter()

    for task in await read_task_records_by_statuses(r, *TERMINAL_DIGEST_STATUSES):
        try:
            terminal_at = float(
                task.get("completed_at")
                or task.get("updated_at")
                or task.get("started_at")
                or task.get("created_at")
                or 0
            )
            if terminal_at < cutoff:
                continue

            status = task.get("status", "")
            agent = task.get("agent", "unknown")
            prompt = task.get("prompt", task.get("description", ""))

            agents[agent] += 1

            prompt_lower = (prompt or "").lower()
            if "home assistant" in prompt_lower or "entities" in prompt_lower:
                categories["home_checks"] += 1
            elif "sonarr" in prompt_lower or "radarr" in prompt_lower or "download" in prompt_lower:
                categories["media_checks"] += 1
            elif "health check" in prompt_lower or "service health" in prompt_lower:
                categories["health_checks"] += 1
            elif "knowledge" in prompt_lower or "qdrant" in prompt_lower:
                categories["knowledge_ops"] += 1
            elif "stash" in prompt_lower:
                categories["stash_checks"] += 1
            elif "digest" in prompt_lower or "briefing" in prompt_lower:
                categories["digests"] += 1
            else:
                categories["other"] += 1

            if status == "completed":
                result_preview = (task.get("result", "") or "")[:200]
                completed.append(
                    {
                        "agent": agent,
                        "prompt": (prompt or "")[:120],
                        "result_preview": result_preview,
                    }
                )
            elif status in ("failed", "error"):
                failed.append(
                    {
                        "agent": agent,
                        "prompt": (prompt or "")[:120],
                        "error": (task.get("error", "") or "")[:200],
                    }
                )
        except Exception:
            continue

    parts = []
    total = len(completed) + len(failed)
    if total == 0:
        parts.append("No proactive tasks ran in the last 24 hours.")
    else:
        parts.append(f"{len(completed)} tasks completed, {len(failed)} failed in the last 24 hours.")

        if categories["home_checks"]:
            parts.append(f"Home Agent ran {categories['home_checks']} entity checks.")
        if categories["media_checks"]:
            parts.append(f"Media Agent ran {categories['media_checks']} download/queue checks.")
        if categories["health_checks"]:
            parts.append(f"System health checked {categories['health_checks']} times.")
        if categories["knowledge_ops"]:
            parts.append(f"Knowledge operations: {categories['knowledge_ops']}.")
        if categories["stash_checks"]:
            parts.append(f"Stash library checked {categories['stash_checks']} times.")

        if failed:
            parts.append(f"Failures: {', '.join(f.get('prompt', '?')[:40] for f in failed[:3])}")

    summary = " ".join(parts)

    digest = {
        "type": "auto",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": "24h",
        "summary": summary,
        "task_count": total,
        "completed_count": len(completed),
        "failed_count": len(failed),
        "by_agent": dict(agents),
        "by_category": dict(categories),
        "recent_completions": completed[:10],
        "recent_failures": failed[:5],
    }

    return digest
