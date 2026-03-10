# Dashboard Sub-Page Completion Plan

## Goal

This plan defines how every dashboard route reaches "complete" status under the
Athanor Next operator-console model. It extends the existing
[`UI_AUDIT.md`](C:/Users/Shaun/dev/athanor-next/projects/dashboard/docs/UI_AUDIT.md)
and turns the remaining route work into a structured execution program instead
of an open-ended redesign.

The target is not "pages that render." The target is a coherent command center
where every route meets the same standards across:

- shell integration
- centralized data ownership
- URL and local state persistence
- loading, empty, degraded, and error handling
- keyboard and accessibility coverage
- smoke, regression, and visual test coverage

## Completion Standard

A route is only considered complete when all of the following are true:

1. The route is integrated into the operator shell with working forward and
   backward navigation, command-palette discovery, and stable route metadata.
2. Production UI code does not hardcode raw cluster URLs or credentials.
3. Data comes from centralized config helpers or dashboard-owned API routes.
4. The route has explicit nominal, loading, empty, degraded, and error states.
5. Route state is persisted correctly:
   - shareable state in the URL
   - private operator state in local storage when appropriate
6. Keyboard flow, focus states, and reduced-motion behavior are verified.
7. The route has Playwright smoke coverage plus any route-specific interaction
   coverage needed for critical actions.

## Shared Layers

Every route is evaluated and built through the same layers.

### 1. Shell and navigation layer

- Route entry in sidebar, command palette, and `/more` where applicable
- Breadcrumb or context framing when the route has drill-down panels
- Verified back navigation from detail states, drawers, and overlays
- Consistent page header, page actions, timestamps, and refresh affordances

### 2. Data and API layer

- Server-owned API contract for each remote dependency
- Typed normalization at the dashboard boundary
- No browser-level fetches to raw remote cluster services
- Polling and refresh policy that is visibility-aware rather than blind

### 3. State and persistence layer

- URL state for filters, selections, tabs, sort, density, time ranges
- Local storage for recent sessions, dismissed hints, and operator preferences
- Clear "new" versus "resume" semantics for conversational or history surfaces

### 4. UX and resilience layer

- Deterministic loading skeletons
- Empty-state guidance with next actions
- Degraded-state messaging when upstream data is partial
- Error recovery paths and manual refresh
- Meaningful operator actions instead of passive read-only surfaces where safe

### 5. Accessibility and interaction layer

- Landmark and heading structure
- Visible focus states
- Keyboard-complete navigation for filters, drawers, dialogs, and transcript
  surfaces
- WCAG-safe status colors and icon usage

### 6. Quality layer

- API smoke tests
- route rendering smoke tests
- back-link and navigation tests
- visual regression coverage where layout stability matters
- targeted interaction tests for the route's primary workflow

## Current Route Status

### Already on the feature-console architecture

These routes already use the newer shell, typed snapshot pattern, and feature
module structure. They still receive follow-up polish, but they are not the
main migration risk.

| Route | Current module | Status |
| --- | --- | --- |
| `/` | `src/features/overview/command-center.tsx` | Strong baseline |
| `/services` | `src/features/services/services-console.tsx` | Strong baseline |
| `/gpu` | `src/features/gpu/gpu-console.tsx` | Strong baseline |
| `/chat` | `src/features/chat/direct-chat-console.tsx` | Strong baseline |
| `/agents` | `src/features/agents/agent-console.tsx` | Strong baseline |
| `/tasks` | `src/features/workforce/tasks-console.tsx` | Mid-stage |
| `/goals` | `src/features/workforce/goals-console.tsx` | Mid-stage |
| `/notifications` | `src/features/workforce/notifications-console.tsx` | Mid-stage |
| `/workplanner` | `src/features/workforce/work-planner-console.tsx` | Mid-stage |
| `/workspace` | `src/features/workforce/workspace-console.tsx` | Mid-stage |

### Still page-local and needing full completion

These are the remaining routes that still carry the most migration and quality
risk.

