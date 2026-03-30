# Runtime Migration Report

Generated from `config/automation-backbone/runtime-migration-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-03-29.2`
- Migration seams tracked: `1`
- Runtime-owned callers tracked: `9`

| Status | Count |
| --- | --- |
| `retired` | 1 |

| Implementation state | Count |
| --- | --- |
| `migrated` | 9 |

| Runtime cutover state | Count |
| --- | --- |
| `cutover_verified` | 9 |

- Latest live content evidence snapshot: `2026-03-30T06:08:39.274399+00:00`
- Observed live `:8760` references: `0`
- Planned callers no longer observed in the live runtime grep scan: `9`
- Sync-required callers: `2`
- Already-synced callers: `7`
- Blocked callers: `0`

| Live content state | Count |
| --- | --- |
| `content_drift` | 2 |
| `content_match` | 7 |

## dev-governor-facade-8760-callers

- Status: `retired`
- Severity: `high`
- Runtime surface: `athanor-governor.service on DEV :8760`
- Runtime owner: `/home/shaun/repos/athanor on DEV`
- Canonical owner: `C:\Athanor`
- Runtime listener: `http://127.0.0.1:8760`
- Runtime backup root: `/home/shaun/.athanor/backups/governor-facade-cutover`
- Systemd backup target: `/home/shaun/.athanor/backups/governor-facade-cutover/athanor-governor.service`
- Canonical successor surfaces: `/v1/tasks`, `/v1/tasks/stats`, `/v1/governor`
- Maintenance window required: `False`
- Observed at: `2026-03-29T02:48:53Z`
- Observed runtime repo head: `075490f`
- Runbook: [`docs/runbooks/governor-facade-retirement.md`](/C:/Athanor/docs/runbooks/governor-facade-retirement.md)
- Live content evidence snapshot: `2026-03-30T06:08:39.274399+00:00`
- Live observed `:8760` references: `0`

### Acceptance Criteria

- All runtime-owned callers that still hit :8760 are migrated to canonical task-engine, governor, or topology-owned health surfaces.
- No new GET /queue or GET /health journal entries land on athanor-governor after maintenance-window cutover.
- athanor-governor.service can be stopped without regressing dashboard, helper, or collector behavior.
- The repo-side compatibility facade is deleted after runtime cutover verification, leaving rollback evidence only.

### Delete Gate

- Every observed DEV runtime caller is covered by this migration registry.
- Every mapped caller already has a passing implementation-authority copy in C:\Athanor.
- The 2026-03-29 DEV cutover removed live :8760 helper traffic, retired athanor-governor.service, and the implementation-authority facade file is now deleted.

### Runtime-Owned Caller Map

| Order | Caller | Implementation | Runtime cutover | Sync strategy | Runtime target | Content sync | Rollback target | Observed `:8760` ref | Ask-first |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1` | `scripts/drift-check.sh` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/scripts/drift-check.sh` | `content_drift` | `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/drift-check.sh` | `False` | `True` |
| `2` | `scripts/smoke-test.sh` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/scripts/smoke-test.sh` | `content_drift` | `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/smoke-test.sh` | `False` | `True` |
| `3` | `services/cluster_config.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/cluster_config.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/cluster_config.py` | `False` | `True` |
| `4` | `services/gateway/main.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/gateway/main.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/gateway/main.py` | `False` | `True` |
| `5` | `services/governor/status_report.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/governor/status_report.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/status_report.py` | `False` | `True` |
| `6` | `services/governor/overnight.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/governor/overnight.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/overnight.py` | `False` | `True` |
| `7` | `services/governor/act_first.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/governor/act_first.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/act_first.py` | `False` | `True` |
| `8` | `services/governor/self_improve.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/governor/self_improve.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/self_improve.py` | `False` | `True` |
| `9` | `services/sentinel/checks.py` | `migrated` | `cutover_verified` | `backup_then_replace_from_implementation_authority` | `/home/shaun/repos/athanor/services/sentinel/checks.py` | `content_match` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/sentinel/checks.py` | `False` | `True` |

### Runtime Sync Verification Checklist

