# Athanor Services Map

*Live service inventory. Updated when services change.*

Last updated: 2026-03-07 (Session 36 — Full cluster audit and doc refresh)

## Node 1 — Foundry (192.168.1.244)

| Service | Port | Details |
|---------|------|---------|
| vLLM Reasoning (Qwen3-32B-AWQ) | 8000 | TP=2 across GPUs 0+1 (2x RTX 5070 Ti), `--quantization awq`, `--tool-call-parser hermes` |
| vLLM Creative (GLM-4.7-Flash-GPTQ-4bit) | 8002 | GPU 2 (RTX 4090), `--quantization gptq_marlin`, `--enable-sleep-mode` |
| vLLM Coding (Huihui-Qwen3-8B-abliterated-v2) | 8004 | GPU 3 (RTX 5070 Ti), `--quantization fp8`, `--enable-sleep-mode` |
| GPU 4 (RTX 5070 Ti) | — | **IDLE** — previously ran embedding model, not currently loaded |
| Agent Server | 9000 | 9 agents + GWT workspace + escalation + activity/preferences + routing + diagnosis + semantic cache + circuit breakers + self-improvement + preference learning APIs |
| Qdrant | 6333/6334 | Vector DB: knowledge (2484), personal_data (2304), conversations, activity, preferences (55), implicit_feedback, events |
| GPU Orchestrator | 9200 | 4 zones, DCGM metrics, vLLM sleep/wake, TTL auto-sleep, Prometheus export |
| wyoming-whisper | 10300 | STT for HA — faster-distil-whisper-large-v3 (float16), GPU 4 |
| Speaches | 8200 | OpenAI-compatible STT+TTS API — Kokoro + faster-whisper, GPU 4 |
| Grafana Alloy | — | Log/metric forwarding |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## Node 2 — Workshop (192.168.1.225)

| Service | Port | Details |
|---------|------|---------|
| vLLM (Qwen3.5-35B-A3B-AWQ-4bit) | 8000 | RTX 5090, vLLM nightly, `--tool-call-parser qwen3_xml`, `--kv-cache-dtype auto` |
| Dashboard | 3001 | Next.js 16, PWA, 5 lens modes, SSE real-time, 17+ pages |
| ws-pty Bridge | 3100 | WebSocket terminal bridge (node-pty + ws sidecar) |
| ComfyUI | 8188 | Flux dev FP8 + Wan2.x T2V, RTX 5060 Ti, WanVideoWrapper + KJNodes |
| EoBQ | 3002 | Empire of Broken Queens — Next.js game app |
| Open WebUI | 3000 | Chat interface (Workshop-local, routes to Node 1 vLLM) |
| Grafana Alloy | — | Log/metric forwarding |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## VAULT (192.168.1.203)

### Core Services

| Service | Port | Details |
|---------|------|---------|
| LiteLLM Proxy | 4000 | 14 routes: reasoning, coding, fast, creative, embedding, reranker, worker, claude, gpt, deepseek, gemini + aliases. LangFuse callbacks. Auth: `sk-athanor-litellm-2026` |
| Neo4j | 7474/7687 | Graph DB (3095 nodes, 4447 rels), auth: neo4j/athanor2026 |
| Redis | 6379 | GWT workspace + GPU orchestrator state + scheduler |
| Qdrant | 6333/6334 | VAULT-side vector DB instance |
| Postgres | 5432 | Shared PostgreSQL |
| Meilisearch | 7700 | Search engine |

### Observability

| Service | Port | Details |
|---------|------|---------|
| LangFuse Web | 3030 | v3.155.1, observability + tracing for LiteLLM |
| LangFuse Worker | — | Background job processor |
| LangFuse Postgres | — | LangFuse-dedicated PostgreSQL 16 |
| LangFuse ClickHouse | — | LangFuse metrics store |
| LangFuse Redis | — | LangFuse cache |
| LangFuse MinIO | — | LangFuse blob storage |
| Prometheus | 9090 | Metrics aggregation |
| Grafana | 3000 | admin/admin (default — container lacks GF_SECURITY_ADMIN_PASSWORD env) |
| Grafana Alloy | — | Log collection agent |
| Loki | — | Log aggregation |
| cadvisor | 9880 | Container metrics |
| node_exporter | 9100 | System metrics |

