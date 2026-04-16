# The Athanor Command Center

> Visual-source note: the structural and operator-workflow decisions in this document remain valid, but its older furnace/alchemical visual metaphor is superseded by the visual-system pack in [`./visual-system/README.md`](./visual-system/README.md). Use the visual-system docs as the canonical source for visual identity, token direction, materials, typography, and signal grammar.

> Deployment note: hostnames, ports, and service placement mentioned here are design-era context only. Live deployment truth comes from [`platform-topology.json`](/C:/Athanor/config/automation-backbone/platform-topology.json), [`STATUS.md`](/C:/Athanor/STATUS.md), and the generated operations reports.

**Status:** Design complete — ready for ADR + implementation
**Date:** 2026-02-25
**Synthesizes:** 5 research documents (web dev environments, command center UI, human-in-the-loop, mobile PWA, novel interface patterns)
**Depends on:** ADR-007 (Dashboard), ADR-017 (Meta-Orchestrator), ADR-018 (GPU Orchestration)

---

## What This Is

The Athanor Command Center is the evolution of the existing dashboard (now fronted canonically at `https://athanor.local/`, with the DEV runtime fallback still available at `http://dev.athanor.local:3001/` while hostname rollout finishes, Next.js 16 + React 19 + shadcn/ui + Tailwind v4) from a monitoring surface into the **primary interface** for the entire system. It replaces the terminal as the default way Shaun interacts with Athanor.

It is:
- A **PWA** that works equally well on desktop and phone — both are first-class
- A **command center** — see, steer, approve, build
- A **living surface** — ambient when healthy, urgent when needed
- A **feedback mechanism** — every interaction teaches the system

