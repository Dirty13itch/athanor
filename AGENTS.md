# Agents & MCP Configuration

## MCP Servers

### Project-Scoped (`.mcp.json`)

| Server | Purpose | Status |
|--------|---------|--------|
| **sequential-thinking** | Multi-step structured reasoning | Active |
| **context7** | Live library/framework documentation | Active |
| **grafana** | Query Grafana dashboards at VAULT:3000 | Active |
| **filesystem** | File operations within project directory | Active |

### User-Scoped (Claude Code settings)

| Server | Purpose | Status |
|--------|---------|--------|
| **github** | GitHub API: repos, PRs, issues, commits | Active |
| **desktop-commander** | Persistent terminal sessions, SSH, file ops | Active |
| **memory** | Knowledge graph persistence across sessions | Active |

### Planned

| Server | When | Prerequisite |
|--------|------|-------------|
| **home-assistant-mcp** | After HA onboarding | HA running at VAULT:8123 |
| **unraid-mcp** | When available | VAULT Unraid API access |
| **postgresql-mcp** | When agents need persistent storage | PostgreSQL deployed |

---

## Agent Teams

Native multi-agent orchestration is available via:
```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

**When to use teams**: Parallel research, auditing multiple nodes simultaneously, multi-component builds, debugging with competing hypotheses. Each teammate is a full independent Claude Code session.

---

## Athanor Agent Framework

The LangGraph agent framework runs on Node 1:9000. Source code lives in `projects/agents/`.

### Architecture

- **Runtime**: LangGraph 1.0.8 + FastAPI
- **API**: OpenAI-compatible (`/v1/chat/completions`, `/v1/models`)
- **Backend LLM**: vLLM at localhost:8000 (Qwen3-32B-AWQ, TP=4)
- **Tool calling**: `--enable-auto-tool-choice --tool-call-parser hermes`

### Agents

| Agent | Type | Schedule | Status |
|-------|------|----------|--------|
| **General Assistant** | Reactive | On-demand | Running |
| **Research Agent** | Reactive | On-demand | Planned |
| **Media Agent** | Proactive | Every 15 min | Running |
| **Home Agent** | Proactive | Every 5 min | Not registered (blocked on HA onboarding) |
| **Creative Agent** | Reactive | On-demand | Planned |
| **Knowledge Agent** | Proactive | Daily 3 AM | Planned |

### Tool Groups

**System tools** (General Assistant):
- `check_services` — Docker container health across nodes
- `get_gpu_metrics` — DCGM exporter GPU utilization
- `get_vllm_models` — Currently loaded models
- `get_storage_info` — NFS mount usage

**Media tools** (Media Agent):
- `search_series` / `add_series` — Sonarr integration
- `search_movies` / `add_movie` — Radarr integration
- `get_plex_activity` / `get_plex_history` — Tautulli integration

**Home tools** (Home Agent):
- Planned: Home Assistant entity control, scene activation, sensor queries

### Deployment

Agents are deployed via Ansible role `ansible/roles/agents/` which sources from `projects/agents/` and deploys to `/opt/athanor/agents/` on Node 1. Docker Compose with `network_mode: host`.

---

## Contract-Driven Architecture

Specialist slots are defined by interface contracts, not model names. Any model that satisfies the contract can fill the slot:

| Slot | Contract | Current Model |
|------|----------|---------------|
| **Reasoning** | Tool calling, 32K+ context, structured output | Qwen3-32B-AWQ (TP=4, `--quantization awq`, 32K context) |
| **Fast Agent** | Tool calling, low latency, 8K context sufficient | Qwen3-14B (RTX 5090, 8K context, enforce-eager) |
| **Embedding** | Dense embeddings, 8K input | Planned: Qwen3-Embedding-0.6B |
| **Reranker** | Cross-encoder reranking | Planned: Qwen3-Reranker-0.6B |
| **Image Gen** | Text-to-image, LoRA support | FLUX.1 dev FP8 |
| **Video Gen** | Text/image-to-video | Planned: Wan2.2 FP8 |