| Order | Caller | Sync decision | Implementation source | Runtime target | Backup target | Rollback ready |
| --- | --- | --- | --- | --- | --- | --- |
| `1` | `scripts/drift-check.sh` | `backup_then_replace_runtime_copy` | `C:\Athanor\scripts\drift-check.sh` | `/home/shaun/repos/athanor/scripts/drift-check.sh` | `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/drift-check.sh` | `True` |
| `2` | `scripts/smoke-test.sh` | `backup_then_replace_runtime_copy` | `C:\Athanor\scripts\smoke-test.sh` | `/home/shaun/repos/athanor/scripts/smoke-test.sh` | `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/smoke-test.sh` | `True` |
| `3` | `services/cluster_config.py` | `already_synced` | `C:\Athanor\services\cluster_config.py` | `/home/shaun/repos/athanor/services/cluster_config.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/cluster_config.py` | `True` |
| `4` | `services/gateway/main.py` | `already_synced` | `C:\Athanor\services\gateway\main.py` | `/home/shaun/repos/athanor/services/gateway/main.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/gateway/main.py` | `True` |
| `5` | `services/governor/status_report.py` | `already_synced` | `C:\Athanor\services\governor\status_report.py` | `/home/shaun/repos/athanor/services/governor/status_report.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/status_report.py` | `True` |
| `6` | `services/governor/overnight.py` | `already_synced` | `C:\Athanor\services\governor\overnight.py` | `/home/shaun/repos/athanor/services/governor/overnight.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/overnight.py` | `True` |
| `7` | `services/governor/act_first.py` | `already_synced` | `C:\Athanor\services\governor\act_first.py` | `/home/shaun/repos/athanor/services/governor/act_first.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/act_first.py` | `True` |
| `8` | `services/governor/self_improve.py` | `already_synced` | `C:\Athanor\services\governor\self_improve.py` | `/home/shaun/repos/athanor/services/governor/self_improve.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/self_improve.py` | `True` |
| `9` | `services/sentinel/checks.py` | `already_synced` | `C:\Athanor\services\sentinel\checks.py` | `/home/shaun/repos/athanor/services/sentinel/checks.py` | `/home/shaun/.athanor/backups/governor-facade-cutover/services/sentinel/checks.py` | `True` |

#### scripts/drift-check.sh

- Current purpose: Cluster-wide drift and service health helper
- Sync order: `1`
- Canonical targets: `scripts/cluster_config.sh`, `gateway:/health`, `memory:/health`, `dashboard:/api/overview`, `agent_server:/health`, `vllm_*:/health`, `ollama_workshop:/api/tags`
- Replacement owner paths: `scripts/drift-check.sh`, `scripts/cluster_config.sh`
- Expected runtime owner path: `/home/shaun/repos/athanor/scripts/drift-check.sh`
- Canonical replacement: Use the implementation-authority drift-check helper with cluster-config-owned service URLs and canonical health or /v1 probes instead of :8760.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `backup_then_replace_runtime_copy`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/drift-check.sh`
- Rollback ready: `True`
- Next action: Unexpected post-cutover drift; resync the runtime-owned file from implementation authority and reopen the migration seam.
- Cutover check: Script runs cleanly from implementation authority without any :8760 reference and the DEV runtime copy no longer journals facade traffic.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_local_helper_scripts_match_live_runtime_truth`, `bash scripts/drift-check.sh`
- Runtime file: `/home/shaun/repos/athanor/scripts/drift-check.sh`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\scripts\drift-check.sh`
- Implementation file exists: `True`
- Live content sync: `content_drift`
- Live `:8760` reference observed: `False`
- Runtime hash: `e64308aa7dee`
- Runtime size: `7071` bytes
- Runtime lines: `226`
- Implementation hash: `157c37b73ef2`
- Implementation size: `7101` bytes
- Implementation lines: `226`
- Notes: `2026-03-29 maintenance window verified the DEV runtime copy matches implementation authority and the post-cutover collector observed no live facade traffic.`

#### scripts/smoke-test.sh

- Current purpose: Minimal critical-surface smoke checker
- Sync order: `2`
- Canonical targets: `scripts/cluster_config.sh`, `gateway:/health`, `quality_gate:/health`, `agent_server:/health`, `litellm:/health`, `subscription_burn:/health`
- Replacement owner paths: `scripts/smoke-test.sh`, `scripts/cluster_config.sh`
- Expected runtime owner path: `/home/shaun/repos/athanor/scripts/smoke-test.sh`
- Canonical replacement: Use the implementation-authority smoke-test helper with cluster-config-owned canonical service URLs and no :8760 dependency.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `backup_then_replace_runtime_copy`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/scripts/smoke-test.sh`
- Rollback ready: `True`
- Next action: Unexpected post-cutover drift; resync the runtime-owned file from implementation authority and reopen the migration seam.
- Cutover check: Script runs cleanly from implementation authority and the DEV runtime copy no longer hits :8760.
- Repo-side gates: `python scripts/validate_platform_contract.py`, `bash scripts/smoke-test.sh`
- Runtime file: `/home/shaun/repos/athanor/scripts/smoke-test.sh`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\scripts\smoke-test.sh`
- Implementation file exists: `True`
- Live content sync: `content_drift`
- Live `:8760` reference observed: `False`
- Runtime hash: `c7f247b6de60`
- Runtime size: `1965` bytes
- Runtime lines: `51`
- Implementation hash: `1d791553df11`
- Implementation size: `1987` bytes
- Implementation lines: `51`
- Notes: none

#### services/cluster_config.py

- Current purpose: Shared canonical service URL and health-path resolver
- Sync order: `3`
- Canonical targets: `config/automation-backbone/platform-topology.json`, `services/cluster_config.py`, `get_health_url(service_id)`, `AGENT_SERVER_URL`
- Replacement owner paths: `services/cluster_config.py`, `config/automation-backbone/platform-topology.json`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/cluster_config.py`
- Canonical replacement: Use platform-topology-backed service resolution and remove any runtime-local governor URL fallback.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/cluster_config.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: DEV runtime repo no longer exports or defaults any localhost:8760 governor URL.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_local_helper_scripts_match_live_runtime_truth`, `python scripts/validate_platform_contract.py`
- Runtime file: `/home/shaun/repos/athanor/services/cluster_config.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\cluster_config.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `af150099834b`
- Runtime size: `4584` bytes
- Runtime lines: `138`
- Implementation hash: `af150099834b`
- Implementation size: `4584` bytes
- Implementation lines: `138`
- Notes: `This is the shared replacement seam for helper scripts that should consume topology-owned service URLs.`

