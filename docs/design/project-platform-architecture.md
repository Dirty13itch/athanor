# Project Platform Architecture

## Overview

Athanor hosts multiple independent projects, each with their own UI, data, and agent interactions. This doc describes how projects are isolated and managed.

## Current Projects

| Project | Stack | Port | Location | Status |
|---------|-------|------|----------|--------|
| Athanor Command Center | Next.js 16 + React 19 | `https://athanor.local/` (runtime `dev.athanor.local:3001`) | `projects/dashboard/` | Production |
| Empire of Broken Queens (EoBQ) | Next.js + ComfyUI | WORKSHOP:3002 | `projects/eoq/` | Production |
| Ulrich Energy | Next.js + LiteLLM | WORKSHOP:8088 | `projects/ulrich-energy/` | Scaffold |
| Kindred | — | — | `projects/kindred/` | Concept only |

## Isolation Model

### Code Isolation
Each project is a standalone Next.js application in `projects/<name>/` with its own:
- `package.json` / `node_modules`
- `src/` application code
- `docker-compose.yml` for deployment
- TypeScript config (`tsconfig.json`)

Projects share NO code at the npm level. Shared patterns are duplicated intentionally — coupling is worse than duplication at this scale.

### Data Isolation
- **Agent tasks:** `project_id` field routes tasks to project-specific context
- **Qdrant collections:** Shared `knowledge` collection, per-project filtering via `category` payload
- **Neo4j:** `Project` nodes with `MANAGES` edges to services
- **Filesystem:** `/output/<project>/` for generated artifacts

### Inference Isolation
All projects share the LiteLLM routing layer (VAULT:4000). No project-specific model deployments. The agent server (FOUNDRY:9000) routes tasks to agents by `agent_id`, with `project_id` metadata for context injection.

## Agent Integration

Projects interact with agents through:
1. **Command Center proxy** — `/api/agents/proxy` forwards to FOUNDRY:9000
2. **Direct API** — `POST /v1/tasks` with `project_id` in request body
3. **Scheduled tasks** — `scheduler.py` can scope tasks to projects

The intelligence console groups patterns by project, allowing project-specific insights.

## Deployment

Each project deploys independently via rsync + docker compose:
```bash
rsync -avz projects/<name>/src/ workshop:/opt/athanor/<name>/src/
ssh workshop "cd /opt/athanor/<name> && docker compose up -d --build"
```

No shared deployment pipeline. Each project is an independent deploy unit.

## Future Considerations

- **Project-scoped Qdrant collections** — if knowledge base grows, split per-project
- **Project-scoped agent instances** — per-project agent configs with tailored system prompts
- **Multi-tenant auth** — currently single-user; would need project-scoped access control

Last updated: 2026-03-14
