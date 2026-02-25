# Intelligence Layers — How Agents Become Intelligent Over Time

*The self-improving loop. The furnace feeding itself. Extends ADR-008.*

Last updated: 2026-02-25

---

## Layer 1 — Reactive Intelligence (deployed)

Each agent responds to requests. No memory between invocations beyond what's in the conversation thread (InMemorySaver, not persistent across restarts). The agent server routes by model name to the correct LangGraph agent. Agents call tools, get results, generate responses via LiteLLM → vLLM.

Simple, debuggable, working.

**What works:** 7 agents live, 25 services healthy, all tools functional, streaming responses, tool call visualization in dashboard, escalation protocol, GWT workspace.

**What's shallow:** Agents treat every request as if they've never seen the user before. No accumulated context injection. No behavioral adaptation. The ReAct loop works but doesn't deepen over time.

---

## Layer 2 — Accumulated Knowledge (deployed, incomplete)

### What's Deployed

1. **Knowledge base:** 922 doc vectors in Qdrant `knowledge` collection, 30 Neo4j graph nodes
2. **Preference storage:** `preferences` Qdrant collection (1024-dim, editable via dashboard)
   - Signal types: `thumbs_up`, `thumbs_down`, `remember_this`, `config_choice`
   - Semantic search — "I prefer dark themes" matches queries about UI colors
   - REST API: POST/GET at Node 1:9000/v1/preferences
3. **Activity logging:** `activity` Qdrant collection, fire-and-forget asyncio on every chat completion
   - Logged: agent name, action type, input/output summaries, tools used, duration, timestamp
   - Dashboard Activity Feed renders this collection
4. **Escalation protocol:** 3-tier confidence system (act/notify/ask) with per-agent thresholds
5. **GWT workspace:** Redis-backed inter-agent coordination, 1Hz competition cycle, capacity 7

### What's Deployed for Layer 2

6. **Context injection** (`context.py`): Every chat completion request is enriched before routing:
   - Single embedding call from user message, reused for all searches
   - Three parallel Qdrant queries: preferences, recent activity, relevant knowledge docs
   - Per-agent configuration: different agents get different context shapes and limits
   - Injected as SystemMessage prefix (before user messages, after agent's static prompt)
   - Graceful degradation: any failed query returns empty, never blocks the request
   - 30-50ms typical latency, ~300-500 token budget
   - Opt-out: `skip_context: true` in request body
   - Diagnostic: `POST /v1/context/preview` to inspect injection without invoking agent

### What's Missing for Full Layer 2

**Conversation history:** The `conversations` collection exists in Qdrant but isn't populated.

Implementation needed:
- After each agent interaction, embed the conversation and store
- Metadata: agent, timestamp, topic tags, user satisfaction signal (if provided)
- Enables "here's what Shaun previously asked about X" context injection

**Proactive indexing:** Knowledge indexing is currently manual (`python3 scripts/index-knowledge.py`).

Implementation needed:
- Cron job on DEV or Node 1 at 03:00 (after backups)
- Incremental updates (only re-embed changed documents)

### Layer 2 Context Injection (deployed)

The agent server's request handler (`server.py`) calls `enrich_context()` from `context.py` before routing:

```
Request arrives
  → Compute embedding from user message (1 call, ~30ms)
  → asyncio.gather():
      → Search preferences collection (agent-specific + global)
      → Scroll recent activity for this agent
      → Search knowledge collection for relevant docs
  → Format as SystemMessage with sections:
      ## Your Stored Preferences
      ## Recent Interactions ({agent})
      ## Relevant Documentation
  → Prepend to message list
  → Route to agent with enriched context
```

Per-agent context configuration (`AGENT_CONTEXT_CONFIG`):

| Agent | Prefs | Activity | Knowledge | Boost Terms |
|-------|-------|----------|-----------|-------------|
| general-assistant | 3 | 3 | 2 | monitoring, detail level |
| media-agent | 5 | 5 | 0 | content, quality, genre |
| home-agent | 5 | 5 | 0 | comfort, temperature, lighting |
| research-agent | 3 | 3 | 3 | depth, format, citations |
| creative-agent | 5 | 3 | 0 | style, visual, artistic |
| knowledge-agent | 3 | 3 | 0 | format, detail |
| coding-agent | 3 | 3 | 2 | conventions, style, stack |

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
| 1 (Reactive) | vLLM, LangGraph, LiteLLM, tool APIs | **Deployed** |
| 2 (Knowledge) | Qdrant, Neo4j, embedding model, preferences, activity logging, context injection | **Deployed** — context injection live, conversation history not yet populated |
| 3 (Patterns) | Conversation history, pattern detection jobs, context refinement | **Not started** |
| 4 (Self-Optimization) | All above + metrics correlation + A/B testing + auto-evaluation | **Future** |

## Implementation Sequence (remaining)

1. ~~Add preferences and activity Qdrant collections~~ ✅ Deployed (Tier 7.8)
2. ~~Add activity logging middleware~~ ✅ Deployed (fire-and-forget asyncio)
3. ~~Add preference storage/retrieval~~ ✅ Deployed (REST API + dashboard)
4. ~~Implement escalation protocol~~ ✅ Deployed (3-tier, per-agent thresholds)
5. ~~Wire context injection~~ ✅ Deployed — `context.py` module, 1 embedding + 3 parallel Qdrant queries, ~30-50ms latency
6. **Populate conversation history** — Post-interaction embedding + storage
7. **Pattern detection jobs** — Hourly/daily analysis of activity logs
8. ~~Dashboard integration — Activity Feed, Preferences~~ ✅ Deployed (Tier 7.12-7.14)
9. **Dashboard Insights page** — Pattern detections, agent learning signals

See `docs/BUILD-MANIFEST.md` for tracking.
