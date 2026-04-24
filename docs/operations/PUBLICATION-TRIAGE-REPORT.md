# Publication Triage Summary

- Active sequence: `2026-04-15-publication-triage-governance`
- Dirty entries: `316`
- Slice-matched entries: `228`
- Deferred-family entries: `0`
- Ambiguous entries: `0`
- Unclassified entries: `88`
- Local-noise entries: `0`

## Slice Coverage

| Slice | Status | Dirty matches | Missing publication refs | Missing generated artifacts |
| --- | --- | --- | --- | --- |
| `backbone-contracts-and-truth-writers` | `published` | `14` | `0` | `0` |
| `runtime-ownership-provider-truth-and-reconciliation` | `published` | `13` | `0` | `0` |
| `pilot-eval-substrate-and-operator-test-machinery` | `published` | `1` | `0` | `0` |
| `graphrag-promotion-wave` | `published` | `1` | `0` | `0` |
| `gpu-scheduler-extension-wave` | `published` | `1` | `0` | `0` |
| `forge-atlas-dashboard-and-startup-truth` | `published` | `123` | `0` | `0` |
| `control-plane-registry-ledgers-and-matrices` | `active` | `5` | `0` | `0` |
| `control-plane-routing-policy-and-subscription-lane` | `active` | `7` | `0` | `0` |
| `agent-execution-kernel-operator-queue-state` | `active` | `6` | `0` | `0` |
| `agent-execution-kernel-scheduler-and-research-loop` | `active` | `7` | `0` | `0` |
| `agent-execution-kernel-self-improvement-and-proving` | `active` | `4` | `0` | `0` |
| `agent-execution-kernel-support-and-tests` | `active` | `5` | `0` | `0` |
| `agent-route-contract-surface-code` | `active` | `8` | `0` | `0` |
| `agent-route-contract-tests` | `active` | `7` | `0` | `0` |
| `control-plane-ralph-and-truth-writers` | `active` | `11` | `0` | `0` |
| `control-plane-proof-generators-and-validators` | `active` | `9` | `0` | `0` |
| `control-plane-deploy-and-runtime-ops-helpers` | `active` | `6` | `0` | `0` |

## Backbone Contracts and Truth Writers (`backbone-contracts-and-truth-writers`)

- Dirty matches: `14`
- Publication refs: `29`
- Working-tree hints: `35`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/completion-program-registry.json
- `M` config/automation-backbone/project-packet-registry.json
- `M` docs/SERVICES.md
- `M` docs/SYSTEM-SPEC.md
- `M` docs/design/project-platform-architecture.md
- `M` docs/operations/PROJECT-MATURITY-REPORT.md
- `M` docs/projects/PORTFOLIO-REGISTRY.md
- `M` docs/projects/ulrich-energy/REQUIREMENTS.md
- `M` docs/projects/ulrich-energy/WORKFLOWS.md
- `M` scripts/tests/test_publication_tranche_triage.py
- `M` scripts/triage_publication_tranche.py
- `M` scripts/validate_platform_contract.py

## Runtime Ownership, Provider Truth, and Reconciliation (`runtime-ownership-provider-truth-and-reconciliation`)

