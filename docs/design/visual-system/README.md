# Athanor Visual System

This directory is the canonical visual source of truth for Athanor's dashboard redesign.

It freezes ad hoc palette churn and replaces it with a research-first, implementation-ready visual contract.

## Program status

- Research phase: `locked`
- Implementation phase: `stages 1-8 completed; DEV command-center rollout verified on the live runtime`
- Current repo UI posture: operator-first, coherent, and systemized across the active cockpit
- Current live UI posture: running on the DEV command center behind Caddy; direct DEV runtime smoke is green, while canonical desktop `athanor.local` access still depends on hostname rollout
- Left-rail attention posture: `live`; urgent/action/watch route signals now derive from overview state and calm down after acknowledgment

## Direction

- Overall direction: `Futurist Control Room`
- Accent strategy: `Multi-signal system`
- Scope: `Full visual system`
- Brand metaphor: `Replace furnace/alchemical framing`
- Selected implementation family: `Carbon Ops`
- Atmosphere rule: `neutral charcoal only; bright neutral highlights and governed signal accents, not page wash`

## Primary product goal

The visual redesign exists to make it easier for Shaun to:

- understand system posture quickly
- steer agents and work priorities confidently
- decide when to approve, retry, pause, or redirect work
- trust why the system chose a lane or escalation path
- see which route needs review right now through governed left-rail attention rather than decorative motion

If a visual idea is interesting but does not improve operator control, it does not belong in Athanor.

## What this pack covers

- [VISUAL_CONSTITUTION.md](./VISUAL_CONSTITUTION.md): brand mood, image words, anti-image words, and non-negotiable visual rules
- [VISUAL_AUDIT.md](./VISUAL_AUDIT.md): current-state route and shell audit
- [REFERENCE_STUDY.md](./REFERENCE_STUDY.md): external research and adopt/avoid guidance
- [TOKEN_SPEC.md](./TOKEN_SPEC.md): semantic token specification and signal grammar
- [COMPONENT_APPEARANCE_STANDARD.md](./COMPONENT_APPEARANCE_STANDARD.md): shared component appearance rules
- [ROUTE_DIRECTION_MEMO.md](./ROUTE_DIRECTION_MEMO.md): route-by-route target direction for the active operator surfaces
- [BEFORE_AFTER_REVIEW.md](./BEFORE_AFTER_REVIEW.md): screenshot evidence set and review rubric
- [DESIGN_DEBT_LEDGER.md](./DESIGN_DEBT_LEDGER.md): keep / retune / redesign / retire classification
- [IMPLEMENTATION_SEQUENCE.md](./IMPLEMENTATION_SEQUENCE.md): staged implementation order after research lock

## What is frozen

Until this pack is implemented, do not make route-level styling changes that invent new:

- accent colors
- status semantics
- chart palettes
- surface materials
- typography roles
- motion behaviors

All future visual work should map back to the semantic rules defined here.

## Baseline evidence

This pack is grounded in:

- the current dashboard source:
  - `projects/dashboard/src/app/globals.css`
  - `projects/dashboard/src/components/app-shell.tsx`
  - `projects/dashboard/src/features/overview/command-center.tsx`
- the current UI route inventory:
  - `projects/dashboard/src/lib/navigation.ts`
  - `projects/dashboard/docs/OPERATOR-ROUTE-CONTRACTS.md`
- current route snapshots:
  - `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/*.png`

## Research stance

The dashboard information architecture is worth preserving.

This is not:

- a route reset
- an IA reset
- a second-shell exploration

This is a full visual-system redesign of the shell, materials, signals, charts, typography, motion, and route polish while preserving the current operator structure.
