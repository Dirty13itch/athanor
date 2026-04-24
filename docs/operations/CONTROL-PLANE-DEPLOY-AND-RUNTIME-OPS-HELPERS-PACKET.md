# Control-Plane Deploy and Runtime Ops Helpers Packet

## Objective

Close the proof-and-ops family by binding the remaining deploy and runtime helper residue into one explicit publication slice.

## Scope

- `projects/agents/docker-compose.yml`
- `ansible/roles/agents/templates/docker-compose.yml.j2`
- `scripts/.cluster_config.unix.sh`
- `scripts/.deploy-agents.unix.sh`
- `scripts/deploy-agents.sh`

## Why This Exists

- These files are the final deploy/runtime helper residue after the Ralph/truth and proof-generator slices are isolated.
- The Foundry agents compose template is part of the same deploy-helper authority surface and should not fall back into generic deployment-authority debt.
- They should remain packet-backed without widening live runtime mutation scope.
- Clearing this packet should collapse `control-plane-proof-and-ops-follow-on` to zero.

## Validation

- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`
- `python scripts/validate_platform_contract.py`

## Success Condition

- Deploy/runtime helper paths classify into `control-plane-deploy-and-runtime-ops-helpers`.
- The governed Foundry agents template delta classifies into this slice instead of `deployment-authority-follow-on`.
- `control-plane-proof-and-ops-follow-on` has `match_count = 0`.
- The blocker map reaches zero remaining publication families.

## Rollback

- Restore the listed deploy/runtime helper files, the governed agents template, and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
