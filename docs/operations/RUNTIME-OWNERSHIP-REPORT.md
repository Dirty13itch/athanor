# Runtime Ownership Report

Generated from `config/automation-backbone/runtime-ownership-contract.json` plus the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-02.5`
- Cached truth snapshot: `2026-04-02T19:40:35.257979+00:00`
- Promotion gate: `runtime_ownership_maturity`
- Goal: Make runtime ownership explicit enough that host-level maintenance no longer depends on undocumented operator memory.
- Implementation authority: `desk-main` -> `C:/Athanor`
- Runtime authority: `dev-runtime-repo` -> `/home/shaun/repos/athanor`
- Runtime state roots: `dev-opt-athanor`, `dev-state`, `dev-systemd`, `dev-cron`, `vault-boot-config`, `vault-appdata`, `vault-appdatacache`, `vault-docker-root`, `foundry-opt-athanor`
- Ownership lanes tracked: `6`
- Execution packets tracked: `4`

| Criterion status | Count |
| --- | --- |
| `met` | 5 |

## Repo Evidence

- Implementation dirty file count: `0`
- DEV runtime dirty file count: `0`
- FOUNDRY compose root matches expected: `True`
- FOUNDRY build root clean: `True`
- FOUNDRY runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`

## Ownership Lanes

| Lane | Host | Mode | Status | Owner roots | Packet | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `dev-runtime-repo-systemd` | `dev` | `repo_worktree_mirror` | `active` | `dev-runtime-repo`, `dev-systemd` | `dev-runtime-repo-sync-packet` | Execute the dev-runtime-repo-sync-packet to make /home/shaun/repos/athanor a clean mirror of implementation authority, then restart only the repo-root services that actually changed. |
| `dev-dashboard-compose` | `dev` | `opt_compose_service` | `active` | `dev-opt-athanor`, `dev-runtime-repo` | `dev-dashboard-shadow-retirement-packet` | Keep athanor-dashboard.service masked as a recovery-only shadow; the active /opt/athanor/dashboard compose lane is the sole ordinary dashboard path. |
| `dev-heartbeat-opt` | `dev` | `opt_systemd_service` | `active` | `dev-opt-athanor`, `dev-systemd` | `dev-heartbeat-opt-deploy-packet` | Use the executed heartbeat deploy packet as the governed replacement path for future /opt/athanor/heartbeat updates. |
| `dev-runtime-state` | `dev` | `host_state_surface` | `active` | `dev-state`, `dev-systemd`, `dev-cron`, `dev-logs` | `none` | Keep these state surfaces explicit in reports so runtime maintenance is tied to named roots instead of operator memory. |
| `foundry-agents-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-agents-compose-deploy-packet` | Use the foundry-agents-compose-deploy-packet and scripts/deploy-agents.sh as the only ordinary update path; do not hot-patch site-packages in the running container. |
| `vault-runtime-maintenance` | `vault` | `vault_host_state` | `active` | `vault-boot-config`, `vault-appdata`, `vault-appdatacache`, `vault-docker-root` | `none` | Keep VAULT maintenance reachable through repo-owned SSH helpers instead of browser-only access. |

## dev-runtime-repo-systemd

- Label: `DEV runtime repo mirror lane`
- Host: `dev`
- Status: `active`
- Mode: `repo_worktree_mirror`
- Owner roots: `dev-runtime-repo -> /home/shaun/repos/athanor`, `dev-systemd -> /etc/systemd/system/athanor-*`
- Source root: `desk-main`
- Runtime scope: Mirror-clean runtime repo on DEV that backs repo-root services and serves as the governed source for repo-based runtime maintenance.
- Source paths: `.`
- Runtime paths: `/home/shaun/repos/athanor`
- Active surfaces: `/home/shaun/repos/athanor`, `athanor-brain.service`, `athanor-classifier.service`, `athanor-quality-gate.service`, `athanor-sentinel.service`, `athanor-overnight.service`
- Execution packet: `dev-runtime-repo-sync-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-MIGRATION-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh dev "systemctl show athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service athanor-overnight.service --property=WorkingDirectory,ExecStart --no-pager"`, `ssh dev "git -C /home/shaun/repos/athanor rev-parse --short HEAD && git -C /home/shaun/repos/athanor status --short | wc -l"`
- Rollback contract: Back up the pre-sync DEV repo state under /home/shaun/.athanor/backups/runtime-ownership/<timestamp>/ and preserve a timestamped backup branch before resetting main to the approved mirror commit.
- Approval boundary: Resetting the DEV runtime repo or restarting repo-root services remains approval-gated.
- Next action: Execute the dev-runtime-repo-sync-packet to make /home/shaun/repos/athanor a clean mirror of implementation authority, then restart only the repo-root services that actually changed.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

