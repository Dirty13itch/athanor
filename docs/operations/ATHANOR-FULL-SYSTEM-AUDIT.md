# Athanor Full-System Audit

Generated: `2026-04-16T22:55:23.152338+00:00`

## Executive Summary

- Adopted live system posture: closure=`closure_in_progress` | active_claim=`Validation and Publication` | runtime_packets=`0` | attention=`Review recommended`
- Build/proving posture: turnover=`ready_for_low_touch_execution` | forge_top_lane=`letta-memory-plane` | atlas_top_lane=`letta-memory-plane` | atlas_routing_lane=`codex_cloudsafe`
- Validator status: Athanor=`fail` | Devstack=`pass`
- Git posture: Athanor dirty=`6` | Devstack dirty=`8`
- Findings: critical=`0` | high=`1` | medium=`0` | low=`0`

## Audit Coverage

- Required subsystems covered: `True`
- Authority layers covered: `['adopted_live_system', 'build_proving_system', 'membrane_and_adoption_boundary', 'strategic_reservoir']`
- Authority layer counts: `{'adopted_live_system': 10, 'build_proving_system': 3, 'membrane_and_adoption_boundary': 1, 'strategic_reservoir': 1}`
- Athanor major subsystem paths present: `{'dashboard': True, 'agents': True, 'gpu_orchestrator': True, 'ws_pty_bridge': True, 'legacy_services': True}`
- Devstack major subsystem paths present: `{'forge_board': True, 'master_atlas': True, 'promotion_packets': True, 'services': True, 'research': True, 'designs': True}`

## Source Layers

- `athanor_backlog`: `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- `athanor_layered_plan`: `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- `ralph_latest`: `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- `finish_scoreboard`: `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- `runtime_packet_inbox`: `/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json`
- `steady_state_status`: `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- `devstack_master_plan`: `/mnt/c/athanor-devstack/MASTER-PLAN.md`
- `devstack_atlas`: `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
- `devstack_forge_board`: `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- `devstack_forge_board_md`: `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`

## Check Status

- Athanor platform contract: `fail`
- Devstack contract: `pass`
- Restart snapshot active claim: `workstream:validation-and-publication`

## Subsystem Score Matrix

| Subsystem | Layer | Overall | Authority | Runtime | Visibility | Verification | Split-brain risk | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Athanor control plane and truth surfaces` | `adopted_live_system` | `4.4` | `5.0` | `3.5` | `5.0` | `3.5` | `low` | `high` |
| `Runtime and deployment reality across nodes` | `adopted_live_system` | `4.4` | `5.0` | `3.5` | `5.0` | `3.5` | `low` | `high` |
| `Dashboard and operator product surfaces` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Agents and orchestration` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `GPU orchestration, capacity, and burn truth` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `WS PTY bridge` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Legacy and shared service surfaces` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Providers, routing, and secrets` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Scripts, validators, generators, and tooling` | `adopted_live_system` | `4.4` | `5.0` | `3.5` | `5.0` | `3.5` | `low` | `high` |
| `Devstack forge, atlas, and queue truth` | `build_proving_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Devstack services and proving workflows` | `build_proving_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Devstack packets and promotion surfaces` | `build_proving_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Adoption membrane between devstack and Athanor` | `membrane_and_adoption_boundary` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Strategic reservoir and capability universe coverage` | `strategic_reservoir` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Operator communication and front-door UX` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |

## Tool and Manifest Inventory

- Athanor top-level file counts: `{'projects': 1125, 'services': 49, 'scripts': 227, 'config': 82, 'docs': 322, 'reports': 203, 'ansible': 141, 'tests': 1, 'evals': 17}`
- Devstack top-level file counts: `{'services': 32, 'scripts': 29, 'configs': 26, 'docs': 25, 'reports': 22, 'research': 32, 'designs': 21, 'shipped': 7}`
- Athanor manifests:
  - `projects/agents/docker-compose.yml`
  - `projects/agents/pyproject.toml`
  - `projects/agents/watchdog/docker-compose.yml`
  - `projects/agents/watchdog/requirements.txt`
  - `projects/dashboard/docker-compose.yml`
  - `projects/dashboard/package.json`
  - `projects/eoq/mcp-renpy/package.json`
  - `projects/eoq/package.json`
  - `projects/gpu-orchestrator/docker-compose.yml`
  - `projects/gpu-orchestrator/pyproject.toml`
  - `projects/kindred/package.json`
  - `projects/ulrich-energy/package.json`
  - `projects/ws-pty-bridge/package.json`
  - `scripts/requirements-test.txt`
  - `services/brain/requirements.txt`
  - `services/gateway/requirements-test.txt`
  - `services/governor/requirements-test.txt`
  - `services/quality-gate/requirements.txt`
  - `services/sentinel/requirements.txt`
