# Athanor System Specification

*The complete operational specification. If you could only read one document about how Athanor works, this is it.*

Last updated: 2026-02-25

---

## 1. System Overview

Athanor is a 4-node homelab that unifies AI inference, media management, home automation, creative tools, and game development under one coherent system. It is owned and operated by one person (Shaun Ulrich). Every design decision passes a single filter: **can one person understand, operate, debug, and fix this alone?**

The system runs 7 GPUs (136 GB VRAM), 7 AI agents, 25 services, and serves a unified dashboard. All inference routes through a central proxy. All configuration is managed by Ansible. All decisions are documented as ADRs.

**What makes it more than a homelab:** The agent layer. Seven specialized AI agents do real work — managing media, controlling the home, generating images, searching the web, writing code, answering questions about the system itself. They share a knowledge base (Qdrant vector store + Neo4j graph), route through a unified inference layer (LiteLLM), and are all accessible through a single dashboard with a chat interface.

**Where it's going:** From reactive (agents wait for commands) to proactive (agents act autonomously within defined boundaries). A GWT-inspired workspace (ADR-017, Phase 1 deployed) enables inter-agent coordination. A GPU orchestrator (ADR-018, Phase 2 deployed) manages hardware utilization. Preference learning and activity logging are live — pattern recognition is next.

For the full philosophy, see `docs/VISION.md`. For the build history, see `docs/BUILD-MANIFEST.md`.

---

## 2. Architecture Map

### Node Topology

```
                    ┌──────────────────────────────────────────────┐
                    │              Network (10GbE)                  │
                    │  USW Pro XG 10 PoE (192.168.1.31)            │
                    └──┬──────────┬──────────┬──────────┬──────────┘
                       │          │          │          │
              ┌────────┴───┐ ┌───┴────────┐ ┌┴─────────┐ ┌┴────────┐
              │  Foundry   │ │  Workshop  │ │  VAULT   │ │   DEV   │
              │  Node 1    │ │  Node 2    │ │  NAS     │ │  WSL2   │
              │  .244      │ │  .225      │ │  .203    │ │  .215   │
              └────────────┘ └────────────┘ └──────────┘ └─────────┘
```

| Node | Role | CPU | RAM | GPUs | Key Services |
|------|------|-----|-----|------|-------------|
| **Foundry** (.244) | Heavy inference, agents | EPYC 7663 56C/112T | 224 GB DDR4 ECC | 4x 5070 Ti + 4090 | vLLM TP=4, Embedding, Agent Server, Qdrant |
| **Workshop** (.225) | Light inference, creative, UI | TR 7960X 24C/48T | 128 GB DDR5 | 5090 + 5060 Ti | vLLM (14B), ComfyUI, Dashboard, EoBQ, Open WebUI |
| **VAULT** (.203) | Storage, routing, media, monitoring | Ryzen 9950X 16C/32T | 128 GB DDR5 | Arc A380 | LiteLLM, Neo4j, Prometheus, Grafana, Plex, *arr, HA |
| **DEV** (.215) | Development workstation | i7-13700K 16C/24T | 64 GB DDR5 | RX 5700 XT | Claude Code (WSL2), Ansible control node |

### Data Flows

**User request → Agent response:**
```
User (Dashboard/Chat)
  → Dashboard API (Node 2:3001)
    → Agent Server (Node 1:9000)
      → LiteLLM Proxy (VAULT:4000)
        → vLLM (Node 1:8000 or Node 2:8000)
      ← Response streams back through same path
```

**Agent using tools:**
```
Agent Server receives request
  → LangGraph routes to correct agent
    → Agent calls tool (e.g., Sonarr API, HA API, Qdrant)
    → Tool returns result
    → Agent generates response via LiteLLM → vLLM
  ← Streams response to client
```

**Knowledge indexing (daily at 03:00):**
```
scripts/index-knowledge.py (DEV cron or manual)
  → Scans docs/ directory (81 files)
  → Chunks into segments
  → Embeds via LiteLLM → Qwen3-Embedding-0.6B (Node 1:8001)
  → Upserts to Qdrant (Node 1:6333) — 922 vectors
```

### Service Inventory

Full inventory in `docs/SERVICES.md`. Summary:

