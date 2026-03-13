# Before / After Review Set

## Purpose

This document defines the screenshot review set for the Athanor visual redesign.

The original "before" side was the pre-redesign transitional baseline. The current repo snapshot set now reflects the implemented redesign, and the remaining comparison task is repo-vs-live verification after deployment.

## Review rules

Each reviewed surface must answer:

- Does it still feel earthy, furnace-based, or warm-metallic?
- Does the shell feel premium and controlled?
- Are chart and status semantics immediately legible?
- Does desktop feel intentional?
- Does mobile feel intentional?
- Does the route still belong to the same product family?

## Current baseline screenshot set

| Surface | Desktop snapshot | Mobile snapshot | Current posture |
| --- | --- | --- | --- |
| Command Center | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/command-center-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/command-center-mobile-chromium-win32.png` | structurally strong, visually transitional |
| Agents | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/agent-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/agent-console-mobile-chromium-win32.png` | operationally strong, needs stronger strata and signal rules |
| Chat | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/direct-chat-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/direct-chat-mobile-chromium-win32.png` | structurally solid, needs dispatch-console identity |
| GPU | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/gpu-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/gpu-console-mobile-chromium-win32.png` | strongest current control-room candidate |
| Monitoring | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/monitoring-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/monitoring-console-mobile-chromium-win32.png` | good telemetry posture, needs chart/signals lock |
| Services | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/services-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/services-console-mobile-chromium-win32.png` | strong structure, needs systemized instrument grammar |
| Home | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/home-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/home-console-mobile-chromium-win32.png` | solid domain surface, needs domain-accent discipline |
| Gallery | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/gallery-console-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/gallery-console-mobile-chromium-win32.png` | route identity is useful but not yet governed |
| History | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/history-activity-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/history-activity-mobile-chromium-win32.png` | needs quieter forensic tone |
| Intelligence / Review | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/intelligence-review-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/intelligence-review-mobile-chromium-win32.png` | needs clearer intelligence-specific grammar |
| Memory / Preferences | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/memory-preferences-desktop-chromium-win32.png` | `projects/dashboard/tests/e2e/visual.spec.ts-snapshots/memory-preferences-mobile-chromium-win32.png` | needs calmer archival tone |

## Current repo state

The repo-backed snapshot set has now been refreshed after the staged implementation sequence:

- shell, core routes, telemetry routes, intelligence/memory/chat routes, and domain/history routes all share the governed material and signal grammar
- the old earthy/furnace reading has been removed from the active screenshot set
- the deployed WORKSHOP dashboard has now been rebuilt and smoke-verified against the refreshed repo baselines
- the remaining review work is optional screenshot-by-screenshot live signoff and any final cosmetic polish

## After-state review requirements

For every surface above, the after screenshot should demonstrate:

- no earthy or furnace-led identity cues
- stronger material hierarchy than the baseline
- consistent shell language
- clearer distinction between structural accent, domain accent, and severity
- charts and metrics that read faster than the baseline

## Review rubric

### Pass

- reads as futurist control room
- route belongs to the same family as the shell
- signals are clear
- mobile layout still feels authored

### Fail

- route still feels warm/earthy
- accents feel random
- shell and content feel disconnected
- charts or metric cards still look generic
- route looks like a different product

## Signoff set

Signoff is not complete until the following are reviewed together:

- command center desktop
- command center mobile
- agents desktop
- tasks/workplanner desktop
- monitoring desktop
- chat desktop
- one memory/intelligence route

That set is the minimum needed to prove the redesign is systemic, not isolated.
