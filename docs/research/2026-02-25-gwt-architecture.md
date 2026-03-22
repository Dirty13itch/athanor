# GWT-Inspired Meta-Orchestrator Architecture

**Date:** 2026-02-25
**Status:** Research complete, ready for ADR
**Supports:** Future ADR (meta-orchestration layer)
**Depends on:** ADR-008 (Agent Framework), existing agent server on Node 1:9000

---

## Summary

Global Workspace Theory (GWT) provides a cognitive architecture model where specialized processors compete to broadcast information through a shared workspace with limited capacity. This research evaluates GWT as the basis for Athanor's agent meta-orchestration layer — a system that transforms the current reactive agent deployment into a proactive, self-coordinating organism.

The core insight: Athanor's 6 agents are currently isolated responders. GWT gives them shared awareness. A media event (new Plex stream, Sonarr grab) becomes visible to every agent without explicit routing. Agents self-select based on relevance. The orchestrator doesn't need to know which agent handles what — agents compete for attention in a shared workspace, and the most relevant response wins broadcast.

---

## Context: What We Have Now

The agent server (`projects/agents/src/athanor_agents/server.py`) runs on Node 1:9000 as a FastAPI application exposing an OpenAI-compatible chat completions endpoint. Six LangGraph agents are deployed:

| Agent | Type | What It Does |
|-------|------|-------------|
| `general-assistant` | Reactive | System monitoring, GPU metrics, storage info |
| `media-agent` | Proactive (15 min) | Sonarr/Radarr/Tautulli — search, add, monitor |
| `home-agent` | Proactive (5 min) | Home Assistant — lights, climate, automations |
| `creative-agent` | Reactive | ComfyUI Flux — image generation |
| `research-agent` | Reactive | Web search, knowledge queries, graph queries |
| `knowledge-agent` | Reactive | Document search, ADRs, research notes, graph |

All inference routes through LiteLLM at VAULT:4000, which maps model aliases (`reasoning`, `fast`, `embedding`) to vLLM instances on Node 1 and Node 2.

### The Problem

The current architecture is hub-spoke with explicit routing:

```
User/Dashboard → POST /v1/chat/completions { model: "media-agent" } → media-agent
```

