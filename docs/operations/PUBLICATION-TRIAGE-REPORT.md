# Publication Triage Summary

Generated: `2026-04-16T18:42:04.250791+00:00`
- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `222`
- Slice-matched entries: `56`
- Deferred-family entries: `164`
- Ambiguous entries: `0`
- Unclassified entries: `2`
- Local-noise entries: `0`

## Slice Coverage

| Slice | Status | Dirty matches | Missing publication refs | Missing generated artifacts |
| --- | --- | --- | --- | --- |
| `backbone-contracts-and-truth-writers` | `published` | `25` | `0` | `0` |
| `runtime-ownership-provider-truth-and-reconciliation` | `published` | `18` | `0` | `0` |
| `pilot-eval-substrate-and-operator-test-machinery` | `published` | `2` | `0` | `0` |
| `graphrag-promotion-wave` | `published` | `1` | `0` | `0` |
| `gpu-scheduler-extension-wave` | `published` | `1` | `0` | `0` |
| `forge-atlas-dashboard-and-startup-truth` | `published` | `9` | `0` | `0` |

## Backbone Contracts and Truth Writers (`backbone-contracts-and-truth-writers`)

- Dirty matches: `25`
- Publication refs: `20`
- Working-tree hints: `25`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/completion-program-registry.json
- `M` config/automation-backbone/contract-registry.json
- `M` config/automation-backbone/project-packet-registry.json
- `M` projects/agents/config/automation-backbone/contract-registry.json
- `M` scripts/validate_platform_contract.py
- `??` config/automation-backbone/architecture-freeze-policy.json
- `??` config/automation-backbone/assumption-governance.json
- `??` config/automation-backbone/canonical-vocabulary-registry.json
- `??` config/automation-backbone/commitment-governance.json
- `??` config/automation-backbone/compatibility-alias-policy.json
- `??` config/automation-backbone/data-handling-policy.json
- `??` config/automation-backbone/execution-lease-policy.json

## Runtime Ownership, Provider Truth, and Reconciliation (`runtime-ownership-provider-truth-and-reconciliation`)

- Dirty matches: `18`
- Publication refs: `24`
- Working-tree hints: `25`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/credential-surface-registry.json
- `M` config/automation-backbone/provider-catalog.json
- `M` config/automation-backbone/repo-roots-registry.json
- `M` config/automation-backbone/runtime-ownership-contract.json
- `M` config/automation-backbone/runtime-ownership-packets.json
- `M` docs/operations/ATHANOR-RECONCILIATION-END-STATE.md
- `M` docs/operations/PROVIDER-CATALOG-REPORT.md
- `M` docs/operations/REPO-ROOTS-REPORT.md
- `M` docs/operations/RUNTIME-OWNERSHIP-PACKETS.md
- `M` docs/operations/RUNTIME-OWNERSHIP-REPORT.md
- `M` docs/operations/SECRET-SURFACE-REPORT.md
- `M` docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md

## Pilot Eval Substrate and Operator-Test Machinery (`pilot-eval-substrate-and-operator-test-machinery`)

- Dirty matches: `2`
- Publication refs: `16`
- Working-tree hints: `15`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/eval-run-ledger.json
- `M` scripts/generate_capability_pilot_readiness.py

## GraphRAG Promotion Wave (`graphrag-promotion-wave`)

- Dirty matches: `1`
- Publication refs: `6`
- Working-tree hints: `3`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/capability-adoption-registry.json

## GPU Scheduler Extension Wave (`gpu-scheduler-extension-wave`)