- Devstack manifests:
  - `services/graphrag/docker-compose.yml`
  - `services/graphrag/requirements.txt`
  - `services/watchdog/docker-compose.yml`
  - `services/watchdog/requirements.txt`

## Athanor control plane and truth surfaces

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Closure is complete, but active-claim and queue metrics still diverge across machine and human surfaces.
- Scores: authority=`5.0` | runtime=`3.5` | visibility=`5.0` | verification=`3.5` | split-brain risk=`low` | remediation priority=`high`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Findings:
  - [HIGH] The Athanor platform validator is currently red. Impact: The adopted live system is not at a clean report/contract fixed point, so current report surfaces cannot be treated as fully converged operational truth.

## Runtime and deployment reality across nodes

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Runtime packets are clear and the live lane is active, but validator drift still affects trust in the current report set.
- Scores: authority=`5.0` | runtime=`3.5` | visibility=`5.0` | verification=`3.5` | split-brain risk=`low` | remediation priority=`high`
- Evidence:
  - `/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- Findings:
  - [HIGH] The Athanor platform validator is currently red. Impact: The adopted live system is not at a clean report/contract fixed point, so current report surfaces cannot be treated as fully converged operational truth.

## Dashboard and operator product surfaces

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: The front door is materially better, but it still depends on lower control-plane surfaces converging cleanly.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- Findings: none materialized from the current truth surfaces.

## Agents and orchestration

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: The active claim is live and dispatchable, but Ralph feedback bookkeeping remains degraded.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- Findings: none materialized from the current truth surfaces.

## GPU orchestration, capacity, and burn truth

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Capacity posture is explicit and harvest-ready, with no critical blocker visible in current truth surfaces.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Findings: none materialized from the current truth surfaces.

## WS PTY bridge

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: The PTY bridge is present as an adopted subsystem and currently has no distinct audit finding from the live truth bundle.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Findings: none materialized from the current truth surfaces.

## Legacy and shared service surfaces

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Shared services remain in scope and visible, with no separate critical divergence materialized from the current audit bundle.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- Findings: none materialized from the current truth surfaces.

## Providers, routing, and secrets

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Provider and secret posture are mostly explicit, with no current finding showing hidden routing debt.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Findings: none materialized from the current truth surfaces.

## Scripts, validators, generators, and tooling

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: The toolchain is strong, but the Athanor validator is currently red on stale generated docs.
- Scores: authority=`5.0` | runtime=`3.5` | visibility=`5.0` | verification=`3.5` | split-brain risk=`low` | remediation priority=`high`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- Findings:
  - [HIGH] The Athanor platform validator is currently red. Impact: The adopted live system is not at a clean report/contract fixed point, so current report surfaces cannot be treated as fully converged operational truth.

## Devstack forge, atlas, and queue truth

- Authority layer: `build_proving_system` (Build/proving system)
- Summary: Devstack has strong capability truth surfaces, but the forge board is stale and priority ownership is inconsistent.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
  - `/mnt/c/athanor-devstack/MASTER-PLAN.md`
- Findings: none materialized from the current truth surfaces.

## Devstack services and proving workflows

- Authority layer: `build_proving_system` (Build/proving system)
- Summary: Proving lanes are explicit, but broad repo dirt reduces confidence in the current build-system snapshot.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/athanor-devstack/MASTER-PLAN.md`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings: none materialized from the current truth surfaces.

## Devstack packets and promotion surfaces

- Authority layer: `build_proving_system` (Build/proving system)
- Summary: Promotion and packet posture are visible, but they inherit forge-board staleness and priority ambiguity.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings: none materialized from the current truth surfaces.

## Adoption membrane between devstack and Athanor

- Authority layer: `membrane_and_adoption_boundary` (Membrane and adoption boundary)
- Summary: The membrane model is explicit, but dirty devstack state and turnover overstatement still increase shadow-authority risk.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings: none materialized from the current truth surfaces.

## Strategic reservoir and capability universe coverage

- Authority layer: `strategic_reservoir` (Strategic reservoir)
- Summary: The strategic universe is broad and useful for completeness, but it must remain non-authoritative for live-state conclusions.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/athanor-devstack/MASTER-PLAN.md`
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- Findings: none materialized from the current truth surfaces.

## Operator communication and front-door UX

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: Operator visibility is improved and actionable, but surface divergence still needs one more normalization pass.
- Scores: authority=`5.0` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`low`
- Evidence:
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- Findings: none materialized from the current truth surfaces.

## Prioritized Remediation Backlog

- `high` `operation` — The Athanor platform validator is currently red. Fix: Regenerate the stale publication and ownership reports in canonical order and re-run the platform validator until it is green before declaring the live report set converged.
