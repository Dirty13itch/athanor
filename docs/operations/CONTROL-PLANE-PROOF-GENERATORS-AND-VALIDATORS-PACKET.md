# Control-Plane Proof Generators and Validators Packet

## Objective

Bind the remaining proof-generation and validation helpers into one explicit publication slice.

## Scope

- `scripts/generate_capability_intelligence.py`
- `scripts/probe_openhands_bounded_worker.py`
- `scripts/proof_workspace_contract.py`
- `scripts/sync_github_portfolio_registry.py`
- `scripts/tests/test_capability_intelligence_contracts.py`
- `scripts/tests/test_proof_workspace_contract.py`
- `scripts/tests/test_sync_github_portfolio_registry.py`
- `scripts/tests/test_validate_platform_contract_monitoring_contracts.py`

## Why This Exists

- These helpers are proof-lane infrastructure, not Ralph/truth-writer ownership and not deploy/runtime helper ownership.
- The family cannot clear until the capability-intelligence, workspace-contract, and GitHub portfolio proof surfaces are packeted explicitly.
- This packet leaves only the deploy/runtime helper residue behind it.

## Validation

- `TMPDIR=/tmp uv run --with pytest pytest scripts/tests/test_capability_intelligence_contracts.py scripts/tests/test_proof_workspace_contract.py scripts/tests/test_sync_github_portfolio_registry.py scripts/tests/test_validate_platform_contract_monitoring_contracts.py -q`
- `python scripts/generate_publication_deferred_family_queue.py`
- `python scripts/write_blocker_map.py --json`
- `python scripts/write_blocker_execution_plan.py --json`
- `python scripts/validate_platform_contract.py`

## Success Condition

- Proof-generator and validator paths classify into `control-plane-proof-generators-and-validators`.
- `control-plane-proof-and-ops-follow-on` advances to `deploy-and-runtime-ops-helpers`.
- The publication queue no longer reports these files as deferred family residue.

## Rollback

- Restore the listed proof-generator/validator files and this packet doc.
- Regenerate the publication queue, blocker map, blocker execution plan, and steady-state status.
