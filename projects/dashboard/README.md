# Athanor Dashboard

Desktop-first operator console for the Athanor homelab. The dashboard now includes:

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
| `/` | Command center with cluster posture, alerts, trends, hotspots, and launch paths |
| `/services` | Service operations surface with URL-persisted filters, probe history, and detail drawer |
| `/gpu` | Fleet telemetry with node trends, hotspot triage, drill-down charts, and comparison |
| `/chat` | Persisted direct-model chat sessions with export/copy/abort controls |
| `/agents` | Persisted agent threads with tool timeline rendering and normalized streaming |

## API Routes

| Route | Purpose |
|-------|---------|
| `/api/overview` | Typed command center snapshot |
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
npm run lint
npm run build
npm run test:e2e
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
- `ATHANOR_VLLM_UTILITY_URL`
- `ATHANOR_VLLM_WORKER_URL`
- `ATHANOR_VLLM_EMBEDDING_URL`
- `ATHANOR_VLLM_RERANKER_URL`
- `ATHANOR_QDRANT_URL`
- `ATHANOR_NEO4J_URL`
- `ATHANOR_HOME_ASSISTANT_URL`

Secrets are env-only:

- `ATHANOR_LITELLM_API_KEY`
- `ATHANOR_NEO4J_PASSWORD`
- `VAPID_PRIVATE_KEY`

The remaining media and UI endpoints fall back to sensible defaults derived from the host variables.

## Notes

- `/api/chat` emits a normalized SSE event stream for both direct model chat and agent chat.
- Agent tool timeline correlation now uses a stable `toolCallId` propagated from the agent server.
- Service history depends on Prometheus blackbox probe metrics added through the `vault-monitoring` Ansible role.
- Storybook currently builds successfully; Vite logs benign Radix `"use client"` bundling warnings during the build.