#### services/gateway/main.py

- Current purpose: Aggregated service-health view for the gateway surface
- Sync order: `4`
- Canonical targets: `gateway:/health`, `agent_server:/health`, `quality_gate:/health`, `embedding:/health`, `reranker:/health`
- Replacement owner paths: `services/gateway/main.py`, `services/cluster_config.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/gateway/main.py`
- Canonical replacement: Monitor topology-owned service ids through get_health_url(service_id) and shared health snapshots instead of :8760.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/gateway/main.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Gateway health references canonical task-engine stats and topology-owned dependency ids instead of localhost:8760.
- Repo-side gates: `python scripts/run_service_contract_tests.py`, `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_local_helper_scripts_match_live_runtime_truth`
- Runtime file: `/home/shaun/repos/athanor/services/gateway/main.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\gateway\main.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `6a7d008aced9`
- Runtime size: `4338` bytes
- Runtime lines: `152`
- Implementation hash: `6a7d008aced9`
- Implementation size: `4338` bytes
- Implementation lines: `152`
- Notes: none

#### services/governor/status_report.py

- Current purpose: Operator-readable status summary generator
- Sync order: `5`
- Canonical targets: `agent_server:/v1/goals`, `agent_server:/v1/tasks/stats`, `agent_server:/v1/improvement/proposals`, `agent_server:/health`, `dashboard:/api/subscriptions/summary`
- Replacement owner paths: `services/governor/status_report.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/governor/status_report.py`
- Canonical replacement: Read posture, task, proposal, skill, and subscription truth from canonical agent-server and dashboard surfaces.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/status_report.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Helper reads canonical task and subscription summary surfaces only.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_automation_uses_canonical_task_routes`, `python scripts/validate_platform_contract.py`
- Runtime file: `/home/shaun/repos/athanor/services/governor/status_report.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\governor\status_report.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `cc4a69872ee5`
- Runtime size: `4072` bytes
- Runtime lines: `105`
- Implementation hash: `cc4a69872ee5`
- Implementation size: `4072` bytes
- Implementation lines: `105`
- Notes: none

#### services/governor/overnight.py

- Current purpose: Overnight pending-task dispatch helper
- Sync order: `6`
- Canonical targets: `agent_server:/v1/tasks?status=pending&limit=50`, `agent_server:/v1/tasks/dispatch`
- Replacement owner paths: `services/governor/overnight.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/governor/overnight.py`
- Canonical replacement: Dispatch pending work only through the canonical task engine.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/overnight.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Helper dispatches through /v1/tasks/dispatch and no longer reads /queue or /dispatch-and-run.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_automation_uses_canonical_task_routes`, `services/governor/tests/test_helper_contracts.py`
- Runtime file: `/home/shaun/repos/athanor/services/governor/overnight.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\governor\overnight.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `0e4c24916ae7`
- Runtime size: `3373` bytes
- Runtime lines: `124`
- Implementation hash: `0e4c24916ae7`
- Implementation size: `3373` bytes
- Implementation lines: `124`
- Notes: none

#### services/governor/act_first.py

- Current purpose: Completed and failed task reporting helper
- Sync order: `7`
- Canonical targets: `agent_server:/v1/tasks?limit=50`
- Replacement owner paths: `services/governor/act_first.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/governor/act_first.py`
- Canonical replacement: Read recent canonical task truth from the task engine and never touch legacy queue surfaces.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/act_first.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Helper reads the canonical task list instead of mutating a local queue snapshot.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_automation_uses_canonical_task_routes`, `services/governor/tests/test_helper_contracts.py`
- Runtime file: `/home/shaun/repos/athanor/services/governor/act_first.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\governor\act_first.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `373befc7eb31`
- Runtime size: `2223` bytes
- Runtime lines: `79`
- Implementation hash: `373befc7eb31`
- Implementation size: `2223` bytes
- Implementation lines: `79`
- Notes: none

#### services/governor/self_improve.py

- Current purpose: Proposal-to-task automation helper
- Sync order: `8`
- Canonical targets: `agent_server:/v1/improvement/proposals`, `agent_server:/v1/improvement/proposals/{proposal_id}`, `agent_server:/v1/tasks`, `agent_server:/v1/goals`
- Replacement owner paths: `services/governor/self_improve.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/governor/self_improve.py`
- Canonical replacement: Read and patch proposals on the agent server, then create durable tasks through canonical /v1/tasks.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/governor/self_improve.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Helper submits durable tasks through /v1/tasks and no longer relies on governor-owned queue surfaces.
- Repo-side gates: `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_automation_uses_canonical_task_routes`, `services/governor/tests/test_helper_contracts.py`
- Runtime file: `/home/shaun/repos/athanor/services/governor/self_improve.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\governor\self_improve.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `eeaf40daffc8`
- Runtime size: `5440` bytes
- Runtime lines: `163`
- Implementation hash: `eeaf40daffc8`
- Implementation size: `5440` bytes
- Implementation lines: `163`
- Notes: none

