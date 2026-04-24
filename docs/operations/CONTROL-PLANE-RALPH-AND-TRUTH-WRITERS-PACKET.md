# Control-Plane Ralph and Truth Writers Packet

## Objective

Bind Ralph and the canonical truth-writer residue into one explicit publication slice so the proof-and-ops family stops hiding core truth-writer debt inside a generic control-plane bucket.

## Scope

- `scripts/run_ralph_loop_pass.py`
- `scripts/truth_inventory.py`
- `scripts/write_steady_state_status.py`
- `scripts/write_current_tree_partition.py`
- `scripts/write_value_throughput_scorecard.py`
- `scripts/tests/test_ralph_loop_contracts.py`
- `scripts/tests/test_truth_inventory_path_overrides.py`
- `scripts/tests/test_write_current_tree_partition.py`
- `scripts/tests/test_write_steady_state_status.py`
- `scripts/tests/test_write_value_throughput_scorecard.py`

## Why This Exists

- The proof-and-ops family cannot clear until Ralph, truth inventory, and the front-door writers are explicitly packeted.
- These files are one authority cluster: claim rotation, truth inventory resolution, steady-state posture, current-tree partition, and throughput writing.
- Clearing them leaves only the remaining proof generators and deploy/runtime helpers.

## Validation

- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`
- `python scripts/validate_platform_contract.py`

## Success Condition

- Ralph and truth-writer paths classify into `control-plane-ralph-and-truth-writers`.
- `control-plane-proof-and-ops-follow-on` advances to `proof-generators-and-validators`.
- The publication queue no longer reports these files as deferred family residue.

## Rollback

- Restore the listed Ralph/truth files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