### Live systemd evidence

| Unit | Working directories | ExecStart | EnvFiles |
| --- | --- | --- | --- |
| `/home/shaun/repos/athanor` | none | none | 0 |
| `athanor-brain.service` | `/home/shaun/repos/athanor/services/brain` | `/home/shaun/repos/athanor/services/brain/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8780` | 0 |
| `athanor-classifier.service` | `/home/shaun/repos/athanor/services/classifier` | `/home/shaun/repos/athanor/services/classifier/.venv/bin/python main.py` | 1 |
| `athanor-quality-gate.service` | `/home/shaun/repos/athanor/services/quality-gate` | `/home/shaun/repos/athanor/services/quality-gate/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8790` | 0 |
| `athanor-sentinel.service` | `/home/shaun/repos/athanor/services/sentinel` | `/home/shaun/repos/athanor/services/sentinel/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8770` | 0 |
| `athanor-overnight.service` | `/home/shaun/repos/athanor` | `/home/shaun/repos/athanor/scripts/overnight-ops.sh` | 0 |

## dev-dashboard-compose

- Label: `DEV command center compose lane`
- Host: `dev`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `dev-opt-athanor -> /opt/athanor`, `dev-runtime-repo -> /home/shaun/repos/athanor`
- Source root: `desk-main`
- Runtime scope: Active command center deployment behind Caddy, built from the dashboard project and running from /opt/athanor/dashboard.
- Source paths: `projects/dashboard/Dockerfile`, `projects/dashboard/docker-compose.yml`
- Runtime paths: `/home/shaun/repos/athanor/projects/dashboard/Dockerfile`, `/home/shaun/repos/athanor/projects/dashboard/docker-compose.yml`, `/opt/athanor/dashboard/Dockerfile`, `/opt/athanor/dashboard/docker-compose.yml`
- Active surfaces: `athanor-dashboard container`, `caddy.service`, `https://athanor.local/`
- Execution packet: `dev-dashboard-shadow-retirement-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/OPERATOR-SURFACE-REPORT.md`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps"`, `ssh dev "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ && curl -sk -o /dev/null -w '%{http_code}' https://athanor.local/"`
- Rollback contract: Preserve the previous /opt/athanor/dashboard bundle under /opt/athanor/backups/dashboard/<timestamp>/ before replacing the compose root.
- Approval boundary: Replacing /opt/athanor/dashboard contents or restarting the live dashboard container remains approval-gated.
- Next action: Keep athanor-dashboard.service masked as a recovery-only shadow; the active /opt/athanor/dashboard compose lane is the sole ordinary dashboard path.
- Packet status: `executed`
- Packet approval type: `systemd_runtime_change`

### Live dashboard evidence

- Deployment mode: `containerized_service_behind_caddy`
- Active root: `/opt/athanor/dashboard`
- Runtime repo compose controls container: `True`
- Container running: `True`
- Container status: `Up 22 hours`
- Compose working dir: `/opt/athanor/dashboard`
- Legacy service state: `inactive` / `dead`
- Legacy unit file state: `masked`
- Legacy service root-cause hint: `none`
- Runtime probe status: `200`
- Canonical probe status: `200`

| Control file | Impl -> runtime repo | Impl -> deploy root | Runtime repo -> deploy root |
| --- | --- | --- | --- |
| `Dockerfile` | `True` | `True` | `True` |
| `docker-compose.yml` | `True` | `True` | `True` |

## dev-heartbeat-opt

- Label: `DEV heartbeat /opt lane`
- Host: `dev`
- Status: `active`
- Mode: `opt_systemd_service`
- Owner roots: `dev-opt-athanor -> /opt/athanor`, `dev-systemd -> /etc/systemd/system/athanor-*`
- Source root: `desk-main`
- Runtime scope: Node heartbeat daemon launched from /opt/athanor/heartbeat through systemd.
- Source paths: `scripts/node-heartbeat.py`
- Runtime paths: `/opt/athanor/heartbeat/node-heartbeat.py`, `/opt/athanor/heartbeat/env`
- Active surfaces: `athanor-heartbeat.service`
- Execution packet: `dev-heartbeat-opt-deploy-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh dev "systemctl is-active athanor-heartbeat.service && systemctl cat athanor-heartbeat.service | sed -n '1,120p'"`
- Rollback contract: Preserve the previous /opt/athanor/heartbeat bundle under /opt/athanor/backups/heartbeat/<timestamp>/ before replacement.
- Approval boundary: Changing the heartbeat bundle or its systemd unit remains approval-gated.
- Next action: Use the executed heartbeat deploy packet as the governed replacement path for future /opt/athanor/heartbeat updates.
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

