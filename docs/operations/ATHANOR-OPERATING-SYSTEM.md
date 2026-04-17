# Athanor Operating System

This file records the operating-model snapshot for Athanor after the shift to registry-backed truth and aggressive prune discipline.

## Source of Truth

The editable control plane lives in [config/automation-backbone](../../config/automation-backbone).

Primary registries:
- `capability-adoption-registry.json`
- `platform-topology.json`
- `project-maturity-registry.json`
- `reconciliation-source-registry.json`
- `completion-program-registry.json`
- `docs-lifecycle-registry.json`
- `program-operating-system.json`
- `hardware-inventory.json`
- `model-deployment-registry.json`
- `provider-catalog.json`
- `autonomy-activation-registry.json`
- `subscription-burn-registry.json`
- `tooling-inventory.json`
- `credential-surface-registry.json`
- `repo-roots-registry.json`
- `routing-taxonomy-map.json`

Loop evidence surfaces:
- `scripts/run_ralph_loop_pass.py`
- `reports/ralph-loop/latest.json`
- `docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md`
- `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`
- `docs/operations/REPO-ROOT-AUTHORITY-AUDIT.md`
- `projects/dashboard/src/generated/master-atlas.json` as a downstream consumer of `C:/athanor-devstack/reports/master-atlas/latest.json`, never as a separate authority surface

## Authority Snapshot

- `C:\Athanor` is the implementation authority for config, contracts, inventories, validation rules, and canonical current-state docs.
- `C:\athanor-devstack` is the build-system authority for `concept`, `prototype`, and `proved` capability work and cannot define live truth without an explicit promotion packet recorded in `capability-adoption-registry.json`.
- `/home/shaun/repos/athanor` on DEV is the runtime and deployment authority until deployment is clean enough to be a strict mirror.
- `C:\Users\Shaun\dev\athanor-next` is an incubation lane and cannot define live truth without an explicit promotion packet.
- `C:\Users\Shaun\.codex` is the operator-local control surface, is tracked as an operator-local root for audit purposes, and cannot silently become project truth.

## Truth Rules

- Runtime truth outranks memory and stale docs.
- Registry truth outranks helper scripts and hardcoded literals.
- Devstack handoff posture, packet admissibility, and low-touch turnover state are owned by the atlas and packet-backed capability truth, not by older status prose or chat memory.
- Official provider terms, observed runtime state, and heuristic estimates are distinct classes and must not be conflated.
- The DEV `:8760` cutover is complete; any autonomy expansion now depends on policy scope and provider confidence, not the retired governor facade.
- Post-cutover autonomy scope is owned by `autonomy-activation-registry.json` and the current live phase is `full_system_phase_3`.
- Runtime mutations remain approval-gated even after first activation.
- Secret surfaces may be reported by presence, location, owner, and env contract only. Secret values never belong in tracked truth.
- If a doc cannot justify its lifecycle class, it should be archived or deleted.
- Startup docs are doctrine and re-entry surfaces only. Volatile build-state truth belongs in the devstack forge board, packets, and atlas, not in Athanor startup prose.

## End-State Contract

The reconciliation closure contract lives in [ATHANOR-RECONCILIATION-END-STATE.md](/C:/Athanor/docs/operations/ATHANOR-RECONCILIATION-END-STATE.md).

That contract is machine-backed by:
- `config/automation-backbone/completion-program-registry.json` `reconciliation_end_state`
- `reports/ralph-loop/latest.json` `reconciliation_end_state`

The operating rule is simple:
- non-steady-state exit gates may be `completed`, `ready_for_operator_approval`, or `external_dependency_blocked`
- the steady-state gate remains active until Ralph-loop clean-cycle acceptance is satisfied
- runtime approval gates do not count as ambiguity if the packeted state is explicit and current

## Execution Loop

1. Validate the registry and generated-doc layer.
2. Generate fresh reports for hardware, model deployment, provider catalog, repo roots, drift, and secret surfaces.
3. Compare runtime probes to registry truth and mark any divergence explicitly as drift.
4. Route any cross-repo or side-root discovery into the reconciliation source registry and the ecosystem control docs before treating it as active program scope.
5. Run the Ralph-loop controller so the next eligible workstream and blocker state are explicit in `reports/ralph-loop/latest.json`.
6. Keep the total-completion program registry, Ralph-loop contract, and completion doc aligned with the current execution frontier.
7. Close the highest-leverage drift or contract bug.
8. Rerun the relevant gate.
9. Delete or freeze superseded material once the replacement truth is verified.

## Operator Shell Boundary

- The adopted bounded shell orchestrator path is owned by the canonical operator-surface registry and its linked runtime packet surface, not by startup prose or ad hoc local helpers.
- The bounded shell path must remain subordinate to Athanor control-plane truth and must not become a second control plane or bypass the dashboard plus terminal front door.
- The DESK operator-local helper remains pinned to the governed LiteLLM lane with deny-by-default MCP extension posture and direct terminal plus specialist CLI as the rollback path.

## Builder Front Door Boundary

- One bounded builder front door is now shadow-adopted in Athanor for `multi_file_implementation` with `private_but_cloud_allowed`, `repo_worktree`, and `needs_github=false`: `builder:codex:direct_cli`.
- The adopted contract is owned by `config/automation-backbone/operator-surface-registry.json`, `config/automation-backbone/lane-selection-matrix.json`, and `config/automation-backbone/failure-routing-matrix.json`, with `/builder` remaining a route inside the canonical command center instead of a second portal.
- That route remains approval-gated and must publish a resumable handle, structured `ResultPacket`, and passing `VerificationContract` state before success is reported.
- External bootstrap builders remain the live bootstrap stack until a separate bounded rollout decision advances beyond the current shadow-adopted, `linked_not_live` posture; this tranche does not silently widen into primary builder takeover.
- Any widening beyond the proved `builder:codex:direct_cli` slice requires a new packet-backed proof tranche; pilots and deferred adapters remain planned or bounded until then.

## Gateway Onboarding Boundary

- The canonical gateway env contract is `ATHANOR_LITELLM_URL` plus `ATHANOR_LITELLM_API_KEY`.
- Compatibility variables such as `OPENAI_API_BASE` and `OPENAI_API_KEY` are shims only and remain subordinate to the Athanor LiteLLM env contract.
- Devstack onboarding notes may explain setup, but `provider-catalog.json`, `routing-taxonomy-map.json`, `credential-surface-registry.json`, and `operator-runbooks.json` remain the adopted authority for gateway posture.
- Continue, Cline, and Roo Code adapter configs must be generated from the devstack adapter-profile generator and must not carry live secret values in tracked files.

## Prune Policy

- Delete stale docs, scripts, configs, and generated outputs once a verified replacement exists.
- Keep material only for audit or legal history, recovery evidence, active migration or cutover work, or a live runbook with no verified replacement.
- Do not leave misleading files in active truth locations with warning banners if they can simply be removed or archived.

## Validation

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_documentation_index.py --check`
- `python scripts/generate_project_maturity_report.py --check`
- `python scripts/generate_truth_inventory_reports.py --check`

If runtime, registry, and doc truth disagree, the disagreement itself is a bug and must be resolved or recorded as explicit drift.
