# Athanor System Audit

> **Status:** Archive audit reference only.
> **Current adopted-system truth lives here:** `python scripts/session_restart_brief.py --refresh`, `STATUS.md`, `docs/SERVICES.md`, `docs/SYSTEM-SPEC.md`, and generated reports under `docs/operations/`.
> **Boundary:** this audit records a historical repo-backed drift assessment; it is not live topology, deployment, or queue authority.

Date: March 9, 2026

## Scope

This is a repo-backed audit of the Athanor system as defined by:

- `ansible/` deployment roles, defaults, templates, inventory, and host vars
- `projects/` application source for dashboard, agents, and EoBQ
- `services/` checked-in Docker Compose snapshots
- top-level system documentation such as `README.md`, `STATUS.md`, `docs/SYSTEM-SPEC.md`, and `docs/SERVICES.md`

This is not a live SSH or runtime Docker inspection of FOUNDRY, WORKSHOP, VAULT, or DEV. It documents the intended architecture, the current repo-declared architecture, and the places where those disagree.

## Executive Summary

Athanor already has a coherent target architecture:

- Ansible is supposed to be the deployment control plane.
- LiteLLM on VAULT is supposed to be the central inference routing layer.
- vLLM instances on FOUNDRY, WORKSHOP, and the embedding host are supposed to sit behind LiteLLM aliases.
- The dashboard on WORKSHOP is supposed to be the operator command center.
- The agent server on FOUNDRY is supposed to be the action/orchestration layer.
- Qdrant, Redis, and Neo4j are supposed to provide shared state, memory, and coordination.
- Prometheus, Grafana, Loki, and Alloy are supposed to be the observability plane.

That model is good. The main problem is not the architecture itself. The main problem is architectural drift.

The repo currently has multiple competing truths for where services run, what model aliases mean, and which endpoints other components should use. Some newer paths are correctly moving toward a centralized, contract-driven system, but older code, snapshot Compose files, and stale docs still bypass those contracts with hardcoded node IPs, model names, and even credentials.

## Canonical Operating Model

### Source of Truth Order

The system should be treated as having this source-of-truth order:

1. `ansible/` for deployment topology, ports, container env, and node placement
2. `projects/` for application behavior and integration logic
3. `docs/` for system intent and human-readable architecture
4. `services/` only as generated or manually refreshed snapshots, never as authoritative deployment configuration

If a change is made in `services/` without an Ansible change, it should be treated as documentation or snapshot drift, not a real architecture change.

### Node Roles

#### FOUNDRY (`192.168.1.244`)

- Heavy inference node
- Agent server
- Qdrant
- GPU orchestrator
- voice services in current documentation set
- currently also still hosts the embedding deployment in Ansible

#### WORKSHOP (`192.168.1.225`)

- Primary UI node
- Dashboard / command center
- Open WebUI (raw/direct model chat)
- EoBQ
- ComfyUI
- worker inference runtime

#### VAULT (`192.168.1.203`)

- Central routing and shared services
- LiteLLM
- Redis
- Neo4j
- Prometheus / Grafana / Loki / Alloy
- media stack
- Home Assistant
- automation and knowledge-adjacent services
- secondary Open WebUI that routes through LiteLLM

#### DEV (`192.168.1.189`)

- development and ops workstation
- Ansible control path
- Claude Code workspace
- documented home for embedding and reranker in several newer docs

## How The System Should Work Together

### 1. Deployment Plane

- Ansible should deploy every durable runtime to the correct node.
- `ansible/playbooks/site.yml` should be the operational map for what lands on FOUNDRY, WORKSHOP, and VAULT.
- `services/` should only exist as generated snapshots or examples. They should not be consulted to determine the live architecture.

### 2. Inference Plane

- LiteLLM on VAULT should be the single inference entry point for applications and agents.
- Applications should use aliases such as `reasoning`, `fast`, `creative`, `worker`, `embedding`, and `reranker`.
- Direct vLLM URLs should only be used for health checks, runtime-specific observability, or exceptional low-level maintenance tasks.
- Model placement can change behind aliases without requiring application code changes.

### 3. Operator Plane

- The dashboard on WORKSHOP should be the main operator console.
- The dashboard should talk to dashboard-owned API routes.
- Those API routes should normalize data from Prometheus, the agent server, LiteLLM, and a controlled set of direct health endpoints.
- The UI should not embed node placement assumptions or raw credentials.