It is not:
- An IDE (agents write code, not Shaun)
- A terminal replacement (terminal access is embedded as a fallback)
- A separate app (it's the existing dashboard, evolved)

---

## Design Philosophy

### Historical Metaphor Note

The original command-center concept used a furnace/alchemical metaphor to explain constant system activity. That metaphor is now historical context only.

The active visual-system metaphor is a futurist control-room identity focused on operator trust, signal clarity, and control. Keep the structural product ideas from this document, but use the visual-system pack as the source of truth for the current visual direction.

### Seven Principles

These are synthesized from SpaceX mission control patterns, Waymo fleet operations, calm technology research, gaming HUD design, and smart home dashboard conventions.

1. **Calm by default, urgent when needed.** The interface is ambient when healthy — readable at a glance, not demanding attention. Information surfaces progressively: subtle indicator → prominent card → persistent alert → modal interruption.

2. **Three layers of depth.** Every piece of information exists at one of three layers:
   - **Pulse Strip** — always visible, aggregate health, answers "is everything okay?"
   - **Domain Cards** — expandable summaries on the home surface
   - **Detail Pages** — full information and controls per domain

3. **State-driven, not static.** The interface changes based on what's happening. Active agents expand. Idle domains recede. Escalations demand attention. This is information architecture responding to reality.

4. **Actions, not just monitoring.** Every domain card offers at least one action. GPU: sleep/wake model. Agents: trigger/cancel task. Media: request download. Home: toggle device. Services: restart.

5. **Agent transparency.** Autonomous agents require trust. Trust requires visibility: reasoning trace, resource consumption, override controls, and clear escalation points.

6. **Information density through typography.** Don't reduce density by removing information. Increase it through typographic hierarchy: Cormorant Garamond for headings, Inter for data, tabular mono for metrics, consistent spacing rhythm, color for status only.

7. **Dark and deliberate.** Not "dark mode applied to a light design." Dark-first: charcoal and carbon neutrals (not flat black), luminance-based elevation, disciplined signal colors, bright structural accent, semi-bold typography.

---

## Core Concepts

### The Home Surface ("The Furnace")

The dashboard home page is a living surface. A dark graphite canvas that breathes with the system's rhythm.

**Ambient state communication:**
- Background tone reflects overall system activity. Dark and restrained when idle. More energized and luminous when busy. The surface gains signal intensity when the system is working.
- Subtle ambient glow at screen edges shifts with system health. Healthy = barely visible. Attention needed = cool signal light intensifying inward.
- The central area is nearly empty when everything is fine. Information appears when relevant and fades when resolved.

**Agent constellation:**
- Each of the 8 agents is an ember/icon in its signature color, arranged in a gentle arc
- Active agents pulse gently. Idle agents are dim. Escalating agents glow brighter and drift toward center.
- Click opens a detail card (slides in, doesn't replace the surface)

**Contextual widget surfacing (Smart Stack):**
- 2-3 widget cards float on the surface, auto-selected by relevance:
  - Morning: overnight agent summary + system health + upcoming tasks
  - Work session: active project metrics + relevant agents + GPU status
  - Evening: media now playing + home status
  - Escalation: the escalating agent's card replaces everything until resolved

### The Crew (Agent Portrait Bar)

Persistent across all views. A horizontal row of 8 agent circles at the bottom of the screen (like an RPG party bar).

| State | Visual Treatment |
|-------|-----------------|
| Idle | Dim, static |
| Processing | Gentle pulse in agent color |
| Success | Brief bright flash, settle |
| Failed | Brief red flash, cool idle |
| Escalating | Continuous signal-blue pulse, larger |
| Disabled | Greyed out, smaller |

Click opens an agent detail panel (slides up from bottom):
- Identity: name, role, icon, color
- Stats: tasks completed (today/week/all-time), success rate, avg response time
- Current task: what it's doing, progress indication
- Recent activity: last 5 actions with outcomes
- Feedback history: recent thumbs up/down
- Performance trend: 7-day sparkline

When agents collaborate (general-assistant delegates to coding-agent), a brief connection animation flashes between portraits.

### The Command Palette (Cmd+K)

The primary navigation mechanism. Replaces page-based navigation as the fastest way to do anything.

- **shadcn/ui CommandDialog** + fuzzy search
- Searchable: agents, services, projects, actions, settings, lenses
- Recent commands history
- Keyboard shortcut: Cmd+K (desktop), swipe-down or dedicated button (mobile)
- Actions: "trigger media scan", "sleep GPU 0", "show EoBQ status", "focus on creative"
- Agent dispatch: "ask research-agent about..." routes to specific agent

### The Lens (Intent-Driven Layout)

The dashboard adapts based on declared intent. Same URL, different view.

**Default lens (no focus):** The Furnace home surface.

**Project lens (e.g., "EoBQ"):** Creative Agent and Coding Agent become primary. Activity stream filters to EoBQ. Quick actions change to "Generate scene", "Review assets". GPU status highlights creative workloads.

**Agent lens (e.g., Creative Agent):** That agent's card fills the main area. Full history, tasks, metrics, configuration. Other agents become small, peripheral.

**Domain lens (e.g., "Media"):** Media Agent expands. Plex now playing, library health, Sonarr/Radarr queue, Tautulli analytics.

**System lens (e.g., "Health check"):** Node cards with full metrics. Service health grid. GPU utilization charts. Active alerts.

**Activation:** Command palette, agent card click, widget click, voice ("Focus on EoBQ"), URL query param for bookmarkability.

### The Stream (Unified Activity)

A single, unified activity stream that merges agent activity, system events, user conversation, and escalation cards. Replaces separate Activity, Tasks, Chat, and Notifications pages as a single chronological view.

**Entry types:**
- Agent activity: "Creative Agent generated 3 images" (with thumbnails inline)
- System events: "GPU utilization peaked at 87%" (with sparkline inline)
- User messages: "Focus on EoBQ tonight" (triggers lens change)
- Escalation cards: "Media Agent wants to reorganize. Approve?" (with action buttons)
- Task completions: "Coding Agent finished review (4 files)" (with diff preview)

**Threading:** Complex interactions expand into threads. A 10-step task is one entry with a "10 steps" link that expands.

**Filtering:** All | Agents | System | Chat | Escalations

### Generative UI (Chat Responses)

Using Vercel AI SDK, chat responses can render React components inline:
- Pure text (normal response)
- React component (GPU chart, media gallery, task status board)
- Action card (approval request, confirmation dialog)
- Agent redirect ("The creative agent will handle this")

This turns the chat from a text-only interface into a rich control surface where asking "how are the GPUs?" returns a live interactive chart, not just text.

---

## Human-in-the-Loop Framework

### The Attention Budget

A single operator with a day job has ~1-2 hours of active attention per weekday evening, 4-8 hours on weekends. Every interaction the system demands is a withdrawal.

**Rules:**
- **Hard notification budget:** Max 5-10 Notable + 0-2 Critical per day. Everything else is Background (logged, never pushed).
- **30-50% actionable target.** If more than half of surfaced items need no action, the system wastes attention.
- **Correlation before notification.** One notification for a situation, not one per agent that noticed it.
- **Fatigue modeling.** If Shaun ignores a category 3 times in a row, suppress until weekly review.
- **Context respect.** Don't push during focused work or at 2 AM.

### Autonomy Levels

Per-agent, per-action-category, using a simplified Sheridan-Verplanck scale:

| Level | Name | Behavior | Examples |
|-------|------|----------|----------|
| A | Full Auto | Act and log. Human sees on request. | Embedding, knowledge indexing, routine monitoring |
| B | Inform | Act and notify summary. | Media management, HA automation, scheduled tasks |
| C | Propose | Recommend and wait for approval. | Spending money, deleting data, changing config |
| D | Manual | Gather info and present options. Human decides. | New service deployment, hardware changes |

The existing 3-tier escalation protocol (act/notify/ask) maps directly to Levels A/B/C.

### Goals Over Tasks

Replace static scheduler prompts with goal-directed agent behavior. Commander's intent model.

**Format:** Each agent has:
- **Purpose** (already in `agent-contracts.md`)
- **Goals:** Natural language with context. "Keep the home comfortable *because Amanda is sensitive to temperature changes*"
- **Constraints:** What they must never do. Max spend, never-delete, always-ask-before-X.
- **Key results:** Measurable outcomes.

Goals are specified completely enough that agents can act for days without human input. Agents can propose goal changes: "I notice you always override 68F to 70F. Should I update the target?"

### The Feedback Loop

**Three types, three cadences:**

1. **Implicit feedback (primary, zero-effort):** Track what Shaun acts on, ignores, undoes, overrides. Behavioral signals require zero effort and are the most sustainable. The absence of correction is a positive signal.

2. **Explicit feedback (binary):** Thumbs up/down on agent outputs. "Don't do this again." "Do more of this." Netflix proved binary beats granular.

3. **Three cadences:**
   - *Immediate:* Corrections applied now. Agent adjusts behavior for this session.
   - *Daily digest:* Summary of what happened, what was notable, what the system learned.
   - *Weekly review:* Goal-level assessment, autonomy level adjustments, trend analysis.

**Impact visibility:** "Based on your corrections this week, the media agent now prioritizes 4K sources. Here's what changed."

### Trust Calibration

- **Track record display:** Per-agent: total actions, success rate, correction rate, 7-day trend. The single most important trust signal.
- **Explain on demand:** Every action has a retrievable justification, hidden by default (noise reduction).
- **Meaningful friction for irreversible actions:** Level C approval shows what will happen, alternatives, and risk — not just "OK".
- **Rubber-stamp detection:** If approval rate exceeds 95% over 20+ requests, suggest raising autonomy level.
- **Progressive trust building:** New agents start at Level C. Demonstrate reliability → graduate to B → then A.

---

## Mobile Architecture

### PWA (Not Native)

PWA covers everything Athanor needs. No native wrapper.

| Capability | Status |
|------------|--------|
| Install to home screen | Yes (Android + iOS) |
| Push notifications | Yes (VAPID, no Firebase) |
| Offline awareness | Yes (service worker) |
| Standalone display (no browser chrome) | Yes |
| Biometric auth (WebAuthn) | Yes (needs HTTPS) |

Capacitor is the escape hatch if iOS push proves unreliable. Do not invest in it now.

### Mobile Layout

- **Bottom tab bar** (5 tabs): Home, Agents, Stream, Chat, More
- **Sidebar on desktop** (≥768px), bottom nav on mobile (<768px)
- **44px minimum touch targets**
- **Pull-to-refresh** with loading indicator
- **Card-based layouts** (not tables/grids)
- **Tap to expand** for detail views

### Mobile-Specific GPU Card

```
+-----------------------------------+
| RTX 5070 Ti #0        [87%] [==] |  <- Name, util, mini bar
| 12.4 / 16.3 GB  |  52C  |  185W |  <- VRAM, temp, power
+-----------------------------------+
```

Tap to expand: sparkline history, loaded model, process list.

### Real-Time: SSE Over WebSocket

- SSE for dashboard home, GPU status, agent status, system events
- WebSocket for chat only (bidirectional needed)
- SSE reconnects automatically on visibility change (tab switch, phone sleep)
- Server-side aggregation: SSE endpoint subscribes to Redis pub/sub (GWT workspace broadcasts)

### Push Notifications

- VAPID keys (no Firebase dependency)
- `web-push` npm package on dashboard backend
- Notification categories: Critical (system down, data loss), Notable (task complete, escalation), Background (logged only)
- Action buttons in notifications: Approve/Reject from notification tray
- Budget enforcement: agent framework tracks daily notification count

---

## Development Environment Integration

The command center optionally embeds development tools rather than replacing them.

### Terminal Page (xterm.js)

An embedded terminal page in the dashboard for Claude Code access:

```
Command Center runtime (DEV:3001)
  └── /terminal page
        └── react-xtermjs (dynamic import, ssr: false)
              └── WebSocket → Terminal Backend (DEV)
                    └── node-pty → Claude Code CLI
```

This is the "drop down to terminal" escape hatch, not the primary interaction.

### Claudeman (Standalone)

Deploy Claudeman on DEV for multi-session Claude Code management:
- 20 parallel sessions, zero-lag mobile input
- Live agent visualization
- Overnight autonomous operation with respawn controller
- Accessible at DEV:3000 on LAN

### Claude Code Remote Control (Zero-Deploy)

`claude remote-control` for instant mobile access via claude.ai app. No infrastructure needed. One session at a time, Anthropic-dependent.

### OpenHands (Complementary)

Deploy on Node 1 as alternative AI coding interface for GitHub issue resolution and sandboxed tasks.

### Priority

| Layer | Effort | What It Gives |
|-------|--------|---------------|
| Remote Control | Zero | Mobile Claude Code access now |
| Claudeman | 30 min | Self-hosted web UI, multi-session, overnight autonomous |
| Terminal page in dashboard | 1-2 days | Integrated terminal from one URL |
| OpenHands | 1 hour | Alternative AI coding interface |

---

## Technical Architecture

### System Diagram

```
Phone / Desktop Browser
  │
  ├── PWA (install to home screen)
  │     ├── Service Worker (push handler, offline fallback)
  │     └── VAPID push subscription → Dashboard API
  │
└── Command Center (DEV:3001, Next.js 16)
        │
        ├── Layout (persistent)
        │     ├── Pulse Strip (SSE-driven, always visible)
        │     ├── Sidebar Nav (desktop) / Bottom Nav (mobile)
        │     ├── Agent Portrait Bar (persistent bottom)
        │     ├── Command Palette (Cmd+K overlay)
        │     └── Notification Toasts (priority-based)
        │
        ├── Home Page ("The Furnace")
        │     ├── Ambient CSS (--system-warmth, --breath-speed)
        │     ├── Agent Constellation
        │     └── Smart Stack Widgets (contextual)
        │
        ├── Stream Page (unified activity)
        │     └── Virtual scroll, type filtering, threading
        │
        ├── Chat Page (generative UI)
        │     └── Vercel AI SDK → streaming React components
        │
        ├── Detail Pages (domain-specific)
        │     ├── /gpu — full GPU metrics + controls
        │     ├── /agents — agent board + task queue
        │     ├── /services — health grid + restart controls
        │     ├── /media — library + downloads
        │     ├── /terminal — xterm.js embedded
        │     └── etc.
        │
        └── API Routes
              ├── /api/events (SSE endpoint, subscribes to Redis pub/sub)
              ├── /api/push (VAPID push trigger)
              ├── /api/chat (Vercel AI SDK → agent server)
              └── /api/feedback (implicit + explicit feedback ingestion)

Data Sources:
  ├── Agent Server (Node 1:9000) — agents, tasks, activity, workspace, escalation
  ├── GPU Orchestrator (Node 1:9200) — GPU status, zone management
  ├── Prometheus (VAULT:9090) — metrics, history
  ├── Redis (VAULT:6379) — GWT workspace, pub/sub, task state
  ├── Qdrant (Node 1:6333) — knowledge, conversations, preferences, activity
  └── Home Assistant (VAULT:8123) — home automation entities
```

### New Dependencies

| Package | Purpose | Size |
|---------|---------|------|
| `motion` | Ambient animation, layout transitions, agent portraits | ~30 KB |
| `ai` (Vercel AI SDK) | Generative UI, streaming React components | ~50 KB |
| `web-push` | VAPID push notifications | ~15 KB |
| `react-xtermjs` | Terminal page | ~5 KB (+xterm.js ~200 KB) |
| `cmdk` | Command palette (already in shadcn/ui) | ~5 KB |

### SSE Architecture

```typescript
// /api/events/route.ts
export async function GET() {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Subscribe to Redis pub/sub (GWT workspace broadcasts)
      const redis = createRedisClient();
      await redis.subscribe('athanor:workspace:broadcast');

      redis.on('message', (channel, message) => {
        controller.enqueue(
          encoder.encode(`data: ${message}\n\n`)
        );
      });

      // Also poll agent health every 5s
      const interval = setInterval(async () => {
        const status = await fetchSystemStatus();
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(status)}\n\n`)
        );
      }, 5000);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

