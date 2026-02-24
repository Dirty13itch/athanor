# Intelligence Layers — How Agents Become Intelligent Over Time

*The self-improving loop. The furnace feeding itself. Extends ADR-008.*

---

## Layer 1 — Reactive Intelligence (current state)

Each agent responds to requests or schedules. No memory between invocations beyond what's in the prompt. The supervisor classifies input and routes to the right agent. Agents call vLLM, get a response, return it.

Simple, debuggable, working. This is where we are now.

---

## Layer 2 — Accumulated Knowledge (next phase)

The Knowledge Agent runs proactively at 3 AM daily. It:

1. Indexes all documents in the repo (CLAUDE.md, ADRs, research docs, project docs)
2. Processes conversation transcripts and session logs
3. Generates embeddings using Qwen3-Embedding-0.6B on Node 1 GPU 4 (port 8001, 1024-dim)
4. Stores embeddings in Qdrant (Node 1:6333, `knowledge` and `conversations` collections)
5. Tracks system state changes over time
6. Builds a knowledge graph of entities, relationships, decisions, and their rationale

When any agent receives a request, the supervisor first queries the Knowledge Agent's accumulated data for relevant context:

- **Research Agent** gets "here's what we've already researched about this topic" before searching the web
- **General Assistant** gets "here's what Shaun has previously said about this" before answering
- **Media Agent** gets "here's Shaun's viewing history and patterns" before making recommendations
- **Home Agent** gets "here's what happened the last 50 times this event fired" before deciding

The more the system is used, the more knowledge accumulates, the better every agent performs.

---

## Layer 3 — Pattern Recognition (future)

Agents recognize patterns in their own operation and user behavior:

- **Media Agent** tracks which shows get watched vs abandoned → adjusts recommendation weights, potentially auto-pauses series matching abandonment patterns
- **Home Agent** learns occupancy patterns over weeks → stops treating regular patterns as events (Shaun always gets up at 6 AM on weekdays — don't fire "motion detected" as novel)
- **Research Agent** learns which sources Shaun finds useful → prioritizes those in future searches
- **Creative Agent** tracks which generation parameters produce kept vs regenerated results → adjusts defaults

**Requirement:** A feedback signal. The system needs to know whether its outputs were good. For some agents this is implicit (Media Agent: was the show watched to completion?). For others it needs explicit signals (thumbs up/down, tracked in the knowledge store).

---

## Layer 4 — Self-Optimization (endgame)

The system monitors its own infrastructure and performance:

- Which models produce the best results for which tasks? (A/B test model versions)
- Which GPU allocation minimizes latency for the current workload mix?
- Which agent configurations get the best satisfaction scores?
- When better models are released, auto-evaluate against baseline and recommend upgrades
- When inference patterns show a GPU is consistently underutilized, suggest reallocation
- When knowledge accumulation shows diminishing returns, trigger summarization/compression

This is where Athanor genuinely starts managing itself. The Knowledge Agent becomes an optimization agent — not just accumulating knowledge but using it to improve the system that accumulates it.

The recursive nature of the furnace feeding itself.

---

## Infrastructure Dependencies

| Layer | Requires | Status |
|-------|----------|--------|
| 1 (Reactive) | vLLM, LangGraph, agents | Running |
| 2 (Knowledge) | Qdrant, embedding model, Knowledge Agent | Qdrant + embeddings deployed; Knowledge Agent planned |
| 3 (Patterns) | Feedback signals, historical data, pattern detection | Future |
| 4 (Self-Optimization) | All above + metrics correlation + auto-evaluation | Endgame |
