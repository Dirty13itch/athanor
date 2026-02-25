# Intelligence Layers — How Agents Become Intelligent Over Time

*The self-improving loop. The furnace feeding itself. Extends ADR-008.*

Last updated: 2026-02-25

---

## Layer 1 — Reactive Intelligence (current state)

Each agent responds to requests. No memory between invocations beyond what's in the conversation thread (InMemorySaver, not persistent across restarts). The agent server routes by model name to the correct LangGraph agent. Agents call tools, get results, generate responses via LiteLLM → vLLM.

Simple, debuggable, working. This is where we are now.

**What works:** 6 agents live, 24 services healthy, all tools functional, streaming responses, tool call visualization in dashboard.

**What's missing:** No memory across sessions. No learning from past interactions. No proactive behavior. No inter-agent coordination.

---

## Layer 2 — Accumulated Knowledge (partially deployed)

### What's Deployed

The Knowledge Agent indexes all project documentation:
1. `scripts/index-knowledge.py` scans 81 docs, chunks into 922 vectors
2. Embeddings via Qwen3-Embedding-0.6B on Node 1 GPU 4 (port 8001, 1024-dim)
3. Stored in Qdrant `knowledge` collection (Node 1:6333)
4. Neo4j graph stores structural relationships (30 nodes, 29 relationships)
5. Any agent can query accumulated knowledge via Knowledge Agent tools

### What's Missing for Full Layer 2

**Preference storage:** A `preferences` Qdrant collection for explicit user signals.

Implementation:
- Collection schema: 1024-dim embeddings + metadata (agent, category, timestamp, signal_type)
- Signal types: `thumbs_up`, `thumbs_down`, `remember_this`, `config_choice`
- Agents query preferences before acting: "Has Shaun expressed a preference about this?"
- Preferences are semantic — "I prefer dark themes" matches queries about UI colors
- Editable via dashboard Preferences page

**Activity logging:** An `activity` Qdrant collection for every agent action.

Implementation:
- Every agent action logged: agent name, action type, input summary, output summary, timestamp, confidence score
- Queryable by agent, time range, action type
- Dashboard Activity Feed renders this collection
- Enables pattern detection in Layer 3

**Conversation history:** The `conversations` collection exists in Qdrant but isn't populated.

Implementation:
- After each agent interaction, embed the conversation and store
- Metadata: agent, timestamp, topic tags, user satisfaction signal (if provided)
- Enables "here's what Shaun previously asked about X" context injection

**Proactive indexing:** Knowledge indexing is currently manual (`python3 scripts/index-knowledge.py`).

Implementation:
- Cron job on DEV or Node 1 at 03:00 (after backups)
- Watch for git commits or file changes → trigger re-index
- Incremental updates (only re-embed changed documents)

### Layer 2 Context Injection

When fully deployed, the agent server's request handler injects relevant context before routing to the agent:

```
Request arrives
  → Query preferences collection for agent-specific priors
  → Query conversations collection for relevant history
  → Query knowledge collection for topic context
  → Inject results as system message prefix
  → Route to agent with enriched context
```

Each agent gets different context:
- **Research Agent** → "Here's what we've already researched about this topic"
- **General Assistant** → "Here's what Shaun has previously said about this"
- **Media Agent** → "Here's Shaun's viewing history and content preferences"
- **Home Agent** → "Here's what happened the last 50 times this event fired"

The more the system is used, the more knowledge accumulates, the better every agent performs.

---

## Layer 3 — Pattern Recognition (future)

Agents recognize patterns in their own operation and user behavior.

### Per-Agent Pattern Sources

| Agent | Implicit Signals | Explicit Signals | Learned Patterns |
|-------|-----------------|------------------|-----------------|
| **Media** | Shows watched to completion, episodes skipped, search→add rate | Thumbs up/down on recommendations | Genre preferences, quality preferences, binge patterns |
| **Home** | Automation overrides, manual adjustments, time-of-day activity | "Too cold", "too bright" feedback | Occupancy routines, comfort baselines, seasonal adjustments |
| **Research** | Sources clicked through, reports that led to ADRs | "That source was useful/useless" | Source quality ranking, preferred report format |
| **Creative** | Images kept vs regenerated, prompt modifications | "I like this style", parameter preferences | Style preferences, prompt patterns that work |
| **Knowledge** | Queries that return useful results, documents frequently cited | "That doc was outdated" | Retrieval strategy, importance weighting, gap detection |