---

## Implementation Plan

### Phase 1: Foundation (1-2 weekends)

**Goal:** PWA install + mobile layout + command palette + ambient foundation

1. **PWA manifest + service worker**
   - `app/manifest.ts` with Athanor branding (graphite/steel dark theme)
   - Minimal `public/sw.js` (push handler + notification click + offline fallback)
   - Generate PWA icons (192, 512, 512-maskable, 180 apple-touch)
   - Verify install-to-home-screen on phone

2. **Mobile layout**
   - `BottomNav` component (5 tabs: Home, Agents, Stream, Chat, More)
   - Responsive layout: sidebar ≥768px, bottom nav <768px
   - 44px touch targets, `overscroll-behavior: contain`
   - Mobile-specific card variants (compact GPU, compact agent)

3. **Command palette**
   - shadcn/ui `CommandDialog` with fuzzy search
   - Categories: Agents, Services, Projects, Actions, Lenses
   - Recent commands history
   - Keyboard shortcut registration (Cmd+K)

4. **Calm visual foundation**
   - CSS custom properties: `--system-warmth` (0-1, driven by activity), `--breath-speed` (driven by load)
   - Apply to background gradients, border colors, accent elements
   - Install `motion` library for transitions

### Phase 2: The Living Home (2-3 weekends)

