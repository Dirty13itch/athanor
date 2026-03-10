#!/usr/bin/env python3
"""LLM-powered entity extraction from Qdrant personal_data into Neo4j.

Phase 6 of the personal data architecture. Scrolls through all points in the
Qdrant personal_data collection, sends substantial text to the LLM for entity
extraction (people, organizations, places, topics, dates), and populates Neo4j
with the resulting nodes and relationships.

Supports incremental runs: points with entities_extracted=true are skipped
unless --force is used.

Usage:
    python3 scripts/extract-entities.py                    # full extraction
    python3 scripts/extract-entities.py --dry-run          # preview only
    python3 scripts/extract-entities.py --limit 10         # test with 10 points
    python3 scripts/extract-entities.py --category bookmark
    python3 scripts/extract-entities.py --force            # re-extract all

Options:
    --dry-run         Show what would be extracted without calling LLM or Neo4j
    --limit N         Process only N points (for testing)
    --category CAT    Only process points matching this category
    --force           Re-extract even if already extracted
    -h, --help        Show this help
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

# --- Config ---
QDRANT_URL = os.environ.get("ATHANOR_QDRANT_URL") or os.environ.get("QDRANT_URL", "http://192.168.1.244:6333")
COLLECTION = "personal_data"

LITELLM_BASE_URL = (os.environ.get("ATHANOR_LITELLM_URL") or "http://192.168.1.203:4000").rstrip("/")
LITELLM_URL = f"{LITELLM_BASE_URL}/v1/chat/completions"
LITELLM_KEY = (
    os.environ.get("ATHANOR_LITELLM_API_KEY")
    or os.environ.get("LITELLM_API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
LLM_MODEL = "fast"

NEO4J_BASE_URL = (
    os.environ.get("ATHANOR_NEO4J_URL")
    or os.environ.get("NEO4J_URL")
    or "http://192.168.1.203:7474"
).rstrip("/")
NEO4J_URL = f"{NEO4J_BASE_URL}/db/neo4j/tx/commit"
NEO4J_USER = os.environ.get("ATHANOR_NEO4J_USER") or os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("ATHANOR_NEO4J_PASSWORD") or os.environ.get("NEO4J_PASSWORD", "")

MIN_TEXT_LENGTH = 50
LLM_BATCH_SIZE = 10
NEO4J_BATCH_SIZE = 50
RATE_LIMIT_SECONDS = 1

EXTRACTION_PROMPT = """\
Extract entities from the following text. Return ONLY valid JSON with this exact structure:

{
  "people": [{"name": "Full Name", "role": "their role or relationship if known"}],
  "organizations": [{"name": "Org Name", "type": "company|university|government|nonprofit|other"}],
  "places": [{"name": "Place Name", "type": "property|city|state|country"}],
  "topics": ["topic1", "topic2"],
  "dates": ["2026-01-15"]
}

Rules:
- Only extract entities that are clearly mentioned, not implied.
- Normalize names: "John Smith" not "john smith" or "J. Smith".
- For people without a clear role, use "unknown".
- Topics should be 1-3 words each, lowercase.
- Dates in ISO format (YYYY-MM-DD). Omit if only a year is mentioned.
- If no entities of a type are found, use an empty array.
- Do NOT wrap the JSON in markdown code fences.