| Route | Current state | Priority |
| --- | --- | --- |
| `/monitoring` | route-local server page, direct Prometheus queries | P1 |
| `/media` | route-local client page, mixed remote status surface | P1 |
| `/insights` | route-local client page, analysis dashboard | P1 |
| `/learning` | route-local client page, learning metrics and benchmarks | P1 |
| `/review` | route-local client page, code/task review workflow | P1 |
| `/activity` | route-local client page, timeline/history | P1 |
| `/conversations` | route-local client page, transcript history | P1 |
| `/outputs` | route-local client page, file explorer/feedback | P1 |
| `/preferences` | route-local client page, memory/preferences store | P1 |
| `/personal-data` | route-local server page, direct Qdrant fetch | P1 |
| `/gallery` | route-local client page, ComfyUI history/generation | P2 |
| `/home` | route-local server page, direct Home Assistant probe | P2 |
| `/terminal` | route-local utility page | P2 |
| `/more` | route-local route index | P2 |
| `/offline` | route-local fallback page | P3 |

## Route-by-Route Completion Program

### `/`

Target role: primary command center and operational landing page.

Remaining completion work:

- keep strengthening summary-to-detail navigation into every secondary route
- ensure every major card has a tested back-link return path
- add explicit links into project, workforce, and domain drill-down routes
- extend smoke tests so every priority lane action resolves to a real route

### `/services`

Target role: service operations console.

Remaining completion work:

- validate history, export, Grafana links, and detail-drawer return paths
- verify stale-state behavior when history is missing but snapshots still load
- extend API smoke coverage to history windows and service-group filters

### `/gpu`

Target role: accelerator fleet console.

Remaining completion work:

- validate pinned compare state survives refresh and shareable URLs
- verify chart fallback on missing range-query data
- extend export and comparison smoke coverage

### `/chat`

Target role: direct model interaction console.

Remaining completion work:

- broaden transcript persistence tests and resume-session behavior
- verify keyboard shortcuts, stop/retry, and render fidelity for code-heavy
  responses
- keep Lighthouse scrutiny on transcript-heavy layouts

### `/agents`

Target role: agent orchestration console.

Remaining completion work:

- deepen thread lifecycle testing for restart, resume, export, and tool timeline
- verify stable `toolCallId` behavior under multi-tool and repeated-tool cases
- extend coverage around thread switching and cross-agent session persistence

### `/tasks`

Target role: workforce execution queue.

Completion work:

- add URL state for status, assignee, project, and priority filters
- add task detail drawer or side panel with back-link-safe navigation
- surface escalation and approval states more clearly
- add direct jump paths to related outputs, review items, and workspaces

### `/goals`

Target role: strategic goal register and project goal board.

Completion work:

- separate global goals from project-scoped goals
- add goal status filters, sort, and due-horizon visibility in URL state
- connect goals to tasks and workplan items with tested cross-links

### `/notifications`

Target role: operational inbox and alert feed.

Completion work:

- distinguish system alerts, agent escalations, reminders, and approvals
- persist filter state and dismissed states
- add tested deep links back into the originating route or item

### `/workplanner`

Target role: planning board for work allocation and sequencing.

Completion work:

- strengthen project-aware planning views
- add drag/drop or explicit reprioritization actions only if they remain
  deterministic and testable
- verify navigation from workplan items to tasks, outputs, and conversations

### `/workspace`

Target role: agent workspace and operating-state surface.

Completion work:

- expose active workspaces by agent and project
- add clearer health, staleness, and ownership cues
- verify cross-links into tasks, conversations, outputs, and reviews

### `/activity`

Current state:

- route-local client page
- fetches `/api/activity`
- basic filters and feedback controls

Target role: operator timeline for everything that happened in Athanor.

Required work:

- move into `src/features/history/activity-console.tsx`
- add typed activity snapshot contract and server wrapper
- add richer filters: agent, project, category, severity, timeframe
- add expandable timeline details with safe back navigation
- add deep links into conversations, tasks, outputs, and affected projects
- persist filters in the URL
- add smoke coverage for timeline load, filter changes, and link traversal

### `/conversations`

Current state:

- route-local client page
- fetches `/api/conversations`
- expandable logged conversation cards

Target role: searchable transcript archive.

Required work:

- move into `src/features/history/conversations-console.tsx`
- add typed archive contract and URL-backed filters
- support agent, project, date range, and thread filters
- make expansion state, selected conversation, and related-thread navigation
  explicit and back-link safe
