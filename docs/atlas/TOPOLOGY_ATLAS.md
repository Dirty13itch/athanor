# Topology Atlas

This atlas maps the live Athanor estate by node, service plane, model route, store, and cross-node flow. It prefers current repo and deployment truth over older planning maps.

## Node Topology

| Node | Role | Primary live surfaces | Core services | Primary truth anchors | Status |
| --- | --- | --- | --- | --- | --- |
| `FOUNDRY` (`.244`) | Heavy inference and agent execution plane | vLLM coordinator, coder model, agent server, Qdrant, GPU orchestration | `vLLM`, `Agent Server`, `Qdrant`, `GPU Orchestrator`, `Speaches`, `wyoming-whisper` | [`../SERVICES.md`](../SERVICES.md), [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), `ansible/`, `services/node1/` | `live` |
| `WORKSHOP` (`.225`) | UI, creative, and worker-inference plane | Dashboard PWA, ws-pty bridge, ComfyUI, EoBQ, worker vLLM | `Dashboard`, `ws-pty`, `ComfyUI`, `EoBQ`, `Open WebUI`, `vLLM` | [`../SERVICES.md`](../SERVICES.md), [`../../projects/dashboard`](../../projects/dashboard), `projects/`, `services/node2/` | `live` |
| `VAULT` (`.203`) | Routing, storage, observability, and domain-services plane | LiteLLM, Neo4j, Redis, Prometheus, Grafana, media stack, Home Assistant | `LiteLLM`, `Neo4j`, `Redis`, `Prometheus`, `Grafana`, `Plex`, `Sonarr`, `Radarr`, `Home Assistant` | [`../SERVICES.md`](../SERVICES.md), [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), `ansible/roles/vault-*` | `live` |
| `DEV` (`.189`) | Development, operations, embedding, and reranking plane | Claude Code, claude-squad, embedding, reranker, runner tooling | `Embedding`, `Reranker`, `Claude Code`, `Gitea Actions Runner` | [`../SERVICES.md`](../SERVICES.md), [`../BUILD-MANIFEST.md`](../BUILD-MANIFEST.md) | `live` |

## Operator Surfaces

| Surface | Role | Source of truth | Status |
| --- | --- | --- | --- |
| Command Center PWA | Primary operator interface for dashboard, tasks, history, monitoring, and agent control | `projects/dashboard`, [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) | `live` |
| Claude Code and claude-squad on `DEV` | Architecture, implementation, build orchestration, and agent direction | [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), [`../BUILD-MANIFEST.md`](../BUILD-MANIFEST.md) | `live` |
| Mobile PWA and remote browser entry | Remote command-center access path | [`../design/command-center.md`](../design/command-center.md), [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) | `live` |

## Service Planes

| Plane | Placement | Responsibilities | Status |
| --- | --- | --- | --- |
| Inference plane | `FOUNDRY`, `WORKSHOP`, `DEV`, routed through `VAULT` | local reasoning, worker, creative, embedding, and reranking paths under LiteLLM aliases | `live` |
| Interface plane | `WORKSHOP` | dashboard PWA, terminal bridge, ComfyUI, EoBQ, Open WebUI | `live` |
| Orchestration plane | `FOUNDRY` | agent server, task engine, scheduler, workspace, goals, subscriptions, outputs | `live` |
| Knowledge plane | `FOUNDRY`, `VAULT`, `DEV` | Qdrant collections, Neo4j graph, indexing, retrieval, preference storage | `live` |
| Observability plane | `VAULT` plus exporters on compute nodes | Prometheus, Grafana, Loki, Alloy, service history, GPU history | `live` |
| Domain-service plane | `VAULT` | media stack, Home Assistant, field apps, auxiliary apps | `live` |

## Model Route Map

