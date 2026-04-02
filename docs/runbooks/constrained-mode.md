# Constrained Mode

Source of truth: `config/automation-backbone/autonomy-activation-registry.json`, `config/automation-backbone/operator-runbooks.json`, `/health`

---

## Trigger

- unread inbox, approvals, or blocked runs breach the bounded attention budget
- compute or queue pressure makes optional work noisy

## Sequence

1. Confirm the current blocker from `/health` and the operator inbox.
2. Set posture so experiments, optional maintenance, and proactive loops are suppressed first.
3. Keep approvals, active run completion, and core operator work moving.
4. Do not widen scope while constrained mode is active.
5. Exit only after the triggering pressure is cleared and the queue has stabilized.

## Verify

- `/health` still shows core dependencies healthy
- optional lanes are paused or deferred
- inbox and blocked-run counts are moving down, not up
