"""Athanor Data Quality Gate — unified write validation for all data stores."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import httpx
import hashlib
import logging

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
from cluster_config import QDRANT_URL as _QDRANT_URL, EMBEDDING_URL as _EMBEDDING_URL

logger = logging.getLogger("quality-gate")

app = FastAPI(title="Athanor Quality Gate", version="0.1.0")

QDRANT_URL = _QDRANT_URL
EMBEDDING_URL = f"{_EMBEDDING_URL}/v1/embeddings"
EMBEDDING_MODEL = "Qwen3-Embedding-0.6B"

# Config
MIN_CONTENT_LENGTH = 20
MAX_CONTENT_LENGTH = 50_000
DEDUP_THRESHOLD = 0.95  # cosine similarity
REQUIRED_METADATA = {"source"}
TEST_SOURCES = {"e2e-test", "coo-verification", "coo:scan", "chaos-test",
                "fixture-session", "smoke-test", "unit-test", "debug",
                "audit", "probe", "wave2", "integration-test"}


class StoreRequest(BaseModel):
    content: str
    collection: str
    metadata: dict = Field(default_factory=dict)
    source_env: str = "production"  # production, test, debug
    skip_dedup: bool = False


class StoreResponse(BaseModel):
    action: str  # STORED, DUPLICATE, REJECTED, ENRICHED
    point_id: str | None = None
    reason: str | None = None
    quality_score: float | None = None
    similar_to: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


# Startup: create httpx client
@app.on_event("startup")
async def startup():
    app.state.http = httpx.AsyncClient(timeout=30)


@app.on_event("shutdown")
async def shutdown():
    await app.state.http.aclose()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quality-gate", "port": 8790}


@app.post("/validate", response_model=ValidationResult)
async def validate(req: StoreRequest):
    """Validate content without storing."""
    return _validate(req)


@app.post("/store", response_model=StoreResponse)
async def store(req: StoreRequest):
    """Validate, dedup, score, and store content."""
    # Step 1: Validate
    validation = _validate(req)
    if not validation.valid:
        return StoreResponse(action="REJECTED", reason="; ".join(validation.errors))

    # Step 2: Classify source environment
    if req.source_env == "test" or _is_test_source(req.metadata.get("source", "")):
        return StoreResponse(action="REJECTED", reason="test_source_blocked")

    # Step 3: Generate embedding
    http = app.state.http
    try:
        embed_resp = await http.post(EMBEDDING_URL, json={
            "model": EMBEDDING_MODEL,
            "input": req.content[:8000],  # truncate for embedding
        })
        embedding = embed_resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.error("Embedding failed: %s", e)
        raise HTTPException(500, f"Embedding service error: {e}")

    # Step 4: Dedup check (unless skipped)
    if not req.skip_dedup:
        try:
            search_resp = await http.post(
                f"{QDRANT_URL}/collections/{req.collection}/points/search",
                json={
                    "vector": embedding,
                    "limit": 3,
                    "score_threshold": DEDUP_THRESHOLD,
                    "with_payload": True,
                }
            )
            matches = search_resp.json().get("result", [])
            if matches:
                best = matches[0]
                if best["score"] >= 0.99:
                    return StoreResponse(
                        action="DUPLICATE",
                        similar_to=str(best["id"]),
                        reason=f"Exact semantic duplicate (score={best['score']:.3f})"
                    )
                elif best["score"] >= DEDUP_THRESHOLD:
                    # Near-duplicate — enrich existing point's metadata
                    existing_payload = best.get("payload", {})
                    merged = _merge_metadata(existing_payload, req.metadata)
                    await http.put(
                        f"{QDRANT_URL}/collections/{req.collection}/points/payload",
                        json={
                            "payload": merged,
                            "points": [best["id"]],
                        }
                    )
                    return StoreResponse(
                        action="ENRICHED",
                        point_id=str(best["id"]),
                        reason=f"Near-duplicate enriched (score={best['score']:.3f})"
                    )
        except Exception as e:
            logger.warning("Dedup check failed, storing anyway: %s", e)

    # Step 5: Compute quality score
    quality_score = _compute_quality_score(req.content, req.metadata)

    # Step 6: Generate deterministic point ID from content hash
    content_hash = hashlib.sha256(req.content.encode()).hexdigest()[:16]
    point_id = int(content_hash, 16) % (2**63)

    # Step 7: Store with enriched metadata
    payload = {
        **req.metadata,
        "content": req.content,
        "quality_score": quality_score,
        "content_hash": content_hash,
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "source_env": req.source_env,
    }

    await http.put(
        f"{QDRANT_URL}/collections/{req.collection}/points",
        json={
            "points": [{
                "id": point_id,
                "vector": embedding,
                "payload": payload,
            }]
        }
    )

    return StoreResponse(
        action="STORED",
        point_id=str(point_id),
        quality_score=quality_score,
    )


@app.post("/batch-dedup")
async def batch_dedup(collection: str, threshold: float = 0.95, dry_run: bool = True):
    """Scan a collection and find/remove near-duplicates."""
    http = app.state.http
    duplicates = []
    seen_hashes = set()
    offset = None

    while True:
        body = {"limit": 100, "with_payload": True, "with_vectors": True}
        if offset is not None:
            body["offset"] = offset
        resp = await http.post(
            f"{QDRANT_URL}/collections/{collection}/points/scroll",
            json=body
        )
        result = resp.json().get("result", {})
        points = result.get("points", [])
        if not points:
            break

        for p in points:
            payload = p.get("payload", {})
            content = _extract_text(payload)
            if not content:
                # No text field found — skip, can't dedup without content
                continue
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            if content_hash in seen_hashes:
                duplicates.append({"id": p["id"], "reason": "exact_content_hash"})
            else:
                seen_hashes.add(content_hash)

        offset = result.get("next_page_offset")
        if offset is None:
            break

    if not dry_run and duplicates:
        ids = [d["id"] for d in duplicates]
        await http.post(
            f"{QDRANT_URL}/collections/{collection}/points/delete",
            json={"points": ids}
        )

    return {
        "collection": collection,
        "scanned": len(seen_hashes) + len(duplicates),
        "duplicates_found": len(duplicates),
        "dry_run": dry_run,
        "deleted": not dry_run,
    }


@app.post("/cleanup-junk")
async def cleanup_junk(collection: str, dry_run: bool = True):
    """Remove test/fixture/debug data from a collection."""
    http = app.state.http
    junk_ids = []
    total_scanned = 0
    offset = None

    while True:
        body = {"limit": 100, "with_payload": True}
        if offset is not None:
            body["offset"] = offset
        resp = await http.post(
            f"{QDRANT_URL}/collections/{collection}/points/scroll",
            json=body
        )
        result = resp.json().get("result", {})
        points = result.get("points", [])
        if not points:
            break

        total_scanned += len(points)

        for p in points:
            payload = p.get("payload", {})
            if _is_junk_point(payload):
                junk_ids.append(p["id"])

        offset = result.get("next_page_offset")
        if offset is None:
            break

    if not dry_run and junk_ids:
        # Delete in batches of 100
        for i in range(0, len(junk_ids), 100):
            batch = junk_ids[i:i+100]
            await http.post(
                f"{QDRANT_URL}/collections/{collection}/points/delete",
                json={"points": batch}
            )

    return {
        "collection": collection,
        "scanned_total": total_scanned,
        "junk_found": len(junk_ids),
        "dry_run": dry_run,
        "deleted": not dry_run,
    }


@app.get("/stats")
async def stats():
    """Quality statistics across all collections."""
    http = app.state.http
    resp = await http.get(f"{QDRANT_URL}/collections")
    collections = resp.json().get("result", {}).get("collections", [])

    result_stats = {}
    for c in collections:
        name = c["name"]
        info = (await http.get(f"{QDRANT_URL}/collections/{name}")).json().get("result", {})
        result_stats[name] = {
            "points": info.get("points_count", 0),
            "vectors_count": info.get("vectors_count", 0),
        }

    return {"collections": result_stats, "total_points": sum(s["points"] for s in result_stats.values())}


# --- Internal helpers ---

def _extract_text(payload: dict) -> str:
    """Extract the main text content from a payload, checking common field names."""
    for field in ("content", "text", "description", "input_summary", "output_summary"):
        val = payload.get(field, "")
        if val:
            return str(val)
    return ""


def _validate(req: StoreRequest) -> ValidationResult:
    errors = []

    if len(req.content.strip()) < MIN_CONTENT_LENGTH:
        errors.append(f"content_too_short (min {MIN_CONTENT_LENGTH} chars, got {len(req.content.strip())})")

    if len(req.content) > MAX_CONTENT_LENGTH:
        errors.append(f"content_too_long (max {MAX_CONTENT_LENGTH} chars)")

    missing = REQUIRED_METADATA - set(req.metadata.keys())
    if missing:
        errors.append(f"missing_metadata: {missing}")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def _is_test_source(source: str) -> bool:
    source_lower = source.lower()
    return any(ts in source_lower for ts in TEST_SOURCES)


def _is_junk_point(payload: dict) -> bool:
    """Heuristic junk detection."""
    import json
    text = json.dumps(payload).lower()

    # Source-based detection
    source = str(payload.get("source", ""))
    if _is_test_source(source):
        return True

    # Content-based detection
    content = str(payload.get("content", payload.get("text", "")))
    junk_phrases = [
        "endpoint verification test",
        "e2e test:",
        "memory system audit",
        "chaos test memory",
        "hidden moonlit vow stored by live smoke",
        "audit memory write",
    ]
    if any(phrase in content.lower() for phrase in junk_phrases):
        return True

    # Session-based detection
    if payload.get("session_id") == "fixture-session":
        return True

    return False


def _compute_quality_score(content: str, metadata: dict) -> float:
    """0.0-1.0 composite quality score."""
    score = 0.0
    # Content length contribution (0-0.3)
    score += 0.3 * min(len(content) / 500, 1.0)
    # Source presence (0.2)
    score += 0.2 if metadata.get("source") else 0.0
    # Additional metadata richness (0.2)
    bonus_fields = {"title", "category", "author", "url", "created_at"}
    present = len(bonus_fields & set(metadata.keys()))
    score += 0.2 * (present / len(bonus_fields))
    # Content density — ratio of unique words to total (0.3)
    words = content.split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        score += 0.3 * unique_ratio
    return round(score, 3)


def _merge_metadata(existing: dict, new: dict) -> dict:
    """Merge metadata from near-duplicate, preferring richer values."""
    merged = {**existing}
    for key, value in new.items():
        if key == "content":
            continue  # Don't overwrite content
        if key not in merged or not merged[key]:
            merged[key] = value
        elif isinstance(value, str) and len(value) > len(str(merged.get(key, ""))):
            merged[key] = value  # Keep longer string
    merged["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
    return merged