- **Node 1 (7 services):** vLLM (32B), vLLM Embedding, Agent Server, Qdrant, GPU Orchestrator, node_exporter, dcgm-exporter
- **Node 2 (7 services):** vLLM (14B), Dashboard, ComfyUI, EoBQ, Open WebUI, node_exporter, dcgm-exporter
- **VAULT (12 services):** LiteLLM, Neo4j, Prometheus, Grafana, Plex, Sonarr, Radarr, Prowlarr, SABnzbd, Tautulli, Stash, Home Assistant

### Model Inventory

| Model | Size | Location | GPU(s) | Purpose | LiteLLM Alias |
|-------|------|----------|--------|---------|---------------|
| Qwen3-32B-AWQ | 18 GB | Node 1:8000 | GPUs 0-3 (TP=4) | Reasoning, agents | `reasoning` |
| Qwen3-14B | 28 GB | Node 2:8000 | GPU 0 (5090) | Fast inference | `fast` |
| Qwen3-Embedding-0.6B | 1.2 GB | Node 1:8001 | GPU 4 (5070 Ti) | Embeddings | `embedding` |
| Flux dev FP8 | 17 GB | Node 2 ComfyUI | GPU 1 (5060 Ti) | Image generation | — |

All inference routes through LiteLLM at VAULT:4000. Agents and dashboard use model aliases (`reasoning`, `fast`, `embedding`), never direct URLs.

---

## 3. Agent System

### Agent Roster

| Agent | Model | Temperature | Mode | Status |
|-------|-------|-------------|------|--------|
| General Assistant | reasoning (32B) | 0.7 | Reactive | Live |
| Media Agent | reasoning (32B) | 0.7 | Reactive (planned proactive) | Live |
| Home Agent | reasoning (32B) | 0.7 | Reactive (planned proactive) | Live |
| Research Agent | reasoning (32B) | 0.7 | Reactive | Live |
| Creative Agent | fast (14B) | 0.8 | Reactive | Live |
| Knowledge Agent | reasoning (32B) | 0.3 | Reactive | Live |
| Coding Agent | reasoning (32B) | 0.3 | Reactive | Live |
| Stash Agent | — | — | Reactive + Proactive | Planned |

All agents are LangGraph `create_react_agent` instances with tool-calling and in-memory conversation checkpointing. They expose an OpenAI-compatible chat completions API at Node 1:9000.

Formal behavior contracts for each agent are in `docs/design/agent-contracts.md`.

### Inter-Agent Coordination

**GWT Workspace (ADR-017, Phase 1 deployed):** Redis-backed shared workspace. Agents compete to broadcast information. A 1Hz competition cycle selects the most salient items (capacity: 7) and broadcasts them to all subscribed agents. REST API at Node 1:9000/v1/workspace. This enables:
- Media Agent detects new episode → broadcasts to workspace → Home Agent dims lights
- Research Agent finds relevant info → broadcasts → Knowledge Agent indexes it
- Home Agent detects Shaun left → broadcasts → Media Agent pauses Plex

### Agent Lifecycle

**Current:** All agents initialize at server startup and stay loaded in memory. No sleep/wake, no dynamic registration.

**Planned:**
1. **Registration** — Agent declares capabilities, tools, activation thresholds
2. **Activation** — Agent is loaded and ready to receive requests
3. **Sleep** — Agent stays registered but releases resources (future, tied to GPU orchestrator)
4. **Deactivation** — Agent removed from rotation (manual, for maintenance)

### Escalation Protocol (deployed)

Three-tier confidence-based escalation with per-agent/per-action thresholds:

| Confidence | Action | Notification |
|------------|--------|-------------|
| > 0.8 | Act autonomously | Log to activity feed |
| 0.5 – 0.8 | Act but notify | Dashboard notification (non-blocking) |
| < 0.5 | Ask before acting | Chat panel / push notification / hold in queue |

Thresholds are per-agent and per-action-type:
- **Low-stakes** (check status, search, report): act at 0.5+
- **Medium-stakes** (add media, adjust lights): notify at 0.6+
- **High-stakes** (delete content, change settings, spend money): ask below 0.95

---

## 4. User Interaction Model

### How Shaun Interacts

| Interface | Current | Use Case |
|-----------|---------|----------|
| **Dashboard** (Node 2:3001) | Live | System overview, chat, monitoring |
| **Terminal** (DEV/WSL2) | Live | Claude Code sessions, Ansible, SSH |
| **Open WebUI** (Node 2:3000) | Live | Direct model chat (no agents) |
| **Mobile** (Termius) | Planned | SSH into tmux sessions from phone |
| **Voice** | Future | Hands-free interaction |

