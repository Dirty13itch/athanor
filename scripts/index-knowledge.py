#!/usr/bin/env python3
"""Index Athanor documentation into Qdrant knowledge base.

Run from DEV (where the git repo lives):
    python3 scripts/index-knowledge.py              # incremental (default)
    python3 scripts/index-knowledge.py --full        # full re-index

Requires: pip install fastembed httpx

Hybrid indexing: dense vectors (Qwen3-Embedding via LiteLLM) +
miniCOIL sparse vectors (local, via FastEmbed 0.7+). The collection is
configured with named vectors:
  - "dense": 1024-dim Cosine (semantic search)
  - "sparse": miniCOIL with modifier=idf (keyword+semantic hybrid)

If the existing collection uses unnamed vectors (pre-miniCOIL format),
this script will delete and recreate it, then do a forced full re-index.

Incremental mode: compares content hashes, only re-embeds changed/new files,
removes points for deleted files. Takes <30s when nothing changed.

This scans docs/ and key project files, chunks them, embeds via LiteLLM,
and upserts into the Qdrant 'knowledge' collection.
"""

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Optional

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
NEO4J_URL = "http://192.168.1.203:7474"
NEO4J_AUTH = ("neo4j", "athanor2026")
COLLECTION = "knowledge"
EMBEDDING_DIM = 1024
CHUNK_SIZE = 1500  # chars per chunk (with overlap)
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "Qwen3-Embedding-0.6B"  # Model serving the `embedding` LiteLLM route
MINICOIL_MODEL = "Qdrant/minicoil-v1"

# --- miniCOIL model (lazy loaded) ---
_minicoil = None


def _get_minicoil():
    """Lazy-load miniCOIL sparse embedding model."""
    global _minicoil
    if _minicoil is None:
        try:
            from fastembed import SparseTextEmbedding
            print("  Loading miniCOIL model (first run: downloads ~90MB)...")
            _minicoil = SparseTextEmbedding(model_name=MINICOIL_MODEL)
            print("  miniCOIL ready.")
        except ImportError:
            print("ERROR: fastembed not installed. Run: pip install fastembed", file=sys.stderr)
            sys.exit(1)
    return _minicoil


def compute_sparse_vectors(texts: list[str]) -> list[dict]:
    """Compute miniCOIL sparse vectors for a batch of texts.

    Returns list of {"indices": [...], "values": [...]} dicts,
    one per input text.
    """
    model = _get_minicoil()
    embeddings = list(model.embed(texts, batch_size=min(len(texts), 32)))
    return [
        {"indices": e.indices.tolist(), "values": e.values.tolist()}
        for e in embeddings
    ]


def content_hash(text: str) -> str:
    """MD5 hash of file content for change detection."""
    return hashlib.md5(text.encode()).hexdigest()


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


def extract_title(content_text: str, filepath: Path) -> str:
    """Extract title from markdown content or fall back to filename."""
    for line in content_text.split("\n")[:10]:
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
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break
            else:
                for sep in [". ", ".\n", "\n"]:
                    sent_break = text.rfind(sep, start + chunk_size // 2, end)
                    if sent_break > start:
                        end = sent_break + len(sep)
                        break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 50]


def _collection_has_sparse(resp_json: dict) -> bool:
    """Check if a Qdrant collection already has sparse_vectors configured."""
    config = resp_json.get("result", {}).get("config", {})
    params = config.get("params", {})
    # Qdrant returns sparse_vectors in params if configured
    sparse = params.get("sparse_vectors", {})
    return bool(sparse)


def _collection_has_named_dense(resp_json: dict) -> bool:
    """Check if a Qdrant collection uses named dense vectors (not unnamed)."""
    config = resp_json.get("result", {}).get("config", {})
    params = config.get("params", {})
    vectors = params.get("vectors", {})
    # Named vectors have a dict of dicts; unnamed has {"size": N, "distance": "..."}
    return isinstance(vectors, dict) and "dense" in vectors


