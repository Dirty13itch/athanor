# Agent Route Surface Code Packet

## Objective

Bind the route implementation surfaces into one explicit publication slice so route code and route-contract proof are separated cleanly.

## Scope

- `projects/agents/src/athanor_agents/routes/bootstrap.py`
- `projects/agents/src/athanor_agents/routes/model_governance.py`
- `projects/agents/src/athanor_agents/routes/operator_work.py`
- `projects/agents/src/athanor_agents/routes/plans.py`
- `projects/agents/src/athanor_agents/routes/projects.py`
- `projects/agents/src/athanor_agents/routes/research.py`
- `projects/agents/src/athanor_agents/routes/tasks.py`

## Why This Exists

- `agent-route-contract-follow-on` needs source-code ownership kept separate from test-contract ownership.
- The route family should clear through two bounded packets, not one broad bucket with mixed code and tests.
- This packet leaves only the contract and CLI verification residue for the follow-on slice.

## Validation

- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Route implementation paths classify into `agent-route-contract-surface-code`.
- `agent-route-contract-follow-on` advances to `route-contract-tests`.
- The publication queue no longer reports these source files as deferred family residue.

## Rollback

- Restore the listed route surface files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
