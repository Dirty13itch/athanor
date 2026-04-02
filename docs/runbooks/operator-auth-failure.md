# Operator Auth Failure

Source of truth: operator session posture and break-glass policy

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

## Verify

- operator session access works on the normal path
- break-glass usage is recorded
- privileged dashboard mutations are gated again by the restored session flow
