# Athanor Mission-Control Rebuild Spec

**Status:** Active design authority for the dashboard rebuild  
**Last updated:** 2026-04-12 21:02 CDT  
**Scope:** [C:\Athanor\projects\dashboard](/C:/Athanor/projects/dashboard)

## Decision

The dashboard should be rebuilt from first principles with current Athanor truth, not iterated from the older "themed admin panel" direction.

What stays:

- Athanor remains the canonical operator front door.
- The route split of command center / operate / build / domains / catalog is directionally right.
- The dashboard stays dark-first and operator-oriented.

What changes:

- `/` becomes a true mission-control surface, not a summary page with extra cards.
- The visual system becomes authored and narrow instead of "custom shell over stock shadcn primitives."
- We stop carrying multiple aesthetic theses inside the live product.
- We design for long-session operation, high information density, strong keyboard flow, and explicit degraded states.

This file replaces the older warm/serif design thesis. That direction no longer matches the product, the current shell, or the operator use case.

## Research Baseline

This rebuild should be treated as a research-backed product reset, not a taste pass.

Primary sources reviewed for this spec:

- [W3C WCAG 2.2 Understanding Docs](https://www.w3.org/WAI/WCAG22/Understanding/)
  - reviewed 2026-04-12
  - page reports update date of 2026-02-11
  - key constraints for the rebuild: reflow, non-text contrast, focus visibility and appearance, target size, and motion-from-interaction controls
- [Carbon Design System Patterns Overview](https://carbondesignsystem.com/patterns/overview)
  - reviewed 2026-04-12
  - current Carbon guidance reinforces shared navigation structure, global header discipline, notifications, loading, and consistency across product surfaces
- [Carbon Design System 2x Grid Overview](https://carbondesignsystem.com/elements/2x-grid/overview/)
  - reviewed 2026-04-12
  - current layout guidance reinforces stable shell structure, predictable alignment, and layout systems that scale across navigation-heavy products
- [Carbon Data Table Usage](https://carbondesignsystem.com/components/data-table/usage/)
  - reviewed 2026-04-12
  - current guidance reinforces efficient data display, toolbar placement, row expansion as progressive disclosure, and table-first thinking over decorative summaries
- [Vercel Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
  - fetched 2026-04-13
  - key constraints for the rebuild: deep-link UI state, explicit focus treatments, reduced motion, semantic structure, text truncation discipline, and touch-safe interactions

Local evidence reviewed alongside outside research:

- live front door at [https://athanor.local/](https://athanor.local/)
- current theme tokens in [C:\Athanor\projects\dashboard\src\app\globals.css](/C:/Athanor/projects/dashboard/src/app/globals.css)
- shell structure in [C:\Athanor\projects\dashboard\src\components\app-shell.tsx](/C:/Athanor/projects/dashboard/src/components/app-shell.tsx)
- current mission-control page in [C:\Athanor\projects\dashboard\src\features\overview\command-center.tsx](/C:/Athanor/projects/dashboard/src/features/overview/command-center.tsx)
- route taxonomy in [C:\Athanor\projects\dashboard\src\lib\navigation.ts](/C:/Athanor/projects/dashboard/src/lib/navigation.ts)
- current route index and catalog surface in [C:\Athanor\projects\dashboard\src\app\more\page.tsx](/C:/Athanor/projects/dashboard/src/app/more/page.tsx)

## Product Thesis

The Athanor dashboard is not a portfolio site, not a BI dashboard, and not a themed launchpad.

It is a mission-control product for:

- posture
- dispatch
- intervention
- verification
- launch into specialist surfaces

The home page should answer only these questions:

1. Is the system healthy enough to operate?
2. What needs attention now?
3. What is running, blocked, or approval-held now?
4. What is the highest-leverage next action?
5. Where do I go next for depth?

Everything else belongs on a specialist route.

## Information Architecture

### Route roles

- `/`
  - mission control only
  - posture, alerts, dispatch state, next action, specialist launch
- `/operator`
  - human-in-the-loop control, approvals, governance, overrides
- `/topology`
  - system map, atlas, nodes, GPUs, agents, runtime relationships
- `/subscriptions`
  - burn economy, provider posture, leases, execution history
- `/routing`
  - route policy, provider elasticity, lane decisions, weak-lane truth
- `/projects`
  - promotion waves, milestones, project governance
- `/catalog`
  - lower-frequency launchpad and specialist discovery
- `/digest`
  - narrative briefings and readouts, not live control

### Command-center rules

- Maximum of 5 zones on the home page.
- Maximum of 8 top-level actionable blocks.
- No deep-dive cards for route families that already have a dedicated page.
- No inline "theme exploration," showcase, or catalog behavior on `/`.
- No dashboard hero language. Utility copy only.

### Specialist-route rules

- Each route gets one dominant work surface.
- Side panels and tables beat stacks of cards.
- State is deep-linkable by default.
- Filters, tabs, selections, and time windows belong in URL state unless clearly private.

## Visual Thesis

### Direction

Use a **dark industrial mission-control system** with a graphite shell, a calmer data plane, and a restrained near-neutral structural accent.

This is the working thesis:

- serious, not startup
- crisp, not glossy
- data-first, not decorative
- long-session friendly, not cinematic
- distinct enough to feel like Athanor, but disciplined enough to scale

### What this means in practice

- Keep dark mode as the primary operating mode.
- Remove diffuse decorative gradients from routine product surfaces.
- Use blur and glass only where chrome genuinely benefits from depth.
- Make state color do operational work, not branding work.
- Reduce the number of surface recipes drastically.

### Target palette model

Base roles only:

- `app`
- `chrome`
- `panel`
- `well`
- `selected`
- `line`
- `text`
- `muted`
- `accent`
- semantic signals: `healthy`, `warning`, `danger`, `review`

Rules:

- one structural accent only
- semantic colors reserved for system state
- domain colors are secondary metadata, not a second accent system
- no background should compete with live state colors

Recommended accent:

- near-neutral chalk / silver structure, never navy, cobalt, tan, or brown

Recommended neutrals:

- graphite to charcoal, with stronger separation than the current gray-on-gray stack

## Typography

The current three-font system is too split in personality.

### New rule

Use only two active families by default:

- `IBM Plex Sans` for UI, structure, and headings
- `IBM Plex Mono` for metrics, tokens, and operational data

If a third voice is required for compressed headers or rails, it must stay in the same family:

- `IBM Plex Sans Condensed`

### Explicit removals

- remove `Space Grotesk` from the primary UI system
- remove any serif direction from active operator product surfaces

### Typography rules

- headings should read as product structure, not editorial branding
- use `font-variant-numeric: tabular-nums` for comparisons and metrics
- labels should be compact and scannable
- big numbers should be louder than section chrome
- title case for primary headings and buttons

## Surface Grammar

The dashboard should be cardless by default.

### Default primitives

- rails
- strips
- panels
- wells
- lists
- tables
- inspectors
- status rows

### Use cards only when

- the card is the interaction boundary
- the card is the selection unit
- the card is an isolated module with a single primary task

### Remove or minimize

- repeated rounded-card mosaics
- nested cards
- decorative shadows on routine UI
- "hero cards"
- stacked micro-panels explaining the same state

## Shell Model

The shell should act like infrastructure.

### Persistent zones

- left rail
- top command strip
- main workspace
- optional right inspector on routes that need it

### Shell rules

- left rail only contains first-class route families and the most important entries
- command palette stays globally visible and keyboard-first
- top strip carries route identity, current system signal, and a small amount of live posture
- no duplicated launch surfaces in both the rail and the page body unless justified

## Motion

Motion should reinforce hierarchy and affordance, not create atmosphere for its own sake.

Allowed:

- command palette presence transitions
- route and drawer transitions
- hover-state sharpening
- subtle list or panel entrance sequencing

Required:

- support reduced motion
- animate transform and opacity only
- keep motion brief and interruptible

Not allowed:

- ornamental drift
- animated gradients in routine operator views
- long-loading shimmer as a design substitute for real state handling

## Data Display Rules

- Tables and structured lists are first-class citizens.
- Important numbers should appear in stable columns or rows, not floating badges.
- Toolbars belong with the thing they control.
- Expansion is preferred over separate drill-down pages when the task is still local.
- Empty, degraded, and stale states must be explicit.
- Route-local summaries should point to the route that owns the full truth.

## Accessibility and Performance Baseline

Every redesign slice must preserve or improve:

- WCAG 2.2 focus visibility and focus appearance
- 24x24 minimum pointer targets where required
- 320px reflow behavior without content loss outside explicit exceptions
- reduced-motion support
- keyboard-complete command palette, navigation, drawers, and filters
- visible degraded states rather than broken transport errors

Performance rules:

- do not increase first-load chrome weight for visual novelty
- keep dashboard-owned API boundaries thin
- large lists or tables must avoid naive full renders
- do not add ornamental client-side animation libraries where CSS is enough

## Autonomous Senior Team Model

This rebuild should be executed like a small senior product team, even when automated.

### Roles

- Front Door Program Lead
  - owns charter, scope, acceptance, and cutover
- Information Architecture Lead
  - owns route roles, page ownership, and what belongs on `/`
- UX Systems Designer
  - owns composition, hierarchy, and interaction model
- Design System Steward
  - owns tokens, primitives, shell chrome, and variant discipline
- Dashboard API and Contract Architect
  - owns front-door DTOs and specialist-route contracts
- Frontend Platform Architect
  - owns feature structure, query policy, URL-state policy, and performance boundaries
- Control Plane Integration Lead
  - owns normalization of upstream truth and degraded-state handling
- Operate Surfaces Lead
  - owns operator-heavy route families
- Build and Catalog Surfaces Lead
  - owns project, routing, model, topology, and catalog surfaces
- Verification and Release Lead
  - owns tests, visual baselines, accessibility checks, and launch gates

### Parallelization model

Can run in parallel:

- IA definition
- visual-system reset
- contract definition
- specialist route audits
- verification harness planning

Must stay sequential:

1. command-center charter
2. route ownership and kill list
3. token and primitive reset
4. shell rewrite
5. home-page rebuild
6. specialist-route rebuilds
7. deletion of superseded surfaces

## Execution Order

### Phase 1: Charter reset

- freeze the job of `/`
- define route ownership and what is no longer allowed on the home page
- explicitly retire the old themed-dashboard thesis

### Phase 2: Token and primitive reset

- rewrite [C:\Athanor\projects\dashboard\src\app\globals.css](/C:/Athanor/projects/dashboard/src/app/globals.css)
- replace generic shadcn-feeling variants in:
  - [C:\Athanor\projects\dashboard\src\components\ui\button.tsx](/C:/Athanor/projects/dashboard/src/components/ui/button.tsx)
  - [C:\Athanor\projects\dashboard\src\components\ui\card.tsx](/C:/Athanor/projects/dashboard/src/components/ui/card.tsx)
  - [C:\Athanor\projects\dashboard\src\components\ui\badge.tsx](/C:/Athanor/projects/dashboard/src/components/ui/badge.tsx)
  - [C:\Athanor\projects\dashboard\src\components\ui\input.tsx](/C:/Athanor/projects/dashboard/src/components/ui/input.tsx)
- remove theme exploration from the live product path, starting with:
  - [C:\Athanor\projects\dashboard\src\app\more\page.tsx](/C:/Athanor/projects/dashboard/src/app/more/page.tsx)

### Phase 3: Shell reset

- rebuild [C:\Athanor\projects\dashboard\src\components\app-shell.tsx](/C:/Athanor/projects/dashboard/src/components/app-shell.tsx)
- simplify the rail
- tighten the top strip
- align shell chrome with route roles and live operator posture

### Phase 4: Mission-control rebuild

- rebuild [C:\Athanor\projects\dashboard\src\features\overview\command-center.tsx](/C:/Athanor/projects/dashboard/src/features/overview/command-center.tsx)
- target one-screen triage on desktop
- move everything non-essential to dedicated routes

### Phase 5: Specialist-route rebuilds

- operate family first
- build family second
- catalog and digest cleanup last

### Phase 6: Verification and deletion

- add direct component coverage for the rebuilt shell and mission-control page
- expand mobile and navigation verification
- delete superseded exploratory or duplicate UI

## Acceptance Criteria

The rebuild is not done when it "looks better." It is done when:

- the first desktop viewport answers posture, attention, active work, and next action
- the home page fits within roughly 1 to 1.5 view heights on desktop
- the home page has no more than 8 top-level actionable blocks
- theme exploration is out of the live operator surface
- typography, shell chrome, and primitives all feel like one system
- stateful UI is deep-linkable
- card count is materially lower without loss of clarity
- keyboard and reduced-motion behavior are explicit and tested
- the front door feels like an operating console, not a themed admin kit

## Immediate Next Slice

The next implementation slice should be:

1. update global tokens and font strategy
2. rewrite shared primitives
3. remove theme exploration from live routes
4. rebuild the shell on the new primitives
5. then rebuild `/` on top of that system
