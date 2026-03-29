# Operator Front Door Consolidation

## Purpose

This runbook now serves as the completed 2026-03-29 cutover record for the Athanor Command Center front door, plus the remaining hostname-rollout follow-up. The DEV-hosted Athanor Command Center is the only production portal, it is fronted by Caddy at `https://athanor.local/`, and the WORKSHOP shadow portal on `:3001` has been retired.

## Canonical Contract

- Canonical operator URL: `https://athanor.local/`
- Current runtime fallback: `http://dev.athanor.local:3001/`
- Canonical production host: `DEV`
- Reverse proxy target: Caddy on `DEV`
- Retired shadow portal reference: `http://192.168.1.225:3001/`

## Current State

- DEV serves the command center from the containerized dashboard runtime behind Caddy.
- `https://athanor.local/` returns `200` from DEV when the hostname is resolvable.
- DEV `:3001` returns `200`, and sampled `/_next/static` assets are clean in the live runtime.
- `python scripts/tests/live-dashboard-smoke.py --base-url http://192.168.1.189:3001` is green again after the 2026-03-29 runtime refresh.
- WORKSHOP `:3001` no longer serves the command center.
- The live dashboard container now runs from `/opt/athanor/dashboard` with `/opt/athanor/dashboard/docker-compose.yml` as the active compose config.
- The remaining operator-facing gap is desktop hostname resolution for `athanor.local`.

## Completed 2026-03-29 Cutover

1. Backed up the DEV dashboard runtime state and the WORKSHOP shadow container state.
2. Built and launched the DEV containerized dashboard runtime from implementation authority.
3. Installed Caddy on DEV and bound `https://athanor.local/` to the dashboard runtime.
4. Verified `200` on DEV runtime and Caddy paths.
5. Retired the WORKSHOP `athanor-dashboard` container on port `3001`.

## Remaining Follow-Up

1. Roll out `athanor.local` hostname resolution to operator desktops without relying on per-command host overrides.
2. Re-run browser smoke from a normal desktop path that resolves `athanor.local`.
3. Keep the former WORKSHOP dashboard lane retired unless it is explicitly reintroduced as preview or recovery-only in operator-surface truth.
4. Keep the dashboard service-health lane pinned to the lightweight operator-session probe instead of regressing to the heavyweight `/api/overview` aggregate.

## Acceptance

- Exactly one active production portal remains in operator-surface truth.
- `https://athanor.local/` is the operator-facing entry point.
- DEV runtime loads with no `_next/static` breakage.
- WORKSHOP no longer acts as a second production command center.
- Dashboard live smoke, browser verification, and truth validators all pass after the hostname rollout.
