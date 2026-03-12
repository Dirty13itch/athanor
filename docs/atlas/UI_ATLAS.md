# UI Atlas

This atlas maps the Athanor dashboard as a system, not just a route list. It covers the shell, route families, shared consoles, persistent state, supporting APIs, and UI systems that exist in code but are not yet fully mounted.

## Shell and Cross-cutting Systems

| System | Current wiring | Role | Status |
| --- | --- | --- | --- |
| Root layout | `src/app/layout.tsx` | global fonts, metadata, providers, service-worker registration, shell mount point | `live` |
| Query client provider | `src/components/app-providers.tsx` | shared React Query cache and polling defaults | `live` |
| App shell | `src/components/app-shell.tsx` | desktop sidebar, mobile sheet nav, top header, quick-access routes, status chips | `live` |
| Command palette | `src/components/command-palette.tsx` | `Ctrl/Cmd+K` route, alert, project, and external-tool launcher | `live` |
| Route family model | `src/lib/navigation.ts` | canonical UI information architecture for route families and nav labels | `live` |
| URL state helper | `src/lib/url-state.ts` | shareable route state via query params with scroll-preserving replace | `live` |
| Local persistence | `src/lib/state.ts` | `uiPreferences`, direct-chat sessions, agent threads, prompt history | `live` |
| PWA registration | `src/components/register-sw.tsx`, `/offline` | service-worker registration and offline fallback route | `live` |
| Push subscription UI | `src/components/push-manager.tsx` | browser push opt-in via `/api/push/subscribe` | `live` |
| Terminal bridge | `src/components/terminal-view.tsx` | xterm.js plus WebSocket PTY bridge to `:3100` | `live` |
| Lens provider and switcher | `src/hooks/use-lens.tsx`, `src/components/lens-switcher.tsx` | color/focus lens system defined in code but provider is not mounted in the root shell | `implemented_not_live` |
| Bottom nav | `src/components/bottom-nav.tsx` | mobile footer navigation component present in repo but not mounted by the shell | `implemented_not_live` |
| Ambient shell widgets | `agent-crew-bar`, `system-pulse`, `daily-briefing`, `unified-stream`, `voice-input`, `voice-output`, `work-plan` | higher-ambience operator components and generative UI helpers present in component library but not first-class shell mounts | `implemented_not_live` |

## Component Families

| Family | Main files | Role | Status |
| --- | --- | --- | --- |
| Shell and navigation | `app-shell`, `command-palette`, `page-header`, `route-icon`, `family-tabs`, `status-dot`, `lens-switcher` | top-level navigation, framing, route grouping, and shared operator controls | `live` |
| Operational cards and charts | `stat-card`, `metric-chart`, `gpu-chart`, `service-grid`, `task-card`, `approval-card`, `daily-digest` | cluster posture, metrics, queue summaries, approvals, and generated status surfaces | `live` |
| History and transcript rendering | `rich-text`, `tool-call`, `message-renderer`, `empty-state`, `error-panel`, `unified-stream` | transcript rendering, tool traces, handoff surfaces, and state-specific feedback | `live` |
| Memory and personal-data widgets | `personal-data/search-bar`, `category-overview`, `graph-summary`, `recent-items` | semantic search, knowledge posture, and indexed-item summaries | `live` |
| Terminal, voice, and notification utilities | `terminal-view`, `push-manager`, `voice-input`, `voice-output` | shell escape hatch, push subscription, and voice-adjacent interaction primitives | `live` with voice-adjacent pieces `implemented_not_live` |
| Design-system primitives | `components/ui/*` | shadcn/ui-based buttons, cards, inputs, sheets, badges, tabs, and layout primitives used by every route | `live` |

## Route Families

| Family | Label | Routes | Role | Status |
| --- | --- | --- | --- | --- |
| `core` | Command Center | `/`, `/services`, `/gpu`, `/workplanner`, `/chat`, `/agents` | cluster posture, direct interaction, work steering, service and model triage | `live` |
| `workforce` | Workforce | `/tasks`, `/goals`, `/notifications`, `/workspace` | queue, trust, approvals, goals, workspace broadcasts | `live` |
| `history` | History / Handoff | `/activity`, `/conversations`, `/outputs` | operator trail, transcripts, output review and backlinking | `live` |
| `intelligence` | Intelligence | `/insights`, `/learning`, `/review` | patterns, benchmarks, review queue, operator posture | `live` |
| `memory` | Memory | `/preferences`, `/personal-data` | explicit preferences, personal-data search, graph and vector posture | `live` |
| `domains` | Domain Consoles | `/monitoring`, `/media`, `/gallery`, `/home`, `/terminal` | domain-specific operational surfaces and utility console | `live` |
| `support` | Support | `/more`, `/offline` | route launcher and fallback | `live` |

