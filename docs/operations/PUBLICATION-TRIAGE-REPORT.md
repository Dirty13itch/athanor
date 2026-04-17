# Publication Triage Summary

- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `3`
- Slice-matched entries: `0`
- Deferred-family entries: `3`
- Ambiguous entries: `0`
- Unclassified entries: `0`
- Local-noise entries: `0`

## Slice Coverage

| Slice | Status | Dirty matches | Missing publication refs | Missing generated artifacts |
| --- | --- | --- | --- | --- |
| `backbone-contracts-and-truth-writers` | `published` | `0` | `0` | `0` |
| `runtime-ownership-provider-truth-and-reconciliation` | `published` | `0` | `0` | `0` |
| `pilot-eval-substrate-and-operator-test-machinery` | `published` | `0` | `0` | `0` |
| `graphrag-promotion-wave` | `published` | `0` | `0` | `0` |
| `gpu-scheduler-extension-wave` | `published` | `0` | `0` | `0` |
| `forge-atlas-dashboard-and-startup-truth` | `published` | `0` | `0` | `0` |

## Backbone Contracts and Truth Writers (`backbone-contracts-and-truth-writers`)

- Dirty matches: `0`
- Publication refs: `20`
- Working-tree hints: `25`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## Runtime Ownership, Provider Truth, and Reconciliation (`runtime-ownership-provider-truth-and-reconciliation`)

- Dirty matches: `0`
- Publication refs: `24`
- Working-tree hints: `25`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## Pilot Eval Substrate and Operator-Test Machinery (`pilot-eval-substrate-and-operator-test-machinery`)

- Dirty matches: `0`
- Publication refs: `16`
- Working-tree hints: `15`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## GraphRAG Promotion Wave (`graphrag-promotion-wave`)

- Dirty matches: `0`
- Publication refs: `6`
- Working-tree hints: `3`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## GPU Scheduler Extension Wave (`gpu-scheduler-extension-wave`)

- Dirty matches: `0`
- Publication refs: `7`
- Working-tree hints: `3`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## Forge, Atlas, Dashboard, and Startup Truth (`forge-atlas-dashboard-and-startup-truth`)

- Dirty matches: `0`
- Publication refs: `9`
- Working-tree hints: `9`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

## Deferred Family Coverage

| Deferred family | Disposition | Dirty matches |
| --- | --- | --- |
| `reference-and-archive-prune` | `archive_or_reference` | `0` |
| `operator-tooling-and-helper-surfaces` | `operator_tooling` | `0` |
| `audit-and-eval-artifacts` | `audit_artifact` | `1` |
| `deployment-authority-follow-on` | `deferred_out_of_sequence` | `0` |
| `runtime-service-follow-on` | `runtime_follow_on` | `0` |
| `control-plane-follow-on` | `deferred_out_of_sequence` | `2` |
| `tenant-product-lanes` | `tenant_surface` | `0` |

## Deferred: Reference and Archive Prune (`reference-and-archive-prune`)

- Disposition: `archive_or_reference`
- Dirty matches: `0`
- Path hints: `9`
- Scope: Historical, research, design, runbook, archive, and top-level reference surfaces that must remain typed as reference or archive instead of masquerading as checkpoint-slice truth.
- Execution class: `cash_now`
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`

## Deferred: Operator Tooling and Helper Surfaces (`operator-tooling-and-helper-surfaces`)

- Disposition: `operator_tooling`
- Dirty matches: `0`
- Path hints: `13`
- Scope: Operator helper rules, local agent tooling, repo scaffolding, and root guidance files that should stay governed but out of checkpoint-slice authority.
- Execution class: `cash_now`
- Next action: Constrain helper surfaces, root guidance, and operator tooling so they stop accumulating shadow instructions or local-only churn.
- Success condition: Operator helper surfaces remain bounded, intentional, and visibly non-authoritative outside their owned scope.
- Owner workstreams: `authority-and-mainline`, `startup-docs-and-prune`

## Deferred: Audit and Eval Artifacts (`audit-and-eval-artifacts`)

- Disposition: `audit_artifact`
- Dirty matches: `1`
- Path hints: `4`
- Scope: Audit bundles, eval outputs, recipe fixtures, and verification traces that should stay typed as evidence or harness material rather than publication-slice truth.
- Execution class: `cash_now`
- Next action: Register, snapshot, or relocate evidence outputs so audit and eval artifacts stay as proof, not accidental authority.
- Success condition: Evidence artifacts are either generated and freshness-checked or clearly typed as archive-only harness material.
- Owner workstreams: `validation-and-publication`, `startup-docs-and-prune`

Sample dirty paths:
- `M` audit/automation/contract-healer-latest.json

## Deferred: Deployment Authority Follow-on (`deployment-authority-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Path hints: `1`
- Scope: Ansible inventory, role, and deployment-authority work that should stay explicit but not block the current bounded checkpoint wave.
- Execution class: `bounded_follow_on`
- Next action: Break Ansible and deployment-authority drift into bounded packet-backed repairs instead of leaving it as one giant residual lane.
- Success condition: Deployment-authority deltas are split into bounded repair tranches with explicit ownership and replay rules.
- Owner workstreams: `deployment-authority-reconciliation`, `validation-and-publication`

## Deferred: Runtime Service Follow-on (`runtime-service-follow-on`)

- Disposition: `runtime_follow_on`
- Dirty matches: `0`
- Path hints: `1`
- Scope: Service-level runtime code and cluster helpers that remain active implementation work but are outside the current publication checkpoint order.
- Execution class: `bounded_follow_on`
- Next action: Split live service deltas into runtime-owned packets and keep service truth aligned with canonical topology and contracts.
- Success condition: Runtime service changes are packet-backed and no service lane remains an undocumented side path.
- Owner workstreams: `runtime-sync-and-governed-packets`, `validation-and-publication`

## Deferred: Control-Plane Follow-on (`control-plane-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `2`
- Path hints: `4`
- Scope: Implementation-authority control-plane, agent-runtime, and operations packet work that is real but intentionally outside the six ready checkpoint slices.
- Execution class: `program_slice`
- Next action: Break the broad control-plane tail into explicit follow-on publication slices before any wider checkpoint publish.
- Success condition: Control-plane residue is no longer one deferred mass; it is decomposed into explicit publication-ready tranches.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

Sample dirty paths:
- `M` scripts/run_ralph_loop_pass.py
- `M` scripts/tests/test_ralph_loop_contracts.py

## Deferred: Tenant Product Lanes (`tenant-product-lanes`)

- Disposition: `tenant_surface`
- Dirty matches: `0`
- Path hints: `5`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Execution class: `tenant_lane`
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`