- Dirty matches: `1`
- Publication refs: `7`
- Working-tree hints: `3`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` scripts/run_gpu_scheduler_baseline_eval.py

## Forge, Atlas, Dashboard, and Startup Truth (`forge-atlas-dashboard-and-startup-truth`)

- Dirty matches: `9`
- Publication refs: `9`
- Working-tree hints: `9`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` STATUS.md
- `M` docs/CODEX-NEXT-STEPS.md
- `M` docs/operations/ATHANOR-TOTAL-COMPLETION-PROGRAM.md
- `M` docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md
- `M` docs/operations/OPERATOR-SURFACE-REPORT.md
- `M` projects/dashboard/src/generated/master-atlas.json
- `M` projects/dashboard/src/generated/operator-surfaces.json
- `??` docs/operations/ATHANOR-COLD-START.md
- `??` docs/operations/ATHANOR-LAYERED-MASTER-PLAN.md

## Deferred Family Coverage

| Deferred family | Disposition | Dirty matches |
| --- | --- | --- |
| `reference-and-archive-prune` | `archive_or_reference` | `35` |
| `operator-tooling-and-helper-surfaces` | `operator_tooling` | `25` |
| `audit-and-eval-artifacts` | `audit_artifact` | `12` |
| `deployment-authority-follow-on` | `deferred_out_of_sequence` | `3` |
| `runtime-service-follow-on` | `runtime_follow_on` | `0` |
| `control-plane-follow-on` | `deferred_out_of_sequence` | `82` |
| `tenant-product-lanes` | `tenant_surface` | `7` |

## Deferred: Reference and Archive Prune (`reference-and-archive-prune`)

- Disposition: `archive_or_reference`
- Dirty matches: `35`
- Path hints: `9`
- Scope: Historical, research, design, runbook, archive, and top-level reference surfaces that must remain typed as reference or archive instead of masquerading as checkpoint-slice truth.
- Execution class: `cash_now`
- Next action: Prune or archive superseded top-level reference docs, repoint surviving references, and keep archive surfaces explicitly non-authoritative.
- Success condition: Top-level reference and archive surfaces stop presenting stale implementation or runtime truth from active-looking paths.
- Owner workstreams: `startup-docs-and-prune`, `validation-and-publication`

Sample dirty paths:
- `M` docs/DOCUMENTATION-INDEX.md
- `M` docs/MASTER-PLAN.md
- `M` docs/RECOVERY.md
- `M` docs/REFERENCE-INDEX.md
- `M` docs/SECURITY-FOLLOWUPS.md
- `M` docs/SERVICES.md
- `M` docs/SYSTEM-SPEC.md
- `M` docs/TROUBLESHOOTING.md
- `M` docs/UI-AUDIT-LOOP.md
- `M` docs/archive/ATHANOR-SYSTEM-MAP.md
- `M` docs/archive/BLOCKED.md
- `M` docs/archive/BUILD-MANIFEST.md

## Deferred: Operator Tooling and Helper Surfaces (`operator-tooling-and-helper-surfaces`)

- Disposition: `operator_tooling`
- Dirty matches: `25`
- Path hints: `13`
- Scope: Operator helper rules, local agent tooling, repo scaffolding, and root guidance files that should stay governed but out of checkpoint-slice authority.
- Execution class: `cash_now`
- Next action: Constrain helper surfaces, root guidance, and operator tooling so they stop accumulating shadow instructions or local-only churn.
- Success condition: Operator helper surfaces remain bounded, intentional, and visibly non-authoritative outside their owned scope.
- Owner workstreams: `authority-and-mainline`, `startup-docs-and-prune`

Sample dirty paths:
- `M` .claude/agents/architect.md
- `M` .claude/agents/doc-writer.md
- `M` .claude/agents/infra-auditor.md
- `M` .claude/commands/status.md
- `M` .claude/hooks/post-compact-reload.sh
- `M` .claude/hooks/pre-compact-save.sh
- `M` .claude/hooks/stop-autocommit.sh
- `M` .claude/rules/docs-sync.md
- `M` .claude/rules/litellm.md
- `M` .claude/rules/qdrant-operations.md
- `M` .claude/rules/session-continuity.md
- `M` .claude/rules/vllm.md

## Deferred: Audit and Eval Artifacts (`audit-and-eval-artifacts`)

