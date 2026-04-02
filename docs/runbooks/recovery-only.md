# Recovery-Only Mode

Source of truth: `/health`, `config/automation-backbone/operator-runbooks.json`

---

## Trigger

- operator ingress is broken
- Postgres durable truth is unavailable
- Redis and Postgres hot-state reconciliation is suspect after restart or restore

## Sequence

1. Stop all non-recovery dispatch.
2. Verify operator auth, durable storage, and CAS or artifact reachability first.
3. Restore or reconcile the durable stores before reopening queues.
4. Keep a written incident reason attached to the recovery session.
5. Exit only by explicit operator decision after verification passes.

## Verify

- Postgres is reachable and schema-ready
- Redis hot state has been rebuilt or cleared safely
- operator ingress works again before dispatch resumes