- Dirty matches: `13`
- Publication refs: `42`
- Working-tree hints: `44`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` ansible/host_vars/vault.yml
- `M` ansible/roles/dashboard/defaults/main.yml
- `M` ansible/roles/dashboard/tasks/main.yml
- `M` ansible/roles/dashboard/templates/docker-compose.yml.j2
- `M` config/automation-backbone/reconciliation-source-registry.json
- `M` config/automation-backbone/runtime-ownership-contract.json
- `M` config/automation-backbone/runtime-ownership-packets.json
- `M` docs/operations/ATHANOR-ECOSYSTEM-REGISTRY.md
- `M` scripts/generate_truth_inventory_reports.py
- `??` docs/operations/WORKSHOP-COMFYUI-COMPOSE-RECONCILIATION-PACKET.md
- `??` docs/operations/WORKSHOP-EOQ-COMPOSE-RECONCILIATION-PACKET.md
- `??` docs/operations/WORKSHOP-OPEN-WEBUI-COMPOSE-RECONCILIATION-PACKET.md

## Pilot Eval Substrate and Operator-Test Machinery (`pilot-eval-substrate-and-operator-test-machinery`)

- Dirty matches: `1`
- Publication refs: `16`
- Working-tree hints: `15`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/eval-run-ledger.json

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

- Dirty matches: `123`
- Publication refs: `9`
- Working-tree hints: `9`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/dashboard/docker-compose.yml
- `M` projects/dashboard/playwright.config.ts
- `M` projects/dashboard/src/app/api/bootstrap/programs/[programId]/nudge/route.test.ts
- `M` projects/dashboard/src/app/api/bootstrap/programs/[programId]/nudge/route.ts
- `M` projects/dashboard/src/app/api/builder/sessions/[sessionId]/control/route.ts
- `M` projects/dashboard/src/app/api/master-atlas/route.test.ts
- `M` projects/dashboard/src/app/api/master-atlas/route.ts
- `M` projects/dashboard/src/app/api/operator/approvals/[approvalId]/approve/route.test.ts
- `M` projects/dashboard/src/app/api/operator/approvals/[approvalId]/approve/route.ts
- `M` projects/dashboard/src/app/api/operator/approvals/[approvalId]/reject/route.test.ts
- `M` projects/dashboard/src/app/api/operator/approvals/[approvalId]/reject/route.ts
- `M` projects/dashboard/src/app/api/operator/approvals/route.test.ts

## Control-Plane Registry Ledgers and Matrices (`control-plane-registry-ledgers-and-matrices`)

- Dirty matches: `5`
- Publication refs: `5`
- Working-tree hints: `5`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` config/automation-backbone/docs-lifecycle-registry.json
- `M` config/automation-backbone/economic-dispatch-ledger.json
- `M` config/automation-backbone/lane-selection-matrix.json
- `??` config/automation-backbone/executive-kernel-registry.json
- `??` docs/operations/CONTROL-PLANE-REGISTRY-LEDGERS-AND-MATRICES-PACKET.md

## Control-Plane Routing Policy and Subscription Lane (`control-plane-routing-policy-and-subscription-lane`)

- Dirty matches: `7`
- Publication refs: `7`
- Working-tree hints: `7`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/config/subscription-routing-policy.yaml
- `M` projects/agents/src/athanor_agents/backbone.py
- `M` projects/agents/src/athanor_agents/model_governance.py
- `M` projects/agents/src/athanor_agents/subscriptions.py
- `M` projects/agents/tests/test_model_governance.py
- `M` projects/agents/tests/test_subscription_policy.py
- `??` docs/operations/CONTROL-PLANE-ROUTING-POLICY-AND-SUBSCRIPTION-LANE-PACKET.md

## Agent Execution Kernel Operator Queue State (`agent-execution-kernel-operator-queue-state`)

- Dirty matches: `6`
- Publication refs: `6`
- Working-tree hints: `6`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/src/athanor_agents/operator_state.py
- `M` projects/agents/src/athanor_agents/operator_work.py
- `M` projects/agents/src/athanor_agents/tasks.py
- `M` projects/agents/tests/test_operator_work.py
- `M` projects/agents/tests/test_tasks.py
- `??` docs/operations/AGENT-EXECUTION-KERNEL-OPERATOR-QUEUE-STATE-PACKET.md

## Agent Execution Kernel Scheduler and Research Loop (`agent-execution-kernel-scheduler-and-research-loop`)

- Dirty matches: `7`
- Publication refs: `7`
- Working-tree hints: `7`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/src/athanor_agents/research_jobs.py
- `M` projects/agents/src/athanor_agents/scheduler.py
- `M` projects/agents/src/athanor_agents/work_pipeline.py
- `M` projects/agents/tests/test_scheduler.py
- `M` projects/agents/tests/test_work_pipeline.py
- `??` docs/operations/AGENT-EXECUTION-KERNEL-SCHEDULER-AND-RESEARCH-LOOP-PACKET.md
- `??` projects/agents/tests/test_research_jobs.py

## Agent Execution Kernel Self-Improvement and Proving (`agent-execution-kernel-self-improvement-and-proving`)

- Dirty matches: `4`
- Publication refs: `4`
- Working-tree hints: `4`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/src/athanor_agents/proving_ground.py
- `M` projects/agents/src/athanor_agents/self_improvement.py
- `M` projects/agents/tests/test_self_improvement.py
- `??` docs/operations/AGENT-EXECUTION-KERNEL-SELF-IMPROVEMENT-AND-PROVING-PACKET.md

## Agent Execution Kernel Support and Tests (`agent-execution-kernel-support-and-tests`)

- Dirty matches: `5`
- Publication refs: `5`
- Working-tree hints: `5`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `??` docs/operations/AGENT-EXECUTION-KERNEL-SUPPORT-AND-TESTS-PACKET.md
- `??` projects/agents/src/athanor_agents/autonomous_queue.py
- `??` projects/agents/src/athanor_agents/capability_intelligence.py
- `??` projects/agents/src/athanor_agents/repo_paths.py
- `??` projects/agents/tests/test_repo_paths.py

