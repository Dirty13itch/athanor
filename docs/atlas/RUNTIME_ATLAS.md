# Runtime Atlas

This atlas maps the active Athanor runtime: the agent server, the workforce subsystems around it, the adaptive loops that shape behavior, and the current split between surfaced and unsurfaced capabilities.

## Command Hierarchy Snapshot

The runtime now treats command and execution as separate layers:

- Shaun remains final authority.
- The constitution and policy registry remain the highest non-human authority.
- The Athanor governor is the runtime commander of record.
- The strategy layer is dual-lane:
  - frontier cloud meta lane
  - sovereign local meta lane
- The control stack owns routing, schedules, durable tasks, leases, and shared attention.
- Specialists execute within domain bounds.
- Worker planes execute; judge planes score.

See [COMMAND_HIERARCHY_ATLAS.md](./COMMAND_HIERARCHY_ATLAS.md) for the full mapped hierarchy and operator-facing surfaces.

## Runtime Strata

| Stratum | Primary modules / surfaces | Responsibility | Status |
| --- | --- | --- | --- |
| Interaction | Dashboard chat, agent console, tasks, goals, workspace, notifications | operator-facing entry into the local workforce | `live` |
| Orchestration | `server.py`, `router.py`, `routing.py`, `tasks.py`, `scheduler.py` | request routing, background work, schedules, approvals, redirection | `live` |
| Cognitive / shared context | `workspace.py`, `cst.py`, `specialist.py`, `conventions.py`, `context.py` | workspace broadcast, CST, specialists, conventions, context preview | `live` |
| Memory and knowledge | `preferences.py`, `preference_learning.py`, `hybrid_search.py`, `graph_context.py`, `consolidation.py` | explicit memory, retrieval, graph context, promotion / consolidation | `live` |
| Adaptive control | `escalation.py`, `patterns.py`, `diagnosis.py`, `self_improvement.py`, `semantic_cache.py`, `circuit_breaker.py` | trust, autonomy, failure handling, pattern detection, adaptive refinement | `live` |
| Subscription brokerage | `subscriptions.py` | provider selection and execution leasing for premium and local model lanes | `live` |
| Emerging subsystems | `skill_learning.py`, `research_jobs.py`, `model_governance.py`, `proving_ground.py` | reusable skills, structured research-job queueing, and model-governance/proving-ground runtime posture | `live` |

## Agent Roster

| Agent | Mode | Primary role | Key tool surface | Primary operator surfaces | Status |
| --- | --- | --- | --- | --- | --- |
| `general-assistant` | proactive + reactive | system status, infrastructure inspection, delegation | service checks, GPU metrics, model inventory, filesystem read tools | `/agents`, `/tasks`, `/activity`, `/workspace` | `live` |
| `media-agent` | proactive + reactive | media acquisition, playback visibility, queue awareness | Sonarr, Radarr, Plex, Tautulli | `/agents`, `/media`, `/notifications`, `/activity` | `live` |
| `home-agent` | proactive + reactive | Home Assistant status and bounded control | entity lookup, service calls, automations | `/agents`, `/home`, `/notifications`, `/activity` | `live` |
| `research-agent` | reactive | web research and synthesis | web search, fetch, knowledge search, infrastructure query, execution lease | `/agents`, `/tasks`, `/review` | `live` |
| `creative-agent` | reactive | image and video generation workflows | ComfyUI generation and queue tools | `/agents`, `/gallery`, `/chat` | `live` |
| `knowledge-agent` | reactive | knowledge-base and graph retrieval | Qdrant, Neo4j, related-doc retrieval, stats | `/agents`, `/personal-data`, `/insights` | `live` |
| `coding-agent` | proactive + reactive | code generation, repo work, test loops | coding helpers, filesystem, commands, execution lease | `/agents`, `/tasks`, `/review`, `/workplanner` | `live` |
| `stash-agent` | reactive | Stash catalog management | Stash GraphQL and tagging tools | `/agents`, `/media` | `live` |
| `data-curator` | proactive | personal-data ingestion and indexing | scan, parse, analyze, index, search, sync | `/tasks`, `/personal-data`, `/activity` | `live` |

## Core Orchestration Subsystems

