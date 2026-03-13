# Design Debt Ledger

## Purpose

This ledger classifies current visual debt so implementation does not waste effort.

## Class meanings

- `keep`: already aligned, retain with minimal polish
- `retune`: structurally right, visual treatment should change
- `redesign`: needs a meaningful visual-system rewrite
- `retire`: should be removed from active visual truth

## Debt ledger

| Surface / asset | Classification | Why |
| --- | --- | --- |
| App shell layout | `keep` | structure and IA are strong |
| Sidebar/topbar materials | `retune` | need final control-room material identity |
| Command palette layout | `keep` | structure is strong |
| Command palette styling | `retune` | needs token/system alignment |
| Command Center composition | `keep` | route composition is already correct |
| Command Center materials | `redesign` | needs final spotlight, panel, and signal grammar |
| Agent console structure | `keep` | route role is clear |
| Agent console visual strata | `redesign` | needs stronger layer separation |
| Task/workplanner structure | `keep` | flow is correct |
| Task/workplanner status grammar | `redesign` | severity, queue, and provider states need a unified language |
| Monitoring/GPU/service chart treatment | `redesign` | needs canonical chart grammar |
| Memory/intelligence route composition | `keep` | route roles are good |
| Memory/intelligence styling | `retune` | needs quieter, role-appropriate identity |
| Current graphite-and-steel token baseline | `retune` | good direction, incomplete system |
| Furnace-era variable names | `retire` | conflicts with final visual identity |
| Furnace-era doc language | `retire` | conflicts with final visual identity |
| Cormorant heading tone | `retire` | wrong voice for futurist control room |
| Current warning amber semantics | `keep` | warning role is valid when strictly semantic |
| Domain accent behavior | `redesign` | under-governed and inconsistent |
| Surface utilities (`surface-*`) | `retune` | strong foundation, need final differentiation |
| Route-local chart colors | `retire` | must be replaced by one chart grammar |
| Status dots and badges | `retune` | strong base, needs stricter semantic separation |
| Ambient glow semantics | `redesign` | must stop implying warmth/furnace |
| Motion system | `redesign` | exists, but not yet one governed system |

## Immediate retire targets

Retire from active visual truth first:

- furnace-era names in design docs
- furnace-era shell language
- warm/ember/bronze metaphor cues
- any chart palette that is not part of the new chart grammar

## Immediate keep targets

Preserve:

- route structure
- shell navigation structure
- command-center composition
- active route family model
- operator density

## Progress update

As of `2026-03-12`, the major debt items above have been addressed in the repo implementation:

- sidebar/topbar materials: retuned
- command-center materials: redesigned
- agent/task/workplanner/status grammar: redesigned
- monitoring/GPU/services chart treatment: redesigned
- memory/intelligence styling: retuned
- domain accent behavior: redesigned and governed
- surface utilities: retuned into the final shared grammar
- route-local chart color drift: retired

Residual debt is now limited to:

- any route-specific polish found during optional live screenshot review
- future incremental refinement, not foundational redesign
