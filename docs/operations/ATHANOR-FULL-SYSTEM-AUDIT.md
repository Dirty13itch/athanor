# Athanor Full-System Audit

Generated: `2026-04-16T21:43:45.718631+00:00`

## Executive Summary

- Adopted live system posture: closure=`repo_safe_complete` | active_claim=`Overnight Harvest` | runtime_packets=`0` | attention=`No action needed`
- Build/proving posture: turnover=`ready_for_low_touch_execution` | forge_top_lane=`letta-memory-plane` | atlas_top_lane=`codex_cloudsafe`
- Validator status: Athanor=`fail` | Devstack=`fail`
- Git posture: Athanor dirty=`2` | Devstack dirty=`84`
- Findings: critical=`0` | high=`3` | medium=`5` | low=`0`

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
- Devstack contract: `fail`
- Restart snapshot active claim: `burn_class:overnight_harvest`

## Subsystem Score Matrix

| Subsystem | Layer | Overall | Authority | Runtime | Visibility | Verification | Split-brain risk | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Athanor control plane and truth surfaces` | `adopted_live_system` | `3.2` | `3.0` | `2.5` | `2.0` | `3.5` | `medium` | `high` |
| `Runtime and deployment reality across nodes` | `adopted_live_system` | `4.4` | `5.0` | `3.5` | `5.0` | `3.5` | `low` | `high` |
| `Dashboard and operator product surfaces` | `adopted_live_system` | `4.2` | `3.0` | `5.0` | `3.0` | `5.0` | `low` | `medium` |
| `Agents and orchestration` | `adopted_live_system` | `4.6` | `5.0` | `4.0` | `4.0` | `5.0` | `low` | `medium` |
| `GPU orchestration, capacity, and burn truth` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `WS PTY bridge` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Legacy and shared service surfaces` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Providers, routing, and secrets` | `adopted_live_system` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Scripts, validators, generators, and tooling` | `adopted_live_system` | `4.4` | `5.0` | `3.5` | `5.0` | `3.5` | `low` | `high` |
| `Devstack forge, atlas, and queue truth` | `build_proving_system` | `3.2` | `1.0` | `5.0` | `3.0` | `3.5` | `medium` | `high` |
| `Devstack services and proving workflows` | `build_proving_system` | `4.4` | `3.5` | `5.0` | `5.0` | `5.0` | `low` | `high` |
| `Devstack packets and promotion surfaces` | `build_proving_system` | `3.4` | `1.0` | `5.0` | `4.0` | `3.5` | `medium` | `high` |
| `Adoption membrane between devstack and Athanor` | `membrane_and_adoption_boundary` | `3.2` | `1.0` | `5.0` | `3.0` | `3.5` | `medium` | `high` |
| `Strategic reservoir and capability universe coverage` | `strategic_reservoir` | `5.0` | `5.0` | `5.0` | `5.0` | `5.0` | `low` | `low` |
| `Operator communication and front-door UX` | `adopted_live_system` | `3.4` | `2.0` | `4.0` | `1.0` | `5.0` | `medium` | `medium` |

## Tool and Manifest Inventory

