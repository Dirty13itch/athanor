# AGENTS.md

Repository-local instructions for Athanor.

## Authority Model

Implementation authority: `C:\Athanor`

Runtime authority: `/home/shaun/repos/athanor` on `DEV`

Reference-only docs:
- [docs/archive/planning-era/VISION.md](/C:/Athanor/docs/archive/planning-era/VISION.md)
- [docs/MASTER-PLAN.md](/C:/Athanor/docs/MASTER-PLAN.md)
- [MEMORY.md](/C:/Athanor/MEMORY.md)
- [CLAUDE.md](/C:/Athanor/CLAUDE.md)

Archive criteria:
- keep only material still needed for audit history, recovery evidence, active migration or cutover work, or a live runbook without a verified replacement
- otherwise delete stale startup guidance, duplicate configs, dead scripts, and superseded generated outputs

## First Sources

Start in this order:
1. [STATUS.md](/C:/Athanor/STATUS.md)
2. [docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md](/C:/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md)
3. [docs/operations/ATHANOR-OPERATING-SYSTEM.md](/C:/Athanor/docs/operations/ATHANOR-OPERATING-SYSTEM.md)
4. [config/automation-backbone](/C:/Athanor/config/automation-backbone)

Prefer runtime truth and current registries over historical analysis.

## Project Layout

- [projects/agents](/C:/Athanor/projects/agents) — governor, routing, automation, control-plane contracts
- [projects/dashboard](/C:/Athanor/projects/dashboard) — Next.js operator product on port `3001`
- [projects/gpu-orchestrator](/C:/Athanor/projects/gpu-orchestrator) — GPU and host orchestration
- [projects/ws-pty-bridge](/C:/Athanor/projects/ws-pty-bridge) — authenticated websocket terminal bridge
- [scripts](/C:/Athanor/scripts) — validators, generators, collectors, and operator utilities
- [config/automation-backbone](/C:/Athanor/config/automation-backbone) — source of truth for topology, maturity, docs lifecycle, inventories, and cadence
- [services](/C:/Athanor/services) — legacy/shared services still being normalized

## Commands

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_documentation_index.py`
- `python scripts/generate_project_maturity_report.py`
- `python scripts/generate_truth_inventory_reports.py`
- `python scripts/run_service_contract_tests.py`
- `bash scripts/drift-check.sh`
- `python scripts/render_ansible_template.py --ansible-root C:\Athanor\ansible --host vault --template roles\vault-litellm\templates\litellm_config.yaml.j2 --defaults roles\vault-litellm\defaults\main.yml`
- `powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1`
- `powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-RepoDeploymentManifestAudit.ps1`
- `cd projects/dashboard && npm run dev`
- `cd projects/dashboard && npm test`
- `cd projects/dashboard && npm run typecheck`
- `cd projects/dashboard && npm run build`
- `cd projects/dashboard && npm run test:e2e:terminal`
- `cd projects/agents && .\.venv\Scripts\python -m pytest tests -q`
- `cd projects/gpu-orchestrator && .\.venv\Scripts\python -m pytest tests -q`
- `cd projects/ws-pty-bridge && npm run ci`

## Live Agent Roster

| Agent | Type | Cadence | Status |
|-------|------|---------|--------|
| **General Assistant** | proactive | event-driven | Live |
| **Media Agent** | proactive | every 15 min | Live |
| **Home Agent** | proactive | every 5 min | Live |
| **Creative Agent** | reactive | on demand | Live |
| **Research Agent** | reactive | on demand | Live |
| **Knowledge Agent** | reactive | on demand | Live |
| **Coding Agent** | proactive | event-driven | Live |
| **Stash Agent** | reactive | on demand | Live |
| **Data Curator** | proactive | every 6 hours | Live |

## Boundaries

Always do:
- update the registry-backed truth first when the change affects topology, maturity, docs lifecycle, provider inventory, or runtime ownership
- verify with the smallest useful command before calling work complete
- keep secret values out of tracked files, reports, and generated artifacts

Ask first:
- systemd unit changes
- LiteLLM config changes on VAULT
- database schema changes
- destructive file or git operations outside the prune policy

Never do:
- treat `/home/shaun/repos/athanor` or `athanor-next` as code authority
- hardcode IPs or hostnames when `cluster_config.py` or topology truth already owns them
- leave stale startup docs in place once replacement truth is verified
