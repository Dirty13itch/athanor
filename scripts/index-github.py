#!/usr/bin/env python3
"""Index GitHub repos and starred repos into Qdrant personal_data collection.

Fetches owned repos (with README content) and starred repos via `gh` CLI,
embeds them via LiteLLM, and upserts into the personal_data Qdrant collection
on Node 1.

Usage:
    python3 scripts/index-github.py                # dry-run: show what would be indexed
    python3 scripts/index-github.py --index        # actually index into Qdrant
    python3 scripts/index-github.py --input gh.json # use cached JSON instead of gh CLI

Options:
    --index     Actually index into Qdrant (dry-run by default)
    --input     Override gh CLI with a JSON file (for testing/offline use)
    -h, --help  Show this help
"""

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

QDRANT_URL = "http://192.168.1.244:6333"
EMBEDDING_URL = (os.environ.get("ATHANOR_LITELLM_URL") or "http://192.168.1.203:4000").rstrip("/") + "/v1"
EMBEDDING_KEY = (
    os.environ.get("ATHANOR_LITELLM_API_KEY")
    or os.environ.get("LITELLM_API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
COLLECTION = "personal_data"
BATCH_SIZE = 20


# ---------------------------------------------------------------------------
# GitHub data fetching via gh CLI
# ---------------------------------------------------------------------------

def run_gh(args):
    """Run a gh CLI command, return parsed JSON."""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"  ERR: gh {' '.join(args)}: {result.stderr.strip()}", file=sys.stderr)
        return None
    return json.loads(result.stdout)


def fetch_owned_repos():
    """Fetch all owned repos with metadata."""
    print("Fetching owned repos...", file=sys.stderr)
    fields = "name,description,primaryLanguage,repositoryTopics,stargazerCount,forkCount,createdAt,pushedAt,url"
    data = run_gh([
        "repo", "list", "--json", fields, "--limit", "100",
    ])
    if not data:
        return []

    repos = []
    for repo in data:
        # Flatten primaryLanguage and repositoryTopics from gh's nested format
        lang = ""
        if repo.get("primaryLanguage"):
            lang = repo["primaryLanguage"].get("name", "")

        topics = []
        for t in (repo.get("repositoryTopics") or []):
            if isinstance(t, dict):
                # gh returns {name: str} inside repositoryTopics
                topics.append(t.get("name", ""))
            elif isinstance(t, str):
                topics.append(t)

        repos.append({
            "name": repo.get("name", ""),
            "description": repo.get("description", "") or "",
            "language": lang,
            "topics": topics,
            "stars": repo.get("stargazerCount", 0),
            "forks": repo.get("forkCount", 0),
            "created_at": repo.get("createdAt", ""),
            "pushed_at": repo.get("pushedAt", ""),
            "url": repo.get("url", ""),
        })

    print(f"  Found {len(repos)} owned repos", file=sys.stderr)
    return repos


def fetch_readme(owner, repo_name):
    """Fetch README.md content for a repo via gh api, base64 decode."""
    result = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo_name}/readme", "--jq", ".content"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    try:
        cleaned = result.stdout.strip().replace("\n", "")
        return base64.b64decode(cleaned).decode("utf-8", errors="replace")
    except Exception:
        return ""


def fetch_readmes_for_repos(repos):
    """Fetch README content for each owned repo."""
    print("Fetching READMEs for owned repos...", file=sys.stderr)
    for i, repo in enumerate(repos):
        # Extract owner from URL: https://github.com/OWNER/NAME
        parts = repo["url"].rstrip("/").split("/")
        if len(parts) >= 2:
            owner = parts[-2]
        else:
            owner = "Dirty13itch"  # fallback

        readme = fetch_readme(owner, repo["name"])
        repo["readme"] = readme
        status = f"{len(readme)} chars" if readme else "none"
        print(f"  [{i+1}/{len(repos)}] {repo['name']}: README {status}", file=sys.stderr)
    return repos