- add copy/export/share actions and route to current live thread where possible
- add smoke coverage for expand/collapse, filters, and transcript navigation

### `/gallery`

Current state:

- route-local client page
- uses `/api/comfyui/*`
- mixes generation controls with output browsing

Target role: creative production gallery for ComfyUI and project outputs.

Required work:

- move into `src/features/creative/gallery-console.tsx`
- add a dashboard-owned gallery snapshot route that unifies history, queue, and
  stats
- split browse, queue, and quick-generate into clear panels
- add project-aware filters, especially EoBQ vs non-project output
- add detail drawer/lightbox with keyboard navigation and back-link safety
- add smoke coverage for image history, filters, queue state, and generation
  entry actions

### `/home`

Current state:

- route-local server page
- directly probes Home Assistant

Target role: home domain overview and future Home Assistant control surface.

Required work:

- add `/api/home` to own Home Assistant status normalization
- move page into `src/features/home/home-console.tsx`
- preserve onboarding/blocked-state messaging but stop direct route-level fetch
- add clear setup ladder: service reachability, onboarding, home-agent state,
  automation integration
- add smoke coverage for configured, degraded, and unavailable fixture states

### `/insights`

Current state:

- route-local client page
- fetches `/api/insights` and `/api/insights/run`

Target role: behavioral and systems insight console.

Required work:

- move into `src/features/intelligence/insights-console.tsx`
- normalize insight pattern types and severity display through typed contracts
- add URL state for severity, agent, category, and timeframe filters
- separate passive insight review from active "run now" operations
- link patterns back to the underlying route or data source when possible
- add smoke coverage for manual runs, filtering, and degraded partial data

### `/learning`

Current state:

- route-local client page
- aggregates `/api/learning/metrics`, `/api/learning/improvement`, and
  `/api/insights`

Target role: learning and continuous-improvement console.

Required work:

- move into `src/features/intelligence/learning-console.tsx`
- add a unified server-owned learning snapshot endpoint instead of route-local
  fan-out
- separate health summary, metrics, benchmark actions, and improvement queue
- add clearer benchmark action states and post-run result handling
- persist selected category/time horizon in the URL
- add smoke coverage for metrics load, improvement load, benchmark triggers, and
  partial upstream failure

### `/media`

Current state:

- route-local client page
- uses `/api/media` plus `/api/stash/stats`
- combines Plex, Sonarr, Radarr, and Stash into one long page

Target role: media operations console for the VAULT domain.

Required work:

- move into `src/features/media/media-console.tsx`
- create a unified `/api/media/overview` route that returns a normalized media
  dashboard snapshot
- separate streaming activity, download queue, release calendar, library stats,
  and Stash state into stable sections
- add safe actions: open app, copy endpoint, refresh section, export summary
- add URL-backed source filters and section anchors
- add smoke coverage for all section loads and all external-tool link targets

### `/monitoring`

Current state:

- route-local server page
- directly queries Prometheus

Target role: deep monitoring console for the cluster.

Required work:

- move into `src/features/monitoring/monitoring-console.tsx`
- add `/api/monitoring/overview` and `/api/monitoring/history` so the page stops
  querying Prometheus directly
- expose node, network, disk, load, and trend state through typed DTOs
- add time-window and node filters in the URL
- link to Grafana and raw Prometheus queries through explicit action slots
- add smoke coverage for history windows, node filters, and degraded metric gaps

### `/more`

Current state:

- route-local index of pages

Target role: route directory and mobile fallback navigator.

Required work:

- align entries with the full route registry and command palette taxonomy
- verify every listed route has working navigation and correct labels
- add smoke coverage that walks the index and validates destinations

### `/offline`

Current state:

- route-local offline fallback

Target role: resilient offline and degraded-state UX.

Required work:

- align styling with the operator shell
- add tested retry path and navigation back into the last known route
- verify service worker and offline-entry behavior if that path is retained

### `/outputs`

Current state:

- route-local client page
- fetches `/api/outputs` and file-content routes
- allows feedback on outputs

Target role: agent output explorer and handoff surface.

Required work:

