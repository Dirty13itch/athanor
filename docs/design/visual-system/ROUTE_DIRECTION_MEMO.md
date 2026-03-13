# Route Direction Memo

## Purpose

This memo defines the target-state visual direction for the active operator routes.

It preserves the current route structure and specifies what each route should become under the locked visual system.

## Shell

### Current truth

- Layout is strong
- Sidebar/header structure should remain
- Primary weakness is material and signal cohesion

### Target direction

- carbon-charcoal shell chrome with bright controlled accents
- stronger separation between shell and content planes
- clearer active state on navigation
- no furnace-era metaphor in copy or materials
- no page-level blue atmospheric wash

## `/`

### Current strengths

- strongest route composition
- right operator priority
- governance cards and system map already positioned correctly

### Target direction

- command-center spotlight surface becomes the visual north star
- daily briefing, smart stack, unified stream, and workplan feel like one orchestrated dashboard, not four neighboring cards
- use strongest material hierarchy here first

### Accent policy

- structural accent primary
- domain accents allowed in subordinate modules
- severe states override all domain accents

## `/agents`

### Current strengths

- already feels operational
- clear route role

### Target direction

- clearer differentiation between:
  - agent roster
  - active run context
  - provider posture
  - judge outcome
  - recent outputs

### Accent policy

- workforce accent permitted as route tone
- sovereign/cloud decision and severity states override workforce tone

## `/tasks`

### Current strengths

- strong queue and action semantics

### Target direction

- approvals, retries, failures, and active work should be visually distinguishable at a glance
- task lineage should feel instrument-like, not card-generic

### Accent policy

- workforce accent secondary
- queue/severity grammar primary

## `/workplanner`

### Current strengths

- correct route importance

### Target direction

- make schedule posture, research queue, backlog pressure, and operator steering feel like parts of one planning console
- stronger planner-vs-execution hierarchy

## `/notifications`

### Target direction

- notification budget, alerts, incidents, and retryables must share one severity-first grammar
- remove any ambiguity between informational and actionable items

## `/learning`

### Target direction

- route should visually own model governance, proving-ground results, and learning posture
- use intelligence accent sparingly, with charts and tables carrying most of the hierarchy

## `/personal-data`

### Target direction

- memory and consolidation should feel trustworthy and calm
- use memory accent lightly
- make data surfaces feel more archival/semantic and less like standard dashboard cards

## `/chat`

### Target direction

- chat route should feel like an operator dispatch console
- routing preview, context preview, sovereign/cloud decisions, and judge posture need stronger integrated presentation

## `/services`, `/gpu`, `/monitoring`

### Current strengths

- closest to a true control-room tone already

### Target direction

- use these routes as canonical instrument surfaces
- standardize chart grammar, telemetry wells, and threshold semantics here first

## `/media`, `/gallery`, `/home`

### Target direction

- keep them clearly part of Athanor
- allow domain accents, but less aggressively than system-critical routes
- maintain route-specific personality without fragmenting the product

## `/review`, `/insights`, `/activity`, `/outputs`, `/conversations`

### Target direction

- make review and historical analysis feel quieter and more forensic
- use intelligence/history accents lightly
- rely more on typography, separators, and state chips than large color moves

## Mobile posture across routes

For every route:

- the first viewport should show the key state and the key action
- cards must preserve importance ordering
- route-level accent behavior must remain readable under small-space compression

## Route rollout priority

Implement visual redesign in this order:

1. shell
2. `/`
3. `/agents`
4. `/tasks`
5. `/workplanner`
6. `/notifications`
7. `/services`, `/gpu`, `/monitoring`
8. `/chat`
9. `/learning`, `/review`, `/personal-data`
10. domain routes and history routes
