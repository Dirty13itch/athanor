# Agent Execution Kernel Support and Tests Packet

## Objective

Close the remaining execution-kernel support and regression residue after queue-state, scheduler, and self-improvement are packeted.

## Scope

- `projects/agents/src/athanor_agents/autonomous_queue.py`
- `projects/agents/src/athanor_agents/capability_intelligence.py`
- `projects/agents/src/athanor_agents/repo_paths.py`
- `projects/agents/tests/test_repo_paths.py`

## Why This Exists

- These files remain after the main execution lanes are isolated but still participate in execution-kernel truth.
- They should not keep the whole family open behind a vague `execution-kernel-tests` label.
- This packet makes the final support residue explicit so the family can fall to zero cleanly.

## Validation

- `cd projects/agents && TMPDIR=/tmp uv run --with pytest pytest tests/test_repo_paths.py -q`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- Support and test paths classify into `agent-execution-kernel-support-and-tests`.
- `agent-execution-kernel-follow-on` has `match_count = 0`.
- The blocker execution plan rotates to `agent-route-contract-follow-on`.

## Rollback

- Restore the listed support files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
