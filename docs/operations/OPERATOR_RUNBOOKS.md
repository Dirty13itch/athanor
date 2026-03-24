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

## Stuck queue recovery

1. Inspect scheduled jobs, task runs, and operator stream events.
2. Check whether the issue is routing, queue depth, worker failure, or an upstream dependency.
3. Retry bounded failed tasks before re-enabling whole lanes.
4. If the same task storms repeatedly, pause the affected lane and inspect the retry policy.

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
6. Record the result and any gaps in the operator stream or experiment ledger.

## Incident review

1. Start with the operator stream and run ledger, not guesswork.
2. Confirm who decided, which lane executed, and what fallback triggered.
3. Check whether the incident is a policy problem, a runtime outage, or a model-quality failure.
4. Decide whether the fix belongs in configuration, routing, evaluation, or recovery posture.
