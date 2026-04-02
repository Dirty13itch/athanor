# Redis Reconciliation

Source of truth: Postgres durable truth, not Redis

---

## Trigger

- Redis restart
- hot-state drift after restore or failover
- stale leases or queue state that no longer matches durable truth

## Sequence

1. Treat Redis as disposable hot state.
2. Rebuild leases, snapshots, or cache entries from Postgres-backed truth.
3. Clear stale queue state that no longer maps to a live durable record.
4. Resume queue activity only after reconciliation completes.

## Verify

- blocked runs, approvals, and operator work match durable reads
- stale or duplicate leases are gone
- queue health is stable after resumption
