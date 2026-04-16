# Athanor Capability Promotion

This document records how work moves from the Athanor build system into the adopted system.

## Promotion Model Snapshot

There are four lanes:

- `C:\Athanor` - adopted system and implementation authority
- `C:\athanor-devstack` - build system and proving lane
- `C:\Users\Shaun\.codex` - operator-local and cross-repo control surface
- Claude archives - searchable evidence only

For this snapshot, the rule is:

- invent and prove in devstack
- adopt and govern in Athanor
- keep workstation-local behavior in Codex home
- keep Claude material as evidence, not authority

## Authority Classes

| Class | Meaning |
|-------|---------|
| `adopted_system` | Canonical Athanor implementation and adopted runtime-facing truth |
| `build_system` | Devstack design, prototype, and proving truth |
| `operator_local` | Codex-home and workstation-local operator surfaces |
| `archive_evidence` | Searchable evidence that must not outrank current truth |

## Capability Stages

| Stage | Owner | Meaning |
|-------|-------|---------|
| `concept` | devstack | Design intent only |
| `prototype` | devstack | Working slice exists |
| `proved` | devstack | Evidence is strong enough to request adoption |
| `adopted` | Athanor | Canonical truth exists in Athanor |
| `retired` | Athanor | Capability is superseded but preserved for lineage |

## Promotion Packet Contract

Every capability graduating from devstack into Athanor needs a promotion packet with:

- capability name
- current stage
- owner
- source repo and source artifacts
- proof artifacts
- acceptance criteria
- target runtime surface
- required Athanor docs, registry, or code updates
- rollback or disable path
- archive instructions for superseded devstack material

## Negative Rules

- No live routing, topology, runtime policy, service dependency, or operational truth may exist only in devstack after adoption.
- No high-churn prototype, benchmark harness, experiment, or design packet should be forced into Athanor before it is proved.
- A promotion is incomplete until Athanor-side canonical representation exists.

## Current Tracking Surface

`config/automation-backbone/capability-adoption-registry.json` is the machine-readable ledger for build-system capabilities that matter to Athanor.

Use it to track:

- what exists only in devstack
- what is ready for adoption
- what is already adopted
- what has been retired
- which promotion packet owns the handoff
- which runtime-ownership lanes and packets carry the live rollout

The current devstack packet drafts live in `C:\athanor-devstack\docs\promotion-packets\`.
The current devstack forge board lives in `C:\athanor-devstack\docs\operations\DEVSTACK-FORGE-BOARD.md`.

## Claude Durable-Value Mapping

The Athanor `.claude` tree is a triage source, not first truth. Durable value from that tree maps like this:

- `.claude/commands/audit.md` plus `.claude/skills/verify-inventory/SKILL.md` map to the validator and truth-inventory report surfaces
- `.claude/commands/morning.md` plus `.claude/skills/state-update.md` map to Athanor top-entry status discipline and current-state update surfaces
- `.claude/rules/litellm.md` and `.claude/rules/vllm.md` map to provider, routing, and model-deployment truth

Everything else in `.claude` stays archive-first unless it is packeted into Athanor truth explicitly.
