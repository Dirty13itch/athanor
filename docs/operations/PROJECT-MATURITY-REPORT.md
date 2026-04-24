# Project Maturity Report

Generated from `config/automation-backbone/project-maturity-registry.json` by `scripts/generate_project_maturity_report.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-20.1`
- Projects tracked: `11`
- Projects meeting declared class: `11`

| Class | Count |
| --- | ---: |
| `platform-core` | 5 |
| `production-product` | 1 |
| `active-scaffold` | 2 |
| `incubation` | 1 |
| `archive` | 2 |

## Project Status

| Project | Class | Status | Owner | Workspace |
| --- | --- | --- | --- | --- |
| `agents` (Athanor Agents) | `platform-core` | meets declared class | `shaun` | `projects/agents` |
| `dashboard` (Athanor Dashboard) | `production-product` | meets declared class | `shaun` | `projects/dashboard` |
| `gpu-orchestrator` (GPU Orchestrator) | `platform-core` | meets declared class | `shaun` | `projects/gpu-orchestrator` |
| `ws-pty-bridge` (WS PTY Bridge) | `platform-core` | meets declared class | `shaun` | `projects/ws-pty-bridge` |
| `gateway` (Gateway) | `platform-core` | meets declared class | `shaun` | `services/gateway` |
| `quality-gate` (Quality Gate) | `platform-core` | meets declared class | `shaun` | `services/quality-gate` |
| `eoq` (EOQ) | `active-scaffold` | meets declared class | `shaun` | `projects/eoq` |
| `comfyui-workflows` (ComfyUI Workflows) | `active-scaffold` | meets declared class | `shaun` | `projects/comfyui-workflows` |
| `kindred` (Kindred) | `incubation` | meets declared class | `shaun` | `projects/kindred` |
| `ulrich-energy` (Ulrich Energy (retired lineage)) | `archive` | meets declared class | `shaun` | `projects/ulrich-energy` |
| `reports` (Reports) | `archive` | meets declared class | `shaun` | `projects/reports` |

## Athanor Agents (`agents`)

- Class: `platform-core`
- Owner: `shaun`
- Workspace: `projects/agents`
- Declared requirements: `owner`, `workspace`, `ci`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `agent_server`
- CI workflow steps: `Agents contract`
- Acceptance workflow steps: `Platform contract validation`, `Agents contract`
- Docs: `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- CI commands:
  - `cd projects/agents && .\.venv\Scripts\python -m pytest tests\test_platform_contract.py tests\test_backbone.py tests\test_operator_tests.py tests\test_command_hierarchy.py tests\test_config_topology_defaults.py tests\test_scheduler.py -q`
- Acceptance gate:
  - `python scripts/validate_platform_contract.py`
  - `cd projects/agents && .\.venv\Scripts\python -m pytest tests -q`
- Notes: Primary control-plane runtime.
- Open issues: none

## Athanor Dashboard (`dashboard`)

- Class: `production-product`
- Owner: `shaun`
- Workspace: `projects/dashboard`
- Declared requirements: `owner`, `workspace`, `ci`, `docs`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `dashboard`
- CI workflow steps: `Dashboard contract`
- Acceptance workflow steps: `Dashboard contract`
- Docs: `projects/dashboard/README.md`, `projects/dashboard/docs/OPERATOR-ROUTE-CONTRACTS.md`, `docs/projects/PORTFOLIO-REGISTRY.md`
- CI commands:
  - `cd projects/dashboard && npm test`
  - `cd projects/dashboard && npm run typecheck`
  - `cd projects/dashboard && npm run build`
  - `cd projects/dashboard && npm run test:e2e:terminal`
- Acceptance gate:
  - `cd projects/dashboard && npm test`
  - `cd projects/dashboard && npm run typecheck`
  - `cd projects/dashboard && npm run build`
  - `cd projects/dashboard && npm run test:e2e:terminal`
- Notes: Authenticated operator console and main human-facing product surface.
- Open issues: none

## GPU Orchestrator (`gpu-orchestrator`)

- Class: `platform-core`
- Owner: `shaun`
- Workspace: `projects/gpu-orchestrator`
- Declared requirements: `owner`, `workspace`, `ci`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `gpu_orchestrator`
- CI workflow steps: `GPU orchestrator contract`
- Acceptance workflow steps: `GPU orchestrator contract`
- Docs: `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- CI commands:
  - `cd projects/gpu-orchestrator && .\.venv\Scripts\python -m pytest tests -q`
