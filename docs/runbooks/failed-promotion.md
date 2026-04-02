# Failed Promotion

Source of truth: foundry deploy candidate record and rollback target

---

## Trigger

- smoke failure after promotion
- operator abort during rollout
- runtime evidence says the promoted candidate is unsafe

## Sequence

1. Freeze the affected channel.
2. Read the recorded `rollback_target` from the candidate record.
3. Execute rollback before attempting any forward fix.
4. Re-run smoke evidence and capture the failure in the incident trail.
5. Do not repromote until the underlying defect is understood.

## Verify

- previous target is restored
- channel health is back to normal
- rollback evidence is attached to the project history
