# Agent Execution Kernel Self-Improvement and Proving Packet

## Objective

Bind self-improvement and proving residue into one explicit publication slice so governed improvement logic stops appearing as anonymous execution-kernel debt.

## Scope

- `projects/agents/src/athanor_agents/proving_ground.py`
- `projects/agents/src/athanor_agents/self_improvement.py`
- `projects/agents/tests/test_self_improvement.py`

## Why This Exists

- The continuity controller should reach this slice immediately after the scheduler/research tranche.
- These files own proposal-first improvement admission, proving-ground evidence, and the conservative self-improvement boundary.
- Clearing them separately keeps product-compounding logic distinct from execution-kernel support utilities.

## Validation

- `cd projects/agents && TMPDIR=/tmp uv run --with pytest pytest tests/test_self_improvement.py -q`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Self-improvement and proving paths classify into `agent-execution-kernel-self-improvement-and-proving`.
- `agent-execution-kernel-follow-on` advances to the final support-and-tests tranche.
- The publication queue no longer reports these files as deferred family residue.

## Rollback

- Restore the listed self-improvement/proving files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