**Goal:** Agent portrait bar + Furnace home surface + SSE real-time

5. **Agent portrait bar**
   - Persistent bottom bar with 8 agent circles
   - State-driven CSS animations (idle/active/escalating)
   - Click opens detail panel (slides up)
   - Agent stats aggregated from `/v1/activity` and `/v1/tasks`

6. **SSE real-time endpoint**
   - `/api/events` subscribes to Redis pub/sub
   - `useSystemStatus` client-side hook with EventSource
   - Reconnection on `visibilitychange`
   - Connection status indicator (online/offline badge)
   - Replace polling on home page, GPU page, agent page

7. **Furnace home surface**
   - Ambient CSS driven by SSE-pushed system metrics
   - Agent constellation (ember icons in signature colors)
   - Smart Stack widget slots (2-3 contextual cards)
   - Initial widgets: GPU summary, Agent activity summary, Active tasks

8. **Glanceable widgets**
   - Small/medium/large sizes
   - GPU status widget (cluster utilization, hottest GPU)
   - Agent summary widget (active count, last escalation)
   - Active tasks widget (running/queued/completed counts)
   - Media widget (now playing, recent additions)

### Phase 3: Intelligence (2-4 weekends)

**Goal:** Unified stream + generative UI + push notifications + lens mode

9. **Unified activity stream**
   - Merge activity + tasks + chat + system events
   - Agent color coding, type filtering
   - Expandable threading for multi-step tasks
   - Virtual scroll for performance
   - Replaces separate Activity and Notifications pages