def fetch_starred_repos():
    """Fetch starred repos using gh api with paginated JSON output."""
    all_stars = []
    page = 1
    while True:
        result = subprocess.run(
            ["gh", "api", f"user/starred?per_page=100&page={page}",
             "-H", "Accept: application/vnd.github.v3+json"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"  ERR fetching starred page {page}: {result.stderr.strip()}", file=sys.stderr)
            break

        data = json.loads(result.stdout)
        if not data:
            break

        for repo in data:
            topics = repo.get("topics", [])
            lang = repo.get("language", "") or ""
            all_stars.append({
                "name": repo.get("full_name", repo.get("name", "")),
                "description": repo.get("description", "") or "",
                "language": lang,
                "topics": topics if isinstance(topics, list) else [],
                "stars": repo.get("stargazers_count", 0),
                "url": repo.get("html_url", ""),
            })

        if len(data) < 100:
            break
        page += 1

    print(f"  Found {len(all_stars)} starred repos", file=sys.stderr)
    return all_stars


# ---------------------------------------------------------------------------
# Embedding and Qdrant
# ---------------------------------------------------------------------------

def get_embeddings(texts):
    """Get embedding vectors from LiteLLM. Accepts a list of texts."""
    # Truncate each text to 2000 chars for the embedding model
    truncated = [t[:2000] for t in texts]
    payload = json.dumps({
        "model": "embedding",
        "input": truncated,
    }).encode()
    req = urllib.request.Request(
        f"{EMBEDDING_URL}/embeddings",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {EMBEDDING_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    # Return embeddings sorted by index
    sorted_data = sorted(data["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in sorted_data]


def ensure_collection():
    """Ensure the personal_data Qdrant collection exists."""
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass

    payload = json.dumps({
        "vectors": {"size": 1024, "distance": "Cosine"},
    }).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    urllib.request.urlopen(req, timeout=10)
    print(f"Created collection '{COLLECTION}'", file=sys.stderr)


def point_id(url):
    """Generate MD5 hex string from URL for use as Qdrant point ID."""
    return hashlib.md5(url.encode()).hexdigest()


def upsert_batch(points):
    """Upsert a batch of points to Qdrant."""
    payload = json.dumps({"points": points}).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Qdrant upsert failed: HTTP {resp.status}")


# ---------------------------------------------------------------------------
# Chunk preparation
# ---------------------------------------------------------------------------

def build_owned_repo_chunks(repos):
    """Build indexable chunks for owned repos (metadata + readme)."""
    chunks = []
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    for repo in repos:
        topics_str = ", ".join(repo["topics"]) if repo["topics"] else "none"
        lang = repo["language"] or "unknown"

        # Chunk 1: repo metadata
        meta_text = (
            f"{repo['name']}: {repo['description']}\n"
            f"Language: {lang}. Topics: {topics_str}.\n"
            f"Stars: {repo['stars']}, Forks: {repo['forks']}.\n"
            f"Created: {repo['created_at']}, Last pushed: {repo['pushed_at']}.\n"
            f"URL: {repo['url']}"
        )
        chunks.append({
            "id": point_id(repo["url"]),
            "text": meta_text,
            "payload": {
                "source": "github:owned",
                "category": "github_repo",
                "subcategory": lang,
                "text": meta_text,
                "title": repo["name"],
                "url": repo["url"],
                "filename": "github",
                "indexed_at": now,
            },
        })

        # Chunk 2: README content (if available and substantial)
        readme = repo.get("readme", "")
        if readme and len(readme.strip()) > 100:
            # Truncate very long READMEs but keep enough for good embedding
            readme_text = f"{repo['name']} README:\n\n{readme[:3000]}"
            readme_url = f"{repo['url']}#readme"
            chunks.append({
                "id": point_id(readme_url),
                "text": readme_text,
                "payload": {
                    "source": "github:owned",
                    "category": "github_repo",
                    "subcategory": f"{lang}:readme",
                    "text": readme_text[:2000],
                    "title": f"{repo['name']} README",
                    "url": readme_url,
                    "filename": "github",
                    "indexed_at": now,
                },
            })

    return chunks


def build_starred_repo_chunks(starred):
    """Build indexable chunks for starred repos (interest signals)."""
    chunks = []
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    for repo in starred:
        topics_str = ", ".join(repo["topics"]) if repo["topics"] else "none"
        lang = repo["language"] or "unknown"

        text = (
            f"Starred: {repo['name']}: {repo['description']}\n"
            f"Language: {lang}. Topics: {topics_str}.\n"
            f"Stars: {repo['stars']}. URL: {repo['url']}"
        )
        chunks.append({
            "id": point_id(repo["url"]),
            "text": text,
            "payload": {
                "source": "github:starred",
                "category": "github_star",
                "subcategory": lang if lang != "unknown" else "interest",
                "text": text,
                "title": repo["name"],
                "url": repo["url"],
                "filename": "github",
                "indexed_at": now,
            },
        })

    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def check_connectivity():
    """Verify Qdrant and LiteLLM are reachable."""
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections")
        with urllib.request.urlopen(req, timeout=5):
            print(f"  Qdrant: OK ({QDRANT_URL})", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Cannot reach Qdrant at {QDRANT_URL}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        req = urllib.request.Request(
            f"{EMBEDDING_URL}/models",
            headers={"Authorization": f"Bearer {EMBEDDING_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=5):
            print(f"  LiteLLM: OK ({EMBEDDING_URL})", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Cannot reach LiteLLM at {EMBEDDING_URL}: {e}", file=sys.stderr)
        sys.exit(1)


def index_chunks(chunks):
    """Embed and upsert all chunks into Qdrant in batches."""
    ensure_collection()

    success = 0
    fail = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start:batch_start + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        try:
            vectors = get_embeddings(texts)
            points = []
            for chunk, vector in zip(batch, vectors):
                points.append({
                    "id": chunk["id"],
                    "vector": vector,
                    "payload": chunk["payload"],
                })
            upsert_batch(points)
            success += len(points)
            print(f"  Indexed {success}/{len(chunks)} chunks...", file=sys.stderr)
        except Exception as e:
            fail += len(batch)
            titles = ", ".join(c["payload"]["title"] for c in batch[:3])
            print(f"  ERR batch [{titles}...]: {e}", file=sys.stderr)

    return success, fail


def main():
    parser = argparse.ArgumentParser(
        description="Index GitHub repos and stars into Qdrant personal_data collection."
    )
    parser.add_argument(
        "--index", action="store_true",
        help="Actually index into Qdrant (dry-run by default, prints what would be indexed)",
    )
    parser.add_argument(
        "--input", type=str, metavar="FILE",
        help="Override gh CLI with a JSON file containing {owned: [...], starred: [...]}",
    )
    args = parser.parse_args()

    print("=== Athanor GitHub Indexer ===\n", file=sys.stderr)

    # --- Fetch data ---
    if args.input:
        print(f"Loading from file: {args.input}", file=sys.stderr)
        with open(args.input) as f:
            data = json.load(f)
        owned = data.get("owned", [])
        starred = data.get("starred", [])
        print(f"  Loaded {len(owned)} owned, {len(starred)} starred repos\n", file=sys.stderr)
    else:
        # Check gh is available
        try:
            subprocess.run(["gh", "auth", "status"], capture_output=True, check=True, timeout=10)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ERROR: gh CLI not authenticated or not found: {e}", file=sys.stderr)
            sys.exit(1)

        owned = fetch_owned_repos()
        if owned:
            fetch_readmes_for_repos(owned)
        starred = fetch_starred_repos()
        print(file=sys.stderr)

        # Save fetched data as JSON for --input reuse
        cache_path = "docs/data/github-repos.json"
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump({"owned": owned, "starred": starred}, f, indent=2)
            print(f"Cached GitHub data to {cache_path}", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: could not cache data: {e}", file=sys.stderr)

    # --- Build chunks ---
    owned_chunks = build_owned_repo_chunks(owned)
    starred_chunks = build_starred_repo_chunks(starred)
    all_chunks = owned_chunks + starred_chunks

    # --- Summary ---
    readme_count = sum(1 for c in owned_chunks if c["payload"]["subcategory"].endswith(":readme"))
    print(f"\nSummary:", file=sys.stderr)
    print(f"  Owned repos:    {len(owned)} ({len(owned_chunks) - readme_count} metadata + {readme_count} READMEs)", file=sys.stderr)
    print(f"  Starred repos:  {len(starred)} ({len(starred_chunks)} metadata)", file=sys.stderr)
    print(f"  Total chunks:   {len(all_chunks)}", file=sys.stderr)

    # --- Dry-run output ---
    if not args.index:
        print(f"\n--- DRY RUN (use --index to actually index) ---\n", file=sys.stderr)
        print("\nOwned repos:", file=sys.stderr)
        for repo in owned:
            readme_status = "yes" if repo.get("readme") else "no"
            print(f"  {repo['name']:30s} lang={repo['language'] or '-':12s} "
                  f"stars={repo['stars']:<4d} readme={readme_status}", file=sys.stderr)

        print("\nStarred repos:", file=sys.stderr)
        for repo in starred:
            print(f"  {repo['name']:45s} lang={repo['language'] or '-':12s} "
                  f"stars={repo['stars']}", file=sys.stderr)

        # Output chunks as JSON to stdout for inspection
        json.dump(
            {"total_chunks": len(all_chunks), "chunks": [c["payload"] for c in all_chunks]},
            sys.stdout,
            indent=2,
        )
        print(file=sys.stdout)
        return 0

    # --- Index ---
    print(f"\nConnectivity check:", file=sys.stderr)
    check_connectivity()

    print(f"\nIndexing {len(all_chunks)} chunks to Qdrant ({COLLECTION})...\n", file=sys.stderr)
    success, fail = index_chunks(all_chunks)
    print(f"\nDone: {success} indexed, {fail} failed", file=sys.stderr)

    # Verify collection state
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            info = json.loads(resp.read()).get("result", {})
            print(f"Collection '{COLLECTION}': {info.get('points_count', '?')} points total",
                  file=sys.stderr)
    except Exception:
        pass

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