## Agent Route Surface Code (`agent-route-contract-surface-code`)

- Dirty matches: `8`
- Publication refs: `8`
- Working-tree hints: `8`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/src/athanor_agents/routes/bootstrap.py
- `M` projects/agents/src/athanor_agents/routes/model_governance.py
- `M` projects/agents/src/athanor_agents/routes/operator_work.py
- `M` projects/agents/src/athanor_agents/routes/plans.py
- `M` projects/agents/src/athanor_agents/routes/projects.py
- `M` projects/agents/src/athanor_agents/routes/research.py
- `M` projects/agents/src/athanor_agents/routes/tasks.py
- `??` docs/operations/AGENT-ROUTE-SURFACE-CODE-PACKET.md

## Agent Route Contract and CLI Tests (`agent-route-contract-tests`)

- Dirty matches: `7`
- Publication refs: `7`
- Working-tree hints: `7`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` projects/agents/tests/test_bootstrap_route_contract.py
- `M` projects/agents/tests/test_foundry_route_contract.py
- `M` projects/agents/tests/test_model_governance_route_contract.py
- `M` projects/agents/tests/test_operator_work_route_contract.py
- `M` projects/agents/tests/test_task_route_contract.py
- `M` scripts/tests/test_cli_router_contracts.py
- `??` docs/operations/AGENT-ROUTE-CONTRACT-AND-CLI-TESTS-PACKET.md

## Control-Plane Ralph and Truth Writers (`control-plane-ralph-and-truth-writers`)

- Dirty matches: `11`
- Publication refs: `11`
- Working-tree hints: `11`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` scripts/run_ralph_loop_pass.py
- `M` scripts/tests/test_ralph_loop_contracts.py
- `M` scripts/tests/test_write_steady_state_status.py
- `M` scripts/truth_inventory.py
- `M` scripts/write_steady_state_status.py
- `??` docs/operations/CONTROL-PLANE-RALPH-AND-TRUTH-WRITERS-PACKET.md
- `??` scripts/tests/test_truth_inventory_path_overrides.py
- `??` scripts/tests/test_write_current_tree_partition.py
- `??` scripts/tests/test_write_value_throughput_scorecard.py
- `??` scripts/write_current_tree_partition.py
- `??` scripts/write_value_throughput_scorecard.py

## Control-Plane Proof Generators and Validators (`control-plane-proof-generators-and-validators`)

