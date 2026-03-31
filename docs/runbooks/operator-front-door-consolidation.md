# Operator Front Door Consolidation

## Purpose

This runbook now serves as the completed 2026-03-29 cutover record for the Athanor Command Center front door, plus the reproducible DESK hostname-rollout procedure. The DEV-hosted Athanor Command Center is the only production portal, it is fronted by Caddy at `https://athanor.local/`, and the WORKSHOP shadow portal on `:3001` has been retired.

## Canonical Contract

- Canonical operator URL: `https://athanor.local/`
- Current runtime fallback: `http://dev.athanor.local:3001/`
- Canonical production host: `DEV`
- Reverse proxy target: Caddy on `DEV`
- Retired shadow portal reference: `http://interface.athanor.local:3001/`

## Current State

- DEV serves the command center from the containerized dashboard runtime behind Caddy.
- `https://athanor.local/` returns `200` from DEV when the hostname is resolvable.
- DEV `:3001` returns `200`, and sampled `/_next/static` assets are clean in the live runtime.
- `python scripts/tests/live-dashboard-smoke.py --base-url http://dev.athanor.local:3001` is green again after the 2026-03-29 runtime refresh.
- DESK now resolves `athanor.local`, `dev.athanor.local`, `vault.athanor.local`, `interface.athanor.local`, and `core.athanor.local` through a scripted Windows hosts-file rollout.
- WORKSHOP `:3001` no longer serves the command center.
- The live dashboard container now runs from `/opt/athanor/dashboard` with `/opt/athanor/dashboard/docker-compose.yml` as the active compose config.
- The remaining front-door follow-up is broader DNS replacement if more operator desktops need the same aliases without the local hosts-file helper.

## Completed 2026-03-29 Cutover

1. Backed up the DEV dashboard runtime state and the WORKSHOP shadow container state.
2. Built and launched the DEV containerized dashboard runtime from implementation authority.
3. Installed Caddy on DEV and bound `https://athanor.local/` to the dashboard runtime.
4. Verified `200` on DEV runtime and Caddy paths.
5. Retired the WORKSHOP `athanor-dashboard` container on port `3001`.

## DESK Hostname Rollout

Run the helper from an elevated PowerShell session on DESK:

```powershell
sudo powershell -ExecutionPolicy Bypass -File C:\Athanor\scripts\setup-desk-host-aliases.ps1
```

The helper is idempotent and writes the canonical host aliases:

- `athanor.local` -> `192.168.1.189`
- `dev.athanor.local` -> `192.168.1.189`
- `vault.athanor.local` -> `192.168.1.203`
- `interface.athanor.local` -> `192.168.1.225`
- `core.athanor.local` -> `192.168.1.244`

## Follow-Up

1. Re-run browser smoke from a normal desktop path that resolves `athanor.local`.
2. Keep the former WORKSHOP dashboard lane retired unless it is explicitly reintroduced as preview or recovery-only in operator-surface truth.
3. Keep the dashboard service-health lane pinned to the lightweight operator-session probe instead of regressing to the heavyweight `/api/overview` aggregate.
4. Replace the local hosts-file rollout with internal DNS if more operator desktops need the same aliases.

## Acceptance

- Exactly one active production portal remains in operator-surface truth.
- `https://athanor.local/` is the operator-facing entry point.
- DEV runtime loads with no `_next/static` breakage.
- WORKSHOP no longer acts as a second production command center.
- Dashboard live smoke, browser verification, and truth validators all pass after the hostname rollout.