Every interaction requires the caller to know which agent to invoke. Nothing happens unless something external pokes an agent. The "proactive" agents (media, home) run on fixed schedules but don't share observations with other agents. If the media agent detects that a new movie finished downloading, the home agent doesn't know about it (and couldn't, say, dim the living room lights for movie night). If the knowledge agent indexes a new research doc about energy efficiency, the general assistant doesn't know there's fresh knowledge available.

There is no shared state. There is no emergent behavior. There is no cross-agent awareness.

---

## Why GWT Over Simple Orchestration

### What Simple Orchestration Looks Like

The naive fix: add a router agent that reads incoming requests and dispatches to the right specialist. This is what most LLM orchestration frameworks do (LangGraph's supervisor pattern, CrewAI's hierarchical process). The router becomes a bottleneck, a single point of failure, and a maintenance burden — every new agent requires updating the router's knowledge of who does what.

### What GWT Adds

GWT, proposed by Bernard Baars in 1988 and subsequently formalized by Dehaene, Changeux, and others as the Global Neuronal Workspace (GNW) theory, models consciousness as a competitive broadcast mechanism:

1. **Shared Workspace**: All agents see all broadcast information simultaneously. A media event becomes visible to the home agent without explicit routing. A new research document becomes visible to the general assistant. Information flows laterally, not just through a central hub.

2. **Competitive Selection**: Agents score incoming workspace items by relevance to their own capabilities. No orchestrator needs to know which agent handles what. New agents register and compete naturally — adding agent #7 doesn't require changing agents #1-6 or any routing logic.

3. **Capacity-Limited Bottleneck**: The workspace holds a limited number of active items (inspired by Miller's Law — 7 plus or minus 2). This forces prioritization and prevents overload. When the workspace is full, low-salience items expire. The system self-regulates attention.

4. **Broadcast → Ignition**: When an item wins the competition, it's broadcast to ALL agents simultaneously. This is the "ignition" event in GNW terminology — the moment information becomes globally available. Any agent can respond. Multiple agents can respond to the same broadcast, enabling emergent collaboration.

5. **Coalition Formation**: Agents can endorse other agents' workspace contributions, forming coalitions that amplify salience. If the media agent observes "new movie downloaded" and the home agent observes "living room unoccupied," a coalition between these observations creates a compound event ("movie ready + room available") with higher salience than either alone.

### What This Means for Athanor

GWT transforms Athanor from a set of tools waiting to be used into a system that notices things, prioritizes them, and acts. The practical difference:

**Without GWT (current):**
- Sonarr finishes downloading a movie → media agent logs it on its next 15-min cycle → nobody else knows
- User asks general assistant "what's new?" → general assistant has no idea about the download

**With GWT:**
- Sonarr webhook fires → Input Gateway creates workspace item: `{content: "Movie 'Dune 3' download complete", source: "sonarr-webhook", salience: 0.6}`
- Competition cycle: media agent scores 0.9 (directly relevant), home agent scores 0.4 (could prep movie environment), knowledge agent scores 0.1 (not relevant)
- Media agent wins broadcast → all agents now know about the download
- Home agent, seeing the broadcast, optionally contributes: "living room is occupied, Amanda watching TV" → this modifies the workspace state
- Next user query to any agent has this context available

---

## Architecture Design

### Overview

```
External Events                              Agents
  (webhooks, cron,          ┌──────────────────────────────────┐
   sensors, API)            │        Global Workspace          │
       │                    │   ┌────────────────────────┐     │
       ▼                    │   │  Active Items (max 7)  │     │    ┌─── general-assistant
  Input Gateway             │   │                        │     │    ├─── media-agent
  (FastAPI :9000)──────────▶│   │  item1  item2  item3   │─────────▶├─── home-agent
       │                    │   │  item4  item5  ...     │broadcast  ├─── creative-agent
       │                    │   └────────────────────────┘     │    ├─── research-agent
       │                    │         ▲           │            │    └─── knowledge-agent
       │                    │         │   competition          │           │
       │                    │    candidate    cycle (1Hz)       │           │
       │                    │     items          │             │           │
       │                    │         │           ▼            │           │
       │                    │   ┌────────────────────────┐     │     responses /
       │                    │   │  Candidate Queue       │◀────────── observations
       │                    │   └────────────────────────┘     │
       │                    └──────────────────────────────────┘
       │                                    │
       ▼                                    ▼
  Redis (pub/sub +               Qdrant "workspace"
   workspace state)            (persistent items +
                                experience memory)
```

### Component Details

#### 1. Input Gateway (FastAPI, Node 1:9000)

The existing agent server gains a new responsibility: accepting external events and converting them to workspace candidates. This extends `server.py`, not replaces it. The existing `/v1/chat/completions` endpoint continues working — direct agent invocation remains available for explicit requests.

New endpoints:

```
POST /v1/workspace/events     ← External events (webhooks, cron results)
GET  /v1/workspace/state      ← Current workspace items (debugging, dashboard)
GET  /v1/workspace/history    ← Recent broadcast history
POST /v1/workspace/inject     ← Manual item injection (for testing / Shaun override)
```

Event sources:
- **Webhooks**: Sonarr/Radarr download complete, Plex playback start/stop, Home Assistant state changes
- **Cron/Scheduled**: Agent scheduled observations (media agent's 15-min scan, home agent's 5-min check)
- **API**: Dashboard interactions, Open WebUI messages, EoBQ game events
- **Internal**: Agent-generated observations from tool calls

#### 2. Global Workspace (Redis + Qdrant)

The workspace is the central data structure. It has two layers:

**Active Workspace (Redis)**: The hot state. Capacity-limited to 7 concurrent items. Redis provides the speed needed for the 1Hz competition cycle and pub/sub broadcast.

Redis key structure:
```
workspace:active              ← Sorted set (score = salience), max 7 members
workspace:candidates          ← List of pending candidate items
workspace:item:{id}           ← Hash with full item data
workspace:broadcast:latest    ← Last broadcast item (for late-joining subscribers)
workspace:stats               ← Counters: total_broadcasts, total_candidates, cycle_count
```

**Persistent Workspace (Qdrant)**: A new `workspace` collection in the existing Qdrant instance (Node 1:6333). Stores all workspace items with vector embeddings for semantic search. Enables experience memory — "what happened last time we saw an event like this?"

Collection schema:
```json
{
  "collection": "workspace",
  "vectors": { "size": 1024, "distance": "Cosine" },
  "payload_schema": {
    "content": "text",
    "salience": "float",
    "source": "keyword",
    "timestamp": "datetime",
    "coalition": "keyword[]",
    "outcome": "keyword",
    "broadcast": "bool",
    "ttl_seconds": "integer"
  }
}
```

#### 3. WorkspaceItem Model

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

class WorkspaceItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: str                          # What happened / what is being proposed
    salience: float = Field(ge=0.0, le=1.0)  # How important (0=background, 1=critical)
    source: str                           # Which agent or external system created this
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300                # Default 5 minutes; high-salience items live longer
    coalition: list[str] = []             # Agents that endorse this item
    metadata: dict = {}                   # Source-specific data (e.g., Sonarr movie ID, HA entity)
    embedding: Optional[list[float]] = None  # Vector from embedding model, set during ingestion
```

Salience scoring guidelines:

| Range | Meaning | Examples |
|-------|---------|---------|
| 0.9-1.0 | Critical / requires immediate attention | Service down, security event, user direct request |
| 0.7-0.8 | High / significant event | Download complete, automation triggered, HA alert |
| 0.4-0.6 | Medium / noteworthy observation | New content available, schedule change, metric anomaly |
| 0.1-0.3 | Low / background information | Periodic status update, routine check passed |

#### 4. Competition Cycle (1Hz Background Loop)

A background asyncio task running inside the agent server process. Every second:

1. **Collect candidates**: Pull all items from `workspace:candidates` Redis list
2. **Score**: Each registered agent scores each candidate (fast — LLM call NOT required, use rule-based scoring per agent)
3. **Select**: Highest combined salience wins. If the workspace is full (7 items), the winner must beat the lowest-salience active item to enter.
4. **Evict**: Remove expired items (TTL exceeded) and lowest-salience items when at capacity
5. **Broadcast**: Winning item published to Redis channel `workspace:broadcast`. All subscribed agents receive it.

```python
async def competition_cycle():
    """Runs every 1 second. The heartbeat of the workspace."""
    while True:
        candidates = await redis.lrange("workspace:candidates", 0, -1)
        if candidates:
            for candidate_json in candidates:
                item = WorkspaceItem.model_validate_json(candidate_json)

                # Each agent scores the item
                scores = {}
                for agent_name, agent_scorer in registered_agents.items():
                    scores[agent_name] = agent_scorer.score(item)

                # Item salience = max(initial_salience, max(agent_scores))
                item.salience = max(item.salience, max(scores.values()))

                # Try to enter active workspace
                active_count = await redis.zcard("workspace:active")
                if active_count < WORKSPACE_CAPACITY:
                    await _admit_item(item)
                else:
                    # Must beat lowest active item
                    lowest = await redis.zrange("workspace:active", 0, 0, withscores=True)
                    if lowest and item.salience > lowest[0][1]:
                        await _evict_item(lowest[0][0])
                        await _admit_item(item)

            # Clear processed candidates
            await redis.delete("workspace:candidates")

        # Evict expired items
        await _evict_expired()

        # Broadcast highest-salience active item that hasn't been broadcast yet
        await _broadcast_top_unbroadcast()

        await asyncio.sleep(1.0)
```

#### 5. Agent Registration and Self-Selection

Each agent registers with the workspace and provides:
- A **relevance scorer**: A fast function (not an LLM call) that scores how relevant a workspace item is to this agent. Rule-based, inspectable, debuggable.
- A **broadcast handler**: An async callback invoked when a broadcast item is relevant to this agent (score above threshold).

```python
class AgentWorkspaceRegistration:
    name: str
    relevance_keywords: list[str]     # Fast keyword match
    relevance_sources: list[str]      # Source types this agent cares about
    relevance_threshold: float        # Minimum score to trigger broadcast handler
    score_fn: Callable[[WorkspaceItem], float]  # Custom scoring function
    on_broadcast: Callable[[WorkspaceItem], Awaitable[None]]  # What to do with broadcast items
```

Example for the media agent:
```python
media_registration = AgentWorkspaceRegistration(
    name="media-agent",
    relevance_keywords=["movie", "show", "download", "plex", "sonarr", "radarr", "stream"],
    relevance_sources=["sonarr-webhook", "radarr-webhook", "plex-webhook", "tautulli"],
    relevance_threshold=0.3,
    score_fn=media_relevance_scorer,
    on_broadcast=media_handle_broadcast,
)
```

The scoring function is simple pattern matching — no LLM required:
```python
def media_relevance_scorer(item: WorkspaceItem) -> float:
    score = 0.0
    if item.source in ["sonarr-webhook", "radarr-webhook", "plex-webhook", "tautulli"]:
        score += 0.7
    content_lower = item.content.lower()
    for keyword in ["movie", "show", "episode", "download", "stream", "plex"]:
        if keyword in content_lower:
            score += 0.1
    return min(score, 1.0)
```

#### 6. LiteLLM Routing Based on Salience

The existing LiteLLM proxy at VAULT:4000 already routes between `reasoning` (Qwen3-32B on Node 1 TP=4) and `fast` (Qwen3-14B on Node 2). The workspace adds a routing policy:

| Salience | Model | Rationale |
|----------|-------|-----------|
| 0.7-1.0 | `reasoning` | High-stakes items get the best model |
| 0.0-0.6 | `fast` | Routine observations use the cheaper model |

This is a soft policy — agents can override if needed. The workspace tracks which model was used for each broadcast response, enabling future optimization.

---

## Implementation Phases

### Phase 1: Shared Workspace (Estimated: 1 weekend session)

**Goal**: Agents can write observations to a shared workspace. Dashboard can view workspace state. No competition or broadcast yet — just shared state.

**Deliverables**:
- `WorkspaceItem` Pydantic model in agent codebase
- Redis container added to Node 1 (or use VAULT — see Technology Choices)
- New endpoints: `POST /v1/workspace/events`, `GET /v1/workspace/state`
- Each agent gains an `observe()` method that writes to the workspace
- Proactive agents (media, home) write observations on their existing schedules
- Dashboard widget showing workspace state (latest items, sources, salience)
- Ansible role for Redis deployment

**What changes**: Agents gain shared awareness but don't act on it yet. The workspace is a shared log.

### Phase 2: Competition Cycle (Estimated: 1 weekend session)

**Goal**: The 1Hz background loop runs, agents register scorers, items compete for workspace slots, winners get broadcast via Redis pub/sub.

**Deliverables**:
- Background `competition_cycle()` task in agent server
- Agent registration system (`AgentWorkspaceRegistration`)
- Relevance scoring functions for all 6 agents
- Redis pub/sub broadcast on channel `workspace:broadcast`
- Agents subscribe and receive broadcasts
- Salience-based LiteLLM model routing
- `/v1/workspace/history` endpoint showing broadcast log
- Dashboard updates: broadcast feed, agent response indicators

**What changes**: The system becomes proactive. Events flow through the workspace, agents compete to respond, and information broadcasts to all agents simultaneously. Cross-agent awareness begins.

### Phase 3: Coalition Formation (Estimated: 1-2 weekend sessions)

**Goal**: Agents can endorse other agents' workspace candidates, forming coalitions that amplify salience. Multi-agent collaboration emerges.

**Deliverables**:
- Coalition mechanism: agents add themselves to `item.coalition` to boost salience
- Coalition salience formula: `base_salience + 0.1 * len(coalition)`
- Compound events: when two related items are both active, a new compound item is created
- Agent-to-agent messaging via workspace (agent A publishes observation, agent B extends it)
- Coalition visualization in dashboard

**Example**: Media agent observes "Dune 3 download complete" (salience 0.6). Home agent endorses with "living room occupied by Amanda" (coalition boost to 0.7). The compound event "movie ready + viewer present" triggers a notification to Shaun: "Dune 3 is ready — Amanda's in the living room. Want me to queue it up on Plex?"

**What changes**: Agents collaborate without explicit orchestration. Emergent behavior from simple rules.

### Phase 4: Experience Memory (Estimated: 2-3 weekend sessions)

**Goal**: The workspace learns from outcomes. Past broadcasts and their results are stored in Qdrant, and the system uses them to improve salience scoring over time.

**Deliverables**:
- All broadcast items stored in Qdrant `workspace` collection with vector embeddings
- Outcome tracking: was the broadcast acted on? Was the result positive/negative/ignored?
- Semantic search for similar past events: "last time we saw a download event like this, what happened?"
- Salience prior adjustment: items similar to past high-outcome events get boosted salience
- Experience decay: old outcomes fade in influence over time (configurable half-life)
- Dashboard: experience memory browser, outcome tracking stats

**What changes**: The system gets smarter over time. Frequently-ignored event types naturally decrease in salience. Events that lead to positive outcomes get boosted. This is the beginning of genuine learning.

**Risk**: Runaway self-modification. If the feedback loop has bugs, salience could converge to 0 (nothing matters) or 1 (everything is critical). Mitigation: hard floor/ceiling on learned adjustments (max +/- 0.2 from base salience), manual override always available, clear logging of all salience adjustments.

---

## Technology Choices

### Redis

**Why**: Lightweight pub/sub plus workspace state management. Redis is the standard tool for this — fast sorted sets for the active workspace, lists for the candidate queue, pub/sub for broadcast, hashes for item storage. Single binary, single container, runs anywhere.

**Deployment**: New container on VAULT alongside the existing services (LiteLLM, Neo4j, Prometheus, etc.). VAULT already runs 12+ containers; one more Redis instance is negligible. Alternatively, deploy on Node 1 co-located with the agent server to minimize latency — but VAULT keeps all stateful services in one place for backup simplicity.

**Recommendation**: VAULT. The 1Hz cycle and pub/sub messages are tiny payloads. Network latency from Node 1 to VAULT over 5GbE is <0.5ms. Backup story is clean — Redis RDB snapshots go to the same VAULT backup location as Neo4j and appdata.

**Memory**: Default Redis with no persistence is fine for the active workspace (it's ephemeral by design). Enable RDB snapshots for stats and configuration persistence. Expected memory: <10 MB for workspace state even at scale.

**Debuggability**: `redis-cli monitor` shows every command in real time. `redis-cli ZRANGE workspace:active 0 -1 WITHSCORES` shows the current workspace at a glance. This is critical for one-person operability — when something is wrong, Shaun can see exactly what the workspace contains and why.

Source: [Redis Sorted Sets](https://redis.io/docs/data-types/sorted-sets/), [Redis Pub/Sub](https://redis.io/docs/interact/pubsub/)

### Qdrant

**Why**: Already deployed on Node 1:6333 with the `knowledge` collection (922 points). Adding a `workspace` collection is a configuration change, not a new service. The existing Qwen3-Embedding-0.6B model on Node 1:8001 provides vectors.

**Collection sizing**: Workspace items are small (text + metadata). At 1 item per second sustained (extreme case), that's ~86,400 items/day. With 1024-dim vectors, each point is ~4 KB. One day = ~345 MB. With a 30-day retention policy, that's ~10 GB — well within Node 1's capacity. In practice, event volume will be orders of magnitude lower.

Source: [Qdrant Collections](https://qdrant.tech/documentation/concepts/collections/)

### FastAPI

**Why**: The agent server is already FastAPI (`server.py`). The workspace endpoints extend the existing app. No new framework, no new deployment — just new routes and a background task.

The competition cycle runs as an asyncio background task started in the existing `lifespan` context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from .agents import _init_agents
    _init_agents()
    # Start workspace competition cycle
    asyncio.create_task(competition_cycle())
    yield
```

### Not Chosen: Kafka / RabbitMQ / NATS

Message brokers are overkill. The workspace handles ~1-100 events per minute, not thousands per second. Redis pub/sub provides exactly the semantics needed (publish to channel, all subscribers receive) without the operational complexity of a dedicated message broker. If event volume ever exceeds Redis capacity (it won't for this use case), NATS is the next step — but that's a problem for a system processing 100K+ events/sec, not 100/min.

### Not Chosen: PostgreSQL for Workspace State

Postgres would work but adds query latency for the 1Hz cycle. The active workspace needs sub-millisecond reads on every cycle. Redis sorted sets provide O(log N) insertion and O(1) reads for the top/bottom items. For 7 items, this is trivially fast. Postgres's strengths (ACID transactions, complex queries, joins) aren't needed for workspace state.

---

## One-Person Scale Assessment

The one-person-scale filter from CLAUDE.md: "Can Shaun understand, operate, debug, and fix this alone?"

### Phase 1-2: Yes, straightforwardly

- Redis is a single container with zero configuration for basic use. `redis-cli` is the debugging interface.
- The workspace data model is one Pydantic class. The competition cycle is one async function.
- Agent scoring functions are simple keyword matchers — no ML, no magic.
- Everything runs in the existing agent server process. No new Docker containers beyond Redis.
- Dashboard integration: one new widget showing workspace items and broadcast history.
- If the workspace breaks, agents still work via direct `/v1/chat/completions` calls. The workspace is an enhancement, not a dependency.

**Debug workflow**: `redis-cli monitor` to watch real-time workspace activity. `curl http://node1:9000/v1/workspace/state` to see current items. Agent server logs show scoring and broadcast decisions. All inspectable from a terminal.

### Phase 3: Yes, with care

Coalition formation adds interactions between agents. The complexity is in understanding emergent behavior — "why did these two agents form a coalition?" The mitigation: extensive logging of coalition decisions, a dashboard view showing coalition graphs, and the ability to manually break coalitions.

The rules are simple (endorsement = salience boost, compound events from co-active items). The emergent behavior from simple rules can be surprising, but it's always traceable because every step is logged.

### Phase 4: Proceed carefully

Experience memory introduces a feedback loop. The system modifies its own salience scoring based on past outcomes. This is powerful but risky:

- **Runaway amplification**: If a bug causes all outcomes to register as "positive," salience converges to maximum for everything. Mitigation: hard bounds on learned adjustments (+/- 0.2 max).
- **Runaway suppression**: If outcomes aren't tracked correctly, everything decays to zero. Mitigation: minimum salience floor (0.1) for all items regardless of learned adjustments.
- **Debugging learned behavior**: "Why did the system ignore this event?" requires tracing through experience memory. Mitigation: `/v1/workspace/explain/{item_id}` endpoint that shows the salience calculation breakdown.

Phase 4 is the most complex, but it's also optional. Phases 1-3 deliver the core GWT value (shared workspace, competition, coalition) without self-modification. Phase 4 can be deferred until the system has been running long enough to generate meaningful outcome data.

---

## Integration Points

### Existing Webhooks / Event Sources

| Source | Event Type | Salience | Integration |
|--------|-----------|----------|-------------|
| Sonarr | Episode grabbed/downloaded | 0.6 | Sonarr webhook → `POST /v1/workspace/events` |
| Radarr | Movie grabbed/downloaded | 0.6 | Radarr webhook → same |
| Plex (via Tautulli) | Playback start/stop | 0.5 | Tautulli notification → same |
| Home Assistant | State change (motion, door, climate) | 0.3-0.7 | HA automation → same |
| EoBQ | Game session events | 0.4 | EoBQ backend → same |
| Prometheus alerts | Service down, high GPU temp | 0.9 | Alertmanager webhook → same |
| Cron (agent schedules) | Periodic observations | 0.2-0.4 | Agent internals |
| Dashboard | User interaction | 0.8 | Dashboard API calls |

### Dashboard Integration

The existing Next.js dashboard (Node 2:3001) gains:
- **Workspace widget**: Live view of 7 active workspace items, color-coded by salience
- **Broadcast feed**: Scrolling log of broadcasts and agent responses
- **Coalition graph**: Visual showing which agents are collaborating on which items
- **Experience stats** (Phase 4): Outcome tracking, salience distribution over time

All via the new `/v1/workspace/*` endpoints — no new backend services, just new API calls from the dashboard.

### Open WebUI Integration

The existing Open WebUI (Node 2:3000) connects to the agent server as an OpenAI-compatible endpoint. Workspace broadcasts can be surfaced as system messages in the chat interface: "Workspace notice: Dune 3 download complete. Media agent and home agent are coordinating." This gives Shaun passive awareness of workspace activity during chat.

---

## Comparison to Other Approaches

| Approach | Routing | New Agents | Cross-Agent Awareness | Proactive Behavior | Complexity |
|----------|---------|------------|----------------------|-------------------|------------|
| **Current (direct call)** | Caller picks agent | Requires caller update | None | Fixed schedules only | Minimal |
| **Router agent (supervisor)** | LLM-based dispatch | Update router prompt | Via router only | Router-driven | Medium |
| **Event bus (pub/sub only)** | Topic-based subscription | Subscribe to topics | By shared topics | Event-driven | Low-medium |
| **GWT workspace** | Competitive self-selection | Register + compete | Full (broadcast) | Emergent from workspace | Medium-high |

GWT is more complex than a simple event bus but solves a different problem. An event bus routes events to known subscribers — you still need to decide which agent subscribes to which topics. GWT lets agents self-select based on content relevance, which means the routing adapts automatically as agents and events evolve.

The router agent approach is simpler for small agent counts but scales poorly. Every new agent requires updating the router's understanding. GWT scales naturally — agent #7 registers, competes, and integrates without touching agents #1-6.

---

## Open Questions

1. **Redis location**: VAULT (centralized, clean backup story) vs. Node 1 (co-located with agent server, lowest latency). Recommendation: VAULT, but benchmark the 1Hz cycle over 5GbE to confirm latency is acceptable.

2. **Workspace capacity**: 7 is a starting point (Miller's Law analogy). The right number depends on event volume and agent count. May need to be tunable.

3. **Broadcast semantics**: Should broadcast mean "all agents are notified" or "all agents are queried for a response"? The first is passive (agents choose to act), the second is active (all agents must respond). Passive is lighter and more GWT-faithful, but active ensures nothing is missed.

4. **Salience calibration**: Initial salience values (0.3 for HA state changes, 0.6 for downloads, 0.9 for service down) are educated guesses. Need real-world tuning after deployment.

5. **User attention model**: Should Shaun's current activity (typing in Open WebUI, idle, away from home) affect workspace behavior? This would enable "don't interrupt with low-salience broadcasts when Shaun is in a coding session."

6. **Failure mode**: If Redis goes down, the workspace stops but agents still respond to direct API calls. This is acceptable — the workspace is an enhancement layer, not a critical dependency. Confirm this graceful degradation in implementation.

---

## Relevance to Athanor

GWT transforms Athanor from reactive (agents wait for instructions) to proactive (workspace drives continuous awareness and action). The specific benefits:

1. **Emergent routing**: Agents self-select based on relevance. Adding a new agent (e.g., the adult content curator from VISION.md) requires only registering it with the workspace — no changes to existing agents or routing logic.

2. **Cross-domain awareness**: The media agent's download event is visible to the home agent. The home agent's occupancy data is visible to EoBQ. Information crosses domain boundaries naturally.

3. **Capacity-limited prioritization**: The 7-item workspace prevents agent overload. When the system is busy, only the most important events get attention. This mirrors how attention works in cognitive systems — and it's a practical engineering constraint that prevents runaway processing.

4. **Foundation for genuine intelligence**: Phases 1-3 create shared awareness and collaboration. Phase 4 adds learning. This is the path from "agents that do tasks" to "a system that understands its environment." It aligns with VISION.md's goal of a unified system where the pieces are aware of each other.

5. **Craftsmanship**: GWT is an elegant cognitive architecture, not a brute-force solution. It rewards understanding and refinement. The competition cycle, coalition formation, and experience memory are individually simple but collectively powerful. This is tüftler territory — refining simple rules into emergent behavior.

---

## References

- Baars, B.J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press. — The original GWT formulation. Proposes consciousness as a global broadcast mechanism in a society of specialized processors.
- Dehaene, S., & Naccache, L. (2001). Towards a cognitive neuroscience of consciousness: basic evidence and a workspace framework. *Cognition*, 79(1-2), 1-37. [DOI: 10.1016/S0010-0277(00)00123-2](https://doi.org/10.1016/S0010-0277(00)00123-2) — Formalized GWT as Global Neuronal Workspace (GNW) with empirical neural correlates. Introduced the "ignition" concept.
- Dehaene, S., Changeux, J.-P., & Naccache, L. (2011). The Global Neuronal Workspace Model of Conscious Access: From Neuronal Architectures to Clinical Applications. In *Characterizing Consciousness: From Cognition to the Clinic?* Springer. [DOI: 10.1007/978-3-642-18015-6_4](https://doi.org/10.1007/978-3-642-18015-6_4) — Extended GNW with clinical applications and detailed neural architecture mapping.
- Franklin, S., et al. (2012). LIDA: A Systems-level Architecture for Cognition, Emotion, and Learning. *IEEE Transactions on Autonomous Mental Development*, 4(1), 19-34. [DOI: 10.1109/TAMD.2012.2195153](https://doi.org/10.1109/TAMD.2012.2195153) — LIDA implements GWT as a software architecture. Demonstrates competition, coalition formation, and broadcast in a computational system. Most directly relevant to this implementation.
- Shanahan, M. (2010). *Embodiment and the Inner Life: Cognition and Consciousness in the Space of Possible Minds*. Oxford University Press. — Philosophical and computational analysis of GWT and related workspace architectures. Good treatment of how simple competition rules produce complex emergent behavior.
- Miller, G.A. (1956). The magical number seven, plus or minus two: Some limits on our capacity for processing information. *Psychological Review*, 63(2), 81-97. [DOI: 10.1037/h0043158](https://doi.org/10.1037/h0043158) — The capacity-limitation principle used for workspace sizing.
- VanRullen, R., & Kanai, R. (2021). Deep learning and the Global Workspace Theory. *Trends in Neurosciences*, 44(9), 692-704. [DOI: 10.1016/j.tins.2021.04.005](https://doi.org/10.1016/j.tins.2021.04.005) — Modern synthesis of GWT with deep learning architectures. Discusses how workspace mechanisms can be implemented in neural network systems.

---

## Recommendation

Proceed with GWT as the meta-orchestration architecture. Begin with Phase 1 (shared workspace + Redis) in the next build session. This requires:

1. Add Redis to VAULT via Ansible (new role or extend existing `docker_services` role)
2. Add `WorkspaceItem` model and workspace endpoints to agent server
3. Modify proactive agents (media, home) to write observations to workspace
4. Add workspace state widget to dashboard

Phase 1 is low-risk and immediately useful — even without competition or broadcast, a shared workspace gives cross-agent visibility that doesn't exist today. Phases 2-4 build on this foundation incrementally.

Create ADR when ready to commit to implementation.
