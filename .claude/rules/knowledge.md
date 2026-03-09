---
paths:
  - "scripts/index-knowledge.py"
  - "projects/agents/**/knowledge*"
  - "projects/agents/**/context*"
---

# Knowledge & RAG Conventions

## Qdrant Collections
- All collections: 1024-dim vectors, Cosine distance
- `knowledge` — ~2500+ points from docs/. Indexed by `scripts/index-knowledge.py`
- `conversations` — Agent conversation history (sparsely populated)
- `activity` — Agent activity logs (fire-and-forget async)
- `preferences` — User preferences + profile (17 profile points)
- `implicit_feedback` — Dashboard interaction signals (page_view, dwell, tap)

## Embedding Model
- Qwen3-Embedding-0.6B at DEV:8001 via vLLM
- 1024 dimensions, 8K context
- Runs on DEV GPU 0 (RTX 5060 Ti 16 GB)

## Indexing
- Full scan: `python3 scripts/index-knowledge.py`
- Sources: `docs/` directory (markdown files)
- Chunking: ~500 tokens per chunk with overlap
- Metadata: file_path, section, timestamp

## Context Injection (context.py)
- 1 embedding call + 4 parallel Qdrant queries + Redis goals
- Time-decayed preferences: 7-day full / 90-day decay / 25% floor
- Total latency: ~30-50ms per request
- Injected as SystemMessage before user query
