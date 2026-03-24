# Agents & MCP Configuration

## Claude Code Custom Agents (`.claude/agents/`)

| Agent | Model | Purpose | Isolation |
|-------|-------|---------|-----------|
| **infra-auditor** | Opus | Audit hardware, topology, and runtime drift | Worktree |
| **researcher** | Opus | Deep technical research with sources | Worktree, background |
| **doc-writer** | Sonnet | Documentation creation and maintenance | Worktree |
| **coder** | Opus | Dispatch boilerplate/refactor/test coding to local Qwen3.5-27B-FP8 via MCP | MCP bridge |
| **debugger** | Inherit | Root cause analysis for errors, service failures, and performance issues | Project memory |
| **node-inspector** | Haiku | Fast node health checks via SSH: GPU status, containers, disk, endpoints | Background |

## MCP Servers

### Always-On (`.mcp.json`)

8 servers loaded every session:

| Server | Purpose |
|--------|---------|
| **docker** | Docker container management across Athanor nodes |
| **athanor-agents** | MCP bridge to 9 local agents and the task API |
| **redis** | Redis state, heartbeats, workspace, scheduler |
| **qdrant** | Vector DB collections, search, scroll |
| **smart-reader** | Enhanced file reading, grep, diff, log |
| **sequential-thinking** | Structured reasoning meta-tool |
| **neo4j** | Direct Cypher queries to knowledge graph |
| **postgres** | SQL access to VAULT databases |

### Disabled by Default (enable per-session via `/mcp`)

| Server | Purpose |
|--------|---------|
| **grafana** | Query Grafana dashboards and Prometheus-backed observability |
| **langfuse** | Trace debugging and prompt management |
| **miniflux** | RSS feed tools |
| **n8n** | Workflow automation |
| **gitea** | Repo/issue/PR management |
| **context7** | Live library docs (resolve-library-id, query-docs) |
| **github** | GitHub repo management (needs GITHUB_TOKEN) |

### Cloud Connectors (claude.ai)

| Server | Purpose | Status |
|--------|---------|--------|
| **Gmail** | Email integration | Active |
| **Google Calendar** | Calendar management | Active |

### Removed

Previously used, removed from config: filesystem, playwright, local context7 duplicate.

---

## Agent Teams

Native multi-agent orchestration is available via:

```bash
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

Use teams for parallel research, topology audits, multi-surface dashboard work, or competing debugging hypotheses.

---

## Athanor Agent Framework

The LangGraph agent framework runs on Foundry (`:9000`). Source code lives in `projects/agents/`.

### Architecture

- **Runtime:** LangGraph + FastAPI
- **API:** OpenAI-compatible (`/v1/chat/completions`, `/v1/models`, `/v1/agents`, `/v1/tasks`) plus subscription broker endpoints under `/v1/subscriptions`
- **Inference contract:** LiteLLM on VAULT is the canonical local model router
- **Subscription control layer:** brokered execution leases route cloud/provider usage through policy instead of direct vendor calls
- **Knowledge fabric:** Qdrant + Neo4j + Redis
- **Coordination substrate:** GWT workspace, task engine, work planner, activity and preference signals

### Agents (9 live)

| Agent | Mode | Schedule | Status |
|-------|------|----------|--------|
| **General Assistant** | Reactive + proactive | 30 min | Live |
| **Media Agent** | Reactive + proactive | 15 min | Live |
| **Home Agent** | Reactive + proactive | 5 min | Live |
| **Research Agent** | Reactive | On-demand | Live |
| **Creative Agent** | Reactive | On-demand | Live |
| **Knowledge Agent** | Reactive | On-demand | Live |
| **Coding Agent** | Reactive | On-demand | Live |
| **Stash Agent** | Reactive | On-demand | Live |
| **Data Curator** | Reactive | On-demand | Live |

Formal behavior contracts live in `docs/design/agent-contracts.md`.

### Runtime Slots

Specialist slots are defined by contracts, not model names.

| Slot | Role | Current Runtime | Node |
|------|------|-----------------|------|
| **reasoning** | Large-model reasoning and coding | Foundry coordinator (`:8000`) | Foundry |
| **coding** | Same reasoning lane, coding-oriented alias | Foundry coordinator (`:8000`) | Foundry |
| **coder** | Dedicated coding and tool-use lane | Foundry coder (`:8006`) | Foundry |
| **creative** | Creative-adjacent local work | Workshop worker (`:8000`) | Workshop |
| **utility** | Utility alias for local specialist work | Workshop worker (`:8000`) | Workshop |
| **fast** | Interactive worker lane | Workshop worker (`:8000`) | Workshop |
| **worker** | Worker alias | Workshop worker (`:8000`) | Workshop |
| **embedding** | Retrieval embeddings | DEV embedding (`:8001`) | DEV |
| **reranker** | Retrieval reranking | DEV reranker (`:8003`) | DEV |

### Tool Domains

- **System and ops:** services, GPU metrics, storage, task delegation, workspace state
- **Media:** Sonarr, Radarr, Tautulli, Plex, Stash
- **Home:** Home Assistant state, automations, and device control
- **Creative:** ComfyUI image/video generation and queue inspection
- **Knowledge:** Qdrant search, Neo4j queries, retrieval stats
- **Coding and execution:** repository reads, controlled writes, command execution, test loops
- **Subscription escalation:** Coding and Research agents can request execution leases before recommending off-cluster work

### Deployment

Agents are deployed via `ansible/roles/agents/`, sourced from `projects/agents/`, and deployed to `/opt/athanor/agents/` on Foundry. Runtime topology and env wiring should be treated as Ansible-owned, not inferred from checked-in compose snapshots.

---

## Contract-Driven Operating Rules

- Use LiteLLM aliases, not direct backend URLs, for application and agent inference.
- Treat DEV as the canonical embedding and reranker host.
- Treat the dashboard as the primary operator-facing surface and the task/work planner as the project coordination surface.
- Keep credentials out of tracked docs and defaults; use vaulted or env-backed values instead.