def ensure_collection() -> bool:
    """Ensure the Qdrant collection exists with correct schema.

    Returns True if collection was recreated (caller should force full re-index).
    """
    resp = httpx.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=5)

    if resp.status_code == 200:
        data = resp.json()
        has_sparse = _collection_has_sparse(data)
        has_named = _collection_has_named_dense(data)

        if has_sparse and has_named:
            print(f"  Collection '{COLLECTION}': OK (named dense + sparse vectors)")
            return False  # No migration needed

        # Migration needed: delete and recreate
        print(f"  Collection '{COLLECTION}': upgrading to named dense + sparse vectors...")
        httpx.delete(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=10).raise_for_status()
        print(f"  Deleted old collection.")

    # Create with named dense + sparse vectors
    print(f"  Creating collection '{COLLECTION}' with miniCOIL sparse vectors...")
    httpx.put(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        json={
            "vectors": {
                "dense": {"size": EMBEDDING_DIM, "distance": "Cosine"},
            },
            "sparse_vectors": {
                "sparse": {"modifier": "idf"},
            },
        },
        timeout=10,
    ).raise_for_status()

    # Create payload text index for keyword fallback
    httpx.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/index",
        json={"field_name": "text", "field_schema": {"type": "text", "tokenizer": "word"}},
        timeout=10,
    ).raise_for_status()

    print(f"  Collection '{COLLECTION}' created with dense + sparse + text index.")
    return True  # Migration occurred


def find_docs() -> list[Path]:
    """Find all markdown files to index."""
    files = set()

    for f in DOCS_DIR.rglob("*.md"):
        if f.name == "CLAUDE.md" and f.parent != DOCS_DIR:
            continue
        files.add(f)

    for f in EXTRA_FILES:
        if f.exists():
            files.add(f)

    return sorted(files)


def get_existing_hashes() -> dict[str, str]:
    """Get content_hash for each source file already in Qdrant.

    Returns: {source_path: content_hash}
    Only reads chunk_index=0 points (one per file) to get the hash.
    """
    hashes: dict[str, str] = {}
    offset = None

    while True:
        body: dict = {
            "filter": {
                "must": [{"key": "chunk_index", "match": {"value": 0}}],
            },
            "limit": 100,
            "with_payload": ["source", "content_hash"],
        }
        if offset is not None:
            body["offset"] = offset

        resp = httpx.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("result", {})
        points = data.get("points", [])

        for p in points:
            payload = p.get("payload", {})
            source = payload.get("source", "")
            h = payload.get("content_hash", "")
            if source:
                hashes[source] = h

        next_offset = data.get("next_page_offset")
        if not next_offset or not points:
            break
        offset = next_offset

    return hashes


def get_source_point_ids(source: str) -> list[str]:
    """Get all point IDs for a given source file."""
    ids = []
    offset = None

    while True:
        body: dict = {
            "filter": {
                "must": [{"key": "source", "match": {"value": source}}],
            },
            "limit": 100,
            "with_payload": False,
        }
        if offset is not None:
            body["offset"] = offset

        resp = httpx.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("result", {})
        points = data.get("points", [])

        for p in points:
            ids.append(p["id"])

        next_offset = data.get("next_page_offset")
        if not next_offset or not points:
            break
        offset = next_offset

    return ids


def delete_points(point_ids: list[str]):
    """Delete specific points from Qdrant."""
    if not point_ids:
        return
    resp = httpx.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/delete",
        json={"points": point_ids},
        timeout=15,
    )
    resp.raise_for_status()


def index_file(filepath: Path, batch: list[dict], file_hash: str) -> int:
    """Read, chunk, and prepare a file for indexing. Returns chunk count."""
    file_content = filepath.read_text(encoding="utf-8", errors="replace")
    if len(file_content.strip()) < 50:
        return 0

    title = extract_title(file_content, filepath)
    category = categorize_file(filepath)
    source = str(filepath.relative_to(REPO_ROOT))
    indexed_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    chunks = chunk_text(file_content)

    for i, chunk in enumerate(chunks):
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
                "embedded_at": indexed_at,
                "content_hash": file_hash,
                "embedding_model": EMBEDDING_MODEL,
                "sparse_model": MINICOIL_MODEL,
                "text": chunk,
            },
        })

    return len(chunks)


