# Steady-State Status

Do not edit manually.

## Purpose

- This tracked document is the durable operator contract for steady-state monitoring and reopen handling.
- Live claim rotation, provider routing, queue posture, and recent activity belong in the ignored live feed and machine JSON, not in repo-tracked markdown.
- Read the live feed first when you need to know what Athanor is doing right now.
- Live operator feed: `/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md`
- Machine proof: `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Canonical blocker map: `/mnt/c/Athanor/reports/truth-inventory/blocker-map.json`
- Blocker execution plan: `/mnt/c/Athanor/reports/truth-inventory/blocker-execution-plan.json`
- Continuity controller state: `/mnt/c/Athanor/reports/truth-inventory/continuity-controller-state.json`

## Operating Contract

- This tracked document is durable by design.
- `docs/operations/STEADY-STATE-STATUS.md` should only change when the operator contract or proof paths change.
- `reports/truth-inventory/steady-state-live.md` is the volatile front door for current work, next up, queue posture, and recent activity.
- `reports/truth-inventory/steady-state-status.json` is the machine-readable source for intervention level, reopen state, and queue counts.
- `reports/truth-inventory/blocker-map.json` is the canonical remaining-work source for family counts, next tranche selection, proof-gate posture, and auto-mutation state.
- `reports/truth-inventory/blocker-execution-plan.json` is the canonical bounded sub-tranche plan when a family requires decomposition.
- `reports/truth-inventory/continuity-controller-state.json` is the machine-readable controller lock, skip, and backoff state for the thread heartbeat lane.
- `reports/ralph-loop/latest.json` remains the deeper live dispatch proof when operator surfaces need forensic confirmation.

## Operator Action

- Start with the live operator feed to see the current lane, provider, and next handoff.
- If the JSON or live feed raises attention above `No action needed`, re-enter through `python scripts/session_restart_brief.py --refresh`.
- Use the finish scoreboard and runtime packet inbox before making closure or reopen claims.

## Reopen Triggers

- finish-scoreboard reports non-zero repo-safe debt
- runtime-packet-inbox packet_count rises above zero
- session restart brief or Ralph artifacts surface a typed brake
- live validation/probe evidence materially reopens Athanor core truth

## Active Reopen Reasons

- Read `reports/truth-inventory/steady-state-status.json` for the current reopen reasons.

## Evidence

- Ralph loop: `/mnt/c/Athanor/reports/ralph-loop/latest.json`
- Finish scoreboard: `/mnt/c/Athanor/reports/truth-inventory/finish-scoreboard.json`
- Runtime packet inbox: `/mnt/c/Athanor/reports/truth-inventory/runtime-packet-inbox.json`
- Blocker map: `/mnt/c/Athanor/reports/truth-inventory/blocker-map.json`
- Blocker execution plan: `/mnt/c/Athanor/reports/truth-inventory/blocker-execution-plan.json`
- Continuity controller state: `/mnt/c/Athanor/reports/truth-inventory/continuity-controller-state.json`
- Session restart brief source: `python scripts/session_restart_brief.py --refresh`
- Live operator feed: `/mnt/c/Athanor/reports/truth-inventory/steady-state-live.md`
- Steady-state JSON: `/mnt/c/Athanor/reports/truth-inventory/steady-state-status.json`
- Cross-system read: `docs/operations/ATHANOR-ECOSYSTEM-MASTER-PLAN.md`, `docs/operations/ATHANOR-OPERATOR-MODEL.md`, `docs/operations/ATHANOR-ECOSYSTEM-DEPENDENCY-MAP.md`
