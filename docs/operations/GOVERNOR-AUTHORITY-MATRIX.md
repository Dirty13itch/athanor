# Governor Authority Matrix

Source of truth: `config/automation-backbone/platform-topology.json`, `projects/agents/src/athanor_agents/task_store.py`, `projects/agents/src/athanor_agents/governor.py`, `projects/agents/src/athanor_agents/governor_backbone.py`, `projects/agents/src/athanor_agents/governor_runtime.py`
Validated against registry version: `platform-topology.json@2026-03-26.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: host placement and service ownership come from the topology registry. This document owns the code-level authority split between registry/backbone truth, durable task truth, and compatibility surfaces inside `projects/agents`.

---

## Purpose

This matrix exists to prevent Athanor from drifting back into split-brain control logic.
The live DEV governor facade is retired and the implementation-authority facade file is deleted. This document remains canonical while its durable rules still need an explicit code-level authority split outside the broader task-engine docs.

The rule is simple:

- registry-backed facts are read from registry/backbone surfaces
- mutable task truth is written through the task store
- compatibility remains inside the canonical task-engine surface, not as a standalone governor service or facade file
- the `runtime.subsystem.task-engine` registry lane now names durable task truth plus governor posture; it does not grant any standalone governor facade alternate task ownership

## Ownership Boundaries

### Registry and backbone truth

These paths own read-mostly operating truth:

- topology-backed service and node expectations
- governor posture
- operator presence
- release tier
- paused lanes
- capacity/readiness snapshots
- lane governance metadata

Authoritative modules:

- `governor_backbone.py`
- `governor_runtime.py`
- registry readers under `model_governance.py`

Allowed consumers:

- dashboard-facing read routes
- scheduler and governance checks
- operator snapshot builders

These modules may read posture and readiness directly. They should not invent duplicate state holders.

### Durable task truth

The authoritative task namespace for this cycle is:

- Redis hash: `athanor:tasks`

Secondary indexes:

- `athanor:tasks:status:<status>`
- `athanor:tasks:lane:<lane>`
- `athanor:tasks:session:<session_id>`
- `athanor:tasks:updated`

Authoritative module:

- `task_store.py`

Current durable record shape:

- `id`
- `agent`
- `prompt`
- `priority`
- `source`
- `lane`
- `status`
- `created_at`
- `started_at`
- `completed_at`
- `updated_at`
- `lease`
- `retry_lineage`
- `assigned_runtime`
- `last_heartbeat`
- `session_id`
- `metadata`
- `result`
- `error`

`tasks.py` is allowed to own queue semantics, worker behavior, retry policy, and prompt construction. It is not allowed to bypass `task_store.py` when persisting task state, and `persist_task_state()` is the only supported persistence seam it exposes.

### Compatibility facade

`governor.py` remains the stable public seam for callers that still import governor helpers. It may:

- re-export governor runtime/backbone functions
- preserve public names
- adapt compatibility callers

It must not:

- become the primary state store
- duplicate task persistence logic
- bypass backbone/runtime helpers to own operator posture directly

## Module Matrix

| Module | May read backbone truth directly | May write governor posture | May write task truth | Notes |
|--------|----------------------------------|----------------------------|----------------------|-------|
| `governor_backbone.py` | yes | yes | no | Owns normalized governor posture state |
| `governor_runtime.py` | yes | compatibility helpers only | no | Runtime helpers and compatibility glue |
| `governor.py` | via backbone/runtime only | via backbone/runtime only | no | Compatibility facade only |
| `task_store.py` | no | no | yes | Only durable task persistence seam |
| `tasks.py` | limited | no | via `task_store.py` only | Worker loop, retry, heartbeat, task lifecycle; `persist_task_state()` is the only supported task-persistence seam |
| `routes/tasks.py` | no | no | via `tasks.py` helpers only | Public task API; privileged mutations now require the shared operator envelope and audit path, and manual task creation now flows through `submit_governed_task()` |
| `routes/governor.py` | yes | via governor facade/backbone | no | Governor/operator API |
| `routes/digests.py` | no | no | read via `task_store.py` only | No direct hash reads |
| `scheduler.py` | yes | no | via `submit_governed_task()` and `submit_task()` only | Proactive schedules use the canonical governed-submission seam; non-governed helper tasks still use the base task API |
| `work_pipeline.py` | yes | no | via `submit_governed_task()` and `submit_task()` only | Plan decomposition uses the canonical governed-submission seam; non-governed recovery helpers still use the base task API |
| `tools/execution.py` | no | no | via task helpers only | Caller of task APIs, not store owner |

## Current Guardrails

- `tasks.py` now backfills and maintains task secondary indexes on worker startup.
- restart recovery converts stranded `running` tasks into durable `stale_lease` records
- bounded retry lineage is preserved when stale or failed tasks requeue
- `routes/digests.py` now reads through `task_store.py` instead of directly scanning the task hash
- `routes/tasks.py` now requires the shared operator-action contract for create, approve, cancel, reject, and batch-approve mutations, and emits denied audit events on failed task mutations
- Manual task submission, proactive scheduler submissions, work-planner task generation, workspace reactions, and pipeline decomposition now all share the canonical `submit_governed_task()` helper for governor gate evaluation, metadata stamping, and approval-hold persistence.
- legacy governor helper scripts now target the canonical `/v1/tasks` and `/v1/tasks/dispatch` routes, and they no longer write new work into the retired alternate governor queue
- legacy governor reporting helpers now read canonical `/v1/tasks` and `/v1/tasks/stats` instead of the alternate `/queue` and `/stats` surfaces
- the active helper estate under `services/governor` now has explicit contract coverage that blocks `/queue`, `/dispatch-and-run`, SQLite, tmux/worktree ownership, and ad hoc tmp-log state from creeping back into `overnight.py`, `self_improve.py`, `act_first.py`, `status_report.py`, or `_imports.py`
- the retired `services/governor/main.py` compatibility facade is deleted from implementation authority after the verified 2026-03-29 cutover, so no standalone governor facade code remains in the active repo
- `runtime-subsystem-registry.json` now describes the `/tasks` + `/governor` lane as task-engine durability plus governor posture only, matching the post-cutover steady state
- The 2026-03-29 runtime collector confirmed DEV no longer runs `athanor-governor.service` on `:8760`, observed runtime references dropped to zero, and the 9 mapped runtime-owned callers now match implementation authority.
- the retired `services/governor/dispatch.py`, `services/governor/continuous_dispatch.py`, `services/governor/db.py`, and the old archived `governor.db` snapshot are deleted from the implementation-authority tree
- `tasks.py` now publishes task submission and retry events through an explicit helper instead of an undefined Redis handle, and the hottest pending-task/status-filtered reads now use the durable task-status index instead of rescanning the entire task hash

## Remaining Migration Rule

If a module needs task data:

1. prefer `tasks.py` helpers for lifecycle-aware behavior
2. use `task_store.py` only when the caller truly needs raw durable records
3. do not read `athanor:tasks` directly from arbitrary routes or helper modules

If a module needs to persist an in-memory `Task` object:

1. use `tasks.persist_task_state()`
2. do not add a second persistence wrapper or import path around it
3. do not call `write_task_record()` directly from `tasks.py` lifecycle helpers outside `persist_task_state()`

If a module needs governor posture:

1. prefer `governor.py` public exports or `governor_backbone.py` snapshot builders
2. do not create a second governor-state cache in a route or worker

## Known Remaining Debt

- The validator still imports `projects/agents` settings through a bootstrap path helper; that sidecar cleanup remains open.
- Shared health/action/audit contracts still need to land across the remaining core services.
- Recovery evidence and bounded automation records now emit through the script-driven evidence lane; stale-lease and runtime-healer records are still pending deeper governor integration.
- The standalone governor-facade decision is closed repo-side as well as runtime-side. The remaining work here is archival demotion, not more authority cleanup around `services/governor/main.py`.
