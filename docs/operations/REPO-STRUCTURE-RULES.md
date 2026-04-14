# Athanor Repo Structure Rules

This document is the placement contract for Athanor implementation-authority material.
Use it when deciding where new files belong, what should be generated versus maintained, and what should be deleted instead of preserved.

## Current Read

### Authority boundaries that should stay fixed

- `C:\Athanor` is the implementation-authority root.
- `C:\athanor-devstack` is the build-system and proving lane and must stay separate unless a capability is explicitly promoted back into Athanor truth.
- `C:\Users\Shaun\dev\athanor-next` is an incubation lane and must stay separate until a deliberate extraction or promotion happens.
- `/home/shaun/repos/athanor`, `/opt/athanor`, `/home/shaun/.athanor`, and the host-specific runtime roots are governed runtime state, not places where implementation authority should silently move.

Those boundaries are already mostly correct. The structural goal is not to collapse them into one tree; it is to keep their authority model explicit so they stop competing.

### Well-separated

- `config/automation-backbone/` is acting as the canonical control-plane source layer.
  It already holds registries, contracts, ledgers, and policy truth well enough to stay authoritative.
- `reports/` is mostly acting as the generated evidence lake.
  Families like `truth-inventory/`, `deployment-drift/`, `bootstrap/`, and `ralph-loop/` are already recognizable report lanes.
- `projects/` is still the right home for implementation code.
  `projects/agents/`, `projects/dashboard/`, and `projects/gpu-orchestrator/` are not the current structure problem.
- `docs/operations/` is the right home for active operator-facing prose.
  The docs-lifecycle registry already gives the repo a formal way to distinguish canonical, generated, reference, and archive material.
- `ansible/` is already the right home for packaging and deployment contracts.
  Those host/runtime surfaces should continue to live there instead of drifting into ad hoc product-local helpers.

### Muddled

- `scripts/` is overloaded.
  Stable operator entrypoints, reusable helper modules, deploy wrappers, one-off migrations, MCP bridges, systemd units, and scratch-era helpers still live side by side at the top level.
- `docs/operations/` mixes canonical and generated files with similar names.
  That is workable only because `config/automation-backbone/docs-lifecycle-registry.json` exists; filenames alone are not enough to infer authority.
- Some generated artifacts still live inside source trees.
  `projects/dashboard/src/generated/` is a valid exception because the product needs checked-in feeds, but it must stay an explicit exception rather than becoming the default pattern.
- Scratch and export surfaces are too implicit.
  `tmp/`, `output/`, repo-root `tmp_*.py`, and ad hoc script probes create ambiguity about what is durable, what is disposable, and what should be tracked.
- `services/` still reads like a normal top-level implementation tree even though it is really transitional.
  That is a structure drag because live-looking system surfaces are split between `services/` and `projects/agents`.
- `projects/reports/` still reads like a real project root even though it is only a compatibility shim.
  That should stay explicit so nobody mistakes it for the canonical reports tree.

## Keep vs Separate vs Transitional

### Keep together

- `projects/agents`, `projects/dashboard`, `projects/gpu-orchestrator`, and `projects/ws-pty-bridge`
- `config/automation-backbone/`
- `reports/`
- `docs/operations/`
- `scripts/`
- `ansible/`

These are already the right homes for their current responsibilities.

### Keep separate

- `C:\Athanor` vs `C:\athanor-devstack`
- `C:\Athanor` vs `C:\Users\Shaun\dev\athanor-next`
- implementation-authority roots vs runtime-state roots
- canonical truth vs generated evidence

These separations are healthy. The problem is not separation itself; it is shadow authority when the separations are not explicit.

### Transitional and no-growth

- `services/`
- `projects/reports/`
- cross-root generated atlas/dashboard consumption surfaces that are acceptable only because script ownership is explicit

These should not quietly expand until a deliberate migration decision says otherwise.

## Durable Placement Rules

### 1. `config/automation-backbone/` is for mutable control-plane truth only

Allowed:

- registries
- contracts
- ledgers
- policy maps
- packet registries
- topology and ownership truth

Not allowed:

- generated snapshots copied from `reports/`
- ad hoc probes
- transient exports
- human narrative docs

Rule:

