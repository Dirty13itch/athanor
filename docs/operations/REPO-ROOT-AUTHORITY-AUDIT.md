# Repo Root Authority Audit

Last updated: 2026-04-14

## Purpose

This audit records the current boundary split among:

- `C:/Athanor`
- `C:/athanor-devstack`
- `C:/Users/Shaun/dev/athanor-next`

It is anchored to:

- `config/automation-backbone/repo-roots-registry.json`
- `docs/operations/REPO-ROOTS-REPORT.md`
- `STATUS.md`
- `PROJECT.md`
- `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- `C:/athanor-devstack/STATUS.md`
- `C:/athanor-devstack/PROJECT.md`
- `C:/athanor-devstack/docs/DEVSTACK-STACK-CANON.md`
- `C:/Users/Shaun/dev/athanor-next/AGENTS.md`
- `C:/Users/Shaun/dev/athanor-next/PROJECT.md`
- `C:/Users/Shaun/dev/athanor-next/docs/design/athanor-next.md`

## Decision Summary

| Root | Keep separate | Authority | What belongs there | What must not live there |
| --- | --- | --- | --- | --- |
| `C:/Athanor` | Yes | `implementation-authority` | adopted code, registries, validators, runtime packets, canonical current-state docs, deployment truth, generated truth | speculative future capability design as the only source, stale lineage docs, competing side-root startup truth |
| `C:/athanor-devstack` | Yes | `build-system` | concept/prototype/proved work, proving harnesses, promotion packets, strategy, atlas compile inputs, experimental services before adoption | live routing truth, live provider posture, runtime policy, secret or operator repair truth that exists only here after adoption |
| `C:/Users/Shaun/dev/athanor-next` | No as a parallel build root; yes only as a bounded lineage/incubation archive | `incubation` | unique historical design intent, selective next-gen ideas not yet normalized elsewhere, archive evidence for harvest | active implementation work, live startup authority, duplicate project ownership, deployment truth, operator runbooks for the live system |

## What Is Recommended To Remain Separate

### `C:/Athanor`

This root should remain separate because it is the only place allowed to combine:

- code authority
- registry authority
- validation authority
- deployment contract authority
- canonical operator-facing current-state docs

It already has the right shape for the adopted system:

- `projects/agents`
- `projects/dashboard`
- `projects/gpu-orchestrator`
- `projects/ws-pty-bridge`
- `config/automation-backbone`
- `scripts`
- `ansible`
- generated operations reports

Anything that changes runtime truth, topology truth, provider posture, autonomy scope, or operator behavior belongs here.

### `C:/athanor-devstack`

This root should also remain separate.

Its structure is usefully different from Athanor:

- `services/` is prototype-heavy instead of deployment-authoritative
- `configs/` is forge-oriented instead of live control-plane truth
- `docs/promotion-packets/` makes adoption explicit
- `reports/master-atlas/latest.json` is a compiled coordination surface, not a runtime source of truth

This separation creates real value:

- high-churn proving work does not pollute Athanor core
- promotion can be explicit and reviewable
- packet discipline prevents speculative systems from silently becoming real systems

Devstack should remain the place where future capability work begins, but it should stop at `proved`.

## What Should Not Remain Parallel

### `C:/Users/Shaun/dev/athanor-next`

This root should not remain a parallel full-code Athanor root.

The physical tree is the clearest signal:

- the top-level shape largely mirrors Athanor: `ansible`, `assets`, `docs`, `evals`, `projects`, `recipes`, `scripts`, `services`, `tests`
- the project tree mirrors Athanor almost exactly: `agents`, `comfyui-workflows`, `dashboard`, `eoq`, `gpu-orchestrator`, `kindred`, `ulrich-energy`, `ws-pty-bridge`

That is not a clean incubation repo. It is a second near-full Athanor tree with older operating assumptions.

The repo-roots registry is already correct that `athanor-next` is only `incubation`, but the folder shape still behaves like a shadow implementation root. That is the real drag.

## Current Drag and Why It Matters

### 1. `athanor-next` still looks operable

`athanor-next` still contains startup-plausible files such as:

- `STATUS.md`
- `PROJECT.md`
- `docs/archive/BUILD-MANIFEST.md`
- `docs/SYSTEM-SPEC.md`
- `docs/design/athanor-next.md`

Those documents still read like live operating guidance unless the reader already knows the newer authority model.

That creates:

- wrong-startup risk
- stale-runbook risk
- path bleed in future agent sessions
- needless hesitation about which repo owns what

### 2. `athanor-next` duplicates core project ownership

Because the project tree overlaps almost one-for-one with Athanor, future changes to:

- `projects/agents`
- `projects/dashboard`
- `projects/gpu-orchestrator`
- `projects/ws-pty-bridge`

can start in the wrong place.

That is worse than a stale-doc problem. It is structural authority confusion.

### 3. `athanor-devstack` is mostly clean, but some operational asks still leak into it

Devstack is the right separate repo, but it still creates drag when operator-runtime needs appear in build-system docs, especially around:

- provider repair asks
- pilot credential asks
- packet review tasks that are really Athanor-side adoption actions

That is acceptable only when those items remain explicitly packet-backed and mirrored from Athanor truth.

### 4. Runtime ownership is supposed to be split; incubation ownership is not

The `implementation-authority` versus `runtime-authority` split is governed and explicit. That is valid complexity.

The `Athanor` versus `athanor-next` split is not the same kind of split. It is mostly historical carryover and should be narrowed hard.

## Boundary Rules By Content Type

| Content type | Home | Rule |
| --- | --- | --- |
| live topology, routing, provider posture, autonomy phase, runtime ownership | `C:/Athanor` | canonical only |
| validators, collectors, generated truth, runtime packets | `C:/Athanor` | canonical only |
| adopted operator/runtime code | `C:/Athanor` | canonical only |
| future capability designs and proving services | `C:/athanor-devstack` | until adopted |
| promotion packets and forge-board status | `C:/athanor-devstack` | draft/proved lane only |
| next-gen strategic intent not yet normalized | `C:/athanor-devstack` or archived lineage docs | not `athanor-next` project code by default |
| historical build manifests, old system specs, planning-era architecture narratives | archive or lineage-only root | must not present as live startup truth |

## Recommended Durable Placement

### Keep in `C:/Athanor`

- all registry-backed truth
- all runtime packet and ownership contracts
- all validators and truth generators
- all adopted platform code
- all current operator runbooks
- any tenant or sidecar that is already live and packet-governed

### Keep in `C:/athanor-devstack`

- strategy
- prototype services
- benchmark and eval harnesses
- proving-only gateway or creative pipelines
- draft promotion packets
- master-atlas compile inputs and build-system coordination docs

### Narrow in `C:/Users/Shaun/dev/athanor-next`

This root should be treated as:

- lineage archive
- selective design mine
- incubation evidence only

It should no longer be treated as a place to start feature work in:

- `projects/`
- `ansible/`
- `services/`
- `scripts/`
- `tests/`

unless a specific salvage pass is intentionally opened and the destination is Athanor or devstack.

## Concrete Calls

### Call 1: `C:/Athanor` remains the only implementation authority

This is already correct and should not change.

### Call 2: `C:/athanor-devstack` remains separate as the forge

This is also correct and should not collapse into Athanor.

### Call 3: `C:/Users/Shaun/dev/athanor-next` should be downgraded from parallel repo to bounded lineage lane

This is the most important cleanup call.

The durable rule should be:

- no new canonical implementation work starts in `athanor-next`
- no live operational truth is maintained there
- unique surviving value is harvested into Athanor or devstack
- the repo remains only as lineage/incubation evidence until it can be frozen further

## Operational Consequences

Future work should route like this:

1. If it changes live truth, deployment truth, runtime truth, or operator behavior, start in `C:/Athanor`.
2. If it is future capability design, proving, or packet drafting, start in `C:/athanor-devstack`.
3. If it comes from `athanor-next`, treat it as salvage or archive review, not as an active build root.

## Cleanup Target

The end-state should be:

- Athanor: active adopted system
- devstack: active forge
- athanor-next: bounded lineage archive with clearly non-authoritative startup language

That split minimizes drag while preserving the useful historical and incubation value.