### Escalation Protocol

Agents assess confidence before acting. Three tiers:

| Confidence | Action | Notification | Example |
|------------|--------|-------------|---------|
| > 0.8 | Act autonomously | Log to activity feed | Home Agent dims lights at usual bedtime |
| 0.5 – 0.8 | Act but notify | Dashboard notification bell | Media Agent added a show matching strong preference pattern |
| < 0.5 | Ask before acting | Chat panel + hold in queue | Home Agent wants to change thermostat based on weak weather signal |

**Thresholds are tunable per-agent and per-action-type:**

| Action Category | Stakes | Default Threshold for Autonomous |
|-----------------|--------|----------------------------------|
| Status queries (read-only) | None | 0.0 (always act) |
| Routine adjustments (lights, temp ±1) | Low | 0.5 |
| Content additions (add show/movie) | Medium | 0.8 (always ask) |
| Deletions (remove content, disable automation) | High | 0.95 (almost always ask) |
| Configuration changes | High | 0.95 |
| Security-related actions | Critical | 1.0 (never autonomous) |

Thresholds are stored in agent config and adjustable via the dashboard Preferences page.

### Pattern Detection Jobs

Background jobs (hourly or daily) analyze accumulated activity logs:

1. **Frequency analysis** — What actions happen most often? What time of day?
2. **Outcome tracking** — Which agent actions were followed by positive vs negative signals?
3. **Sequence detection** — What patterns of actions tend to happen together?
4. **Drift detection** — Have preferences changed over time? (e.g., stopped watching genre X)
5. **Gap detection** — What questions does Shaun ask that agents can't answer?

Results are stored as pattern records in preferences collection, queryable by agents.

---

## Layer 4 — Self-Optimization (endgame)

The system monitors its own performance and optimizes:

### Model Performance Tracking
- Track response quality per model per task type
- When new models are released, run baseline evaluation
- Recommend model swaps when improvement exceeds threshold
- A/B test model versions on non-critical requests

### Resource Optimization
- Correlate GPU utilization with request patterns
- Identify GPUs that are consistently underutilized
- Recommend reallocation (e.g., move embedding to CPU, free GPU for creative)
- vLLM Sleep Mode scheduling based on usage patterns (ADR-018)

### Agent Performance
- Track which agents get the most/least use
- Identify agents with high "ask again" rates (indicating poor first response)
- Recommend system prompt adjustments based on satisfaction patterns
- Auto-tune temperature based on task type outcomes

### Knowledge Management
- Detect when knowledge accumulation shows diminishing returns
- Trigger summarization/compression of old data
- Identify stale documents that need updating
- Recommend new indexing sources

This is where Athanor genuinely starts managing itself. The recursive nature of the furnace feeding itself.

---

## Infrastructure Dependencies

| Layer | Requires | Status |
|-------|----------|--------|
| 1 (Reactive) | vLLM, LangGraph, LiteLLM, tool APIs | **Running** |
| 2 (Knowledge) | Qdrant, Neo4j, embedding model, Knowledge Agent | **Partially deployed** — knowledge indexed, preferences/activity/conversations not yet |
| 3 (Patterns) | Preference collection, activity logging, pattern detection jobs, escalation protocol | Planned (Tier 7) |
| 4 (Self-Optimization) | All above + metrics correlation + A/B testing + auto-evaluation | Future |

## Implementation Sequence

1. **Add `preferences` and `activity` Qdrant collections** — Schema definition, collection creation, basic CRUD endpoints on agent server
2. **Add activity logging middleware** — Every agent action logged automatically
3. **Add preference storage/retrieval** — Endpoints + agent context injection
4. **Implement escalation protocol** — Confidence scoring + threshold config + notification routing
5. **Populate conversation history** — Post-interaction embedding + storage
6. **Pattern detection jobs** — Hourly/daily analysis of activity logs
7. **Dashboard integration** — Activity Feed, Preferences, Insights pages

See `docs/BUILD-MANIFEST.md` Tier 7 for the full implementation plan.
