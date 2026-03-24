#!/usr/bin/env python3
"""Populate Neo4j graph with bookmark and topic nodes from parsed bookmarks JSON.

Creates :Bookmark nodes, :Topic nodes (from folder hierarchy), and relationships:
  (:Bookmark)-[:CATEGORIZED_AS]->(:Topic)
  (:Topic)-[:SUBCATEGORY_OF]->(:Topic)

Usage:
    python3 scripts/graph-bookmarks.py [--dry-run]

Options:
    --dry-run   Print Cypher statements without executing
    -h, --help  Show this help
"""

import argparse
import hashlib
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
BOOKMARKS_JSON = Path("docs/data/bookmarks.json")


def neo4j_query(statements, dry_run=False):
    """Execute one or more Cypher statements against Neo4j."""
    if dry_run:
        for s in statements:
            print(f"  CYPHER: {s['statement'][:120]}...")
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


def build_topic_tree(folders):
    """Build topic hierarchy from folder paths like 'Bookmarks bar > Homelab > AI Development'."""
    topics = {}  # name -> {parent: str|None, full_path: str}

    for folder_path in folders:
        if not folder_path:
            continue
        parts = [p.strip() for p in folder_path.split(" > ")]
        for i, part in enumerate(parts):
            full = " > ".join(parts[: i + 1])
            parent_full = " > ".join(parts[:i]) if i > 0 else None
            if full not in topics:
                topics[full] = {
                    "name": part,
                    "full_path": full,
                    "parent": parent_full,
                    "depth": i,
                }

    return topics


def main():
    parser = argparse.ArgumentParser(description="Populate Neo4j with bookmark graph")
    parser.add_argument("--dry-run", action="store_true", help="Print Cypher without executing")
    args = parser.parse_args()

    if not BOOKMARKS_JSON.exists():
        print(f"Error: {BOOKMARKS_JSON} not found. Run parse-bookmarks.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(BOOKMARKS_JSON.read_text())
    bookmarks = data["bookmarks"]
    folders = data["folders"]

    print(f"Loaded {len(bookmarks)} bookmarks in {len(folders)} folders", file=sys.stderr)

    # Step 1: Create constraints and indexes
    print("\n1. Creating constraints...", file=sys.stderr)
    neo4j_query([
        {"statement": "CREATE CONSTRAINT bookmark_url IF NOT EXISTS FOR (b:Bookmark) REQUIRE b.url IS UNIQUE"},
        {"statement": "CREATE CONSTRAINT topic_path IF NOT EXISTS FOR (t:Topic) REQUIRE t.full_path IS UNIQUE"},
        {"statement": "CREATE INDEX bookmark_category IF NOT EXISTS FOR (b:Bookmark) ON (b.category)"},
    ], dry_run=args.dry_run)

    # Step 2: Build topic tree and create Topic nodes
    topics = build_topic_tree(folders)
    print(f"\n2. Creating {len(topics)} Topic nodes...", file=sys.stderr)

    topic_batch = []
    for topic in topics.values():
        topic_batch.append({
            "statement": (
                "MERGE (t:Topic {full_path: $path}) "
                "SET t.name = $name, t.depth = $depth"
            ),
            "parameters": {
                "path": topic["full_path"],
                "name": topic["name"],
                "depth": topic["depth"],
            },
        })

    # Execute in batches of 50
    for i in range(0, len(topic_batch), 50):
        batch = topic_batch[i : i + 50]
        neo4j_query(batch, dry_run=args.dry_run)
        print(f"  Created {min(i + 50, len(topic_batch))}/{len(topic_batch)} topics", file=sys.stderr)

    # Step 3: Create SUBCATEGORY_OF relationships
    print(f"\n3. Creating topic hierarchy relationships...", file=sys.stderr)
    hierarchy_batch = []
    for topic in topics.values():
        if topic["parent"]:
            hierarchy_batch.append({
                "statement": (
                    "MATCH (child:Topic {full_path: $child_path}) "
                    "MATCH (parent:Topic {full_path: $parent_path}) "
                    "MERGE (child)-[:SUBCATEGORY_OF]->(parent)"
                ),
                "parameters": {
                    "child_path": topic["full_path"],
                    "parent_path": topic["parent"],
                },
            })

    for i in range(0, len(hierarchy_batch), 50):
        batch = hierarchy_batch[i : i + 50]
        neo4j_query(batch, dry_run=args.dry_run)
    print(f"  Created {len(hierarchy_batch)} SUBCATEGORY_OF relationships", file=sys.stderr)

    # Step 4: Create Bookmark nodes
    print(f"\n4. Creating {len(bookmarks)} Bookmark nodes...", file=sys.stderr)
    bookmark_batch = []
    for bm in bookmarks:
        bookmark_batch.append({
            "statement": (
                "MERGE (b:Bookmark {url: $url}) "
                "SET b.title = $title, b.category = $category, "
                "b.folder = $folder, b.add_date = $add_date"
            ),
            "parameters": {
                "url": bm["url"],
                "title": bm["title"],
                "category": bm["category"],
                "folder": bm["folder"],
                "add_date": bm.get("add_date_human", ""),
            },
        })

    for i in range(0, len(bookmark_batch), 50):
        batch = bookmark_batch[i : i + 50]
        neo4j_query(batch, dry_run=args.dry_run)
        if (i + 50) % 200 == 0 or i + 50 >= len(bookmark_batch):
            print(f"  Created {min(i + 50, len(bookmark_batch))}/{len(bookmark_batch)} bookmarks", file=sys.stderr)

    # Step 5: Create CATEGORIZED_AS relationships (bookmark -> topic)
    print(f"\n5. Creating bookmark-to-topic relationships...", file=sys.stderr)
    cat_batch = []
    for bm in bookmarks:
        if bm["folder"]:
            cat_batch.append({
                "statement": (
                    "MATCH (b:Bookmark {url: $url}) "
                    "MATCH (t:Topic {full_path: $folder}) "
                    "MERGE (b)-[:CATEGORIZED_AS]->(t)"
                ),
                "parameters": {
                    "url": bm["url"],
                    "folder": bm["folder"],
                },
            })

    for i in range(0, len(cat_batch), 50):
        batch = cat_batch[i : i + 50]
        neo4j_query(batch, dry_run=args.dry_run)
    print(f"  Created {len(cat_batch)} CATEGORIZED_AS relationships", file=sys.stderr)

    # Step 6: Connect topics to existing Project nodes where relevant
    print(f"\n6. Connecting topics to existing project nodes...", file=sys.stderr)
    project_links = [
        ("Bookmarks bar > Homelab", "Athanor"),
        ("Bookmarks bar > Homelab > AI Development", "Athanor"),
    ]
    for topic_path, project_name in project_links:
        neo4j_query([{
            "statement": (
                "MATCH (t:Topic {full_path: $topic_path}) "
                "MATCH (p:Project {name: $project_name}) "
                "MERGE (t)-[:RELATES_TO]->(p)"
            ),
            "parameters": {"topic_path": topic_path, "project_name": project_name},
        }], dry_run=args.dry_run)

    # Summary
    if not args.dry_run:
        result = neo4j_query([{
            "statement": (
                "MATCH (n) WHERE n:Bookmark OR n:Topic "
                "RETURN labels(n) as labels, count(n) as cnt "
                "ORDER BY cnt DESC"
            ),
        }])
        print(f"\n--- Summary ---", file=sys.stderr)
        for s in result.get("results", []):
            for r in s.get("data", []):
                print(f"  {r['row'][0]}: {r['row'][1]}", file=sys.stderr)

    print("\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
