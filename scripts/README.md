# Scripts Inventory

## Operations

| Script | Purpose | Usage |
|--------|---------|-------|
| `health-check-all.sh` | Check all service health endpoints with formatted output | `./scripts/health-check-all.sh [-q] [-j]` |
| `deploy-agents.sh` | Deploy agent server to FOUNDRY (sync, build, restart) | `./scripts/deploy-agents.sh [--no-build]` |
| `model-inventory.sh` | Scan NFS models and report available vs loaded | `bash scripts/model-inventory.sh` |
| `set-gpu-power-limits.sh` | Set GPU power limits on FOUNDRY (run on boot) | Run on FOUNDRY |
| `vault-ssh.py` | SSH to VAULT via paramiko (native SSH hangs) | `python3 scripts/vault-ssh.py <command>` |
| `node-heartbeat.py` | GPU metrics + container status daemon (Redis, 10s interval) | Systemd service on each node |
| `audit-deployment-ownership.py` | Audit deployment ownership and service reachability | `python3 scripts/audit-deployment-ownership.py` |

## Backups (Cron)

| Script | Purpose | Schedule |
|--------|---------|----------|
| `backup-appdata.sh` | Backup VAULT container appdata as tarballs | Cron on VAULT |
| `backup-neo4j.sh` | Export Neo4j graph via Cypher | Cron on VAULT |
| `backup-qdrant.sh` | Snapshot Qdrant collections to VAULT HDD | Cron on FOUNDRY |
| `backup-age-exporter.py` | Prometheus exporter for backup freshness | Systemd service on VAULT |
| `backup-age-metrics.sh` | Write backup age metrics for node_exporter | Cron every 15min |

## Data Indexing

| Script | Purpose | Usage |
|--------|---------|-------|
| `index-knowledge.py` | Index Athanor docs into Qdrant knowledge base | `python3 scripts/index-knowledge.py [--full]` |
| `index-files.py` | Index personal data files into Qdrant | `python3 scripts/index-files.py` |
| `index-github.py` | Index GitHub repos/stars into Qdrant | `python3 scripts/index-github.py` |
| `extract-entities.py` | LLM entity extraction from Qdrant → Neo4j | `python3 scripts/extract-entities.py` |
| `graph-bookmarks.py` | Populate Neo4j with bookmark nodes | `python3 scripts/graph-bookmarks.py` |
| `graph-github.py` | Populate Neo4j with GitHub repo nodes | `python3 scripts/graph-github.py` |
| `parse-bookmarks.py` | Parse Chrome bookmark HTML → Qdrant + JSON | `python3 scripts/parse-bookmarks.py` |
| `build-profile.sh` | Gather user profile data, upsert to Qdrant | `python3 scripts/build-profile.sh` |
| `sync-personal-data.sh` | Sync personal data from DEV to FOUNDRY | `./scripts/sync-personal-data.sh` |
| `seed-eoq-graph.py` | Seed Neo4j with EoBQ character graph | `python3 scripts/seed-eoq-graph.py` |
| `seed-miniflux-feeds.py` | Seed Miniflux RSS feeds | `python3 scripts/seed-miniflux-feeds.py` |

## Self-Improvement Pipeline

| Script | Purpose | Usage |
|--------|---------|-------|
| `export-langfuse-traces.py` | Export LangFuse traces for analysis | `python3 scripts/export-langfuse-traces.py` |
| `score-interactions.py` | Score interactions via local reasoning model | `python3 scripts/score-interactions.py` |
| `identify-failures.py` | Cluster failure patterns, suggest improvements | `python3 scripts/identify-failures.py` |
| `deploy-improvements.py` | Deploy validated improvements to agent server | `python3 scripts/deploy-improvements.py` |
| `nightly-improvement.sh` | Full OODA loop: export → score → identify → deploy | Systemd timer |
| `sync-prompts-to-langfuse.py` | Sync agent system prompts to LangFuse | `python3 scripts/sync-prompts-to-langfuse.py` |

## MCP Servers

| Script | Purpose | Usage |
|--------|---------|-------|
| `mcp-athanor-agents.py` | MCP bridge to agent server (stdio) | Claude Code MCP |
| `mcp-docker.py` | Multi-node Docker management via SSH | Claude Code MCP |
| `mcp-qdrant.py` | Qdrant vector DB access | Claude Code MCP |
| `mcp-redis.py` | Redis cluster state access | Claude Code MCP |
| `mcp-smart-reader.py` | Smart file reading with local model summarization | Claude Code MCP |

## Completion Audit

| Script | Purpose | Usage |
|--------|---------|-------|
| `run-completion-audit.py` | Run completion audit and build readiness report | `python3 scripts/run-completion-audit.py` |
| `completion_audit_common.py` | Shared helpers for audit toolchain | Library (imported) |
| `census-dashboard-api.py` | Census dashboard API from filesystem evidence | `python3 scripts/census-dashboard-api.py` |
| `census-dashboard-components.py` | Inventory dashboard components and features | `python3 scripts/census-dashboard-components.py` |
| `census-dashboard-routes.py` | Census dashboard routes from source files | `python3 scripts/census-dashboard-routes.py` |
| `census-env-contracts.py` | Inventory env/config contracts across layers | `python3 scripts/census-env-contracts.py` |
| `map-agent-endpoints.py` | Map agent-server endpoints to subsystems | `python3 scripts/map-agent-endpoints.py` |
| `find-mounted-ui.py` | Build dashboard mount graph, classify UI state | `python3 scripts/find-mounted-ui.py` |
| `probe-agent-runtime.py` | Probe live agent-server runtime (read-only) | `python3 scripts/probe-agent-runtime.py` |
| `validate-atlas.py` | Validate atlas docs and inventory layer | `python3 scripts/validate-atlas.py` |
| `check-doc-refs.py` | Check for broken internal markdown links | `python3 scripts/check-doc-refs.py` |

## Evaluation & Benchmarks

| Script | Purpose | Usage |
|--------|---------|-------|
| `run-evals.sh` | Run agent evaluation suite via promptfoo | `./scripts/run-evals.sh [--output FILE]` |
| `tp-benchmark.sh` | Live throughput benchmark for vLLM endpoints | `./scripts/tp-benchmark.sh [REQUESTS]` |

## Creative / Media

| Script | Purpose | Usage |
|--------|---------|-------|
| `gen-switch.sh` | Switch between ComfyUI and Wan2GP on WORKSHOP GPU | `./scripts/gen-switch.sh [comfyui\|wan2gp]` |
| `prepare-dataset.sh` | Prepare photo dataset for LoRA training | `./scripts/prepare-dataset.sh <dir> <trigger> [sdxl\|flux]` |
| `prepare-dataset.py` | Automated face detection + dataset prep for LoRA | `python3 scripts/prepare-dataset.py` |
| `train-lora.sh` | Quick LoRA training launcher | `./scripts/train-lora.sh [sdxl\|flux] <trigger> <dir>` |

## Monitoring

| Script | Purpose | Usage |
|--------|---------|-------|
| `import-grafana-dashboards.sh` | Import Grafana dashboards on VAULT | Run on VAULT |
| `overnight-ops.sh` | Scheduled overnight maintenance tasks | `./scripts/overnight-ops.sh [--dry-run]` |

## Subdirectories

| Directory | Contents |
|-----------|----------|
| `setup/` | Rack build: autoinstall YAML, Ventoy USB prep, post-install audit |
| `tests/` | Live smoke tests: dashboard, EoBQ, Ulrich, UI coverage audit |
