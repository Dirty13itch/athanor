# Athanor Ecosystem Master Plan

Do not edit manually.


## Current Ecosystem Truth

### Live

- Athanor adopted system is `closure_in_progress` with operator mode `active_closure`.
- Current governed work is `Validation and Publication` and the next staged handoff is `Reference and Archive Prune`.
- Runtime packet inbox currently holds `0` packets.
- The canonical command center is `https://athanor.local/`.

### Proved

- Devstack turnover status is `ready_for_low_touch_execution`.
- Devstack top packet-drafting lane is `letta-memory-plane`.
- Atlas tracks `9` capabilities with `6` adopted and `3` concept lanes.

### Adopted

- Athanor core closure is `closure_in_progress`.
- Atlas-adopted capability set currently includes `Agent Gateway Layer, GraphRAG Hybrid Retrieval, Watchdog Runtime Guard, GPU Scheduler Extension, Creative Identity Pipeline, Goose Operator Shell`.

### Local-Only

- Codex System Config remains the operator-local control plane for machine defaults, worktrees, and rollout audits.
- Safe-surface executive loop currently tracks `27` non-Athanor queue items and keeps Athanor-adjacent paths denied by default.

### External-Only

- Provider usage evidence currently records `170` provider capture rows.
- Planned subscription evidence currently records `2` subscription evidence rows.
- External provider auth, billing, and SaaS uptime remain outside Athanor authority even when they affect execution.

### Blocked By Human or Operator Input

- Provider secret repair: Repair or rotate the optional-elasticity provider keys on VAULT without treating them as switchover debt.
- LETTA_API_KEY: Wire LETTA_API_KEY only when the Letta pilot is intentionally reactivated.
- OpenHands substrate readiness: Repair the DESK WSL-first substrate only when the bounded worker pilot is intentionally reactivated.

## Ownership Model

| Domain | Owner | State Class | Current State | Blockers | Next Maturity Move |
| --- | --- | --- | --- | --- | --- |
| `Athanor core adopted system` | `C:/Athanor` | `adopted` | Core posture is `closure_in_progress` with `active_closure`; current governed claim is `Validation and Publication` and the runtime inbox is `0`. | none | Keep the steady-state control-plane pass green and reopen only on typed debt, packet, or validator evidence. |
| `devstack forge` | `C:/athanor-devstack` | `proving` | Turnover is `ready_for_low_touch_execution`, top lane is `letta-memory-plane`, and packet drafting lanes total `3`. | Provider secret repair, LETTA_API_KEY, OpenHands substrate readiness | Advance the next bounded promotion lane through proof, packet, and Athanor landing surfaces without leaking build truth into runtime truth. |
| `cluster and host substrate` | `FOUNDRY / WORKSHOP / VAULT / DEV / DESK` | `runtime` | Topology tracks `5` nodes; atlas harvest posture is `open_harvest_window` and work-economy posture is `ready`. | OpenHands substrate readiness on DESK | Keep runtime mutations packet-backed, preserve host-role clarity, and only widen pilot substrate work when a specific activation lane needs it. |
| `operator-local systems` | `C:/Users/Shaun/.codex and C:/Codex System Config` | `local_only` | Codex System Config is the machine-level control plane, WSL-first execution is the default, and the safe-surface loop remains explicitly non-Athanor by policy. | none | Keep worktree audits, WSL tooling parity, and machine-level control proof current without letting global defaults absorb repo-local truth. |
| `external providers and SaaS` | `External APIs, billing systems, and SaaS control planes` | `external` | Provider evidence is explicit with `170` usage captures and `2` planned-subscription captures; optional elasticity maintenance remains externalized rather than core-blocking. | Provider secret repair | Keep provider proof current, rotate or repair keys only when a live lane or pilot actually requires the expanded surface, and avoid treating optional elasticity as core blockage. |
| `artifact and evidence systems` | `Generated reports, docs, local artifacts, and audit traces` | `evidence` | Generated evidence covers capacity (`2026-04-11.1`), quota (`2026-04-12.1`), audit, steady-state, forge, and atlas surfaces. | none | Keep evidence regenerated in canonical order and make stale generated docs a hard trust signal rather than background noise. |
| `tenant and product systems` | `Registry-backed tenant roots and adjacent products` | `segregated` | Registry-backed tenant and adjacent roots remain segregated; current tenant source ids include `brayburn-trails-hoa-website, codexbuild-rfi-hers-rater-assistant, codexbuild-rfi-hers-rater-assistant-safe, codexbuild-rfi-hers-rater-assistant-v2, codexbuild-rfi-hers-stabilization-review, field-inspect-operations-runtime`. | none | Keep tenant lanes visible but non-blocking unless they leak back into Athanor startup, runtime, queue, or operator surfaces. |
| `human approval and decision gates` | `Shaun` | `approval` | Core Athanor does not currently need intervention (`Review recommended`), but explicit approval and operator-input gates remain on future activation lanes. | Provider secret repair, LETTA_API_KEY, OpenHands substrate readiness | Keep approvals explicit and lane-specific: only elevate them when a bounded runtime mutation, credential gate, or pilot activation is intentionally being executed. |

