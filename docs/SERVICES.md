# Athanor Services Map

Source of truth: `config/automation-backbone/platform-topology.json`, `docs/projects/PORTFOLIO-REGISTRY.md`
Validated against registry version: `platform-topology.json@2026-03-27.1`, `project-maturity-registry.json@2026-03-27.1`
Mutable facts policy: service ids, nodes, ports, auth classes, and health paths belong to `platform-topology.json`. This document is the operator-facing map for the current validated registry snapshot and should be rewritten when topology changes.

---

## How To Read This Map

- If a service is listed here, it is in the topology registry and is part of current live truth.
- If a service is not listed here, it is not part of the canonical live map, even if a historical doc or host still references it.
- Use the topology registry for exact URLs and env overrides.
- Use this document to understand service role, operator expectations, and which surfaces are core versus supporting.

## Auth Classes

| Auth class | Meaning |
|------------|---------|
| `admin` | Privileged control-plane service. Mutations must fail closed. |
| `operator` | Human/operator-facing or guarded product surface. |
| `internal_only` | Backend-only dependency. Not for unauthenticated browser or LAN mutation. |

## Runtime Classes

| Runtime class | Meaning |
|---------------|---------|
| `control_plane` | Coordination, policy, observability, or privileged orchestration surface |
| `data_plane` | Inference, state, routing, or backend data dependency |
| `product_app` | User/operator-facing application surface |
| `scaffold` | Intentionally incomplete surface with limited obligations |

## Registry-Managed Services

### Control Plane

| Service id | Node | Auth | Health | Role |
|------------|------|------|--------|------|
| `gateway` | `dev` | `internal_only` | `/health` | Local gateway/control helper on the ops host |
| `quality_gate` | `dev` | `admin` | `/health` | Quality and cleanup gate for curated data/control flows |
| `semantic_router` | `dev` | `internal_only` | `/health` | Routing helper for intent or semantic dispatch |
| `agent_server` | `foundry` | `admin` | `/health` | Main agent runtime, task API, workspace, subscriptions, and backbone read models |
| `gpu_orchestrator` | `foundry` | `admin` | `/health` | GPU placement and runtime power/lease control |
| `grafana` | `vault` | `operator` | `/api/health` | Metrics and dashboards |
| `langfuse` | `vault` | `operator` | `/api/public/health` | Observability and tracing surface |
| `ntfy` | `vault` | `operator` | none | Push notification service |
| `ntfy_topic` | `vault` | `operator` | none | Topic endpoint used by notification flows |
| `prometheus` | `vault` | `operator` | `/-/healthy` | Metrics aggregation |
| `uptime_kuma` | `vault` | `operator` | none | Availability checks and endpoint monitoring |
| `ws_pty_bridge` | `workshop` | `admin` | `/health` | Privileged terminal bridge with signed-ticket access |

### Data Plane

| Service id | Node | Auth | Health | Role |
|------------|------|------|--------|------|
| `embedding` | `dev` | `internal_only` | `/health` | Embedding service |
| `memory` | `dev` | `internal_only` | `/health` | Memory/data helper on the ops host |
| `reranker` | `dev` | `internal_only` | `/health` | Reranker service |
| `vllm_coder` | `foundry` | `internal_only` | `/health` | Dedicated coder inference lane |
| `vllm_coordinator` | `foundry` | `internal_only` | `/health` | Main reasoning/coordinator inference lane |
| `litellm` | `vault` | `internal_only` | `/health` | Central routed inference proxy |
| `neo4j` | `vault` | `internal_only` | none | Bolt graph endpoint |
| `neo4j_http` | `vault` | `internal_only` | `/` | HTTP graph endpoint |
| `qdrant` | `vault` | `internal_only` | `/collections` | Vector store |
| `redis` | `vault` | `internal_only` | TCP connect | Shared volatile/durable runtime state for this cycle |
| `ollama_workshop` | `workshop` | `internal_only` | `/api/tags` | Workshop-local model runtime |
| `scorer` | `workshop` | `internal_only` | `/health` | Scoring/evaluation helper |
| `vllm_vision` | `workshop` | `internal_only` | `/health` | Vision lane |
| `vllm_worker` | `workshop` | `internal_only` | `/health` | Worker/utility inference lane |

### Product Apps

| Service id | Node | Auth | Health | Role |
|------------|------|------|--------|------|
| `dashboard` | `dev` | `operator` | `/api/overview` | Main authenticated operator console |
| `speaches` | `foundry` | `operator` | none | Speech/STT/TTS surface |
| `miniflux` | `vault` | `operator` | `/healthcheck` | RSS and signal intake product surface |
| `stash` | `vault` | `operator` | none | Adult-content management surface |
| `comfyui` | `workshop` | `operator` | `/system_stats` | Image/video generation surface |

### Scaffolds

| Service id | Node | Auth | Health | Role |
|------------|------|------|--------|------|
| `openfang` | `dev` | `operator` | `/api/health` | Incubating/operator-adjacent scaffold |
| `subscription_burn` | `dev` | `internal_only` | `/health` | Subscription and quota scaffold |
| `n8n` | `vault` | `operator` | none | Workflow automation scaffold |

## Core-First Surfaces

The following services sit directly on the current `platform-core` or `production-product` path and should be treated as highest-priority runtime truth:

- `agent_server`
- `gpu_orchestrator`
- `ws_pty_bridge`
- `dashboard`
- `quality_gate`
- `redis`
- `qdrant`
- `neo4j` / `neo4j_http`
- `litellm`

If one of these drifts, the repo contract or operator surface drifts with it.

## Reference-Only / Historical Names

Historical docs and scripts may still mention services that are not in the current topology registry. Those names are reference-only until re-registered. Common examples:

- `mind`
- `perception`
- `classifier`
- `provider_bridge`
- `ui`
- `open-webui`
- `whisparr`
- `seerr`
- `vaultwarden`
- `headscale`
- `arize-phoenix`

Do not treat those names as part of current canonical service truth unless they are added back to `platform-topology.json`.
