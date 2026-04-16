# Scripts Inventory

Placement contract:

- stable operator entrypoints and reusable script libraries belong in `scripts/`
- script contract tests belong in `scripts/tests/`
- disposable probes belong in `tmp/` and should stay untracked
- use [docs/operations/REPO-STRUCTURE-RULES.md](/C:/Athanor/docs/operations/REPO-STRUCTURE-RULES.md) when deciding whether something belongs in `scripts/`, `reports/`, `docs/operations/`, or `config/automation-backbone/`

## Operations

| Script | Purpose | Usage |
|--------|---------|-------|
| `drift-check.sh` | Registry-backed runtime drift verification across the active Athanor service map | `bash scripts/drift-check.sh` |
| `contract-tests.sh` | Quick interface-shape and endpoint-presence contract checks for live runtime surfaces | `bash scripts/contract-tests.sh [--quiet]` |
| `deploy-agents.sh` | Deploy agent server to FOUNDRY (sync, build, restart) | `./scripts/deploy-agents.sh [--no-build]` |
| `run_autonomy_loop_pass.py` | Run one governed native loop pass across builtin and agent-schedule jobs, then write `reports/autonomy-loop/latest.json` | `python scripts/run_autonomy_loop_pass.py [--force-deferred] [--skip-agent-schedules]` |
| `run_ralph_loop_pass.py` | Run one Ralph-loop control pass: refresh evidence, classify workstreams, and write `reports/ralph-loop/latest.json` | `python scripts/run_ralph_loop_pass.py [--skip-refresh] [--skip-validation]` |
| `session_restart_brief.py` | Print a compact session-restart brief from live Ralph, governed-dispatch, atlas, capacity, and git state so a fresh session can re-enter quickly | `python scripts/session_restart_brief.py [--refresh] [--json] [--write output/session-restart-brief.md]` |
| `write_steady_state_status.py` | Write the steady-state operator status surfaces from live finish-scoreboard, runtime inbox, and restart context | `python scripts/write_steady_state_status.py [--json] [--check]` |
| `run_steady_state_control_plane.py` | Run the canonical fixed-point steady-state control-plane pass: refresh truth, Ralph, restart/status surfaces, and final validation in one ordered command | `python scripts/run_steady_state_control_plane.py [--skip-restart-brief] [--json]` |
| `model-inventory.sh` | Scan NFS models and report available vs loaded | `bash scripts/model-inventory.sh` |
| `run_service_contract_tests.py` | Create or reuse the disposable service-contract venv and run the service and script health-contract suites | `python scripts/run_service_contract_tests.py [--reinstall]` |
| `requirements-test.txt` | Dependency bundle for script-service contract tests in the disposable service-contract venv | Consumed by `python scripts/run_service_contract_tests.py` |
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
| `extract-entities.py` | LLM entity extraction from Qdrant -> Neo4j | `python3 scripts/extract-entities.py` |
| `graph-bookmarks.py` | Populate Neo4j with bookmark nodes | `python3 scripts/graph-bookmarks.py` |
| `graph-github.py` | Populate Neo4j with GitHub repo nodes | `python3 scripts/graph-github.py` |
| `parse-bookmarks.py` | Parse Chrome bookmark HTML -> Qdrant + JSON | `python3 scripts/parse-bookmarks.py` |
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
| `nightly-improvement.sh` | Full OODA loop: export -> score -> identify -> deploy | Systemd timer |
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
| `map-agent-endpoints.py` | Map the live agent-server FastAPI route registry to runtime subsystems | `python3 scripts/map-agent-endpoints.py` |
| `find-mounted-ui.py` | Build dashboard mount graph, classify UI state | `python3 scripts/find-mounted-ui.py` |
| `probe-agent-runtime.py` | Probe live agent-server runtime (read-only) | `python3 scripts/probe-agent-runtime.py` |
| `check-doc-refs.py` | Check for broken internal markdown links | `python3 scripts/check-doc-refs.py <path>` |

