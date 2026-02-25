# Athanor Services Map

*Live service inventory. Updated when services change.*

Last updated: 2026-02-24 (Session 11)

## Node 1 — Foundry (192.168.1.244)

| Service | Port | Details |
|---------|------|---------|
| vLLM (Qwen3-32B-AWQ) | 8000 | TP=4 across 3x RTX 5070 Ti + RTX 4090, `--quantization awq` |
| vLLM Embedding (Qwen3-Embedding-0.6B) | 8001 | RTX 5070 Ti GPU 4, 1024-dim embeddings |
| Agent Server | 9000 | 5 agents: general, media, research, creative, knowledge |
| Qdrant | 6333/6334 | Vector DB, collections: knowledge (922 pts), conversations |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## Node 2 — Workshop (192.168.1.225)

| Service | Port | Details |
|---------|------|---------|
| vLLM (Qwen3-14B) | 8000 | RTX 5090, enforce-eager mode |
| Dashboard | 3001 | Next.js 16, dark theme |
| ComfyUI | 8188 | Flux dev FP8, RTX 5060 Ti |
| Open WebUI | 3000 | Chat interface |
| node_exporter | 9100 | Prometheus metrics |
| dcgm-exporter | 9400 | GPU metrics |

## VAULT (192.168.1.203)

| Service | Port | Details |
|---------|------|---------|
| LiteLLM Proxy | 4000 | Routes: reasoning/fast/embedding. Auth: `sk-athanor-litellm-2026` |
| Neo4j | 7474/7687 | Graph DB, auth: neo4j/athanor2026 |
| Prometheus | 9090 | 5 scrape targets UP |
| Grafana | 3000 | admin/newpass123, Prometheus + Node Exporter + DCGM dashboards |
| Plex | 32400 | Claimed, libraries added |
| Sonarr | 8989 | Needs Prowlarr indexer config |
| Radarr | 7878 | Needs Prowlarr indexer config |
| Prowlarr | 9696 | Needs indexers added |
| SABnzbd | 8080 | Needs Usenet provider config |
| Tautulli | 8181 | Running |
| Stash | 9999 | Running |
| Home Assistant | 8123 | Needs onboarding in browser |

## Models on NFS (`/mnt/vault/models/`)

| Model | Size | Purpose |
|-------|------|---------|
| Qwen3-32B-AWQ | 18G | Reasoning (LiteLLM alias: `reasoning`) |
| Qwen3-14B | 28G | Fast inference (alias: `fast`) |
| Qwen3-0.6B | 1.5G | Draft/speculative decoding |
| Qwen3-Embedding-0.6B | 1.2G | Embeddings (alias: `embedding`) |
| gte-Qwen2-7B-instruct | 14G | Legacy embedding (unused) |
| Flux dev FP8 | 17G | Image generation (ComfyUI) |
