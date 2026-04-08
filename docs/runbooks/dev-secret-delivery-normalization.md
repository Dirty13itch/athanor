# DEV Secret Delivery Normalization

Source of truth: `config/automation-backbone/credential-surface-registry.json`, `config/automation-backbone/repo-roots-registry.json`, `docs/SECURITY-FOLLOWUPS.md`
Validated against registry version: `credential-surface-registry.json@2026-04-02.1`, `repo-roots-registry.json@2026-04-06.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: live secret-delivery surfaces, runtime-state roots, and approval boundaries come from the registries. This runbook owns the operator sequence for normalizing DEV cron and systemd delivery without printing secret values.

---

## Purpose

Normalize and maintain the DEV secret-bearing runtime surfaces so recurring jobs and systemd units keep explicit envfile-backed delivery instead of drifting back toward inline assignments.

This remains an ask-first runtime lane. Prepare and verify from the repo first, then execute on DEV during an intentional maintenance window whenever a future change touches the live secret-delivery contract.

## Current Truth

- User-crontab secret delivery now lives at `/home/shaun/.athanor/runtime.env`, sourced from `/var/spool/cron/crontabs/shaun` through `BASH_ENV`.
- Dedicated system cron files also exist at `/etc/cron.d/athanor-drift-check` and `/etc/cron.d/athanor-overnight`.
- The reviewed systemd estate now uses one of two explicit contracts:
  - `athanor-classifier.service`, `athanor-dashboard.service`, and `athanor-heartbeat.service` use `EnvironmentFile`
  - the remaining reviewed Athanor units start envless by deliberate contract

## Target State

- User-crontab jobs that require secrets stay on the `BASH_ENV` plus host-local envfile pattern.
- Systemd units that require secrets or runtime configuration stay on `EnvironmentFile`.
- Repo truth and generated reports keep tracking only presence, location, owner, and env contract names.

## Preflight

1. Regenerate the current truth reports.
2. Review `docs/operations/SECRET-SURFACE-REPORT.md`.
3. Review `config/automation-backbone/credential-surface-registry.json`.
4. Review `config/automation-backbone/repo-roots-registry.json`.
5. Confirm the maintenance window, rollback path, and restart order.

## Read-Only Audit Commands

Use these before changing live runtime state:

```bash
ssh dev 'crontab -l'
ssh dev 'ls -1 /etc/cron.d | grep athanor'
ssh dev 'systemctl list-unit-files "athanor-*" --no-legend --no-pager'
ssh dev 'systemctl cat athanor-dashboard.service athanor-heartbeat.service athanor-classifier.service'
python scripts/collect_truth_inventory.py
```

Do not copy secret values into notes or tracked files while auditing.

## Change Sequence

1. Create or update the host-local envfile for the affected cron jobs.
2. Keep secret-bearing user-crontab jobs on the `BASH_ENV` plus envfile-backed pattern instead of reintroducing inline assignments.
3. Identify every Athanor systemd unit that relies on runtime configuration.
4. Keep those units on explicit `EnvironmentFile` delivery one service at a time.
5. Reload systemd and restart only the units touched in the maintenance window.
6. Re-run the read-only audit commands and update repo truth if the live surface changed materially.

## Acceptance Checks

After the live runtime pass:

```bash
ssh dev 'crontab -l'
ssh dev 'systemctl cat athanor-dashboard.service athanor-heartbeat.service athanor-classifier.service'
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --check
python scripts/validate_platform_contract.py
```

Success criteria:

- no user-crontab job carries inline secret-bearing environment assignments
- every reviewed Athanor systemd unit uses either `EnvironmentFile` or a deliberate envless contract
- the secret-surface report and drift report remain aligned with the live runtime state

## Rollback

1. Restore the previous crontab and unit files from the pre-maintenance backup.
2. Reload systemd.
3. Restart only the affected units.
4. Re-run the read-only audit commands and confirm the system is back to the prior known state.
