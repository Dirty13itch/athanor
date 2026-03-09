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

*Research agent results pending for this section — update when abf693a2562bb0c60 completes.*

**Preview from existing knowledge:**
- Qdrant BM42 sparse vectors now production-ready. Add sparse vector index to `knowledge` collection for hybrid dense+sparse — better recall for keyword-heavy queries.
- GraphRAG (LightRAG/HippoRAG variants) beat standard vector RAG for multi-hop queries. Athanor's Qdrant + Neo4j hybrid is architecturally aligned.
- Observation masking for context window: mark old observations with `[truncated]`, keep reasoning. Cheaper and often better than summarization.

---

## 5. Priority Actions (From This Research)

### Immediate (no approval needed)
- [x] vLLM upgrade planning: document upgrade path for 0.16.0 → 0.17.0
- [ ] ntfy wired to agent escalations (done this session)
- [ ] Circuit breaker wired to task worker (circuit_breaker.py exists, not connected)
- [ ] Add sparse vector index to `knowledge` Qdrant collection (Tier 2 win)

### Infrastructure (requires planning)
- [ ] vLLM 0.17.0 upgrade: WORKSHOP first, then FOUNDRY (DEV test → WORKSHOP → FOUNDRY)
- [ ] FLUX.2 Klein swap: replace FLUX.1 Schnell in ComfyUI with FLUX.2 Klein (Apache 2.0, faster)
- [ ] Qwen3.5-Coder-Next evaluation: test on WORKSHOP, compare vs current coding-agent quality

### Research to document (after remaining agents complete)
- [ ] Knowledge architecture update (abf693a2562bb0c60 results)
- [ ] Local AI productivity patterns (a7e43bcca72fc9be0 results)
- [ ] Self-improving AI systems (a299b928323e5e4d4 full results)

---

## Sources

- arxiv:2503.13657 — MAST failure taxonomy (1600+ traces)
- arxiv:2601.09527 — Consumer Blackwell LLM benchmarks (Feb 2026)
- Deloitte 2026 AI Agent Orchestration report
- JetBrains observation masking research (Dec 2025)
- vLLM 0.17.0 release notes (March 7, 2026)
- MiniCPM-o-4.5 GitHub (March 2026)
- Qwen2.5-Omni blog (March 2025)
- Northflank STT benchmarks 2026
- NVIDIA Parakeet-TDT technical blog
