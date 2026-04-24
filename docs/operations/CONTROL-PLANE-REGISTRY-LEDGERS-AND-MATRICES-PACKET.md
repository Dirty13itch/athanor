# Control-Plane Registry Ledgers and Matrices Packet

## Objective

Bound the first `control-plane-registry-and-routing` sub-tranche into an explicit publication slice so the registry-ledger residue stops appearing as anonymous program-slice debt.

## Scope

- `config/automation-backbone/docs-lifecycle-registry.json`
- `config/automation-backbone/economic-dispatch-ledger.json`
- `config/automation-backbone/lane-selection-matrix.json`
- `config/automation-backbone/executive-kernel-registry.json`

## Why This Exists

- The publication triage matcher was still treating these files as deferred-family residue.
- The continuity controller needs this sub-tranche to become owned work before it can advance to the routing-policy and runtime follow-ons.
- This packet keeps registry and routing authority explicit without pretending the remaining subscription-policy and agent-runtime deltas are already closed.

## Validation

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Registry-ledger paths classify into the publication slice `control-plane-registry-ledgers-and-matrices`.
- `control-plane-registry-and-routing` remains only with the routing-policy, runtime, and test residue that belongs to later sub-tranches.
- The blocker execution plan advances to `routing-policy-and-subscription-lane`.

## Rollback

- Restore the four registry surfaces and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
