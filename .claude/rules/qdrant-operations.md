---
paths:
  - "projects/agents/**"
  - "scripts/**"
---

# Qdrant Operations

This rule file is governed helper guidance only. Verify current topology, restart-brief posture, and runtime reports before treating the endpoint or collection notes below as current authority.

Endpoint: `http://192.168.1.203:6333` (VAULT). No auth required (internal network).
Python client: `from qdrant_client import QdrantClient` — `QdrantClient("192.168.1.203", port=6333)`.
REST API also available. MCP tool `qdrant` is preferred over raw curl for ad-hoc queries.

## Collections

| Collection | Dimensions | Distance | Points | Use Case |
|------------|------------|----------|--------|----------|
| knowledge | 1024 | Cosine | ~3076 | Indexed docs, ADRs, research |
| conversations | 1024 | Cosine | ~2242 | Agent chat logs |
| signals | 1024 | Cosine | — | RSS / intelligence signals |
| activity | 1024 | Cosine | ~5573 | Agent activity logs |
| preferences | 1024 | Cosine | ~59 | User preference vectors |
| implicit_feedback | 1024 | Cosine | ~324 | Inferred preference signals |
| events | 1024 | Cosine | ~10461 | Workspace events |
| llm_cache | 1024 | Cosine | — | Semantic response cache |
| personal_data | 1024 | Cosine | ~15747 | Personal files, bookmarks, repos |

## Search Patterns

**Vector search:** embed the query via LiteLLM `embedding` model first, then search:
```python
vector = litellm.embedding(model="embedding", input=[query]).data[0].embedding
results = client.search("knowledge", query_vector=vector, score_threshold=0.75, limit=10)
```

**Payload filtering:**
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

# must / should / must_not
filt = Filter(must=[FieldCondition(key="category", match=MatchValue(value="adr"))])

# date range on ISO8601 string field
filt = Filter(must=[FieldCondition(key="ingested_at", range=Range(gte="2026-01-01T00:00:00Z"))])
```

**Pagination:**
- `offset` + `limit` for search results
- Scroll with point ID cursor for full collection traversal: `client.scroll(collection, offset=next_page_offset)`

## Safety Rules

- NEVER drop a collection without explicit user approval — full re-index required.
- Use `delete-by-filter` for targeted cleanup, never bulk delete with empty filter.
- Check point count before and after any delete operation.
- Consolidation and cleanup run at 3 AM daily via the scheduler — don't duplicate manually.

**Safe targeted delete:**
```json
{"filter": {"must": [{"key": "source", "match": {"value": "path/to/file.md"}}]}}
```

**Dangerous — require approval:**
- `DELETE /collections/{name}` — drops entire collection
- `POST /collections/{name}/points/delete` with empty or over-broad filter
- Recreating a collection with wrong vector dimensions (breaks all indexed data)
