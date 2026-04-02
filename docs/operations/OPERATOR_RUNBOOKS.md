# Operator Runbooks

These are the plain-language operating runbooks for the Athanor backbone.

## Morning review

1. Open the Command Center.
2. Review the daily briefing, unified stream, and governor posture.
3. Check failed jobs, degraded services, and provider reserve posture.
4. Confirm the current workplan still matches what matters today.
5. Resume paused lanes only if the reason for pause is resolved.

## Pause or resume automation

1. Use the governor surface first; do not SSH unless the governor path is unavailable.
2. Pause globally only for incidents or major maintenance.
3. Prefer pausing a single lane when only one domain is unhealthy.
4. Record the reason so the operator stream explains the posture later.
5. Resume only after health, provider, or dependency posture is back to normal.

## Provider exhaustion recovery

1. Check subscription summary for constrained lanes and reserve posture.
2. Confirm whether the work can fall back to local worker or sovereign supervisor lanes.
3. Defer quota-harvesting and noncritical cloud review before touching interactive reserves.
4. If no safe fallback exists, keep the task pending and notify rather than silently downgrading quality.

## Provider evidence capture

1. Use the provider catalog report first to identify whether the lane is blocked on billing proof, CLI proof, or provider-specific LiteLLM proof.
2. For Vault LiteLLM API lanes, start with `python scripts/probe_provider_usage_evidence.py --provider-id <provider-id>` so the proof uses the catalog-owned served model contract instead of a guessed alias.
3. If the probe returns `auth_failed`, switch to [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md) instead of forcing a manual evidence write.
4. Keep source labels concrete enough that later review can find the same log or request surface again.
5. Regenerate the truth reports immediately after recording the proof so the provider report and verification queue update.

## VAULT LiteLLM provider auth repair

1. Start from the provider catalog report, secret-surface report, and [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md), not guesswork.
2. Refresh `reports/truth-inventory/vault-litellm-env-audit.json` with `python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json` before changing anything.
3. Treat the `litellm` container env surface as the owner of upstream provider-key delivery on VAULT.
4. Repair missing provider env vars in the managed host-local secret surface only; do not place values in tracked source.
5. Recreate or redeploy only the `litellm` container after the env surface is repaired.
6. Re-run `python scripts/probe_provider_usage_evidence.py --all-vault-proxy`.
7. Regenerate the truth collector and truth reports before closing the maintenance pass.
8. Use [vault-litellm-provider-auth-repair.md](/C:/Athanor/docs/runbooks/vault-litellm-provider-auth-repair.md) for mutation boundaries and rollback notes, and use [VAULT-LITELLM-AUTH-REPAIR-PACKET.md](/C:/Athanor/docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md) for the generated provider-by-provider repair checklist.

## Local runtime env bootstrap

1. Treat `~/.athanor/runtime.env` as the preferred DESK-local secret surface for script lanes.
2. Keep only env names and path references in repo truth; never track the values.
3. Verify the surface with `python scripts/runtime_env.py --check ATHANOR_REDIS_URL ATHANOR_REDIS_PASSWORD`.
4. If the managed env file is missing, let Redis-backed automation scripts fail closed instead of silently downgrading auth.

## DEV secret-delivery normalization

1. Review the generated secret-surface and truth-drift reports before touching live runtime state.
2. Audit DEV user crontab and Athanor systemd units read-only first.
3. Keep user-crontab secret delivery on the `BASH_ENV` plus `/home/shaun/.athanor/runtime.env` contract instead of reintroducing inline assignments.
4. Keep reviewed Athanor systemd units on `EnvironmentFile` where secrets or runtime config are required, and keep envless units deliberate.
5. Treat this as an ask-first maintenance action and rerun the truth collectors immediately after the live pass.

## Governor facade rollback and audit

1. Treat `athanor-governor` on DEV as a retired compatibility surface, not canonical task or posture truth.
2. Confirm `/v1/governor` and `/v1/tasks/stats` are healthy before touching `:8760`.
3. Start from the latest truth collector evidence; the 2026-03-29 cutover proves the live listener is gone, observed `:8760` references are zero, and all 9 mapped callers are synced.
4. Audit the saved unit, journal, and listener evidence read-only first, then use [RUNTIME-MIGRATION-REPORT.md](/C:/Athanor/docs/operations/RUNTIME-MIGRATION-REPORT.md) plus [GOVERNOR-FACADE-CUTOVER-PACKET.md](/C:/Athanor/docs/operations/GOVERNOR-FACADE-CUTOVER-PACKET.md) as rollback and audit references instead of a forward migration checklist.
5. Treat any future systemd reactivation or `:8760` listener return as an explicit rollback or drift investigation, not as part of the normal operator path.
6. After any rollback or audit pass, rerun the truth collector and confirm the runtime checks stay green with no new `/queue` or `/health` traffic.

## Autonomy operations

