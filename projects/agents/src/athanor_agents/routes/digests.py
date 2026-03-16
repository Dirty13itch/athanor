"""Digest endpoints — auto-generated summaries from proactive task results."""

import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter

from ..workspace import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["digests"])

DIGESTS_KEY = "athanor:digests"
MAX_DIGESTS = 30


@router.get("/digests")
async def list_digests(limit: int = 10):
    """List stored digests (most recent first)."""
    r = await get_redis()
    raw = await r.lrange(DIGESTS_KEY, 0, limit - 1)
    digests = [json.loads(item if isinstance(item, str) else item.decode()) for item in raw]
    return {"digests": digests, "count": len(digests)}


@router.get("/digests/latest")
async def latest_digest():
    """Get the most recent digest, or generate one from recent tasks if none stored."""
    r = await get_redis()
    raw = await r.lrange(DIGESTS_KEY, 0, 0)
    if raw:
        digest = json.loads(raw[0] if isinstance(raw[0], str) else raw[0].decode())
        return digest
    # Auto-generate from recent task history
    return await _generate_digest_from_tasks(r)


@router.post("/digests/generate")
async def generate_digest():
    """Generate and store a digest from recent completed tasks."""
    r = await get_redis()
    digest = await _generate_digest_from_tasks(r)
    if digest.get("task_count", 0) > 0:
        await r.lpush(DIGESTS_KEY, json.dumps(digest))
        await r.ltrim(DIGESTS_KEY, 0, MAX_DIGESTS - 1)
    return digest


async def _generate_digest_from_tasks(r) -> dict:
    """Build a digest from completed tasks in the last 24 hours."""
    # Fetch recent tasks from Redis — stored as JSON in hash "athanor:tasks"
    TASKS_KEY = "athanor:tasks"
    all_tasks_raw = await r.hgetall(TASKS_KEY)
    now = time.time()
    cutoff = now - 86400  # 24 hours

    completed = []
    failed = []
    agents = Counter()
    categories = Counter()

    for _task_id, task_json in all_tasks_raw.items():
        try:
            raw = task_json.decode() if isinstance(task_json, bytes) else task_json
            task = json.loads(raw)

            created = float(task.get("created_at", 0))
            if created < cutoff:
                continue

            status = task.get("status", "")
            agent = task.get("agent_id", "unknown")
            prompt = task.get("prompt", task.get("description", ""))

            agents[agent] += 1

            # Categorize by prompt keywords
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
                completed.append({
                    "agent": agent,
                    "prompt": (prompt or "")[:120],
                    "result_preview": result_preview,
                })
            elif status in ("failed", "error"):
                failed.append({
                    "agent": agent,
                    "prompt": (prompt or "")[:120],
                    "error": (task.get("error", "") or "")[:200],
                })
        except Exception:
            continue

    # Build summary text
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
