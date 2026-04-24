# Agent Route Contract and CLI Tests Packet

## Objective

Close the remaining route proof residue by binding the route contract tests and CLI router contract test into one explicit publication slice.

## Scope

- `projects/agents/tests/test_bootstrap_route_contract.py`
- `projects/agents/tests/test_foundry_route_contract.py`
- `projects/agents/tests/test_model_governance_route_contract.py`
- `projects/agents/tests/test_operator_work_route_contract.py`
- `projects/agents/tests/test_task_route_contract.py`
- `scripts/tests/test_cli_router_contracts.py`

## Why This Exists

- The route family is not clearable with source-code ownership alone because `scripts/tests/test_cli_router_contracts.py` is part of the same deferred residue.
- Folding the CLI router contract into this packet keeps the family at two bounded tranches instead of reopening a third micro-slice.
- This is the final route-family proof packet before the controller rotates to proof-and-ops residue.

## Validation

- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Route contract and CLI test paths classify into `agent-route-contract-tests`.
- `agent-route-contract-follow-on` has `match_count = 0`.
- The blocker execution plan rotates to `control-plane-proof-and-ops-follow-on`.

## Rollback

- Restore the listed route/CLI test files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
