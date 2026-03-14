"""Memory Consolidation Pipeline — prevents unbounded Qdrant growth.

Runs daily at 3 AM (via scheduler) or on-demand via /v1/consolidate.

Steps:
1. Archive old activity entries (>30 days) — delete from Qdrant
2. Archive old conversations (>30 days) — delete
3. Clean implicit_feedback (>7 days) — ephemeral, short TTL
4. Clean old events (>14 days) — keep recent for pattern detection
5. Report summary (counts per collection)

Ported from: reference/local-system/services/memory/consolidation.py
Adapted for Athanor: direct Qdrant REST (no memory service), async httpx,
schedules via existing scheduler.py.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_QDRANT_URL = settings.qdrant_url

# Retention policies (days)
RETENTION = {
    "activity": 30,
    "conversations": 30,
    "implicit_feedback": 7,
    "events": 14,
}

# Max points to delete per collection per run (safety cap)
MAX_DELETE_BATCH = 500


async def run_consolidation() -> dict[str, Any]:
    """Run full consolidation pipeline across all collections.

    Returns summary dict with counts and errors.
    """
    started = datetime.now(timezone.utc)
    results: dict[str, Any] = {
        "started_at": started.isoformat(),
        "collections": {},
        "total_deleted": 0,
        "errors": [],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for collection, retention_days in RETENTION.items():
            try:
                deleted = await _purge_old_points(
                    client, collection, retention_days
                )
                results["collections"][collection] = {
                    "deleted": deleted,
                    "retention_days": retention_days,
                }
                results["total_deleted"] += deleted
            except Exception as e:
                msg = f"{collection}: {e}"
                results["errors"].append(msg)
                logger.warning("Consolidation failed for %s: %s", collection, e)

    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000

    logger.info(
        "Consolidation complete: deleted %d points across %d collections "
        "(%.0fms, errors=%d)",
        results["total_deleted"],
        len(results["collections"]),
        duration_ms,
        len(results["errors"]),
    )

    # Log consolidation event for pattern detection
    try:
        from .activity import log_event
        import asyncio

        asyncio.create_task(log_event(
            event_type="consolidation_run",
            agent="system",
            description=(
                f"Deleted {results['total_deleted']} old points "
                f"across {len(results['collections'])} collections"
            ),
            data=results["collections"],
        ))
    except Exception as e:
        logger.debug("Consolidation activity log failed: %s", e)

    return results


async def _purge_old_points(
    client: httpx.AsyncClient,
    collection: str,
    retention_days: int,
) -> int:
    """Delete points older than retention_days from a collection.

    Uses Qdrant's scroll + batch delete pattern:
    1. Scroll for points with timestamp_unix < cutoff
    2. Collect point IDs
    3. Batch delete by ID
    """
    cutoff_unix = int(time.time()) - (retention_days * 86400)

    # First, check if collection exists
    resp = await client.get(f"{_QDRANT_URL}/collections/{collection}")
    if resp.status_code != 200:
        logger.debug("Collection %s does not exist, skipping", collection)
        return 0

    # Count points before (for logging)
    count_resp = await client.post(
        f"{_QDRANT_URL}/collections/{collection}/points/count",
        json={"exact": True},
    )
    total_before = 0
    if count_resp.status_code == 200:
        total_before = count_resp.json().get("result", {}).get("count", 0)

    # Scroll for old points
    old_ids: list[str] = []
    offset = None

    while len(old_ids) < MAX_DELETE_BATCH:
        scroll_body: dict[str, Any] = {
            "limit": 100,
            "with_payload": False,
            "with_vector": False,
            "filter": {
                "must": [
                    {"key": "timestamp_unix", "range": {"lt": cutoff_unix}},
                ]
            },
        }
        if offset is not None:
            scroll_body["offset"] = offset

        resp = await client.post(
            f"{_QDRANT_URL}/collections/{collection}/points/scroll",
            json=scroll_body,
        )
        if resp.status_code != 200:
            break

        result = resp.json().get("result", {})
        points = result.get("points", [])
        if not points:
            break

        for p in points:
            old_ids.append(p["id"])

        # Check for next page
        next_offset = result.get("next_page_offset")
        if next_offset is None or len(old_ids) >= MAX_DELETE_BATCH:
            break
        offset = next_offset

    if not old_ids:
        logger.debug(
            "Collection %s: no points older than %d days (total=%d)",
            collection, retention_days, total_before,
        )
        return 0

    # Batch delete
    resp = await client.post(
        f"{_QDRANT_URL}/collections/{collection}/points/delete",
        json={"points": old_ids},
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Delete failed ({resp.status_code}): {resp.text[:200]}"
        )

    logger.info(
        "Collection %s: deleted %d/%d points older than %d days",
        collection, len(old_ids), total_before, retention_days,
    )
    return len(old_ids)


async def get_collection_stats() -> dict[str, Any]:
    """Get point counts for all tracked collections."""
    stats = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for collection in RETENTION:
            try:
                resp = await client.post(
                    f"{_QDRANT_URL}/collections/{collection}/points/count",
                    json={"exact": True},
                )
                if resp.status_code == 200:
                    count = resp.json().get("result", {}).get("count", 0)
                    stats[collection] = {
                        "count": count,
                        "retention_days": RETENTION[collection],
                    }
                else:
                    stats[collection] = {"count": -1, "error": "not found"}
            except Exception as e:
                stats[collection] = {"count": -1, "error": str(e)}
    return stats