def upsert_batch(batch: list[dict]):
    """Embed (dense + sparse) and upsert a batch of points to Qdrant."""
    if not batch:
        return

    texts = [p["text"] for p in batch]

    # Dense embeddings via LiteLLM
    resp = httpx.post(
        f"{LITELLM_URL}/embeddings",
        json={"model": "embedding", "input": texts},
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        timeout=120,
    )
    resp.raise_for_status()
    dense_vectors = [d["embedding"] for d in resp.json()["data"]]

    # Sparse embeddings via miniCOIL (local, fast)
    sparse_vectors = compute_sparse_vectors(texts)

    points = []
    for item, dense, sparse in zip(batch, dense_vectors, sparse_vectors):
        points.append({
            "id": item["id"],
            "vectors": {
                "dense": dense,
                "sparse": sparse,
            },
            "payload": item["payload"],
        })

    resp = httpx.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": points},
        timeout=30,
    )
    resp.raise_for_status()


def upsert_neo4j_docs(docs: list[dict]):
    """Create or update AthanorDoc Document nodes in Neo4j.

    Each doc requires: {source, title, category, qdrant_point_id}

    Uses doc_type='athanor' to distinguish these from bookmark/GitHub Document
    nodes in the same graph. MERGE on (source, doc_type) is idempotent.
    Failures are non-fatal — Qdrant is the source of truth.
    """
    if not docs:
        return

    cypher = """
    UNWIND $docs AS doc
    MERGE (d:Document {source: doc.source, doc_type: 'athanor'})
    SET d.title = doc.title,
        d.category = doc.category,
        d.qdrant_point_id = doc.qdrant_point_id,
        d.doc_id = doc.source
    """
    try:
        resp = httpx.post(
            f"{NEO4J_URL}/db/neo4j/tx/commit",
            json={"statements": [{"statement": cypher, "parameters": {"docs": docs}}]},
            auth=NEO4J_AUTH,
            timeout=30,
        )
        resp.raise_for_status()
        errors = resp.json().get("errors", [])
        if errors:
            print(f"  Warning: Neo4j write errors: {errors[:2]}", file=sys.stderr)
        else:
            print(f"  Neo4j: {len(docs)} Document nodes upserted")
    except Exception as e:
        print(f"  Warning: Neo4j write failed (graph expansion won't work): {e}", file=sys.stderr)


def check_connectivity():
    """Verify Qdrant and LiteLLM are reachable."""
    try:
        httpx.get(f"{QDRANT_URL}/collections", timeout=5).raise_for_status()
        print(f"  Qdrant: OK ({QDRANT_URL})")
    except Exception as e:
        print(f"ERROR: Cannot reach Qdrant at {QDRANT_URL}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        httpx.get(
            f"{LITELLM_URL}/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            timeout=5,
        ).raise_for_status()
        print(f"  LiteLLM: OK ({LITELLM_URL})")
    except Exception as e:
        print(f"ERROR: Cannot reach LiteLLM at {LITELLM_URL}: {e}", file=sys.stderr)
        sys.exit(1)


def run_full():
    """Full re-index: re-embed every document."""
    print("Mode: FULL re-index\n")

    docs = find_docs()
    print(f"Found {len(docs)} documents to index\n")

    batch: list[dict] = []
    neo4j_docs: list[dict] = []
    total_chunks = 0
    batch_size = 20

    for i, filepath in enumerate(docs):
        rel = filepath.relative_to(REPO_ROOT)
        file_content = filepath.read_text(encoding="utf-8", errors="replace")
        file_hash = content_hash(file_content)
        n = index_file(filepath, batch, file_hash)
        total_chunks += n
        print(f"  [{i+1}/{len(docs)}] {rel} -> {n} chunks")

        if n > 0:
            source = str(filepath.relative_to(REPO_ROOT))
            title = extract_title(file_content, filepath)
            category = categorize_file(filepath)
            neo4j_docs.append({
                "source": source,
                "title": title,
                "category": category,
                "qdrant_point_id": text_to_uuid(f"{source}:chunk:0"),
            })

        if len(batch) >= batch_size:
            print(f"    Embedding + upserting batch ({len(batch)} chunks)...")
            upsert_batch(batch)
            batch.clear()

    if batch:
        print(f"\n  Embedding + upserting final batch ({len(batch)} chunks)...")
        upsert_batch(batch)

    print(f"\n=== Done: {total_chunks} chunks from {len(docs)} documents indexed ===")
    upsert_neo4j_docs(neo4j_docs)


