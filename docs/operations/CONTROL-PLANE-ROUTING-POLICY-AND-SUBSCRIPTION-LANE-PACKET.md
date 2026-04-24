# Control-Plane Routing Policy and Subscription Lane Packet

## Objective

Close the remaining `control-plane-registry-and-routing` residue after the registry-ledger slice by moving the routing policy, routing-aware runtime surfaces, and their proof tests into one explicit publication slice.

## Scope

- `projects/agents/config/subscription-routing-policy.yaml`
- `projects/agents/src/athanor_agents/backbone.py`
- `projects/agents/src/athanor_agents/model_governance.py`
- `projects/agents/src/athanor_agents/subscriptions.py`
- `projects/agents/tests/test_model_governance.py`
- `projects/agents/tests/test_subscription_policy.py`

## Why This Exists

- The publication controller now cleared the registry-ledger sub-tranche and needs a bounded follow-on instead of reusing the old family bucket.
- These files are one coherent routing lane change: ordinary-routing posture, subscription economics, capability-aware provider scoring, and the scheduled-job/runtime read surfaces that expose that policy.
- Clearing this packet should collapse the entire `control-plane-registry-and-routing` deferred family and rotate the controller to the execution-kernel tranche.

## Validation

- `python scripts/validate_platform_contract.py`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/write_steady_state_status.py --json`

## Success Condition

- The deferred family `control-plane-registry-and-routing` has `match_count = 0`.
- `blocker-execution-plan.json` rotates to `agent-execution-kernel-follow-on`.
- The front door and continuity controller stop pointing at the cleared routing family.

## Rollback

- Restore the routing policy, runtime surfaces, proof tests, and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