### Media Stack

| Service | Port | Details |
|---------|------|---------|
| Plex | 32400 | Media server |
| Sonarr | 8989 | TV management |
| Radarr | 7878 | Movie management |
| Prowlarr | 9696 | Indexer management |
| SABnzbd | 8080 | Usenet downloader |
| Tautulli | 8181 | Plex analytics |
| Stash | 9999 | Adult content management |
| Tdarr | 8265-8266 | Media transcoding (server + node) |

### Home + Voice

| Service | Port | Details |
|---------|------|---------|
| Home Assistant | 8123 | v2026.2.3, 38+ entities, agent token active |
| wyoming-piper | 10200 | TTS for HA — en_US-lessac-medium, CPU-only |
| wyoming-openwakeword | 10400 | Wake word detection for HA, CPU-only |

### Applications

| Service | Port | Details |
|---------|------|---------|
| Gitea | 3033 | Self-hosted git + CI/CD (SQLite, Actions enabled, admin: athanor/athanor2026) |
| Miniflux | 8070 | RSS reader (17 feeds, 6 categories, dedicated PostgreSQL, admin/athanor2026) |
| n8n | 5678 | Workflow automation — Miniflux RSS → LLM classification → Qdrant signals pipeline |
| Open WebUI (VAULT) | 3090 | Chat interface (routes through LiteLLM) |
| Spiderfoot | 5001 | OSINT tool |
| ntfy | 8880 | Push notification server |
| Field Inspect App | 3080 | Field inspection PWA (dedicated Postgres :5433, MinIO :9000-9001) |

## DEV (192.168.1.189)

| Service | Port | Details |
|---------|------|---------|
| Claude Code | — | Primary development tool (native install, auto-updates) |
| claude-squad | — | Multi-session Claude Code manager (git worktrees, parallel sessions) |
| Embedding (Qwen3-Embedding-0.6B) | 8001 | vLLM embedding model on RTX 5060 Ti |
| Reranker | 8003 | Reranker model on RTX 5060 Ti |
| Gitea Actions Runner | — | act_runner v0.2.11 (systemd service, self-hosted label) |

## LiteLLM Model Routes

| Route | Backend | Model | Node |
|-------|---------|-------|------|
| `reasoning` / `gpt-4` | vLLM | Qwen3-32B-AWQ | Foundry :8000 |
| `coding` | vLLM | Huihui-Qwen3-8B-abliterated-v2 | Foundry :8004 |
| `fast` / `gpt-3.5-turbo` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `creative` | vLLM | GLM-4.7-Flash-GPTQ-4bit | Foundry :8002 |
| `embedding` / `text-embedding-ada-002` | vLLM | Qwen3-Embedding-0.6B | DEV :8001 |
| `reranker` | vLLM | Reranker model | DEV :8003 |
| `worker` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `claude` | Anthropic API | Claude | Cloud |
| `gpt` | OpenAI API | GPT | Cloud |
| `deepseek` | DeepSeek API | DeepSeek | Cloud |
| `gemini` | Google API | Gemini | Cloud |

## Models on NFS (`/mnt/vault/models/`)

| Model | Size | Purpose |
|-------|------|---------|
| Qwen3-32B-AWQ | 19G | Reasoning (LiteLLM: `reasoning`) — Foundry TP=2 |
| Qwen3.5-35B-A3B-AWQ-4bit | — | Fast inference (LiteLLM: `fast`) — Workshop |
| Qwen3.5-27B-AWQ | 21G | Previous fast model (replaced by 35B-A3B) |
| Huihui-Qwen3.5-27B-abliterated | 52G | Abliterated 27B (available, not loaded) |
| Huihui-Qwen3-8B-abliterated-v2 | 16G | Coding model — Foundry GPU 3 |
| GLM-4.7-Flash-GPTQ-4bit | 16G | Creative model — Foundry GPU 2 (4090) |
| Qwen3-0.6B | 1.5G | Draft/speculative decoding |
| gte-Qwen2-7B-instruct | 29G | Legacy embedding (unused) |
| comfyui models | 99G | Flux dev FP8, Wan2.x T2V, text encoders, VAE |
