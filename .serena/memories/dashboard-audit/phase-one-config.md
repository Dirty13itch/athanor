# Dashboard Audit Phase 1: Config Complete

**Status:** DONE - config.ts and server-config.ts fully read and documented.

## Key Findings

### Backend Endpoints (config.ts)
- **Foundry (.244)**: 
  - Agent Server: 9000
  - Coordinator: 8000
  - Coder: 8001
  - Speeches (TTS): 8200
- **Workshop (.225)**:
  - Worker: 8002
  - ComfyUI: 8188
  - Open WebUI: 3000
  - EOQ: 3002
- **VAULT (.203)**:
  - LiteLLM: 4000
  - Prometheus: 9090
  - Grafana: 3000
  - Qdrant: 6333
  - Neo4j: 7474
  - Open WebUI: 3090
  - Media stack: Plex, Sonarr, Radarr, Tautulli, Prowlarr, SABnzbd, Stash
- **DEV (.189)**:
  - Embedding: 8003
  - Reranker: 8004

### Credentials Required
- `ATHANOR_LITELLM_API_KEY` (vault:4000)
- `ATHANOR_NEO4J_USER` (vault:7474, default "neo4j")
- `ATHANOR_NEO4J_PASSWORD` (vault:7474)

### Service Registry (27 monitored)
- **Inference** (6): LiteLLM Proxy, Foundry Coordinator, Foundry Coder, Workshop Worker, DEV Embedding, DEV Reranker
- **Observability** (3): Prometheus, Grafana, Loki
- **Media** (9): Plex, Sonarr, Radarr, Tautulli, Prowlarr, SABnzbd, Stash, ComfyUI, Plex Webhook
- **Experience** (4): Neo4j, Qdrant, Speeches, HTTP Cache
- **Platform** (3): Ansible, Logstash, MQTT Broker
- **Knowledge** (1): Knowledge Agent
- **Home** (1): Home Assistant

### GPU Assignments
- **Foundry**: 4×5070 Ti (inference), 4090 (VRAM-heavy)
- **Workshop**: 5090 (creative), 5060 Ti (compute)
- **DEV**: 5060 Ti (embedding, reranking)

## Next Phases
2. **Pages**: Read all 46 page.tsx files to document routes and purposes
3. **Routes**: Read all 120+ API routes to document methods and backend targets
4. **Components**: Read key component files for descriptions
5. **Data Connections**: Map page → backend service relationships
6. **Issues**: Search for TODO/FIXME/HACK comments
7. **Hardcoded Values**: Identify any IP/port hardcoding in components
