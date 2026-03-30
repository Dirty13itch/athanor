# Command Center and Mission Control UI Design Patterns

**Date:** 2026-02-25
**Status:** Complete -- ready for design decisions
**Supports:** Dashboard evolution from monitoring tool to command center
**Depends on:** ADR-007 (Dashboard + Unified Interface), existing Next.js + shadcn/ui stack

---

## Context

The Athanor dashboard is a Next.js app (React 19, Next.js 16, shadcn/ui, Tailwind CSS v4, Radix) deployed at DEV via athanor.local (runtime fallback dev.athanor.local:3001) with 16 pages and 26 service health checks. It currently works as a monitoring surface -- you can see what is happening, but you cannot steer the system from it in any meaningful way.

The goal is to evolve it into a true command center: the single surface through which the human operator sees, steers, and interacts with the entire autonomous system. This means displaying real-time state of 4 nodes, 7 GPUs, 8 AI agents, 26+ services, media management, home automation, creative tools, and game development infrastructure -- and providing controls for all of them.

This research examines design patterns from mission control systems, smart homes, NOCs, gaming HUDs, and modern dashboard frameworks to extract principles and specific recommendations for our stack.

---

## 1. SpaceX Mission Control: Density Through Discipline

### Technology Stack

SpaceX Crew Dragon's entire flight interface runs on Chromium, with the UI written in HTML and JavaScript using a custom reactive framework (not React, not Angular -- a self-written library for quality control reasons). They use open-source libraries only as a last resort. The displays are touchscreens -- the first spacecraft operated almost entirely through touch interfaces.

