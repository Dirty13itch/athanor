# Athanor Services Map

*Live service inventory. Updated when services change.*

Last updated: 2026-03-14 (Session 56 — added backup-exporter, ulrich-energy-website, blackbox-exporter to VAULT)

## Node 1 â€” Foundry (192.168.1.244)

| Service | Port | Details |
|---------|------|---------|
| vLLM Coordinator (Qwen3.5-27B-FP8) | 8000 | TP=4 across GPUs 0,1,3,4 (4x RTX 5070 Ti), `--tool-call-parser qwen3_xml`, `--enforce-eager`, `--language-model-only` |
| vLLM Coder (Qwen3-Coder-30B-A3B-Instruct-AWQ) | 8006 | GPU 2 (RTX 4090), dedicated coding and tool-heavy lane |
| Agent Server | 9000 | 9 agents + GWT workspace + escalation + activity/preferences + routing + diagnosis + semantic cache + circuit breakers + self-improvement + preference learning APIs |
| Qdrant | 6333/6334 | Vector DB: knowledge (2484), personal_data (2304), conversations, activity, preferences (55), implicit_feedback, events |
| GPU Orchestrator | 9200 | 4 zones, DCGM metrics, vLLM sleep/wake, TTL auto-sleep, Prometheus export |
| wyoming-whisper | 10300 | STT for HA â€” faster-distil-whisper-large-v3 (float16), GPU 4 |
| Speaches | 8200 | OpenAI-compatible STT+TTS API â€” Kokoro + faster-whisper, GPU 4 |
| Grafana Alloy | â€” | Log/metric forwarding |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## Node 2 â€” Workshop (192.168.1.225)

| Service | Port | Details |
|---------|------|---------|
| vLLM (Qwen3.5-35B-A3B-AWQ-4bit) | 8000 | RTX 5090, vLLM nightly, `--tool-call-parser qwen3_xml`, `--kv-cache-dtype auto` |
| Dashboard | 3001 | Next.js 16, PWA, 5 lens modes, SSE real-time, 17+ pages |
| ws-pty Bridge | 3100 | WebSocket terminal bridge (node-pty + ws sidecar) |
| ComfyUI | 8188 | Flux dev FP8 + Wan2.x T2V, RTX 5060 Ti, WanVideoWrapper + KJNodes |
| EoBQ | 3002 | Empire of Broken Queens â€” Next.js game app |
| Open WebUI | 3000 | Chat interface (Workshop-local, routes to Node 1 vLLM) |
| Grafana Alloy | â€” | Log/metric forwarding |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## VAULT (192.168.1.203)

### Core Services

| Service | Port | Details |
|---------|------|---------|
| LiteLLM Proxy | 4000 | Routed local + cloud inference: reasoning, coding, coder, creative, utility, fast, worker, uncensored, embedding, reranker, Anthropic, OpenAI, Google, DeepSeek, Moonshot, Z.ai, OpenRouter. LangFuse callbacks. Auth is env-backed. |
| Neo4j | 7474/7687 | Graph DB (3095 nodes, 4447 rels), auth is env-backed. |
| Redis | 6379 | GWT workspace + GPU orchestrator state + scheduler |
| Qdrant | 6333/6334 | VAULT-side vector DB instance |
| Postgres | 5432 | Shared PostgreSQL |
| Meilisearch | 7700 | Search engine |

### Observability

| Service | Port | Details |
|---------|------|---------|
| LangFuse Web | 3030 | v3.155.1, observability + tracing for LiteLLM |
| LangFuse Worker | â€” | Background job processor |
| LangFuse Postgres | â€” | LangFuse-dedicated PostgreSQL 16 |
| LangFuse ClickHouse | â€” | LangFuse metrics store |
| LangFuse Redis | â€” | LangFuse cache |
| LangFuse MinIO | â€” | LangFuse blob storage |
| Prometheus | 9090 | Metrics aggregation |
| Grafana | 3000 | Admin credentials are managed outside tracked docs. |
| Grafana Alloy | â€” | Log collection agent |
| Loki | â€” | Log aggregation |
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
| wyoming-piper | 10200 | TTS for HA â€” en_US-lessac-medium, CPU-only |
| wyoming-openwakeword | 10400 | Wake word detection for HA, CPU-only |