- Athanor top-level file counts: `{'projects': 1125, 'services': 49, 'scripts': 227, 'config': 82, 'docs': 319, 'reports': 200, 'ansible': 141, 'tests': 1, 'evals': 17}`
- Devstack top-level file counts: `{'services': 32, 'scripts': 28, 'configs': 26, 'docs': 24, 'reports': 21, 'research': 32, 'designs': 21, 'shipped': 7}`
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
- Scores: authority=`3.0` | runtime=`2.5` | visibility=`2.0` | verification=`3.5` | split-brain risk=`medium` | remediation priority=`high`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Findings:
  - [HIGH] The Athanor platform validator is currently red. Impact: The adopted live system is not at a clean report/contract fixed point, so current report surfaces cannot be treated as fully converged operational truth.
  - [MEDIUM] Ralph automation feedback is degraded even though the live lane is active. Impact: Autonomous execution can look healthy from the front door while the loop’s own feedback ledger still records repeated failures, which weakens confidence in unattended operation.
  - [MEDIUM] Athanor operator surfaces disagree on the active claim. Impact: The front door and the machine truth do not point at the same current work, which degrades operator trust and makes handoff decisions ambiguous.
  - [MEDIUM] Queue posture metrics diverge across Athanor operator surfaces. Impact: The system can report different dispatchable and suppressed counts depending on which surface the operator reads, which weakens the front-door contract.

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
- Scores: authority=`3.0` | runtime=`5.0` | visibility=`3.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`medium`
- Evidence:
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- Findings:
  - [MEDIUM] Athanor operator surfaces disagree on the active claim. Impact: The front door and the machine truth do not point at the same current work, which degrades operator trust and makes handoff decisions ambiguous.
  - [MEDIUM] Queue posture metrics diverge across Athanor operator surfaces. Impact: The system can report different dispatchable and suppressed counts depending on which surface the operator reads, which weakens the front-door contract.

## Agents and orchestration

- Authority layer: `adopted_live_system` (Adopted live system)
- Summary: The active claim is live and dispatchable, but Ralph feedback bookkeeping remains degraded.
- Scores: authority=`5.0` | runtime=`4.0` | visibility=`4.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`medium`
- Evidence:
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- Findings:
  - [MEDIUM] Ralph automation feedback is degraded even though the live lane is active. Impact: Autonomous execution can look healthy from the front door while the loop’s own feedback ledger still records repeated failures, which weakens confidence in unattended operation.

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
- Scores: authority=`1.0` | runtime=`5.0` | visibility=`3.0` | verification=`3.5` | split-brain risk=`medium` | remediation priority=`high`
- Evidence:
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
  - `/mnt/c/athanor-devstack/MASTER-PLAN.md`
- Findings:
  - [HIGH] The devstack repo currently carries a large unpublished dirty tranche. Impact: Capability-forge truth, packet state, and proving surfaces are mixed with broad in-flight changes, which raises shadow-authority and auditability risk at the adoption membrane.
  - [HIGH] The devstack contract validator is currently red. Impact: Build/proving truth is not internally clean, so forge execution, packet posture, and readiness claims cannot be treated as fully trustworthy without caveats.
  - [MEDIUM] The devstack atlas and forge board disagree on the top-priority lane. Impact: Operators can receive two different answers about what the build system should do next, which weakens queue authority and packet sequencing.
  - [MEDIUM] Devstack turnover posture appears overstated relative to validator and repo state. Impact: The atlas advertises low-touch execution readiness while the forge contract is red and the repo is broadly dirty, which can make adoption timing look safer than it is.

## Devstack services and proving workflows

- Authority layer: `build_proving_system` (Build/proving system)
- Summary: Proving lanes are explicit, but broad repo dirt reduces confidence in the current build-system snapshot.
- Scores: authority=`3.5` | runtime=`5.0` | visibility=`5.0` | verification=`5.0` | split-brain risk=`low` | remediation priority=`high`
- Evidence:
  - `/mnt/c/athanor-devstack/MASTER-PLAN.md`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings:
  - [HIGH] The devstack repo currently carries a large unpublished dirty tranche. Impact: Capability-forge truth, packet state, and proving surfaces are mixed with broad in-flight changes, which raises shadow-authority and auditability risk at the adoption membrane.

## Devstack packets and promotion surfaces

- Authority layer: `build_proving_system` (Build/proving system)
- Summary: Promotion and packet posture are visible, but they inherit forge-board staleness and priority ambiguity.
- Scores: authority=`1.0` | runtime=`5.0` | visibility=`4.0` | verification=`3.5` | split-brain risk=`medium` | remediation priority=`high`
- Evidence:
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings:
  - [HIGH] The devstack repo currently carries a large unpublished dirty tranche. Impact: Capability-forge truth, packet state, and proving surfaces are mixed with broad in-flight changes, which raises shadow-authority and auditability risk at the adoption membrane.
  - [HIGH] The devstack contract validator is currently red. Impact: Build/proving truth is not internally clean, so forge execution, packet posture, and readiness claims cannot be treated as fully trustworthy without caveats.
  - [MEDIUM] The devstack atlas and forge board disagree on the top-priority lane. Impact: Operators can receive two different answers about what the build system should do next, which weakens queue authority and packet sequencing.

## Adoption membrane between devstack and Athanor

