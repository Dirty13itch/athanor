# Publication Deferred-Family Queue

- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `222`
- Slice-matched entries: `56`
- Deferred-family entries: `164`
- Deferred families: `7`

## Next Recommended Tranche

- Family: `reference-and-archive-prune`
- Title: Reference and Archive Prune
- Execution class: `cash_now`
- Dirty matches: `35`
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.

## Ordered Queue

| Rank | Family | Class | Dirty matches | Disposition | Owner workstreams |
| --- | --- | --- | --- | --- | --- |
| `1` | `reference-and-archive-prune` | `cash_now` | `35` | `archive_or_reference` | `startup-docs-and-prune, validation-and-publication` |
| `2` | `operator-tooling-and-helper-surfaces` | `cash_now` | `25` | `operator_tooling` | `authority-and-mainline, startup-docs-and-prune` |
| `3` | `audit-and-eval-artifacts` | `cash_now` | `12` | `audit_artifact` | `validation-and-publication, startup-docs-and-prune` |
| `4` | `deployment-authority-follow-on` | `bounded_follow_on` | `3` | `deferred_out_of_sequence` | `deployment-authority-reconciliation, validation-and-publication` |
| `5` | `runtime-service-follow-on` | `bounded_follow_on` | `0` | `runtime_follow_on` | `runtime-sync-and-governed-packets, validation-and-publication` |
| `6` | `control-plane-follow-on` | `program_slice` | `82` | `deferred_out_of_sequence` | `authority-and-mainline, validation-and-publication` |
| `7` | `tenant-product-lanes` | `tenant_lane` | `7` | `tenant_surface` | `tenant-architecture-and-classification, validation-and-publication` |

## 1. Reference and Archive Prune (`reference-and-archive-prune`)

- Execution class: `cash_now`
- Disposition: `archive_or_reference`
- Dirty matches: `35`
- Scope: Historical, research, design, runbook, archive, and top-level reference surfaces that must remain typed as reference or archive instead of masquerading as checkpoint-slice truth.
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`

Sample paths:
- `docs/DOCUMENTATION-INDEX.md`
- `docs/MASTER-PLAN.md`
- `docs/RECOVERY.md`
- `docs/REFERENCE-INDEX.md`
- `docs/SECURITY-FOLLOWUPS.md`
- `docs/SERVICES.md`
- `docs/SYSTEM-SPEC.md`
- `docs/TROUBLESHOOTING.md`
- `docs/UI-AUDIT-LOOP.md`
- `docs/archive/ATHANOR-SYSTEM-MAP.md`
- `docs/archive/BLOCKED.md`
- `docs/archive/BUILD-MANIFEST.md`

## 2. Operator Tooling and Helper Surfaces (`operator-tooling-and-helper-surfaces`)

- Execution class: `cash_now`
- Disposition: `operator_tooling`
- Dirty matches: `25`
- Scope: Operator helper rules, local agent tooling, repo scaffolding, and root guidance files that should stay governed but out of checkpoint-slice authority.
- Next action: Constrain helper surfaces, root guidance, and operator tooling so they stop accumulating shadow instructions or local-only churn.
- Success condition: Operator helper surfaces remain bounded, intentional, and visibly non-authoritative outside their owned scope.
- Owner workstreams: `authority-and-mainline`, `startup-docs-and-prune`

Sample paths:
- `.claude/agents/architect.md`
- `.claude/agents/doc-writer.md`
- `.claude/agents/infra-auditor.md`
- `.claude/commands/status.md`
- `.claude/hooks/post-compact-reload.sh`
- `.claude/hooks/pre-compact-save.sh`
- `.claude/hooks/stop-autocommit.sh`
- `.claude/rules/docs-sync.md`
- `.claude/rules/litellm.md`
- `.claude/rules/qdrant-operations.md`
- `.claude/rules/session-continuity.md`
- `.claude/rules/vllm.md`

## 3. Audit and Eval Artifacts (`audit-and-eval-artifacts`)

- Execution class: `cash_now`
- Disposition: `audit_artifact`
- Dirty matches: `12`
- Scope: Audit bundles, eval outputs, recipe fixtures, and verification traces that should stay typed as evidence or harness material rather than publication-slice truth.
- Next action: Register, snapshot, or relocate evidence outputs so audit and eval artifacts stay as proof, not accidental authority.
- Success condition: Evidence artifacts are either generated and freshness-checked or clearly typed as archive-only harness material.
- Owner workstreams: `validation-and-publication`, `startup-docs-and-prune`

Sample paths:
- `audit/automation/contract-healer-latest.json`
- `audit/recovery/restore-drill-latest.json`
- `evals/ab-comparison.yaml`
- `evals/eoq/promptfooconfig.yaml`
- `evals/promptfooconfig.yaml`
- `recipes/port-hydra-module.yaml`
- `recipes/test-all-endpoints.yaml`
- `tests/harness.py`
- `tests/ui-audit/findings-ledger.json`
- `tests/ui-audit/last-run.json`
- `tests/ui-audit/surface-registry.json`
- `tests/ui-audit/uncovered-surfaces.json`

## 4. Deployment Authority Follow-on (`deployment-authority-follow-on`)

- Execution class: `bounded_follow_on`
- Disposition: `deferred_out_of_sequence`
- Dirty matches: `3`
- Scope: Ansible inventory, role, and deployment-authority work that should stay explicit but not block the current bounded checkpoint wave.
- Next action: Break Ansible and deployment-authority drift into bounded packet-backed repairs instead of leaving it as one giant residual lane.
- Success condition: Deployment-authority deltas are split into bounded repair tranches with explicit ownership and replay rules.
- Owner workstreams: `deployment-authority-reconciliation`, `validation-and-publication`

Sample paths:
- `ansible/roles/eoq/defaults/main.yml`
- `ansible/roles/eoq/templates/docker-compose.yml.j2`
- `ansible/roles/vault-litellm/templates/litellm_config.yaml.j2`

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
- Dirty matches: `82`
- Scope: Implementation-authority control-plane, agent-runtime, and operations packet work that is real but intentionally outside the six ready checkpoint slices.
- Next action: Break the broad control-plane tail into explicit follow-on publication slices before any wider checkpoint publish.
- Success condition: Control-plane residue is no longer one deferred mass; it is decomposed into explicit publication-ready tranches.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

Sample paths:
- `config/automation-backbone/artifact-topology-registry.json`
- `config/automation-backbone/autonomy-activation-registry.json`
- `config/automation-backbone/data-lifecycle-registry.json`
- `config/automation-backbone/docs-lifecycle-registry.json`
- `config/automation-backbone/operator-runbooks.json`
- `config/automation-backbone/operator-surface-registry.json`
- `config/automation-backbone/runtime-subsystem-registry.json`
- `config/automation-backbone/tooling-inventory.json`
- `config/automation-backbone/vendor-policy-registry.json`
- `docs/operations/ATHANOR-CAPABILITY-PROMOTION.md`
- `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- `docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md`

## 7. Tenant Product Lanes (`tenant-product-lanes`)

- Execution class: `tenant_lane`
- Disposition: `tenant_surface`
- Dirty matches: `7`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`

Sample paths:
- `projects/eoq/README.md`
- `projects/eoq/soulforge/README.md`
- `projects/eoq/soulforge/dialogue.py`
- `projects/eoq/soulforge/engine.py`
- `projects/eoq/src/app/api/chat/route.ts`
- `projects/eoq/src/app/api/narrate/route.ts`
- `projects/eoq/src/lib/config.ts`
