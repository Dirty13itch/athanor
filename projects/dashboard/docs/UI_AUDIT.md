# Athanor UI Audit

## Scope

This audit covers the operator shell and the five primary console routes:

- `/`
- `/services`
- `/gpu`
- `/chat`
- `/agents`

The standard is a desktop-first single-operator console with WCAG 2.2 AA accessibility, strong keyboard support, deterministic loading/error states, and testable route behavior.

## Rubric

Each surface is reviewed against the same categories:

| Category | Standard |
| --- | --- |
| Information hierarchy | Primary state is visible in the first viewport and action paths are obvious |
| Interaction flow | Core tasks can be completed without dead ends or ambiguous controls |
| Accessibility | Semantic headings, keyboard completion, focus visibility, contrast-safe states |
| State handling | Nominal, loading, empty, degraded, and error states are explicit |
| Resilience | UI tolerates stale or partial upstream data without collapsing |
| Quality coverage | Shared behavior is covered by unit, accessibility, e2e, and visual checks |

## Scorecard

| Surface | Info | Flow | A11y | States | Resilience | Coverage | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shell | Strong | Strong | Strong | Strong | Strong | Moderate | Command palette, responsive nav, volatile-state masking for visual tests |
| `/` Command Center | Strong | Strong | Strong | Strong | Strong | Moderate | Clear posture, alert lane, hotspots, and launch paths |
| `/services` | Strong | Strong | Strong | Strong | Strong | Strong | URL-persisted filters, detail drawer, history, export, safe actions |
| `/gpu` | Strong | Strong | Strong | Strong | Strong | Strong | Time windows, focus state, pin compare, export, hotspot drill-down |
| `/chat` | Strong | Strong | Strong | Strong | Strong | Strong | Persisted sessions, prompt history, stop/retry-ready streaming path |
| `/agents` | Strong | Strong | Strong | Strong | Strong | Strong | Stable `toolCallId` handling, thread persistence, tool timeline UI |

## Key Findings Resolved

- Hardcoded route-local fetch logic was moved behind typed dashboard-owned APIs and React Query.
- Desktop shell now exposes global state, quick actions, and keyboard routing instead of acting like a static sidebar.
- Core console routes now expose explicit empty/error/loading states instead of silently collapsing.
- Agent tool-call correlation no longer relies on tool names alone.
- Route state is shareable through URL params and private operator context is stored locally.
- The quality harness now includes deterministic fixture-mode e2e runs, route-level accessibility checks, visual baselines, and state-helper unit coverage.

## Remaining Watch Items

- Service-history UX quality still depends on Prometheus blackbox probe deployment in the live environment.
- Visual regression baselines intentionally mask volatile timestamps; structural regressions are still caught, but timestamp text itself is not baseline compared.
- Storybook covers shared primitives and route-state building blocks; feature-module stories can be expanded further if the team wants richer visual review outside Playwright.