The dashboard is the primary interface — a Next.js app with dark theme, live system metrics, and an integrated chat panel that can talk to any agent.

### Transparency Model

Every agent action is visible. Nothing happens silently.

| Event Type | Where | When | Urgency |
|------------|-------|------|---------|
| Agent took autonomous action | Activity feed | Real-time | Low |
| Agent needs input | Notification bell + chat | Real-time | Medium |
| Background job completed | Activity feed | Batched (hourly) | Low |
| System health issue | Alert banner + push | Real-time | High |
| Agent learned something | Insights section | Daily digest | Low |
| Build session completed | Activity feed + terminal | After completion | Medium |

**Activity log:** All agent actions are logged to a structured `activity` Qdrant collection — browsable, searchable, filterable by agent/time/type. The dashboard Activity Feed page renders this log.

### Dashboard Pages

| Page | Status | Purpose |
|------|--------|---------|
| Home | Live | System overview, quick links, health summary |
| GPUs | Live | GPU utilization, VRAM, temperature, orchestrator status |
| Monitoring | Live | Per-node CPU/memory/disk/network metrics |
| Agents | Live | Agent roster, status, capabilities |
| Chat | Live | Talk to any agent, tool call visualization |
| Gallery | Live | Image generation history from ComfyUI |
| Media | Live | Sonarr/Radarr/Plex integration |
| Home | Live | Home Assistant entity overview |
| Services | Live | Service health checks across all nodes |
| Activity Feed | Live | Every agent action, searchable, filterable |
| Notifications | Live | Escalation alerts, agent requests |
| Preferences | Live | Stored preferences, editable |
| Workspace | Planned | GWT workspace — what agents are working on |
| Insights | Planned | What agents learned, pattern detections |

### Feedback Mechanisms

How agents learn what Shaun wants (three layers, progressively deeper):

**1. Explicit preferences (immediate)**
A `preferences` Qdrant collection stores explicit signals:
- Thumbs up/down on agent outputs
- "Remember I like X" statements
- Configuration choices
- Agents query this collection before acting
- Stored as embeddings + metadata for semantic retrieval

**2. Behavioral patterns (accumulated)**
Over time, agents observe patterns:
- Which recommendations get accepted vs rejected
- Which shows get watched to completion vs abandoned
- What time of day certain agents are used
- What generation parameters produce kept vs regenerated images
- This feeds intelligence layers 2→3 (see Section 6)

**3. Codified conventions (permanent)**
Patterns confirmed across multiple interactions get promoted to:
- Skill files (`.claude/skills/`)
- Agent system prompts
- Config defaults
- This is the permanent memory — persists even if Qdrant is wiped

---

## 5. Development Model

### Orchestrator Model

Shaun specifies requirements and architectural intent. AI agents write the code. Shaun reviews, tests, and refines. This is not "Shaun codes with AI assistance" — it's "AI codes under Shaun's direction."

### Cloud/Local Hybrid

**Cloud AI (Claude Code, Kimi Code):**
- Architecture design and review
- Novel problem solving
- Cross-codebase reasoning
- Large-context analysis
- This document was written by Claude Code

**Local AI (Qwen3-32B, Qwen3-14B):**
- Boilerplate generation
- Pattern application
- Test execution
- Bulk edits and refactoring
- Agent-driven tasks

The full hybrid development architecture (MCP bridge, Agent Teams, dispatch heuristics) is specified in `docs/design/hybrid-development.md`.

### Build Workflow

**Interactive sessions:** Shaun opens Claude Code, describes what to build, Claude Code implements it. Most current work happens this way.

**Autonomous builds (`/build`):** Claude Code reads `BUILD-MANIFEST.md`, picks the next unblocked item, executes it completely (research → implement → test → document → commit), updates tracking files, continues to next item.

**Session continuity:** `MEMORY.md` tracks what happened and what's next. Claude Code reads it at session start to pick up where the last session left off.

### Project Organization

Each project lives in `projects/{name}/` with its own:
- Source code and build config
- Docker and Ansible deployment
- Project-specific documentation in `docs/projects/{name}/`

Projects share Athanor's infrastructure (GPU, storage, networking, inference) but don't interfere with each other. Adding a new project means creating a directory and an Ansible role.

| Project | Directory | Status | Deployed |
|---------|-----------|--------|----------|
| Agent Server | `projects/agents/` | Live | Node 1:9000 |
| Dashboard | `projects/dashboard/` | Live | Node 2:3001 |
| Empire of Broken Queens | `projects/eoq/` | Live (mock) | Node 2:3002 |
| Kindred | `projects/kindred/` | Concept only | — |
| Ulrich Energy | `projects/ulrich-energy/` | Placeholder | — |