Source: [HN discussion on Dragon tech stack](https://news.ycombinator.com/item?id=23404310), [JavaScript in Space - InfoQ](https://www.infoq.com/news/2020/06/javascript-spacex-dragon/)

### Design Principles

**1. Minimalism as safety.** SpaceX's data visualizations eliminate anything that is not critical. If a detail is not essential, it does not belong. The most important information is always the most prominent. This is not aesthetic minimalism -- it is operational minimalism where clutter can kill.

**2. Information hierarchy through layout zones.** The Dragon interface uses:
- A **side menu** for section navigation (roughly 25-30 individual pages)
- A **top bar** with persistent real-time indicators
- A **main content area** that changes based on selected subsystem
- A **globe view** for trajectory and position

**3. Subsystem isolation.** Each subsystem (navigation, propulsion, life support, etc.) gets its own dedicated page. Vehicle screens show overview, functions, and alerts for each subsystem individually. This prevents cross-contamination of unrelated information.

**4. Hardware fallbacks for critical actions.** Even with full touchscreen operation, physical buttons exist below the displays for mission-critical operations. The lesson: always provide a fast path to critical actions, not buried in menus.

**5. Iterative testing with actual operators.** SpaceX worked directly with astronauts through simulations, prototypes, and feedback loops. The placement of every element was evaluated for ergonomics and cognitive load under stress.

**6. Digital twins for monitoring.** Mission Control uses virtual representations of physical assets with real-time data, giving operators a digital replica to monitor trajectory, loads, and propulsion systems.

Source: [Shane Mielke - Crew Dragon Displays](https://shanemielke.com/work/spacex/crew-dragon-displays/), [Dillon Baird - Recreating Dragon UI](https://dillonbaird.io/articles/mutantdragon/), [Black Label - Dataviz at SpaceX](https://blacklabel.net/blog/data-visualization/dataviz-in-action/dataviz-at-spacex/)

### What to Steal for Athanor

- **Persistent status strip** (already partially implemented as "System Pulse Strip")
- **Subsystem pages with dedicated views** (already have 16 pages -- this is the right pattern)
- **Minimalism as philosophy, not style** -- every element must earn its screen space
- **Digital twin concept** -- a visual representation of the cluster topology showing nodes, GPUs, services, and their relationships in real time

---

## 2. Smart Home Dashboards: Single-Operator Efficiency

### Home Assistant (2026.2)

Home Assistant's 2026.2 release made the Home Dashboard the default for new installations. Key UX improvements:

- **Prominent controls at the forefront** instead of buried in menus
- **Area-based organization** with functional automations, climate controls, and energy reporting per area
- **Entity-level control selection** -- you choose exactly which entities appear in area cards, not just entire types
- **Sections layout** as the default for simplicity

Source: [Home Assistant 2026.2 Release](https://www.home-assistant.io/blog/2026/02/04/release-20262), [XDA - HA February Update](https://www.xda-developers.com/home-assistant-february-update-2026/)

### Design Patterns

**Mushroom cards** with dark themes have become the de facto standard for premium HA dashboards. They use:
- Rounded, minimal cards
- Consistent icon language
- State-dependent coloring (device on = accent color, off = muted)
- Tap to toggle, long-press for details

**Floor plan dashboards** show an interactive floorplan with devices highlighted when active. Tap controls toggle devices directly. This spatial mapping is effective when the mental model is physical space.

**Widget-based layouts** (as opposed to list-based) allow repositioning and prioritization by the user.

Source: [Seeed Studio - HA Dashboard Ideas](https://www.seeedstudio.com/blog/2026/01/09/best-home-assistant-dashboards/), [SmartHomeScene - HA Themes](https://smarthomescene.com/blog/best-home-assistant-dashboard-themes-in-2023/)

### What to Steal for Athanor

- **Area/zone-based organization** maps well to node-based organization (Foundry, Workshop, VAULT, DEV)
- **Prominent controls** -- the dashboard should let you DO things (restart services, trigger agents, pause tasks), not just watch
- **State-dependent styling** -- items change visual treatment based on their current state (idle, working, error, sleeping)
- **Tap for action, drill-down for detail** -- progressive disclosure through interaction

---

## 3. NOC Design: The Art of "Everything Is Fine"

### Core Patterns

**Traffic-light severity model.** NOCs universally use green/yellow/amber/red color coding for severity. The key insight: **avoid keeping red on screen for extended periods** -- it desensitizes operators. Use alerts for non-urgent issues, reserve red for genuine emergencies.

**Hierarchical incident management.** Incidents are categorized by type and severity, with escalation chains (L1/L2/L3). For a single operator, this translates to priority tiers: what you must act on now, what you should know about, and what you can ignore.

**Central video wall principle.** In NOCs, a central display shows the big picture while individual workstations show detail. For a single operator, this translates to the home/overview page being the "video wall" -- always showing aggregate health -- with drill-down pages as the "workstations."

Source: [AlertOps - NOC Dashboard Examples](https://alertops.com/noc-dashboard-examples/), [Splunk - What is a NOC](https://www.splunk.com/en_us/blog/learn/noc-network-operations-center.html), [ExtNOC - NOC Design](https://www.extnoc.com/network-operations-center/noc-design-and-layout/)

### Grafana's Design Philosophy

Grafana's official best practices document codifies several principles worth adopting:

**1. RED method layout.** Request rate and error rate on the left, latency/duration on the right. One row per service. Row order reflects data flow. This gives you an at-a-glance service health view.

**2. Tell a story.** Every dashboard should answer a specific question. Create a logical progression from general to specific, large to small.

**3. Hierarchical drill-down.** Start with "is everything okay?" and progressively reveal more detail. High-level dashboards link to low-level dashboards. Low-level dashboards link to log queries and debugging tools.

**4. Template variables.** One parameterized dashboard serves multiple instances instead of duplicating dashboards per node/service.

**5. Minimize cognitive load.** "Cognitive load is basically how hard you need to think about something." Dashboards must be immediately interpretable. Normalize axes. Use consistent panel sizes. Consistent naming conventions.

**6. Text panels for context.** Include brief descriptions of what the dashboard shows and why. Panel descriptions visible on hover add context without cluttering.

Source: [Grafana - Dashboard Best Practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/)

### Datadog's Approach

Datadog prioritizes speed-to-value with out-of-the-box dashboards and a large integrations catalog. Their design philosophy centers on unified search and predefined dashboards that "just work." For Athanor, this means: the default dashboard should show something useful with zero configuration.

Source: [SigNoz - Datadog vs Grafana](https://signoz.io/blog/datadog-vs-grafana/)

### What to Steal for Athanor

- **The "is everything okay?" question** as the primary design goal of the home page
- **Traffic-light severity** but used sparingly -- green dots for healthy, absence of indicator for normal, colored indicators only when attention is needed
- **Hierarchical drill-down** from overview to detail pages
- **Row-per-service layout** for the services page using RED-style metrics
- **Template variables** for parameterized views (select a node, select an agent, select a time range)

---

## 4. Gaming HUDs: Real-Time Density Without Overwhelm

### Strategy Game Patterns

**Widget-based peripheral UI.** Strategy game UI has evolved from simple bars to widgets that stick out around the screen edges. This is the modern standard because widgets scale independently -- you can add, remove, or resize them without redesigning the layout.

Source: [Medium - Strategy Game Battle UI](https://medium.com/@treeform/strategy-game-battle-ui-3024ce6362d0)

**Stellaris notification system.** Stellaris uses two notification types:
- **Square alerts** -- persistent, remain until the circumstance changes (like a service being down)
- **Round alerts** -- transient, disappear after brief display (like a completed task)
- **Urgency color coding** for priority

Additionally, Stellaris relies heavily on **tooltips** for progressive disclosure. Hovering over any element reveals deeper information. This keeps the primary UI clean while making detail available instantly.

Source: [Stellaris Wiki - Main Interface](https://stellaris.paradoxwikis.com/Main_interface), [Interface In Game - Stellaris](https://interfaceingame.com/games/stellaris/)

**Factorio's 120-window problem.** Factorio has approximately 120 distinct UI windows, making it one of the most information-dense games ever made. Their design philosophy:
- **Functional over decorative.** Neutral, sober look that helps focus on relevant elements without distracting decorations.
- **Content over controls.** Maximize space for primary content by minimizing secondary interface elements.
- **Flexible scaling.** Windows adapt to content volume rather than maintaining fixed dimensions. A window with 3 items looks different from one with 20.
- **Horizontal space usage.** Modern 16:9+ screens have more horizontal space than vertical. Layouts should exploit width, not force vertical scrolling.
- **Respect the existing mental model.** Changes are made only when clearly beneficial, not for the sake of change.

Source: [Factorio FFF #212 - GUI Update Part 1](https://www.factorio.com/blog/post/fff-212), [Factorio FFF #238 - GUI Update Part 2](https://factorio.com/blog/post/fff-238), [Alt-F4 #17 - Interface Design Philosophy](https://alt-f4.blog/cs/ALTF4-17/)

**Satisfactory's missing dashboard.** Notably, Satisfactory does NOT have a centralized production dashboard, and its absence is one of the most requested features. Players must physically visit machines to check status. This is a cautionary tale: when you have many systems to monitor, a centralized overview is not optional -- it is the most-demanded feature.

Source: [Satisfactory Q&A - Production Dashboard Request](https://questions.satisfactorygame.com/post/6088475daa0ba107e325b58a)

### General HUD Principles

- **Context-sensitive highlighting.** Show different information based on what is happening NOW, not what might be relevant.
- **Consistent visual language.** Uniform patterns make behavior predictable, reducing learning curve.
- **Non-diegetic UI for tactical decisions.** In strategy games, the UI exists outside the game world but is essential for decision-making. Similarly, the Athanor dashboard is a meta-layer over the system, not part of any individual service.

Source: [Medium - UX and UI in Game Design](https://medium.com/@brdelfino.work/ux-and-ui-in-game-design-exploring-hud-inventory-and-menus-5d8c189deb65), [Toptal - Game UI Guide](https://www.toptal.com/designers/ui/game-ui)

### What to Steal for Athanor

- **Widget-based layout** that can be extended without redesigning
- **Persistent vs transient notifications** (Stellaris pattern)
- **Tooltip-based progressive disclosure** -- hover for detail, click for full view
- **Content-first, controls-minimized** (Factorio philosophy)
- **Horizontal layout exploitation** for widescreen monitors
- **Centralized overview as the core feature** (Satisfactory's lesson)

---

## 5. Adaptive and Contextual Dashboards

### Current State of the Art (2025-2026)

**Context-aware interfaces** are the dominant trend in 2026 dashboard design. Products now dynamically adjust content, layout, tone, and functionality based on:
- What the user is trying to do
- What device they are using
- What is happening in the system right now
- Historical usage patterns

Source: [DEV.to - UI/UX Trends 2026](https://dev.to/pixel_mosaic/top-uiux-design-trends-for-2026-ai-first-context-aware-interfaces-spatial-experiences-166j)

**AI-enhanced adaptive dashboards** dynamically reconfigure views, KPIs, and alerts based on usage patterns, behavioral history, or cognitive load thresholds. This is the "calm design" movement -- interfaces that avoid burning attention on things that do not matter.

Source: [Orizon - UI/UX Trends 2026](https://www.orizon.co/blog/10-ui-ux-trends-that-will-shape-2026)

### Adaptive Patterns for Athanor

**Mode-based views.** The dashboard should have implicit or explicit modes:

| System State | Dashboard Behavior |
|---|---|
| Everything healthy, no activity | Calm overview -- minimal info, ambient display quality |
| Agent is executing a task | Task progress surfaces automatically, agent thought log visible |
| Service is down | Alert surfaces immediately, affected services highlighted, rest dims |
| Media is streaming | Now-playing card appears with session details |
| Creative generation in progress | ComfyUI progress appears with preview |
| High GPU utilization | GPU cards expand with detail, utilization sparklines |
| Idle GPUs | GPU cards show "sleeping" or "available" with suggestion to allocate |

**Attention-based priority.** Instead of showing everything always, surface what matters:
1. **Errors and alerts** always on top
2. **Active tasks** (agents working, media streaming, generation running)
3. **System health summary** (only if something deviates from normal)
4. **Historical/ambient data** (recent activity, statistics)

**Generative UI.** The most forward-looking trend is AI-generated interfaces -- the agent system itself could compose dashboard views based on what it thinks the operator needs to see. This is aspirational for Athanor but worth keeping in mind architecturally.

Source: [Fuselab Creative - UI Design for AI Agents](https://fuselabcreative.com/ui-design-for-ai-agents/)

### What to Steal for Athanor

- **State-driven layout changes** -- the dashboard shows different information based on what is happening
- **Calm-by-default** -- when nothing needs attention, the dashboard should be ambient, not noisy
- **Progressive escalation** -- problems surface gradually (subtle indicator -> prominent card -> full alert)
- **Agent transparency** -- when agents are working, show what they are doing and why

---

## 6. Information Hierarchy and Progressive Disclosure

### The Three-Layer Model

For a system with 4 nodes, 7 GPUs, 8 agents, 26+ services, multiple projects:

**Layer 1: Pulse Strip (always visible)**
A persistent strip (already implemented partially) showing:
- GPU utilization bars (7 mini-bars, color-coded)
- VRAM usage (aggregate)
- Nodes online (count)
- Services health (count + any alerts)
- Agents online (count + any active tasks)
- Power draw (aggregate)

This strip should be visible on EVERY page, not just the home page. It is the constant heartbeat of the system.

**Layer 2: Zone Cards (home page)**
Expandable cards organized by domain:
- **Compute** -- GPU map, inference status, model allocation
- **Agents** -- Active/idle agents, current tasks, recent completions
- **Media** -- Now playing, download queue, library stats
- **Services** -- Health grid, any alerts
- **Creative** -- ComfyUI status, recent generations
- **Home** -- HA entity summary, active automations

Each card shows a 2-3 line summary when collapsed, expanding to show detail.

**Layer 3: Dedicated Pages (drill-down)**
Full pages for each domain with complete detail, controls, and history. The existing 16 pages map to this layer.

### Progressive Disclosure Patterns

**Overview -> Detail -> Action** is the standard flow:
1. See aggregate health on home page
2. Notice something interesting/wrong
3. Click to expand or navigate to detail page
4. Take action (restart, trigger, configure)

**Tooltip depth.** Follow Stellaris: hover to see a summary tooltip, click to navigate to the full view. This adds a zero-click information layer.

**Expand-in-place.** Cards that expand within the grid layout (not navigating away) for medium-depth information. Good for checking on an agent's current task without leaving the overview.

Source: [IxDF - Progressive Disclosure](https://www.interaction-design.org/literature/topics/progressive-disclosure), [UXPin - Dashboard Design Principles](https://www.uxpin.com/studio/blog/dashboard-design-principles/), [Lollypop Design - Progressive Disclosure in SaaS](https://lollypop.design/blog/2025/may/progressive-disclosure/)

---

## 7. Real-Time Data: SSE Over WebSockets

### The Recommendation: Server-Sent Events (SSE)

For the Athanor dashboard, **SSE is the better choice** over WebSockets for most data flows:

| Factor | SSE | WebSocket |
|---|---|---|
| Direction | Server-to-client (one-way) | Bidirectional |
| Protocol | Standard HTTP | Custom protocol over TCP |
| Reconnection | Built-in automatic | Manual implementation |
| Firewall compatibility | Works everywhere | May be blocked |
| Complexity | Simple | Complex |
| Browser support | Universal (EventSource API) | Universal |
| Best for | Status updates, metrics, alerts | Chat, interactive controls |

The dashboard is primarily a **read surface** -- it displays system state. The few interactive features (triggering agents, restarting services) can use standard HTTP POST requests. SSE handles the continuous status stream.

Source: [HackerNoon - Streaming in Next.js 15](https://hackernoon.com/streaming-in-nextjs-15-websockets-vs-server-sent-events), [Pedro Alonso - SSE in Next.js](https://www.pedroalonso.net/blog/sse-nextjs-real-time-notifications/)

### SSE in Next.js App Router

Next.js 15/16 has clean SSE support using the `ReadableStream` API in API routes:

```typescript
// app/api/status/stream/route.ts
export async function GET() {
  const stream = new ReadableStream({
    start(controller) {
      const interval = setInterval(async () => {
        const status = await getSystemStatus();
        controller.enqueue(`data: ${JSON.stringify(status)}\n\n`);
      }, 5000);

      // Cleanup on close
      return () => clearInterval(interval);
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

Client-side consumption:

```typescript
// hooks/useSystemStatus.ts
function useSystemStatus() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const source = new EventSource('/api/status/stream');
    source.onmessage = (e) => setStatus(JSON.parse(e.data));
    source.onerror = () => {
      source.close();
      // EventSource auto-reconnects, but we can add backoff
    };
    return () => source.close();
  }, []);

  return status;
}
```

### Performance Optimization

- **Throttle updates** to 1-5 second intervals for most metrics (GPU util, service health)
- **Batch updates** -- collect 100-200ms of events then flush as one payload
- **Snapshot + delta** -- send full state periodically, small diffs between
- **Coalesce** -- multiple metric changes in one update instead of separate messages

Source: [Johal.in - Real-Time Dashboards](https://johal.in/real-time-dashboards-with-next-js-python-websockets-for-live-data-updates-2025/)

### When to Use WebSockets

Reserve WebSockets for:
- **Chat interface** (already handled by Open WebUI)
- **Interactive agent control** if we want real-time bidirectional communication with running agents
- **ComfyUI progress** (ComfyUI already uses WebSocket for generation progress)

### Current State

The existing dashboard uses `revalidate = 15` (Next.js ISR with 15-second revalidation). This means data is 0-15 seconds stale. Moving to SSE would make it genuinely real-time (sub-second) for the status stream while keeping SSR/ISR for initial page loads.

---

## 8. Dark/Ambient UI Design

### The Existing Design Language

From VISION.md: "Dark, minimal, clean. Cormorant Garamond, subtle warmth, no clutter."

Current implementation uses shadcn/ui defaults with dark mode. This is a good foundation but can be elevated.

### What Makes Dark UI Feel Premium vs Just Dark

**1. Never use pure black.** Use dark gray (`#0a0a0a` to `#1a1a1a`) as the base. Pure black (#000000) creates harsh contrast and looks flat. Google Material Design recommends `#121212` as the dark surface color.

**2. Elevation through luminance, not shadow.** In dark mode, higher surfaces should be *lighter*, not darker with shadows. A card at elevation 1 might be `#1a1a1a`, while elevation 2 is `#222222`. Shadows are invisible against dark backgrounds -- luminance is how depth works in dark mode.

**3. Desaturated accent colors.** Vibrant saturated colors on dark backgrounds create visual fatigue and can fail accessibility contrast checks. Desaturate brand colors for dark mode use. For the warm amber accent (`#d4a574`), a slightly desaturated variant works better on dark surfaces.

**4. Light gray text, not white.** Use `rgba(255,255,255,0.87)` or approximately `#dedede` for primary text. Pure white (#ffffff) on dark gray creates excessive contrast and eye strain. Secondary text at `rgba(255,255,255,0.60)` and disabled text at `rgba(255,255,255,0.38)`.

**5. Subtle colored tints in backgrounds.** Adding a hint of dark blue or warm brown to black/gray backgrounds prevents the "dead screen" look and adds subtle warmth. For Athanor's warm aesthetic: a barely-perceptible warm tint to grays.

**6. Data visualization on dark backgrounds.** Use mostly muted/gray data points with one or two strongly colored accents to direct attention. Colorful elements should be the exception, not the norm. This is the SpaceX approach applied to charts.

**7. Glassmorphism for layered elements.** Semi-transparent backgrounds with `backdrop-filter: blur()` create depth and context. Effective for modals, tooltips, and overlay panels. Opacity between 10-40%, blur radius 10-20px.

**8. Typography weight adjustment.** Use semi-bold or medium weights rather than thin/light weights, which fade against dark backgrounds. Cormorant Garamond for headings should use weight 500-600 in dark mode, not 300-400.

Source: [Wendy Zhou - Dark Dashboard UI Design](https://www.wendyzhou.se/blog/dark-dashboard-ui-design-inspiration/), [Medium - Color Tokens for Dark Mode](https://medium.com/design-bootcamp/color-tokens-guide-to-light-and-dark-modes-in-design-systems-146ab33023ac), [EightShapes - Light & Dark Color Modes](https://medium.com/eightshapes-llc/light-dark-9f8ea42c9081)

### Recommended Color Token System

```
// Backgrounds (luminance-based elevation)
--bg-base:       hsl(20, 5%, 4%)     // ~#0b0a09 - deepest background
--bg-surface:    hsl(20, 4%, 7%)     // ~#131210 - card surface
--bg-elevated:   hsl(20, 3%, 11%)    // ~#1c1b19 - elevated cards, modals
--bg-hover:      hsl(20, 3%, 14%)    // ~#242320 - hover states

// Warm amber accent (the Athanor signature)
--accent:        hsl(28, 45%, 64%)   // ~#d4a574 - primary accent
--accent-muted:  hsl(28, 30%, 50%)   // muted variant for less emphasis
--accent-subtle: hsl(28, 20%, 15%)   // subtle background tint

// Text hierarchy
--text-primary:  hsl(0, 0%, 87%)     // ~#dedede
--text-secondary: hsl(0, 0%, 60%)    // ~#999999
--text-muted:    hsl(0, 0%, 38%)     // ~#616161

// Status colors (desaturated for dark mode)
--status-ok:     hsl(142, 50%, 50%)  // green, only when status matters
--status-warn:   hsl(38, 80%, 55%)   // amber warning
--status-error:  hsl(0, 65%, 55%)    // red error
--status-info:   hsl(210, 50%, 55%)  // blue informational

// Borders
--border:        hsl(20, 3%, 15%)    // subtle borders
--border-active: hsl(28, 45%, 40%)   // active/focused borders
```

### The Ambient Quality

The dashboard should feel like a well-designed instrument panel, not a web app. When everything is healthy and nothing needs attention, it should be almost ambient -- pleasant to glance at, not demanding attention. Think of it as the difference between a car's instrument cluster (always readable, not distracting) and a slot machine (screaming for attention).

---

## 9. Notification and Alert Systems

### The Notification Fatigue Problem

The single greatest risk in a monitoring dashboard is notification fatigue. When everything generates alerts, nothing gets attention. The goal is an alert system where every notification that surfaces genuinely needs the operator's attention.

### Carbon Design System Notification Framework

IBM's Carbon Design System provides the most well-thought-out notification taxonomy:

| Type | Behavior | Use Case |
|---|---|---|
| **Inline** | Appears near related content, optionally dismissible | Validation errors, contextual warnings |
| **Toast** | Slides in top-right, auto-dismisses after 5s | Task completions, status changes |
| **Banner** | Top of interface, persists until dismissed | System-wide announcements, maintenance |
| **Modal** | Interrupts current task, requires action | Critical errors, destructive confirmations |
| **Notification center** | Collected in a panel, reviewed on demand | History, non-urgent updates |

**Urgency-to-style mapping:**
- **High-contrast style** for urgent/critical notifications (red/orange backgrounds)
- **Low-contrast style** for informational/supplemental notifications (subtle borders)

Source: [Carbon Design System - Notification Pattern](https://carbondesignsystem.com/patterns/notification-pattern/)

### Priority-Based Alerting for Athanor

**P0 - Critical (Modal or Banner)**
- Node offline
- All GPUs in a pool unavailable
- VAULT storage > 95%
- Agent framework crashed

**P1 - Warning (Toast with persistence)**
- Service down (individual)
- GPU temperature > 85C
- vLLM model unloaded unexpectedly
- NFS stale handle detected
- Agent task failed after retries

**P2 - Informational (Toast, auto-dismiss)**
- Agent task completed
- Media download finished
- Creative generation complete
- Scheduled backup complete

**P3 - Ambient (Notification center only)**
- Agent heartbeat summary
- Library statistics update
- Dashboard version update available

### Acknowledge Workflow

For P0 and P1 alerts:
1. Alert appears with timestamp
2. Operator acknowledges (click/dismiss) -- logged with timestamp
3. If not acknowledged within threshold, alert escalates (changes visual treatment, appears in more prominent location)
4. Resolution logged when condition clears

For Athanor (single operator), the "escalation" is visual: an unacknowledged P0 grows from a toast to a persistent banner to an overlay that demands attention.

### Implementation Pattern

```typescript
interface Notification {
  id: string;
  priority: 0 | 1 | 2 | 3;
  title: string;
  detail?: string;
  source: string;         // "gpu-monitor", "agent-framework", "service-check"
  timestamp: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  actions?: { label: string; handler: string }[];
}
```

Source: [OneUptime - Alert Priority Levels](https://oneuptime.com/blog/post/2026-01-30-alert-priority-levels/view), [DigitalOcean - Monitoring and Alerting](https://www.digitalocean.com/community/tutorials/putting-monitoring-and-alerting-into-practice), [Grafana - Alerting Best Practices](https://grafana.com/docs/grafana/latest/alerting/guides/best-practices/)

---

## 10. Dashboard Frameworks: Staying with shadcn/ui + Tremor

### Framework Comparison

| Framework | Chart Support | Dark Theme | Customization | Bundle Size | Maturity | Best For |
|---|---|---|---|---|---|---|
| **shadcn/ui** | Via Recharts (built-in charts component) | Native, excellent | Full (source owned) | Zero runtime | High | General UI + some charts |
| **Tremor** | 30+ chart types, KPI cards, sparklines | Native | Full (Tailwind) | Small (tree-shakes) | High | Data dashboards |
| **Radix UI** | None (primitives only) | Themeable | Full | Tiny | High | Accessible primitives |
| **NextUI** | None | Native | Good | Sub-40KB gzip | Medium | General UI |
| **MUI** | Via MUI X Charts | Good | Limited by system | Large | Very High | Enterprise apps |
| **Ant Design** | Via AntV/G2 | Good | Moderate | Large | Very High | Enterprise apps |

Source: [Makers Den - React UI Libraries 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra), [Untitled UI - React Component Libraries 2026](https://www.untitledui.com/blog/react-component-libraries), [DesignRevision - Best React Component Libraries 2026](https://designrevision.com/blog/best-react-component-libraries)

### Recommendation: shadcn/ui + shadcn Charts + Tremor Components

The current stack (shadcn/ui + Radix + Tailwind) is correct. For the command center evolution, add:

**1. shadcn/ui Charts (built on Recharts).** Shadcn recently introduced chart components. They integrate with the shadcn theming system, so dark mode works automatically. Install via `npx shadcn@latest add chart`. Chart types: area, bar, line, pie, radar. These handle most standard visualization needs.

Source: [shadcn/ui Charts](https://ui.shadcn.com/charts/area), [shadcn.io - React Charts](https://www.shadcn.io/charts)

**2. Tremor for dashboard-specific components.** Tremor is built on Recharts + Radix (the same primitives as shadcn/ui), making it compatible with the existing stack. It adds:
- **KPI cards** with delta indicators and progress bars
- **Sparklines** for inline trend visualization
- **Area/bar/donut charts** with dashboard-optimized defaults
- **Filter controls** for parameterized views
- **30+ copy-paste components** designed for analytics dashboards

Tremor is NOT a replacement for shadcn/ui. It is a complement that adds dashboard-specific components. Both use Tailwind and Radix, so they compose naturally.

Source: [Tremor](https://www.tremor.so/), [Refine - Building with Tremor](https://refine.dev/blog/building-react-admin-dashboard-with-tremor/)

**3. Consider for specific needs:**
- **D3.js** -- only if you need custom visualizations that Recharts cannot handle (network topology graph, custom GPU heatmap)
- **Framer Motion** -- for tasteful animation of state transitions (card expand/collapse, alert entry/exit)
- **react-use-websocket** -- for the few bidirectional needs (ComfyUI progress, interactive agent control)

### What NOT to Add

- **MUI/Ant Design** -- enterprise frameworks that would conflict with the existing Tailwind-first approach
- **Victory** -- unnecessary when Recharts is already in the stack via shadcn/Tremor
- **Plotly** -- overkill for dashboard charts, heavy bundle, wrong aesthetic
- **Apache ECharts** -- powerful but complex API, poor Tailwind integration

---

## 11. AI Agent Dashboard Patterns (New Domain, 2025-2026)

This is an emerging design space directly relevant to Athanor's 8-agent system.

### Mission Control for Agents

The emerging pattern for agent management UIs is "mission control-style interfaces" -- not traditional CRUD admin panels but live status feeds with drill-down capability. Key components:

**Agent Status Board.** Shows each agent with:
- Current state (idle, working, waiting, error)
- Current task (if any) with progress
- Last activity timestamp
- Resource consumption (tokens used, API calls)
- Performance metrics (task completion rate, average duration)

**Thought Log / Reasoning Trace.** A visible log of why the agent chose a particular action. This is the transparency layer that builds operator trust. Without it, autonomous agents are a black box.

**Override Controls.** Cancel, pause, redirect, or modify agent behavior. "While autonomy is beneficial, users must always feel they have the final say." This means:
- Cancel button on running tasks
- Pause/resume for long-running agents
- Edit agent output before it takes effect
- Manual task assignment to specific agents

Source: [Fuselab Creative - AI Agent UI Design](https://fuselabcreative.com/ui-design-for-ai-agents/), [Verdent - Ralph TUI](https://www.verdent.ai/guides/ralph-tui-ai-agent-dashboard)

### Ralph TUI: Lessons from a Production Agent Dashboard

Ralph TUI is a terminal-based mission control dashboard for AI agents. Its creator states: "Running autonomous AI agents without a dashboard isn't engineering; it's gambling." Key design decisions:

**1. Visibility prevents waste.** Real-time task execution display prevents the "black box problem" where you cannot tell if agents are reasoning productively or burning API credits in loops.

**2. Bounded iteration.** First runs of any task are bounded (e.g., max 5 iterations). This "cage before freedom" approach prevents runaway loops. Only after validation are limits removed.

**3. Stuck detection.** The dashboard tracks how long an agent has been on the same step. If > 5 minutes, it flags the agent as potentially stuck.

**4. Cost tracking.** Per-task cost tracking enables optimization -- you can see which tasks are expensive and why.

**5. State persistence.** Session state persists to disk, enabling recovery after crashes. Agents remember their execution point.

Source: [Verdent - Ralph TUI](https://www.verdent.ai/guides/ralph-tui-ai-agent-dashboard)

### ServiceNow AI Control Tower

ServiceNow launched an "AI Control Tower" in 2025 -- a centralized command center to govern, manage, secure, and realize value from any AI agent. While enterprise-scale, the concept of a single pane of glass for all agent operations is exactly what Athanor needs.

Source: [ServiceNow - AI Control Tower](https://www.servicenow.com/company/media/press-room/ai-control-tower-knowledge-25.html)

---

## Synthesized Design Principles for Athanor

Drawing from all 10 research vectors, here are the core design principles for the command center:

### Principle 1: Calm by Default, Urgent When Needed

The dashboard should be ambient when healthy. Like a well-designed car instrument panel -- readable at a glance, not demanding attention. When something needs attention, it should surface progressively: subtle indicator -> prominent card -> persistent alert -> modal interruption.

### Principle 2: Three Layers of Depth

Every piece of information exists at one of three layers:
1. **Pulse Strip** -- always visible, aggregate health, the answer to "is everything okay?"
2. **Domain Cards** -- expandable summaries on the home page
3. **Detail Pages** -- full information and controls per domain

### Principle 3: State-Driven, Not Static

The dashboard changes based on system state. When agents are working, the agent section expands. When media is streaming, the media section surfaces. When everything is idle, the dashboard is minimal. This is not animation for its own sake -- it is information architecture that responds to reality.

### Principle 4: Actions, Not Just Monitoring

Every domain card should offer at minimum one action:
- **GPU**: Sleep/wake model
- **Agents**: Trigger task, cancel task, view thought log
- **Media**: Request download, search library
- **Services**: Restart service
- **Creative**: Generate image/video
- **Home**: Toggle device, trigger automation

### Principle 5: Agent Transparency

When agents are autonomous, the operator needs to trust them. This requires:
- Visible thought process (reasoning trace)
- Visible resource consumption (tokens, time)
- Easy override (cancel, pause, redirect)
- Clear escalation (when does the agent ask for help?)

### Principle 6: Information Density Through Typography and Space

Do NOT reduce information density by removing information. Increase it through:
- Tabular mono-spaced data for metrics (easy scanning)
- Cormorant Garamond for section headings (hierarchy)
- Inter/system sans-serif for data (readability)
- Consistent spacing that creates scannable rhythm
- Color used sparingly and meaningfully (status only, not decoration)

### Principle 7: Dark and Warm

The aesthetic is not "dark mode applied to a light design." It is dark-first:
- Dark warm grays for backgrounds (not pure black)
- Luminance-based elevation (lighter = higher)
- Desaturated status colors
- Warm amber accent for brand identity
- Light gray text (not pure white)
- Semi-bold typography (not thin weights)

---

## Specific Implementation Recommendations

### Phase 1: Foundation (immediate)

1. **Install shadcn Charts** -- `npx shadcn@latest add chart`
2. **Add Tremor** -- `npm install @tremor/react` for KPI cards, sparklines, and dashboard-specific components
3. **Implement SSE endpoint** -- `/api/status/stream` that pushes system state every 5 seconds
4. **Create `useSystemStatus` hook** -- client-side EventSource consumer
5. **Make Pulse Strip persistent** -- move from home page only to layout (visible on all pages)
6. **Implement notification system** -- priority-based toasts with notification center

### Phase 2: Interactivity (next sprint)

1. **Add action buttons to domain cards** -- trigger agents, restart services, sleep/wake models
2. **Agent status board** -- real-time view of all 8 agents with state, current task, last activity
3. **Expand-in-place cards** -- click to expand domain cards for medium-depth information without navigation
4. **Tooltip layer** -- hover over any metric for contextual detail

### Phase 3: Intelligence (future)

1. **State-driven layout** -- dashboard adapts based on system state
2. **Agent thought logs** -- visible reasoning trace for autonomous tasks
3. **Anomaly surfacing** -- highlight deviations from normal patterns
4. **Keyboard navigation** -- `Cmd+K` command palette for quick actions across the entire system

### Technical Architecture

```
Browser
  |
  +-- Layout (persistent)
  |     +-- Pulse Strip (SSE-driven, always visible)
  |     +-- Sidebar Nav (16 pages)
  |     +-- Notification Toasts (priority-based)
  |
  +-- Home Page (SSE-driven)
  |     +-- Compute Zone (GPUs, inference, models)
  |     +-- Agent Zone (status, tasks, activity)
  |     +-- Media Zone (now playing, downloads, library)
  |     +-- Services Zone (health grid, alerts)
  |     +-- Creative Zone (ComfyUI, generations)
  |     +-- Home Zone (HA entities, automations)
  |
  +-- Detail Pages (SSR + SSE for live data)
        +-- /gpu -- full GPU metrics, history, controls
        +-- /agents -- agent board, task queue, thought logs
        +-- /services -- service grid, logs, restart controls
        +-- /media -- library browser, download manager
        +-- /chat -- agent chat interface
        +-- /gallery -- creative generations
        +-- /monitoring -- Prometheus metrics deep dive
        +-- etc.
```

---

## Sources

### SpaceX Mission Control
- [HN Discussion - SpaceX Dragon Tech Stack](https://news.ycombinator.com/item?id=23404310)
- [InfoQ - JavaScript in Space](https://www.infoq.com/news/2020/06/javascript-spacex-dragon/)
- [Shane Mielke - Crew Dragon Displays](https://shanemielke.com/work/spacex/crew-dragon-displays/)
- [Dillon Baird - Recreating SpaceX Dragon UI](https://dillonbaird.io/articles/mutantdragon/)
- [Dillon Baird - Bringing Outer Space UI Down to Earth](https://dillonbaird.io/blog/makingmutantdragon/)
- [Black Label - Dataviz at SpaceX](https://blacklabel.net/blog/data-visualization/dataviz-in-action/dataviz-at-spacex/)
- [UX Collective - Recreating Crew Dragon UI](https://uxdesign.cc/how-i-recreated-crew-dragons-ui-15877eddf3ed)
- [Lithios - SpaceX Dragon Capsule](https://www.lithiosapps.com/blog/a-look-under-the-hood-of-spacexs-dragon-capsule)

### Smart Home Dashboards
- [Home Assistant 2026.2 Release](https://www.home-assistant.io/blog/2026/02/04/release-20262)
- [Home Assistant Dashboards Documentation](https://www.home-assistant.io/dashboards/)
- [Seeed Studio - HA Dashboard Ideas](https://www.seeedstudio.com/blog/2026/01/09/best-home-assistant-dashboards/)
- [XDA - Home Assistant February 2026 Update](https://www.xda-developers.com/home-assistant-february-update-2026/)
- [SmartHomeScene - HA Dashboard Themes](https://smarthomescene.com/blog/best-home-assistant-dashboard-themes-in-2023/)
- [HomeShift - HA Dashboard Examples](https://joinhomeshift.com/home-assistant-dashboard-examples)

### NOC and Monitoring
- [AlertOps - NOC Dashboard Examples](https://alertops.com/noc-dashboard-examples/)
- [Splunk - What is a NOC](https://www.splunk.com/en_us/blog/learn/noc-network-operations-center.html)
- [ExtNOC - NOC Design and Layout](https://www.extnoc.com/network-operations-center/noc-design-and-layout/)
- [Grafana - Dashboard Best Practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/)
- [SigNoz - Datadog vs Grafana](https://signoz.io/blog/datadog-vs-grafana/)
- [Pragmatic SRE - Alerts & Dashboards](https://www.pragmaticsre.com/psre-guide/3-operational-excellence/alerts-dashboards)

### Gaming HUD Design
- [Factorio FFF #212 - GUI Update Part 1](https://www.factorio.com/blog/post/fff-212)
- [Factorio FFF #238 - GUI Update Part 2](https://factorio.com/blog/post/fff-238)
- [Alt-F4 #17 - Interface Design Philosophy](https://alt-f4.blog/cs/ALTF4-17/)
- [Stellaris Wiki - Main Interface](https://stellaris.paradoxwikis.com/Main_interface)
- [Interface In Game - Stellaris](https://interfaceingame.com/games/stellaris/)
- [Game UI Database](https://www.gameuidatabase.com/)
- [Toptal - Game UI Guide](https://www.toptal.com/designers/ui/game-ui)
- [Medium - Strategy Game Battle UI](https://medium.com/@treeform/strategy-game-battle-ui-3024ce6362d0)
- [Satisfactory Q&A - Production Dashboard Request](https://questions.satisfactorygame.com/post/6088475daa0ba107e325b58a)

### Adaptive and Contextual Design
- [DEV.to - UI/UX Trends 2026](https://dev.to/pixel_mosaic/top-uiux-design-trends-for-2026-ai-first-context-aware-interfaces-spatial-experiences-166j)
- [Orizon - UI/UX Trends 2026](https://www.orizon.co/blog/10-ui-ux-trends-that-will-shape-2026)
- [UXPin - Dashboard Design Principles](https://www.uxpin.com/studio/blog/dashboard-design-principles/)
- [F1Studioz - Smart SaaS Dashboard Design 2026](https://f1studioz.com/blog/smart-saas-dashboard-design/)

### Progressive Disclosure
- [IxDF - Progressive Disclosure](https://www.interaction-design.org/literature/topics/progressive-disclosure)
- [Lollypop Design - Progressive Disclosure in SaaS](https://lollypop.design/blog/2025/may/progressive-disclosure/)

### Dark UI Design
- [Wendy Zhou - Dark Dashboard UI Design Inspiration](https://www.wendyzhou.se/blog/dark-dashboard-ui-design-inspiration/)
- [Medium - Color Tokens for Dark Mode](https://medium.com/design-bootcamp/color-tokens-guide-to-light-and-dark-modes-in-design-systems-146ab33023ac)
- [EightShapes - Light & Dark Color Modes](https://medium.com/eightshapes-llc/light-dark-9f8ea42c9081)
- [Toptal - Dark UI Design Principles](https://www.toptal.com/designers/ui/dark-ui-design)
- [Dribbble - Dark Theme Dashboard](https://dribbble.com/tags/dark-theme-dashboard)

### Real-Time Data
- [HackerNoon - Streaming in Next.js 15](https://hackernoon.com/streaming-in-nextjs-15-websockets-vs-server-sent-events)
- [Pedro Alonso - SSE in Next.js](https://www.pedroalonso.net/blog/sse-nextjs-real-time-notifications/)
- [Johal.in - Real-Time Dashboards with Next.js](https://johal.in/real-time-dashboards-with-next-js-python-websockets-for-live-data-updates-2025/)
- [PortalZINE - SSE's Comeback in 2025](https://portalzine.de/sses-glorious-comeback-why-2025-is-the-year-of-server-sent-events/)

### Notification Systems
- [Carbon Design System - Notification Pattern](https://carbondesignsystem.com/patterns/notification-pattern/)
- [OneUptime - Alert Priority Levels](https://oneuptime.com/blog/post/2026-01-30-alert-priority-levels/view)
- [DigitalOcean - Monitoring and Alerting](https://www.digitalocean.com/community/tutorials/putting-monitoring-and-alerting-into-practice)
- [Grafana - Alerting Best Practices](https://grafana.com/docs/grafana/latest/alerting/guides/best-practices/)

### Dashboard Frameworks
- [shadcn/ui Charts](https://ui.shadcn.com/charts/area)
- [Tremor](https://www.tremor.so/)
- [Makers Den - React UI Libraries 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra)
- [Untitled UI - React Component Libraries 2026](https://www.untitledui.com/blog/react-component-libraries)
- [DesignRevision - Shadcn Dashboard Tutorial](https://designrevision.com/blog/shadcn-dashboard-tutorial)
- [Refine - Building with Tremor](https://refine.dev/blog/building-react-admin-dashboard-with-tremor/)

### AI Agent Dashboards
- [Fuselab Creative - UI Design for AI Agents](https://fuselabcreative.com/ui-design-for-ai-agents/)
- [Verdent - Ralph TUI AI Agent Dashboard](https://www.verdent.ai/guides/ralph-tui-ai-agent-dashboard)
- [ServiceNow - AI Control Tower](https://www.servicenow.com/company/media/press-room/ai-control-tower-knowledge-25.html)
- [Daito Design - Designing Agentic Systems](https://www.daitodesign.com/blog/agentic-systems)
- [Codewave - Designing Agentic AI UI](https://codewave.com/insights/designing-agentic-ai-ui/)

### Homelab Dashboards
- [Its FOSS - Homelab Dashboard Tools](https://itsfoss.com/homelab-dashboard/)
- [Oreate AI - Ultimate Homelab Dashboard Guide](https://www.oreateai.com/blog/the-ultimate-homelab-dashboard-a-guide-to-the-best-options/389bb6013d29f90437602585ff1f751c)
- [Medium - Transform Homelab with Dashy](https://medium.com/@u.mair/transform-your-homelab-into-a-command-center-with-dashy-6e331304a6c7)
