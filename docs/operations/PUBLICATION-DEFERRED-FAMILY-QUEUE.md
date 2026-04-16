# Publication Deferred-Family Queue

- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `28`
- Slice-matched entries: `12`
- Deferred-family entries: `16`
- Deferred families: `7`

## Next Recommended Tranche

- Family: `reference-and-archive-prune`
- Title: Reference and Archive Prune
- Execution class: `cash_now`
- Dirty matches: `1`
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.

## Ordered Queue

| Rank | Family | Class | Dirty matches | Disposition | Owner workstreams |
| --- | --- | --- | --- | --- | --- |
| `1` | `reference-and-archive-prune` | `cash_now` | `1` | `archive_or_reference` | `startup-docs-and-prune, validation-and-publication` |
| `2` | `operator-tooling-and-helper-surfaces` | `cash_now` | `0` | `operator_tooling` | `authority-and-mainline, startup-docs-and-prune` |
| `3` | `audit-and-eval-artifacts` | `cash_now` | `0` | `audit_artifact` | `validation-and-publication, startup-docs-and-prune` |
| `4` | `deployment-authority-follow-on` | `bounded_follow_on` | `0` | `deferred_out_of_sequence` | `deployment-authority-reconciliation, validation-and-publication` |
| `5` | `runtime-service-follow-on` | `bounded_follow_on` | `0` | `runtime_follow_on` | `runtime-sync-and-governed-packets, validation-and-publication` |
| `6` | `control-plane-follow-on` | `program_slice` | `15` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |
| `7` | `tenant-product-lanes` | `tenant_lane` | `0` | `tenant_surface` | `tenant-architecture-and-classification, validation-and-publication` |

## 1. Reference and Archive Prune (`reference-and-archive-prune`)

- Execution class: `cash_now`
- Disposition: `archive_or_reference`
- Dirty matches: `1`
- Scope: Historical, research, design, runbook, archive, and top-level reference surfaces that must remain typed as reference or archive instead of masquerading as checkpoint-slice truth.
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`

Sample paths:
- `docs/DOCUMENTATION-INDEX.md`

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

## 6. Control-Plane Follow-on (`control-plane-follow-on`)

- Execution class: `program_slice`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `15`
- Scope: Implementation-authority control-plane, agent-runtime, and operations packet work that is real but intentionally outside the six ready checkpoint slices.
- Next action: Break the broad control-plane tail into explicit follow-on publication slices before any wider checkpoint publish.
- Success condition: Control-plane residue is no longer one deferred mass; it is decomposed into explicit publication-ready tranches.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

Sample paths:
- `config/automation-backbone/docs-lifecycle-registry.json`
- `docs/operations/ATHANOR-FULL-SYSTEM-AUDIT.md`
- `docs/operations/AUDIT-REMEDIATION-BACKLOG.md`
- `docs/operations/DEVSTACK-MEMBRANE-AUDIT.md`
- `docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md`
- `docs/operations/RUNTIME-MIGRATION-REPORT.md`
- `docs/operations/VAULT-REDIS-REPAIR-PACKET.md`
- `scripts/closure_finish_common.py`
- `scripts/generate_full_system_audit.py`
- `scripts/run_ralph_loop_pass.py`
- `scripts/session_restart_brief.py`
- `scripts/tests/test_ralph_loop_contracts.py`

## 7. Tenant Product Lanes (`tenant-product-lanes`)

- Execution class: `tenant_lane`
- Disposition: `tenant_surface`
- Dirty matches: `0`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`
