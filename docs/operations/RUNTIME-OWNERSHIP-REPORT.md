# Runtime Ownership Report

Generated from `config/automation-backbone/runtime-ownership-contract.json` plus the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-06.2`
- Cached truth snapshot: `2026-04-08T00:13:15.964104+00:00`
- Promotion gate: `runtime_ownership_maturity`
- Goal: Make runtime ownership explicit enough that host-level maintenance no longer depends on undocumented operator memory.
- Implementation authority: `desk-main` -> `C:/Athanor`
- Runtime authority: `dev-runtime-repo` -> `/home/shaun/repos/athanor`
- Runtime state roots: `dev-opt-athanor`, `dev-state`, `dev-systemd`, `dev-cron`, `vault-boot-config`, `vault-appdata`, `vault-appdatacache`, `vault-docker-root`, `foundry-opt-athanor`, `workshop-opt-athanor`
- Ownership lanes tracked: `12`
- Execution packets tracked: `10`

| Criterion status | Count |
| --- | --- |
| `met` | 5 |

## Repo Evidence

- Implementation dirty file count: `0`
- DEV runtime dirty file count: `2`
- FOUNDRY compose root matches expected: `True`
- FOUNDRY build root clean: `True`
- FOUNDRY runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`

## Ownership Lanes

| Lane | Host | Mode | Status | Owner roots | Packet | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `dev-runtime-repo-systemd` | `dev` | `repo_worktree_mirror` | `active` | `dev-runtime-repo`, `dev-systemd` | `dev-runtime-repo-sync-packet` | Execute the dev-runtime-repo-sync-packet to make /home/shaun/repos/athanor a clean mirror of implementation authority, then restart only the repo-root services that actually changed. |
| `dev-dashboard-compose` | `dev` | `opt_compose_service` | `active` | `dev-opt-athanor`, `dev-runtime-repo` | `dev-dashboard-compose-deploy-packet` | Use the dev-dashboard-compose-deploy-packet and scripts/deploy-dashboard.sh as the only ordinary dashboard update path; keep athanor-dashboard.service masked as a recovery-only shadow. |
| `dev-heartbeat-opt` | `dev` | `opt_systemd_service` | `active` | `dev-opt-athanor`, `dev-systemd` | `dev-heartbeat-opt-deploy-packet` | Use the executed heartbeat deploy packet as the governed replacement path for future /opt/athanor/heartbeat updates. |
| `dev-runtime-state` | `dev` | `host_state_surface` | `active` | `dev-state`, `dev-systemd`, `dev-cron`, `dev-logs` | `none` | Keep these state surfaces explicit in reports so runtime maintenance is tied to named roots instead of operator memory. |
| `foundry-agents-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-agents-compose-deploy-packet` | Use the foundry-agents-compose-deploy-packet and scripts/deploy-agents.sh as the only ordinary update path; do not hot-patch site-packages in the running container. |
| `foundry-vllm-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-vllm-compose-reconciliation-packet` | Use the foundry-vllm-compose-reconciliation-packet to reconcile the live compose root to implementation authority and explicitly remove or reclassify any runtime-only extra service during an approved maintenance window. |
| `workshop-control-surface-compose` | `workshop` | `opt_compose_service` | `active` | `workshop-opt-athanor` | `workshop-control-surface-compose-reconciliation-packet` | Use the workshop-control-surface-compose-reconciliation-packet to align the live compose root with the newly formalized source contract while keeping the dashboard shadow explicitly recovery-only. |
| `workshop-vllm-compose` | `workshop` | `opt_compose_service` | `active` | `workshop-opt-athanor` | `workshop-vllm-compose-reconciliation-packet` | Use the workshop-vllm-compose-reconciliation-packet to reconcile the live compose root to implementation authority and explicitly decide whether the current custom image and runtime-only launch posture should be promoted or removed. |
| `workshop-product-compose` | `workshop` | `opt_compose_service` | `active` | `workshop-opt-athanor` | `none` | Keep these roots explicit and split them into narrower per-surface repair packets only when a specific Workshop product or creative service is intentionally reconciled. |
| `vault-litellm-config` | `vault` | `vault_host_state` | `active` | `vault-appdata`, `vault-docker-root` | `vault-litellm-config-reconciliation-packet` | Use the vault-litellm-config-reconciliation-packet to align the live config with implementation authority while keeping provider-auth repair as a separate explicit maintenance decision. |
| `vault-prometheus-config` | `vault` | `vault_host_state` | `active` | `vault-appdata`, `vault-docker-root` | `vault-prometheus-config-reconciliation-packet` | Use the vault-prometheus-config-reconciliation-packet to align the live scrape config with implementation authority and retire stale shadow targets in one governed maintenance window. |
| `vault-runtime-maintenance` | `vault` | `vault_host_state` | `active` | `vault-boot-config`, `vault-appdata`, `vault-appdatacache`, `vault-docker-root` | `none` | Keep VAULT maintenance reachable through repo-owned SSH helpers and route specific config drift through the named LiteLLM and Prometheus packets instead of generic host-state edits. |

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
- Source paths: `projects/dashboard`, `scripts/deploy-dashboard.sh`
- Runtime paths: `/home/shaun/repos/athanor/projects/dashboard`, `/opt/athanor/dashboard`
- Active surfaces: `athanor-dashboard container`, `caddy.service`, `https://athanor.local/`
- Execution packet: `dev-dashboard-compose-deploy-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/OPERATOR-SURFACE-REPORT.md`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-dashboard.sh`
- Verification commands: `ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps dashboard"`, `ssh dev "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ && curl -sk -o /dev/null -w '%{http_code}' https://athanor.local/"`
- Rollback contract: Preserve the previous /opt/athanor/dashboard bundle under /opt/athanor/backups/dashboard/<timestamp>/ before replacing the compose root.
- Approval boundary: Replacing /opt/athanor/dashboard contents or restarting the live dashboard container remains approval-gated.
- Next action: Use the dev-dashboard-compose-deploy-packet and scripts/deploy-dashboard.sh as the only ordinary dashboard update path; keep athanor-dashboard.service masked as a recovery-only shadow.
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

