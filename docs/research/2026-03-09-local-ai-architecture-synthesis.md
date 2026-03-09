# Local AI Architecture Synthesis
*Research sweep: 2026-03-09. Three parallel research agents, ~150k tokens consumed.*

---

## Status: March 2026 Snapshot

**What's confirmed about Athanor's stack:**
- Qwen3.5-27B-FP8 TP=4 on FOUNDRY: validated production pattern (Blackwell consumer research, Feb 2026)
- Qwen3.5-35B-A3B-AWQ on WORKSHOP 5090: validated — 5090 is 2.6× A100 80GB throughput
- LangGraph: confirmed fastest/most battle-tested agentic framework (no migration needed)
- vLLM 0.17.0 released March 7 — FOUNDRY is on 0.16.0 → upgrade for FlashAttention 4 + better Qwen3.5 GDN support
- SGLang broken for Qwen3.5-35B-A3B-AWQ (#19644) — confirmed, vLLM is correct choice

---

## 1. Multi-Agent Orchestration (What Actually Works in Production)

### Failure Mode Taxonomy (MAST, 2025 peer-reviewed, 1600+ traces)

14 failure modes. 79% are **coordination failures**, not model quality:

**System Design (40%):**
- Incorrect task decomposition — orchestrator splits request badly
- Disobeying task specifications — agent ignores constraints
- Missing error handling — no recovery path

**Inter-Agent Misalignment (35%):**
- Information withholding — agent doesn't pass context downstream
- Conversation resets — agent loses context between turns
- Incompatible output formats — schema mismatch breaks handoffs

**Task Verification (25%):**
- Hallucinated success — agent claims completion when it failed
- Premature termination — stops before actually done
- Verification failures — orchestrator can't tell if agent succeeded

**Hallucination Cascades** are the real production killer. An invented SKU in step 1 becomes a real order in step 3. Mitigation: each agent validates upstream inputs before acting.

### Implication for Athanor
Your 9-agent system at 27B is right at the quality threshold for multi-agent coordination. At 27B the failure modes shift from "model too weak" to "coordination issues." This is exactly why iteration budgets, circuit breakers, and output schemas matter.

### Recommendations (not yet implemented)
1. **Iteration budgets**: max 10 turns per agent per workflow. Prevents infinite loops.
2. **Circuit breakers**: 3 failures in 5 min → route to fallback (general-assistant). Circuit breaker module already exists (`circuit_breaker.py`) but not wired to task worker.
3. **Observation masking** over summarization: keeps agent reasoning, replaces verbose old observations with placeholders. 50% token reduction, often *better* accuracy than summarization.
4. **Explicit handoff schema**: agent produces `{status, result, next_agent, context}` — not raw text.
5. **GWT workspace:consensus key**: broadcast current objective + critical blockers to all agents every planning cycle. Agents self-correct against it.

### What's Already Right
- Centralized orchestrator (Claude as COO) + 9 specialist agents — optimal architecture
- Redis Streams for task distribution — persistent, replay-capable
- Proactive scheduling with feedback loop — aligned with 2026 production patterns

---

## 2. Multi-Modal Capabilities (What's Deployable Now)

### Vision-Language (Sweet Spot for FOUNDRY/WORKSHOP)

| Model | VRAM | Quality | Use Case |
|-------|------|---------|----------|
| **MiniCPM-o-4.5** | 12-14GB (FP8) | Omni-modal | Full-duplex live audio+video+text. March 2026. Best streaming. |
| **Qwen2.5-VL-7B** | ~14GB | High | Document parsing, OCR, structured reasoning. Production-tested. |
| **Qwen2.5-Omni-7B** | ~16GB | High | Thinker-Talker architecture, text+image+audio+video. March 2025. |
| **MiniCPM-V-4.5** | ~16GB | High | 1.8M pixel support, OCR excellence, 1,075 tok/sec at 32 concurrent. |

**Key finding**: MiniCPM-o-4.5 (March 2026) is the full-duplex streaming leader. Runs on WORKSHOP 5060Ti (16GB) for interactive sessions, or FOUNDRY for batched inference. Full-duplex means it sees, hears, and speaks simultaneously.

### Speech-to-Text

| Model | VRAM | WER | RTF | Notes |
|-------|------|-----|-----|-------|
| **Parakeet-TDT-0.6B v3** | 2GB | 6.2% | 1500× | Best for streaming. NVIDIA NeMo required. |
| **Whisper Large-v3 Turbo** | ~3GB | 7.75% | 6× faster than v3 | Best universal (CPU-feasible, 99+ langs). |

Athanor already has `wyoming-whisper` on FOUNDRY. Parakeet is a significant upgrade if STT quality matters.

### Text-to-Speech

| Model | VRAM | Latency | Notes |
|-------|------|---------|-------|
| **Chatterbox-Turbo** | 1GPU | ~200ms | Fastest, sub-200ms end-to-end. |
| **Kokoro-82M** | CPU-feasible | <500ms | Lightweight, multilingual, real-time. |
| **CosyVoice2** | Integrated in MiniCPM-o | Streaming | Best if using MiniCPM-o anyway. |

`speaches` container already running on FOUNDRY:8200.

### Deployment Strategy (if adding multi-modal)

WORKSHOP 5060Ti (16GB) is ideal for:
- Qwen2.5-VL-7B (document understanding) — frees FOUNDRY for agent reasoning
- MiniCPM-o-4.5 (interactive omni-modal sessions)
- FLUX.2 Klein (image generation, Apache 2.0, faster than FLUX.1)

FOUNDRY 4090 (24GB, currently running Huihui-Qwen3-8B utility) is ideal for:
- Kokoro TTS (1GB) + STT (2GB) alongside utility model
- Or swap utility model for Parakeet + Kokoro + vision encoder

---

## 3. Bleeding-Edge News (March 2026)

### Model Landscape

**Active in production:**
- Claude Sonnet 4.6 (Feb 17) — matches Opus 4.6 in reasoning, same pricing. Can replace Opus-tier in agents.
- Claude Opus 4.6 (Feb 5) — agent teams, PowerPoint integration
- Qwen3.5-Coder-Next 80B MoE (3B active) — dominates open-weight coding benchmarks, outperforms DeepSeek V3.2
- DeepSeek V4 (Mar 3 expected) — 1T params, 32B active per token, native multimodal
- FLUX.2 family (Nov 2025) — 10× faster than FLUX.1, better text rendering, Apache 2.0 for Klein variant

**Not released yet:**
- Claude 5 ("Sonnet 5 Fennec" in Vertex AI logs, not official)
- Wan 3.0 (4K video, 3-min narratives, physics engine — expected H1 2026)
- Qwen3-Omni (early access, production by Q2 2026)

### vLLM 0.17.0 (March 7, 2026) — ACTION ITEM

Key improvements relevant to Athanor:
- **FlashAttention 4 backend** — significant throughput improvement
- **Native Qwen3.5 GDN layer support** with FP8 quantization
- **MTP speculative decoding** for Qwen3.5 — higher throughput
- **PyTorch 2.10.0 upgrade** (breaking: requires NGC container update)

FOUNDRY is on vLLM 0.16.0. The upgrade path:
1. Pull latest NGC container for Blackwell (sm_120 full support confirmed in 0.17.0)
2. Test on DEV first (vllm-embedding uses different container)
3. Deploy to WORKSHOP, then FOUNDRY

**Do not rush this.** PyTorch 2.10 is a breaking change. Test first.

### Consumer Blackwell Benchmarks (Feb 2026, arxiv:2601.09527)

Confirms the cluster choices:
- RTX 5090: 5,841 tokens/sec (Qwen 2.5-Coder-7B, batch 8) — 2.6× faster than A100 80GB
- RTX 5070 Ti: solid for 20B-27B models at W4A16/FP8
- ROI: $0.001-0.04/million tokens, hardware payback < 4 months vs cloud

64K context costs 40% throughput. Design agents to stay under 32K.

---

## 4. Knowledge Architecture (What's Next for Athanor's RAG)

*Full research doc: `docs/research/2026-03-09-knowledge-architecture-memory.md` (10 topics, 54 sources)*

### Key Corrections to Prior Assumptions

**BM42 is dead.** Qdrant acknowledged a benchmark error in their evaluation script. BM42 does not outperform BM25. The successor is **miniCOIL** — available now in FastEmbed v0.7+ via `Qdrant/minicoil-v1`. miniCOIL adds 4D semantic vectors per word (falls back to BM25 for unknown vocabulary), achieving +2-5% NDCG@10 over BM25 on standard benchmarks (MS MARCO +2.9%, NQ +4.9%, Quora +2.3%).

**Qdrant v1.15→v1.17 requires stepping.** v1.17 removed RocksDB in favor of gridstore. Cannot upgrade directly — must go v1.15→v1.16→v1.17.

### GraphRAG: HippoRAG v2 Wins for Homelab

| System | Multi-hop F1 (MuSiQue) | Indexing Tokens | Cost |
|--------|------------------------|-----------------|------|
| MS GraphRAG | Lowest | ~115M | $33K for 5GB corpus |
| LightRAG | Moderate | Moderate | Low |
| **HippoRAG v2** | **51.9 F1** (best) | **~9M** (12× less) | Low |

HippoRAG v2 wins on multi-hop QA without degrading simple QA. 12× fewer indexing tokens than MS GraphRAG. Native vLLM support — designed for local LLM deployment. Uses PPR (Personalized PageRank) which aligns with Neo4j's existing capabilities. Accepted at ICML '25.

**Caveat:** GraphRAG-Bench (ICLR 2026) notes GraphRAG frequently underperforms vanilla RAG on real-world tasks. The value scales with query complexity — factoid lookups → standard RAG wins; multi-hop synthesis → HippoRAG wins.

### Neo4j + Qdrant Hybrid: Official Package Now Exists

The `neo4j-graphrag-python` package provides `QdrantNeo4jRetriever`:
```python
from neo4j_graphrag.retrievers import QdrantNeo4jRetriever
retriever = QdrantNeo4jRetriever(
    driver=neo4j_driver, client=qdrant_client,
    collection_name="knowledge",
    id_property_external="id", id_property_neo4j="id"
)
results = retriever.search(query_vector=embedding, top_k=5)
```

Pipeline: Qdrant kNN (1-5ms) → extract entity IDs → Neo4j 2-hop Cypher expansion (5-20ms) → combine vector + graph context. Lettria measured +20% accuracy over vector-only search with this approach.

### Conversation Context: Observational Memory is the Breakthrough

| Approach | LongMemEval | Token Usage | Complexity |
|----------|-------------|-------------|------------|
| Letta Core+Recall | 74.0% | Variable | High |
| Mem0 Extract+Update | 66.9% | 90% less | Medium |
| **Mastra Observational** | **94.87%** | **5-40× less** | Medium |

Mastra's architecture: two background agents (Observer at 30K tokens, Reflector at 40K tokens) compress conversation history into dated observation logs. Main agent sees the compressed log — no vector search needed during active sessions. Enables prompt caching (stable prefix). 3-6× compression for text, 5-40× for tool outputs.

**Key insight:** Conversation history is a compression problem, not a retrieval problem. Athanor's Redis is the right store for observation logs (always in-context, sub-ms access).

### Athanor's Tri-Store is Already Correct

Athanor's Redis + Qdrant + Neo4j stack matches or exceeds Letta/Mem0 architectures. What's missing is the code patterns, not infrastructure:
- **Agent-driven memory management** (what to remember, forget, update) — needs implementation
- **Mem0-style fact extraction pipeline** — post-conversation extraction into Qdrant `knowledge` + Neo4j entities
- **Observational memory** — Observer/Reflector LangGraph background nodes for active conversations

### Qdrant 2025-2026 Feature Wins (Available Now)

- **Score-Boosting Reranking** — blend vector similarity with freshness timestamps or priority signals
- **MMR (Maximal Marginal Relevance)** — reduces near-duplicate chunks in results
- **Full-Text Filtering** — native multilingual tokenization (the payload text index we added is the entry point)
- **ACORN Algorithm** — higher-quality filtered HNSW queries

### Knowledge Freshness System Needed

At 3,026 points (growing), embedding drift will silently degrade retrieval quality. Every Qdrant point needs: `content_hash`, `embedded_at`, `source_path`, `embedding_model_version`. Content hash comparison enables skip-on-unchanged re-embedding. At our scale, full re-embedding takes ~5 minutes on DEV — the cost is tracking, not compute.

### ColPali: Not Yet

ColPali/ColQwen2 for visual document retrieval is not worth deploying now. Athanor's knowledge base is text-primary. Storage requirement (~60GB/million pages even with token pooling) and 2.5s/page indexing time make it overkill. Revisit when personal document scans enter the pipeline.

---

## 5. Local AI Productivity (What Actually Works)

*Full research doc: `docs/research/2026-03-09-local-ai-productivity-patterns.md` (54 sources, community consensus)*

### The Three Laws

**1. Model Quality Threshold.** Below ~70% on BFCL (tool calling), autonomous agent work produces more cleanup than value. Qwen3.5-27B-FP8 is estimated in the 70-80% range — works for well-defined tasks, unreliable on open-ended multi-step work. Claude Code (Anthropic) for anything requiring novel reasoning.

**2. The Complexity Budget.** Every model served, agent running, MCP server connected, and automation loop is a maintenance liability. Athanor at 9 agents + 13 MCPs + 42 containers is past the complexity cliff for a single operator. Audit ruthlessly.

**3. The Hybrid Pattern Is Not Optional.** No successful local AI practitioners run 100% local. Local = volume/privacy/cost. Cloud API = quality/reasoning/complexity. Not a tradeoff — a routing decision.

### Tool Calling: The Real Numbers

MCPMark (real-world multi-step agentic tasks, avg 16.2 turns, 17.4 tool calls) vs BFCL (single function calls):

| Model | BFCL Score | MCPMark Pass@1 |
|-------|-----------|----------------|
| GPT-5 Medium | 59% | **52.6%** |
| Claude Sonnet 4 | 70% | 28.1% |
| Qwen-3-Coder | N/A | 24.8% |

**2-3× reliability drop** from single-call benchmarks to real agentic workflows. This is the compound reliability problem:
- 5 sequential calls at 95%: 77% overall
- 10 sequential calls at 95%: 60% overall
- 5 sequential calls at 80%: 33% overall

**Design implication for Athanor:** Keep agent workflows to 2-4 tool calls per turn. Circuit breakers at 3 failures are correctly sized.

### Claude Code + Local Models

Infrastructure to route Claude Code to FOUNDRY:8000 is already in place (LiteLLM at VAULT:4000 has Anthropic API compatibility). What works: boilerplate generation, test writing, simple refactoring, documentation. What breaks: complex multi-file architecture, novel problem-solving, long tool-calling chains. Use hybrid routing — don't expect equivalent quality.

### Aider: No Qwen3.5 Benchmark Yet

The Aider polyglot leaderboard has no Qwen3.5 entries. Best open-source entries: DeepSeek V3.2-Exp at 74.2% (cloud-hosted), Qwen3-235B-A22B at 59.6%. Qwen2.5-Coder-32B at 73.7% is most battle-tested local option for Aider. **Testing Qwen3.5-27B-FP8 on Aider polyglot would fill a community gap.** Use `--edit-format whole` for MoE models; `--edit-format diff` only for validated dense 27B+ models.

### Goose: Not Ready for vLLM Yet

vLLM tool calling bug remains unresolved (Discussion #5914). Goose sees tools but cannot invoke them via vLLM endpoint. Workaround: test with Ollama backend. When fixed, Goose's recipe system is the most mature automation format in the ecosystem for scheduled unattended tasks. **Do not deploy as primary autonomous agent yet.**

### claude-squad: Single-Task Pattern Works

Agent Teams (native Claude) are still buggy — worktree isolation doesn't work (#28175), sessions crash, teammates stop on errors. claude-squad with single-task prompts is more reliable:
```
1. One well-defined task per session with clear acceptance criteria
2. 2-3 sessions max in parallel (not 5+)
3. Each session in its own git worktree
4. --yes for known-safe operations
5. Morning: review diffs, cherry-pick good work
```

### Highest-ROI Daily Workflows (In Order)

1. **IDE autocomplete (Continue.dev → FOUNDRY:8000)** — Zero latency, zero cost, daily value. The single highest-ROI local AI action.
2. **Test generation** — After implementing a feature, agent generates unit tests. 30-50% testing time saved.
3. **Code review first-pass** — Local model catches common issues before human review. CI failure logs fed back for collaborative fix loop.
4. **Morning intelligence briefing** — Miniflux RSS + local model summarization. Pieces already exist.
5. **Spec-to-code pipeline** — `spec.md` → Claude Code/Aider implementation. Waterfall in 15 minutes.

Complex multi-agent research workflows, autonomous code refactoring, home automation AI control are Tier 3 — impressive but low daily value relative to setup cost.

### Agent Count Assessment

Honest: 9 agents is probably 4 more than produce regular value. Top-4 (General Assistant, Coding, Research, Media) clearly justify themselves. Lower-use agents (Home, Creative, Knowledge, Stash, Data Curator) may be creating maintenance burden without proportional value. **Action: audit LangFuse traces for per-agent invocation frequency.**

---

## 6. Priority Actions (From This Research)

### Completed This Session
- [x] ntfy wired to agent escalations
- [x] Circuit breaker wired to task worker
- [x] `pending_approval` dashboard UI (Approve button, amber badge, filter)
- [x] Qdrant `knowledge` payload text index (BM25-style keyword search enabled)
- [x] Autonomy adjustments + improvement cycle added to `/learning` page
- [x] Knowledge architecture research synthesized (Section 4)
- [x] Local AI productivity research synthesized (Section 5)

### Immediate (no approval needed)
- [ ] **Continue.dev setup** — point at FOUNDRY:8000 for zero-latency autocomplete. Highest-ROI single action.
- [ ] **miniCOIL sparse vectors** — replace the payload text index with proper miniCOIL hybrid search (`Qdrant/minicoil-v1` via FastEmbed v0.7+). Modify `index-knowledge.py` and search code.
- [ ] **Wire `QdrantNeo4jRetriever`** — `pip install "neo4j_graphrag[qdrant]"`, integrate into agent context pipeline. +20% accuracy on multi-hop queries.
- [ ] **Freshness metadata** — add `content_hash`, `embedded_at`, `embedding_model_version` to all Qdrant payloads in indexing pipeline.
- [ ] **Audit LangFuse for agent invocation frequency** — determine which of the 9 agents get used daily vs. never.
- [ ] **Benchmark Qwen3.5-27B-FP8 on Aider polyglot** — community gap, fills a real need.

### Infrastructure (requires planning)
- [ ] **vLLM 0.17.0 upgrade** — DEV test → WORKSHOP → FOUNDRY. PyTorch 2.10 is breaking change. Do not rush.
- [ ] **FLUX.2 Klein swap** — replace FLUX.1 Schnell in ComfyUI (Apache 2.0, 10× faster).
- [ ] **Observational memory** — Observer/Reflector LangGraph background nodes for long-running agent conversations.
- [ ] **Mem0-style fact extraction** — post-conversation pipeline: extract facts → Qdrant `knowledge` + Neo4j entities.
- [ ] **Qdrant version check** — verify VAULT is not on v1.15 if planning v1.17 upgrade (must step through v1.16).

### Blocked on Shaun
- [ ] n8n "Intelligence Signal Pipeline" activation (2 min browser task at VAULT:5678)
- [ ] Google OAuth → Gmail + Calendar → morning briefing becomes useful
- [ ] Anthropic API key → Claude Code quality cascade routing

---

## Sources

**Multi-agent orchestration:**
- arxiv:2503.13657 — MAST failure taxonomy (1600+ traces)
- Deloitte 2026 AI Agent Orchestration report
- JetBrains observation masking research (Dec 2025)

**Multi-modal:**
- arxiv:2601.09527 — Consumer Blackwell LLM benchmarks (Feb 2026)
- MiniCPM-o-4.5 GitHub (March 2026)
- Qwen2.5-Omni blog (March 2025)
- Northflank STT benchmarks 2026
- NVIDIA Parakeet-TDT technical blog

**Infrastructure:**
- vLLM 0.17.0 release notes (March 7, 2026)

**Knowledge architecture (full citations in `2026-03-09-knowledge-architecture-memory.md`):**
- HippoRAG v2 — arxiv:2502.14802, ICML '25
- GraphRAG-Bench — ICLR '26
- Qdrant miniCOIL — qdrant.tech/articles/minicoil/
- Mastra observational memory — mastra.ai/research/observational-memory
- neo4j-graphrag-python — neo4j.com/docs/neo4j-graphrag-python/
- Lettria case study — qdrant.tech/blog/case-study-lettria-v2/

**Productivity patterns (full citations in `2026-03-09-local-ai-productivity-patterns.md`):**
- BFCL V4 — gorilla.cs.berkeley.edu/leaderboard.html
- MCPMark benchmark — multiple sources
- ToolScan taxonomy — arxiv:2411.13547
- Aider leaderboards — aider.chat/docs/leaderboards/
- Goose vLLM bug — github.com/block/goose/discussions/5914
- C Compiler experiment — anthropic.com/engineering/building-c-compiler
- ICLR 2026 Recursive Self-Improvement Workshop
