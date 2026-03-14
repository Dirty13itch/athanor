# Intelligence Layers — How Agents Become Intelligent Over Time

*The self-improving loop. The furnace feeding itself. Extends ADR-008.*

Last updated: 2026-03-14

---

## Layer 0 — Meta Orchestration (deployed)

This hierarchy is now governed rather than Claude-only. The authoritative command model lives in [command-hierarchy-governance.md](./command-hierarchy-governance.md) and [ADR-023](../decisions/ADR-023-command-hierarchy-and-governance.md).

Above the agent layer sits a governed strategy layer. Claude remains the frontier strategic lead for allowed cloud workloads, but Athanor now acts as the runtime governor and a sovereign local meta lane is the co-equal strategic path for refusal-sensitive, uncensored, private, or sovereign-only work.

```
Claude (COO) — cloud intelligence, operational decisions
  ↓ directs via task API + chat
Local Agents — domain expertise, autonomous execution
  ↓ act on
Infrastructure — GPUs, services, storage, networking
```

Claude directs agent work, monitors quality (trust scores, feedback), adjusts schedules and escalation thresholds, and escalates to Shaun only when human judgment is required. This meta-orchestration layer is what transforms a collection of reactive agents into a coordinated workforce.

---

## Layer 1 — Reactive Intelligence (deployed)

Each agent responds to requests. No memory between invocations beyond what's in the conversation thread (InMemorySaver, not persistent across restarts). The agent server routes by model name to the correct LangGraph agent. Agents call tools, get results, generate responses via LiteLLM → vLLM.

Simple, debuggable, working.

**What works:** 9 agents live, 25+ services healthy, all tools functional, streaming responses, tool call visualization in dashboard, escalation protocol, GWT workspace, task execution engine, proactive scheduler.

**What's evolved past:** Context injection now deployed (Layer 2). Agents receive preferences, activity history, knowledge docs, and active goals in every request. The "no memory" limitation is mitigated by the context enrichment pipeline.

---

## Layer 2 — Accumulated Knowledge (deployed)

### What's Deployed

