# Audit Remediation Backlog

| Order | Priority | Blocking Status | Owner Surface | Action |
| --- | --- | --- | --- | --- |
| `1` | `high` | `operation` | `Scripts, validators, generators, and tooling` | Regenerate the stale publication and ownership reports in canonical order and re-run the platform validator until it is green before declaring the live report set converged. |
| `2` | `high` | `adoption` | `Adoption membrane between devstack and Athanor` | Slice the devstack dirty tranche into explicit publication checkpoints or packet-backed work bundles and keep forge/atlas truth isolated from exploratory edits. |
| `3` | `high` | `adoption` | `Devstack forge, atlas, and queue truth` | Regenerate the forge board JSON and markdown from the current lane registry and forge loop until validate_devstack_contract.py passes, then re-audit readiness against the refreshed board. |
| `4` | `medium` | `trust` | `Agents and orchestration` | Audit Ralph automation failure bookkeeping so claimed or already-dispatched runs do not accumulate as degraded failures when the live lane is otherwise healthy. |
| `5` | `medium` | `trust` | `Athanor control plane and truth surfaces` | Make finish-scoreboard and restart snapshot derive the active claim from the same Ralph claim surface used by steady-state status, or explicitly mark lagging/closure-only state as non-authoritative for live work. |
| `6` | `medium` | `trust` | `Operator communication and front-door UX` | Normalize queue summary derivation so finish-scoreboard, Ralph latest, restart snapshot, and steady-state status all compute dispatchable and suppressed counts from the same queue snapshot. |
| `7` | `medium` | `trust` | `Devstack forge, atlas, and queue truth` | Choose one source as the canonical top-priority-lane owner and derive the other from it, or explicitly distinguish routing-profile priority from lane-id priority. |
| `8` | `medium` | `adoption` | `Adoption membrane between devstack and Athanor` | Gate turnover-ready posture on a clean devstack contract pass and a bounded dirty-tranche threshold, or explicitly downgrade turnover posture when either condition is violated. |
