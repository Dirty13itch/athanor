# AGENTS.md — Athanor Repository Agent Instructions

## Commands
- `npm run dev` — Start UI in development mode (port 3001)
- `npm run build` — Build UI for production
- `pytest` — Run Python tests (from service directories)
- `ruff check .` — Lint Python code
- `biome check .` — Lint JS/TS code

## Testing
- Python services: `cd services/<name> && pytest`
- UI: `cd ui && npm test`
- Full drift check: `bash scripts/drift-check.sh`

## Project Structure
- `services/` — Microservice source code
- `scripts/` — Deployment, maintenance, and automation scripts
- `docs/` — Architecture, research, design documents
- `config/` — System configuration files
- `ui/` — Next.js 15 frontend (React 19, Tailwind 4)
- `.claude/` — Claude Code agents, skills, rules

## Code Style
- Python: Formatted with ruff, type-checked with basedpyright
- TypeScript: Strict mode, formatted with biome
- All services use FastAPI + uvicorn
- Import ordering: stdlib, third-party, local

## Git Workflow
- Branch per feature: `agent/<agent-name>/<task-id>`
- Conventional commits (feat:, fix:, chore:, docs:)
- PR required for merge to main
- Tests must pass before merge

## Boundaries
### Always Do
- Run tests before submitting PR
- Use existing service patterns from Gateway/Memory/MIND
- Route through LiteLLM (VAULT:4000) for model calls, never direct
- Use cluster_config.py for IP addresses, never hardcode

### Ask First
- Changes to systemd service files
- Changes to LiteLLM config on VAULT
- Database schema changes (PostgreSQL, Qdrant, Neo4j)
- Any destructive operations (rm -rf, DROP TABLE, git reset)

### Never Do
- Commit secrets, API keys, or credentials
- Push directly to main
- Modify CONSTITUTION.yaml without explicit approval
- Access external APIs without going through LiteLLM proxy
- Delete backup files or logs
