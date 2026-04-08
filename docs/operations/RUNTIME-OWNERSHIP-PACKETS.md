# Runtime Ownership Packets

Generated from `config/automation-backbone/runtime-ownership-packets.json`, `config/automation-backbone/runtime-ownership-contract.json`, and the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Registry version: `2026-04-08.1`
- Cached truth snapshot: `2026-04-08T02:49:45.200756+00:00`
- Packets tracked: `10`

| Packet | Status | Lane | Approval type | Goal |
| --- | --- | --- | --- | --- |
| `dev-runtime-repo-sync-packet` | `ready_for_approval` | `dev-runtime-repo-systemd` | `runtime_host_reconfiguration` | Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone. |
| `dev-dashboard-shadow-retirement-packet` | `executed` | `dev-dashboard-compose` | `systemd_runtime_change` | Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path. |
| `dev-dashboard-compose-deploy-packet` | `executed` | `dev-dashboard-compose` | `runtime_host_reconfiguration` | Make the active /opt/athanor/dashboard compose lane explicit so dashboard updates replace the governed compose build context instead of relying on remembered manual copy steps. |
| `dev-heartbeat-opt-deploy-packet` | `executed` | `dev-heartbeat-opt` | `runtime_host_reconfiguration` | Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps. |
| `foundry-agents-compose-deploy-packet` | `executed` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes. |
| `foundry-vllm-compose-reconciliation-packet` | `executed` | `foundry-vllm-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/vllm compose root onto the deterministic pinned image athanor/vllm:qwen35-20260315 so the FOUNDRY coordinator and coder lanes stop drifting by host-local floating image state. |
| `workshop-control-surface-compose-reconciliation-packet` | `ready_for_approval` | `workshop-control-surface-compose` | `runtime_host_reconfiguration` | Reconcile the live Workshop dashboard-shadow compose root with implementation authority now that the source contract explicitly includes the active ws-pty-bridge service and the correct worker lane URL. |
| `workshop-vllm-compose-reconciliation-packet` | `executed` | `workshop-vllm-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/vllm-node2 compose root onto the deterministic pinned image athanor/vllm:qwen35-20260315 so the Workshop worker lane stops drifting by host-local floating image state. |
| `vault-litellm-config-reconciliation-packet` | `ready_for_approval` | `vault-litellm-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/litellm/config.yaml file with implementation authority so the coder lane and other routed model definitions stop drifting independently of the repo. |
| `vault-prometheus-config-reconciliation-packet` | `executed` | `vault-prometheus-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/prometheus/prometheus.yml file with implementation authority so monitoring truth stops drifting across stale shadow targets, extra jobs, and outdated node labels. |

## dev-runtime-repo-sync-packet

- Label: `DEV runtime repo sync packet`
- Status: `ready_for_approval`
- Lane: `dev-runtime-repo-systemd`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone.
- Lane next action: Re-run the dev-runtime-repo-sync-packet after the current implementation-authority tranche settles; the 2026-04-07 live probe showed /home/shaun/repos/athanor back on commit d7b25c8 with generated-artifact drift, so the lane is open again even though the earlier sync path was proven.
- Backup root: `/home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>`
- Evidence: `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/sync_dev_runtime_repo.py`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `.` | `/home/shaun/repos/athanor` | `athanor-brain.service`, `athanor-classifier.service`, `athanor-quality-gate.service`, `athanor-sentinel.service`, `athanor-overnight.service` |

### Live evidence

- DEV runtime dirty file count: `13`

### Preflight Commands

- python scripts/validate_platform_contract.py
- python scripts/sync_dev_runtime_repo.py
- python scripts/sync_dev_runtime_repo.py --cleanup-only
- ssh dev "git -C /home/shaun/repos/athanor rev-parse --short HEAD && git -C /home/shaun/repos/athanor status --short | wc -l"
- ssh dev "systemctl show athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service athanor-overnight.service --property=WorkingDirectory,ExecStart --no-pager"

### Exact Steps