def run_incremental():
    """Incremental index: only re-embed changed/new files, delete removed."""
    print("Mode: INCREMENTAL (hash-based change detection)\n")

    # Step 1: Get current state from Qdrant
    print("  Checking existing index...")
    existing = get_existing_hashes()
    print(f"  {len(existing)} files currently indexed\n")

    # Step 2: Discover current docs
    docs = find_docs()
    current_sources: dict[str, Path] = {}
    current_hashes: dict[str, str] = {}

    for filepath in docs:
        source = str(filepath.relative_to(REPO_ROOT))
        file_content = filepath.read_text(encoding="utf-8", errors="replace")
        current_sources[source] = filepath
        current_hashes[source] = content_hash(file_content)

    # Step 3: Classify files
    new_files = []
    changed_files = []
    unchanged_files = []
    deleted_sources = []

    for source, filepath in current_sources.items():
        if source not in existing:
            new_files.append((source, filepath))
        elif existing[source] != current_hashes[source]:
            changed_files.append((source, filepath))
        else:
            unchanged_files.append(source)

    for source in existing:
        if source not in current_sources:
            deleted_sources.append(source)

    print(f"  New:       {len(new_files)} files")
    print(f"  Changed:   {len(changed_files)} files")
    print(f"  Unchanged: {len(unchanged_files)} files")
    print(f"  Deleted:   {len(deleted_sources)} files")

    if not new_files and not changed_files and not deleted_sources:
        print("\n=== No changes detected. Knowledge base is up to date. ===")
        return

    # Step 4: Delete points for changed + deleted files
    for source in deleted_sources:
        print(f"  Removing: {source}")
        ids = get_source_point_ids(source)
        delete_points(ids)

    for source, _ in changed_files:
        ids = get_source_point_ids(source)
        delete_points(ids)

    # Step 5: Re-index new + changed files
    to_index = new_files + changed_files
    batch: list[dict] = []
    neo4j_docs: list[dict] = []
    total_chunks = 0
    batch_size = 20

    print()
    for i, (source, filepath) in enumerate(to_index):
        rel = filepath.relative_to(REPO_ROOT)
        tag = "NEW" if source not in existing else "UPDATED"
        n = index_file(filepath, batch, current_hashes[source])
        total_chunks += n
        print(f"  [{i+1}/{len(to_index)}] [{tag}] {rel} -> {n} chunks")

        if n > 0:
            file_content = filepath.read_text(encoding="utf-8", errors="replace")
            title = extract_title(file_content, filepath)
            category = categorize_file(filepath)
            neo4j_docs.append({
                "source": source,
                "title": title,
                "category": category,
                "qdrant_point_id": text_to_uuid(f"{source}:chunk:0"),
            })

        if len(batch) >= batch_size:
            print(f"    Embedding + upserting batch ({len(batch)} chunks)...")
            upsert_batch(batch)
            batch.clear()

    if batch:
        print(f"\n  Embedding + upserting final batch ({len(batch)} chunks)...")
        upsert_batch(batch)

    deleted_count = len(deleted_sources)
    print(f"\n=== Done: {total_chunks} chunks indexed, {deleted_count} sources removed ===")
    upsert_neo4j_docs(neo4j_docs)


def main():
    parser = argparse.ArgumentParser(
        description="Index Athanor documentation into Qdrant knowledge base."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full re-index (re-embed everything). Default is incremental.",
    )
    args = parser.parse_args()

    print("=== Athanor Knowledge Indexer ===\n")
    check_connectivity()

    migrated = ensure_collection()
    print()

    # Force full re-index after schema migration
    if migrated:
        print("Schema migration detected: forcing full re-index.\n")
        run_full()
    elif args.full:
        run_full()
    else:
        run_incremental()

    # Verify
    resp = httpx.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=5)
    info = resp.json().get("result", {})
    print(f"Collection '{COLLECTION}': {info.get('points_count', '?')} points")


if __name__ == "__main__":
    main()
