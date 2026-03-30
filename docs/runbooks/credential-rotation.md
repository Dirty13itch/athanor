# Credential Rotation Runbook

Source of truth: `docs/SECURITY-FOLLOWUPS.md`, `config/automation-backbone/platform-topology.json`, `config/automation-backbone/credential-surface-registry.json`
Validated against registry version: `platform-topology.json@2026-03-27.1`, `credential-surface-registry.json@2026-03-29.2`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: affected services, host placement, and auth classes come from the topology registry. This runbook owns the operator sequence for rotating credentials without reintroducing tracked secret values.

---

## Rules

- Never place the new secret value in tracked source while rotating it.
- Rotate one secret family at a time and verify every dependent service before moving on.
- Prefer host-local secret files or deployment-time injection over inline shell history.
- Treat rotation as a controlled maintenance action, not a background cleanup task.

## Preflight

1. Identify the secret family in `docs/SECURITY-FOLLOWUPS.md`.
2. Review the affected delivery surface in `config/automation-backbone/credential-surface-registry.json`.
3. If the change touches DEV cron or systemd delivery, review `docs/runbooks/dev-secret-delivery-normalization.md`.
4. If the change touches DESK-local script auth, review `docs/runbooks/local-runtime-env.md`.
5. If the change touches VAULT LiteLLM upstream provider keys, review `docs/runbooks/vault-litellm-provider-auth-repair.md`.
6. Map every dependent service from the current topology registry.
7. Pause affected automation lanes if the rotation can break live operator flows.
8. Create the new secret locally in a non-tracked location.
9. Record which services will need restart or redeploy.

## LiteLLM Master Key

This is the highest-priority shared credential because it fans out to the main control-plane clients.

1. Generate a new key into a non-tracked local file such as `~/.secrets/litellm-master-key-new`.
2. Update the VAULT-side LiteLLM deployment env or secret source.
3. Restart `litellm`.
4. Update dependent client secrets for:
   - `agent_server`
   - `dashboard`
   - `ws_pty_bridge` or any bridge/client that proxies through LiteLLM
   - any product surface or scaffold still using the routed model lane
5. Verify:
   - LiteLLM health
   - agent-server health
   - dashboard operator flows that rely on routed inference
   - the credential surface still matches the intended managed delivery method
6. Replace the old local secret file only after all dependents are green.

## Neo4j and Redis-Backed Runtime Credentials

1. Rotate the secret on the owning host.
2. Restart the owning store.
3. Restart dependent control-plane services one layer at a time.
4. Verify read and write behavior, not just health endpoints.
5. For Redis-backed control state, confirm queue/task/governor paths still function after reconnection.

## Home and Media Tokens

1. Rotate the token in the owning upstream system.
2. Update the host-local secret source used by agents.
3. Restart or refresh the agent runtime if required.
4. Run a narrow live read check against the affected integration.

## Observability and App-Specific Credentials

1. Rotate Langfuse and Miniflux credentials with their deployments isolated from the core control plane.
2. Verify their dedicated services before reconnecting agents or dashboards that consume them.
3. Rotate product-specific credentials such as Ulrich Energy separately so they do not widen blast radius during core recovery.

## Post-Rotation Verification

Run the smallest useful verification that proves the rotated secret works:

- service health endpoint
- one authenticated read call
- one authenticated mutation where applicable
- `python scripts/validate_platform_contract.py`
- `bash scripts/drift-check.sh` if the rotation affects multiple operator surfaces

## Cleanup

1. Remove temporary secret files or rotate them into their permanent local location.
2. Confirm no tracked file now contains the new value.
3. Record what was rotated, what was restarted, and what still needs follow-up.
4. If the rotation exposed a delivery-method drift, update `credential-surface-registry.json` and regenerate the secret-surface report before closing the maintenance window.
5. If the rotation changed the DEV cron/systemd or DESK local-runtime-env shape, keep the dedicated runbooks in sync with the new delivery method.
