---
paths:
  - "scripts/index-knowledge.py"
  - "agents/**"
  - "projects/agents/**"
---

# Qdrant Operations

Endpoint: `http://192.168.1.244:6333` (FOUNDRY). MCP tool `qdrant` is preferred over raw curl.

## Collections

| Collection | Vectors | Distance | Points | Use Case |
|------------|---------|----------|--------|----------|
| knowledge | dense (1024) + sparse (miniCOIL) | Cosine | ~3076 | Documentation chunks |
| conversations | dense (1024) | Cosine | ~2242 | Chat history |
| activity | dense (1024) | Cosine | ~5573 | Activity tracking |
| preferences | dense (1024) | Cosine | ~59 | User preference vectors |
| implicit_feedback | dense (1024) | Cosine | ~324 | Inferred preferences |
| events | dense (1024) | Cosine | ~10461 | System events |
| personal_data | dense (1024) | Cosine | ~15747 | Personal data sync |
| signals | dense (1024) | Cosine | — | Signal pipeline |
| llm_cache | dense (1024) | Cosine | — | Response cache |

## Safe Operations

- **Collection stats:** `GET /collections/{name}` — point count, vector dims, status
- **Scroll:** `POST /collections/{name}/points/scroll` — paginate with `limit` + `offset` (next_page_offset)
- **Search:** `POST /collections/{name}/points/search` — requires vector, returns scored results
- **Filter scroll:** Use `filter.must` with `key`/`match` for metadata queries
- **Count:** `POST /collections/{name}/points/count` with optional filter

## Dangerous — NEVER Without Approval

- `DELETE /collections/{name}` — drops entire collection, requires full re-index
- `POST /collections/{name}/points/delete` with empty/broad filter — mass deletion
- Recreating a collection with wrong vector dimensions — breaks all indexed data

## Deletion Pattern (safe)

Always delete by specific filter, never drop collection:
```json
{"filter": {"must": [{"key": "source", "match": {"value": "path/to/file.md"}}]}}
```

## Consistency Checks

- Orphaned points: source file deleted but points remain — run `index-knowledge.py` incremental
- Missing metadata: points without `source`, `title`, or `category` fields
- Duplicate points: same source + chunk_index — deduplicated via `text_to_uuid` in indexer