### 4. Agent Plane

- The agent server on FOUNDRY should receive user and dashboard requests.
- The agent server should route all LLM work through LiteLLM aliases.
- Agents should use Redis for workspace/state coordination, Qdrant for memory and activity retrieval, and Neo4j where graph queries are needed.
- Agents should call media, home, and system tools through configured endpoints, not inline host-specific literals.

### 5. Knowledge And State Plane

- Qdrant on FOUNDRY should serve vector search, activity, preferences, conversations, and other retrieval-backed agent data.
- Redis on VAULT should back shared workspace state, alert deduplication, and GPU orchestrator coordination.
- Neo4j on VAULT should back graph-oriented system and knowledge queries.
- Anything requiring embeddings should go through the `embedding` route, not by guessing the current embedding host.

### 6. Creative Plane

- EoBQ on WORKSHOP should use LiteLLM for dialogue, ComfyUI for image generation, and Qdrant for memory/retrieval.
- ComfyUI should remain a specialized runtime, not a general orchestration surface.

### 7. Media And Home Plane

- Agents, dashboard pages, and media/home UIs should consume these services as integrations, not as independent control planes.
- Media and home endpoints should be centrally configured.
- The dashboard should surface health and operator shortcuts; the agent server should handle reasoning and automation.

### 8. Observability Plane

- Prometheus on VAULT should scrape node exporters, DCGM exporters, and blackbox probe targets.
- The dashboard should use Prometheus as the canonical source for service history and GPU history.
- Grafana is the deep-dive observability surface; the dashboard is the operator summary/control surface.

## Current Repo Reality

### Deployment Topology In Ansible

The deployment intent is mostly clear in `ansible/playbooks/site.yml`:

- FOUNDRY gets monitoring exporters, `vllm`, `vllm-embedding`, `agents`, and `gpu-orchestrator`.
- WORKSHOP gets monitoring exporters, `vllm`, `comfyui`, `open-webui`, `dashboard`, and `eoq`.
- VAULT gets the storage/media/monitoring/routing roles, including LiteLLM and the VAULT Open WebUI.

### Dashboard Runtime Model

The dashboard has moved in the right direction:

- it exposes dashboard-owned APIs for overview, services, GPU telemetry, models, agents, and chat
- it uses Prometheus range queries for service and GPU history
- it has a more formal operator-console shell

But the repo also still contains older dashboard routes and feature areas that bypass the new config/data model and talk directly to node IPs and backend services.

### Agent Runtime Model

The agent server also has the right intended direction:

- `projects/agents/src/athanor_agents/config.py` makes LiteLLM the primary inference entry point
- the server exposes an OpenAI-compatible surface
- agent memory and activity features are wired around Qdrant and Redis

But several tools still bypass config and embed infra details directly.

## Findings

### F1. Ansible, docs, and `services/` snapshots disagree about the live system

Severity: High

This is the largest source of confusion in the repo.

Examples:

- `services/node2/dashboard/docker-compose.yml` only sets `NEXT_PUBLIC_PROMETHEUS_URL`, while the real deployment template in `ansible/roles/dashboard/templates/docker-compose.yml.j2` now passes the full dashboard env set.
- `services/node1/agents/docker-compose.yml` still shows the older direct `ATHANOR_VLLM_BASE_URL` pattern and inline API keys, while the current Ansible template routes the app through LiteLLM and includes more shared services.
- `services/node1/vllm/docker-compose.yml` is a handwritten phase-specific runtime snapshot and does not match the current generalized Ansible `vllm` role.

Impact:

- operators can look at the wrong file and infer the wrong topology
- contributors can patch the wrong deployment path
- service placement and env contract changes can appear "done" in one layer while remaining stale elsewhere

Recommendation:

- declare `ansible/` authoritative in writing
- mark `services/` as snapshots only
- either generate `services/` from Ansible or add a top-level warning that they are not source-of-truth

### F2. The embedding service location is unresolved across the stack

Severity: High

There is a direct contradiction between documentation, application config, and Ansible deployment.

Evidence:

- `docs/SYSTEM-SPEC.md`, `docs/SERVICES.md`, and `STATUS.md` describe embedding on DEV at `:8001`
- `ansible/playbooks/site.yml` still deploys `vllm-embedding` with the FOUNDRY role set
- `ansible/roles/vllm-embedding/defaults/main.yml` defines the deploy directory and port for the embedding service under the compute-node deployment model
- `ansible/roles/agents/defaults/main.yml` points `agent_vllm_embedding_url` at FOUNDRY (`192.168.1.244:8001/v1`)
- `projects/agents/src/athanor_agents/config.py` points `vllm_embedding_url` at DEV (`192.168.1.189:8001/v1`)
- `ansible/roles/gpu-orchestrator/defaults/main.yml` points the embedding endpoint at FOUNDRY
- `projects/dashboard/src/lib/config.ts` still exposes the embedding health endpoint on FOUNDRY

Impact:

- embedding-dependent features can silently point at different hosts depending on which code path is used
- retrieval, reranking, and health surfaces may all report different realities
- any migration of embedding off FOUNDRY is incomplete and therefore operationally risky

Recommendation:

- make one explicit decision: embedding lives on DEV or FOUNDRY
- update LiteLLM, Ansible, agent config, GPU orchestrator defaults, dashboard config, and docs in the same change
- after that, ban direct embedding host literals outside centralized config

### F3. LiteLLM alias semantics and dashboard model metadata have drifted

Severity: High

The route alias layer is supposed to decouple apps from model placement, but the alias meaning is not consistent across docs and UI metadata.

Evidence:

- `ansible/roles/vault-litellm/templates/litellm_config.yaml.j2` currently maps:
  - `reasoning` to FOUNDRY `:8000`
  - `utility` and `fast` to FOUNDRY `:8002`
  - `creative` and `worker` to WORKSHOP `:8000`
  - `embedding` and `reranker` to the embedding host
- `docs/SERVICES.md` describes:
  - `creative` as the FOUNDRY Huihui utility model
  - `fast` as the WORKSHOP worker model
- `projects/dashboard/src/lib/config.ts` still labels the inference backends as `Foundry / Qwen3-32B` and `Workshop / Qwen3-14B`, which does not match newer docs or the current LiteLLM route map

Impact:

- the dashboard can describe the cluster inaccurately
- operators can make bad routing assumptions
- agent/app developers lose confidence that aliases are stable contracts

Recommendation:

- pick one canonical alias taxonomy and publish it
- have the dashboard derive model metadata from a normalized API rather than embedding old marketing labels in config
- treat alias meaning changes as interface changes, not informal infra tweaks

### F4. Centralized config is incomplete; many services still bypass it with hardcoded IPs and credentials

Severity: Critical

The system is only partially contract-driven today. Several code paths still hardcode node IPs, ports, and secrets directly in app code.

Evidence in agents:

- `projects/agents/src/athanor_agents/tools/system.py` hardcodes service URLs for LiteLLM, coordinator, worker, embedding, dashboard, media services, Home Assistant, Neo4j, LangFuse, and GPU orchestrator
- `projects/agents/src/athanor_agents/tools/data_curator.py` hardcodes Qdrant
- `projects/agents/src/athanor_agents/tools/knowledge.py` hardcodes Qdrant, Neo4j URL, and Neo4j credentials
- `projects/agents/src/athanor_agents/tools/research.py` also hardcodes Neo4j auth
- `projects/agents/src/athanor_agents/config.py` carries a Redis password in the default URL

Evidence in dashboard:

- `projects/dashboard/src/app/api/personal-data/stats/route.ts` hardcodes Qdrant and Neo4j URLs plus Neo4j credentials
- `projects/dashboard/src/app/api/personal-data/search/route.ts` hardcodes Qdrant
- `projects/dashboard/src/app/home/page.tsx`, `src/app/media/page.tsx`, and `src/app/monitoring/page.tsx` still embed direct VAULT, FOUNDRY, and WORKSHOP URLs
- several dashboard routes outside the new command-center core still bypass `src/lib/config.ts`

Evidence in Compose/defaults:

- `projects/agents/docker-compose.yml` includes a Redis URL with password and a Miniflux password
- `services/node1/agents/docker-compose.yml` contains inline Sonarr, Radarr, and Tautulli API keys
- `ansible/roles/dashboard/defaults/main.yml` includes the dashboard VAPID private key

Impact:

