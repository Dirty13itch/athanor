# Runtime Ownership Contract

Source of truth: `config/automation-backbone/runtime-ownership-contract.json`, `config/automation-backbone/runtime-ownership-packets.json`, `config/automation-backbone/repo-roots-registry.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
Validated against registry version: `runtime-ownership-contract.json@2026-04-08.3`, `runtime-ownership-packets.json@2026-04-08.3`, `repo-roots-registry.json@2026-04-06.1`, `program-operating-system.json@2026-03-25.1`
Mutable facts policy: implementation authority, runtime authority, deployed roots, and live deployment modes come from the registries plus the latest truth snapshot. This runbook describes how code and runtime state move between those roots.

---

## Purpose

This runbook closes the old gap where `runtime_ownership_maturity` was described, but not transacted.

Current authority split:

- implementation authority: `C:\Athanor`
- runtime authority: `/home/shaun/repos/athanor` on `DEV`
- deployed runtime state: `/opt/athanor`, `/home/shaun/.athanor`, `/etc/systemd/system/athanor-*`, `/etc/cron.d/athanor-*`
- VAULT maintenance state: `/boot/config`, `/mnt/user/appdata`, `/mnt/appdatacache`, `/mnt/docker`

Runtime ownership is now explicit enough for full-system promotion to be an operator decision instead of a runtime-ownership blocker. The governed maintenance paths still live in `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`.

## Current Live Lanes

### 1. DEV runtime repo mirror lane

These services still run directly from `/home/shaun/repos/athanor`, but the governed end state is broader than a five-path patch: the entire DEV runtime repo should be a clean mirror of `C:\Athanor`, with restarts limited to the repo-root services that actually execute from that tree.

- `athanor-brain.service`
- `athanor-classifier.service`
- `athanor-quality-gate.service`
- `athanor-sentinel.service`
- `athanor-overnight.service`

Contract:

- code authority starts in `C:\Athanor`
- approved mirror sync lands in `/home/shaun/repos/athanor`
- service verification comes from `systemctl show ... WorkingDirectory,ExecStart`
- rollback requires a timestamped backup under `/home/shaun/.athanor/backups/runtime-ownership/<timestamp>/`
- packet id: `dev-runtime-repo-sync-packet`

### 2. DEV command center compose lane

The live dashboard is not the inactive `athanor-dashboard.service` unit. The active path is:

- source project: `/home/shaun/repos/athanor/projects/dashboard`
- deploy root: `/opt/athanor/dashboard`
- activation: `docker compose` container `athanor-dashboard`
- edge: `caddy.service`
- checks: `http://127.0.0.1:3001/` and `https://athanor.local/`

Contract:

- ordinary updates are governed by `scripts/deploy-dashboard.sh`
- runtime truth must keep the dashboard build root aligned between implementation authority, runtime repo, and `/opt/athanor/dashboard`
- replacing the live `/opt/athanor/dashboard` bundle is approval-gated and must preserve a timestamped backup first
- the inactive `athanor-dashboard.service` unit is masked as a recovery-only shadow and must stay out of ordinary dashboard startup paths
- packet ids: `dev-dashboard-shadow-retirement-packet` for the masked legacy unit, `dev-dashboard-compose-deploy-packet` for ordinary compose updates

### 3. DEV heartbeat /opt lane

The live heartbeat daemon runs from `/opt/athanor/heartbeat` through `athanor-heartbeat.service`.

Contract:

- source code comes from `scripts/node-heartbeat.py`
- deployed bundle lives under `/opt/athanor/heartbeat`
- the envfile remains host-local at `/opt/athanor/heartbeat/env`
- bundle replacement or service-unit changes are approval-gated and require a timestamped backup first
- packet id: `dev-heartbeat-opt-deploy-packet`

### 4. DEV runtime state surfaces

These are runtime-state roots, not implementation roots:

- `/home/shaun/.athanor`
- `/etc/systemd/system/athanor-*`
- `/etc/cron.d/athanor-*`
- `/var/log/athanor`

Contract:

- keep them explicit in reports and collectors
- do not silently treat them as repo-owned code
- treat mutations as runtime maintenance with backup, verification, and approval boundaries

### 5. VAULT maintenance lane

VAULT maintenance must use repo-owned helpers:

- `python scripts/vault-ssh.py`
- `python scripts/ssh-vault.ps1`

Contract:

- browser-terminal-only recovery is no longer acceptable as the default operator path
- back up `/boot/config` and targeted appdata bundles before live mutations
- keep Redis and LiteLLM maintenance grounded in the generated audit artifacts

## Mirror And Deploy Sequence

Use the packet report as the execution checklist. This runbook defines the lane boundaries; `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` defines the step-by-step maintenance packets that satisfy those boundaries.

### Repo-backed DEV services

1. Change `C:\Athanor`.
2. Verify locally.
3. Sync the approved runtime-owned paths into `/home/shaun/repos/athanor`.
4. Back up any runtime-owned file that will be replaced.
5. Restart or reload only the explicitly affected service.
6. Re-run the smallest useful health check and refresh truth reports.

### Dashboard compose lane

1. Change `C:\Athanor\projects\dashboard`.
2. Verify locally.
3. Sync the dashboard project into the governed DEV root.
4. Back up `/opt/athanor/dashboard`.
5. Run `scripts/deploy-dashboard.sh` so the active compose lane is rebuilt from implementation authority.
6. Verify:
   - `docker compose -f /opt/athanor/dashboard/docker-compose.yml ps dashboard`
   - `curl http://127.0.0.1:3001/`
   - `curl -k https://athanor.local/`
7. Refresh truth reports.

### Heartbeat /opt lane

1. Change `C:\Athanor\scripts\node-heartbeat.py`.
2. Verify locally if possible.
3. Back up `/opt/athanor/heartbeat`.
4. Replace the deployed heartbeat bundle.
5. Verify `systemctl is-active athanor-heartbeat.service`.
6. Refresh truth reports.

## Required Verification

- `python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json`
- `python scripts/generate_truth_inventory_reports.py`
- `python scripts/validate_platform_contract.py`
- `ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps"`
- `ssh dev "systemctl is-active athanor-heartbeat.service"`
- `ssh foundry "curl -sS http://localhost:9000/health"`

## Open Gaps

- `athanor-dashboard.service` is still present but inactive; the active dashboard is the `/opt/athanor/dashboard` compose lane.
- `dev-dashboard-compose-deploy-packet` now governs ordinary dashboard updates so `/opt/athanor/dashboard` and `/opt/athanor/ws-pty-bridge` are replaced through one explicit backup/rebuild path instead of remembered manual copy steps.
- `dev-runtime-repo-sync-packet` remains the governed maintenance path for bringing implementation authority and the DEV runtime repo closer to mirror-clean.
- `athanor-dashboard.service` remains masked as a recovery-only shadow; keep it out of ordinary startup and deployment paths.
- `foundry-agents-compose-deploy-packet` now governs the FOUNDRY `athanor-agents` lane explicitly. The live container importing from `/usr/local/lib/python3.12/site-packages/athanor_agents` is expected image layout, while `/workspace/projects/agents/src`, `/workspace/agents/src`, and `/app/src` remain read-only mirrors. Ordinary updates should go through the compose deploy packet and repo-owned deploy script, not ad hoc hotfixes.
- The remaining FOUNDRY cleanup work is build-root hygiene under `/opt/athanor/agents`, especially nested `src/athanor_agents/athanor_agents` residue or stale `*.bak-codex` files before the next approved rollout.
- Full-system promotion is no longer blocked by runtime ownership. The remaining work in this lane is governed maintenance and periodic truth refresh.
