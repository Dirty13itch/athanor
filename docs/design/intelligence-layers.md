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

### What's Missing for Full Layer 2

**Context injection:** Agents don't yet query preferences/activity/conversations before responding. The collections exist and are populated, but no agent actually reads them at request time to enrich its context. This is the single biggest gap — the data is there, the plumbing to use it is not.

Implementation needed:
- Agent server request handler queries relevant collections before routing
- Each agent gets different context (Research → prior research, Media → viewing history, etc.)
- Inject as system message prefix, not tool calls (faster, always present)

**Conversation history:** The `conversations` collection exists in Qdrant but isn't populated.

Implementation needed:
- After each agent interaction, embed the conversation and store
- Metadata: agent, timestamp, topic tags, user satisfaction signal (if provided)
- Enables "here's what Shaun previously asked about X" context injection

**Proactive indexing:** Knowledge indexing is currently manual (`python3 scripts/index-knowledge.py`).

Implementation needed:
- Cron job on DEV or Node 1 at 03:00 (after backups)
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
| 1 (Reactive) | vLLM, LangGraph, LiteLLM, tool APIs | **Deployed** |
| 2 (Knowledge) | Qdrant, Neo4j, embedding model, preferences, activity logging | **Deployed** — collections live, context injection not yet wired |
| 3 (Patterns) | Context injection, conversation history, pattern detection jobs | **Not started** |
| 4 (Self-Optimization) | All above + metrics correlation + A/B testing + auto-evaluation | **Future** |

## Implementation Sequence (remaining)

1. ~~Add preferences and activity Qdrant collections~~ ✅ Deployed (Tier 7.8)
2. ~~Add activity logging middleware~~ ✅ Deployed (fire-and-forget asyncio)
3. ~~Add preference storage/retrieval~~ ✅ Deployed (REST API + dashboard)
4. ~~Implement escalation protocol~~ ✅ Deployed (3-tier, per-agent thresholds)
5. **Wire context injection** — Agent server queries preferences/activity before routing to agent
6. **Populate conversation history** — Post-interaction embedding + storage
7. **Pattern detection jobs** — Hourly/daily analysis of activity logs
8. ~~Dashboard integration — Activity Feed, Preferences~~ ✅ Deployed (Tier 7.12-7.14)
9. **Dashboard Insights page** — Pattern detections, agent learning signals

See `docs/BUILD-MANIFEST.md` for tracking.