Completion-audit inventories now land under `reports/completion-audit/latest/inventory/` instead of `docs/atlas/inventory/completion/`.
The runtime subsystem census now derives from the live `athanor_agents.server.app` route registry instead of `docs/atlas/inventory/runtime-inventory.json`.

For canonical runtime verification, start with `drift-check.sh` plus `run_service_contract_tests.py`.
Treat `contract-tests.sh` as a narrower live endpoint contract helper, not a replacement for the registry-backed drift lane.

## Evaluation & Benchmarks

| Script | Purpose | Usage |
|--------|---------|-------|
| `run-evals.sh` | Run agent evaluation suite via promptfoo | `./scripts/run-evals.sh [--output FILE]` |
| `run_capability_pilot_formal_preflight.py` | Validate whether Goose, OpenHands, Letta, and AGT have the env, scaffold, and artifact contract needed for a formal pilot eval without actually executing it | `python scripts/run_capability_pilot_formal_preflight.py [--run-id ...] [--host-id desk]` |
| `run_capability_pilot_formal_eval.py` | Run one formal pilot eval when preflight is ready, or emit a blocked or manual-review artifact when it is not. Promptfoo pilots execute directly; benchmark-spec pilots materialize comparison artifacts for manual contract review once valid fixtures exist. | `python scripts/run_capability_pilot_formal_eval.py --run-id goose-operator-shell-lane-eval-2026q2` |
| `generate_capability_pilot_readiness.py` | Build pilot-readiness truth for packet-drafting capabilities from lanes, evals, packets, and tooling inventory | `python scripts/generate_capability_pilot_readiness.py [--host-id desk]` |
| `run_capability_pilot_evals.py` | Execute bounded pilot flows for Goose, OpenHands, Letta, and AGT, then write machine-readable pilot-eval evidence | `python scripts/run_capability_pilot_evals.py [--run-id ...] [--host-id desk]` |
| `run_gpu_scheduler_baseline_eval.py` | Pin the current live GPU-orchestrator baseline and check whether the scheduler surface is source-aligned without overclaiming formal readiness | `python scripts/run_gpu_scheduler_baseline_eval.py` |
| `run_gpu_scheduler_promotion_eval.py` | Execute the bounded scheduler promotion-eval contract and report whether live rollout plus bounded mutation surfaces exist yet | `python scripts/run_gpu_scheduler_promotion_eval.py` |
| `record_supported_tool_usage.py` | Record a supported-tool usage proof for planned subscription families such as GLM Coding Plan | `python scripts/record_supported_tool_usage.py --family-id glm_coding_plan --tool-name codex --request-surface "<surface>"` |
| `tp-benchmark.sh` | Live throughput benchmark for vLLM endpoints | `./scripts/tp-benchmark.sh [REQUESTS]` |

## Creative / Media

| Script | Purpose | Usage |
|--------|---------|-------|
| `gen-switch.sh` | Switch between ComfyUI and Wan2GP on WORKSHOP GPU | `./scripts/gen-switch.sh [comfyui|wan2gp]` |
| `prepare-dataset.sh` | Prepare photo dataset for LoRA training | `./scripts/prepare-dataset.sh <dir> <trigger> [sdxl|flux]` |
| `prepare-dataset.py` | Automated face detection + dataset prep for LoRA | `python3 scripts/prepare-dataset.py` |
| `train-lora.sh` | Quick LoRA training launcher | `./scripts/train-lora.sh [sdxl|flux] <trigger> <dir>` |

## Monitoring

| Script | Purpose | Usage |
|--------|---------|-------|
| `import-grafana-dashboards.sh` | Import Grafana dashboards on VAULT | Run on VAULT |
| `overnight-ops.sh` | Scheduled overnight maintenance tasks plus Ralph-loop evidence refresh and control-pass planning | `./scripts/overnight-ops.sh [--dry-run]` |

## Subdirectories

| Directory | Contents |
|-----------|----------|
| `setup/` | Rack build: autoinstall YAML, Ventoy USB prep, post-install audit |
| `tests/` | Live smoke tests plus direct script-service contract suites |
