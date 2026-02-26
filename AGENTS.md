# Agents & MCP Configuration

## Claude Code Custom Agents (`.claude/agents/`)

| Agent | Model | Purpose | Isolation |
|-------|-------|---------|-----------|
| **infra-auditor** | Opus | Audit hardware/network against documented state | Worktree |
| **researcher** | Opus | Deep technical research with sources | Worktree, background |
| **doc-writer** | Sonnet | Documentation creation and maintenance | Worktree |
| **Local Coder** | — | Dispatch coding to local Qwen3-32B via MCP bridge | — |

## MCP Servers

### Project-Scoped (`.mcp.json`)

| Server | Purpose | Status |
|--------|---------|--------|
| **sequential-thinking** | Multi-step structured reasoning | Active |
| **context7** | Live library/framework documentation | Active |
| **grafana** | Query Grafana dashboards at VAULT:3000 | Active |
| **filesystem** | File operations within project directory | Active |
| **athanor-agents** | MCP bridge to 8 local agents (14 tools) | Active |

### Planned

| Server | When | Prerequisite |
|--------|------|-------------|
| **memory** | When persistent cross-session knowledge graph needed | Node.js |
| **home-assistant-mcp** | After HA onboarding | HA running at VAULT:8123 |

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

### Agents (8 live)

| Agent | Type | Schedule | Tools | Status |
|-------|------|----------|-------|--------|
| **General Assistant** | Reactive + Delegation | 30 min | 9 + delegation | Running |
| **Research Agent** | Reactive | On-demand | 5 | Running |
| **Media Agent** | Proactive | 15 min | 6 (Sonarr/Radarr/Tautulli) | Running |
| **Home Agent** | Proactive | 5 min | 5 (HA) | Running |
| **Creative Agent** | Reactive | On-demand | 5 | Running |
| **Knowledge Agent** | Proactive | 24h (disabled) | 5 | Running |
| **Coding Agent** | Reactive | On-demand | 9 (autonomous loop) | Running |
| **Stash Agent** | Reactive | On-demand | 12 (GraphQL) | Running |

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

| Slot | Contract | Current Model | Node |
|------|----------|---------------|------|
| **Reasoning** | Tool calling, 32K+ context, structured output | Qwen3-32B-AWQ (TP=4) | Node 1 |
| **Fast Agent** | Tool calling, low latency | Qwen3-14B FP16 (5090) | Node 2 |
| **Embedding** | Dense embeddings, 1024-dim, 8K input | Qwen3-Embedding-0.6B | Node 1 (GPU 4) |
| **Reranker** | Cross-encoder reranking | Planned: Qwen3-Reranker-0.6B | Node 1 (CPU) |
| **Image Gen** | Text-to-image, LoRA support | FLUX.1 dev FP8 | Node 2 (5090) |
| **Video Gen** | Text/image-to-video | Wan2.1 FP8 | Node 2 (5090) |
| **TTS** | Text-to-speech | Kokoro-82M ONNX (Speaches) | Node 1 (GPU 4) |
| **STT** | Speech-to-text | wyoming-whisper | Node 1 (GPU 4) |
