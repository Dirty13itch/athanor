# Athanor Command Center

Desktop-first operator console for the Athanor cluster. The user-facing product is the Athanor Command Center; `dashboard` remains the internal package and service name during the transition.

The canonical front door is `https://athanor.local/`. The current transitional runtime target is DEV `:3001`, and the production deployment artifact is the containerized build defined by the local `Dockerfile`.

The command center includes:

- a full command center shell with global status, quick actions, and command palette
- typed dashboard-owned APIs for overview, services, GPU telemetry, models, and agents
- first-class project platform context for Athanor core, EoBQ, and scaffolded future tenants
- Prometheus-backed service history and GPU history views
- browser-persisted direct-chat sessions and agent threads
- Storybook, Vitest, Playwright, and Lighthouse CI scaffolding for frontend quality
- a documented route-by-route audit baseline in `docs/UI_AUDIT.md`

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Command center with cluster posture, alerts, blockers, approvals, recent work, and launch paths |
| `/topology` | Cluster topology plus the compiled master atlas relationship map for authority, promotion, capacity, and lane orchestration |
| `/services` | Service operations surface with URL-persisted filters, probe history, and detail drawer |
| `/gpu` | Fleet telemetry with node trends, hotspot triage, drill-down charts, and comparison |
| `/chat` | Persisted direct-model chat sessions with export/copy/abort controls |
| `/agents` | Persisted agent threads with tool timeline rendering and normalized streaming |

## API Routes

| Route | Purpose |
|-------|---------|
| `/api/overview` | Typed command center snapshot |
| `/api/master-atlas` | Compiled federated relationship map used by the topology front door |
| `/api/services` | Current service snapshot |
| `/api/services/history` | Service probe history from Prometheus |
| `/api/gpu` | Current GPU snapshot |
| `/api/gpu/history` | GPU range history from Prometheus |
| `/api/models` | Normalized model inventory |
| `/api/agents` | Normalized agent roster |
| `/api/projects` | Normalized project registry snapshot |
| `/api/chat` | Normalized chat stream proxy for inference backends and agent server |

## Development

```bash
npm install
npm run dev
```

Local QA commands:

```bash
npm test
npm run typecheck
npm run lint
npm run build
npm run test:e2e
npm run test:e2e:terminal
npm run storybook:build
```

Optional local tools:

```bash
npm run storybook
npm run lighthouse
```

Deterministic QA runs use `DASHBOARD_FIXTURE_MODE=1` so the dashboard renders stable snapshots instead of depending on live homelab telemetry during test execution.

## Configuration

Copy `.env.example` to `.env.local` and adjust only the endpoints that differ from the default homelab layout.

Primary variables:

- `ATHANOR_NODE1_HOST`
- `ATHANOR_NODE2_HOST`
- `ATHANOR_VAULT_HOST`
- `ATHANOR_DEV_HOST`
- `ATHANOR_AGENT_SERVER_URL`
- `ATHANOR_PROMETHEUS_URL`
- `ATHANOR_GRAFANA_URL`
- `ATHANOR_VLLM_COORDINATOR_URL`
- `ATHANOR_VLLM_CODER_URL`
- `ATHANOR_VLLM_WORKER_URL`
- `ATHANOR_VLLM_EMBEDDING_URL`
- `ATHANOR_VLLM_RERANKER_URL`
- `ATHANOR_QDRANT_URL`
- `ATHANOR_NEO4J_URL`
- `ATHANOR_HOME_ASSISTANT_URL`
- `ATHANOR_FOUNDRY_DOCKER_PROXY`
- `ATHANOR_VAULT_DOCKER_PROXY`

Secrets are env-only:

- `ATHANOR_LITELLM_API_KEY`
- `ATHANOR_NEO4J_PASSWORD`
- `VAPID_PRIVATE_KEY`

The remaining media and UI endpoints fall back to sensible defaults derived from the host variables.

Front-door-specific variables:

- `ATHANOR_COMMAND_CENTER_URL`
- `ATHANOR_WORKSHOP_LINK_HOST`
- `ATHANOR_VAULT_LINK_HOST`
- `ATHANOR_ULRICH_LINK_URL`

## Notes

- `/api/chat` emits a normalized SSE event stream for both direct model chat and agent chat.
- Agent tool timeline correlation now uses a stable `toolCallId` propagated from the agent server.
- Service history depends on Prometheus blackbox probe metrics added through the `vault-monitoring` Ansible role.
- Storybook currently builds successfully; Vite logs benign Radix `"use client"` bundling warnings during the build.