- Authority layer: `membrane_and_adoption_boundary` (Membrane and adoption boundary)
- Summary: The membrane model is explicit, but dirty devstack state and turnover overstatement still increase shadow-authority risk.
- Scores: authority=`1.0` | runtime=`5.0` | visibility=`3.0` | verification=`3.5` | split-brain risk=`medium` | remediation priority=`high`
- Evidence:
  - `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
  - `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
  - `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- Findings:
  - [HIGH] The devstack repo currently carries a large unpublished dirty tranche. Impact: Capability-forge truth, packet state, and proving surfaces are mixed with broad in-flight changes, which raises shadow-authority and auditability risk at the adoption membrane.
  - [HIGH] The devstack contract validator is currently red. Impact: Build/proving truth is not internally clean, so forge execution, packet posture, and readiness claims cannot be treated as fully trustworthy without caveats.
  - [MEDIUM] The devstack atlas and forge board disagree on the top-priority lane. Impact: Operators can receive two different answers about what the build system should do next, which weakens queue authority and packet sequencing.
  - [MEDIUM] Devstack turnover posture appears overstated relative to validator and repo state. Impact: The atlas advertises low-touch execution readiness while the forge contract is red and the repo is broadly dirty, which can make adoption timing look safer than it is.

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
- Scores: authority=`2.0` | runtime=`4.0` | visibility=`1.0` | verification=`5.0` | split-brain risk=`medium` | remediation priority=`medium`
- Evidence:
  - `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
  - `/mnt/c/Athanor/reports/ralph-loop/latest.json`
  - `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- Findings:
  - [MEDIUM] Ralph automation feedback is degraded even though the live lane is active. Impact: Autonomous execution can look healthy from the front door while the loop’s own feedback ledger still records repeated failures, which weakens confidence in unattended operation.
  - [MEDIUM] Athanor operator surfaces disagree on the active claim. Impact: The front door and the machine truth do not point at the same current work, which degrades operator trust and makes handoff decisions ambiguous.
  - [MEDIUM] Queue posture metrics diverge across Athanor operator surfaces. Impact: The system can report different dispatchable and suppressed counts depending on which surface the operator reads, which weakens the front-door contract.
  - [MEDIUM] Devstack turnover posture appears overstated relative to validator and repo state. Impact: The atlas advertises low-touch execution readiness while the forge contract is red and the repo is broadly dirty, which can make adoption timing look safer than it is.

## Prioritized Remediation Backlog

- `high` `operation` — The Athanor platform validator is currently red. Fix: Regenerate the stale publication and ownership reports in canonical order and re-run the platform validator until it is green before declaring the live report set converged.
- `high` `adoption` — The devstack repo currently carries a large unpublished dirty tranche. Fix: Slice the devstack dirty tranche into explicit publication checkpoints or packet-backed work bundles and keep forge/atlas truth isolated from exploratory edits.
- `high` `adoption` — The devstack contract validator is currently red. Fix: Regenerate the forge board JSON and markdown from the current lane registry and forge loop until validate_devstack_contract.py passes, then re-audit readiness against the refreshed board.
- `medium` `trust` — Ralph automation feedback is degraded even though the live lane is active. Fix: Audit Ralph automation failure bookkeeping so claimed or already-dispatched runs do not accumulate as degraded failures when the live lane is otherwise healthy.
- `medium` `trust` — Athanor operator surfaces disagree on the active claim. Fix: Make finish-scoreboard and restart snapshot derive the active claim from the same Ralph claim surface used by steady-state status, or explicitly mark lagging/closure-only state as non-authoritative for live work.
- `medium` `trust` — Queue posture metrics diverge across Athanor operator surfaces. Fix: Normalize queue summary derivation so finish-scoreboard, Ralph latest, restart snapshot, and steady-state status all compute dispatchable and suppressed counts from the same queue snapshot.
- `medium` `trust` — The devstack atlas and forge board disagree on the top-priority lane. Fix: Choose one source as the canonical top-priority-lane owner and derive the other from it, or explicitly distinguish routing-profile priority from lane-id priority.
- `medium` `adoption` — Devstack turnover posture appears overstated relative to validator and repo state. Fix: Gate turnover-ready posture on a clean devstack contract pass and a bounded dirty-tranche threshold, or explicitly downgrade turnover posture when either condition is violated.
