#!/usr/bin/env python3
"""Index Athanor documentation into Qdrant knowledge base.

Run from DEV (where the git repo lives):
    python3 scripts/index-knowledge.py

This scans docs/ and key project files, chunks them, embeds via LiteLLM,
and upserts into the Qdrant 'knowledge' collection.
"""

import hashlib
import os
import sys
import time
from pathlib import Path

import httpx

# --- Config ---
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
EXTRA_FILES = [
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "MEMORY.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs" / "VISION.md",
    REPO_ROOT / "docs" / "BUILD-MANIFEST.md",
    REPO_ROOT / "docs" / "SYSTEM-SPEC.md",
    REPO_ROOT / "docs" / "SERVICES.md",
]

QDRANT_URL = "http://192.168.1.244:6333"
LITELLM_URL = "http://192.168.1.203:4000/v1"
LITELLM_KEY = "sk-athanor-litellm-2026"
COLLECTION = "knowledge"
EMBEDDING_DIM = 1024
CHUNK_SIZE = 1500  # chars per chunk (with overlap)
CHUNK_OVERLAP = 200


def get_embedding(text: str) -> list[float]:
    """Get embedding from LiteLLM proxy."""
    resp = httpx.post(
        f"{LITELLM_URL}/embeddings",
        json={"model": "embedding", "input": text},
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def text_to_uuid(text: str) -> str:
    """Generate a UUID-format string from text for Qdrant point IDs."""
    h = hashlib.md5(text.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def categorize_file(path: Path) -> str:
    """Determine the category of a documentation file."""
    rel = str(path.relative_to(REPO_ROOT))
    if "decisions/ADR" in rel:
        return "adr"
    if "research/" in rel:
        return "research"
    if "hardware/" in rel:
        return "hardware"
    if "design/" in rel:
        return "design"
    if "projects/" in rel:
        return "project"
    if "VISION" in rel:
        return "vision"
    if "BUILD" in rel or "ROADMAP" in rel:
        return "build"
    if "plans/" in rel:
        return "design"
    return "general"


def extract_title(content: str, filepath: Path) -> str:
    """Extract title from markdown content or fall back to filename."""
    for line in content.split("\n")[:10]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return filepath.stem.replace("-", " ").title()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break
            else:
                # Look for sentence break
                for sep in [". ", ".\n", "\n"]:
                    sent_break = text.rfind(sep, start + chunk_size // 2, end)
                    if sent_break > start:
                        end = sent_break + len(sep)
                        break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 50]  # Skip tiny fragments


def ensure_collection():
    """Ensure the Qdrant collection exists."""
    resp = httpx.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=5)
    if resp.status_code == 200:
        return

    print(f"Creating collection '{COLLECTION}'...")
    httpx.put(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        json={
            "vectors": {"size": EMBEDDING_DIM, "distance": "Cosine"},
        },
        timeout=10,
    ).raise_for_status()


def find_docs() -> list[Path]:
    """Find all markdown files to index."""
    files = set()

    # All markdown in docs/
    for f in DOCS_DIR.rglob("*.md"):
        # Skip any CLAUDE.md inside docs subdirs (these are context hints, not content)
        if f.name == "CLAUDE.md" and f.parent != DOCS_DIR:
            continue
        files.add(f)

    # Extra top-level files
    for f in EXTRA_FILES:
        if f.exists():
            files.add(f)

    return sorted(files)


def index_file(filepath: Path, batch: list[dict]) -> int:
    """Read, chunk, and prepare a file for indexing. Returns chunk count."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    if len(content.strip()) < 50:
        return 0

    title = extract_title(content, filepath)
    category = categorize_file(filepath)
    source = str(filepath.relative_to(REPO_ROOT))
    indexed_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    chunks = chunk_text(content)

    for i, chunk in enumerate(chunks):
        # Prepend title context to chunk for better embeddings
        embed_text = f"{title}\n\n{chunk}" if i > 0 else chunk

        point_id = text_to_uuid(f"{source}:chunk:{i}")

        batch.append({
            "id": point_id,
            "text": embed_text,
            "payload": {
                "source": source,
                "title": title,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "indexed_at": indexed_at,
                "text": chunk,
            },
        })

    return len(chunks)


def upsert_batch(batch: list[dict]):
    """Embed and upsert a batch of points to Qdrant."""
    if not batch:
        return

    # Embed all texts (batched for efficiency)
    texts = [p["text"] for p in batch]

    # LiteLLM/vLLM can handle batched embeddings
    resp = httpx.post(
        f"{LITELLM_URL}/embeddings",
        json={"model": "embedding", "input": texts},
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        timeout=120,
    )
    resp.raise_for_status()
    embeddings = [d["embedding"] for d in resp.json()["data"]]

    # Build Qdrant upsert payload
    points = []
    for item, vector in zip(batch, embeddings):
        points.append({
            "id": item["id"],
            "vector": vector,
            "payload": item["payload"],
        })

    resp = httpx.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": points},
        timeout=30,
    )
    resp.raise_for_status()


def main():
    print("=== Athanor Knowledge Indexer ===\n")

    # Check connectivity
    try:
        httpx.get(f"{QDRANT_URL}/collections", timeout=5).raise_for_status()
        print(f"Qdrant: OK ({QDRANT_URL})")
    except Exception as e:
        print(f"ERROR: Cannot reach Qdrant at {QDRANT_URL}: {e}")
        sys.exit(1)

    try:
        httpx.get(
            f"{LITELLM_URL}/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            timeout=5,
        ).raise_for_status()
        print(f"LiteLLM: OK ({LITELLM_URL})")
    except Exception as e:
        print(f"ERROR: Cannot reach LiteLLM at {LITELLM_URL}: {e}")
        sys.exit(1)

    ensure_collection()

    docs = find_docs()
    print(f"\nFound {len(docs)} documents to index\n")

    batch: list[dict] = []
    total_chunks = 0
    batch_size = 20  # Embed this many chunks at once

    for i, filepath in enumerate(docs):
        rel = filepath.relative_to(REPO_ROOT)
        n = index_file(filepath, batch)
        total_chunks += n
        print(f"  [{i+1}/{len(docs)}] {rel} → {n} chunks")

        # Flush batch when it's large enough
        if len(batch) >= batch_size:
            print(f"    Embedding + upserting batch ({len(batch)} chunks)...")
            upsert_batch(batch)
            batch.clear()

    # Final batch
    if batch:
        print(f"\n  Embedding + upserting final batch ({len(batch)} chunks)...")
        upsert_batch(batch)

    print(f"\n=== Done: {total_chunks} chunks from {len(docs)} documents indexed ===")

    # Verify
    resp = httpx.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=5)
    info = resp.json().get("result", {})
    print(f"Collection '{COLLECTION}': {info.get('points_count', '?')} points")


if __name__ == "__main__":
    main()
