# Athanor Ecosystem Master Plan

Do not edit manually.


## Current Ecosystem Truth

### Live

- Athanor adopted system is `repo_safe_complete` with operator mode `steady_state_monitoring`.
- Live claim rotation, queue posture, and packet inbox state are carried by `/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md` and `reports/ralph-loop/latest.json`.
- The canonical command center remains `https://athanor.local/`.

### Proved

- Devstack turnover status is `devstack_primary_build_and_shadow`.
- Devstack top packet-drafting lane is `migration-hygiene`.
- Atlas tracks `10` capabilities with `7` adopted and `2` concept lanes.

### Adopted

- Athanor core closure is `repo_safe_complete`.
- Atlas-adopted capability set currently includes `Agent Gateway Layer, GraphRAG Hybrid Retrieval, Watchdog Runtime Guard, GPU Scheduler Extension, Creative Identity Pipeline, Goose Operator Shell`.

### Local-Only

- Codex System Config remains the operator-local control plane for machine defaults, worktrees, and rollout audits.
- Safe-surface executive loop currently tracks `41` non-Athanor queue items and keeps Athanor-adjacent paths denied by default.

### External-Only

- Provider usage evidence currently records `170` provider capture rows.
- Planned subscription evidence currently records `2` subscription evidence rows.
- External provider auth, billing, and SaaS uptime remain outside Athanor authority even when they affect execution.

### Blocked By Human or Operator Input

- No explicit operator-input blockers are currently recorded.

## Ownership Model

| Domain | Owner | State Class | Current State | Blockers | Next Maturity Move |
| --- | --- | --- | --- | --- | --- |
| `Athanor core adopted system` | `C:/Athanor` | `adopted` | Core posture is `repo_safe_complete` with `steady_state_monitoring`; live claim, queue posture, and packet inbox state are intentionally carried by the ignored live operator feed and machine JSON surfaces. | none | Keep the steady-state control-plane pass green and reopen only on typed debt, packet, or validator evidence. |
| `devstack forge` | `C:/athanor-devstack` | `proving` | Turnover is `devstack_primary_build_and_shadow`; current top lane and packet drafting flow are carried live by the forge board and atlas surfaces. | none | Advance the next bounded promotion lane through proof, packet, and Athanor landing surfaces without leaking build truth into runtime truth. |
| `cluster and host substrate` | `FOUNDRY / WORKSHOP / VAULT / DEV / DESK` | `runtime` | Topology tracks `5` nodes; atlas harvest posture is `open_harvest_window` and work-economy posture is `ready`. | none | Keep runtime mutations packet-backed, preserve host-role clarity, and only widen pilot substrate work when a specific activation lane needs it. |
| `operator-local systems` | `C:/Users/Shaun/.codex and C:/Codex System Config` | `local_only` | Codex System Config is the machine-level control plane, WSL-first execution is the default, and the safe-surface loop remains explicitly non-Athanor by policy. | none | Keep worktree audits, WSL tooling parity, and machine-level control proof current without letting global defaults absorb repo-local truth. |
| `external providers and SaaS` | `External APIs, billing systems, and SaaS control planes` | `external` | Provider evidence is explicit with `170` usage captures and `2` planned-subscription captures; optional elasticity maintenance remains externalized rather than core-blocking. | none | Keep provider proof current, rotate or repair keys only when a live lane or pilot actually requires the expanded surface, and avoid treating optional elasticity as core blockage. |
| `artifact and evidence systems` | `Generated reports, docs, local artifacts, and audit traces` | `evidence` | Generated evidence covers capacity (`2026-04-11.1`), quota (`2026-04-12.1`), audit, steady-state, forge, and atlas surfaces. | none | Keep evidence regenerated in canonical order and make stale generated docs a hard trust signal rather than background noise. |
| `tenant and product systems` | `Registry-backed tenant roots and adjacent products` | `segregated` | Registry-backed tenant and adjacent roots remain segregated; current tenant source ids include `brayburn-trails-hoa-website, codexbuild-rfi-hers-rater-assistant, codexbuild-rfi-hers-rater-assistant-safe, codexbuild-rfi-hers-rater-assistant-v2, codexbuild-rfi-hers-stabilization-review, field-inspect-operations-runtime`. | none | Keep tenant lanes visible but non-blocking unless they leak back into Athanor startup, runtime, queue, or operator surfaces. |
| `human approval and decision gates` | `Shaun` | `approval` | Approvals stay explicit and lane-specific; live attention posture and pending gates surface through the live operator feed, steady-state JSON, and forge deferred inputs. | none | Keep approvals explicit and lane-specific: only elevate them when a bounded runtime mutation, credential gate, or pilot activation is intentionally being executed. |

## Active Execution Lanes

- Live Athanor execution rotates through `/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md` and `/mnt/c/Athanor/reports/ralph-loop/latest.json`.
- The strategic next-adoption order is the activation program below, not the transient current claim ticker.
- The current devstack proving lane remains visible on `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` and `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`.
- Safe-surface work remains a separate non-Athanor queue governed by the operator-local control plane.


## Activation Program