10. **Generative UI (chat)**
    - Install Vercel AI SDK (`ai` package)
    - Chat responses render React components inline
    - Start with 3-4 component types: GPU chart, media gallery, task status, approval card
    - Agent routing: "ask creative-agent about..." delegates appropriately

11. **Push notifications**
    - VAPID key generation + `.env` storage
    - Push subscription management (subscribe/unsubscribe UI)
    - Wire agent escalation events → push
    - Wire system alerts (GPU overtemp, service down) → push
    - Notification action buttons (Approve/Reject)
    - Daily notification budget enforcement

12. **Lens mode**
    - Lens state manager (React context + URL query param)
    - Per-lens layout definitions (which components, what size, what order)
    - Command palette triggers lens changes
    - Smooth layout transitions via `motion`
    - Initial lenses: Default, System, Media, Creative

### Phase 4: Human-in-the-Loop (2-3 weekends)

**Goal:** Goals API + feedback system + trust calibration + daily digest

13. **Goals API**
    - `POST /v1/goals` — natural language goals with constraints
    - `GET /v1/goals` — list active goals per agent
    - `POST /v1/goals/steer` — natural language steering ("focus on media quality")
    - Store in Redis or Qdrant for persistence
    - Wire into scheduler: goals drive agent task generation

14. **Feedback system**
    - Implicit: track actions (tap, ignore, undo, override) on agent outputs
    - Explicit: binary thumbs up/down on activity stream entries
    - Store in `preferences` Qdrant collection
    - Impact visibility: "This feedback affected 3 subsequent decisions"
    - Dashboard feedback surface: inline micro-feedback on all agent outputs

