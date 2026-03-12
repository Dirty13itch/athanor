# API Atlas

This atlas maps the API boundary between the dashboard, the agent server, and the backing services that power Athanor. It treats the dashboard API layer as a normalization boundary, not as a thin pass-through.

## Ownership Boundary

- The browser should interact with dashboard-owned API routes and typed contracts, not directly with raw cluster services.
- The dashboard API layer normalizes upstream services into stable UI contracts in `src/lib/contracts.ts`.
- The agent server is the main runtime API for workforce state, task execution, subscriptions, learning, outputs, and chat completions.
- Prometheus, Neo4j, Qdrant, Home Assistant, ComfyUI, Plex-stack services, and LiteLLM sit behind those two higher-level API layers.

## Contract Anchors

| Contract source | Responsibility | Status |
| --- | --- | --- |
| `projects/dashboard/src/lib/contracts.ts` | typed dashboard snapshots and UI-owned response models | `live` |
| `projects/dashboard/src/lib/dashboard-data.ts` | overview, services, GPU, workforce, projects, and model normalization | `live` |
| `projects/dashboard/src/lib/subpage-data.ts` | monitoring, media, gallery, memory, intelligence, history, and home normalization | `live` |
| `projects/agents/src/athanor_agents/server.py` | runtime endpoint surface for the agent workforce | `live` |

## Dashboard API Families

| Family | Entry points | Upstream dependencies | Main UI consumers | Status |
| --- | --- | --- | --- | --- |
| Overview and projects | `/api/overview`, `/api/projects` | dashboard data aggregators, Prometheus, agent server | `/`, command palette, supporting project metadata | `live` |
| Services | `/api/services`, `/api/services/history` | agent server service checks, Prometheus history | `/services` | `live` |
| GPU telemetry | `/api/gpu`, `/api/gpu/history` | Prometheus DCGM metrics | `/gpu` | `live` |
| Models and agents | `/api/models`, `/api/agents`, `/api/autonomy` | LiteLLM / vLLM backends, agent server, autonomy state | `/chat`, `/agents`, agent detail surfaces | `live` |
| Workforce snapshot and mutations | `/api/workforce`, `/api/workforce/*` | agent-server tasks, goals, workplan, workspace, notifications, conventions | `/tasks`, `/goals`, `/notifications`, `/workspace`, `/workplanner`, `/review` | `live` |
| History and outputs | `/api/history`, `/api/activity`, `/api/conversations`, `/api/outputs`, `/api/outputs/[...path]` | agent-server activity, conversation, tasks, outputs | `/activity`, `/conversations`, `/outputs` | `live` |
| Intelligence and learning | `/api/intelligence`, `/api/insights`, `/api/insights/run`, `/api/learning/*` | agent-server patterns, metrics, benchmarks, improvement data | `/insights`, `/learning`, `/review` | `live` |
| Memory and preference surfaces | `/api/memory`, `/api/preferences`, `/api/personal-data/search`, `/api/personal-data/stats` | agent server, Qdrant, Neo4j | `/preferences`, `/personal-data` | `live` |
| Media and gallery | `/api/media`, `/api/media/overview`, `/api/stash/stats`, `/api/gallery/overview`, `/api/comfyui/*` | Plex-stack APIs, Stash, ComfyUI | `/media`, `/gallery` | `live` |
| Monitoring and home | `/api/monitoring`, `/api/home/overview` | Prometheus, Home Assistant probes | `/monitoring`, `/home` | `live` |
| Subscription brokerage | `/api/subscriptions/providers`, `/api/subscriptions/policy`, `/api/subscriptions/quotas`, `/api/subscriptions/leases` | agent-server subscription broker | `/agents`, `/tasks` | `live` |
| Skills | `/api/skills`, `/api/skills/stats`, `/api/skills/top`, `/api/skills/[skillId]`, `/api/skills/[skillId]/execution` | agent-server emerging capability endpoints | `/learning` | `live` |
| Research jobs and scheduling | `/api/research/jobs`, `/api/research/jobs/[jobId]/execute`, `/api/scheduling/status` | agent-server research jobs and scheduling status | `/workplanner` | `live` |
| Consolidation | `/api/consolidation`, `/api/consolidation/stats` | agent-server consolidation endpoints | `/personal-data` | `live` |
| Alerts and notification budgets | `/api/alerts`, `/api/notification-budget` | agent-server alerts and notification budget endpoints | `/notifications` | `live` |
| Routing and context preview | `/api/context/preview`, `/api/routing/classify` | agent-server routing and context preview endpoints | `/chat`, `/agents` | `live` |
| Stream / feedback / voice / push | `/api/stream`, `/api/feedback`, `/api/feedback/implicit`, `/api/tts`, `/api/push/subscribe`, `/api/push/send` | Prometheus, agent server, browser push, TTS proxy | mounted supporting components and partially mounted ambient UI widgets | `implemented_not_live` |