| Order | Lane | Why Now | Prerequisites | Proof Surfaces | Acceptance | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| `1` | `Letta Memory Plane` | It is the top devstack packet-drafting lane and the clearest next memory-plane expansion path. | LETTA_API_KEY, bounded continuity benchmark | `C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md`, `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`, `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md` | Credential is present, bounded continuity benchmark passes, packet proof is updated, and the Athanor landing surfaces remain explicit and replayable. | Disable the Letta lane and fall back to the current Athanor memory posture. |
| `2` | `Agent Governance Toolkit Policy Plane` | It is the next governance-plane candidate, but it should remain below adapter work until it proves unique value. | second protocol-boundary scenario, formal eval progression | `C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md`, `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md` | A second protocol-boundary scenario demonstrates non-duplicative value, proof artifacts are updated, and a bounded Athanor landing plan exists. | Do not land a live adapter; keep governance in native Athanor policy. |
| `3` | `OpenHands Bounded Worker Lane` | It is the next worker-plane candidate but remains substrate-blocked until DESK can host the bounded worker path cleanly. | OpenHands command on DESK, worker env wiring, bounded worker eval | `C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md`, `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` | DESK substrate is ready, the bounded-worker eval passes, and the lane can be disabled cleanly if it misbehaves. | Disable the worker lane and fall back to the existing manual/operator workflow. |

## Operator Model

- Front door: `Athanor Command Center` at `https://athanor.local/`.
- First read: `reports/truth-inventory/steady-state-live.md`.
- Stable operator contract: `docs/operations/STEADY-STATE-STATUS.md`.
- Cross-system read: `docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md`.
- Build/proving read: `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` and `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`.
- Deep proof: drop to the JSON artifacts only when summary surfaces contradict or you need exact evidence.

## Longer-Horizon Ecosystem Maturation

- `memory plane`: Letta remains the next memory-plane candidate but is still operator-input gated. Next move: Prove bounded continuity gain with explicit pruning and replayability.
- `governance plane`: Native Athanor governance remains primary; AGT is still a proving-only candidate. Next move: Reopen only if a second protocol-boundary scenario proves non-duplicative value.
- `worker plane`: Bounded worker expansion is still substrate-blocked on DESK. Next move: Repair OpenHands substrate only when the lane is intentionally activated.
- `creative/runtime maturity`: Cluster substrate and harvest posture are healthy enough to support broader proving work. Next move: Protect runtime ownership clarity while widening only packet-backed lanes.
- `provider/routing maturity`: Provider evidence is explicit; optional elasticity maintenance remains separated from core health. Next move: Keep billing and auth posture explicit and avoid hidden provider assumptions.
- `tenant/product governance`: Tenant and product roots are visible and segregated rather than merged into Athanor core. Next move: Advance only bounded extractions or packet-backed reopenings.
- `cluster/hardware evolution`: Node roles and scheduler posture are explicit enough for current operation. Next move: Change hardware or runtime posture only through topology truth, runtime packets, and explicit proof.

## Source Layers

- `athanor_status`: `/mnt/c/Athanor/STATUS.md`
- `athanor_backlog`: `/mnt/c/Athanor/docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`
- `layered_plan`: `/mnt/c/Athanor/docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md`
- `steady_state_status`: `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- `finish_scoreboard`: `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- `runtime_packet_inbox`: `/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json`
- `ralph_latest`: `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- `platform_topology`: `/mnt/c/Athanor/config/automation-backbone/platform-topology.json`
- `operator_surface_registry`: `/mnt/c/Athanor/config/automation-backbone/operator-surface-registry.json`
- `project_packet_registry`: `/mnt/c/Athanor/config/automation-backbone/project-packet-registry.json`
- `reconciliation_source_registry`: `/mnt/c/Athanor/config/automation-backbone/reconciliation-source-registry.json`
- `provider_usage_evidence`: `/mnt/c/Athanor/reports/truth-inventory/provider-usage-evidence.json`
- `planned_subscription_evidence`: `/mnt/c/Athanor/reports/truth-inventory/planned-subscription-evidence.json`
- `quota_truth`: `/mnt/c/Athanor/reports/truth-inventory/quota-truth.json`
- `capacity_telemetry`: `/mnt/c/Athanor/reports/truth-inventory/capacity-telemetry.json`
- `devstack_status`: `/mnt/c/athanor-devstack/STATUS.md`
- `devstack_master_plan`: `/mnt/c/athanor-devstack/MASTER-PLAN.md`
- `devstack_forge_board`: `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.json`
- `devstack_forge_board_md`: `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`
- `devstack_master_atlas`: `/mnt/c/athanor-devstack/reports/master-atlas/latest.json`
- `devstack_master_atlas_md`: `/mnt/c/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`
- `devstack_lane_registry`: `/mnt/c/athanor-devstack/configs/devstack-capability-lane-registry.json`
- `codex_status`: `/mnt/c/Codex System Config/STATUS.md`
- `codex_project`: `/mnt/c/Codex System Config/PROJECT.md`
- `codex_next_steps`: `/mnt/c/Codex System Config/docs/CODEX-NEXT-STEPS.md`
- `safe_surface_scope`: `/mnt/c/Users/Shaun/.codex/control/safe-surface-scope.md`
- `safe_surface_policy`: `/mnt/c/Users/Shaun/.codex/control/safe-surface-policy.md`
- `safe_surface_queue`: `/mnt/c/Users/Shaun/.codex/control/safe-surface-queue.json`
- `safe_surface_state`: `/mnt/c/Users/Shaun/.codex/control/safe-surface-state.json`
