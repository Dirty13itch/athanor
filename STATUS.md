# Athanor System Status

*Ground-truth assessment as of 2026-03-08. Auto-generated from live cluster inspection.*

---

## Claude Code Environment

| Item | Status | Details |
|------|--------|---------|
| Claude Code | v2.1.71 native install | `~/.local/share/claude/versions/2.1.71` — auto-updates ✅ |
| Model | opus (claude-opus-4-6) | Set in `~/.claude/settings.json` |
| Effort | high | Set in user settings |
| mosh | Installed | `/usr/bin/mosh` |
| tmux launcher | Created | `~/bin/athanor` |
| Aider | Installed | `~/.local/bin/aider`, config at `.aider.conf.yml` |
| Goose | Installed | v1.27.2 at `/usr/local/bin/goose`, config at `~/.config/goose/profiles.yaml` |
| claude-squad | Installed | v1.0.16 at `/usr/local/bin/cs` |

## MCP Servers

| Server | Source | Status | Purpose |
|--------|--------|--------|---------|
| grafana | .mcp.json (local) | Active | Query Grafana dashboards, alerts, datasources |
| docker | .mcp.json (local) | Active | Docker container management |
| athanor-agents | .mcp.json (local) | Active | Agent server at foundry:9000 |
| redis | .mcp.json (local) | Active | Redis state, heartbeats, workspace, scheduler |
| qdrant | .mcp.json (local) | Active | Vector DB collections, search, scroll |
| smart-reader | .mcp.json (local) | Active | Smart file reading, grep, diff, log |
| Context7 | claude.ai connector | Active | Library documentation lookup |
| Gmail | claude.ai connector | Active | Email integration |
| Google Calendar | claude.ai connector | Active | Calendar management |
| Grafana | claude.ai connector | Active (duplicate) | Same as local, managed by Anthropic |
| Hugging Face | claude.ai connector | Active | Model/dataset search — low value for ops |
| Vercel | claude.ai connector | Active | Deployment platform — not currently used |

**Removed from local config:** sequential-thinking, context7 (plugin duplicate), filesystem, playwright.

## Configuration Inventory

### Commands (10)
`audit` `build` `decide` `deploy` `health` `morning` `orient` `project` `research` `status`

### Skills (13)
`architecture-decision` `athanor-conventions` `comfyui-deploy` `deploy-agent` `deploy-docker-service` `gpu-placement` `local-coding` `network-diagnostics` `node-ssh` `state-update` `troubleshoot` `verify-inventory` `vllm-deploy`

### Agents (6)
`coder` `debugger` `doc-writer` `infra-auditor` `node-inspector` `researcher`

### Rules (10)
`agents` `ansible` `dashboard` `docker` `docs` `eoq` `knowledge` `scripts` `session-continuity` `vllm`

### Hooks (12 scripts, 14 registrations)
| Hook | Event | Purpose |
|------|-------|---------|
| pre-tool-use-protect-paths | PreToolUse (Edit/Write) | Protects critical files from accidental overwrites |
| pre-tool-use-bash-firewall | PreToolUse (Bash) | Blocks dangerous commands |
| post-tool-use-typecheck | PostToolUse (Edit/Write) | Runs TypeScript/Python checks after edits |
| post-tool-use-failure | PostToolUseFailure | Injects diagnostic context on tool failures |
| pre-compact-save | PreCompact | Saves session state before context compression |
| session-start | SessionStart | Loads context at session start |
| session-start-health | SessionStart | Quick cluster health check |
| session-end | SessionEnd | Updates STATUS.md timestamp |
| stop-autocommit | Stop | Auto-commits state files on session end |
| task-completed-notify | TaskCompleted | Desktop notification for background tasks |
| user-prompt-context | UserPromptSubmit | Injects timestamp + git context |
| statusline | StatusLine | Node health from Redis heartbeats |

## Cluster State

### FOUNDRY (.244) — 11 containers

| GPU | Model | VRAM | Temp | Container | Port | Flags |
|-----|-------|------|------|-----------|------|-------|
| 0: RTX 5070 Ti (MSI) | Qwen3-32B-AWQ (TP=2) | 14.9/16.3 GB | 37°C | vllm-reasoning | 8000 | `--tool-call-parser hermes --kv-cache-dtype fp8_e5m2 --enforce-eager` |
| 1: RTX 5070 Ti (Gigabyte) | Qwen3-32B-AWQ (TP=2) | 14.9/16.3 GB | 47°C | (shared with GPU 0) | — | — |
| 2: RTX 4090 (ASUS) | GLM-4.7-Flash-GPTQ-4bit | 23.0/24.6 GB | 45°C | vllm-coding | 8002 | `--tool-call-parser hermes --quantization gptq_marlin --enable-sleep-mode` |
| 3: RTX 5070 Ti (Gigabyte) | Huihui-Qwen3-8B | 15.0/16.3 GB | 30°C | vllm-creative | 8004 | `--quantization fp8 --enable-sleep-mode` |
| 4: RTX 5070 Ti (MSI) | **IDLE** | 0.0/16.3 GB | 34°C | — | — | Available for new workload |