#### services/sentinel/checks.py

- Current purpose: Heartbeat, readiness, and integration probe definitions
- Sync order: `9`
- Canonical targets: `get_health_url(service_id)`, `agent_server:/v1/tasks/stats`, `agent_server:/v1/agents`
- Replacement owner paths: `services/sentinel/checks.py`, `services/cluster_config.py`
- Expected runtime owner path: `/home/shaun/repos/athanor/services/sentinel/checks.py`
- Canonical replacement: Probe topology-owned health surfaces and canonical /v1/tasks/stats instead of :8760.
- Sync strategy: `backup_then_replace_from_implementation_authority`
- Sync decision: `already_synced`
- Rollback target: `/home/shaun/.athanor/backups/governor-facade-cutover/services/sentinel/checks.py`
- Rollback ready: `True`
- Next action: Cutover is verified; no further runtime file action is required unless drift reappears.
- Cutover check: Sentinel integration checks use canonical task-engine stats and topology-owned service health URLs.
- Repo-side gates: `python scripts/run_service_contract_tests.py`, `projects/agents/tests/test_repo_contracts.py::test_legacy_governor_main_is_deleted_from_implementation_authority`
- Runtime file: `/home/shaun/repos/athanor/services/sentinel/checks.py`
- Runtime file exists: `True`
- Runtime target matches registry: `True`
- Implementation file: `C:\Athanor\services\sentinel\checks.py`
- Implementation file exists: `True`
- Live content sync: `content_match`
- Live `:8760` reference observed: `False`
- Runtime hash: `2d7a06ad3103`
- Runtime size: `9235` bytes
- Runtime lines: `282`
- Implementation hash: `2d7a06ad3103`
- Implementation size: `9235` bytes
- Implementation lines: `282`
- Notes: none