## Agent-server Endpoint Families

| Family | Entry points | Responsibility | Main consumers | Status |
| --- | --- | --- | --- | --- |
| Health and model inventory | `/health`, `/v1/models`, `/v1/agents` | runtime health, agent roster, OpenAI-style model listing | dashboard overview, chat, agents, ops checks | `live` |
| Subscription brokerage | `/v1/subscriptions/*` | provider policy, lease issuance, quota summary, outcome recording | coding agent, research agent, future provider-aware dashboards | `live` |
| Service and media status | `/v1/status/services`, `/v1/status/media` | normalized service and media state for operators and dashboards | dashboard snapshots and ops surfaces | `live` |
| Activity, conversations, outputs | `/v1/activity`, `/v1/conversations`, `/v1/outputs*` | durable operator trail and output discovery | history family, review flows | `live` |
| Preferences, notifications, and routing | `/v1/preferences*`, `/v1/notifications*`, `/v1/notification-budget`, `/v1/context/preview`, `/v1/routing/classify` | memory capture, notification resolution, routing preview, and budget visibility | memory routes plus `/chat`, `/agents`, and `/notifications` | `live` |
| Escalation, trust, autonomy | `/v1/escalation/*`, `/v1/trust`, `/v1/autonomy`, `/v1/autonomy/reset` | confidence gating and autonomy posture | notification flows, review logic, supporting autonomy UI | `live` |
| Workspace and cognitive state | `/v1/workspace*`, `/v1/events*`, `/v1/cognitive/*`, `/v1/conventions*` | shared broadcast, event ingestion, CST, conventions, specialist registry | workspace UI, review of shared context, future cognitive inspection surfaces | `live` |
| Tasks and workplan | `/v1/tasks*`, `/v1/workplan*`, `/v1/projects*`, `/v1/goals*` | task execution, planning, redirection, project metadata, steering goals | workforce family, Claude-driven operations | `live` |
| Skills, research jobs, and consolidation | `/v1/skills*`, `/v1/research/jobs*`, `/v1/consolidate*` | reusable skills, execution stats, queued research work, and memory consolidation | `/learning`, `/workplanner`, `/personal-data` | `live` |
| Learning metrics and briefings | `/v1/learning/metrics`, `/v1/briefing`, `/v1/metrics/*` | learning posture, briefings, and agent/inference metrics | intelligence layers, background refinement, ops analysis | `live` |
| Chat completions | `/v1/chat/completions` | primary OpenAI-compatible agent interaction surface | dashboard chat, agent console, external clients | `live` |

## Consumer Matrix

| UI surface | Primary API families |
| --- | --- |
| Command Center shell | overview/projects, stream support, route metadata, dashboard polling |
| Services / GPU / Monitoring | services, GPU telemetry, monitoring |
| Chat / Agents | models and agents, chat completions, routing/context preview, subscription brokerage |
| Tasks / Goals / Notifications / Workspace / Work Planner | workforce snapshot and mutations, task/workplan families, subscription brokerage, research jobs and scheduling, alerts and notification budgets |
| Activity / Conversations / Outputs | history and outputs families |
| Insights / Learning / Review | intelligence and learning, skills, plus task approvals |
| Preferences / Personal Data | memory and preference families, consolidation, plus push subscribe |
| Media / Gallery / Home / Terminal | media/gallery, home, ws-pty bridge |

## Current API Reading

- The dashboard API surface is broad because it deliberately owns normalization and lets the browser stay ignorant of raw cluster topology.
- `/api/stash/stats` remains in the media family as an internal support route, but media posture should be read from `/api/media/overview` rather than treating stash stats as the primary UI contract.
- Some dashboard support routes are still ahead of what the mounted shell currently exposes. That should be read as `implemented_not_live`, not as dead code by default.
- The main dashboard now mounts the strongest agent-server operator lanes for subscriptions, routing preview, skills, research jobs, and consolidation; the remaining unsurfaced server capability is mostly deeper cognitive inspection and ambient support hooks.