- move into `src/features/history/outputs-console.tsx`
- add typed output index and output detail contracts
- support project, agent, file type, and recency filters in URL state
- add detail panel with safe back navigation and richer preview handling
- add explicit jump paths to originating task, review, conversation, or project
- add smoke coverage for file browsing, preview loading, feedback, and back
  navigation

### `/personal-data`

Current state:

- route-local server page
- directly queries Qdrant for collection stats

Target role: personal knowledge and memory exploration surface.

Required work:

- add `/api/personal-data/overview` to own the Qdrant and Neo4j snapshot model
- move page into `src/features/memory/personal-data-console.tsx`
- preserve search, graph, recent items, and category breakdown, but unify them
  behind one dashboard-owned entry contract
- add project-aware and entity-type filters in URL state
- add degraded-state handling when Qdrant and Neo4j disagree
- add smoke coverage for search, graph summary, recent items, and empty states

### `/preferences`

Current state:

- route-local client page
- reads and writes `/api/preferences`
- mixes push setup with preference search and entry

Target role: preference and operator-memory management surface.

Required work:

- move into `src/features/memory/preferences-console.tsx`
- separate notification setup from memory/preference operations
- add typed form state, submission states, and search result normalization
- add URL-backed search filters and recent-query persistence
- add smoke coverage for search, store, filter, and push-manager coexistence

### `/review`

Current state:

- route-local client page
- fetches workforce task data and renders code-review artifacts

Target role: review and approval console.

Required work:

- move into `src/features/workforce/review-console.tsx`
- split review queue, selected item detail, diff view, and feedback actions
- add URL state for selected review item and queue filters
- ensure every reviewed artifact links back to task, output, agent, and project
- add smoke coverage for review selection, diff rendering, feedback, and back
  navigation

### `/terminal`

Current state:

- route-local utility route

Target role: controlled operator terminal surface.

Required work:

- decide whether this remains a first-class shell route or a utility launch
- if retained, align shell framing, keyboard flow, and connection status display
- add smoke coverage for mount, reconnect, and empty/unavailable states

## Execution Order

### Wave 1: Quality hardening and smoke coverage

- Add route smoke coverage for every route in the registry
- Add API smoke coverage for every read-oriented dashboard-owned endpoint
- Add shell/back-link coverage from `/` and `/more`
- Fix failures before broad route rebuild work continues

### Wave 2: P1 legacy console migrations

- `/monitoring`
- `/media`
- `/insights`
- `/learning`
- `/review`
- `/activity`
- `/conversations`
- `/outputs`
- `/preferences`
- `/personal-data`

Deliverable:

- all P1 routes moved onto feature modules plus dashboard-owned APIs or config
  helpers

### Wave 3: P2 domain and utility route migrations

- `/gallery`
- `/home`
- `/terminal`
- `/more`

Deliverable:

- all remaining interactive routes aligned with the same shell/data/state model

### Wave 4: P3 resilience and polish

- `/offline`
- route-level loading/error/not-found boundary review
- final command-palette, `/more`, and back-link verification sweep

## Smoke and Regression Matrix

Every route should eventually have the following minimum coverage:

| Route type | Required coverage |
| --- | --- |
| Console route | render smoke, heading, primary CTA/action, URL state |
| List/detail route | render smoke, filter smoke, selection, back navigation |
| History/archive route | render smoke, expand detail, filter, copy/export path |
| Domain overview route | render smoke, degraded-state render, external link checks |
| Utility route | render smoke, unavailable-state coverage |

Additional required cross-route coverage:

- shell navigation for every route group
- command-palette navigation to all primary routes
- `/more` route index link validation
- browser back/forward navigation from detail states and modal/lightbox surfaces
- API shape checks for all dashboard-owned read endpoints
- no console errors, page errors, or failed same-origin route loads during smoke
  runs

## Exit Criteria

The sub-page completion program is done when:

1. Every route is either:
   - on the feature-console architecture, or
   - intentionally deprecated and removed from the route registry
2. No production route fetches raw remote cluster services directly from the UI
   layer
3. Every route has tested forward and backward navigation
4. Every route has deterministic nominal, loading, empty, degraded, and error
   behavior
5. The route smoke suite covers the entire public dashboard route surface
