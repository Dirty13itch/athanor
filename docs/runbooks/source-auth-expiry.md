# Source Auth Expiry

Source of truth: source-policy registry and source-auth incident evidence

---

## Trigger

- crawl or acquisition source reports expired auth

## Sequence

1. Pause the affected source immediately.
2. Capture the auth surface, last-success timestamp, and next retry posture.
3. Refresh the source credentials or auth session through the approved surface only.
4. Resume only after a fresh validation request succeeds.

## Verify

- source health returns to normal
- paused jobs resume without duplicate imports
- incident evidence records the repaired auth boundary