- host or port changes require unsafe, repo-wide search-and-replace work
- secrets are duplicated across code, Compose, and build outputs
- newer contract-driven work can never fully converge while older surfaces bypass it

Recommendation:

- centralize all runtime endpoints and secrets behind Ansible-provided env or a single app config layer
- remove committed real credentials from source control
- keep project-local `docker-compose.yml` files for development only, and ensure they source secrets from env files or Ansible-generated env

### F5. The dashboard is only partially migrated to the new operator-console architecture

Severity: Medium

The new command center work is real, but the rest of the dashboard is mixed.

Evidence:

- the new APIs and typed data layer are in place for core command-center surfaces
- older route families such as personal data, monitoring, media, home, and feedback still contain direct service URLs or hand-rolled integration logic
- the dashboard now has both a newer normalized data layer and older page-local backend assumptions

Impact:

- the "command center" can be more correct than the pages around it
- env-driven deployment fixes do not automatically fix legacy pages
- the UI cannot yet be treated as a single, coherent operator surface

Recommendation:

- finish migrating legacy dashboard routes to the centralized config/data model
- treat any page that talks directly to backend IPs as technical debt to be eliminated

### F6. Repo guidance docs are stale relative to the deployed system model

Severity: Medium

Examples:

- `AGENTS.md` still says "8 live" Athanor agents
- `projects/agents/src/athanor_agents/server.py` contains 9 agent entries, including `data-curator`
- `STATUS.md` and other docs already describe 9 agents

Impact:

- human operators and contributors get conflicting descriptions of the same system
- onboarding and operational reasoning degrade

Recommendation:

- align `AGENTS.md`, `STATUS.md`, and the dashboard agent metadata with the same roster and capability map

## What Already Looks Correct

These pieces are directionally sound and should remain the backbone of the system:

- LiteLLM as the central inference router on VAULT
- dashboard-owned APIs for operator views instead of route-local browser fetches to every backend
- Prometheus blackbox probe support for service history
- agent server as the action/orchestration layer
- Qdrant, Redis, and Neo4j as distinct shared-state systems rather than one overloaded store
- EoBQ using LiteLLM, ComfyUI, and Qdrant as a specialized vertical app
- separate Open WebUI surfaces with explicit roles:
  - WORKSHOP Open WebUI for direct/raw model access
  - VAULT Open WebUI for LiteLLM-routed access

## Recommended Cleanup Order

### Phase 1: Freeze the architecture contracts

- Declare Ansible authoritative for deployment topology.
- Decide the embedding host once.
- Decide the canonical LiteLLM alias map once.
- Update docs to reflect those decisions in one pass.

### Phase 2: Remove config bypasses

- Replace hardcoded IPs and credentials in agents and dashboard code with centralized config.
- Remove committed secrets from project Compose files, snapshot Compose files, and defaults.
- Convert any remaining direct dashboard backend calls into normalized dashboard-owned API routes.

### Phase 3: Clean the repo surface

- Mark `services/` as snapshots or regenerate them from Ansible.
- Update `AGENTS.md`, `STATUS.md`, and other topology docs so they agree.
- Remove stale model labels from dashboard config and UI copy.

### Phase 4: Enforce the contracts

- add tests that validate:
  - dashboard config matches the Ansible env model
  - LiteLLM alias docs match the LiteLLM template
  - agent roster docs match `AGENT_METADATA`
  - no forbidden raw node IPs appear outside approved config fixtures/tests

## Practical Target State

If the system is operating correctly, the interaction chain should look like this:

1. User opens the dashboard on WORKSHOP.
2. Dashboard UI calls its own API routes, not raw infra endpoints.
3. Dashboard API routes pull service history and GPU history from Prometheus, current service status from approved health endpoints, and agent state from the agent server.
4. User chat from the dashboard goes to the agent server or the direct chat proxy.
5. The agent server routes all inference through LiteLLM aliases.
6. LiteLLM routes the request to the currently assigned vLLM backend.
7. Agents use Redis, Qdrant, Neo4j, and domain APIs for memory, coordination, and tool execution.
8. Observability remains centered on Prometheus and Grafana, with the dashboard consuming summaries instead of inventing its own parallel telemetry model.

That is the architecture Athanor is closest to already. The remaining work is mostly convergence work: make every layer obey the same contracts.
