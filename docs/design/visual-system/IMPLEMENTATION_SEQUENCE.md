# Implementation Sequence

## Purpose

This is the staged implementation order after the visual research pack is approved.

No route-specific redesign should start before the token, signal, material, and typography rules are locked.

## Stage 0: freeze

Status: `complete`

- stop ad hoc styling changes
- point all living docs to this visual pack
- treat this pack as the only visual source of truth

## Stage 1: token layer

Status: `complete`

- rename/replace legacy warm/furnace-era token names
- implement the new neutral, severity, domain, and interaction token sets
- implement typography stack changes
- implement motion timing primitives

## Stage 2: shell chrome

Status: `complete`

- sidebar
- topbar
- nav states
- command palette shell
- mobile sheet nav

## Stage 3: shared primitives

Status: `complete`

- cards
- tiles
- metrics
- badges
- status dots
- dialogs
- drawers
- tables
- chart wrappers

## Stage 4: command center and operator core

Status: `complete`

- `/`
- `/agents`
- `/tasks`
- `/workplanner`
- `/notifications`

## Stage 5: chart and metric grammar

Status: `complete`

- monitoring
- gpu
- services
- common chart components
- metric-card deltas and thresholds

## Stage 6: intelligence, memory, and chat

Status: `complete`

- `/learning`
- `/review`
- `/personal-data`
- `/chat`

## Stage 7: domain route polish

Status: `complete`

- `/media`
- `/gallery`
- `/home`
- history routes

## Stage 8: validation

Status: `complete`; `WORKSHOP rollout smoke-verified`

- visual snapshot refresh
- accessibility contrast review
- desktop/mobile screenshot review
- live deployment review

## Signoff gates

The visual redesign is not complete until:

- the dashboard no longer reads as earthy or furnace-based
- multi-signal behavior is clear and controlled
- route screenshots feel like one system
- desktop and mobile both look intentional
- another implementer could continue from the docs without inventing missing rules

## Current completion note

As of `2026-03-12`, the repo implementation has completed all staged visual-system work through validation:

- semantic token migration is in place
- shell chrome and shared primitives are systemized
- command-center and core operator routes are redesigned
- telemetry routes use the canonical chart and signal grammar
- intelligence, memory, chat, domain, and history routes are harmonized
- desktop and mobile visual baselines were refreshed
- `tsc`, `vitest`, `next build`, and the full Playwright suite passed from the canonical root

The remaining validation work is optional screenshot-driven live signoff and any last route-level polish found there. The repo implementation and live WORKSHOP rollout are already smoke-verified.
