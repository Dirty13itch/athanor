# Athanor Ecosystem Dependency Map

Do not edit manually.

Generated: `2026-04-16T23:58:13.741450+00:00`

## Current Sequence

1. `Letta Memory Plane`
2. `Agent Governance Toolkit Policy Plane`
3. `OpenHands Bounded Worker Lane`

## Typed Blockers

### Operator Input

- `Provider secret repair`: Repair or rotate the optional-elasticity provider keys on VAULT without treating them as switchover debt.
- `LETTA_API_KEY`: Wire LETTA_API_KEY only when the Letta pilot is intentionally reactivated.
- `OpenHands substrate readiness`: Repair the DESK WSL-first substrate only when the bounded worker pilot is intentionally reactivated.

### Runtime Input

- `OpenHands substrate readiness`: DESK substrate must be ready before the bounded worker lane activates.
- `Runtime mutation packets`: any future live runtime change still goes through explicit packet-backed execution.

### External Dependency

- Provider auth, billing posture, and SaaS health remain external even when they influence active lanes.

### Soft Blocker

- Stale generated reports reduce trust immediately even when the system is still nominally up.
- AGT stays below adapter work until it proves unique value over native Athanor policy.

### Non-Blocking Follow-On

- Tenant and product lanes remain segregated unless they leak back into Athanor core authority.
- Safe-surface work remains active but explicitly non-Athanor.

## Dependency Edges

| Upstream | Downstream | Type | Status | Why It Matters | Next Action |
| --- | --- | --- | --- | --- | --- |
| `cluster_and_host_substrate` | `athanor_core_adopted_system` | `runtime input` | `healthy` | Athanor runtime truth, service reachability, and host-role ownership depend on the cluster substrate. | Keep runtime mutations packet-backed and host truth current. |
| `external_providers_and_saas` | `athanor_core_adopted_system` | `external dependency` | `managed` | Provider auth, billing posture, and external SaaS uptime can degrade routing or pilot breadth. | Treat provider maintenance as explicit follow-on, not ambient assumption. |
| `artifact_and_evidence_systems` | `athanor_core_adopted_system` | `soft blocker` | `healthy` | Generated evidence is required to keep operator truth and validator posture coherent. | Refresh generated surfaces in canonical order whenever repo-tracked truth changes. |
| `operator_local_systems` | `athanor_core_adopted_system` | `soft blocker` | `healthy` | DESK/Codex-local control surfaces are how Shaun actually sees and operates the system. | Keep WSL-first tool parity and machine-level audits current. |
| `devstack_forge` | `athanor_core_adopted_system` | `hard blocker` | `governed` | Capabilities must graduate through packets and Athanor landing surfaces instead of leaking directly from devstack. | Promote only through explicit packets, proof, and adoption surfaces. |
| `human_approval_and_decision_gates` | `devstack_forge` | `operator input` | `active` | Future pilot activation depends on explicit operator inputs and approval posture. | Keep pending inputs explicit on the forge board and activation program. |
| `external_providers_and_saas` | `devstack_forge` | `operator input` | `active` | Letta and related pilots require real external credentials before proof can progress. | Provide LETTA_API_KEY only when the Letta lane is intentionally activated. |
| `cluster_and_host_substrate` | `devstack_forge` | `runtime input` | `active` | OpenHands depends on DESK substrate readiness before the bounded worker lane can run. | Repair DESK substrate only when the OpenHands pilot is intentionally activated. |
| `tenant_and_product_systems` | `athanor_core_adopted_system` | `non-blocking follow-on` | `segregated` | Tenant lanes stay visible but should not block Athanor core unless they leak authority back into it. | Keep tenant/product work packeted and segregated. |
| `operator_local_systems` | `devstack_forge` | `soft blocker` | `healthy` | The current devstack posture assumes WSL-first Codex execution and worktree-aware tooling. | Keep worktree lanes and Codex platform audits current. |

## Evidence Paths

- `/mnt/c/Athanor/docs/operations/STEADY-STATE-STATUS.md`
- `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- `/mnt/c/athanor-devstack/docs/operations/DEVSTACK-FORGE-BOARD.md`
- `/mnt/c/athanor-devstack/docs/operations/MASTER-ATLAS-REPORT.md`
- `/mnt/c/Codex System Config/docs/CORE-ROLLOUT-STATUS.md`