## Core Family Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | `CommandCenter` | query-param lens is designed; recent context is browser-local from chat sessions and agent threads | open incidents, open work planner, resume agents | `/api/overview` | `/services`, `/workplanner`, `/agents`, `/tasks` | `live` |
| `/services` | `ServicesConsole` | URL: `search,status,node,category,sort,service,window` | refresh, export, open service drawer, copy URL, jump to Grafana/service | `/api/services`, `/api/services/history` | `/monitoring`, `/gpu` | `live` |
| `/gpu` | `GpuConsole` | URL: `window,highlight,compare` | refresh, export, highlight GPU, compare up to three GPUs | `/api/gpu`, `/api/gpu/history` | `/services`, `/monitoring` | `live` |
| `/workplanner` | `WorkPlannerConsole` | URL: `search,project,status` | refresh, generate plan, redirect work, approve/cancel queued work | `/api/workforce`, `/api/workforce/plan`, `/api/workforce/redirect`, workforce task mutations | `/tasks`, `/goals`, `/workspace`, `/review` | `live` |
| `/chat` | `DirectChatConsole` | URL: `session,model`; local: sessions, prompt history, UI preferences | refresh, new session, select model, send, abort, export, copy transcript | `/api/models`, `/api/chat` | `/agents`, `/review` | `live` |
| `/agents` | `AgentConsole` | URL: `agent,thread`; local: agent threads and UI preferences | refresh, new thread, select agent, send, abort, export thread | `/api/agents`, `/api/chat` | `/tasks`, `/activity`, `/workspace` | `live` |

## Workforce Family Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/tasks` | `TasksConsole` | URL: `search,status,agent`; local: composer open state, expanded task | refresh, compose task, approve, cancel, rerun, expand task detail | `/api/workforce`, `/api/workforce/tasks`, `/api/workforce/tasks/{taskId}/approve`, `/api/workforce/tasks/{taskId}/cancel` | `/workplanner`, `/review`, `/outputs` | `live` |
| `/goals` | `GoalsConsole` | local-only form state for text, agent, priority | refresh, add goal, remove goal, inspect trust posture | `/api/workforce`, `/api/workforce/goals`, `/api/workforce/goals/{goalId}` | `/workplanner`, `/notifications` | `live` |
| `/notifications` | `NotificationsConsole` | URL: `resolved` | refresh, show/hide resolved, approve, reject | `/api/workforce`, `/api/workforce/notifications/{notificationId}/resolve` | `/review`, `/tasks`, `/activity` | `live` |
| `/workspace` | `WorkspaceConsole` | local feedback / busy state | refresh, endorse broadcast item, confirm or reject conventions | `/api/workforce`, `/api/workforce/workspace/{itemId}/endorse`, `/api/workforce/conventions/*` | `/tasks`, `/goals`, `/activity` | `live` |

## History / Handoff Family Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/activity` | `HistoryConsole` (`activity` variant) | URL: `search,project,agent,status,timeframe,selection` | refresh, export snapshot, filter, open detail drawer | `/api/history`, supporting `/api/activity` | `/tasks`, `/workplanner`, `/review` | `live` |
| `/conversations` | `HistoryConsole` (`conversations` variant) | URL: `search,project,agent,status,timeframe,selection` | refresh, export snapshot, inspect transcript and backlinks | `/api/history`, supporting `/api/conversations` | `/agents`, `/chat`, `/review` | `live` |
| `/outputs` | `HistoryConsole` (`outputs` variant) | URL: `search,project,agent,status,timeframe,selection` | refresh, export snapshot, preview output, follow task/project backlinks | `/api/history`, `/api/outputs`, `/api/outputs/[...path]` | `/tasks`, `/review`, `/workplanner` | `live` |