### Live heartbeat evidence

- Unit file state: `enabled`
- Working directories: none
- ExecStart: `/opt/athanor/heartbeat/venv/bin/python3 /opt/athanor/heartbeat/node-heartbeat.py`
- EnvFiles: `1`
- Deployed script exists: `True`
- Host-local env exists: `True`
- Runtime venv exists: `True`
- Implementation matches deploy root: `True`

## dev-runtime-state

- Label: `DEV runtime state surfaces`
- Host: `dev`
- Status: `active`
- Mode: `host_state_surface`
- Owner roots: `dev-state -> /home/shaun/.athanor`, `dev-systemd -> /etc/systemd/system/athanor-*`, `dev-cron -> /etc/cron.d/athanor-* and /var/spool/cron/crontabs/shaun`, `dev-logs -> /var/log/athanor`
- Source root: `none`
- Runtime scope: Runtime envfiles, work queues, systemd units, cron definitions, and service logs that support live DEV operation.
- Source paths: none
- Runtime paths: `/home/shaun/.athanor`, `/etc/systemd/system/athanor-*`, `/etc/cron.d/athanor-*`, `/var/log/athanor`
- Active surfaces: `/home/shaun/.athanor/runtime.env`, `/home/shaun/.athanor/systemd`, `athanor-* systemd estate`, `athanor-* cron estate`
- Execution packet: `none`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/runbooks/local-runtime-env.md`
- Verification commands: `ssh dev "ls -1 /home/shaun/.athanor && systemctl list-unit-files 'athanor-*' --no-legend && ls -1 /etc/cron.d/athanor-* 2>/dev/null"`
- Rollback contract: Capture timestamped backups under /home/shaun/.athanor/backups/runtime-state/<timestamp>/ before mutating envfiles, cron, or service units.
- Approval boundary: Systemd, cron, and other host-level state mutations remain approval-gated.
- Next action: Keep these state surfaces explicit in reports so runtime maintenance is tied to named roots instead of operator memory.

### Live runtime-state evidence

- /opt entries: `backups`, `dashboard`, `draftsman`, `heartbeat`, `scripts`
- /home/shaun/.athanor entries: `backups`, `cli-router-embeddings.npz`, `overnight-queue.yaml`, `provider-execution`, `runtime.env`, `subscription-burn-state.json`, `subscription-tasks`, `systemd`, `worktrees`
- Cron files: `/etc/cron.d/athanor-drift-check`, `/etc/cron.d/athanor-overnight`

## foundry-agents-compose

- Label: `FOUNDRY athanor-agents compose lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active athanor-agents deployment built from the repo-owned compose bundle under /opt/athanor/agents on FOUNDRY.
- Source paths: `projects/agents/Dockerfile`, `projects/agents/pyproject.toml`, `projects/agents/docker-compose.yml`, `projects/agents/config/subscription-routing-policy.yaml`, `projects/agents/src/athanor_agents`, `scripts/deploy-agents.sh`
- Runtime paths: `/opt/athanor/agents/Dockerfile`, `/opt/athanor/agents/pyproject.toml`, `/opt/athanor/agents/docker-compose.yml`, `/opt/athanor/agents/config/subscription-routing-policy.yaml`, `/opt/athanor/agents/src/athanor_agents`, `/usr/local/lib/python3.12/site-packages/athanor_agents`
- Active surfaces: `athanor-agents container`, `/opt/athanor/agents compose bundle`, `http://foundry:9000/health`
- Execution packet: `foundry-agents-compose-deploy-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-agents.sh`
- Verification commands: `ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"`, `ssh foundry "docker exec athanor-agents python3 -c \"import json, pathlib, athanor_agents, athanor_agents.bootstrap_state as bootstrap_state; print(json.dumps({'module': str(pathlib.Path(athanor_agents.__file__).resolve()), 'bootstrap_state': str(pathlib.Path(bootstrap_state.__file__).resolve())}))\""`, `ssh foundry "curl -sS http://localhost:9000/health"`
- Rollback contract: Preserve the previous /opt/athanor/agents bundle under /opt/athanor/backups/agents/<timestamp>/ before replacement, and rebuild the compose lane from that backup if the rollout regresses.
- Approval boundary: Replacing /opt/athanor/agents contents or rebuilding the live athanor-agents container remains approval-gated.
- Next action: Use the foundry-agents-compose-deploy-packet and scripts/deploy-agents.sh as the only ordinary update path; do not hot-patch site-packages in the running container.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