- if a file is the thing the system should believe, it belongs here
- if a file is evidence about whether that truth is currently satisfied, it belongs in `reports/`

### 2. `reports/` is for generated evidence and machine-written snapshots

Allowed:

- `latest.json` style current snapshots
- machine-written markdown reports
- runtime probes
- eval artifacts
- drift audits
- historical report families

Required pattern:

- current evidence stays in a named family such as `reports/truth-inventory/`
- historical rollups stay under that family or `reports/history/`
- report directories should describe the evidence family, not the script name that wrote them

Not allowed:

- canonical source truth
- hand-maintained planning prose
- implementation code

### 3. `docs/operations/` is for active human-facing operating material

Allowed:

- canonical operator docs
- active program docs
- runbooks
- packets
- generated markdown reports that are explicitly tracked by the docs-lifecycle registry

Rule:

- every active doc under `docs/operations/` must be classified in `config/automation-backbone/docs-lifecycle-registry.json`
- generated docs under `docs/operations/` must have a registered generator and pass freshness validation
- filename alone does not determine authority; the registry does

### 4. Generated artifacts may live in source trees only when the product runtime needs them

Current allowed checked-in exception:

- `projects/dashboard/src/generated/`

Related governed exception:

- `C:\athanor-devstack\reports\master-atlas\latest.json` feeding `C:\Athanor\projects\dashboard\src\generated\master-atlas.json`

Rule:

- generated-in-source artifacts are allowed only when a shipped surface reads them directly
- they must be reproducible from canonical truth outside that source tree
- they must never become the only source of truth

### 5. `scripts/` is for stable operator entrypoints and reusable script libraries

Allowed at `scripts/` top level:

- stable deploy entrypoints
- stable validators
- stable collectors
- stable generators
- stable audits
- shared script libraries imported by those entrypoints

Not allowed at `scripts/` top level:

- throwaway probes
- session-specific scratch helpers
- renamed `tmp_*` experiments

Rule:

- `scripts/tests/` is for contract and smoke suites for script surfaces
- disposable probes belong in `tmp/` and should stay untracked
- when a probe becomes reusable, promote it into a properly named script or library module

### 6. `tmp/` is the only repo-local scratch lane

Allowed:

- temporary probes
- one-off helper output
- local export fragments used during active investigation

Rule:

- nothing in `tmp/` is authoritative
- no scratch file should be created at repo root
- no scratch file should be promoted into tracked repo truth without rename and placement review

### 7. `output/` is for disposable packaged output, not truth

Allowed:

- deploy tarballs
- probe captures
- export bundles

Not allowed:

- canonical reports
- authoritative configs
- long-lived review artifacts that belong in `reports/`

### 8. Archive and reference material must stay out of active control paths

Rule:

- historical reasoning goes under `docs/archive/`
- helpful but non-authoritative context stays `reference` in the lifecycle registry
- active startup or operator docs must not point first to archive material when canonical or generated truth exists

## Immediate Cleanup Decisions From This Audit

- repo-root `tmp_*.py` probes are scratch leakage and should not remain
- `scripts/tmp_*` tracked helpers are scratch leakage and should be deleted or moved into `tmp/`
- stale helpers already declared deleted in startup truth must not remain in `scripts/`
- duplicate entries in the docs-lifecycle registry are contract drift and must fail validation
- `services/` must stay explicitly transitional and no-growth until its remaining live surfaces are either migrated or intentionally reclassified
- `projects/reports/` must stay clearly labeled as a compatibility shim and must not become a second canonical reports root

## Enforced Rules

The validator should fail when:

- a repo-root `tmp_*` file exists
- a tracked `scripts/tmp_*` file exists
- `config/automation-backbone/docs-lifecycle-registry.json` contains duplicate paths

## Practical Decision Test

When placing a new file, use this order:

1. Is it canonical truth the system should believe?
   Put it in `config/automation-backbone/`.
2. Is it generated evidence about current state?
   Put it in `reports/`.
3. Is it active human-facing operating guidance?
   Put it in `docs/operations/` and classify it in the lifecycle registry.
4. Is it source code or product-local documentation?
   Put it under the owning `projects/*` root.
5. Is it disposable investigation residue?
   Put it in `tmp/` or do not track it at all.
