# Operator Auth Failure

Source of truth: operator session posture, break-glass policy, `python scripts/session_restart_brief.py --refresh`, and `reports/truth-inventory/finish-scoreboard.json`

---

## Trigger

- WebAuthn failure
- session unlock failure
- operator dashboard ingress unavailable because auth posture is broken

## Sequence

1. Confirm the failure is auth, not general network or service outage.
2. Use the approved break-glass path only if the normal passkey flow is unavailable.
3. Restore the normal operator auth surface before resuming privileged mutations.
4. Rotate or revoke broken session material after access is restored.
5. Refresh the restart brief so finish-scoreboard and operator session posture agree before resuming other privileged work.

## Verify

- operator session access works on the normal path
- break-glass usage is recorded
- privileged dashboard mutations are gated again by the restored session flow