1. **Knowledge base:** 3076 doc vectors in Qdrant `knowledge` collection, 3095 Neo4j nodes (172 Document + 879 Entity), 4447 relationships
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
   - Five parallel Qdrant queries: preferences (with time-decay), recent activity, knowledge (hybrid search), personal data, conversations
   - Neo4j graph expansion: related documents from knowledge graph
   - CST (Cognitive State Tracker), active goals, detected patterns, learned conventions, matched skills
   - Per-agent configuration: different agents get different context shapes and limits
   - Injected as SystemMessage prefix (before user messages, after agent's static prompt)
   - Graceful degradation: any failed query returns empty, never blocks the request
   - Latency tracked via `GET /v1/metrics/context` (ring buffer with p50/p95/p99 per agent)
   - Opt-out: `skip_context: true` in request body
   - Diagnostic: `POST /v1/context/preview` to inspect injection without invoking agent

### Layer 2 Completion Status

**Conversation history:** Deployed. The `conversations` collection is populated by `log_conversation()` in `activity.py`, wired since session 40. Conversations are embedded and stored after each agent interaction with agent, timestamp, and conversation content metadata.

**Proactive indexing:** Knowledge indexing is manual (`python3 scripts/index-knowledge.py`). A cron-based incremental re-index (only changed docs) would automate this. Low priority — manual runs after doc changes are sufficient for current scale (172 docs, ~3 min full re-index).

### Layer 2 Context Injection (deployed)

The agent server's request handler (`server.py`) calls `enrich_context()` from `context.py` before routing:

```
Request arrives
  → Compute embedding from user message (1 call, ~30ms)
  → asyncio.gather() — 5 parallel queries:
      → Search preferences (agent-specific + global, time-decay weighted)
      → Scroll recent activity for this agent
      → Hybrid search knowledge collection (dense + sparse)
      → Hybrid search personal_data collection
      → Search conversations collection (agent-filtered)
  → Neo4j graph expansion (related docs from knowledge graph)
  → Redis lookups:
      → CST (Cognitive State Tracker) — current focus, emotional state
      → Active goals for this agent
      → Detected behavioral patterns
      → Learned conventions
  → Skill matching (find_matching_skill from skill_learning.py)
  → Format as SystemMessage with sections:
      ## Your Stored Preferences
      ## Recent Interactions ({agent})
      ## Relevant Documentation
      ## Related Knowledge (graph)
      ## Personal Context
      ## Recent Conversations
      ## Current Focus / Goals / Patterns / Conventions
      ## Applicable Skills
  → Budget enforcement (MAX_CONTEXT_CHARS = 6000)
  → Prepend to message list
  → Route to agent with enriched context
```

Per-agent context configuration (`AGENT_CONTEXT_CONFIG`):

| Agent | Prefs | Activity | Knowledge | Personal | Convos | Boost Terms |
|-------|-------|----------|-----------|----------|--------|-------------|
| general-assistant | 3 | 3 | 2 | 3 | 3 | monitoring, detail level |
| media-agent | 5 | 5 | 0 | 0 | 2 | content, quality, genre |
| home-agent | 5 | 5 | 0 | 2 | 2 | comfort, temperature, lighting |
| research-agent | 3 | 3 | 3 | 3 | 3 | depth, format, citations |
| creative-agent | 5 | 3 | 0 | 0 | 2 | style, visual, artistic |
| knowledge-agent | 3 | 3 | 0 | 5 | 2 | format, detail |
| coding-agent | 3 | 3 | 2 | 0 | 2 | conventions, style, stack |
| stash-agent | 5 | 3 | 0 | 0 | 2 | content, library, organization |
| data-curator | 3 | 3 | 2 | 3 | 2 | data, indexing, quality |

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
| 0 (Meta Orchestration) | Claude as frontier lead, sovereign local meta lane, governor control path | **Deployed** — runtime command is now governor-mediated rather than Claude-only |
| 1 (Reactive) | vLLM, LangGraph, LiteLLM, tool APIs | **Deployed** |
| 2 (Knowledge) | Qdrant, Neo4j, embedding model, preferences, activity logging, context injection, goals, conversations, skills | **Deployed** — full context pipeline live including conversations, graph expansion, CST, skills |
| 3 (Patterns) | Pattern detection jobs, context refinement, insights dashboard | **Partial** — pattern detection engine deployed (`patterns.py`, daily 5AM schedule), skill learning live (8 skills, ~2K executions) |
| 4 (Self-Optimization) | All above + metrics correlation + A/B testing + auto-evaluation | **Future** |

## Implementation Sequence (remaining)

1. ~~Add preferences and activity Qdrant collections~~ ✅ Deployed (Tier 7.8)
2. ~~Add activity logging middleware~~ ✅ Deployed (fire-and-forget asyncio)
3. ~~Add preference storage/retrieval~~ ✅ Deployed (REST API + dashboard)
4. ~~Implement escalation protocol~~ ✅ Deployed (3-tier, per-agent thresholds)
5. ~~Wire context injection~~ ✅ Deployed — `context.py` module, 1 embedding + 5 parallel Qdrant queries + graph expansion + CST + goals + patterns + conventions + skills
6. ~~Populate conversation history~~ ✅ Deployed — `log_conversation()` in `activity.py`, wired since session 40
7. ~~Pattern detection jobs~~ ✅ Deployed — `patterns.py`, daily 5AM schedule, `GET /v1/patterns`
8. ~~Dashboard integration — Activity Feed, Preferences~~ ✅ Deployed (Tier 7.12-7.14)
9. ~~Skill learning loop~~ ✅ Deployed — 8 seeded skills, automatic execution recording, `GET /v1/skills/stats`
10. **Dashboard Insights page** — Pattern detections, agent learning signals, context latency metrics

See `docs/BUILD-MANIFEST.md` for tracking.