- Disposition: `audit_artifact`
- Dirty matches: `12`
- Path hints: `4`
- Scope: Audit bundles, eval outputs, recipe fixtures, and verification traces that should stay typed as evidence or harness material rather than publication-slice truth.
- Execution class: `cash_now`
- Next action: Register, snapshot, or relocate evidence outputs so audit and eval artifacts stay as proof, not accidental authority.
- Success condition: Evidence artifacts are either generated and freshness-checked or clearly typed as archive-only harness material.
- Owner workstreams: `validation-and-publication`, `startup-docs-and-prune`

Sample dirty paths:
- `M` audit/automation/contract-healer-latest.json
- `M` audit/recovery/restore-drill-latest.json
- `M` evals/ab-comparison.yaml
- `M` evals/eoq/promptfooconfig.yaml
- `M` evals/promptfooconfig.yaml
- `M` recipes/port-hydra-module.yaml
- `M` recipes/test-all-endpoints.yaml
- `M` tests/harness.py
- `M` tests/ui-audit/findings-ledger.json
- `M` tests/ui-audit/last-run.json
- `M` tests/ui-audit/surface-registry.json
- `M` tests/ui-audit/uncovered-surfaces.json

## Deferred: Deployment Authority Follow-on (`deployment-authority-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `3`
- Path hints: `1`
- Scope: Ansible inventory, role, and deployment-authority work that should stay explicit but not block the current bounded checkpoint wave.
- Execution class: `bounded_follow_on`
- Next action: Break Ansible and deployment-authority drift into bounded packet-backed repairs instead of leaving it as one giant residual lane.
- Success condition: Deployment-authority deltas are split into bounded repair tranches with explicit ownership and replay rules.
- Owner workstreams: `deployment-authority-reconciliation`, `validation-and-publication`

Sample dirty paths:
- `M` ansible/roles/eoq/defaults/main.yml
- `M` ansible/roles/eoq/templates/docker-compose.yml.j2
- `M` ansible/roles/vault-litellm/templates/litellm_config.yaml.j2

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
- Dirty matches: `82`
- Path hints: `4`
- Scope: Implementation-authority control-plane, agent-runtime, and operations packet work that is real but intentionally outside the six ready checkpoint slices.
- Execution class: `program_slice`
- Next action: Break the broad control-plane tail into explicit follow-on publication slices before any wider checkpoint publish.
- Success condition: Control-plane residue is no longer one deferred mass; it is decomposed into explicit publication-ready tranches.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

Sample dirty paths:
- `M` config/automation-backbone/artifact-topology-registry.json
- `M` config/automation-backbone/autonomy-activation-registry.json
- `M` config/automation-backbone/data-lifecycle-registry.json
- `M` config/automation-backbone/docs-lifecycle-registry.json
- `M` config/automation-backbone/operator-runbooks.json
- `M` config/automation-backbone/operator-surface-registry.json
- `M` config/automation-backbone/runtime-subsystem-registry.json
- `M` config/automation-backbone/tooling-inventory.json
- `M` config/automation-backbone/vendor-policy-registry.json
- `M` docs/operations/ATHANOR-CAPABILITY-PROMOTION.md
- `M` docs/operations/ATHANOR-OPERATING-SYSTEM.md
- `M` docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md

## Deferred: Tenant Product Lanes (`tenant-product-lanes`)

- Disposition: `tenant_surface`
- Dirty matches: `7`
- Path hints: `5`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Execution class: `tenant_lane`
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`

Sample dirty paths:
- `M` projects/eoq/README.md
- `M` projects/eoq/soulforge/README.md
- `M` projects/eoq/soulforge/dialogue.py
- `M` projects/eoq/soulforge/engine.py
- `M` projects/eoq/src/app/api/chat/route.ts
- `M` projects/eoq/src/app/api/narrate/route.ts
- `M` projects/eoq/src/lib/config.ts

## Unclassified Entries

- `M` .mcp.json
- `M` MEMORY.md