### Live dashboard evidence

- Deployment mode: `containerized_service_behind_caddy`
- Active root: `/opt/athanor/dashboard`
- Runtime repo compose controls container: `True`
- Container running: `True`
- Container status: `Up 3 days`
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
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

### Live FOUNDRY agents evidence

- Expected root exists: `True`
- Compose root matches expected: `True`
- Build root clean: `True`
- Nested source dir present: `False`
- bak-codex files: none
- Container running: `True`
- Container status: `Up 23 hours`
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

## foundry-vllm-compose

- Label: `FOUNDRY vLLM compose lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active FOUNDRY vLLM deployment under /opt/athanor/vllm that serves the coordinator and coder lanes and currently carries runtime-owned compose drift against the rendered repo config.
- Source paths: `ansible/host_vars/core.yml`, `ansible/roles/vllm/defaults/main.yml`, `ansible/roles/vllm/templates/docker-compose.yml.j2`, `reports/rendered/foundry-vllm.rendered.yml`
- Runtime paths: `/opt/athanor/vllm/docker-compose.yml`
- Active surfaces: `vllm-coordinator container`, `vllm-coder container`, `http://foundry:8000/v1/models`, `http://foundry:8006/v1/models`
- Execution packet: `foundry-vllm-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/foundry-vllm.diff`, `reports/rendered/foundry-vllm.rendered.yml`, `reports/live/foundry-vllm.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh foundry "cd /opt/athanor/vllm && docker compose ps"`, `ssh foundry "docker inspect vllm-coder --format '{{json .Config.Cmd}}'"`, `ssh foundry "curl -sS http://localhost:8006/v1/models"`
- Rollback contract: Preserve the previous /opt/athanor/vllm bundle under /opt/athanor/backups/vllm/<timestamp>/ before replacing the compose root, and restore that bundle if the approved reconcile pass regresses the active coder or coordinator lanes.
- Approval boundary: Replacing /opt/athanor/vllm/docker-compose.yml or recreating the live FOUNDRY vLLM containers remains approval-gated.
- Next action: Use the foundry-vllm-compose-reconciliation-packet to reconcile the live compose root to implementation authority and explicitly remove or reclassify any runtime-only extra service during an approved maintenance window.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

## workshop-control-surface-compose