1. Start from [AUTONOMY-ACTIVATION-REPORT.md](/C:/Athanor/docs/operations/AUTONOMY-ACTIVATION-REPORT.md), not `STATUS.md` prose alone.
2. Treat `full_system_phase_3` as the live autonomy scope and keep the full roster inside the registry-backed provider, sovereignty, and approval boundaries.
3. Keep runtime mutations approval-gated even while full-system autonomy is active.
4. Confirm provider posture still excludes auth-failed, configured-unused, or governed-handoff-only lanes from ordinary auto-routing.
5. Keep refusal-sensitive and private creative work on sovereign-only lanes even though those workload classes are now active.
6. If you need to change scope or exceptions, update the autonomy-activation registry first, then regenerate reports and rerun validators before treating the change as real.

## Constrained mode

1. Use constrained mode when inbox, approval, blocked-run, or compute pressure exceeds the bounded operating budget.
2. Pause experiments, optional maintenance, and proactive loops first.
3. Keep approvals, active run completion, and operator work flowing.
4. Do not widen scope while the system is constrained.

## Degraded mode

1. Use degraded mode for core dependency outages or blocker debt large enough to make normal dispatch unsafe.
2. Freeze promotions, launches, and nonessential dispatch.
3. Keep operator ingress, approvals, active run completion, and repair work alive.
4. Exit only after the degraded dependency or blocker queue is actually cleared.

## Recovery-only

1. Enter recovery-only when operator ingress, Postgres durable truth, or Redis reconciliation is suspect.
2. Stop all non-recovery dispatch.
3. Restore auth, durable storage, and reconciliation before reopening queues.
4. Exit only by explicit operator decision after verification passes.

## Blocked approval

1. Treat approval-gated runtime mutation as blocked work, not as permission to improvise.
2. Record the blocker, the required approval class, and the blocked slice or action in the operator inbox.
3. Keep unrelated ready slices moving; do not halt the whole program because one approval is pending.
4. Resume only after the approval packet is explicitly cleared and the blocker evidence is updated.

## Postgres restore

1. Snapshot the broken state before overwrite.
2. Restore into a staged target first.
3. Verify operator work, runs, approvals, and foundry records before repointing runtime.
4. Reopen the system only after `/health` clears the durable-state blocker.

## Redis reconciliation

1. Treat Redis as hot state only.
2. Rebuild or clear stale leases and queue state from durable Postgres truth.
3. Resume queue activity only after the hot state matches durable records again.

## Failed promotion

1. Freeze the affected channel immediately.
2. Use the recorded rollback target instead of improvising rollback.
3. Re-run smoke evidence after rollback.
4. Do not repromote until the defect is understood.

## Stuck task-engine recovery

1. Inspect scheduled jobs, task runs, and operator stream events.
2. Check whether the issue is routing posture, pending-task backlog, worker failure, or an upstream dependency.
3. Retry bounded failed tasks before re-enabling whole lanes.
4. If the same task storms repeatedly, pause the affected lane and inspect the retry policy.

## Stuck media pipeline

1. Check Prowlarr, Sonarr or Radarr, SABnzbd, Plex, and Tautulli in order.
2. Prefer targeted retry, pause, resume, or refresh before any config mutation.
3. Keep destructive media config changes behind explicit approval.
4. Close the incident only after downstream library visibility is restored.

## Source auth expiry

1. Pause the affected source immediately.
2. Capture the auth surface and last-success evidence.
3. Refresh auth through the approved surface only.
4. Resume only after a fresh validation call succeeds.

## Model lane outage

1. Confirm whether the outage is local, frontier-cloud, or handoff-only.
2. Keep sovereign-only work on sovereign lanes even if throughput drops.
3. Reroute only to allowed fallback lanes.
4. Capture provider evidence before closing the incident.

## Operator auth failure

1. Confirm the issue is auth and not a broader ingress outage.
2. Use the approved break-glass path only when normal passkey flow is unavailable.
3. Restore the normal auth path before resuming privileged mutations.
4. Record break-glass use and rotate session material if required.

## Sovereign routing verification

1. Inspect the task or run lineage.
2. Confirm the policy class and selected meta lane.
3. For `hybrid_abstractable`, verify only abstracted structure went cloud-side.
4. For `refusal_sensitive` and `sovereign_only`, confirm no cloud lane was used anywhere in the run lineage.

## Restore drill

1. Confirm which critical store is being tested.
2. Start with the non-destructive live rehearsal in the operations surface so Redis, Qdrant, Neo4j, and deployment-state probes produce current evidence.
3. Verify the most recent backup exists and is readable before any destructive restore step.
4. Restore in documented recovery order.
5. Validate the restored service before reconnecting dependent automation.
6. Generate the current rehearsal artifact with `python scripts/generate_recovery_evidence.py`.
7. Record the result and any gaps in the operator stream or experiment ledger, and confirm the artifact did not write credential-bearing URLs.

## Incident review

1. Start with the operator stream and run ledger, not guesswork.
2. Confirm who decided, which lane executed, and what fallback triggered.
3. Check whether the incident is a policy problem, a runtime outage, or a model-quality failure.
4. Decide whether the fix belongs in configuration, routing, evaluation, or recovery posture.
