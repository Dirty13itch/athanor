#!/usr/bin/env python3
"""Populate Neo4j graph with GitHub repo nodes from cached github-repos.json.

Creates :GitRepo nodes and connects them to :Topic and :Project nodes.

Usage:
    python3 scripts/graph-github.py [--dry-run]
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url

NEO4J_BASE_URL = (
    os.environ.get("ATHANOR_NEO4J_URL")
    or os.environ.get("NEO4J_URL")
    or get_url("neo4j_http")
).rstrip("/")
NEO4J_URL = f"{NEO4J_BASE_URL}/db/neo4j/tx/commit"
NEO4J_USER = os.environ.get("ATHANOR_NEO4J_USER") or os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("ATHANOR_NEO4J_PASSWORD") or os.environ.get("NEO4J_PASSWORD", "")
GITHUB_JSON = Path("docs/data/github-repos.json")


def neo4j_query(statements, dry_run=False):
    """Execute Cypher statements against Neo4j."""
    if dry_run:
        for s in statements:
            print(f"  CYPHER: {s['statement'][:120]}...", file=sys.stderr)
        return {"results": [], "errors": []}

    if not NEO4J_PASS:
        raise RuntimeError("Set ATHANOR_NEO4J_PASSWORD or NEO4J_PASSWORD before writing to Neo4j.")

    import base64
    payload = json.dumps({"statements": statements}).encode()
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req = urllib.request.Request(
        NEO4J_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if result.get("errors"):
        for err in result["errors"]:
            print(f"  NEO4J ERROR: {err['message']}", file=sys.stderr)
    return result


def main():
    parser = argparse.ArgumentParser(description="Populate Neo4j with GitHub repo graph")
    parser.add_argument("--dry-run", action="store_true", help="Print Cypher without executing")
    args = parser.parse_args()

    if not GITHUB_JSON.exists():
        print(f"Error: {GITHUB_JSON} not found. Run index-github.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(GITHUB_JSON.read_text())
    owned = data.get("owned", [])
    starred = data.get("starred", [])

    print(f"Loaded {len(owned)} owned + {len(starred)} starred repos", file=sys.stderr)

    # Step 1: Create constraints
    print("\n1. Creating constraints...", file=sys.stderr)
    neo4j_query([
        {"statement": "CREATE CONSTRAINT gitrepo_url IF NOT EXISTS FOR (r:GitRepo) REQUIRE r.url IS UNIQUE"},
        {"statement": "CREATE INDEX gitrepo_name IF NOT EXISTS FOR (r:GitRepo) ON (r.name)"},
    ], dry_run=args.dry_run)

    # Step 2: Create GitRepo nodes for owned repos
    print(f"\n2. Creating {len(owned)} owned GitRepo nodes...", file=sys.stderr)
    batch = []
    for repo in owned:
        batch.append({
            "statement": (
                "MERGE (r:GitRepo {url: $url}) "
                "SET r.name = $name, r.description = $desc, r.language = $lang, "
                "r.stars = $stars, r.forks = $forks, r.owned = true, "
                "r.created_at = $created, r.pushed_at = $pushed"
            ),
            "parameters": {
                "url": repo.get("url", ""),
                "name": repo.get("name", ""),
                "desc": repo.get("description", "") or "",
                "lang": repo.get("language", "") or "",
                "stars": repo.get("stars", 0),
                "forks": repo.get("forks", 0),
                "created": repo.get("created_at", ""),
                "pushed": repo.get("pushed_at", ""),
            },
        })
    neo4j_query(batch, dry_run=args.dry_run)

    # Step 3: Create GitRepo nodes for starred repos
    print(f"\n3. Creating {len(starred)} starred GitRepo nodes...", file=sys.stderr)
    batch = []
    for repo in starred:
        batch.append({
            "statement": (
                "MERGE (r:GitRepo {url: $url}) "
                "SET r.name = $name, r.description = $desc, r.language = $lang, "
                "r.stars = $stars, r.owned = false"
            ),
            "parameters": {
                "url": repo.get("url", ""),
                "name": repo.get("full_name", repo.get("name", "")),
                "desc": repo.get("description", "") or "",
                "lang": repo.get("language", "") or "",
                "stars": repo.get("stargazers_count", repo.get("stars", 0)),
            },
        })
    neo4j_query(batch, dry_run=args.dry_run)

    # Step 4: Create topic connections from repo topics/tags
    print(f"\n4. Connecting repos to topics...", file=sys.stderr)
    topic_links = 0
    batch = []
    for repo in owned:
        for topic in repo.get("topics", []):
            batch.append({
                "statement": (
                    "MERGE (t:Topic {full_path: $topic_path}) "
                    "SET t.name = $topic_name, t.depth = 0 "
                    "WITH t "
                    "MATCH (r:GitRepo {url: $url}) "
                    "MERGE (r)-[:RELATES_TO]->(t)"
                ),
                "parameters": {
                    "topic_path": f"github:{topic}",
                    "topic_name": topic,
                    "url": repo.get("url", ""),
                },
            })
            topic_links += 1

    for repo in starred:
        for topic in repo.get("topics", []):
            batch.append({
                "statement": (
                    "MERGE (t:Topic {full_path: $topic_path}) "
                    "SET t.name = $topic_name, t.depth = 0 "
                    "WITH t "
                    "MATCH (r:GitRepo {url: $url}) "
                    "MERGE (r)-[:RELATES_TO]->(t)"
                ),
                "parameters": {
                    "topic_path": f"github:{topic}",
                    "topic_name": topic,
                    "url": repo.get("url", ""),
                },
            })
            topic_links += 1

    # Execute in batches
    for i in range(0, len(batch), 50):
        neo4j_query(batch[i : i + 50], dry_run=args.dry_run)
    print(f"  Created {topic_links} repo-topic links", file=sys.stderr)

    # Step 5: Connect owned repos to existing Athanor project
    print(f"\n5. Connecting Athanor repo to project...", file=sys.stderr)
    neo4j_query([{
        "statement": (
            "MATCH (r:GitRepo {name: 'athanor'}) "
            "MATCH (p:Project {name: 'Athanor'}) "
            "MERGE (r)-[:BELONGS_TO]->(p)"
        ),
    }], dry_run=args.dry_run)

    # Step 6: Create EVOLVED_FROM for historical repos
    print(f"\n6. Creating project evolution chain...", file=sys.stderr)
    evolution = [
        ("hydra", "kaizen"),
        ("kaizen", "athanor"),
    ]
    for old, new in evolution:
        neo4j_query([{
            "statement": (
                "MATCH (old:GitRepo {name: $old_name}) "
                "MATCH (new:GitRepo {name: $new_name}) "
                "MERGE (new)-[:EVOLVED_FROM]->(old)"
            ),
            "parameters": {"old_name": old, "new_name": new},
        }], dry_run=args.dry_run)

    # Summary
    if not args.dry_run:
        result = neo4j_query([{
            "statement": (
                "MATCH (n) "
                "RETURN labels(n) as labels, count(n) as cnt "
                "ORDER BY cnt DESC"
            ),
        }])
        print(f"\n--- Graph Summary ---", file=sys.stderr)
        total = 0
        for s in result.get("results", []):
            for r in s.get("data", []):
                label, cnt = r["row"]
                total += cnt
                print(f"  {label[0]:15s} {cnt:5d}", file=sys.stderr)
        print(f"  {'TOTAL':15s} {total:5d}", file=sys.stderr)

    print("\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
