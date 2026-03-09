# Knowledge Architecture & Memory for Local AI Systems
*Deep Research: 2026-03-09*
*Status: Complete -- 10 topics researched with production recommendations for Athanor*

---

## Executive Summary

This document covers 10 research topics spanning GraphRAG, multi-vector retrieval, tiered memory, hybrid graph+vector search, Qdrant updates, proactive retrieval, knowledge freshness, personal data indexing, RAG failure modes, and conversation persistence. Each section follows Context, Options, Analysis, Recommendation, Sources.

**Key findings for Athanor:**
1. HippoRAG v2 is the best GraphRAG option for homelab -- 12x cheaper indexing than MS GraphRAG, works with local vLLM
2. ColPali/ColQwen2 are production-ready but not yet worth deploying -- Athanor's docs are mostly text, not visual PDFs
3. Athanor's Redis+Qdrant+Neo4j stack already matches or exceeds Letta/Mem0 architectures -- build the glue, don't adopt a framework
4. Qdrant's miniCOIL should replace BM25/BM42 for sparse vectors in hybrid search
5. Observational memory (Mastra pattern) is the right approach for conversation context -- scores 94.87% on LongMemEval
6. Time-weighted retrieval + content hashing is the proven freshness pattern
7. At 2,547 points, Athanor is pre-failure-mode scale -- invest in pipeline hygiene now before hitting 10K+

---

## 1. GraphRAG Advances: MS GraphRAG vs LightRAG vs HippoRAG

### Context

Multi-hop queries (questions requiring synthesis across multiple documents) are the primary weakness of standard vector-similarity RAG. Graph-based retrieval augments vector search with entity-relationship traversal. Three leading approaches have emerged.

### Options

| System | Architecture | Multi-hop F1 (MuSiQue) | Indexing Tokens | Prompt Size | Cost |
|--------|-------------|------------------------|-----------------|-------------|------|
| **MS GraphRAG** | Full KG + community summaries + GNN embeddings | Lowest | ~115M | ~40K tokens | Very high ($33K for 5GB corpus) |
| **LightRAG** | Lightweight KG + dual-level retrieval | Moderate | Moderate | ~10K tokens | Low |
| **HippoRAG v2** | PPR + deeper passage integration + online LLM | **51.9 F1** (best) | **~9M** (12x less than GraphRAG) | **~1K tokens** | Low (10-30x cheaper than iterative) |

