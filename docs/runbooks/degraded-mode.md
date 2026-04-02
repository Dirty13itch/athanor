# Degraded Mode

Source of truth: `config/automation-backbone/autonomy-activation-registry.json`, `/health`, `docs/operations/ATHANOR-OPERATING-SYSTEM.md`

---

## Trigger

- Tier 0 or equivalent core outage
- multiple Tier 1 degradations
- blocked-run debt large enough that normal dispatch is unsafe

## Sequence

1. Freeze new promotions, launches, and nonessential dispatch.
2. Keep operator ingress, approvals, active run completion, and recovery work alive.
3. Route new work into inbox or backlog instead of immediate execution.
4. Record the degraded cause in the operator surface before any manual intervention.
5. Recover the dependency or drain the blocker queue before returning to normal.

## Verify

- `/health` shows the degraded dependency or blocker clearly
- nonessential loops are suppressed
- promotion paths are not advancing while degraded mode is active