- Acceptance gate:
  - `cd projects/gpu-orchestrator && .\.venv\Scripts\python -m pytest tests -q`
- Notes: Privileged runtime placement and GPU control surface.
- Open issues: none

## WS PTY Bridge (`ws-pty-bridge`)

- Class: `platform-core`
- Owner: `shaun`
- Workspace: `projects/ws-pty-bridge`
- Declared requirements: `owner`, `workspace`, `ci`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `ws_pty_bridge`
- CI workflow steps: `WS PTY bridge contract`
- Acceptance workflow steps: `WS PTY bridge contract`
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- CI commands:
  - `cd projects/ws-pty-bridge && npm run ci`
- Acceptance gate:
  - `cd projects/ws-pty-bridge && npm run ci`
- Notes: Infrastructure bridge used by operator and agent workflows.
- Open issues: none

## Gateway (`gateway`)

- Class: `platform-core`
- Owner: `shaun`
- Workspace: `services/gateway`
- Declared requirements: `owner`, `workspace`, `ci`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `gateway`
- CI workflow steps: `Gateway contract`
- Acceptance workflow steps: `Gateway contract`
- Docs: `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- CI commands:
  - `python -m pytest services/gateway/tests -q`
- Acceptance gate:
  - `python -m pytest services/gateway/tests -q`
- Notes: Internal read-only health aggregation surface for cluster-wide service status.
- Open issues: none

## Quality Gate (`quality-gate`)

- Class: `platform-core`
- Owner: `shaun`
- Workspace: `services/quality-gate`
- Declared requirements: `owner`, `workspace`, `ci`, `env_example`, `monitoring`, `acceptance_gate`
- Monitoring: `quality_gate`
- CI workflow steps: `Quality gate contract`
- Acceptance workflow steps: `Quality gate contract`
- Docs: `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- CI commands:
  - `python -m pytest services/quality-gate/tests -q`
- Acceptance gate:
  - `python -m pytest services/quality-gate/tests -q`
- Notes: Privileged data-quality validation and destructive cleanup control surface.
- Open issues: none

## EOQ (`eoq`)

- Class: `active-scaffold`
- Owner: `shaun`
- Workspace: `projects/eoq`
- Declared requirements: `owner`, `workspace`, `env_example`, `explicit_status`
- Monitoring: none
- CI workflow steps: none
- Acceptance workflow steps: none
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- Notes: Active product lane but not yet under full production contract.
- Open issues: none

## ComfyUI Workflows (`comfyui-workflows`)

- Class: `active-scaffold`
- Owner: `shaun`
- Workspace: `projects/comfyui-workflows`
- Declared requirements: `owner`, `workspace`, `env_example`, `explicit_status`
- Monitoring: none
- CI workflow steps: none
- Acceptance workflow steps: none
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- Notes: Reusable workflow asset pack and creative scaffold surface.
- Open issues: none

## Kindred (`kindred`)

- Class: `incubation`
- Owner: `shaun`
- Workspace: `projects/kindred`
- Declared requirements: `owner`, `workspace`, `explicit_status`
- Monitoring: none
- CI workflow steps: none
- Acceptance workflow steps: none
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- Notes: Incubating product concept.
- Open issues: none

## Ulrich Energy (retired lineage) (`ulrich-energy`)

- Class: `archive`
- Owner: `shaun`
- Workspace: `projects/ulrich-energy`
- Declared requirements: `workspace`, `archive_note`
- Monitoring: none
- CI workflow steps: none
- Acceptance workflow steps: none
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- Notes: Retired lineage surface. The external Ulrich Energy Auditing Website is the only current delivery authority.
- Open issues: none

## Reports (`reports`)

- Class: `archive`
- Owner: `shaun`
- Workspace: `projects/reports`
- Declared requirements: `workspace`, `archive_note`
- Monitoring: none
- CI workflow steps: none
- Acceptance workflow steps: none
- Docs: `docs/projects/PORTFOLIO-REGISTRY.md`
- Notes: Output archive and report artifacts, not an active product runtime.
- Open issues: none
