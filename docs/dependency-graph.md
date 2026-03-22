# Athanor Service Dependency Graph

## Critical Path (if these die, everything stops)
```
LiteLLM (VAULT:4000) -- ALL model routing depends on this
  |
  +-- Gateway (DEV:8700) depends on LiteLLM
  +-- MIND (DEV:8710) depends on LiteLLM
  +-- Memory (DEV:8720) depends on Qdrant + LiteLLM
  +-- Agent Server (FOUNDRY:9000) depends on LiteLLM + Qdrant + Neo4j
  +-- OpenFang (DEV:4200) depends on LiteLLM
  +-- All CLI tools depend on LiteLLM for local model routing
```

## DEV Services
```
UI (DEV:3001) -- standalone (Next.js)
Gateway (DEV:8700) -> LiteLLM, Memory
MIND (DEV:8710) -> LiteLLM, Memory, Gateway
Memory (DEV:8720) -> Qdrant (VAULT:6333), Neo4j (VAULT:7687)
Perception (DEV:8730) -> Memory
Semantic Router (DEV:8060) -> Gateway
OpenFang (DEV:4200) -> LiteLLM
Subscription Burn (DEV:8065) -> standalone
Open WebUI (DEV:3080) -> LiteLLM
Classifier (DEV:8740) -> standalone (CPU model)
Governor (DEV:8760) -> standalone (dispatches to CLI tools)
Arize Phoenix (DEV:6006) -> standalone
Embedding (DEV:8001) -> standalone (Docker, GPU)
Reranker (DEV:8003) -> standalone (Docker, GPU)
```

## VAULT Services
```
LiteLLM (VAULT:4000) -> vLLM endpoints, cloud APIs
Qdrant (VAULT:6333) -> standalone
Neo4j (VAULT:7687) -> standalone
PostgreSQL (VAULT:5432) -> standalone
Redis (VAULT:6379) -> standalone
Prometheus (VAULT:9090) -> scrapes all nodes
Grafana (VAULT:3000) -> Prometheus
Langfuse (VAULT:3030) -> PostgreSQL
ntfy (VAULT:8880) -> standalone
n8n (VAULT:5678) -> standalone
Uptime Kuma (VAULT:3009) -> standalone
Stash (VAULT:9999) -> standalone (PostgreSQL)
```

## FOUNDRY Services
```
vLLM Coordinator (FOUNDRY:8000) -> standalone (TP=4 GPUs 0,1,3,4)
vLLM Coder (FOUNDRY:8006) -> standalone (GPU 2 = 4090)
Agent Server (FOUNDRY:9000) -> LiteLLM, Qdrant, Neo4j
Voice Pipeline (FOUNDRY:8250) -> Agent Server
```

## WORKSHOP Services
```
vLLM Worker (WORKSHOP:8010) -> standalone (GPU 0 = 5090)
Ollama (WORKSHOP:11434) -> standalone (GPU 1 = 5060 Ti)
ComfyUI (WORKSHOP:8188) -> standalone (GPU 0 = 5090, timeshared with vLLM)
```

## SPOF Analysis
- LiteLLM down = all model routing fails (mitigate: local vLLM direct fallback)
- VAULT down = databases + monitoring gone (mitigate: offsite backup)
- FOUNDRY down = no coordinator model, no agent server (mitigate: WORKSHOP models as fallback)
