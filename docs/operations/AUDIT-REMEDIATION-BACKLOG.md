# Audit Remediation Backlog

| Order | Priority | Blocking Status | Owner Surface | Action |
| --- | --- | --- | --- | --- |
| `1` | `high` | `operation` | `Scripts, validators, generators, and tooling` | Regenerate the stale publication and ownership reports in canonical order and re-run the platform validator until it is green before declaring the live report set converged. |
| `2` | `medium` | `trust` | `Athanor control plane and truth surfaces` | Make finish-scoreboard and restart snapshot derive the active claim from the same Ralph claim surface used by steady-state status, or explicitly mark lagging/closure-only state as non-authoritative for live work. |
| `3` | `medium` | `trust` | `Operator communication and front-door UX` | Normalize queue summary derivation so finish-scoreboard, Ralph latest, restart snapshot, and steady-state status all compute dispatchable and suppressed counts from the same queue snapshot. |