15. **Trust calibration**
    - Per-agent track record display on agent detail panel
    - Rubber-stamp detection (95%+ approval over 20+ requests → suggest Level upgrade)
    - Intervention rate tracking (Prometheus metric, downward trend goal)
    - Progressive trust: new agents start Level C, graduate based on track record

16. **Daily digest**
    - Scheduled task (general-assistant, 6:55 AM) compiles overnight summary
    - Available via dashboard widget, push notification, and voice ("Athanor, what happened overnight?")
    - Content: agent actions, system events, escalations resolved, feedback impact

### Phase 5: Advanced (ongoing)

17. **Terminal page** — xterm.js + WebSocket to DEV
18. **Diff viewer** — git diff rendering for task outputs
19. **Anticipatory scheduling** — learn temporal patterns, pre-compute relevant info
20. **Dynamic autonomy** — raise autonomy when away, lower when active
21. **Convention library** — store learned conventions, surface for periodic confirmation
22. **Smart Stack ML** — time + behavior + escalation-based widget priority

---

## What This Changes in Existing Architecture

### Pages Retired
- `/activity` → merged into unified Stream
- `/notifications` → merged into unified Stream + push notifications

### Pages Evolved
- `/` (home) → The Furnace surface
- `/chat` → Generative UI with rich embeds
- `/agents` → Part of Stream + Agent Portrait Bar + Agent Lens

### Pages Added
- `/terminal` — xterm.js embedded terminal
- `/stream` — unified activity/task/chat/notification stream

### New Backend Endpoints
- `/api/events` — SSE real-time stream (Redis pub/sub)
- `/api/push` — VAPID push trigger
- `/api/feedback` — implicit + explicit feedback ingestion

### Agent Server Changes
- Goals API (`/v1/goals`, `/v1/goals/steer`)
- Formalized autonomy levels in agent config
- Daily digest scheduled task
- Notification budget tracking
- Feedback-aware context injection

---

## Open Questions

1. **Icon design.** PWA icons need custom design. The current favicon is Next.js default.
2. **Mobile bottom nav tabs.** Proposed: Home, Agents, Stream, Chat, More. But "GPUs" and "Tasks" might be more useful than some of these.
3. **SSE backend source.** Does the SSE endpoint poll on behalf of clients (server-side aggregation) or subscribe to Redis pub/sub (GWT workspace already broadcasts there)? Recommendation: Redis pub/sub primary + 5s polling for metrics not on pub/sub.
4. **Notification trigger location.** Where do push triggers live? Agent framework (Node 1:9000) sends to the command-center API on DEV `:3001` which then sends to the browser? Or agent framework sends directly via web-push? Recommendation: agent framework fires webhook to the command-center API, which manages subscriptions and sends pushes.
5. **Auth.** No auth on LAN is fine for now. WebAuthn requires HTTPS. Defer until remote access is needed.
6. **Vercel AI SDK + local models.** AI SDK supports any OpenAI-compatible endpoint. Wire to LiteLLM (VAULT:4000) for local model generative UI. Test quality with Qwen3.5-27B.

---

## Success Criteria

The command center is successful when:

1. Shaun checks the system from his phone as naturally as checking the weather
2. 95% of agent activity requires no intervention
3. The remaining 5% is surfaced clearly with enough context to decide in <30 seconds
4. Feedback given today visibly affects agent behavior tomorrow
5. No page takes more than 2 taps to reach on mobile
6. The system feels alive — not a dead dashboard you load to read numbers

---

## Research Sources

This design synthesizes findings from 5 research documents totaling ~4,500 lines:

- `docs/research/2026-02-25-web-development-environments.md` — Browser IDEs, Claude Code web access, Claudeman, OpenHands, xterm.js, orchestrator's workbench concept
- `docs/archive/research/2026-02-25-command-center-ui-design.md` — SpaceX, smart home, NOC, gaming HUD, adaptive UI patterns, dark dashboard design, real-time frameworks
- `docs/research/2026-02-25-human-in-the-loop-patterns.md` — Waymo, trading, RLHF, drones, recommendations, goal-setting, attention management, trust calibration, feedback loops
- `docs/research/2026-02-25-mobile-pwa-architecture.md` — PWA capabilities, service workers, VAPID push, SSE, mobile visualization, authentication, responsive patterns
- `docs/research/2026-02-25-novel-interface-patterns.md` — Conversational UI, calm technology, spatial interfaces, agent-as-character, intent-based interfaces, generative UI, glanceable design, feedback surfaces
