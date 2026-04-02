# Postgres Restore

Source of truth: `projects/agents/src/athanor_agents/sql/bootstrap_durable_state.sql`, `/health`

---

## Trigger

- durable work or run state is unavailable or corrupted

## Sequence

1. Enter recovery-only posture.
2. Snapshot the current broken state before overwrite.
3. Restore the latest valid backup into a staged target.
4. Run integrity checks over operator work, runs, approvals, and foundry packets.
5. Repoint runtime only after staged verification passes.

## Verify

- durable schema is ready
- operator work, runs, and foundry reads succeed against the restored store
- `/health` no longer reports `durable_state:*` blockers