---

## 6. Intelligence Progression

The system evolves through four layers. Each layer builds on the previous and has specific infrastructure requirements.

### Layer 1: Reactive Intelligence (current)

Agents respond to requests. No memory between invocations beyond what's in the conversation thread. The agent server classifies input by model name and routes to the correct agent. Agents call tools, get results, generate responses.

**Infrastructure:** vLLM, LangGraph, LiteLLM, tool APIs.
**Verification:** Agent responds correctly to direct questions. Tools return accurate data.

### Layer 2: Accumulated Knowledge (deployed, context injection pending)

Knowledge base (922 vectors), preferences collection, activity logging, and escalation protocol are all deployed. Neo4j stores structural relationships (30 nodes, 29 relationships).

**What's deployed:** Knowledge indexing, preference storage + retrieval (REST API + dashboard), activity logging (fire-and-forget on every chat completion), escalation protocol (3-tier confidence).

**What's missing for full Layer 2:**
- Context injection — agents don't query preferences/activity before responding (data exists, plumbing doesn't)
- Conversation history indexing (collection exists but isn't populated)
- Proactive knowledge indexing (currently manual, should be cron)

**Infrastructure:** Qdrant, Neo4j, embedding model, index scripts, Redis.
**Verification:** Agent cites relevant ADRs/research when answering questions about past decisions. Preferences are stored and queryable.

### Layer 3: Pattern Recognition (planned)

Agents recognize patterns in their own operation and user behavior:

| Agent | Pattern Source | What It Learns |
|-------|---------------|----------------|
| Media Agent | Watch history, add/ignore signals | Content preferences, genre weights |
| Home Agent | Occupancy sensors, time patterns | Daily routines, seasonal adjustments |
| Research Agent | Source acceptance/rejection | Preferred sources, useful formats |
| Creative Agent | Kept vs regenerated images | Style preferences, parameter defaults |
| Knowledge Agent | Query patterns, retrieval success | What docs are most useful, gaps in coverage |

**Feedback signals:**
- Implicit: media watched to completion, image kept, automation not overridden
- Explicit: thumbs up/down, "remember this" statements, preference edits
- Meta: which agent actions led to follow-up requests (indicating incomplete results)

**Infrastructure:** Preference collection (deployed), activity logging (deployed), pattern detection jobs (not started), context injection (not started).
**Verification:** Agent recommendations improve measurably over time. Media Agent stops suggesting genres Shaun ignores.

### Layer 4: Self-Optimization (future)

The system monitors its own performance and optimizes:
- Which models produce the best results for which tasks
- Which GPU allocation minimizes latency for the current workload
- When to auto-evaluate new model releases against baseline
- When knowledge accumulation shows diminishing returns → trigger summarization

**Infrastructure:** All of the above + metrics correlation + A/B testing framework.
**Verification:** System makes a recommendation to change its own configuration that improves measured performance.

Full details in `docs/design/intelligence-layers.md`.

---

## 7. Resource Management

### GPU Allocation

| GPU | Node | VRAM | Current Workload | Utilization |
|-----|------|------|-----------------|-------------|
| GPU 0 (5070 Ti) | Node 1 | 16 GB | vLLM TP=4 shard | ~10-27% |
| GPU 1 (5070 Ti) | Node 1 | 16 GB | vLLM TP=4 shard | ~10-27% |
| GPU 2 (5070 Ti) | Node 1 | 16 GB | vLLM TP=4 shard | ~10-27% |
| GPU 3 (4090) | Node 1 | 24 GB | vLLM TP=4 shard | ~10-27% |
| GPU 4 (5070 Ti) | Node 1 | 16 GB | Embedding model (1.2 GB used) | <5% |
| GPU 0 (5090) | Node 2 | 32 GB | vLLM Qwen3-14B | ~10-15% |
| GPU 1 (5060 Ti) | Node 2 | 16 GB | ComfyUI Flux | <5% (idle unless generating) |

**Total:** 136 GB VRAM allocated, ~15% average compute utilization.

**Planned optimization (ADR-018):** Custom GPU orchestrator with vLLM Sleep Mode integration. Priority-based scheduling: Interactive > Agent > Creative > Batch > Training. Sleep-level 1 frees ~80% VRAM (wake <1s), level 2 frees ~100% (wake ~5-10s).

### Model Lifecycle

**Current:** All models are always loaded. No sleep/wake, no swapping.

**Planned states:**
1. **Active** — Model loaded in VRAM, ready for requests
2. **Sleeping L1** — KV cache offloaded to CPU RAM, model weights in VRAM, wake <1s
3. **Sleeping L2** — Weights offloaded to CPU RAM, VRAM freed, wake ~5-10s
4. **Stopped** — Container stopped, VRAM completely free

### Background Job Schedule

| Time | Job | Node | Description |
|------|-----|------|-------------|
| 03:00 | Qdrant backup | Node 1 | Snapshot API → NFS → VAULT |
| 03:15 | Neo4j backup | VAULT | Cypher export to `/mnt/user/backups/` |
| 03:30 | Appdata backup | VAULT | Tar 11 service appdatas |
| Manual | Knowledge index | DEV | `python3 scripts/index-knowledge.py` |

### Storage

| Mount | Source | Nodes | Purpose |
|-------|--------|-------|---------|
| `/mnt/vault/models` | VAULT NFS | Node 1, Node 2 | Shared model files |
| `/mnt/vault/data` | VAULT NFS | Node 1, Node 2 | Shared data (backups, outputs) |
| VAULT HDD array | Local | VAULT | 164 TB usable, 89% used |

**Gotcha:** NFS mounts go stale after VAULT reboots. The Ansible common role auto-recovers, but manual fix is `sudo umount -f /mnt/vault/models && sudo mount -a`.

---

## 8. Organizational Structure

Athanor doesn't have departments. It has clear responsibilities.

### Responsibility Map

| Responsibility | Owner | Agent Support | Tooling |
|----------------|-------|---------------|---------|
| Architecture & decisions | Shaun + Claude Code | — | ADRs in `docs/decisions/` |
| Infrastructure operations | Claude Code (lead) | General Assistant | Ansible, Prometheus |
| Agent development | Claude Code (lead) | — | LangGraph, FastAPI |
| Knowledge management | Knowledge Agent | Auto-indexing | Qdrant, Neo4j |
| Media operations | Media Agent | Proactive scans (planned) | Sonarr, Radarr, Plex |
| Home automation | Home Agent | Pattern learning (planned) | Home Assistant |
| Creative production | Creative Agent | — | ComfyUI, Flux |
| System monitoring | Prometheus + Grafana | Alerting rules | Dashboard |
| Documentation | Claude Code | — | Markdown, ADRs |
| Research | Research Agent | Web search | DuckDuckGo, Qdrant |
| Backup & recovery | Cron scripts | — | Automated daily |

### Decision Process

```
Research → Document findings in docs/research/
  → Evaluate options against one-person-scale filter
    → Write ADR in docs/decisions/
      → Build, test, deploy
        → Update BUILD-MANIFEST.md
```

18 ADRs documented to date. Every technology choice has a rationale and evaluated alternatives.

### Incident Process (planned)

```
Alert (Prometheus/Grafana)
  → Investigate (agent or Claude Code)
    → Fix (Ansible re-converge or manual)
      → Postmortem (if significant)
        → Update docs/gotchas or create ADR
```

### Feedback Loop

```
Agent acts
  → User responds (explicit or implicit)
    → Signal stored in preferences collection
      → Agent queries preferences next time
        → Better action
```

---

## Appendix: Key File Paths

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code role, principles, project structure |
| `MEMORY.md` | Session continuity between Claude Code sessions |
| `docs/VISION.md` | Philosophy, identity, non-negotiables |
| `docs/BUILD-MANIFEST.md` | Build plan with priorities and status |
| `docs/SERVICES.md` | Live service inventory |
| `docs/SYSTEM-SPEC.md` | This document |
| `docs/design/agent-contracts.md` | Per-agent behavior specifications |
| `docs/design/hybrid-development.md` | Cloud/local coding architecture |
| `docs/design/intelligence-layers.md` | Intelligence progression details |
| `docs/hardware/inventory.md` | Complete hardware inventory |
| `docs/decisions/ADR-*.md` | Architecture Decision Records |
| `docs/research/*.md` | Research notes |
| `projects/agents/` | Agent server source |
| `projects/dashboard/` | Dashboard source |
| `projects/eoq/` | Empire of Broken Queens source |
| `ansible/` | Infrastructure as Code |
| `scripts/` | Utility scripts |
