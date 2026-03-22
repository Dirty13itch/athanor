# Athanor System Architecture

## Nodes
```
DESK (Win11, .50) ──SSH──> DEV (.189, command center)
                              |
                    +---------+---------+
                    |         |         |
                 VAULT     FOUNDRY   WORKSHOP
                 (.203)    (.244)    (.225)
                 Storage   Compute   Creative
```

## DEV Services (Command Center)
| Port | Service | Purpose |
|------|---------|---------|
| 3001 | UI | Command Center dashboard (Next.js) |
| 3080 | Open WebUI | Uncensored chat interface |
| 4200 | OpenFang | Agent OS, Telegram bridge |
| 6006 | Arize Phoenix | Agent tracing + visualization |
| 7681 | ttyd | Web terminal (Steam Deck) |
| 8001 | Embedding | Qwen3-Embedding-0.6B (Docker) |
| 8003 | Reranker | Qwen3-Reranker-0.6B (Docker) |
| 8060 | Semantic Router | Intent routing |
| 8065 | Sub Burn | Subscription burn scheduler |
| 8700 | Gateway | API hub |
| 8710 | MIND | Interactive reasoning |
| 8720 | Memory | 6-tier memory system |
| 8730 | Perception | Content indexing |
| 8740 | Classifier | Content-aware routing (Qwen3Guard) |
| 8760 | Governor | Task queue + agent dispatch |

## VAULT Services (Storage + Infrastructure)
| Port | Service |
|------|---------|
| 4000 | LiteLLM (38 models, 10+ providers) |
| 5432 | PostgreSQL |
| 5678 | n8n (7 workflows) |
| 6333 | Qdrant (vector DB) |
| 6379 | Redis |
| 7687 | Neo4j (graph DB) |
| 3000 | Grafana |
| 3009 | Uptime Kuma |
| 3030 | Langfuse |
| 8880 | ntfy (notifications) |
| 9090 | Prometheus |
| 9999 | Stash |

## FOUNDRY Services (Heavy Compute)
| Port | Service | GPU | Model |
|------|---------|-----|-------|
| 8000 | vLLM Coordinator | TP=4 (4x5070Ti) | Qwen3.5-27B-FP8 |
| 8006 | vLLM Coder | 4090 | Devstral Small 2 24B AWQ |
| 8200 | speaches TTS | - | - |
| 8250 | Voice Pipeline | - | - |
| 9000 | Agent Server | - | 9 agents, 77 tools |
| 10300 | Wyoming Whisper | CPU | STT |

## WORKSHOP Services (Creative)
| Port | Service | GPU | Model |
|------|---------|-----|-------|
| 8010 | vLLM Worker | 5090 | Qwen3.5-35B-Abliterated-AWQ (sovereign) |
| 8188 | ComfyUI | 5090 | Flux, PuLID, InfiniteYou |
| 11434 | Ollama | 5060Ti | qwen2.5-coder:7b (FIM) |

## Data Flow
```
User -> Open WebUI (:3080) -> LiteLLM (VAULT:4000) -> model endpoint
                                  |
                          Classifier (:8740) decides route:
                          safe -> cloud (Claude/GPT/Gemini)
                          unsafe -> local (abliterated on WORKSHOP)
                          coding -> Devstral (FOUNDRY) or cloud
```

## Subscription Fleet ($508/mo)
| Sub | $/mo | CLI | Capacity |
|-----|------|-----|----------|
| Claude Max | $200 | claude | 1M ctx, Opus 4.6, Agent Teams |
| ChatGPT Pro | $200 | codex | 1M ctx, GPT-5.4, cloud sandbox |
| Copilot Pro+ | $39 | copilot | Unlimited GPT-5 mini, Fleet Mode |
| GLM Z.ai | $30 | litellm | GLM-5-Turbo, agent-optimized |
| Gemini Adv | $20 | gemini | 1M ctx, code review |
| Kimi Code | $19 | kimi | 100-agent swarm |