## Active Execution Lanes

- Running now: Athanor is on `Validation and Publication`.
- Next in Athanor: `Reference and Archive Prune`.
- Next in devstack: `letta-memory-plane`.
- Safe-surface queue count: `27` with last outcome `idle`.

### Recent Activity

- `Validation and Publication` | `validation_and_checkpoint` | Current governed dispatch claim.
- `Validation and Publication` | `ralph_loop` | Ralph loop selected dispatch-and-work-economy-closure under governor_scheduling with evidence fresh and claim workstream:validation-and-publication via already_dispatched.
- `Audit and Eval Artifacts` | `ralph_loop` | Ralph loop selected dispatch-and-work-economy-closure under governor_scheduling with evidence fresh and claim deferred_family:audit-and-eval-artifacts via already_dispatched.
- `Operator Tooling and Helper Surfaces` | `ralph_loop` | Ralph loop selected dispatch-and-work-economy-closure under governor_scheduling with evidence fresh and claim deferred_family:operator-tooling-and-helper-surfaces via already_dispatched.

## Activation Program

| Order | Lane | Why Now | Prerequisites | Proof Surfaces | Acceptance | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| `1` | `Letta Memory Plane` | It is the top devstack packet-drafting lane and the clearest next memory-plane expansion path. | continuity-gain-unproven, formal_eval_run, release_tier_progression | `C:/athanor-devstack/docs/promotion-packets/letta-memory-plane.md`, `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`, `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md` | Credential is present, bounded continuity benchmark passes, packet proof is updated, and the Athanor landing surfaces remain explicit and replayable. | Disable the pilot memory adapter and keep durable context on the current registry, packet, and repo-doc stack only. |
| `2` | `Agent Governance Toolkit Policy Plane` | It is the next governance-plane candidate, but it should remain below adapter work until it proves unique value. | policy-bridge-slice-unproven, formal_eval_run, release_tier_progression | `C:/athanor-devstack/docs/promotion-packets/agent-governance-toolkit-policy-plane.md`, `C:/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md` | A second protocol-boundary scenario demonstrates non-duplicative value, proof artifacts are updated, and a bounded Athanor landing plan exists. | Remove the AGT adapter or policy bridge and fall back to the existing Athanor approval, routing, and failure-governance contracts. |
| `3` | `OpenHands Bounded Worker Lane` | It is the next worker-plane candidate but remains substrate-blocked until DESK can host the bounded worker path cleanly. | bounded-worker-value-unproven, formal_eval_run, release_tier_progression | `C:/athanor-devstack/docs/promotion-packets/openhands-bounded-worker-lane.md`, `C:/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md` | DESK substrate is ready, the bounded-worker eval passes, and the lane can be disabled cleanly if it misbehaves. | Demote OpenHands back to research-only status, remove it from preferred lane-selection output, and keep its artifacts as devstack-only pilot evidence. |

## Operator Model

- Front door: `Athanor Command Center` at `https://athanor.local/`.
- First read: `docs/operations/STEADY-STATE-STATUS.md`.
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
