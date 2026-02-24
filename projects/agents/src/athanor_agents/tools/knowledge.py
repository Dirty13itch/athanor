"""Knowledge tools — search, retrieve, and manage the Athanor knowledge base."""

import hashlib
import httpx
from langchain_core.tools import tool

from ..config import settings

_QDRANT_URL = "http://192.168.1.244:6333"
_NEO4J_URL = "http://192.168.1.203:7474"
_NEO4J_AUTH = ("neo4j", "athanor2026")
_EMBEDDING_URL = settings.llm_base_url.replace("/v1", "") + "/v1"
_EMBEDDING_KEY = settings.llm_api_key


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector from the embedding model via LiteLLM."""
    resp = httpx.post(
        f"{_EMBEDDING_URL}/embeddings",
        json={"model": "embedding", "input": text},
        headers={"Authorization": f"Bearer {_EMBEDDING_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def _text_to_id(text: str) -> str:
    """Generate a deterministic point ID from text content."""
    h = hashlib.md5(text.encode()).hexdigest()
    # Qdrant accepts UUID-like strings or unsigned ints
    return h


def _run_cypher(cypher: str) -> dict:
    """Execute a Cypher query against Neo4j."""
    resp = httpx.post(
        f"{_NEO4J_URL}/db/neo4j/tx/commit",
        json={"statements": [{"statement": cypher}]},
        auth=_NEO4J_AUTH,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@tool
def search_knowledge(query: str, collection: str = "knowledge", limit: int = 5) -> str:
    """Search the Athanor knowledge base using semantic vector search.

    Finds documents by meaning, not just keywords. Use this to:
    - Answer questions about Athanor's architecture, decisions, and history
    - Find ADRs (Architecture Decision Records) related to a topic
    - Look up research notes, design docs, and hardware specs
    - Check what was previously documented about a subject

    Args:
        query: Natural language question or topic description
        collection: Qdrant collection to search ("knowledge" or "conversations")
        limit: Number of results to return (default 5)
    """
    try:
        vector = _get_embedding(query)

        resp = httpx.post(
            f"{_QDRANT_URL}/collections/{collection}/points/search",
            json={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])

        if not results:
            return f"No matches found in '{collection}' for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            payload = r.get("payload", {})
            source = payload.get("source", "unknown")
            title = payload.get("title", source)
            category = payload.get("category", "")
            text = payload.get("text", "")[:600]
            lines.append(f"[{i}] {title} (score: {score:.3f}, source: {source})")
            if category:
                lines.append(f"    Category: {category}")
            lines.append(f"    {text}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Knowledge search error: {e}"


@tool
def list_documents(category: str = "", limit: int = 20) -> str:
    """List indexed documents in the knowledge base.

    Use this to browse what's in the knowledge base without a specific query.

    Args:
        category: Filter by category (e.g. "adr", "research", "hardware", "design", "project"). Empty = all.
        limit: Maximum number of documents to return
    """
    try:
        body: dict = {
            "limit": limit,
            "with_payload": ["source", "title", "category", "indexed_at"],
        }
        if category:
            body["filter"] = {
                "must": [{"key": "category", "match": {"value": category}}]
            }

        resp = httpx.post(
            f"{_QDRANT_URL}/collections/knowledge/points/scroll",
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        points = resp.json().get("result", {}).get("points", [])

        if not points:
            return f"No documents found{f' in category {category!r}' if category else ''}."

        lines = [f"Documents in knowledge base ({len(points)} shown):"]
        lines.append("")
        for p in points:
            payload = p.get("payload", {})
            source = payload.get("source", "unknown")
            title = payload.get("title", source)
            cat = payload.get("category", "uncategorized")
            indexed = payload.get("indexed_at", "unknown")
            lines.append(f"  - [{cat}] {title}")
            lines.append(f"    Source: {source} | Indexed: {indexed}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing documents: {e}"


@tool
def query_knowledge_graph(question: str) -> str:
    """Query the infrastructure knowledge graph to answer structural questions.

    The graph contains: Node, Service, Agent, Project, Document entities and
    RUNS_ON, DEPENDS_ON, ROUTES_TO, MANAGES, USES, DOCUMENTS relationships.

    Use this for:
    - "What services run on Node 1?"
    - "What does the media agent depend on?"
    - "What projects exist?"
    - "What decisions relate to inference?"

    Args:
        question: Natural language question about Athanor's structure
    """
    # Map common question patterns to Cypher queries
    q = question.lower()

    # Resolve node name aliases
    node_name = None
    if "node 1" in q or "foundry" in q or "node1" in q:
        node_name = "Foundry"
    elif "node 2" in q or "workshop" in q or "node2" in q:
        node_name = "Workshop"
    elif "vault" in q:
        node_name = "VAULT"
    elif "dev" in q and ("workstation" in q or "node" in q):
        node_name = "DEV"

    if "service" in q and node_name:
        cypher = f"MATCH (s:Service)-[:RUNS_ON]->(n:Node {{name: '{node_name}'}}) RETURN s.name AS service, s.port AS port, s.status AS status"
    elif node_name and ("run" in q or "what" in q):
        cypher = f"MATCH (e)-[:RUNS_ON]->(n:Node {{name: '{node_name}'}}) RETURN labels(e)[0] AS type, e.name AS name, e.port AS port, e.status AS status"
    elif "depend" in q:
        cypher = "MATCH (a)-[:DEPENDS_ON]->(b) RETURN labels(a)[0] AS type, a.name AS entity, b.name AS depends_on"
    elif "agent" in q:
        cypher = "MATCH (a:Agent) OPTIONAL MATCH (a)-[:USES]->(s) RETURN a.name AS agent, a.model AS model, collect(s.name) AS uses"
    elif "project" in q:
        cypher = "MATCH (p:Project) RETURN p.name AS project, p.status AS status, p.description AS description"
    elif "route" in q or "routing" in q:
        cypher = "MATCH (a)-[:ROUTES_TO]->(b) RETURN a.name AS from_entity, b.name AS to_entity"
    else:
        # Broad overview
        cypher = "MATCH (n) RETURN labels(n)[0] AS type, n.name AS name, n.status AS status ORDER BY type, name LIMIT 30"

    try:
        data = _run_cypher(cypher)
        errors = data.get("errors", [])
        if errors:
            return f"Graph error: {errors[0].get('message', 'Unknown')}"

        results = data.get("results", [{}])[0]
        columns = results.get("columns", [])
        rows = results.get("data", [])

        if not rows:
            return f"No results for: {question}"

        lines = [" | ".join(columns)]
        lines.append("-" * max(len(lines[0]), 20))
        for row in rows[:30]:
            values = [str(v) for v in row.get("row", [])]
            lines.append(" | ".join(values))

        return f"Query: {cypher}\n\n" + "\n".join(lines)
    except Exception as e:
        return f"Graph query error: {e}"


@tool
def find_related_docs(topic: str, limit: int = 5) -> str:
    """Find documents related to a topic using both semantic search and graph relationships.

    This combines vector similarity (Qdrant) with structural relationships (Neo4j)
    for richer results than either alone.

    Args:
        topic: The topic to find related documents for
        limit: Number of results from each source
    """
    results_parts = []

    # 1. Semantic search in Qdrant
    try:
        vector = _get_embedding(topic)
        resp = httpx.post(
            f"{_QDRANT_URL}/collections/knowledge/points/search",
            json={"vector": vector, "limit": limit, "with_payload": True},
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("result", [])

        if hits:
            results_parts.append("## Semantically Similar Documents")
            for i, h in enumerate(hits, 1):
                payload = h.get("payload", {})
                results_parts.append(
                    f"  {i}. {payload.get('title', 'Untitled')} "
                    f"(score: {h['score']:.3f}, source: {payload.get('source', '?')})"
                )
    except Exception as e:
        results_parts.append(f"Semantic search error: {e}")

    # 2. Graph relationships
    try:
        # Find entities matching the topic
        cypher = (
            f"MATCH (n) WHERE toLower(n.name) CONTAINS toLower('{topic}') "
            f"OPTIONAL MATCH (n)-[r]-(m) "
            f"RETURN n.name AS entity, labels(n)[0] AS type, "
            f"type(r) AS relationship, m.name AS connected_to, labels(m)[0] AS connected_type "
            f"LIMIT 20"
        )
        data = _run_cypher(cypher)
        rows = data.get("results", [{}])[0].get("data", [])

        if rows:
            results_parts.append("\n## Graph Relationships")
            for row in rows:
                vals = row.get("row", [])
                if len(vals) >= 5 and vals[2]:
                    results_parts.append(
                        f"  {vals[0]} ({vals[1]}) --[{vals[2]}]--> {vals[3]} ({vals[4]})"
                    )
                elif len(vals) >= 2:
                    results_parts.append(f"  {vals[0]} ({vals[1]})")
    except Exception as e:
        results_parts.append(f"Graph search error: {e}")

    if not results_parts:
        return f"No related documents found for: {topic}"

    return "\n".join(results_parts)


@tool
def get_knowledge_stats() -> str:
    """Get statistics about the knowledge base — collection sizes, categories, freshness.

    Use this to understand the current state of the knowledge base:
    how many documents are indexed, what categories exist, when last updated.
    """
    lines = ["# Knowledge Base Statistics\n"]

    # Qdrant collection info
    for coll_name in ["knowledge", "conversations"]:
        try:
            resp = httpx.get(f"{_QDRANT_URL}/collections/{coll_name}", timeout=5)
            resp.raise_for_status()
            info = resp.json().get("result", {})
            count = info.get("points_count", 0)
            status = info.get("status", "unknown")
            lines.append(f"## Collection: {coll_name}")
            lines.append(f"  Points: {count}")
            lines.append(f"  Status: {status}")
            lines.append("")
        except Exception as e:
            lines.append(f"## Collection: {coll_name}")
            lines.append(f"  Error: {e}")
            lines.append("")

    # Neo4j entity counts
    try:
        for label in ["Node", "Service", "Agent", "Project", "Document"]:
            data = _run_cypher(f"MATCH (n:{label}) RETURN count(n) AS count")
            rows = data.get("results", [{}])[0].get("data", [])
            count = rows[0]["row"][0] if rows else 0
            lines.append(f"  Graph {label}s: {count}")

        # Relationship count
        data = _run_cypher("MATCH ()-[r]->() RETURN count(r) AS count")
        rows = data.get("results", [{}])[0].get("data", [])
        rel_count = rows[0]["row"][0] if rows else 0
        lines.append(f"  Graph Relationships: {rel_count}")
    except Exception as e:
        lines.append(f"  Graph error: {e}")

    return "\n".join(lines)


KNOWLEDGE_TOOLS = [
    search_knowledge,
    list_documents,
    query_knowledge_graph,
    find_related_docs,
    get_knowledge_stats,
]