### Live FOUNDRY agents evidence

- Expected root exists: `True`
- Compose root matches expected: `True`
- Build root clean: `True`
- Nested source dir present: `False`
- bak-codex files: none
- Container running: `True`
- Container status: `Up 2 minutes`
- Compose working dir: `/opt/athanor/agents`
- Compose config files: `/opt/athanor/agents/docker-compose.yml`
- Runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`
- Site-packages import: `True`
- Source mirrors: `/workspace/projects/agents/src/athanor_agents`, `/workspace/agents/src/athanor_agents`, `/app/src/athanor_agents`

| Control path | Kind | Impl exists | Runtime exists | Impl -> runtime |
| --- | --- | --- | --- | --- |
| `Dockerfile` | `file` | `True` | `True` | `True` |
| `pyproject.toml` | `file` | `True` | `True` | `True` |
| `docker-compose.yml` | `file` | `True` | `True` | `True` |
| `config/subscription-routing-policy.yaml` | `file` | `True` | `True` | `True` |
| `src/athanor_agents` | `directory` | `True` | `True` | `False` |

## vault-runtime-maintenance

- Label: `VAULT maintenance and host-state lane`
- Host: `vault`
- Status: `active`
- Mode: `vault_host_state`
- Owner roots: `vault-boot-config -> /boot/config`, `vault-appdata -> /mnt/user/appdata`, `vault-appdatacache -> /mnt/appdatacache`, `vault-docker-root -> /mnt/docker`
- Source root: `none`
- Runtime scope: Persistent Unraid config, Docker root, appdata, cache, and host-backed maintenance surfaces required for Athanor dependencies.
- Source paths: none
- Runtime paths: `/boot/config`, `/mnt/user/appdata`, `/mnt/appdatacache`, `/mnt/docker`
- Active surfaces: `repo-owned VAULT SSH helper path`, `Docker-backed infrastructure on VAULT`, `LiteLLM, Redis, and storage maintenance packets`
- Execution packet: `none`
- Evidence: `reports/truth-inventory/vault-redis-audit.json`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `scripts/vault-ssh.py`, `scripts/ssh-vault.ps1`
- Verification commands: `python scripts/vault-ssh.py "echo CONNECTED && hostname"`, `python scripts/vault_redis_audit.py --write reports/truth-inventory/vault-redis-audit.json`
- Rollback contract: Back up /boot/config and any targeted appdata bundle before mutating live VAULT runtime state.
- Approval boundary: VAULT Docker, env, and host-level mutations remain approval-gated.
- Next action: Keep VAULT maintenance reachable through repo-owned SSH helpers instead of browser-only access.

## Promotion Criteria

| Criterion | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `live_surface_mapping_complete` | `met` | Every live DEV and VAULT runtime surface relevant to Athanor has one declared ownership lane. | `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `vault_operator_access_non_browser` | `met` | VAULT maintenance must be reachable through repo-owned helpers instead of depending on the browser terminal. | `scripts/vault-ssh.py`, `scripts/ssh-vault.ps1`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `dashboard_shadow_unit_retired_or_recovery_only` | `met` | The inactive athanor-dashboard.service unit must be explicitly retired or downgraded to recovery-only so it cannot be mistaken for the active dashboard deployment path. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `repo_to_runtime_sync_packet_explicit` | `met` | The code path from C:/Athanor to /home/shaun/repos/athanor must have one explicit sync packet with verification and rollback instead of generic dirty-repo drift. | `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `opt_root_deploy_contract_complete` | `met` | Each active /opt/athanor surface must declare source path, deploy mode, verification, and rollback contract. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |

## Execution Packets

| Packet | Status | Lane | Approval type | Goal |
| --- | --- | --- | --- | --- |
| `dev-runtime-repo-sync-packet` | `ready_for_approval` | `dev-runtime-repo-systemd` | `runtime_host_reconfiguration` | Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone. |
| `dev-dashboard-shadow-retirement-packet` | `executed` | `dev-dashboard-compose` | `systemd_runtime_change` | Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path. |
| `dev-heartbeat-opt-deploy-packet` | `executed` | `dev-heartbeat-opt` | `runtime_host_reconfiguration` | Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps. |
| `foundry-agents-compose-deploy-packet` | `ready_for_approval` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes. |