Text:
"""


# --- Qdrant helpers ---

def qdrant_scroll(category_filter=None, skip_extracted=True):
    """Scroll through all points in the personal_data collection.

    Yields (point_id, payload) tuples.
    """
    offset = None

    while True:
        body = {
            "limit": 100,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset

        # Build filter conditions
        must_conditions = []
        must_not_conditions = []

        if category_filter:
            must_conditions.append({
                "key": "category",
                "match": {"value": category_filter},
            })

        if skip_extracted:
            must_not_conditions.append({
                "key": "entities_extracted",
                "match": {"value": True},
            })

        if must_conditions or must_not_conditions:
            body["filter"] = {}
            if must_conditions:
                body["filter"]["must"] = must_conditions
            if must_not_conditions:
                body["filter"]["must_not"] = must_not_conditions

        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        result = data.get("result", {})
        points = result.get("points", [])

        for point in points:
            yield point["id"], point.get("payload", {})

        next_offset = result.get("next_page_offset")
        if not next_offset or not points:
            break
        offset = next_offset


def qdrant_set_payload(point_id, payload_update):
    """Update payload fields on a Qdrant point (partial update)."""
    body = json.dumps({
        "points": [point_id],
        "payload": payload_update,
    }).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/payload",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Qdrant payload update failed: HTTP {resp.status}")


# --- LLM helpers ---

def extract_entities_llm(text):
    """Call LLM to extract entities from text. Returns parsed dict or None."""
    # Truncate very long texts to avoid excessive token usage
    truncated = text[:3000]

    body = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "user", "content": EXTRACTION_PROMPT + truncated},
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
        # Disable Qwen3 <think> blocks — we need raw JSON, not reasoning
        "extra_body": {
            "chat_template_kwargs": {"enable_thinking": False},
        },
    }).encode()

    req = urllib.request.Request(
        LITELLM_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_KEY}",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())

    content = data["choices"][0]["message"]["content"].strip()

    # Strip Qwen3 <think>...</think> blocks
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        entities = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                entities = json.loads(content[start:end])
            except json.JSONDecodeError:
                return None
        else:
            return None

    # Validate structure
    expected_keys = {"people", "organizations", "places", "topics", "dates"}
    for key in expected_keys:
        if key not in entities:
            entities[key] = []

    return entities


# --- Neo4j helpers ---

def neo4j_query(statements, dry_run=False):
    """Execute one or more Cypher statements against Neo4j."""
    if dry_run:
        for s in statements:
            stmt = s["statement"]
            display = stmt[:120] + "..." if len(stmt) > 120 else stmt
            print(f"  CYPHER: {display}")
        return {"results": [], "errors": []}

    if not NEO4J_PASS:
        raise RuntimeError("Set ATHANOR_NEO4J_PASSWORD or NEO4J_PASSWORD before writing to Neo4j.")

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


def ensure_neo4j_constraints(dry_run=False):
    """Create uniqueness constraints and indexes for entity nodes."""
    print("Creating Neo4j constraints and indexes...", file=sys.stderr)
    # Note: Topic uniqueness constraint skipped — Topics from bookmarks, GitHub,
    # and entity extraction can share names (e.g., "games") across sources.
    # MERGE on Topic.name correctly deduplicates.
    neo4j_query([
        {"statement": "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE"},
        {"statement": "CREATE CONSTRAINT org_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE"},
        {"statement": "CREATE CONSTRAINT place_name IF NOT EXISTS FOR (pl:Place) REQUIRE pl.name IS UNIQUE"},
        {"statement": "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE"},
        {"statement": "CREATE INDEX document_source IF NOT EXISTS FOR (d:Document) ON (d.source)"},
        {"statement": "CREATE INDEX topic_name_idx IF NOT EXISTS FOR (t:Topic) ON (t.name)"},
    ], dry_run=dry_run)


def build_document_id(payload):
    """Build a stable document ID from a Qdrant point payload."""
    url = payload.get("url", "")
    if url:
        return hashlib.md5(url.encode()).hexdigest()
    # Fall back to source + title
    source = payload.get("source", "")
    title = payload.get("title", "")
    key = f"{source}:{title}" if source or title else str(time.time())
    return hashlib.md5(key.encode()).hexdigest()


def build_cypher_statements(point_id, payload, entities):
    """Build Cypher statements for a single document's extracted entities.

    Returns a list of Cypher statement dicts ready for neo4j_query().
    """
    statements = []
    doc_id = build_document_id(payload)
    doc_title = payload.get("title", "untitled")
    doc_source = payload.get("source", "")
    doc_url = payload.get("url", "")
    doc_category = payload.get("category", "")

    # MERGE the Document node
    statements.append({
        "statement": (
            "MERGE (d:Document {doc_id: $doc_id}) "
            "SET d.title = $title, d.source = $source, "
            "d.url = $url, d.category = $category, "
            "d.qdrant_point_id = $point_id"
        ),
        "parameters": {
            "doc_id": doc_id,
            "title": doc_title,
            "source": doc_source,
            "url": doc_url,
            "category": doc_category,
            "point_id": str(point_id),
        },
    })

    # People
    for person in entities.get("people", []):
        name = person.get("name", "").strip()
        if not name:
            continue
        role = person.get("role", "unknown")
        statements.append({
            "statement": (
                "MERGE (p:Person {name: $name}) "
                "SET p.role = $role "
                "WITH p "
                "MATCH (d:Document {doc_id: $doc_id}) "
                "MERGE (d)-[:MENTIONS]->(p)"
            ),
            "parameters": {
                "name": name,
                "role": role,
                "doc_id": doc_id,
            },
        })

    # Organizations
    for org in entities.get("organizations", []):
        name = org.get("name", "").strip()
        if not name:
            continue
        org_type = org.get("type", "other")
        statements.append({
            "statement": (
                "MERGE (o:Organization {name: $name}) "
                "SET o.type = $type "
                "WITH o "
                "MATCH (d:Document {doc_id: $doc_id}) "
                "MERGE (d)-[:MENTIONS]->(o)"
            ),
            "parameters": {
                "name": name,
                "type": org_type,
                "doc_id": doc_id,
            },
        })

    # Places
    for place in entities.get("places", []):
        name = place.get("name", "").strip()
        if not name:
            continue
        place_type = place.get("type", "city")
        statements.append({
            "statement": (
                "MERGE (pl:Place {name: $name}) "
                "SET pl.type = $type "
                "WITH pl "
                "MATCH (d:Document {doc_id: $doc_id}) "
                "MERGE (d)-[:MENTIONS]->(pl)"
            ),
            "parameters": {
                "name": name,
                "type": place_type,
                "doc_id": doc_id,
            },
        })

    # Topics
    for topic in entities.get("topics", []):
        topic = topic.strip().lower() if isinstance(topic, str) else ""
        if not topic:
            continue
        statements.append({
            "statement": (
                "MERGE (t:Topic {name: $name}) "
                "WITH t "
                "MATCH (d:Document {doc_id: $doc_id}) "
                "MERGE (d)-[:MENTIONS]->(t)"
            ),
            "parameters": {
                "name": topic,
                "doc_id": doc_id,
            },
        })

    return statements


# --- Connectivity checks ---

def check_qdrant():
    """Verify Qdrant is reachable and collection exists."""
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        count = data.get("result", {}).get("points_count", "?")
        print(f"  Qdrant: OK ({COLLECTION}: {count} points)", file=sys.stderr)
        return True
    except Exception as e:
        print(f"ERROR: Cannot reach Qdrant at {QDRANT_URL}: {e}", file=sys.stderr)
        return False


def check_litellm():
    """Verify LiteLLM is reachable."""
    try:
        req = urllib.request.Request(
            f"{LITELLM_BASE_URL}/v1/models",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        print(f"  LiteLLM: OK (model: {LLM_MODEL})", file=sys.stderr)
        return True
    except Exception as e:
        print(f"ERROR: Cannot reach LiteLLM: {e}", file=sys.stderr)
        return False


def check_neo4j():
    """Verify Neo4j is reachable."""
    try:
        result = neo4j_query([{"statement": "RETURN 1 AS ok"}])
        if result.get("errors"):
            raise RuntimeError(result["errors"][0]["message"])
        print(f"  Neo4j: OK ({NEO4J_URL})", file=sys.stderr)
        return True
    except Exception as e:
        print(f"ERROR: Cannot reach Neo4j: {e}", file=sys.stderr)
        return False


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="LLM-powered entity extraction from Qdrant personal_data into Neo4j"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be extracted without calling LLM or Neo4j")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only N points (for testing)")
    parser.add_argument("--category", type=str, default="",
                        help="Only process points matching this category")
    parser.add_argument("--force", action="store_true",
                        help="Re-extract even if already extracted")
    args = parser.parse_args()

    print("=== Athanor Entity Extractor (Phase 6) ===\n", file=sys.stderr)

    # Connectivity checks
    if not check_qdrant():
        sys.exit(1)
    if not args.dry_run:
        if not check_litellm():
            sys.exit(1)
        if not check_neo4j():
            sys.exit(1)
    print(file=sys.stderr)

    # Neo4j schema setup
    if not args.dry_run:
        ensure_neo4j_constraints()
        print(file=sys.stderr)

    # Collect eligible points
    print("Scanning Qdrant for eligible points...", file=sys.stderr)
    skip_extracted = not args.force
    category_filter = args.category if args.category else None

    points = []
    for point_id, payload in qdrant_scroll(
        category_filter=category_filter,
        skip_extracted=skip_extracted,
    ):
        text = payload.get("text", "")
        if len(text) < MIN_TEXT_LENGTH:
            continue
        points.append((point_id, payload))
        if args.limit and len(points) >= args.limit:
            break

    print(f"Found {len(points)} points to process", file=sys.stderr)
    if not points:
        print("\nNothing to do.", file=sys.stderr)
        return 0

    if args.dry_run:
        print(f"\n--- Dry Run: would process {len(points)} points ---\n", file=sys.stderr)
        for i, (point_id, payload) in enumerate(points[:20]):
            title = payload.get("title", "untitled")
            category = payload.get("category", "?")
            text_len = len(payload.get("text", ""))
            print(f"  [{i+1}] id={point_id}  cat={category}  "
                  f"title={title[:60]}  text={text_len} chars", file=sys.stderr)
        if len(points) > 20:
            print(f"  ... and {len(points) - 20} more", file=sys.stderr)
        print(f"\nDry run complete. Use without --dry-run to execute.", file=sys.stderr)
        return 0

    # Process in batches
    print(f"\nProcessing {len(points)} points (batch size: {LLM_BATCH_SIZE})...\n",
          file=sys.stderr)

    extracted_count = 0
    error_count = 0
    empty_count = 0
    cypher_buffer = []

    for i, (point_id, payload) in enumerate(points):
        title = payload.get("title", "untitled")
        text = payload.get("text", "")

        print(f"  [{i+1}/{len(points)}] {title[:60]}...", end="", file=sys.stderr)

        try:
            entities = extract_entities_llm(text)

            if entities is None:
                print(" PARSE_ERROR", file=sys.stderr)
                error_count += 1
                continue

            # Count extracted entities
            total_entities = (
                len(entities.get("people", []))
                + len(entities.get("organizations", []))
                + len(entities.get("places", []))
                + len(entities.get("topics", []))
            )

            if total_entities == 0:
                print(" (no entities)", file=sys.stderr)
                empty_count += 1
            else:
                people_count = len(entities.get("people", []))
                org_count = len(entities.get("organizations", []))
                place_count = len(entities.get("places", []))
                topic_count = len(entities.get("topics", []))
                print(f" P:{people_count} O:{org_count} L:{place_count} T:{topic_count}",
                      file=sys.stderr)

            # Build Cypher statements
            stmts = build_cypher_statements(point_id, payload, entities)
            cypher_buffer.extend(stmts)

            # Flush Cypher buffer when it reaches batch size
            if len(cypher_buffer) >= NEO4J_BATCH_SIZE:
                neo4j_query(cypher_buffer)
                cypher_buffer = []

            # Update Qdrant point with extraction results
            qdrant_set_payload(point_id, {
                "entities_extracted": True,
                "entities": entities,
                "entities_extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

            extracted_count += 1

        except Exception as e:
            print(f" ERROR: {e}", file=sys.stderr)
            error_count += 1

        # Rate limit between LLM calls
        if i < len(points) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    # Flush remaining Cypher statements
    if cypher_buffer:
        neo4j_query(cypher_buffer)

    # Summary
    print(f"\n{'=' * 50}", file=sys.stderr)
    print(f"Extraction complete:", file=sys.stderr)
    print(f"  Processed:  {extracted_count}", file=sys.stderr)
    print(f"  Empty:      {empty_count} (no entities found)", file=sys.stderr)
    print(f"  Errors:     {error_count}", file=sys.stderr)
    print(f"  Total:      {len(points)}", file=sys.stderr)

    # Neo4j summary
    result = neo4j_query([{
        "statement": (
            "MATCH (n) WHERE n:Document OR n:Person OR n:Organization OR n:Place OR n:Topic "
            "RETURN labels(n) as labels, count(n) as cnt "
            "ORDER BY cnt DESC"
        ),
    }])
    print(f"\n--- Neo4j Graph Summary ---", file=sys.stderr)
    for s in result.get("results", []):
        for r in s.get("data", []):
            print(f"  {r['row'][0]}: {r['row'][1]}", file=sys.stderr)

    rel_result = neo4j_query([{
        "statement": (
            "MATCH ()-[r:MENTIONS]->() "
            "RETURN count(r) as mentions"
        ),
    }])
    for s in rel_result.get("results", []):
        for r in s.get("data", []):
            print(f"  MENTIONS relationships: {r['row'][0]}", file=sys.stderr)

    print(f"\nDone.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
