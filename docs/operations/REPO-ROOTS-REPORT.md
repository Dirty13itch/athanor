# Repo Roots Report

Generated from `config/automation-backbone/repo-roots-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-03-29.1`
- Roots tracked: `9`

| Root | Host | Authority | Status | Scope |
| --- | --- | --- | --- | --- |
| `desk-main` | `desk` | `implementation-authority` | `active` | durable config, contracts, inventories, validators, and canonical current-state docs |
| `dev-runtime-repo` | `dev` | `runtime-authority` | `active` | live deployed repo and service runtime truth |
| `dev-opt-athanor` | `dev` | `runtime-state` | `active` | deployed application code and support assets |
| `dev-state` | `dev` | `runtime-state` | `active` | operator and service state |
| `dev-systemd` | `dev` | `runtime-state` | `active` | service unit definitions |
| `dev-cron` | `dev` | `runtime-state` | `active` | cron definitions |
| `dev-logs` | `dev` | `runtime-state` | `active` | service logs |
| `athanor-next` | `desk` | `incubation` | `active` | parallel next-gen experimentation |
| `desk-legacy` | `desk` | `vestigial` | `inactive` | historical root |

## desk-main

- Path: `C:/Athanor`
- Host: `desk`
- Authority: `implementation-authority`
- Notes: `Primary code and control-plane authority.`

## dev-runtime-repo

- Path: `/home/shaun/repos/athanor`
- Host: `dev`
- Authority: `runtime-authority`
- Notes: `Runtime and deployment authority until deployment is mirror-clean.`, `Observed 2026-03-29 runtime probe shows HEAD 075490f, the retired governor-facade caller set fully synced, and broader runtime-owned deployment surfaces still living only in the DEV runtime repo.`

## dev-opt-athanor

- Path: `/opt/athanor`
- Host: `dev`
- Authority: `runtime-state`
- Notes: `Observed 2026-03-26 entries include draftsman, heartbeat, and scripts.`

## dev-state

- Path: `/home/shaun/.athanor`
- Host: `dev`
- Authority: `runtime-state`
- Notes: `Observed 2026-03-26 entries include subscription-burn-state.json, subscription-tasks, provider-execution, overnight-queue.yaml, runtime.env, systemd envfiles, and worktrees.`

## dev-systemd

- Path: `/etc/systemd/system/athanor-*`
- Host: `dev`
- Authority: `runtime-state`
- Notes: `Observed 2026-03-26 estate includes 10 athanor-* units or timers.`, `Classifier, dashboard, and heartbeat are now EnvironmentFile-backed.`, `The remaining reviewed units are envless by deliberate contract rather than inheriting shell state.`

## dev-cron

- Path: `/etc/cron.d/athanor-* and /var/spool/cron/crontabs/shaun`
- Host: `dev`
- Authority: `runtime-state`
- Notes: `Observed 2026-03-26 system cron files include athanor-drift-check and athanor-overnight.`, `The Shaun user crontab now sources /home/shaun/.athanor/runtime.env through BASH_ENV, and the inline secret-bearing assignments were removed.`

## dev-logs

- Path: `/var/log/athanor`
- Host: `dev`
- Authority: `runtime-state`
- Notes: none

## athanor-next

- Path: `C:/Users/Shaun/dev/athanor-next`
- Host: `desk`
- Authority: `incubation`
- Notes: `Cannot silently become primary.`

## desk-legacy

- Path: `C:/Users/Shaun/athanor`
- Host: `desk`
- Authority: `vestigial`
- Notes: `Treat as non-authoritative unless explicitly promoted.`

## Known Drift

- `implementation-runtime-split` (medium): Implementation truth and runtime authority still live in different roots. Drift must reconcile from DEV back into C:/Athanor until deployment becomes a strict mirror.
- `dev-governor-facade-runtime-lag` (medium): The 2026-03-29 DEV cutover retired athanor-governor.service, removed the :8760 listener, and synced the mapped runtime-owned helper consumers back to implementation authority.