- Dirty matches: `9`
- Publication refs: `9`
- Working-tree hints: `9`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` scripts/sync_github_portfolio_registry.py
- `M` scripts/tests/test_validate_platform_contract_monitoring_contracts.py
- `??` docs/operations/CONTROL-PLANE-PROOF-GENERATORS-AND-VALIDATORS-PACKET.md
- `??` scripts/generate_capability_intelligence.py
- `??` scripts/probe_openhands_bounded_worker.py
- `??` scripts/proof_workspace_contract.py
- `??` scripts/tests/test_capability_intelligence_contracts.py
- `??` scripts/tests/test_proof_workspace_contract.py
- `??` scripts/tests/test_sync_github_portfolio_registry.py

## Control-Plane Deploy and Runtime Ops Helpers (`control-plane-deploy-and-runtime-ops-helpers`)

- Dirty matches: `6`
- Publication refs: `6`
- Working-tree hints: `6`
- Missing publication refs: `0`
- Missing generated artifacts: `0`

Sample dirty paths:
- `M` ansible/roles/agents/templates/docker-compose.yml.j2
- `M` projects/agents/docker-compose.yml
- `M` scripts/deploy-agents.sh
- `??` docs/operations/CONTROL-PLANE-DEPLOY-AND-RUNTIME-OPS-HELPERS-PACKET.md
- `??` scripts/.cluster_config.unix.sh
- `??` scripts/.deploy-agents.unix.sh

## Deferred Family Coverage

| Deferred family | Disposition | Dirty matches |
| --- | --- | --- |
| `reference-and-archive-prune` | `archive_or_reference` | `0` |
| `operator-tooling-and-helper-surfaces` | `operator_tooling` | `0` |
| `audit-and-eval-artifacts` | `audit_artifact` | `0` |
| `deployment-authority-follow-on` | `deferred_out_of_sequence` | `0` |
| `runtime-service-follow-on` | `runtime_follow_on` | `0` |
| `control-plane-registry-and-routing` | `deferred_out_of_sequence` | `0` |
| `agent-execution-kernel-follow-on` | `deferred_out_of_sequence` | `0` |
| `tenant-product-lanes` | `tenant_surface` | `0` |
| `agent-route-contract-follow-on` | `deferred_out_of_sequence` | `0` |
| `control-plane-proof-and-ops-follow-on` | `deferred_out_of_sequence` | `0` |

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
- Dirty matches: `0`
- Path hints: `4`
- Scope: Audit bundles, eval outputs, recipe fixtures, and verification traces that should stay typed as evidence or harness material rather than publication-slice truth.
- Execution class: `cash_now`
- Next action: Register, snapshot, or relocate evidence outputs so audit and eval artifacts stay as proof, not accidental authority.
- Success condition: Evidence artifacts are either generated and freshness-checked or clearly typed as archive-only harness material.
- Owner workstreams: `validation-and-publication`, `startup-docs-and-prune`

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

## Deferred: Control-Plane Registry and Routing (`control-plane-registry-and-routing`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Path hints: `10`
- Scope: Implementation-authority registry, routing, and dispatch policy surfaces that should publish as one bounded control-plane tranche instead of riding inside a generic residual bucket.
- Execution class: `program_slice`
- Next action: Isolate registry, routing, and dispatch policy residue into a bounded publication-ready tranche.
- Success condition: Registry and routing policy residue is isolated, packet-backed where needed, and ready for bounded publication.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## Deferred: Agent Execution Kernel Follow-on (`agent-execution-kernel-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Path hints: `18`
- Scope: Agent execution-kernel, queue, scheduler, and proving surfaces that remain active implementation authority but should no longer hide inside one broad control-plane tail.
- Execution class: `program_slice`
- Next action: Bound the execution-kernel, queue, scheduler, and proving logic into an explicit follow-on publication tranche.
- Success condition: Execution-kernel residue is isolated into a bounded follow-on tranche with explicit closure proof and replay boundaries.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## Deferred: Tenant Product Lanes (`tenant-product-lanes`)

- Disposition: `tenant_surface`
- Dirty matches: `0`
- Path hints: `5`
- Scope: Tenant and product-lane repos that are governed local roots but not part of the current checkpoint publication sequence.
- Execution class: `tenant_lane`
- Next action: Push tenant roots through product-specific classification, packet lanes, and local-root governance instead of Athanor checkpoint publication.
- Success condition: Tenant product changes route through their governed tenant lanes without leaking into Athanor checkpoint slices.
- Owner workstreams: `tenant-architecture-and-classification`, `validation-and-publication`

## Deferred: Agent Route Contract Follow-on (`agent-route-contract-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Path hints: `7`
- Scope: Agent HTTP route and route-contract surfaces that should move as one bounded contract tranche instead of blending with runtime kernel work.
- Execution class: `program_slice`
- Next action: Split route surfaces and route-contract verification into a dedicated publication-ready follow-on tranche.
- Success condition: Route and route-contract residue is isolated, contract-tested, and ready for bounded publication.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## Deferred: Control-Plane Proof and Ops Follow-on (`control-plane-proof-and-ops-follow-on`)

- Disposition: `deferred_out_of_sequence`
- Dirty matches: `0`
- Path hints: `22`
- Scope: Control-plane proof scripts, deployment helpers, and ops automation surfaces that still matter to live closure but should no longer appear as one undifferentiated residual family.
- Execution class: `program_slice`
- Next action: Isolate proof-generation, control-plane ops, and deployment helper residue into a bounded follow-on tranche.
- Success condition: Proof and ops residue is isolated, verified, and publishable without hiding behind a generic control-plane bucket.
- Owner workstreams: `authority-and-mainline`, `validation-and-publication`

## Unclassified Entries

- `M` config/automation-backbone/autonomy-activation-registry.json
- `M` config/automation-backbone/operator-surface-registry.json
- `M` config/automation-backbone/project-maturity-registry.json
- `M` projects/agents/Dockerfile
- `M` projects/agents/src/athanor_agents/agents/__init__.py
- `M` projects/agents/src/athanor_agents/agents/coding.py
- `M` projects/agents/src/athanor_agents/bootstrap_state.py
- `M` projects/agents/src/athanor_agents/owner_model.py
- `M` projects/agents/src/athanor_agents/projects.py
- `M` projects/agents/src/athanor_agents/routing.py
- `M` projects/agents/src/athanor_agents/supervisor.py
- `M` projects/agents/src/athanor_agents/tools/execution.py