- Label: `WORKSHOP control-surface compose lane`
- Host: `workshop`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `workshop-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Recovery-only Workshop dashboard shadow plus the live ws-pty-bridge compose bundle rooted under /opt/athanor/dashboard and /opt/athanor/ws-pty-bridge.
- Source paths: `ansible/host_vars/interface.yml`, `ansible/roles/dashboard/defaults/main.yml`, `ansible/roles/dashboard/tasks/main.yml`, `ansible/roles/dashboard/templates/docker-compose.yml.j2`, `projects/dashboard`, `projects/ws-pty-bridge`, `reports/rendered/workshop-dashboard.rendered.yml`
- Runtime paths: `/opt/athanor/dashboard/docker-compose.yml`, `/opt/athanor/ws-pty-bridge`
- Active surfaces: `athanor-dashboard container (shadow recovery)`, `athanor-ws-pty-bridge container`, `http://workshop:3001/`, `http://workshop:3100/health`
- Execution packet: `workshop-control-surface-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/workshop-dashboard.diff`, `reports/rendered/workshop-dashboard.rendered.yml`, `reports/live/workshop-dashboard.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh workshop "cd /opt/athanor/dashboard && docker compose ps"`, `ssh workshop "docker inspect athanor-ws-pty-bridge --format '{{.Name}}|{{.State.Status}}'"`, `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3100/health"`
- Rollback contract: Preserve the previous /opt/athanor/dashboard compose bundle and /opt/athanor/ws-pty-bridge source under /opt/athanor/backups/dashboard-shadow/<timestamp>/ before replacement, and restore both if the approved reconcile pass regresses bridge access or the shadow recovery surface.
- Approval boundary: Replacing Workshop control-surface compose roots or recreating the live dashboard shadow or ws-pty-bridge containers remains approval-gated.
- Next action: Use the workshop-control-surface-compose-reconciliation-packet to align the live compose root with the newly formalized source contract while keeping the dashboard shadow explicitly recovery-only.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

## workshop-vllm-compose

- Label: `WORKSHOP vLLM compose lane`
- Host: `workshop`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `workshop-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active Workshop vLLM worker deployment rooted at /opt/athanor/vllm-node2 and serving the Workshop worker lane on :8010.
- Source paths: `ansible/host_vars/interface.yml`, `ansible/roles/vllm/defaults/main.yml`, `ansible/roles/vllm/templates/docker-compose.yml.j2`, `reports/rendered/workshop-vllm.rendered.yml`
- Runtime paths: `/opt/athanor/vllm-node2/docker-compose.yml`
- Active surfaces: `vllm-node2 container`, `http://workshop:8010/v1/models`
- Execution packet: `workshop-vllm-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/workshop-vllm.diff`, `reports/rendered/workshop-vllm.rendered.yml`, `reports/live/workshop-vllm.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh workshop "cd /opt/athanor/vllm-node2 && docker compose ps"`, `ssh workshop "docker inspect vllm-node2 --format '{{json .Config.Cmd}}'"`, `ssh workshop "curl -sS http://127.0.0.1:8010/v1/models"`
- Rollback contract: Preserve the previous /opt/athanor/vllm-node2 compose bundle under /opt/athanor/backups/vllm-node2/<timestamp>/ before replacement, and restore it if the approved reconcile pass regresses the active Workshop worker lane.
- Approval boundary: Replacing /opt/athanor/vllm-node2/docker-compose.yml or recreating the live Workshop vLLM worker container remains approval-gated.
- Next action: Use the workshop-vllm-compose-reconciliation-packet to reconcile the live compose root to implementation authority and explicitly decide whether the current custom image and runtime-only launch posture should be promoted or removed.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

## workshop-product-compose

- Label: `WORKSHOP product and creative compose lane`
- Host: `workshop`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `workshop-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active Workshop product and creative compose roots for Open WebUI, ComfyUI, EoBQ, and Ulrich Energy under /opt/athanor.
- Source paths: `ansible/host_vars/interface.yml`, `ansible/roles/open-webui/defaults/main.yml`, `ansible/roles/open-webui/templates/docker-compose.yml.j2`, `ansible/roles/comfyui/defaults/main.yml`, `ansible/roles/comfyui/templates/docker-compose.yml.j2`, `ansible/roles/eoq/defaults/main.yml`, `ansible/roles/eoq/templates/docker-compose.yml.j2`, `ansible/roles/ulrich-energy/defaults/main.yml`, `ansible/roles/ulrich-energy/templates/docker-compose.yml.j2`, `projects/eoq`, `projects/ulrich-energy`, `projects/comfyui-workflows`
- Runtime paths: `/opt/athanor/open-webui/docker-compose.yml`, `/opt/athanor/comfyui/docker-compose.yml`, `/opt/athanor/eoq/docker-compose.yml`, `/opt/athanor/ulrich-energy/docker-compose.yml`
- Active surfaces: `open-webui container`, `comfyui container`, `athanor-eoq container`, `athanor-ulrich-energy container`, `http://workshop:3000/`, `http://workshop:8188/`, `http://workshop:3002/`, `http://workshop:3003/`
- Execution packet: `none`
- Evidence: `reports/deployment-drift/workshop-open-webui.diff`, `reports/deployment-drift/workshop-comfyui.diff`, `reports/deployment-drift/workshop-eoq.diff`, `reports/deployment-drift/workshop-ulrich-energy.diff`, `reports/live/workshop-open-webui.live.yml`, `reports/live/workshop-comfyui.live.yml`, `reports/live/workshop-eoq.live.yml`, `reports/live/workshop-ulrich-energy.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`
- Verification commands: `ssh workshop "docker compose -f /opt/athanor/open-webui/docker-compose.yml ps && docker compose -f /opt/athanor/comfyui/docker-compose.yml ps && docker compose -f /opt/athanor/eoq/docker-compose.yml ps && docker compose -f /opt/athanor/ulrich-energy/docker-compose.yml ps"`, `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/ && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8188/ && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3002/ && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3003/"`
- Rollback contract: Preserve the current product and creative compose bundles under timestamped /opt/athanor/backups/<service>/<timestamp>/ roots before any future runtime mutation on these Workshop surfaces.
- Approval boundary: Replacing Workshop product or creative compose roots or recreating their live containers remains approval-gated.
- Next action: Keep these roots explicit and split them into narrower per-surface repair packets only when a specific Workshop product or creative service is intentionally reconciled.