Additional contenders: G2ConS (+22.3% context recall over LightRAG on MuSiQue), EcphoryRAG (SOTA EM 0.474 vs HippoRAG's 0.392), Fast-GraphRAG (60.08% accuracy on novel datasets).

### Analysis

**MS GraphRAG is not viable for homelab.** The construction cost ($33K for 5GB) is designed for enterprise budgets. It requires full graph regeneration on updates, and community summary generation is extremely LLM-token-intensive. The indexing token count (115M for MuSiQue) would consume significant vLLM capacity.

**LightRAG is the practical middle ground** -- incremental updates (+50% faster), low latency (~80ms), reasonable graph construction. But it drops 5-10 F1 on simple QA tasks, which is unacceptable when most queries are simple.

**HippoRAG v2 is the clear winner for Athanor:**
- Best multi-hop QA (51.9 F1 on MuSiQue) without degrading simple QA
- 12x fewer indexing tokens than GraphRAG (9M vs 115M)
- Compact prompts (~1K tokens vs GraphRAG's 40K)
- Native vLLM support -- explicitly designed for local LLM deployment
- Uses open-source Llama-3.3-70B-Instruct for NER/OpenIE extraction (Qwen3.5-27B should work)
- Accepted at ICML '25 (peer-reviewed)
- PPR (Personalized PageRank) algorithm aligns with Neo4j's existing graph capabilities

**Critical finding from GraphRAG-Bench (ICLR 2026):** "Despite its conceptual promise, recent studies report that GraphRAG frequently underperforms vanilla RAG on many real-world tasks." The value scales with query complexity -- for factoid lookups, standard RAG wins. For multi-hop reasoning, graph RAG is clearly superior.

### Recommendation

**Deploy HippoRAG v2 as the GraphRAG layer on top of existing Qdrant + Neo4j.** Use Qwen3.5-27B-FP8 on FOUNDRY for NER/OpenIE extraction during indexing (off-peak). Store extracted triples in Neo4j. Use PPR traversal for multi-hop retrieval. Keep standard vector search for simple queries.

### Sources
- [HippoRAG GitHub](https://github.com/OSU-NLP-Group/HippoRAG)
- [HippoRAG 2 paper (ICML '25)](https://arxiv.org/abs/2502.14802)
- [GraphRAG-Bench (ICLR '26)](https://github.com/GraphRAG-Bench/GraphRAG-Benchmark)
- [GraphRAG vs HippoRAG vs PathRAG comparison (Jan 2026)](https://medium.com/graph-praxis/graphrag-vs-hipporag-vs-pathrag-vs-og-rag-choosing-the-right-architecture-for-your-knowledge-graph-a4745e8b125f)
- [G2ConS paper](https://arxiv.org/html/2510.24120v1)
- [GraphRAG analysis (Maarga Systems)](https://www.maargasystems.com/2025/05/12/understanding-graphrag-vs-lightrag-a-comparative-analysis-for-enhanced-knowledge-retrieval/)
- [When to use Graphs in RAG (ICLR '26)](https://arxiv.org/html/2506.05690v1)

---

## 2. ColPali and Multi-Vector Retrieval

### Context

ColPali/ColQwen2 use vision language models to create multi-vector embeddings of document pages as images, bypassing OCR entirely. Late interaction scoring (MaxSim) enables fine-grained matching between query tokens and document patches.

### Options

| Model | Params | VRAM | Patches | Query Encode | Page Index | nDCG@5 |
|-------|--------|------|---------|-------------|------------|--------|
| **ColPali** (PaliGemma-3B) | ~3B | ~16GB | 1024 | ~30ms | ~2.5s/page | Baseline |
| **ColQwen2** (Qwen2-VL 2B) | ~2B | ~16GB | 768 | Similar | Similar | +5.3 over ColPali |
| **ColSmol-500M** | 500M | ~4GB | Fewer | Faster | Faster | Lower quality |
| **Nemotron ColEmbed V2-8B** | 8B | ~32GB | N/A | N/A | N/A | SOTA (63.42 ViDoRe v3) |

### Analysis

**Storage is the killer.** ColPali creates 1000+ vectors per page. At 128 dimensions per vector, indexing 1M pages requires ~184.3 GB of storage. Token pooling (pool factor 3) reduces this by 66.7% while retaining 97.8% performance, but storage remains ~60 GB per million pages.

**Throughput:** ~2.5 seconds per page for indexing on a T4 GPU. For Athanor's ~2,547 knowledge points (roughly comparable to pages), indexing would take ~106 minutes. Query encoding is fast (~30ms).

**Where it shines:** Complex PDFs with tables, charts, diagrams, mixed layouts. The vision-based approach eliminates OCR errors and preserves visual relationships.

**Where it doesn't help Athanor:** Most of Athanor's knowledge base is text (markdown docs, research notes, conversations). ColPali's strength is visual document understanding -- tables in PDFs, slides, forms. For pure text, standard dense embeddings (Qwen3-Embedding-0.6B) are faster, smaller, and sufficient.

**Production ecosystem maturity (early 2026):** Multiple production platforms exist (ColiVara, Mixpeek, AstraDB integration). BentoML supports efficient deployment. ECIR 2026 has a dedicated workshop (LIR). The field is maturing but storage and computation challenges remain for large-scale deployment.

### Recommendation

**Do not deploy ColPali/ColQwen2 now.** Athanor's knowledge base is primarily text. ColPali's value emerges with visual-heavy documents (scanned PDFs, slides, forms). If Athanor later indexes personal document scans, tax forms, or other visual content, ColQwen2 on DEV's 5060Ti (16GB) would be the right deployment target.

**Future trigger:** When personal data indexing (topic 8) includes scanned documents or complex PDFs, revisit ColQwen2 deployment.

### Sources
- [ColPali paper](https://arxiv.org/html/2407.01449v4)
- [ColPali GitHub](https://github.com/illuin-tech/colpali)
- [Late Interaction Overview (Weaviate)](https://weaviate.io/blog/late-interaction-overview)
- [Nemotron ColEmbed V2](https://arxiv.org/html/2602.03992v1)
- [Scaling ColPali to billions (Vespa)](https://blog.vespa.ai/scaling-colpali-to-billions/)
- [LIR Workshop @ ECIR 2026](https://arxiv.org/html/2511.00444)
- [Visual RAG Toolkit](https://arxiv.org/html/2602.12510)

---

## 3. MemGPT/Letta Tiered Memory vs Redis+Qdrant+Neo4j

### Context

Letta (formerly MemGPT) pioneered tiered agent memory (core/recall/archival). The question is whether Athanor's existing Redis+Qdrant+Neo4j stack already provides equivalent or superior capabilities, or whether adopting Letta's framework would add value.

### Options

| System | Architecture | LoCoMo Score | Latency (p95) | Token Usage | Self-Hosted |
|--------|-------------|-------------|---------------|-------------|-------------|
| **Letta** | Core + Recall + Archival, agent-editable | 74.0% (GPT-4o mini) | Depends on LLM | Full context + memory blocks | Yes (open-source) |
| **Mem0** | Extract + Update pipeline, graph variant | 66.9% (26% over OpenAI) | 1.44s (91% lower than full-context) | ~1.8K/conv (90% reduction) | Yes (open-source) |
| **Mem0g** (graph) | Mem0 + graph edges for temporal reasoning | ~69% (+2% over base) | Higher (graph overhead) | More tokens | Yes |
| **Redis+Qdrant+Neo4j** (Athanor) | Redis state/cache, Qdrant vectors, Neo4j graph | N/A (not benchmarked) | Sub-ms (Redis), ~10ms (Qdrant) | Configurable | Yes (already deployed) |
| **Mastra Observational** | Observer + Reflector compression | **94.87% (gpt-5-mini)**, 84.23% (gpt-4o) | Low (no retrieval) | 5-40x compression | Yes (open-source) |
| **MemMachine** | N/A | 84.87% | N/A | N/A | No |

### Analysis

**Letta's value proposition is the self-editing memory pattern**, not the infrastructure. Athanor already has better infrastructure:
- **Redis** handles core memory (always-in-context state, sub-ms access)
- **Qdrant** handles recall memory (semantic search across conversations/knowledge)
- **Neo4j** handles relational memory (entity relationships, temporal edges)

What Athanor lacks is the **agent-driven memory management** -- the pattern where agents decide what to remember, forget, and update. This is a code pattern, not an infrastructure choice.

**Mem0's key contribution** is the two-phase Extract+Update pipeline that achieves 90% token reduction. This is directly portable to Athanor's stack -- run extraction against conversations, store facts in Qdrant with metadata, use the same selective retrieval pattern.

**Mastra's observational memory is the breakthrough finding.** At 94.87% on LongMemEval (industry record), it outperforms all memory frameworks by a significant margin. The architecture is deliberately simple: no vector DB required for conversation context. Two background agents (Observer at 30K token threshold, Reflector at 40K) compress conversation history into dated observation logs. The main agent sees compressed observations instead of raw history.

**Why this matters for Athanor:** The 9 agents already have proactive schedules and a self-improvement loop. Adding Observer/Reflector background processes for conversation compression fits naturally into the existing architecture. Redis can store the observation logs. No new infrastructure needed.

**Benchmark controversy:** Mem0 and Letta dispute each other's LoCoMo results. Letta claims Mem0's methodology was unclear; Mem0 didn't respond to clarification. Letta's own result (74.0%) used a filesystem approach, not their memory framework. This suggests the memory retrieval mechanism matters less than the agent's ability to search effectively.

### Recommendation

**Do not adopt Letta or Mem0 as frameworks.** Athanor's Redis+Qdrant+Neo4j stack is already superior infrastructure. Instead:

1. **Implement the Mem0 Extract+Update pattern** as a post-conversation pipeline:
   - After each conversation, extract key facts using Qwen3.5-27B
   - Store extracted facts in Qdrant `knowledge` collection with source attribution
   - Store entity relationships in Neo4j
   - Store current user state in Redis

2. **Implement Mastra-style observational memory** for long-running agent conversations:
   - Observer process: at 30K unprocessed tokens, compress into observation log
   - Reflector process: at 40K observation tokens, consolidate and restructure
   - Store observation logs in Redis (fast access, always in-context)
   - Eliminates need for conversation vector search during active sessions

### Sources
- [Letta Agent Memory Benchmark](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- [Letta v1 Architecture](https://www.letta.com/blog/letta-v1-agent)
- [Mem0 paper (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413)
- [Mem0 Research](https://mem0.ai/research)
- [Mastra Observational Memory Research](https://mastra.ai/research/observational-memory)
- [Mastra Observational Memory Docs](https://mastra.ai/docs/memory/observational-memory)
- [Observational Memory VentureBeat](https://venturebeat.com/data/observational-memory-cuts-ai-agent-costs-10x-and-outscores-rag-on-long)
- [Stateful AI Agents: Letta Deep Dive (Feb 2026)](https://medium.com/@piyush.jhamb4u/stateful-ai-agents-a-deep-dive-into-letta-memgpt-memory-models-a2ffc01a7ea1)
- [Top 10 AI Memory Products 2026](https://medium.com/@bumurzaqov2/top-10-ai-memory-products-2026-09d7900b5ab1)
- [AWS AgentCore Memory](https://aws.amazon.com/blogs/machine-learning/building-smarter-ai-agents-agentcore-long-term-memory-deep-dive/)
- [Redis AI Agent Memory](https://redis.io/blog/ai-agent-memory-stateful-systems/)

---

## 4. Neo4j + Qdrant Hybrid: Best Practices

### Context

Athanor runs both Neo4j (4,447 relationships) and Qdrant (8 collections, 2,547 knowledge points). The question is how to optimally combine graph traversal with vector similarity for retrieval.

### Query Pipeline Pattern (Production-Proven)

The official `neo4j-graphrag-python` package provides `QdrantNeo4jRetriever`:

```python
from neo4j_graphrag.retrievers import QdrantNeo4jRetriever

retriever = QdrantNeo4jRetriever(
    driver=neo4j_driver,
    client=qdrant_client,
    collection_name="knowledge",
    id_property_external="id",    # Qdrant payload field
    id_property_neo4j="id"        # Neo4j node property
)
results = retriever.search(query_vector=embedding, top_k=5)
```

**Pipeline steps:**
1. Encode query to vector
2. Qdrant kNN search returns top-k vectors with `neo4j_id` in payload
3. Extract entity IDs from Qdrant results
4. Neo4j Cypher traversal expands multi-hop relationships:
   ```cypher
   MATCH (e:Entity)-[r1]-(n1)-[r2]-(n2)
   WHERE e.id IN $entity_ids
   RETURN e, r1, n1, r2, n2
   ```
5. Format graph context as readable text
6. Combine vector-retrieved chunks + graph context for LLM

### Case Study: Lettria (Production)

Lettria integrated Qdrant + Neo4j for enterprise GraphRAG and measured:
- **+20% accuracy** over vector-only search
- Standard vector search alone: ~70% accuracy (insufficient for production)
- Hybrid graph+vector: ~90% accuracy

**Sync mechanism:** Custom ingest with transactional batching:
1. Prepare writes as Neo4j transaction batch
2. Snapshot Qdrant points before update
3. Update Qdrant optimistically
4. If Neo4j commit fails, rollback Qdrant from snapshot

### Best Practices (Validated)

1. **Schema alignment:** Ensure `id` fields match between Qdrant payloads and Neo4j node properties
2. **Ontology-driven ingestion:** Use LLM to extract semantically meaningful triples, not all possible triples. Reduces noise.
3. **Index everything used in filters:** Neo4j composite indexes on frequently queried properties
4. **Quantization in Qdrant:** Use scalar or binary quantization for the knowledge collection (2,547 points is small -- this matters more at scale)
5. **Batched writes:** Group ingestion into Neo4j transactions + Qdrant batch upserts. Use snapshot-based rollback for consistency.
6. **Two-stage retrieval:** Fast Qdrant kNN first (broad recall), then Neo4j graph expansion (precision + context)

### Latency Profile

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Qdrant kNN (top-10) | 1-5ms | At 2,547 points, essentially instant |
| Neo4j 2-hop traversal | 5-20ms | Depends on graph density |
| Full hybrid pipeline | 10-30ms | Well within production SLAs |
| LLM generation | 500-2000ms | Dominates total latency |

### Recommendation

**Wire the `QdrantNeo4jRetriever` into the agent pipeline.** The official package (`pip install "neo4j_graphrag[qdrant]"`) provides exactly the integration Athanor needs. Ensure all Qdrant points in the `knowledge` collection have a `neo4j_id` payload field linking to corresponding Neo4j entities.

### Sources
- [GraphRAG with Qdrant and Neo4j (Qdrant official)](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)
- [Lettria Case Study (Qdrant)](https://qdrant.tech/blog/case-study-lettria-v2/)
- [Neo4j GraphRAG Python Package](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html)
- [Neo4j + Qdrant RAG Pipeline (Neo4j blog)](https://neo4j.com/blog/developer/qdrant-to-enhance-rag-pipeline/)
- [graphrag-hybrid (GitHub)](https://github.com/rileylemm/graphrag-hybrid)
- [Graph-Enhanced RAG DeepWiki](https://deepwiki.com/qdrant/examples/6.2-graph-enhanced-rag-with-neo4j)

---

## 5. Qdrant 2025-2026 Updates

### Major New Features (2025)

| Feature | Version | Impact |
|---------|---------|--------|
| **Score-Boosting Reranking** | 2025 | Blend vector similarity with business signals (e.g., freshness, priority) |
| **Full-Text Filtering** | 2025 | Native multilingual tokenization, stemming, phrase matching |
| **ACORN Algorithm** | 2025 | Higher-quality filtered HNSW queries |
| **MMR (Maximal Marginal Relevance)** | 2025 | Balances relevance + diversity in results |
| **GPU-Accelerated HNSW Indexing** | 2025 | ~10x faster ingestion |
| **Inline Storage** | 2025 | Quantized vectors in graph for disk-based search |
| **1.5-bit, 2-bit, Asymmetric Quantization** | 2025 | Extreme compression options |
| **Qdrant Edge (Beta)** | 2025 | In-process Qdrant (same storage format as server) |
| **miniCOIL** | Feb 2026 | Neural sparse retrieval replacing BM42 |
| **Conditional Updates** | 2025 | Safe concurrent workflows |
| **Tiered Multitenancy** | 2025 | Efficient small + large tenant handling |

### BM42 vs BM25 vs miniCOIL

| Sparse Method | Architecture | Quality vs BM25 | Status |
|--------------|-------------|-----------------|--------|
| **BM25** | TF-IDF statistical | Baseline | Production standard |
| **BM42** | Transformer attention weights replacing TF | **Does not outperform BM25** (benchmark error acknowledged) | Experimental only |
| **miniCOIL** | BM25 + 4D COIL semantic vectors per word | **+2-5% NDCG@10** over BM25 on standard benchmarks | Production-ready (FastEmbed v0.7+) |

**miniCOIL details:**
- Vocabulary: 30,000 most common English words
- 4D semantic vector per word (4 consecutive cells in sparse vector)
- Falls back to pure BM25 for unknown words
- Training: ~50 seconds per word on single CPU (40M sentences from OpenWebText)
- Uses `jina-embeddings-v2-small-en` (512D) as input encoder
- Benchmark: MS MARCO +2.9%, NQ +4.9%, Quora +2.3% over BM25

**BM42 post-mortem:** Qdrant acknowledged a mistake in their evaluation script. BM42 does not outperform BM25 in production. They advise treating it as experimental. miniCOIL is the successor.

### 2026 Roadmap

- 4-bit quantization (further compression)
- Read-write segregation
- Block storage integration
- Relevance feedback (agent-native retrieval)
- Expanded inference capabilities
- Fully scalable multitenancy with read-only replicas

### Migration: v1.15.x to v1.17.x

**Critical:** v1.17.x removed RocksDB in favor of gridstore. Direct upgrade from v1.15.x to v1.17.x is **not possible** -- must upgrade one minor version at a time (v1.15 -> v1.16 -> v1.17).

### Recommendation

1. **Replace BM25 with miniCOIL** for sparse vectors in hybrid search. Use FastEmbed handle `Qdrant/minicoil-v1` with `Modifier.IDF`.
2. **Enable Score-Boosting Reranking** to blend vector similarity with freshness timestamps.
3. **Check Qdrant version** on VAULT and plan incremental upgrade to v1.17+ if not already there.
4. **Enable MMR** for diversity in retrieval results (prevents returning near-duplicate chunks).

### Sources
- [Qdrant 2025 Recap](https://qdrant.tech/blog/2025-recap/)
- [miniCOIL article (Qdrant)](https://qdrant.tech/articles/minicoil/)
- [miniCOIL FastEmbed docs](https://qdrant.tech/documentation/fastembed/fastembed-minicoil/)
- [BM42 article (Qdrant)](https://qdrant.tech/articles/bm42/)
- [BM42 evaluation (GitHub)](https://github.com/qdrant/bm42_eval)
- [Qdrant Releases (GitHub)](https://github.com/qdrant/qdrant/releases)
- [Modern Sparse Neural Retrieval (Qdrant)](https://qdrant.tech/articles/modern-sparse-neural-retrieval/)
- [Hybrid Search with Qdrant Query API](https://qdrant.tech/articles/hybrid-search/)

---

## 6. Proactive/Anticipatory Retrieval

### Context

Standard RAG waits for a query. Proactive retrieval pushes relevant context to agents before they ask. This aligns with Athanor's existing proactive scheduling (agents have scheduled tasks via the self-improvement loop).

### State of the Art (2025-2026)

**Production implementations:**
- **ChatGPT Pulse** (Sept 2025): Researched based on past interactions without prompts. Paused Dec 2025 due to quality concerns.
- **Google CC** (Dec 2025): Daily "Your Day Ahead" briefing from Gmail/Calendar/Drive. No prompt needed.
- **Meta AI Brief** (Nov 2025 testing): Personalized morning briefings on Facebook.

**Academic:** ProActLLM Workshop (CIKM 2025) explored anticipatory information-seeking.

### Architecture Pattern

Proactive retrieval requires three components:
1. **Ambient sensing:** Continuous monitoring of information streams (email, calendar, docs, activity)
2. **Trigger detection:** Identifying when context should be pushed (time-based, event-based, pattern-based)
3. **Relevance filtering:** Ensuring pushed context is valuable (avoiding alert fatigue)

### What Works as Triggers

| Trigger Type | Example | False Positive Risk |
|-------------|---------|-------------------|
| **Calendar-based** | Pre-meeting context injection | Low (deterministic) |
| **Activity-based** | User opens project -> push related notes | Medium |
| **Pattern-based** | "You discussed X yesterday, here's an update" | High |
| **Event-based** | RSS feed matches known interest | Medium |

### Relevance to Athanor

Athanor already has the infrastructure for proactive retrieval:
- **Redis Pub/Sub** for event distribution
- **Miniflux RSS** (17 feeds, 6 categories) for external signals
- **n8n workflows** for automation
- **Agent proactive schedules** (5:30 AM daily cycle)

What's missing is the **context push mechanism** -- having agents pre-populate context for the user based on detected patterns.

### Recommendation

**Implement proactive retrieval in three phases:**

1. **Phase 1 (Calendar/Time-based):** Morning briefing agent that pulls today's calendar, recent conversations, and pending tasks. Push to Command Center dashboard. Low false-positive risk.

2. **Phase 2 (RSS/Event-based):** Miniflux integration in the Intelligence Signal Pipeline already exists. Add relevance scoring against user interests (stored in Qdrant `preferences` collection). Push only high-relevance items.

3. **Phase 3 (Pattern-based):** After accumulating interaction history, detect recurring patterns (e.g., "user always asks about X before Y"). This requires the observation log from topic 3's observational memory pattern.

### Sources
- [Proactive AI (Big Think)](https://bigthink.com/science-tech/proactive-ai/)
- [ProActLLM Workshop](https://proactllm.github.io/)
- [Proactive AI 2026 (Alpha Sense)](https://www.alpha-sense.com/resources/research-articles/proactive-ai/)
- [State of AI Agents 2026 (Prosus)](https://www.prosus.com/news-insights/2026/state-of-ai-agents-2026-autonomy-is-here)
- [Agentic AI Trends 2025 (Svitla)](https://svitla.com/blog/agentic-ai-trends-2025/)
- [Agent Memory Paper List (GitHub)](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)

---

## 7. Knowledge Freshness and Staleness

### Context

Qdrant's `knowledge` collection has 2,547 points. As documents update, embeddings become stale. The question is how to detect and manage this systematically.

### The Problem

A RAG system works well for ~3 months, then knowledge staleness compounds:
- Documents update but embeddings don't
- New terminology isn't recognized
- Outdated info ranks higher than current info (embedding proximity bias)
- Embedding drift from partial re-embeddings creates geometry misalignment

### Proven Patterns (2025-2026)

1. **Content hash comparison:** Hash document content at embedding time. Store hash in Qdrant payload. On re-indexing scan, compare hashes. Only re-embed changed documents. Cost: pennies per document ($0.001-$0.01 per doc with standard models).

2. **Time-weighted retrieval:** Add `embedded_at` timestamp to Qdrant payloads. Apply decay function to similarity scores:
   ```
   final_score = similarity * exp(-lambda * age_days)
   ```
   Newer content gets a boost without re-embedding everything.

3. **Event-driven re-embedding:** Don't batch-refresh on a schedule. Trigger re-embedding when source content changes (file watcher, git webhook, RSS update). CDC (Change Data Capture) pipelines achieve sub-minute freshness but triple complexity.

4. **Embedding version tracking:** Store model version + preprocessing config hash with each point. If any pipeline component changes, flag all affected points for re-embedding.

5. **Monthly full-corpus validation:** Even with incremental updates, run a monthly scan comparing all content hashes. Catches missed updates.

### Embedding Drift Details

Partial re-embeddings (e.g., re-embedding 20% of corpus) create geometric misalignment in vector space. A document that ranked #2 last week might rank #8 because the geometry around it shifted. Recall drops from 0.92 to 0.74 with no log evidence.

**Mitigation:** If you change any part of the pipeline (model, preprocessing, chunking), re-embed the entire corpus. At 2,547 points with Qwen3-Embedding-0.6B running locally, full re-embedding takes minutes and costs nothing.

### Recommendation

**Implement a four-layer freshness system:**

1. **Payload metadata:** Every Qdrant point gets `content_hash`, `embedded_at`, `source_path`, `embedding_model_version`
2. **Time-weighted scoring:** Use Qdrant's Score-Boosting Reranking to blend similarity with freshness
3. **Content hash pipeline:** On knowledge ingestion, compute SHA-256 of source content. Skip re-embedding if hash matches. Store in Qdrant payload.
4. **Monthly audit:** Scheduled job (existing 5:30 AM cycle) that scans all points, flags stale hashes, triggers re-embedding for changed content

At 2,547 points, full re-embedding is trivial (~5 minutes on DEV's 5060Ti). The freshness system is primarily about tracking what changed, not about computational cost.

### Sources
- [Knowledge Drift (Medium)](https://medium.com/@leeladesai/knowledge-drift-the-silent-ai-killer-in-rag-models-034eb35c7af4)
- [RAG in 2025: 7 Strategies (Morphik)](https://www.morphik.ai/blog/retrieval-augmented-generation-strategies)
- [RAG Infrastructure Production Guide (Introl)](https://introl.com/blog/rag-infrastructure-production-retrieval-augmented-generation-guide)
- [Embedding Drift: The Silent Killer (DEV Community)](https://dev.to/dowhatmatters/embedding-drift-the-quiet-killer-of-retrieval-quality-in-rag-systems-4l5m)
- [Detecting Embedding Drift (Decompressed)](https://decompressed.io/learn/embedding-drift)
- [RAG in 2026: Beyond Vector Embeddings (Prism Labs)](https://www.prismlabs.uk/blog/rag-beyond-vector-embeddings-2026)
- [Embedding Update Strategies (Milvus)](https://milvus.io/ai-quick-reference/what-strategies-can-be-used-to-update-or-improve-embeddings-over-time-as-new-data-becomes-available-and-how-would-that-affect-ongoing-rag-evaluations)
- [From RAG to Context: 2025 Review (RAGFlow)](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)

---

## 8. Personal Data Indexing

### Context

Athanor aims to index personal documents (emails, calendar, notes, files) for AI retrieval. This is a sovereign system -- all data stays local. Privacy concerns are architectural, not regulatory (single-operator homelab).

### Best Practices for Self-Hosted Personal RAG

**Chunking strategies for personal data:**

| Data Type | Chunk Strategy | Size | Rationale |
|-----------|---------------|------|-----------|
| **Emails** | Per-email (subject + body + metadata) | 256-512 tokens | Emails are natural semantic units |
| **Calendar** | Per-event (title + description + attendees + time) | 128-256 tokens | Small, structured, time-anchored |
| **Notes (Markdown)** | Semantic chunking by heading | 512-1024 tokens | Preserve section coherence |
| **Files (PDFs)** | Page-level with heading extraction | 512-1024 tokens | Page boundaries are natural breaks |
| **Chat history** | Per-conversation thread | Variable | Conversational context is a unit |
| **Code** | Per-function/class | Variable | Logical code units |

**Metadata is critical for personal data:**
- `source_type` (email/calendar/note/file)
- `timestamp` (creation/modification)
- `author` / `sender`
- `tags` / `categories`
- `file_path` (for attribution)

**Privacy architecture (even for local systems):**
- Separate collections by sensitivity tier (personal, work, public)
- Access control metadata in Qdrant payloads
- PII redaction option for shared collections
- Audit trail of what was indexed and when

### Existing Tools Worth Examining

- **Reor** (GitHub: reorproject/reor): AI note-taking app with automatic linking and semantic search. Uses LanceDB internally. Local-first, Obsidian-like editor.
- **RAG Builder** (various implementations): Transforms Markdown vaults into searchable knowledge bases using LangChain's `RecursiveCharacterTextSplitter`.
- **LightRAG 1.5.0:** Supports PostgreSQL and Neo4j backends, RAGAS evaluation, Langfuse tracing.

### Case Study: Eric J. Ma (March 2026)

Reduced knowledge management overhead from 30-40% to <10% of his time using Obsidian + AI coding agents. Key insight: "Plain text turned out to be exactly the right format for 2025-2026 era knowledge management." No proprietary formats, no vendor lock-in, AI agents process it natively.

### Recommendation for Athanor

**Index personal data into Qdrant using source-specific chunking strategies:**

1. **Create dedicated Qdrant collections** by data type (or use payload filtering on a unified collection):
   - `personal_docs` -- notes, documents, files
   - `personal_comms` -- emails, messages (when/if integrated)
   - `personal_calendar` -- events and schedules

2. **Use semantic chunking** (split by meaning, not fixed size) for notes and documents. The existing Qwen3-Embedding-0.6B handles this well.

3. **Rich metadata payloads:** timestamp, source, author, tags, content_hash, file_path

4. **Google Drive integration** (blocked by OAuth -- Shaun blocker) would cover ~40% of personal data

5. **Start with Obsidian vault** or equivalent markdown notes. Easiest to index, highest value per effort.

### Sources
- [RAG for Personal Knowledge Management: Obsidian (dasroot.net)](https://dasroot.net/posts/2025/12/rag-personal-knowledge-management-obsidian-integration/)
- [Reor Project (GitHub)](https://github.com/reorproject/reor)
- [Mastering PKM with Obsidian and AI (March 2026)](https://ericmjl.github.io/blog/2026/3/6/mastering-personal-knowledge-management-with-obsidian-and-ai/)
- [AI Document Indexing (Infrrd)](https://www.infrrd.ai/blog/ai-document-indexing)
- [RAG Implementation Guide (Mayhemcode)](https://www.mayhemcode.com/2025/12/rag-implementation-guide-embedding.html)

---

## 9. RAG Failure Modes at Scale

### Context

Athanor's knowledge base is at 2,547 points -- well below the ~10K threshold where most failure modes emerge. Understanding these now prevents architectural decisions that would compound later.

### Failure Mode Taxonomy

| Failure Mode | Threshold | Severity | Detectability |
|-------------|-----------|----------|---------------|
| **Embedding drift** | Any partial re-embedding | High | Very low (gradual, invisible) |
| **Chunking mismatch** | Any poorly chunked document | High | Medium (audit chunk boundaries) |
| **Query-document mismatch** | Always present | Medium | Low (queries are short, chunks are long) |
| **Dimensionality collapse** | 100K+ documents | High | Low (distances compress) |
| **Index sync staleness** | 10K+ daily updates | High | Medium (orphaned vectors) |
| **Multi-hop reasoning failure** | Complex queries | High | Low (correct facts, wrong synthesis) |
| **Context position bias** | LLMs always | Medium | Low (LLMs favor early/late context) |
| **Citation hallucination** | Always present | Medium | Medium (verify citations post-generation) |
| **Temporal staleness** | Any evolving corpus | Medium | High (check timestamps) |
| **Cross-document contradictions** | Growing corpus | High | Very low (no contradiction detection) |

### Quantitative Benchmarks

| Metric | Target | Notes |
|--------|--------|-------|
| TTFT p90 | <2 seconds | Autoscaling trigger |
| Semantic cache lookup | <100ms | No perceptible delay |
| Hybrid recall improvement | +1-9% over vector-only | Document type dependent |
| Semantic cache cost savings | 68.8% LLM cost reduction | Typical workload |
| Optimal chunk size (factoid) | 256-512 tokens | Sweet spot |
| Optimal chunk size (analytical) | 1024 tokens | Complex reasoning |
| Overlap | 10-20% | Prevents context loss at boundaries |

### Industry Reality (2026)

- **72% of enterprise RAG systems fail in their first year**
- **80% require complete architectural redesign** (not incremental fixes)
- The breaking point is usually index sync at scale, not retrieval quality

### What Breaks at 10K+ Documents

1. **Vector space density:** Embedding space becomes increasingly dense. Distances between semantically different chunks compress. What should be distinct clusters blur together.

2. **Orphaned vectors:** Superseded content leaves stale vectors. Without explicit deletion tracking, the index accumulates ghost documents.

3. **Partial re-embedding:** Re-embedding 20% of the corpus creates two embedding populations. Cross-population similarity scores are unreliable.

4. **Batch re-indexing lag:** 24-hour freshness windows mean orphaned vectors persist for days.

### Recommendation for Athanor

**Invest in pipeline hygiene now, before scale forces it:**

1. **Versioned embeddings:** Store `embedding_model`, `embedding_version`, `preprocessing_hash` in every Qdrant payload
2. **Content hashing:** SHA-256 of source content, stored in payload. Skip re-embedding if hash matches.
3. **Explicit deletion tracking:** When source document is removed/updated, delete old Qdrant point before inserting new one. Never leave orphans.
4. **Chunk quality monitoring:** Log chunk sizes, overlap percentages. Flag chunks <100 tokens or >1500 tokens.
5. **Hybrid search from day one:** Dense (Qwen3-Embedding) + sparse (miniCOIL) + metadata filters. Don't rely on single retrieval method.
6. **Semantic cache:** Already implemented (`llm_cache` collection). Ensure similarity threshold is 0.90-0.95.

### Sources
- [Ten Failure Modes of RAG (DEV Community)](https://dev.to/kuldeep_paul/ten-failure-modes-of-rag-nobody-talks-about-and-how-to-detect-them-systematically-7i4)
- [5 Reasons Standard RAG Dies at Scale (RAGAboutIt)](https://ragaboutit.com/5-reasons-standard-rag-dies-at-scale-and-what-replaces-it/)
- [RAG at Scale 2026 (Redis)](https://redis.io/blog/rag-at-scale/)
- [Embedding Drift: Silent Killer (Decompressed)](https://decompressed.io/learn/embedding-drift)
- [Chunking Strategies 2026 (Firecrawl)](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [RAG Failure Modes (Snorkel)](https://snorkel.ai/blog/retrieval-augmented-generation-rag-failure-modes-and-how-to-fix-them/)
- [Document Chunking: 9 Strategies (LangCopilot)](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide)

---

## 10. Conversation Context Persistence

### Context

Athanor's 9 agents need to maintain conversation context across sessions. Current approach: LangGraph `InMemorySaver` (lost on restart) + Qdrant `conversations` collection for long-term search. The question is what works better than naive vector similarity for conversation retrieval.

### State of the Art (2025-2026)

The industry has converged on **context engineering** as a discipline -- treating conversation context as a first-class system with its own architecture, lifecycle, and constraints. Simply enlarging context windows delays the problem but introduces "context rot" where performance degrades with more history.

### Approaches Compared

| Approach | Mechanism | Quality | Cost | Complexity |
|----------|----------|---------|------|------------|
| **Full context** (all messages) | Entire conversation in prompt | Baseline | Highest (26K tokens/conv) | Lowest |
| **Sliding window** | Last N messages | Poor for long conversations | Low | Lowest |
| **Vector retrieval** (naive) | Embed messages, retrieve similar | Good for factoid recall | Medium | Medium |
| **Mem0 Extract+Update** | LLM extracts facts, stores selectively | 66.9% LoCoMo | 90% less tokens | Medium |
| **Letta Core+Recall** | Agent-editable blocks + searchable history | 74.0% LoCoMo | Variable | High |
| **Observational Memory** (Mastra) | Observer/Reflector compress to dated log | **94.87% LongMemEval** | 5-40x less tokens | Medium |

### Why Observational Memory Wins

The key insight: **conversation history isn't a retrieval problem, it's a compression problem.** You don't need to search past conversations -- you need a compressed, up-to-date representation of what happened.

Mastra's approach:
1. Conversations accumulate normally
2. At 30K unprocessed tokens, Observer compresses into dated observations
3. Observations append to an always-in-context log
4. At 40K observation tokens, Reflector consolidates the log
5. The main agent sees the observation log -- no vector search needed

**Why this beats vector retrieval:**
- No retrieval latency (observations are in-context)
- No relevance ranking errors (everything important is already compressed)
- No context position bias (log is structured, not a dump of raw messages)
- Enables **prompt caching** (stable prefix = cached across turns)
- 3-6x compression for text, 5-40x for tool outputs

### Implementation for Athanor

**Three-tier conversation persistence:**

1. **Tier 1: Active Context (Redis)**
   - Current conversation thread for each agent
   - Observation log (compressed history)
   - Always in memory, sub-ms access
   - This is the working memory

2. **Tier 2: Searchable History (Qdrant)**
   - Completed conversation summaries (not raw messages)
   - Extracted facts and decisions
   - Used for cross-conversation recall ("what did we discuss about X last week?")
   - The `conversations` collection already exists

3. **Tier 3: Graph Relationships (Neo4j)**
   - Entity relationships extracted from conversations
   - Temporal edges ("discussed X on date Y")
   - Used for multi-hop reasoning ("what topics are connected to X?")

**Observational Memory integration:**
- Observer process runs as a LangGraph background node
- Triggered when unprocessed message tokens exceed threshold (configurable, start at 30K)
- Reflector runs when observation log exceeds threshold (start at 40K)
- Both use Qwen3.5-27B on FOUNDRY (fast, local, zero cost)
- Observation logs stored in Redis with TTL (active conversations) and persisted to Qdrant (completed conversations)

### Key Research Finding

"The hard lesson of 2025 was that more data and bigger models alone don't guarantee success -- understanding and architecture do." (Context Engineering paradigm)

95% of organizations saw no measurable ROI from enterprise GenAI in 2025, with "context rot" being a primary cause -- simply storing more history without managing it degrades performance.

### Recommendation

**Implement Mastra-style observational memory for active conversations, with Qdrant + Neo4j for cross-session recall.** This combines the best of both worlds: efficient in-context memory during active sessions, and structured long-term memory for historical recall.

### Sources
- [Memory for AI Agents (The New Stack)](https://thenewstack.io/memory-for-ai-agents-a-new-paradigm-of-context-engineering/)
- [AI Memory vs Context Understanding (Sphere)](https://www.sphereinc.com/blogs/ai-memory-and-context/)
- [Observational Memory (Mastra)](https://mastra.ai/research/observational-memory)
- [Agent Memory (Letta)](https://www.letta.com/blog/agent-memory)
- [Google MemoryService (ADK)](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/)
- [Redis AI Agent Memory](https://redis.io/blog/ai-agent-memory-stateful-systems/)
- [AI Agent Architecture 2026 (Redis)](https://redis.io/blog/ai-agent-architecture/)

---

## Synthesis: Athanor Knowledge Architecture Roadmap

### What's Already Right
- **Qdrant + Neo4j + Redis** is the correct tri-store architecture (matches or exceeds Letta/Mem0)
- **Hybrid search** (dense + keyword) is implemented
- **Semantic cache** (`llm_cache` collection) is implemented
- **8 Qdrant collections** provide good separation of concerns
- **Self-improvement loop** with proactive schedules is ahead of industry

### Immediate Actions (No New Infrastructure)

| Action | Effort | Impact | Depends On |
|--------|--------|--------|------------|
| Replace BM25 with miniCOIL sparse vectors | Small | +2-5% retrieval quality | FastEmbed v0.7+ |
| Add freshness metadata to Qdrant payloads | Small | Prevents staleness | Code change only |
| Wire `QdrantNeo4jRetriever` into agents | Medium | +20% accuracy on multi-hop | `neo4j_graphrag[qdrant]` |
| Implement Mem0-style fact extraction pipeline | Medium | 90% token reduction on context | Qwen3.5-27B |
| Enable Score-Boosting Reranking | Small | Blend similarity + freshness | Qdrant feature |
| Enable MMR for diversity | Small | Reduces duplicate chunks | Qdrant feature |

### Medium-Term (New Patterns, Existing Infrastructure)

| Action | Effort | Impact | Depends On |
|--------|--------|--------|------------|
| Observational memory for conversations | Medium | 94.87% context retention, 5-40x compression | Observer/Reflector agents |
| HippoRAG v2 integration | Large | Multi-hop QA improvement (~7% F1 lift) | NER/OpenIE pipeline |
| Personal data indexing pipeline | Large | Unlock personal knowledge for agents | Google OAuth (blocker) |
| Proactive morning briefing | Medium | Context push before user asks | Calendar + RSS integration |

### Not Worth Doing Now

| Technology | Why Not |
|-----------|---------|
| MS GraphRAG | $33K/5GB construction cost, no local LLM support |
| ColPali/ColQwen2 | Text-primary corpus, visual retrieval not needed yet |
| Letta framework | Athanor's stack is already better infrastructure |
| Mem0 SaaS | Self-hosted is trivially better for sovereign system |
| BM42 | Experimental, doesn't outperform BM25 (acknowledged by Qdrant) |

---

*Last updated: 2026-03-09*
