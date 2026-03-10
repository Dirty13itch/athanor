# Agents & MCP Configuration

## Claude Code Custom Agents (`.claude/agents/`)

| Agent | Model | Purpose | Isolation |
|-------|-------|---------|-----------|
| **infra-auditor** | Opus | Audit hardware, topology, and runtime drift | Worktree |
| **researcher** | Opus | Deep technical research with sources | Worktree, background |
| **doc-writer** | Sonnet | Documentation creation and maintenance | Worktree |
| **Local Coder** | Local | Dispatch coding to Athanor's local inference stack via MCP | MCP bridge |

## MCP Servers

### Project-Scoped (`.mcp.json`)

| Server | Purpose | Status |
|--------|---------|--------|
| **grafana** | Query Grafana dashboards and Prometheus-backed observability | Active |
| **docker** | Docker container management across Athanor nodes | Active |
| **athanor-agents** | MCP bridge to 9 local agents and the task API | Active |
| **smart-reader** | Enhanced file reading | Disabled |

### Cloud Connectors (claude.ai)

| Server | Purpose | Status |
|--------|---------|--------|
| **Context7** | Library and framework documentation lookup | Active |
| **Gmail** | Email integration | Active |
| **Google Calendar** | Calendar management | Active |

### Removed

Previously used, removed from `.mcp.json`: sequential-thinking, local Context7 duplicate, filesystem, playwright.

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
- **API:** OpenAI-compatible (`/v1/chat/completions`, `/v1/models`, `/v1/agents`, `/v1/tasks`)
- **Inference contract:** LiteLLM on VAULT is the canonical model router
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
| **creative** | Utility and uncensored specialist work | Foundry utility (`:8002`) | Foundry |
| **utility** | Utility alias for local specialist work | Foundry utility (`:8002`) | Foundry |
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

### Deployment

Agents are deployed via `ansible/roles/agents/`, sourced from `projects/agents/`, and deployed to `/opt/athanor/agents/` on Foundry. Runtime topology and env wiring should be treated as Ansible-owned, not inferred from checked-in compose snapshots.

---

## Contract-Driven Operating Rules

- Use LiteLLM aliases, not direct backend URLs, for application and agent inference.
- Treat DEV as the canonical embedding and reranker host.
- Treat the dashboard as the primary operator-facing surface and the task/work planner as the project coordination surface.
- Keep credentials out of tracked docs and defaults; use vaulted or env-backed values instead.