## Intelligence Family Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/insights` | `IntelligenceConsole` (`insights` variant) | URL: `search,project,agent,severity,review,selection` | refresh, run insights, filter patterns, inspect review links | `/api/intelligence`, `/api/insights`, `/api/insights/run` | `/review`, `/learning`, `/activity` | `live` |
| `/learning` | `IntelligenceConsole` (`learning` variant) | URL: `search,project,agent,severity,review,selection` | refresh, run benchmarks, inspect learning posture | `/api/intelligence`, `/api/learning/metrics`, `/api/learning/benchmarks`, `/api/learning/improvement` | `/insights`, `/review`, `/goals` | `live` |
| `/review` | `IntelligenceConsole` (`review` variant) | URL: `search,project,agent,severity,review,selection` | refresh, open review task, approve selected review item | `/api/intelligence`, workforce task approve route | `/tasks`, `/outputs`, `/conversations` | `live` |

## Memory Family Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/preferences` | `MemoryConsole` (`preferences` variant) | URL: `query,project,agent,category,entity`; local form state | refresh, store preference, manage push notifications | `/api/memory`, `/api/preferences`, `/api/push/subscribe` | `/personal-data`, `/notifications` | `live` |
| `/personal-data` | `MemoryConsole` (`personal-data` variant) | URL: `query,project,agent,category,entity` | refresh, search semantic memory, inspect indexed item drawer | `/api/memory`, `/api/personal-data/search`, `/api/personal-data/stats` | `/preferences`, `/insights`, `/workspace` | `live` |

## Domain Console Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/monitoring` | `MonitoringConsole` | URL: `node,panel` | refresh, filter nodes, open Grafana drawer preview | `/api/monitoring` | `/services`, `/gpu` | `live` |
| `/media` | `MediaConsole` | URL: `panel` | refresh, open safe drawer preview for external tool launches | `/api/media/overview`, supporting `/api/media`, `/api/stash/stats` | `/gallery`, `/activity` | `live` |
| `/gallery` | `GalleryConsole` | URL: `source,selection,query` | refresh, filter sources, open generation drawer preview | `/api/gallery/overview`, supporting `/api/comfyui/*` | `/media`, `/chat` | `live` |
| `/home` | `HomeConsole` | URL: `panel` | refresh, open Home Assistant, inspect setup ladder and focused panel drawer | `/api/home/overview` | `/monitoring`, `/notifications` | `live` |
| `/terminal` | `TerminalConsole` | local-only selected node and connection state | choose node, open PTY session, reconnect on node change | ws-pty bridge on `:3100` | `/services`, `/monitoring` | `live` |

## Support Routes

| Route | Page / console | URL and local state | Primary actions | Backing APIs | Related routes | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `/more` | route index page | preserves `lens` query state in deep links | browse all families, switch lens intents | route metadata from `navigation.ts` | every other route | `live` |
| `/offline` | offline fallback | none | retry / reload after network loss | service worker / browser network state | `/` | `live` |

## Shared Console Families

| Family | Shared routes | What stays consistent across the family | Status |
| --- | --- | --- | --- |
| `HistoryConsole` | `/activity`, `/conversations`, `/outputs` | one filter model, one selection drawer model, one backlink pattern | `live` |
| `IntelligenceConsole` | `/insights`, `/learning`, `/review` | one filter model, one operator posture lane, one review-task selection model | `live` |
| `MemoryConsole` | `/preferences`, `/personal-data` | one query/project/category/entity filter model with different action lanes | `live` |
| Workforce consoles | `/tasks`, `/goals`, `/notifications`, `/workspace`, `/workplanner` | shared workforce snapshot, cross-links, approval and trust concepts | `live` |

## Mounted vs Dormant UI Capability

- The shell, route families, major consoles, drawers, query-state model, browser persistence, service-worker registration, and push subscription flow are mounted and part of the current operator experience.
- The lens implementation, bottom-nav, ambient crew and pulse widgets, unified stream, voice widgets, and some feedback/autonomy components are implemented in code but not first-class mounted shell systems today.
- Supporting APIs such as `/api/stream`, `/api/autonomy`, `/api/tts`, `/api/feedback`, and `/api/feedback/implicit` exist partly to support those dormant or partially mounted UI capabilities.
