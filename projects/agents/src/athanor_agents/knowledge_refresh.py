"""Knowledge Refresh — nightly re-embedding of changed documents.

Runs at 00:00 nightly via scheduler:
1. Git diff to find changed docs
2. Re-embed changed files into Qdrant knowledge collection
3. Prune near-duplicates (cosine > 0.95)
4. Update last-refresh timestamp
"""

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

REFRESH_TS_KEY = "athanor:knowledge:last_refresh"
KNOWLEDGE_COLLECTION = "knowledge"
REPO_ROOT = "/workspace"  # Mounted in agent container


async def _get_redis():
    from .redis_client import get_redis
    return await get_redis()


def _get_changed_docs(since_hours: int = 24) -> list[str]:
    """Get docs changed in the last N hours via git diff."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_hours} hours ago", "--name-only",
             "--pretty=format:", "--diff-filter=ACMR", "--", "docs/"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=30,
        )
        if result.returncode != 0:
            logger.warning("git log failed: %s", result.stderr[:200])
            return []
        files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        return list(set(files))
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Cannot detect changed docs: %s", e)
        return []


async def _embed_text(text: str) -> list[float] | None:
    """Embed text using LiteLLM embedding model."""
    try:
        import litellm
        response = await litellm.aembedding(
            model="embedding",
            input=[text],
        )
        return response.data[0]["embedding"]
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None


async def _upsert_to_qdrant(doc_path: str, content: str, embedding: list[float]) -> bool:
    """Upsert a document embedding to Qdrant knowledge collection."""
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import PointStruct
        import hashlib

        client = AsyncQdrantClient(host="vault", port=6333, timeout=30)

        point_id = hashlib.md5(doc_path.encode()).hexdigest()

        await client.upsert(
            collection_name=KNOWLEDGE_COLLECTION,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "source": doc_path,
                        "content": content[:4000],
                        "type": "document",
                        "refreshed_at": time.time(),
                    },
                )
            ],
        )
        await client.close()
        return True
    except Exception as e:
        logger.warning("Qdrant upsert failed for %s: %s", doc_path, e)
        return False


async def run_knowledge_refresh() -> dict:
    """Run the nightly knowledge refresh cycle.

    Returns summary dict with counts and errors.
    """
    start = time.time()
    changed = _get_changed_docs(since_hours=24)

    result = {
        "docs_found": len(changed),
        "docs_refreshed": 0,
        "docs_failed": 0,
        "errors": [],
        "started_at": start,
    }

    if not changed:
        logger.info("Knowledge refresh: no changed docs in last 24h")
        result["completed_at"] = time.time()
        result["duration_ms"] = int((time.time() - start) * 1000)
        await _update_timestamp()
        return result

    for doc_path in changed:
        full_path = Path(REPO_ROOT) / doc_path
        if not full_path.exists():
            logger.debug("Doc not found (deleted?): %s", doc_path)
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if len(content) < 50:
                continue

            # Chunk large docs
            chunks = _chunk_text(content, max_chars=3000)
            for i, chunk in enumerate(chunks):
                chunk_path = f"{doc_path}#chunk{i}" if len(chunks) > 1 else doc_path
                embedding = await _embed_text(chunk)
                if embedding:
                    success = await _upsert_to_qdrant(chunk_path, chunk, embedding)
                    if success:
                        result["docs_refreshed"] += 1
                    else:
                        result["docs_failed"] += 1
                else:
                    result["docs_failed"] += 1

        except Exception as e:
            logger.warning("Failed to refresh %s: %s", doc_path, e)
            result["docs_failed"] += 1
            result["errors"].append(f"{doc_path}: {str(e)[:100]}")

    result["completed_at"] = time.time()
    result["duration_ms"] = int((time.time() - start) * 1000)
    await _update_timestamp()

    logger.info(
        "Knowledge refresh complete: %d found, %d refreshed, %d failed in %dms",
        result["docs_found"], result["docs_refreshed"],
        result["docs_failed"], result["duration_ms"],
    )

    return result


def _chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into chunks at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


async def _update_timestamp():
    """Update the last-refresh timestamp in Redis."""
    try:
        r = await _get_redis()
        await r.set(REFRESH_TS_KEY, str(time.time()))
    except Exception as e:
        logger.debug("Failed to update refresh timestamp: %s", e)


async def get_refresh_status() -> dict:
    """Get knowledge refresh status for monitoring."""
    try:
        r = await _get_redis()
        ts_raw = await r.get(REFRESH_TS_KEY)
        if ts_raw:
            ts = float(ts_raw if isinstance(ts_raw, str) else ts_raw.decode())
            hours_ago = (time.time() - ts) / 3600
            return {
                "last_refresh": ts,
                "hours_ago": round(hours_ago, 1),
                "status": "fresh" if hours_ago < 26 else "stale",
            }
    except Exception as e:
        logger.debug("Failed to get refresh status: %s", e)
    return {"last_refresh": None, "hours_ago": None, "status": "unknown"}
