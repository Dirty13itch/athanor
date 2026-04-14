# Athanor Operating System

This file defines the standing operating model for Athanor after the shift to registry-backed truth and aggressive prune discipline.

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

Live loop surfaces:
- `scripts/run_ralph_loop_pass.py`
- `reports/ralph-loop/latest.json`
- `docs/operations/ATHANOR-RALPH-LOOP-PROGRAM.md`
- `docs/operations/ATHANOR-RECONCILIATION-END-STATE.md`
- `docs/operations/REPO-ROOT-AUTHORITY-AUDIT.md`

## Authority Model

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

- The bounded Goose shell path is owned by `config/automation-backbone/operator-surface-registry.json` surface `desk_goose_operator_shell` and runtime packet `desk-goose-operator-shell-rollout-packet`.
- Goose is now the adopted bounded shell orchestrator path, but it must remain subordinate to Athanor control-plane truth and must not become a second control plane or bypass the dashboard plus terminal front door.
- The DESK operator-local helper remains pinned to the governed LiteLLM lane with deny-by-default MCP extension posture and direct terminal plus specialist CLI as the rollback path.

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