## vault-litellm-config

- Label: `VAULT LiteLLM config lane`
- Host: `vault`
- Status: `active`
- Mode: `vault_host_state`
- Owner roots: `vault-appdata -> /mnt/user/appdata`, `vault-docker-root -> /mnt/docker`
- Source root: `desk-main`
- Runtime scope: Live VAULT LiteLLM proxy config and container state rooted at /mnt/user/appdata/litellm/config.yaml, including the coder lane mapping that still differs from implementation authority.
- Source paths: `ansible/host_vars/vault.yml`, `ansible/roles/vault-litellm/defaults/main.yml`, `ansible/roles/vault-litellm/templates/litellm_config.yaml.j2`, `reports/rendered/vault-litellm-config.rendered.yaml`
- Runtime paths: `/mnt/user/appdata/litellm/config.yaml`
- Active surfaces: `litellm container`, `/mnt/user/appdata/litellm/config.yaml`, `http://vault:4000/health`
- Execution packet: `vault-litellm-config-reconciliation-packet`
- Evidence: `reports/deployment-drift/vault-litellm.diff`, `reports/rendered/vault-litellm-config.rendered.yaml`, `reports/live/vault-litellm-config.live.yaml`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md`
- Verification commands: `python scripts/vault-ssh.py "docker inspect litellm --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"`, `python scripts/vault-ssh.py "test -f /mnt/user/appdata/litellm/config.yaml && sed -n '1,120p' /mnt/user/appdata/litellm/config.yaml"`, `python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4000/health"`
- Rollback contract: Back up the current /mnt/user/appdata/litellm/config.yaml plus the current litellm container definition before replacing the config, and restore both if the approved reconcile pass regresses routing or auth posture.
- Approval boundary: Mutating /mnt/user/appdata/litellm/config.yaml or recreating the live litellm container on VAULT remains approval-gated.
- Next action: Use the vault-litellm-config-reconciliation-packet to align the live config with implementation authority while keeping provider-auth repair as a separate explicit maintenance decision.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

## vault-prometheus-config

- Label: `VAULT Prometheus config lane`
- Host: `vault`
- Status: `active`
- Mode: `vault_host_state`
- Owner roots: `vault-appdata -> /mnt/user/appdata`, `vault-docker-root -> /mnt/docker`
- Source root: `desk-main`
- Runtime scope: Live VAULT Prometheus scrape config rooted at /mnt/user/appdata/prometheus/prometheus.yml, including blackbox targets and direct metrics jobs that currently drift from implementation authority.
- Source paths: `ansible/host_vars/vault.yml`, `ansible/roles/vault-monitoring/defaults/main.yml`, `ansible/roles/vault-monitoring/templates/prometheus.yml.j2`, `reports/rendered/vault-prometheus.rendered.yml`
- Runtime paths: `/mnt/user/appdata/prometheus/prometheus.yml`
- Active surfaces: `prometheus container`, `/mnt/user/appdata/prometheus/prometheus.yml`, `http://vault:9090/-/healthy`
- Execution packet: `vault-prometheus-config-reconciliation-packet`
- Evidence: `reports/deployment-drift/vault-prometheus.diff`, `reports/rendered/vault-prometheus.rendered.yml`, `reports/live/vault-prometheus.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`
- Verification commands: `python scripts/vault-ssh.py "docker inspect prometheus --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"`, `python scripts/vault-ssh.py "test -f /mnt/user/appdata/prometheus/prometheus.yml && sed -n '1,220p' /mnt/user/appdata/prometheus/prometheus.yml"`, `python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/-/healthy"`
- Rollback contract: Back up the current /mnt/user/appdata/prometheus/prometheus.yml and the current Prometheus container definition before replacement, and restore them if the approved reconcile pass regresses monitoring coverage or the Prometheus service state.
- Approval boundary: Mutating /mnt/user/appdata/prometheus/prometheus.yml or recreating the live Prometheus container on VAULT remains approval-gated.
- Next action: Use the vault-prometheus-config-reconciliation-packet to align the live scrape config with implementation authority and retire stale shadow targets in one governed maintenance window.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

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
- Active surfaces: `repo-owned VAULT SSH helper path`, `Docker-backed infrastructure on VAULT`, `LiteLLM, Prometheus, Redis, and storage maintenance packets`
- Execution packet: `none`
- Evidence: `reports/truth-inventory/vault-redis-audit.json`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `scripts/vault-ssh.py`, `scripts/ssh-vault.ps1`
- Verification commands: `python scripts/vault-ssh.py "echo CONNECTED && hostname"`, `python scripts/vault_redis_audit.py --write reports/truth-inventory/vault-redis-audit.json`
- Rollback contract: Back up /boot/config and any targeted appdata bundle before mutating live VAULT runtime state.
- Approval boundary: VAULT Docker, env, and host-level mutations remain approval-gated.
- Next action: Keep VAULT maintenance reachable through repo-owned SSH helpers and route specific config drift through the named LiteLLM and Prometheus packets instead of generic host-state edits.

