"""Graph context expansion — Neo4j enrichment for Qdrant knowledge retrieval.

After Qdrant kNN returns top-k knowledge chunks, expands the result set by
finding related documents via Neo4j graph traversal.

Linking key: `source` (file path) — already present in Qdrant payloads.
Athanor Document nodes in Neo4j carry `doc_type='athanor'` to distinguish them
from bookmark/GitHub Document nodes created by other indexers.

2-hop expansion:
  Qdrant sources → Neo4j Document nodes (by source)
    → same category set
      → related AthanorDoc Documents not yet retrieved

Falls back gracefully (returns []) if:
  - Neo4j is unavailable
  - No AthanorDoc Document nodes exist yet (run index-knowledge.py first)
  - No related docs found in the category expansion
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
    """Find related AthanorDoc Document nodes via Neo4j category traversal.

    Given Qdrant knowledge result source paths, finds other AthanorDoc
    Documents in the same categories that weren't retrieved by vector search.

    This is a 2-hop expansion:
      source → {categories from matched docs} → related docs in those categories

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
    MATCH (found:Document)
    WHERE found.doc_type = 'athanor' AND found.source IN $sources
    WITH collect(DISTINCT found.category) AS cats
    MATCH (related:Document)
    WHERE related.doc_type = 'athanor'
      AND related.category IN cats
      AND NOT related.source IN $sources
    RETURN related.source AS source,
           related.title AS title,
           related.category AS category
    ORDER BY related.source
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