- Create a timestamped backup root under /home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>.
- Dry-run the governed sync with python scripts/sync_dev_runtime_repo.py and confirm the target temp branch, backup branch, and backup root.
- Capture the pre-sync DEV repo state both as a timestamped archive and as a timestamped backup branch before any reset.
- Push the approved implementation commit to a temporary ref in /home/shaun/repos/athanor/.git from implementation authority instead of copying files ad hoc.
- Reset DEV main to that approved mirror commit so tracked files and new tracked paths match implementation authority exactly.
- Clean leftover pre-sync residue that is not present in the approved commit, then restart only the repo-root services that actually changed.
- Prune all consumed runtime-sync/* refs immediately after the reset and retain only the newest 3 backup/runtime-sync-* branches plus the newest 3 timestamped backup directories under the runtime-repo-sync backup root.
- Refresh the truth snapshot and generated reports immediately after the sync.

### Verification Commands

- ssh dev "cd /home/shaun/repos/athanor && git status --short | wc -l && git rev-parse --short HEAD"
- ssh dev "systemctl is-active athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service athanor-overnight.service"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore DEV main from the timestamped backup branch or archive captured before the mirror reset.
- Restart only the affected repo-root services after the restore.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## dev-dashboard-shadow-retirement-packet

- Label: `DEV dashboard shadow retirement packet`
- Status: `executed`
- Lane: `dev-dashboard-compose`
- Approval type: `systemd_runtime_change` (Systemd runtime change)
- Host: `dev`
- Goal: Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path.
- Lane next action: Use the dev-dashboard-compose-deploy-packet and scripts/deploy-dashboard.sh as the only ordinary dashboard update path; keep athanor-dashboard.service masked as a recovery-only shadow.
- Backup root: `/home/shaun/.athanor/backups/runtime-ownership/dashboard-shadow/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/OPERATOR-SURFACE-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

- Target units: `athanor-dashboard.service`

### Live evidence

- Legacy service state: `inactive` / `dead`
- Legacy unit file state: `masked`
- Legacy fragment path: `/etc/systemd/system/athanor-dashboard.service`
- Container running: `True`
- Canonical probe status: `200`

### Preflight Commands

- ssh dev "systemctl cat athanor-dashboard.service > /home/shaun/.athanor/backups/runtime-ownership/dashboard-shadow/<timestamp>/athanor-dashboard.service"
- ssh dev "journalctl -u athanor-dashboard.service -n 200 --no-pager > /home/shaun/.athanor/backups/runtime-ownership/dashboard-shadow/<timestamp>/athanor-dashboard.service.journal.log"
- ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps && systemctl show athanor-dashboard.service --property=LoadState,ActiveState,SubState,UnitFileState,FragmentPath --no-pager"

### Exact Steps

- Back up the current unit file and recent journal before any mutation.
- Disable and mask athanor-dashboard.service so it cannot be mistaken for an ordinary dashboard start path.
- If the retained unit file is not needed for recovery, move it out of the active systemd estate into the timestamped backup root; otherwise keep only the masked recovery copy.
- Reload systemd and leave the active /opt/athanor/dashboard compose lane untouched.

### Verification Commands

- ssh dev "systemctl show athanor-dashboard.service --property=LoadState,ActiveState,SubState,UnitFileState --no-pager"
- ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps"
- ssh dev "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/ && curl -sk -o /dev/null -w '%{http_code}' https://athanor.local/"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report operator_surfaces --report runtime_ownership --report runtime_ownership_packets

### Rollback Steps

- Unmask athanor-dashboard.service if the rollback requires the legacy recovery path.
- Restore the backed up unit file into the active systemd estate if it was moved.
- Reload systemd and verify the compose lane still serves the dashboard before considering any legacy start path.

## dev-dashboard-compose-deploy-packet

- Label: `DEV command center compose deploy packet`
- Status: `executed`
- Lane: `dev-dashboard-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Make the active /opt/athanor/dashboard compose lane explicit so dashboard updates replace the governed compose build context instead of relying on remembered manual copy steps.
- Lane next action: Use the dev-dashboard-compose-deploy-packet and scripts/deploy-dashboard.sh as the only ordinary dashboard update path; keep athanor-dashboard.service masked as a recovery-only shadow.
- Backup root: `/opt/athanor/backups/dashboard/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/OPERATOR-SURFACE-REPORT.md`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/TRUTH-DRIFT-REPORT.md`, `scripts/deploy-dashboard.sh`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/dashboard` | `/opt/athanor/dashboard` | `athanor-dashboard` |

### Preflight Commands

- cd projects/dashboard && npm run typecheck
- cd projects/dashboard && npm run build
- ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps dashboard"
- ssh dev "test -d /opt/athanor/dashboard"
- ssh dev "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/api/operator/session && curl -sk -o /dev/null -w '%{http_code}' https://athanor.local/api/operator/session"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/dashboard/<timestamp> and back up the current /opt/athanor/dashboard bundle before replacement.
- Run scripts/deploy-dashboard.sh so the active compose build context is replaced from implementation authority.
- Let the script rebuild and recreate the dashboard service from the governed /opt/athanor/dashboard compose root instead of editing the live container by hand.
- Refresh truth inventory and reports immediately after the rollout.

### Verification Commands

- ssh dev "docker compose -f /opt/athanor/dashboard/docker-compose.yml ps dashboard"
- ssh dev "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/api/operator/session && curl -sk -o /dev/null -w '%{http_code}' https://athanor.local/api/operator/session"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report operator_surfaces --report repo_roots --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/dashboard bundle from /opt/athanor/backups/dashboard/<timestamp>.
- Rebuild and restart the dashboard service from the restored compose root.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## dev-heartbeat-opt-deploy-packet

- Label: `DEV heartbeat /opt deploy packet`
- Status: `executed`
- Lane: `dev-heartbeat-opt`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps.
- Lane next action: Use the executed heartbeat deploy packet as the governed replacement path for future /opt/athanor/heartbeat updates.
- Backup root: `/opt/athanor/backups/heartbeat/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `scripts/node-heartbeat.py` | `/opt/athanor/heartbeat/node-heartbeat.py` | `athanor-heartbeat.service` |

### Live evidence

- Deployed script exists: `True`
- Implementation matches deploy root: `True`
- Host-local env exists: `True`
- Runtime venv exists: `True`

### Preflight Commands

- ssh dev "systemctl cat athanor-heartbeat.service | sed -n '1,120p'"
- ssh dev "test -f /opt/athanor/heartbeat/node-heartbeat.py && sha256sum /opt/athanor/heartbeat/node-heartbeat.py"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/heartbeat/<timestamp> and copy the current node-heartbeat.py there before replacement.
- Replace only /opt/athanor/heartbeat/node-heartbeat.py from implementation authority; do not overwrite the host-local env file or the runtime venv as part of this packet.
- Restart athanor-heartbeat.service after the script replacement.
- Refresh the truth snapshot and generated reports immediately after the restart.

### Verification Commands

- ssh dev "systemctl is-active athanor-heartbeat.service && systemctl show athanor-heartbeat.service --property=ExecStart,EnvironmentFiles --no-pager"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up node-heartbeat.py from /opt/athanor/backups/heartbeat/<timestamp>.
- Restart athanor-heartbeat.service.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## foundry-agents-compose-deploy-packet

- Label: `FOUNDRY athanor-agents compose deploy packet`
- Status: `executed`
- Lane: `foundry-agents-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes.
- Lane next action: Use the foundry-agents-compose-deploy-packet and scripts/deploy-agents.sh as the only ordinary update path; do not hot-patch site-packages in the running container.
- Backup root: `/opt/athanor/backups/agents/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/TRUTH-DRIFT-REPORT.md`, `scripts/deploy-agents.sh`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/agents/Dockerfile` | `/opt/athanor/agents/Dockerfile` | `athanor-agents` |
| `projects/agents/pyproject.toml` | `/opt/athanor/agents/pyproject.toml` | `athanor-agents` |
| `projects/agents/docker-compose.yml` | `/opt/athanor/agents/docker-compose.yml` | `athanor-agents` |
| `projects/agents/config/subscription-routing-policy.yaml` | `/opt/athanor/agents/config/subscription-routing-policy.yaml` | `athanor-agents` |
| `projects/agents/src/athanor_agents` | `/opt/athanor/agents/src/athanor_agents` | `athanor-agents` |

### Live evidence

- Compose root matches expected: `True`
- Build root clean: `True`
- Nested source dir present: `False`
- bak-codex files: none
- Container running: `True`
- Container status: `Up 26 hours`
- Runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`

### Preflight Commands

- python scripts/validate_platform_contract.py
- ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"
- ssh foundry "docker inspect athanor-agents --format '{{.Config.Image}}|{{.State.Status}}|{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}|{{index .Config.Labels \"com.docker.compose.project.config_files\"}}'"
- ssh foundry "docker exec athanor-agents python3 -c \"import json, pathlib, athanor_agents, athanor_agents.server as server; print(json.dumps({'module': str(pathlib.Path(athanor_agents.__file__).resolve()), 'server': str(pathlib.Path(server.__file__).resolve())}))\""

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/agents/<timestamp> and back up the current /opt/athanor/agents bundle before replacement.
- Remove known runtime-root pollution from the staged build root only inside the approved maintenance window, including nested /opt/athanor/agents/src/athanor_agents/athanor_agents and stale *.bak-codex files if present.
- Run scripts/deploy-agents.sh so the full compose build context is replaced from implementation authority: src/, config/, Dockerfile, pyproject.toml, and docker-compose.yml.
- Let the script rebuild and recreate athanor-agents from the governed /opt/athanor/agents compose root instead of patching /usr/local/lib/python3.12/site-packages by hand.
- Refresh truth inventory and reports immediately after the rollout.

### Verification Commands

- ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"
- ssh foundry "curl -sS http://localhost:9000/health"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/agents bundle from /opt/athanor/backups/agents/<timestamp>.
- Rebuild and restart athanor-agents from the restored compose root.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## foundry-vllm-compose-reconciliation-packet

- Label: `FOUNDRY vLLM compose reconciliation packet`
- Status: `executed`
- Lane: `foundry-vllm-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Reconcile the live /opt/athanor/vllm compose root onto the deterministic pinned image athanor/vllm:qwen35-20260315 so the FOUNDRY coordinator and coder lanes stop drifting by host-local floating image state.
- Lane next action: Keep the FOUNDRY vLLM lane pinned to athanor/vllm:qwen35-20260315 and treat any future image or compose change as a deliberate packet-backed rollout; the 2026-04-07 reprobe showed healthy coordinator and coder lanes on the pinned artifact.
- Backup root: `/opt/athanor/backups/vllm/<timestamp>`
- Evidence: `reports/deployment-drift/foundry-vllm.diff`, `reports/rendered/foundry-vllm.rendered.yml`, `reports/live/foundry-vllm.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/foundry-vllm.rendered.yml` | `/opt/athanor/vllm/docker-compose.yml` | `vllm-coordinator`, `vllm-coder`, `vllm-vlm` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- ssh foundry "cd /opt/athanor/vllm && docker compose ps"
- ssh foundry "docker inspect vllm-coder --format '{{json .Config.Cmd}}'"
- ssh foundry "test -f /opt/athanor/vllm/docker-compose.yml && sed -n '1,220p' /opt/athanor/vllm/docker-compose.yml"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/vllm/<timestamp> and back up the current /opt/athanor/vllm/docker-compose.yml before replacement.
- Re-render the canonical compose file through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Promote the deterministic athanor/vllm:qwen35-20260315 artifact to FOUNDRY so the coordinator and coder lanes use the same known-good image lineage as Workshop instead of a host-local floating qwen35 tag.
- Replace /opt/athanor/vllm/docker-compose.yml from the rendered canonical artifact inside the approved maintenance window.
- Recreate only the affected vLLM services from the governed compose root, then refresh drift evidence immediately.

### Verification Commands

- ssh foundry "cd /opt/athanor/vllm && docker compose ps"
- ssh foundry "curl -sS http://localhost:8000/v1/models && curl -sS http://localhost:8006/v1/models"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/vllm/docker-compose.yml from /opt/athanor/backups/vllm/<timestamp>.
- Recreate the affected vLLM services from the restored compose root.
- Re-run the deployment-drift audit and validator to confirm rollback.

## workshop-control-surface-compose-reconciliation-packet

- Label: `WORKSHOP control-surface compose reconciliation packet`
- Status: `ready_for_approval`
- Lane: `workshop-control-surface-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `workshop`
- Goal: Reconcile the live Workshop dashboard-shadow compose root with implementation authority now that the source contract explicitly includes the active ws-pty-bridge service and the correct worker lane URL.
- Lane next action: Keep the live ws-pty bridge healthy but leave the Workshop dashboard-shadow compose root in ready-for-approval state until the workshop-control-surface-compose-reconciliation-packet is executed; the lane is still pending because workshop-dashboard.live.yml continues to differ from implementation authority.
- Backup root: `/opt/athanor/backups/dashboard-shadow/<timestamp>`
- Evidence: `reports/deployment-drift/workshop-dashboard.diff`, `reports/rendered/workshop-dashboard.rendered.yml`, `reports/live/workshop-dashboard.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/dashboard` | `/opt/athanor/dashboard` | `athanor-dashboard`, `athanor-ws-pty-bridge` |
| `projects/ws-pty-bridge` | `/opt/athanor/ws-pty-bridge` | `athanor-ws-pty-bridge` |
| `reports/rendered/workshop-dashboard.rendered.yml` | `/opt/athanor/dashboard/docker-compose.yml` | `athanor-dashboard`, `athanor-ws-pty-bridge` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- ssh workshop "cd /opt/athanor/dashboard && docker compose ps"
- ssh workshop "docker inspect athanor-ws-pty-bridge --format '{{.Name}}|{{.State.Status}}|{{.Config.Image}}'"
- ssh workshop "test -f /opt/athanor/dashboard/docker-compose.yml && sed -n '1,220p' /opt/athanor/dashboard/docker-compose.yml"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/dashboard-shadow/<timestamp> and back up the current /opt/athanor/dashboard compose bundle plus /opt/athanor/ws-pty-bridge source before replacement.
- Re-render the Workshop control-surface compose file through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Replace the Workshop dashboard-shadow source bundle and ws-pty-bridge source bundle from implementation authority during the approved maintenance window.
- Replace /opt/athanor/dashboard/docker-compose.yml from the rendered canonical artifact and keep the dashboard container explicitly recovery-only in operator posture.
- Recreate the affected Workshop control-surface services and refresh deployment-drift evidence immediately.

### Verification Commands

- ssh workshop "cd /opt/athanor/dashboard && docker compose ps"
- ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3100/health && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3001/"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/dashboard compose bundle and /opt/athanor/ws-pty-bridge source from /opt/athanor/backups/dashboard-shadow/<timestamp>.
- Recreate the affected Workshop control-surface services from the restored bundle.
- Re-run the deployment-drift audit and validator to confirm rollback.

## workshop-vllm-compose-reconciliation-packet

- Label: `WORKSHOP vLLM compose reconciliation packet`
- Status: `executed`
- Lane: `workshop-vllm-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `workshop`
- Goal: Reconcile the live /opt/athanor/vllm-node2 compose root onto the deterministic pinned image athanor/vllm:qwen35-20260315 so the Workshop worker lane stops drifting by host-local floating image state.
- Lane next action: Keep the Workshop worker pinned to athanor/vllm:qwen35-20260315 and treat future image or launch-flag changes as deliberate packet-backed rollouts; the 2026-04-07 reprobe showed the worker healthy on the pinned artifact.
- Backup root: `/opt/athanor/backups/vllm-node2/<timestamp>`
- Evidence: `reports/deployment-drift/workshop-vllm.diff`, `reports/rendered/workshop-vllm.rendered.yml`, `reports/live/workshop-vllm.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/workshop-vllm.rendered.yml` | `/opt/athanor/vllm-node2/docker-compose.yml` | `vllm-node2` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- ssh workshop "cd /opt/athanor/vllm-node2 && docker compose ps"
- ssh workshop "docker inspect vllm-node2 --format '{{json .Config.Cmd}}'"
- ssh workshop "test -f /opt/athanor/vllm-node2/docker-compose.yml && sed -n '1,220p' /opt/athanor/vllm-node2/docker-compose.yml"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/vllm-node2/<timestamp> and back up the current /opt/athanor/vllm-node2 compose bundle before replacement.
- Re-render the canonical Workshop vLLM compose file through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Promote the deterministic athanor/vllm:qwen35-20260315 image on Workshop from the last known-good custom lineage, including the DeltaNet compatibility patch needed by the Qwen3.5 worker lane.
- Replace /opt/athanor/vllm-node2/docker-compose.yml from the rendered canonical artifact during the approved maintenance window.
- Recreate the Workshop worker container and refresh deployment-drift evidence immediately.

### Verification Commands

- ssh workshop "cd /opt/athanor/vllm-node2 && docker compose ps"
- ssh workshop "curl -sS http://127.0.0.1:8010/v1/models"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/vllm-node2 compose bundle from /opt/athanor/backups/vllm-node2/<timestamp>.
- Recreate the Workshop worker container from the restored bundle.
- Re-run the deployment-drift audit and validator to confirm rollback.

## vault-litellm-config-reconciliation-packet

- Label: `VAULT LiteLLM config reconciliation packet`
- Status: `ready_for_approval`
- Lane: `vault-litellm-config`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `vault`
- Goal: Reconcile the live /mnt/user/appdata/litellm/config.yaml file with implementation authority so the coder lane and other routed model definitions stop drifting independently of the repo.
- Lane next action: Keep the VAULT LiteLLM config lane in ready-for-approval state until the live config stops differing from implementation authority; the current packet remains separate from the missing-secret provider-auth repair and the 2026-04-07 drift evidence still shows config divergence.
- Backup root: `/mnt/user/appdata/litellm/backups/config-reconcile/<timestamp>`
- Evidence: `reports/deployment-drift/vault-litellm.diff`, `reports/rendered/vault-litellm-config.rendered.yaml`, `reports/live/vault-litellm-config.live.yaml`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/vault-litellm-config.rendered.yaml` | `/mnt/user/appdata/litellm/config.yaml` | `litellm` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/vault-ssh.py "docker inspect litellm --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"
- python scripts/vault-ssh.py "test -f /mnt/user/appdata/litellm/config.yaml && sed -n '1,220p' /mnt/user/appdata/litellm/config.yaml"
- python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json

### Exact Steps

- Create a timestamped backup root under /mnt/user/appdata/litellm/backups/config-reconcile/<timestamp> and back up the current config.yaml plus a docker inspect snapshot of the litellm container before replacement.
- Re-render the canonical LiteLLM config through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Replace only /mnt/user/appdata/litellm/config.yaml during the approved maintenance window; keep provider-secret delivery decisions under the separate VAULT auth-repair packet instead of mixing them into this config reconcile pass.
- Recreate or restart only the litellm container after the config replacement.
- Refresh both the deployment-drift evidence and the VAULT env audit immediately after restart.

### Verification Commands

- python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4000/health"
- python scripts/vault_litellm_env_audit.py --write reports/truth-inventory/vault-litellm-env-audit.json
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /mnt/user/appdata/litellm/config.yaml and saved container definition from /mnt/user/appdata/litellm/backups/config-reconcile/<timestamp>.
- Restart the litellm container with the restored config.
- Re-run the VAULT env audit, deployment-drift audit, and validator to confirm rollback.

## vault-prometheus-config-reconciliation-packet

- Label: `VAULT Prometheus config reconciliation packet`
- Status: `executed`
- Lane: `vault-prometheus-config`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `vault`
- Goal: Reconcile the live /mnt/user/appdata/prometheus/prometheus.yml file with implementation authority so monitoring truth stops drifting across stale shadow targets, extra jobs, and outdated node labels.
- Lane next action: Keep the executed vault-prometheus-config-reconciliation-packet as the governed update path; the 2026-04-07 reprobe showed the Prometheus container healthy after the reconcile pass.
- Backup root: `/mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp>`
- Evidence: `reports/deployment-drift/vault-prometheus.diff`, `reports/rendered/vault-prometheus.rendered.yml`, `reports/live/vault-prometheus.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/vault-prometheus.rendered.yml` | `/mnt/user/appdata/prometheus/prometheus.yml` | `prometheus` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/vault-ssh.py "docker inspect prometheus --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"
- python scripts/vault-ssh.py "test -f /mnt/user/appdata/prometheus/prometheus.yml && sed -n '1,260p' /mnt/user/appdata/prometheus/prometheus.yml"
- python scripts/vault-ssh.py "curl -s http://127.0.0.1:9090/api/v1/targets | head -c 4000"

### Exact Steps

- Create a timestamped backup root under /mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp> and back up the current prometheus.yml plus a docker inspect snapshot of the prometheus container before replacement.
- Re-render the canonical Prometheus config through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Replace /mnt/user/appdata/prometheus/prometheus.yml during the approved maintenance window and keep any live-only targets only if they are explicitly reclassified into source truth later.
- Recreate or restart only the Prometheus container after the config replacement.
- Refresh deployment-drift evidence and confirm the active targets set no longer certifies stale Workshop shadow or outdated node labels.

### Verification Commands

- python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/-/healthy"
- python scripts/vault-ssh.py "curl -s http://127.0.0.1:9090/api/v1/targets | head -c 4000"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /mnt/user/appdata/prometheus/prometheus.yml and saved container definition from /mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp>.
- Restart the Prometheus container with the restored config.
- Re-run the deployment-drift audit and validator to confirm rollback.