| Alias / Route | Backend | Placement | Primary use | Status |
| --- | --- | --- | --- | --- |
| `reasoning` | Qwen3.5-27B-FP8 | `FOUNDRY:8000` via LiteLLM | agent reasoning, high-value orchestration | `live` |
| `coding` | Qwen3.5-27B-FP8 | `FOUNDRY:8000` via LiteLLM | coordinator lane with coding-oriented prompt posture | `live` |
| `coder` | Qwen3.5-35B-A3B-AWQ-4bit | `FOUNDRY:8006` via LiteLLM | dedicated coding and tool-use lane | `live` |
| `creative` | Qwen3.5-35B-A3B-AWQ | `WORKSHOP:8000` via LiteLLM | creative-adjacent and broad local utility jobs | `live` |
| `utility` | Qwen3.5-35B-A3B-AWQ | `WORKSHOP:8000` via LiteLLM | local utility lane for non-premium workloads | `live` |
| `fast` | Qwen3.5-35B-A3B-AWQ | `WORKSHOP:8000` via LiteLLM | worker inference and fast interactive model lane | `live` |
| `worker` | Qwen3.5-35B-A3B-AWQ | `WORKSHOP:8000` via LiteLLM | delegated work and batch tasks | `live` |
| `uncensored` | Qwen3.5-35B-A3B-AWQ | `WORKSHOP:8000` via LiteLLM | local alternate-content lane | `live` |
| `embedding` | Qwen3-Embedding-0.6B | `DEV:8001` via LiteLLM | vectorization and retrieval | `live` |
| `reranker` | Qwen3-Reranker-0.6B | `DEV:8003` via LiteLLM | reranking and retrieval quality | `live` |
| `claude`, `gpt`, `gemini`, `deepseek` | cloud provider routes | `VAULT` LiteLLM proxy to external APIs | overflow, premium reasoning, and provider-specific workflows | `live` |

## Core Stores and Shared State

| Store | Placement | Main responsibilities | Status |
| --- | --- | --- | --- |
| Qdrant (canonical runtime collections) | `FOUNDRY` | knowledge, personal data, activity, conversations, preferences, events | `live` |
| Neo4j | `VAULT` | graph memory, infrastructure graph, semantic relationships | `live` |
| Redis | `VAULT` | task queue, workspace broadcast, scheduler, ephemeral control state | `live` |
| Prometheus | `VAULT` | infrastructure metrics, service history, GPU telemetry | `live` |
| Grafana / Loki / Alloy | `VAULT` plus node agents | observability visualization and log pipeline | `live` |
| Dashboard local storage | browser runtime | chat sessions, agent threads, prompt history, UI preferences | `live` |

## Cross-node Flows

| Flow | Path | Primary source anchors | Status |
| --- | --- | --- | --- |
| Operator chat to model | Dashboard -> Next.js API -> Agent Server or model backend -> LiteLLM -> vLLM/cloud -> streamed response back | [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), `projects/dashboard/src/app/api/chat/route.ts`, `projects/agents/src/athanor_agents/server.py` | `live` |
| Background task execution | UI or Claude -> `/v1/tasks` -> Redis-backed worker -> agent execution -> outputs / notifications / workspace broadcast | [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), `projects/agents/src/athanor_agents/tasks.py`, `server.py` | `live` |
| Knowledge indexing and retrieval | docs or events -> embedding -> Qdrant / Neo4j -> dashboard or agents retrieve via APIs | [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md), [`../design/personal-data-architecture.md`](../design/personal-data-architecture.md) | `live` |
| Creative generation | Dashboard gallery/media -> ComfyUI APIs -> output history -> gallery snapshots and previews | `projects/dashboard/src/app/api/comfyui/*`, `projects/dashboard/src/features/gallery/*` | `live` |
| Monitoring drill-down | Dashboard -> dashboard-owned monitoring APIs -> Prometheus -> Grafana deep links | `projects/dashboard/src/app/api/monitoring/route.ts`, [`../SERVICES.md`](../SERVICES.md) | `live` |

## Deployment Truth and Drift Boundaries

| Layer | Current role | When it is authoritative | Current atlas reading |
| --- | --- | --- | --- |
| `ansible/` | desired deployment baseline | infrastructure shape, service defaults, host intent, canonical deployment model | authoritative baseline, but not every live app-layer manifest is fully converged |
| `services/` | node-scoped service manifests | service stacks that already match live node behavior better than some Ansible roles | authoritative for parts of `FOUNDRY` and `WORKSHOP` service layout |
| `projects/` | project-local compose truth | app-local deployment surfaces such as dashboard and agents when the project folder is the real owner | authoritative for several app surfaces on `WORKSHOP` |
| live node manifests | actual runtime evidence | tie-breaker for what is running now when repo layers disagree | evidence, not long-term canonical source |

## Current Drift Notes

- `VAULT` LiteLLM routing has been promoted into repo-backed templates, but the live rollout still needs verification against the regenerated config.
- `VAULT` Prometheus and alerting still carry legacy-shaped monitoring assumptions relative to the current Athanor model.
- `FOUNDRY` and `WORKSHOP` are structurally aligned with Athanor, but some app-layer manifests match `services/` or `projects/` better than current Ansible templates.
- The atlas therefore treats topology truth as a reconciled stack: runtime evidence tells you what is active, while repo manifests tell you what should survive.