| Subsystem | Responsibility | Main entrypoints | Source anchors | Status |
| --- | --- | --- | --- | --- |
| Agent server | OpenAI-compatible runtime and shared API boundary for agents and workforce state | `/health`, `/v1/chat/completions`, `/v1/agents`, `/v1/models` | `projects/agents/src/athanor_agents/server.py` | `live` |
| Task engine | Redis-backed queued execution with approval and cancellation flows | `/v1/tasks`, `/v1/tasks/{id}`, `/v1/tasks/{id}/approve`, `/v1/tasks/{id}/cancel` | `tasks.py`, [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) | `live` |
| Scheduler | periodic proactive loops and schedule introspection | `/v1/tasks/schedules`, `/v1/scheduling/status` | `scheduler.py`, `scheduling.py` | `live` |
| Workspace / GWT | shared competition window, subscriptions, endorsements, broadcasts | `/v1/workspace`, `/v1/workspace/stats`, `/v1/workspace/subscriptions`, `/v1/workspace/{item_id}/endorse` | `workspace.py`, `cst.py`, `specialist.py` | `live` |
| Goals and workplan | steering intent, plan generation, redirects, project-aware planning | `/v1/goals`, `/v1/workplan`, `/v1/workplan/generate`, `/v1/workplan/redirect`, `/v1/projects` | `goals.py`, `workplanner.py`, `projects.py` | `live` |
| Notifications and escalation | approvals, notify/ask routing, notification budget, escalation evaluation | `/v1/notifications`, `/v1/notifications/{id}/resolve`, `/v1/escalation/*`, `/v1/notification-budget` | `alerts.py`, `escalation.py` | `live` |
| Preferences and memory | explicit preferences, preference learning, model preferences | `/v1/preferences`, `/v1/preferences/models` | `preferences.py`, `preference_learning.py` | `live` |
| Patterns and learning | pattern detection, learning metrics, self-improvement telemetry | `/v1/patterns`, `/v1/patterns/run`, `/v1/learning/metrics`, `/v1/briefing` | `patterns.py`, `self_improvement.py`, `briefing.py` | `live` |
| Subscription control layer | execution leasing across local and cloud providers | `/v1/subscriptions/*` | `subscriptions.py`, [`../decisions/ADR-022-subscription-control-layer.md`](../decisions/ADR-022-subscription-control-layer.md) | `live` |
| Command hierarchy, governor posture, and operator stream | read-only hierarchy map, governor posture, normalized run ledger, scheduled jobs, provider summary, and operator events | `/v1/system-map`, `/v1/governor`, `/v1/activity/operator-stream`, `/v1/tasks/runs`, `/v1/tasks/scheduled`, `/v1/subscriptions/summary` | `command_hierarchy.py`, `governor.py`, `backbone.py`, [`../decisions/ADR-023-command-hierarchy-and-governance.md`](../decisions/ADR-023-command-hierarchy-and-governance.md) | `live` |
| Model governance, judge plane, and proving ground | model-role registry, workload registry, champion/challenger posture, proving-ground cadence, local judge posture, and live benchmark evidence | `/v1/models/governance`, `/v1/models/proving-ground`, `/v1/review/judges` | `model_governance.py`, `judge.py`, `proving_ground.py`, `config/automation-backbone/*.json`, [`./MODEL_GOVERNANCE_ATLAS.md`](./MODEL_GOVERNANCE_ATLAS.md) | `live` |
| Skills library | learned skills, execution stats, top-skill inspection | `/v1/skills*` | `skill_learning.py` | `live` |
| Research jobs | queued research work separate from direct agent chat | `/v1/research/jobs*` | `research_jobs.py` | `live` |
| Consolidation | explicit promotion / consolidation lane for memory work | `/v1/consolidate*` | `consolidation.py` | `live` |

## Control Loops

| Loop | Path | What it changes | Status |
| --- | --- | --- | --- |
| Request routing | dashboard or API request -> router -> agent/model lane | picks the active execution lane | `live` |
| Task execution | queued task -> worker -> tool steps -> result / approval / failure | turns workforce intent into durable work | `live` |
| Workspace competition | event or agent output -> workspace item -> salience cycle -> broadcast | shares the highest-value context across agents | `live` |
| Feedback to trust | explicit and implicit feedback -> trust/autonomy scores -> review posture | calibrates whether agents act, notify, or ask | `live` |
| Learning and patterning | activity + conversations + failures -> patterns -> recommendations / benchmarks | surfaces behavior drift and improvement opportunities | `live` |
| Subscription leasing | requester -> lease policy -> provider selection -> outcome feedback | spends premium or local model capacity deliberately | `live` |

## Surfaced vs Unsurfaced Runtime

| Runtime surface | Current state | Atlas reading |
| --- | --- | --- |
| Tasks, goals, workspace, notifications, history, outputs, subscriptions | connected to the live operator shell through dashboard routes and APIs | `live` |
| Skills library, research jobs, and consolidation | connected to `/learning`, `/workplanner`, and `/personal-data` through first-class dashboard cards and actions | `live` |
| Model governance, governor posture, and proving-ground registries | surfaced in the Command Center, `/learning`, `/review`, `/agents`, `/tasks`, and `/workplanner`; registry visibility, benchmark execution, governor controls, system-map visibility, and judge-plane visibility are all live | `live` |
| Older Local-System behavior lines | useful only as lineage/reference for drift analysis | `legacy` |

## Truth Boundaries

- `projects/agents/src/athanor_agents/server.py` is the runtime contract source for endpoint surface and boot behavior.
- `projects/agents/src/athanor_agents/*` modules are the source for subsystem implementation and dependency shape.
- [`../design/agent-contracts.md`](../design/agent-contracts.md) is the normative behavioral layer above implementation details.
- [`../SYSTEM-SPEC.md`](../SYSTEM-SPEC.md) explains the runtime in operational terms and remains the primary prose spec below the atlas.

When those sources disagree, the atlas favors the actual agent-server surface and marks the older description instead of silently blending them.