### Applications

| Service | Port | Details |
|---------|------|---------|
| Gitea | 3033 | Self-hosted git + CI/CD (SQLite, Actions enabled, admin credentials managed outside tracked docs) |
| Miniflux | 8070 | RSS reader (17 feeds, 6 categories, dedicated PostgreSQL, admin credentials managed outside tracked docs) |
| n8n | 5678 | Workflow automation â€” Miniflux RSS â†’ LLM classification â†’ Qdrant signals pipeline |
| Open WebUI (VAULT) | 3090 | Chat interface (routes through LiteLLM) |
| Spiderfoot | 5001 | OSINT tool |
| ntfy | 8880 | Push notification server |
| Field Inspect App | 3080 | Field inspection PWA (dedicated Postgres :5433, MinIO :9000-9001) |
| Ulrich Energy Website | 8088 | Ulrich Energy business site |
| backup-exporter | 9199 | Prometheus exporter for backup job status |
| blackbox-exporter | 9115 | Prometheus blackbox exporter for endpoint probing |

## DEV (192.168.1.189)

| Service | Port | Details |
|---------|------|---------|
| Claude Code | â€” | Primary development tool (native install, auto-updates) |
| claude-squad | â€” | Multi-session Claude Code manager (git worktrees, parallel sessions) |
| Embedding (Qwen3-Embedding-0.6B) | 8001 | vLLM embedding model on RTX 5060 Ti |
| Reranker | 8003 | Reranker model on RTX 5060 Ti |
| Gitea Actions Runner | â€” | act_runner v0.2.11 (systemd service, self-hosted label) |

## LiteLLM Model Routes

| Route | Backend | Model | Node |
|-------|---------|-------|------|
| `reasoning` / `gpt-4` | vLLM | Qwen3.5-27B-FP8 | Foundry :8000 (TP=4) |
| `coding` | vLLM | Qwen3.5-27B-FP8 | Foundry :8000 (same coordinator lane, coding-oriented alias) |
| `coder` | vLLM | Qwen3-Coder-30B-A3B-Instruct-AWQ | Foundry :8006 |
| `creative` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `utility` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `fast` / `gpt-3.5-turbo` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `worker` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `uncensored` | vLLM | Qwen3.5-35B-A3B-AWQ-4bit | Workshop :8000 |
| `embedding` / `text-embedding-ada-002` | vLLM | Qwen3-Embedding-0.6B | DEV :8001 |
| `reranker` | vLLM | Reranker model | DEV :8003 |
| `claude` | Anthropic API | Claude | Cloud |
| `gpt` | OpenAI API | GPT | Cloud |
| `deepseek` | DeepSeek API | DeepSeek | Cloud |
| `gemini` | Google API | Gemini | Cloud |
| `kimi` | Moonshot API | Kimi | Cloud |
| `glm` | Z.ai API | GLM | Cloud |
| `openrouter` | OpenRouter API | OpenRouter | Cloud |

## Models Available to Inference Nodes (`/mnt/vault/models/` or `/mnt/local-fast/models/`)

| Model | Size | Purpose |
|-------|------|---------|
| Qwen3.5-27B-FP8 | ~29G | Coordinator (LiteLLM: `reasoning`, `coding`) - Foundry TP=4 |
| Qwen3.5-35B-A3B-AWQ-4bit | ~22G | Worker lane (LiteLLM: `fast`, `worker`, `creative`, `utility`, `uncensored`) - Workshop |
| Qwen3-Coder-30B-A3B-Instruct-AWQ | ~16G | Coder lane (LiteLLM: `coder`) - Foundry GPU 2 (4090) |
| Qwen3-32B-AWQ | 19G | Previous reasoning model (replaced by Qwen3.5-27B-FP8) |
| GLM-4.7-Flash-GPTQ-4bit | 16G | Previous local creative candidate (not currently loaded) |
| Huihui-Qwen3.5-27B-abliterated | 52G | Abliterated 27B (available, not loaded) |
| Qwen3-0.6B | 1.5G | Draft/speculative decoding |
| gte-Qwen2-7B-instruct | 29G | Legacy embedding (unused) |
| comfyui models | 99G | Flux dev FP8, Wan2.x T2V, text encoders, VAE |