Other containers: `athanor-agents` (9000), `athanor-gpu-orchestrator`, `alloy`, `wyoming-whisper` (10300), `qdrant` (6333-6334), `speaches` (8200), `dcgm-exporter` (9400), `node-exporter`

### WORKSHOP (.225) — 9 containers

| GPU | Model | VRAM | Temp | Container | Port |
|-----|-------|------|------|-----------|------|
| 0: RTX 5090 | Qwen3.5-35B-A3B-AWQ-4bit | 31.3/32.6 GB | 38°C | vllm-node2 | 8000 |
| 1: RTX 5060 Ti | ComfyUI | 5.1/16.3 GB | 32°C | comfyui | 8188 |

Other: `athanor-dashboard` (3001), `athanor-eoq` (3002), `athanor-ws-pty-bridge` (3100), `open-webui` (3000), `alloy`, `dcgm-exporter`, `node-exporter`

### VAULT (.203) — 42 containers

Key services: `litellm` (4000), `grafana` (3000), `prometheus`, `backup-exporter`, `n8n` (5678), `gitea` (3033), `miniflux` (8070), `redis`, `vault-open-webui` (3090), `langfuse-web` (3030) + 5 langfuse services, `neo4j` (7474/7687), `qdrant` (6333), `postgres` (5432), `stash` (9999), `plex`, `homeassistant`, media stack (sonarr/radarr/prowlarr/sabnzbd/tautulli/tdarr), `spiderfoot` (5001), `ntfy` (8880), `meilisearch` (7700), `field-inspect-app` (3080), monitoring (loki, alloy, cadvisor, node-exporter)

### DEV (.189) — 2 containers

| GPU | Model | VRAM | Container | Port |
|-----|-------|------|-----------|------|
| 0: RTX 5060 Ti | Embedding + Reranker | 4.8/16.3 GB | vllm-embedding (8001), vllm-reranker (8003) | 8001, 8003 |

## Service Health (verified from DEV)

| Endpoint | Model/Service | Status |
|----------|---------------|--------|
| foundry:8000 | Qwen3-32B-AWQ | ✅ Healthy |
| foundry:8002 | GLM-4.7-Flash-GPTQ-4bit | ✅ Healthy |
| foundry:8004 | Huihui-Qwen3-8B | ✅ Healthy |
| foundry:9000 | Agent Server (9 agents) | ✅ Healthy |
| workshop:8000 | Qwen3.5-35B-A3B-AWQ-4bit | ✅ Healthy |
| vault:4000 | LiteLLM (14 model routes) | ✅ Healthy |

### LiteLLM Model Routes
`reasoning` `coding` `fast` `creative` `embedding` `reranker` `worker` `claude` `gpt` `deepseek` `gemini` + aliases (`gpt-4` `gpt-3.5-turbo` `text-embedding-ada-002`)

## Known Issues & Blockers

| Issue | Impact | Resolution |
|-------|--------|------------|
| **Ansible vault-password** | Resolved | Vault recreated 2026-03-08, `ansible vault -m ping` verified |
| **MSI 5070 Ti RGB still ON** (×2) | Cosmetic | I2C port 1 not exposed on Blackwell. Fix: one-time MSI Center from Windows |
| **FOUNDRY GPU 4 idle** | 16 GB VRAM unused | Could serve embedding, reranker, or another model |
| **NordVPN credentials** | qBittorrent blocked | Shaun needs to provide |
| **Anthropic API key** | Quality Cascade cloud escalation blocked | Shaun needs to provide |
| **Google Drive OAuth** | ~40% personal data inaccessible | Shaun needs to run rclone config |

## Build Progress

All 16 tiers COMPLETE. Remaining open items are backlog or blocked on Shaun:
- 6.2 InfiniBand (backlog)
- 6.4 Mobile access (backlog)
- 6.7 Mining enclosure (physical)
- 8.4 Dedicated Coding Model (deferred)
- 14.3 Home Assistant depth (needs Shaun)
- 14.5 Kindred prototype (awaiting decision)

---

*Last updated: 2026-03-08 21:10 PDT
