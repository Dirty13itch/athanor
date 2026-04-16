# Athanor

Athanor is a sovereign AI cluster and operator control plane. This repository is the durable implementation authority for the control layer, inventories, validation rules, and canonical current-state docs.

For a fast current-state restart, run:
- `python scripts/session_restart_brief.py --refresh`

> **Boundary:** This is the onboarding surface, not the live runtime or queue oracle. When current mutable state matters, defer to `STATUS.md`, `python scripts/session_restart_brief.py --refresh`, `reports/ralph-loop/latest.json`, `reports/truth-inventory/finish-scoreboard.json`, `reports/truth-inventory/runtime-packet-inbox.json`, `reports/truth-inventory/`, and generated reports under `docs/operations/`.

## Authority Model

Implementation authority: `C:\Athanor`

Runtime authority: `/home/shaun/repos/athanor` on `DEV`

Reference-only docs:
- [docs/archive/planning-era/VISION.md](/C:/Athanor/docs/archive/planning-era/VISION.md)
- [docs/MASTER-PLAN.md](/C:/Athanor/docs/MASTER-PLAN.md)
- [MEMORY.md](/C:/Athanor/MEMORY.md)
- [CLAUDE.md](/C:/Athanor/CLAUDE.md)

Archive criteria:
- keep only material still required for legal or audit history, recovery evidence, an active migration or cutover, or a live runbook with no verified replacement
- delete stale docs, configs, scripts, and generated outputs once replacement truth is verified

## Start Here

Read these in order:
- [STATUS.md](/C:/Athanor/STATUS.md)
- [docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md](/C:/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md)
- [docs/operations/ATHANOR-OPERATING-SYSTEM.md](/C:/Athanor/docs/operations/ATHANOR-OPERATING-SYSTEM.md)
- [PROJECT.md](/C:/Athanor/PROJECT.md)
- [config/automation-backbone](/C:/Athanor/config/automation-backbone)

Runtime truth outranks memory or historical docs when they disagree.

## Registry Truth

The active control plane lives under [config/automation-backbone](/C:/Athanor/config/automation-backbone).

Primary registries:
- `platform-topology.json`
- `project-maturity-registry.json`
- `reconciliation-source-registry.json`
- `docs-lifecycle-registry.json`
- `program-operating-system.json`
- `hardware-inventory.json`
- `model-deployment-registry.json`
- `provider-catalog.json`
- `tooling-inventory.json`
- `credential-surface-registry.json`
- `repo-roots-registry.json`
- `routing-taxonomy-map.json`

Generated reports derived from those registries live under [docs/operations](/C:/Athanor/docs/operations).

## Repository Structure

- [projects/agents](/C:/Athanor/projects/agents) — control plane, governor, routing, and automation runtime
- [projects/dashboard](/C:/Athanor/projects/dashboard) — operator product
- [projects/gpu-orchestrator](/C:/Athanor/projects/gpu-orchestrator) — GPU sleep/wake and host control
- [projects/ws-pty-bridge](/C:/Athanor/projects/ws-pty-bridge) — authenticated terminal bridge
- [config](/C:/Athanor/config) — registry-backed control-plane truth
- [scripts](/C:/Athanor/scripts) — validation, reporting, maintenance, and collectors
- [docs](/C:/Athanor/docs) — canonical, generated, reference, and archive docs classified by lifecycle registry
- [services](/C:/Athanor/services) — transitional legacy and shared service surfaces under no-growth normalization

Structure placement rules live in [docs/operations/REPO-STRUCTURE-RULES.md](/C:/Athanor/docs/operations/REPO-STRUCTURE-RULES.md).

## Core Validation

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_documentation_index.py --check`
- `python scripts/generate_project_maturity_report.py --check`
- `python scripts/generate_truth_inventory_reports.py --check`
- `cd projects/dashboard && npm run typecheck`
- `cd projects/dashboard && npm test`
- `cd projects/agents && .\.venv\Scripts\python -m pytest tests -q`

## Working Rule

Do not treat old narrative docs as live truth. If a runtime fact, registry, and doc disagree, fix the doc or helper so it matches the verified runtime and registry model.
