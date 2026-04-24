# Publication Deferred-Family Queue

- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `316`
- Slice-matched entries: `228`
- Deferred-family entries: `0`
- Deferred families: `10`

## Ordered Queue

| Rank | Family | Class | Dirty matches | Disposition | Owner workstreams |
| --- | --- | --- | --- | --- | --- |
| `1` | `reference-and-archive-prune` | `cash_now` | `0` | `archive_or_reference` | `startup-docs-and-prune, validation-and-publication` |
| `2` | `operator-tooling-and-helper-surfaces` | `cash_now` | `0` | `operator_tooling` | `authority-and-mainline, startup-docs-and-prune` |
| `3` | `audit-and-eval-artifacts` | `cash_now` | `0` | `audit_artifact` | `validation-and-publication, startup-docs-and-prune` |
| `4` | `deployment-authority-follow-on` | `bounded_follow_on` | `0` | `deferred_out_of_sequence` | `deployment-authority-reconciliation, validation-and-publication` |
| `5` | `runtime-service-follow-on` | `bounded_follow_on` | `0` | `runtime_follow_on` | `runtime-sync-and-governed-packets, validation-and-publication` |
| `6` | `control-plane-registry-and-routing` | `program_slice` | `0` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |
| `7` | `agent-execution-kernel-follow-on` | `program_slice` | `0` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |
| `7` | `tenant-product-lanes` | `tenant_lane` | `0` | `tenant_surface` | `tenant-architecture-and-classification, validation-and-publication` |
| `8` | `agent-route-contract-follow-on` | `program_slice` | `0` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |
| `9` | `control-plane-proof-and-ops-follow-on` | `program_slice` | `0` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |

## 1. Reference and Archive Prune (`reference-and-archive-prune`)

- Execution class: `cash_now`
- Disposition: `archive_or_reference`
- Dirty matches: `0`
- Scope: Historical, research, design, runbook, archive, and top-level reference surfaces that must remain typed as reference or archive instead of masquerading as checkpoint-slice truth.
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`

## 2. Operator Tooling and Helper Surfaces (`operator-tooling-and-helper-surfaces`)

- Execution class: `cash_now`
- Disposition: `operator_tooling`
- Dirty matches: `0`
- Scope: Operator helper rules, local agent tooling, repo scaffolding, and root guidance files that should stay governed but out of checkpoint-slice authority.
- Next action: Constrain helper surfaces, root guidance, and operator tooling so they stop accumulating shadow instructions or local-only churn.
- Success condition: Operator helper surfaces remain bounded, intentional, and visibly non-authoritative outside their owned scope.
- Owner workstreams: `authority-and-mainline`, `startup-docs-and-prune`

## 3. Audit and Eval Artifacts (`audit-and-eval-artifacts`)

- Execution class: `cash_now`
- Disposition: `audit_artifact`
- Dirty matches: `0`
- Scope: Audit bundles, eval outputs, recipe fixtures, and verification traces that should stay typed as evidence or harness material rather than publication-slice truth.
- Next action: Register, snapshot, or relocate evidence outputs so audit and eval artifacts stay as proof, not accidental authority.
- Success condition: Evidence artifacts are either generated and freshness-checked or clearly typed as archive-only harness material.
- Owner workstreams: `validation-and-publication`, `startup-docs-and-prune`

## 4. Deployment Authority Follow-on (`deployment-authority-follow-on`)

- Execution class: `bounded_follow_on`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Scope: Ansible inventory, role, and deployment-authority work that should stay explicit but not block the current bounded checkpoint wave.
- Next action: Break Ansible and deployment-authority drift into bounded packet-backed repairs instead of leaving it as one giant residual lane.
- Success condition: Deployment-authority deltas are split into bounded repair tranches with explicit ownership and replay rules.
- Owner workstreams: `deployment-authority-reconciliation`, `validation-and-publication`

## 5. Runtime Service Follow-on (`runtime-service-follow-on`)

- Execution class: `bounded_follow_on`
- Disposition: `runtime_follow_on`
- Dirty matches: `0`
- Scope: Service-level runtime code and cluster helpers that remain active implementation work but are outside the current publication checkpoint order.
- Next action: Split live service deltas into runtime-owned packets and keep service truth aligned with canonical topology and contracts.
- Success condition: Runtime service changes are packet-backed and no service lane remains an undocumented side path.
- Owner workstreams: `runtime-sync-and-governed-packets`, `validation-and-publication`

## 6. Control-Plane Registry and Routing (`control-plane-registry-and-routing`)

- Execution class: `program_slice`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Scope: Implementation-authority registry, routing, and dispatch policy surfaces that should publish as one bounded control-plane tranche instead of riding inside a generic residual bucket.
- Next action: Isolate registry, routing, and dispatch policy residue into a bounded publication-ready tranche.
- Success condition: Registry and routing policy residue is isolated, packet-backed where needed, and ready for bounded publication.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## 7. Agent Execution Kernel Follow-on (`agent-execution-kernel-follow-on`)

- Execution class: `program_slice`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Scope: Agent execution-kernel, queue, scheduler, and proving surfaces that remain active implementation authority but should no longer hide inside one broad control-plane tail.
- Next action: Bound the execution-kernel, queue, scheduler, and proving logic into an explicit follow-on publication tranche.
- Success condition: Execution-kernel residue is isolated into a bounded follow-on tranche with explicit closure proof and replay boundaries.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## 7. Tenant Product Lanes (`tenant-product-lanes`)

- Execution class: `tenant_lane`
- Disposition: `tenant_surface`
- Dirty matches: `0`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`

## 8. Agent Route Contract Follow-on (`agent-route-contract-follow-on`)

- Execution class: `program_slice`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Scope: Agent HTTP route and route-contract surfaces that should move as one bounded contract tranche instead of blending with runtime kernel work.
- Next action: Split route surfaces and route-contract verification into a dedicated publication-ready follow-on tranche.
- Success condition: Route and route-contract residue is isolated, contract-tested, and ready for bounded publication.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## 9. Control-Plane Proof and Ops Follow-on (`control-plane-proof-and-ops-follow-on`)

- Execution class: `program_slice`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Scope: Control-plane proof scripts, deployment helpers, and ops automation surfaces that still matter to live closure but should no longer appear as one undifferentiated residual family.
- Next action: Isolate proof-generation, control-plane ops, and deployment helper residue into a bounded follow-on tranche.
- Success condition: Proof and ops residue is isolated, verified, and publishable without hiding behind a generic control-plane bucket.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`
