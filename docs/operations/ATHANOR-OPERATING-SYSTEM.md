# Athanor Operating System

This file defines the standing operating model for Athanor after the shift to registry-backed truth and aggressive prune discipline.

## Source of Truth

The editable control plane lives in [config/automation-backbone](../../config/automation-backbone).

Primary registries:
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

## Authority Model

- `C:\Athanor` is the implementation authority for config, contracts, inventories, validation rules, and canonical current-state docs.
- `/home/shaun/repos/athanor` on DEV is the runtime and deployment authority until deployment is clean enough to be a strict mirror.
- `C:\Users\Shaun\dev\athanor-next` is an incubation lane and cannot define live truth without an explicit promotion packet.

## Truth Rules

- Runtime truth outranks memory and stale docs.
- Registry truth outranks helper scripts and hardcoded literals.
- Official provider terms, observed runtime state, and heuristic estimates are distinct classes and must not be conflated.
- The DEV `:8760` cutover is complete; any autonomy expansion now depends on policy scope and provider confidence, not the retired governor facade.
- Post-cutover autonomy scope is owned by `autonomy-activation-registry.json` and starts at software-core only.
- Runtime mutations remain approval-gated even after first activation.
- Secret surfaces may be reported by presence, location, owner, and env contract only. Secret values never belong in tracked truth.
- If a doc cannot justify its lifecycle class, it should be archived or deleted.

## Execution Loop

1. Validate the registry and generated-doc layer.
2. Generate fresh reports for hardware, model deployment, provider catalog, repo roots, drift, and secret surfaces.
3. Compare runtime probes to registry truth and mark any divergence explicitly as drift.
4. Route any cross-repo or side-root discovery into the reconciliation source registry and the ecosystem control docs before treating it as active program scope.
5. Keep the total-completion program registry and completion doc aligned with the current execution frontier.
6. Close the highest-leverage drift or contract bug.
7. Rerun the relevant gate.
8. Delete or freeze superseded material once the replacement truth is verified.

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