## Promotion Criteria

| Criterion | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `live_surface_mapping_complete` | `met` | Every live DEV, WORKSHOP, FOUNDRY, and VAULT runtime surface relevant to Athanor has one declared ownership lane. | `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `vault_operator_access_non_browser` | `met` | VAULT maintenance must be reachable through repo-owned helpers instead of depending on the browser terminal. | `scripts/vault-ssh.py`, `scripts/ssh-vault.ps1`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `dashboard_shadow_unit_retired_or_recovery_only` | `met` | The inactive athanor-dashboard.service unit must be explicitly retired or downgraded to recovery-only so it cannot be mistaken for the active dashboard deployment path. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `repo_to_runtime_sync_packet_explicit` | `met` | The code path from C:/Athanor to /home/shaun/repos/athanor must have one explicit sync packet with verification and rollback instead of generic dirty-repo drift. | `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `opt_root_deploy_contract_complete` | `met` | Each active /opt/athanor surface on DEV, WORKSHOP, and FOUNDRY must declare source path, deploy mode, verification, and rollback contract. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |

## Execution Packets

| Packet | Status | Lane | Approval type | Goal |
| --- | --- | --- | --- | --- |
| `dev-runtime-repo-sync-packet` | `ready_for_approval` | `dev-runtime-repo-systemd` | `runtime_host_reconfiguration` | Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone. |
| `dev-dashboard-shadow-retirement-packet` | `executed` | `dev-dashboard-compose` | `systemd_runtime_change` | Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path. |
| `dev-dashboard-compose-deploy-packet` | `executed` | `dev-dashboard-compose` | `runtime_host_reconfiguration` | Make the active /opt/athanor/dashboard compose lane explicit so dashboard updates replace the governed compose build context instead of relying on remembered manual copy steps. |
| `dev-heartbeat-opt-deploy-packet` | `executed` | `dev-heartbeat-opt` | `runtime_host_reconfiguration` | Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps. |
| `foundry-agents-compose-deploy-packet` | `executed` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes. |
| `foundry-vllm-compose-reconciliation-packet` | `ready_for_approval` | `foundry-vllm-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/vllm compose root with implementation authority so the FOUNDRY coder lane, coordinator tuning, and extra runtime-only services stop drifting silently. |
| `workshop-control-surface-compose-reconciliation-packet` | `ready_for_approval` | `workshop-control-surface-compose` | `runtime_host_reconfiguration` | Reconcile the live Workshop dashboard-shadow compose root with implementation authority now that the source contract explicitly includes the active ws-pty-bridge service and the correct worker lane URL. |
| `workshop-vllm-compose-reconciliation-packet` | `ready_for_approval` | `workshop-vllm-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/vllm-node2 compose root with implementation authority so the Workshop worker lane stops carrying ungoverned image and launch-flag drift. |
| `vault-litellm-config-reconciliation-packet` | `ready_for_approval` | `vault-litellm-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/litellm/config.yaml file with implementation authority so the coder lane and other routed model definitions stop drifting independently of the repo. |
| `vault-prometheus-config-reconciliation-packet` | `ready_for_approval` | `vault-prometheus-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/prometheus/prometheus.yml file with implementation authority so monitoring truth stops drifting across stale shadow targets, extra jobs, and outdated node labels. |
