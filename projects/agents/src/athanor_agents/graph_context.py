"""Graph context expansion — Neo4j enrichment for Qdrant knowledge retrieval.

After Qdrant kNN returns top-k knowledge chunks, expands the result set by
finding related documents via Neo4j entity traversal (HippoRAG-style).

Linking key: `source` (file path) — already present in Qdrant payloads.
Athanor Document nodes in Neo4j carry `doc_type='athanor'` to distinguish them
from bookmark/GitHub Document nodes created by other indexers.

Entity-based 2-hop expansion (primary):
  Qdrant sources → Document -[:MENTIONS]-> Entity <-[:MENTIONS]- related Document
  Ranked by number of shared entities (semantic overlap).

Falls back gracefully (returns []) if:
  - Neo4j is unavailable
  - No AthanorDoc Document nodes exist yet (run index-knowledge.py first)
  - Entities haven't been extracted yet (run index-knowledge.py --full)
  - No related docs share entities with the retrieved sources
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_NEO4J_URL = "http://192.168.1.203:7474"
_NEO4J_AUTH = ("neo4j", "athanor2026")
_TIMEOUT = 2.0  # stay well within context injection budget


async def expand_knowledge_graph(
    client: httpx.AsyncClient,
    sources: list[str],
    limit: int = 3,
) -> list[dict]:
    """Find related AthanorDoc Document nodes via Neo4j entity traversal.

    Given Qdrant knowledge result source paths, finds other AthanorDoc
    Documents that share named entities (services, models, concepts, etc.)
    with the retrieved docs. Ranked by number of shared entities so the
    most semantically related docs surface first.

    Entity nodes are created by index-knowledge.py at index time (NER via
    Qwen3.5-27B-FP8). MENTIONS edges link Document → Entity.

    This is a 2-hop expansion:
      source → Document -[:MENTIONS]-> Entity <-[:MENTIONS]- related Document

    Args:
        client: Shared async HTTP client.
        sources: Qdrant result source paths (e.g. "docs/decisions/ADR-008-vllm.md").
        limit: Max related docs to return.

    Returns:
        List of {source, title, category} dicts. Empty on any error or miss.
    """
    if not sources:
        return []

    cypher = """
    MATCH (found:Document)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(related:Document)
    WHERE found.doc_type = 'athanor' AND found.source IN $sources
      AND related.doc_type = 'athanor' AND NOT related.source IN $sources
    WITH related, count(DISTINCT e) AS shared_entities
    RETURN related.source AS source,
           related.title AS title,
           related.category AS category
    ORDER BY shared_entities DESC
    LIMIT $limit
    """

    try:
        resp = await client.post(
            f"{_NEO4J_URL}/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": cypher,
                    "parameters": {"sources": sources, "limit": limit},
                }]
            },
            auth=_NEO4J_AUTH,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()

        data = resp.json()
        rows = data.get("results", [{}])[0].get("data", [])

        results = []
        for row in rows:
            cols = row.get("row", [])
            if len(cols) >= 3:
                results.append({
                    "source": cols[0],
                    "title": cols[1],
                    "category": cols[2],
                })

        if results:
            logger.debug(
                "Graph expansion: %d sources → %d related docs",
                len(sources), len(results),
            )

        return results

    except Exception as e:
        logger.debug("Graph expansion failed: %s", e)
        return []
