# Runtime Ownership Packets

Generated from `config/automation-backbone/runtime-ownership-packets.json`, `config/automation-backbone/runtime-ownership-contract.json`, and the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Registry version: `2026-04-16.2`
- Cached truth snapshot: `2026-04-16T23:02:10.691252+00:00`
- Packets tracked: `17`

| Packet | Status | Lane | Approval type | Goal |
| --- | --- | --- | --- | --- |
| `dev-runtime-repo-sync-packet` | `retired` | `dev-runtime-repo-systemd` | `runtime_host_reconfiguration` | Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone. |
| `dev-dashboard-shadow-retirement-packet` | `executed` | `dev-dashboard-compose` | `systemd_runtime_change` | Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path. |
| `dev-dashboard-compose-deploy-packet` | `executed` | `dev-dashboard-compose` | `runtime_host_reconfiguration` | Make the active /opt/athanor/dashboard compose lane explicit so dashboard updates replace the governed compose build context instead of relying on remembered manual copy steps. |
| `dev-heartbeat-opt-deploy-packet` | `executed` | `dev-heartbeat-opt` | `runtime_host_reconfiguration` | Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps. |
| `foundry-agents-compose-deploy-packet` | `executed` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes. |
| `foundry-graphrag-compose-deploy-packet` | `executed` | `foundry-graphrag-compose` | `runtime_host_reconfiguration` | Make the live /opt/athanor/graphrag compose root a governed knowledge-subsystem lane so GraphRAG rollout and rollback stop depending on remembered host-local steps. |
| `foundry-gpu-orchestrator-compose-deploy-packet` | `executed` | `foundry-gpu-orchestrator-compose` | `runtime_host_reconfiguration` | Keep the active /opt/athanor/gpu-orchestrator compose root aligned to implementation authority so host-local runtime identity does not drift away from the repo-owned coordinator and zone-routing contract. |
| `foundry-gpu-orchestrator-scheduler-state-rollout-packet` | `executed` | `foundry-gpu-orchestrator-compose` | `runtime_host_reconfiguration` | Roll out the bounded scheduler surface through the existing FOUNDRY GPU Orchestrator lane so live runtime explicitly proves both /scheduler/state and the governed mutation-route envelope instead of relying on source-only claims. |
| `foundry-watchdog-runtime-guard-rollout-packet` | `executed` | `foundry-watchdog-runtime-guard` | `runtime_host_reconfiguration` | Keep the Athanor-owned watchdog bundle under /opt/athanor/watchdog as the packet-backed live canary lane so monitoring, bounded restart controls, and rollback posture stay explicit while live remediation authority remains narrow. |
| `desk-goose-operator-shell-rollout-packet` | `executed` | `desk-goose-operator-shell` | `runtime_host_reconfiguration` | Roll out the bounded DESK Goose shell helper so the preferred Athanor shell path is pinned to the intended LiteLLM DeepSeek lane with explicit fallback behavior instead of relying on remembered workstation-local defaults. |
| `foundry-vllm-compose-reconciliation-packet` | `executed` | `foundry-vllm-compose` | `runtime_host_reconfiguration` | Reconcile the live FOUNDRY coordinator compose root and the llama-dolphin dolphin3-r1-24b coder runtime so the active coordinator and coder lanes stop drifting through host-local state. |
| `workshop-control-surface-compose-reconciliation-packet` | `executed` | `workshop-control-surface-compose` | `runtime_host_reconfiguration` | Reconcile the live Workshop dashboard-shadow compose root with implementation authority now that the source contract explicitly includes the active ws-pty-bridge service and the correct worker lane URL. |
| `workshop-vllm-compose-reconciliation-packet` | `executed` | `workshop-vllm-compose` | `runtime_host_reconfiguration` | Retire the stale /opt/athanor/vllm-node2 worker contract now that the pinned Workshop worker model directory is absent and the live Workshop data-plane is ComfyUI plus vllm-vision instead of a reachable :8010 worker lane. |
| `vault-litellm-config-reconciliation-packet` | `executed` | `vault-litellm-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/litellm/config.yaml file with implementation authority so the coder lane and other routed model definitions stop drifting independently of the repo. |
| `vault-prometheus-config-reconciliation-packet` | `executed` | `vault-prometheus-config` | `runtime_host_reconfiguration` | Reconcile the live /mnt/user/appdata/prometheus/prometheus.yml and alert-rules.yml files with implementation authority so monitoring truth stops drifting across stale shadow targets, extra jobs, and outdated node labels. |
| `dev-runtime-ssh-access-recovery-packet` | `executed` | `dev-runtime-state` | `runtime_host_reconfiguration` | Restore one governed DEV SSH access path so truth collection, runtime verification, and repo-root maintenance no longer depend on a broken alias or remembered fallback guesses. |
| `foundry-agents-runtime-alignment-packet` | `executed` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/agents source tree and imported `athanor_agents` module path with implementation authority when the truth collector reports a source/runtime mismatch. |

## dev-runtime-repo-sync-packet

- Label: `DEV runtime repo sync packet`
- Status: `retired`
- Lane: `dev-runtime-repo-systemd`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Make /home/shaun/repos/athanor a mirror-clean runtime repo that matches implementation authority instead of leaving DEV on a broad dirty clone.
- Lane next action: Keep the executed dev-runtime-repo-sync-packet as the governed resync path for future repo-root maintenance. The 2026-04-08 execution left /home/shaun/repos/athanor mirror-clean at commit 5148170 with athanor-brain, athanor-classifier, athanor-quality-gate, and athanor-sentinel healthy; athanor-overnight.service remains outside the immediate mirror-clean verification window because it rewrites tracked generated artifacts.
- Backup root: `/home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>`
- Evidence: `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/sync_dev_runtime_repo.py`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `.` | `/home/shaun/repos/athanor` | `athanor-brain.service`, `athanor-classifier.service`, `athanor-quality-gate.service`, `athanor-sentinel.service` |

### Live evidence

- DEV runtime dirty file count: `0`

### Preflight Commands

- python scripts/validate_platform_contract.py
- python scripts/sync_dev_runtime_repo.py
- python scripts/sync_dev_runtime_repo.py --cleanup-only
- ssh dev "git -C /home/shaun/repos/athanor rev-parse --short HEAD && git -C /home/shaun/repos/athanor status --short | wc -l"
- ssh dev "systemctl show athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service --property=WorkingDirectory,ExecStart --no-pager"

### Exact Steps

- Create a timestamped backup root under /home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>.
- Dry-run the governed sync with python scripts/sync_dev_runtime_repo.py and confirm the target temp branch, backup branch, and backup root.
- Capture the pre-sync DEV repo state both as a timestamped archive and as a timestamped backup branch before any reset.
- Push the approved implementation commit to a temporary ref in /home/shaun/repos/athanor/.git from implementation authority instead of copying files ad hoc.
- Reset DEV main to that approved mirror commit so tracked files and new tracked paths match implementation authority exactly.
- Clean leftover pre-sync residue that is not present in the approved commit, then restart only the long-running repo-root services that actually changed.
- Do not restart athanor-overnight.service in the immediate post-sync path; that timer-backed one-shot rewrites tracked truth artifacts and should remain outside the mirror-clean verification window.
- Prune all consumed runtime-sync/* refs immediately after the reset and retain only the newest 3 backup/runtime-sync-* branches plus the newest 3 timestamped backup directories under the runtime-repo-sync backup root.
- Refresh the truth snapshot and generated reports immediately after the sync.

### Verification Commands

- ssh dev "cd /home/shaun/repos/athanor && git status --short | wc -l && git rev-parse --short HEAD"
- ssh dev "systemctl is-active athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service"
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

- Deployed script exists: `False`
- Implementation matches deploy root: `False`
- Host-local env exists: `False`
- Runtime venv exists: `False`

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
- Lane next action: Keep `foundry-agents-compose-deploy-packet` as the ordinary update path, but treat the current blocker as the narrower `foundry-agents-runtime-alignment-packet`: prove the governed `/opt/athanor/agents/src/athanor_agents` tree matches the approved implementation tree and that the imported module path is only the image-layout result of that same build before any manual runtime patching or site-packages edits.
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
- Container status: `Up 3 hours`
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

## foundry-graphrag-compose-deploy-packet

- Label: `FOUNDRY GraphRAG compose deploy packet`
- Status: `executed`
- Lane: `foundry-graphrag-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Make the live /opt/athanor/graphrag compose root a governed knowledge-subsystem lane so GraphRAG rollout and rollback stop depending on remembered host-local steps.
- Lane next action: Keep the executed foundry-graphrag-compose-deploy-packet as the governed runtime update path for future GraphRAG changes; the runtime and promotion eval are already green, so the remaining boundary is packet review and adoption acceptance for widening beyond shadow-tier evidence.
- Backup root: `/opt/athanor/backups/graphrag/<timestamp>`
- Evidence: `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `C:/athanor-devstack/docs/promotion-packets/graphrag-hybrid-retrieval.md`, `C:/athanor-devstack/services/graphrag/README.md`, `C:/Athanor/reports/truth-inventory/graphrag-promotion-eval.json`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `services/graphrag` | `/opt/athanor/graphrag` | `athanor-graphrag` |

### Preflight Commands

- ssh foundry "cd /opt/athanor/graphrag && docker compose ps"
- ssh foundry "test -f /opt/athanor/graphrag/docker-compose.yml && sed -n '1,220p' /opt/athanor/graphrag/docker-compose.yml"
- ssh foundry "curl -sS --max-time 20 http://127.0.0.1:9300/health"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/graphrag/<timestamp> and back up the current /opt/athanor/graphrag bundle before replacement.
- Replace the full /opt/athanor/graphrag compose bundle from devstack implementation authority during the approved maintenance window instead of patching container files by hand.
- Rebuild and recreate only the athanor-graphrag container from the governed compose root.
- Re-run GraphRAG health verification, then run the governed promotion-eval contract so the rollout proves live /status and /query/hybrid behavior instead of relying on source-only recovery claims.
- Refresh truth/report surfaces immediately after the rollout.

### Verification Commands

- ssh foundry "cd /opt/athanor/graphrag && docker compose ps"
- ssh foundry "curl -sS --max-time 20 http://127.0.0.1:9300/health"
- python scripts/run_graphrag_promotion_eval.py
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/graphrag bundle from /opt/athanor/backups/graphrag/<timestamp>.
- Rebuild and restart athanor-graphrag from the restored compose root.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## foundry-gpu-orchestrator-compose-deploy-packet

- Label: `FOUNDRY GPU Orchestrator compose deploy packet`
- Status: `executed`
- Lane: `foundry-gpu-orchestrator-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Keep the active /opt/athanor/gpu-orchestrator compose root aligned to implementation authority so host-local runtime identity does not drift away from the repo-owned coordinator and zone-routing contract.
- Lane next action: Use scripts/deploy-gpu-orchestrator.sh as the governed update path for future FOUNDRY GPU Orchestrator changes; the bounded scheduler surface should roll through foundry-gpu-orchestrator-scheduler-state-rollout-packet so /scheduler/state, write-capability posture, and scheduler request/preload/release route presence are verified explicitly before the lane advances beyond offline proof.
- Backup root: `/opt/athanor/backups/gpu-orchestrator/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-gpu-orchestrator.sh`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/gpu-orchestrator/Dockerfile` | `/opt/athanor/gpu-orchestrator/Dockerfile` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/pyproject.toml` | `/opt/athanor/gpu-orchestrator/pyproject.toml` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/docker-compose.yml` | `/opt/athanor/gpu-orchestrator/docker-compose.yml` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/src/gpu_orchestrator` | `/opt/athanor/gpu-orchestrator/src/gpu_orchestrator` | `gpu-orchestrator` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- ssh foundry "cd /opt/athanor/gpu-orchestrator && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9200/health && curl -sS http://127.0.0.1:9200/zones"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/gpu-orchestrator/<timestamp> and back up the current /opt/athanor/gpu-orchestrator bundle before replacement.
- Run scripts/deploy-gpu-orchestrator.sh so the full compose build context is replaced from implementation authority: src/, Dockerfile, pyproject.toml, and docker-compose.yml.
- Let the script rebuild and recreate the gpu-orchestrator container from the governed /opt/athanor/gpu-orchestrator compose root instead of leaving runtime identity to host-local drift.
- Refresh truth inventory and deployment-drift evidence immediately after the rollout.

### Verification Commands

- ssh foundry "cd /opt/athanor/gpu-orchestrator && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9200/health && curl -sS http://127.0.0.1:9200/zones"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/gpu-orchestrator bundle from /opt/athanor/backups/gpu-orchestrator/<timestamp>.
- Rebuild and restart the gpu-orchestrator container from the restored compose root.
- Re-run the deployment-drift audit and validator to confirm rollback.

## foundry-gpu-orchestrator-scheduler-state-rollout-packet

- Label: `FOUNDRY GPU Orchestrator scheduler surface rollout packet`
- Status: `executed`
- Lane: `foundry-gpu-orchestrator-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Roll out the bounded scheduler surface through the existing FOUNDRY GPU Orchestrator lane so live runtime explicitly proves both /scheduler/state and the governed mutation-route envelope instead of relying on source-only claims.
- Lane next action: Use scripts/deploy-gpu-orchestrator.sh as the governed update path for future FOUNDRY GPU Orchestrator changes; the bounded scheduler surface should roll through foundry-gpu-orchestrator-scheduler-state-rollout-packet so /scheduler/state, write-capability posture, and scheduler request/preload/release route presence are verified explicitly before the lane advances beyond offline proof.
- Backup root: `/opt/athanor/backups/gpu-orchestrator/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/truth-inventory/gpu-scheduler-baseline-eval.json`, `reports/truth-inventory/gpu-scheduler-promotion-eval.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-gpu-orchestrator.sh`, `scripts/run_gpu_scheduler_baseline_eval.py`, `scripts/run_gpu_scheduler_promotion_eval.py`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/gpu-orchestrator/src/gpu_orchestrator` | `/opt/athanor/gpu-orchestrator/src/gpu_orchestrator` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/Dockerfile` | `/opt/athanor/gpu-orchestrator/Dockerfile` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/pyproject.toml` | `/opt/athanor/gpu-orchestrator/pyproject.toml` | `gpu-orchestrator` |
| `projects/gpu-orchestrator/docker-compose.yml` | `/opt/athanor/gpu-orchestrator/docker-compose.yml` | `gpu-orchestrator` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- python scripts/run_gpu_scheduler_baseline_eval.py
- ssh foundry "cd /opt/athanor/gpu-orchestrator && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9200/health && curl -sS http://127.0.0.1:9200/zones"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/gpu-orchestrator/<timestamp> and preserve the current /opt/athanor/gpu-orchestrator bundle before replacement.
- Run GPU_ORCH_EXPECT_SCHEDULER_STATE=1 GPU_ORCH_EXPECT_SCHEDULER_MUTATION_SURFACE=1 scripts/deploy-gpu-orchestrator.sh after the approved runtime expectation update. The packet-scoped expectation update is those two deploy-time env flags; no broader env-surface widening is implied. The governed compose lane should rebuild the container, wait for /scheduler/state, and verify the scheduler request/preload/release routes exist live as POST-only surfaces.
- Re-run the pinned baseline eval immediately after deploy so live runtime captures the bounded scheduler surface instead of relying only on generic health and zone probes.
- Run the bounded scheduler promotion-eval contract after the rollout; it should remain blocked until the live mutation surface is both present and write-enabled, but the post-deploy artifact must prove the governed scheduler delta landed cleanly.

### Verification Commands

- ssh foundry "cd /opt/athanor/gpu-orchestrator && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9200/health && curl -sS http://127.0.0.1:9200/zones && curl -sS http://127.0.0.1:9200/scheduler/state"
- ssh foundry "test \"$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9200/scheduler/request)\" = '405' && test \"$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9200/scheduler/preload)\" = '405' && test \"$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9200/scheduler/release)\" = '405'"
- python scripts/run_gpu_scheduler_baseline_eval.py
- python scripts/run_gpu_scheduler_promotion_eval.py
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/gpu-orchestrator bundle from /opt/athanor/backups/gpu-orchestrator/<timestamp>.
- Rebuild and restart the gpu-orchestrator container from the restored compose root.
- Re-run the baseline eval, promotion eval, deployment-drift audit, and validator to confirm the rollback returned the lane to the prior state.

## foundry-watchdog-runtime-guard-rollout-packet

- Label: `FOUNDRY watchdog runtime-guard rollout packet`
- Status: `executed`
- Lane: `foundry-watchdog-runtime-guard`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Keep the Athanor-owned watchdog bundle under /opt/athanor/watchdog as the packet-backed live canary lane so monitoring, bounded restart controls, and rollback posture stay explicit while live remediation authority remains narrow.
- Lane next action: Maintain the executed live canary as the packet-backed watchdog lane, keep operator-envelope and protected-service boundaries intact, and reopen only for a later production widening or rollback.
- Backup root: `/opt/athanor/backups/watchdog/<timestamp>`
- Evidence: `projects/agents/watchdog/README.md`, `projects/agents/tests/test_watchdog_runtime_guard.py`, `projects/agents/tests/test_watchdog_route_contract.py`, `reports/truth-inventory/watchdog-runtime-guard-formal-eval.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/OPERATOR_RUNBOOKS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/agents/watchdog` | `/opt/athanor/watchdog` | `athanor-watchdog` |

### Preflight Commands

- C:/Athanor/projects/agents/.venv/Scripts/python.exe -m pytest C:/Athanor/projects/agents/tests/test_watchdog_runtime_guard.py -q
- C:/Athanor/projects/agents/.venv/Scripts/python.exe -m pytest C:/Athanor/projects/agents/tests/test_watchdog_route_contract.py -q
- python scripts/validate_platform_contract.py
- ssh foundry "cd /opt/athanor/watchdog && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9301/health && curl -sS http://127.0.0.1:9301/status"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/watchdog/<timestamp> and preserve the current /opt/athanor/watchdog bundle before replacement.
- Sync the Athanor-owned projects/agents/watchdog bundle into /opt/athanor/watchdog without widening scope beyond the watchdog container and its compose root.
- Set WATCHDOG_INITIAL_PAUSED=false, WATCHDOG_MUTATIONS_ENABLED=true, WATCHDOG_RUNTIME_PACKET_ID=foundry-watchdog-runtime-guard-rollout-packet, and WATCHDOG_RUNTIME_PACKET_STATUS=executed so the service boots into the active canary posture.
- Rebuild and recreate only the athanor-watchdog container from the staged bundle, then verify /health and /status expose the open mutation gate, protected-service policy, and operator action contract.
- Attach post-activation evidence, including the live canary probe and a bounded operator-envelope restart proof, before treating the lane as ordinary adopted runtime.

### Verification Commands

- ssh foundry "cd /opt/athanor/watchdog && docker compose ps"
- ssh foundry "curl -sS http://127.0.0.1:9301/health && curl -sS http://127.0.0.1:9301/status"
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the prior /opt/athanor/watchdog bundle from /opt/athanor/backups/watchdog/<timestamp>.
- Recreate the athanor-watchdog container from the restored bundle with WATCHDOG_MUTATIONS_ENABLED=false and WATCHDOG_INITIAL_PAUSED=true so the service returns to guarded monitoring posture.
- Re-run the watchdog tests, runtime-ownership reports, and validator sequence to confirm the rollback restored the prior bounded surface.

## desk-goose-operator-shell-rollout-packet

- Label: `DESK Goose operator-shell rollout packet`
- Status: `executed`
- Lane: `desk-goose-operator-shell`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `desk`
- Goal: Roll out the bounded DESK Goose shell helper so the preferred Athanor shell path is pinned to the intended LiteLLM DeepSeek lane with explicit fallback behavior instead of relying on remembered workstation-local defaults.
- Lane next action: Treat the DESK Goose helper as the adopted bounded shell path; keep future shell-path changes packet-backed through desk-goose-operator-shell-rollout-packet instead of drifting through workstation-local defaults.
- Backup root: `C:/Users/Shaun/AppData/Local/Athanor/backups/operator-shell/<timestamp>`
- Evidence: `reports/truth-inventory/goose-operator-shell-formal-eval.json`, `reports/truth-inventory/goose-operator-shell-promptfoo-results.json`, `reports/truth-inventory/goose-boundary-evidence.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/run-goose-athanor-shell.ps1`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `scripts/run-goose-athanor-shell.ps1` | `C:/Users/Shaun/AppData/Local/Athanor/operator-shell/run-goose-athanor-shell.ps1` | `goose-cli` |

### Preflight Commands

- powershell -ExecutionPolicy Bypass -File .\scripts\run-goose-athanor-shell.ps1 run --text "Reply with READY only." --no-session --no-profile --quiet --output-format text --max-turns 1
- python scripts/run_capability_pilot_formal_eval.py --run-id goose-operator-shell-lane-eval-2026q2
- python scripts/validate_platform_contract.py

### Exact Steps

- Create a timestamped backup root under C:/Users/Shaun/AppData/Local/Athanor/backups/operator-shell/<timestamp> and preserve any prior DESK Goose helper before replacement.
- Copy scripts/run-goose-athanor-shell.ps1 into the operator-local path so the bounded DESK Goose shell helper becomes the governed launch path for Athanor shell trials instead of relying on the weaker local default provider/model selection.
- Keep the rollout scoped to provider pinning, fallback behavior, and bounded helper plumbing; do not mutate Goose tokens, provider secrets, or unreviewed profile state as part of this packet.
- Re-run the Goose formal eval contract after the helper is in place so the shadow-tier packet continues to point at current evidence.

### Verification Commands

- powershell -ExecutionPolicy Bypass -File .\scripts\run-goose-athanor-shell.ps1 run --text "Reply with READY only." --no-session --no-profile --quiet --output-format text --max-turns 1
- python scripts/run_capability_pilot_formal_eval.py --run-id goose-operator-shell-lane-eval-2026q2
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Remove the DESK Goose helper from the operator-local path and restore any prior helper or shell default captured in the timestamped backup root.
- Return the preferred shell posture to direct terminal plus specialist CLI lanes if the Goose helper rollout regresses shell behavior or obscures fallback boundaries.
- Re-run the Goose formal eval and validator sequence to confirm the rollback restored the prior shell path.

## foundry-vllm-compose-reconciliation-packet

- Label: `FOUNDRY coder runtime reconciliation packet`
- Status: `executed`
- Lane: `foundry-vllm-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Reconcile the live FOUNDRY coordinator compose root and the llama-dolphin dolphin3-r1-24b coder runtime so the active coordinator and coder lanes stop drifting through host-local state.
- Lane next action: Keep the FOUNDRY compose root packet-backed, but treat :8100 as the canonical healthy text lane and :8000 as degraded nonblocking lineage until a future bounded packet either restores real completion health or retires the coordinator lane explicitly.
- Backup root: `/opt/athanor/backups/vllm/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/foundry-vllm.rendered.yml`, `reports/live/foundry-vllm.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/foundry-vllm.rendered.yml` | `/opt/athanor/vllm/docker-compose.yml` | `vllm-coordinator`, `llama-dolphin`, `vllm-vlm` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- ssh foundry "cd /opt/athanor/vllm && docker compose ps"
- ssh foundry "docker inspect llama-dolphin --format '{{json .Config.Cmd}}'"
- ssh foundry "test -f /opt/athanor/vllm/docker-compose.yml && sed -n '1,220p' /opt/athanor/vllm/docker-compose.yml"

### Exact Steps

- Create a timestamped backup root under /opt/athanor/backups/vllm/<timestamp> and back up the current /opt/athanor/vllm/docker-compose.yml before replacement.
- Re-render the canonical compose file through the governed deployment-drift audit or render_ansible_template.py so the replacement artifact matches implementation authority exactly.
- Promote the deterministic coordinator artifact to FOUNDRY and keep the llama-dolphin dolphin3-r1-24b coder runtime pinned to its governed host configuration instead of drifting through host-local edits.
- Replace /opt/athanor/vllm/docker-compose.yml from the rendered canonical artifact inside the approved maintenance window.
- Recreate only the affected coordinator and coder services from the governed runtime roots, then refresh drift evidence immediately.

### Verification Commands

- ssh foundry "cd /opt/athanor/vllm && docker compose ps"
- ssh foundry "curl -sS http://localhost:8000/v1/models && curl -sS http://localhost:8100/v1/models"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/vllm/docker-compose.yml from /opt/athanor/backups/vllm/<timestamp>.
- Recreate the affected vLLM services from the restored compose root.
- Re-run the deployment-drift audit and validator to confirm rollback.

## workshop-control-surface-compose-reconciliation-packet

- Label: `WORKSHOP control-surface compose reconciliation packet`
- Status: `executed`
- Lane: `workshop-control-surface-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `workshop`
- Goal: Reconcile the live Workshop dashboard-shadow compose root with implementation authority now that the source contract explicitly includes the active ws-pty-bridge service and the correct worker lane URL.
- Lane next action: Keep the live Workshop dashboard shadow and ws-pty bridge healthy and treat any future compose or source change as packet-backed runtime work; the 2026-04-08 backup-first reconcile pass synced the source bundles, replaced /opt/athanor/dashboard/docker-compose.yml from implementation authority, and re-probed both :3001 and :3100/health at 200.
- Backup root: `/opt/athanor/backups/dashboard-shadow/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/workshop-dashboard.rendered.yml`, `reports/live/workshop-dashboard.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

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
- Goal: Retire the stale /opt/athanor/vllm-node2 worker contract now that the pinned Workshop worker model directory is absent and the live Workshop data-plane is ComfyUI plus vllm-vision instead of a reachable :8010 worker lane.
- Lane next action: Keep this lane retired and rely on Workshop ComfyUI plus vllm-vision as the active Workshop data-plane surfaces unless a future packet deliberately restores a real :8010 worker runtime.
- Backup root: `/opt/athanor/backups/vllm-node2/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/workshop-vllm.rendered.yml`, `reports/live/workshop-vllm.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

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

- Preserve the governed /opt/athanor/vllm-node2 compose lineage as historical evidence instead of treating it as an active runtime target.
- Retire the Workshop worker lane in Athanor source truth because /mnt/vault/models/Qwen3.5-35B-A3B-AWQ-4bit is absent and the latest runtime reprobe confirmed the container crashes on startup.
- Use Workshop ComfyUI plus vllm-vision as the active creative and vision surfaces unless a future bounded packet intentionally restores a real :8010 worker lane.

### Verification Commands

- ssh workshop "docker ps -a --filter name=vllm-node2 --format 'table {{.Names}}\t{{.Status}}'"
- ssh workshop "ls -ld /mnt/vault/models /mnt/vault/models/Qwen3.5-35B-A3B-AWQ-4bit 2>/dev/null || true"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/vllm-node2 compose bundle from /opt/athanor/backups/vllm-node2/<timestamp> only if a future bounded packet intentionally revives a real worker lane.
- Recreate the Workshop worker container only after the missing model directory is restored or the lane is rebound to a new explicit model path.
- Re-run the deployment-drift audit and validator to confirm the restored lane is genuinely back before clearing retirement.

## vault-litellm-config-reconciliation-packet

- Label: `VAULT LiteLLM config reconciliation packet`
- Status: `executed`
- Lane: `vault-litellm-config`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `vault`
- Goal: Reconcile the live /mnt/user/appdata/litellm/config.yaml file with implementation authority so the coder lane and other routed model definitions stop drifting independently of the repo.
- Lane next action: Keep the executed VAULT LiteLLM config packet as the governed update path for future routing changes; the 2026-04-08 reprobe showed /mnt/user/appdata/litellm/config.yaml identical to implementation authority, the litellm container healthy, and provider-auth follow-through narrowed to the separate missing-secret and upstream-auth lane.
- Backup root: `/mnt/user/appdata/litellm/backups/config-reconcile/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/vault-litellm-config.rendered.yaml`, `reports/live/vault-litellm-config.live.yaml`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

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
- Goal: Reconcile the live /mnt/user/appdata/prometheus/prometheus.yml and alert-rules.yml files with implementation authority so monitoring truth stops drifting across stale shadow targets, extra jobs, and outdated node labels.
- Lane next action: Keep the executed vault-prometheus-config-reconciliation-packet as the governed update path; the 2026-04-08 reprobe showed both Prometheus config surfaces identical to implementation authority and the Prometheus container healthy after restart.
- Backup root: `/mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp>`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/vault-prometheus.rendered.yml`, `reports/rendered/vault-alert-rules.rendered.yml`, `reports/live/vault-prometheus.live.yml`, `reports/live/vault-alert-rules.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `reports/rendered/vault-prometheus.rendered.yml` | `/mnt/user/appdata/prometheus/prometheus.yml` | `prometheus` |
| `reports/rendered/vault-alert-rules.rendered.yml` | `/mnt/user/appdata/prometheus/alert-rules.yml` | `prometheus` |

### Preflight Commands

- python scripts/validate_platform_contract.py
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/vault-ssh.py "docker inspect prometheus --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"
- python scripts/vault-ssh.py "test -f /mnt/user/appdata/prometheus/prometheus.yml && sed -n '1,260p' /mnt/user/appdata/prometheus/prometheus.yml"
- python scripts/vault-ssh.py "test -f /mnt/user/appdata/prometheus/alert-rules.yml && sed -n '1,220p' /mnt/user/appdata/prometheus/alert-rules.yml"
- python scripts/vault-ssh.py "curl -s http://127.0.0.1:9090/api/v1/targets | head -c 4000"

### Exact Steps

- Create a timestamped backup root under /mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp> and back up the current prometheus.yml, alert-rules.yml, plus a docker inspect snapshot of the prometheus container before replacement.
- Re-render the canonical Prometheus config and alert-rules files through the governed deployment-drift audit or render_ansible_template.py so the replacement artifacts match implementation authority exactly.
- Replace /mnt/user/appdata/prometheus/prometheus.yml and /mnt/user/appdata/prometheus/alert-rules.yml during the approved maintenance window and keep any live-only targets only if they are explicitly reclassified into source truth later.
- Recreate or restart only the Prometheus container after the config replacement.
- Refresh deployment-drift evidence and confirm the active targets set no longer certifies stale Workshop shadow or outdated node labels.

### Verification Commands

- python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/-/healthy"
- python scripts/vault-ssh.py "curl -s http://127.0.0.1:9090/api/v1/targets | head -c 4000"
- powershell -ExecutionPolicy Bypass -File .\scripts\Invoke-DeploymentDriftAudit.ps1
- python scripts/generate_truth_inventory_reports.py --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /mnt/user/appdata/prometheus/prometheus.yml, /mnt/user/appdata/prometheus/alert-rules.yml, and saved container definition from /mnt/user/appdata/prometheus/backups/config-reconcile/<timestamp>.
- Restart the Prometheus container with the restored config.
- Re-run the deployment-drift audit and validator to confirm rollback.

## dev-runtime-ssh-access-recovery-packet

- Label: `DEV runtime SSH access recovery packet`
- Status: `executed`
- Lane: `dev-runtime-state`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Restore one governed DEV SSH access path so truth collection, runtime verification, and repo-root maintenance no longer depend on a broken alias or remembered fallback guesses.
- Lane next action: Keep this lane on access-path recovery only until either the governed `ssh dev` path or an explicitly blessed raw-host fallback is restored through `dev-runtime-ssh-access-recovery-packet`, then refresh collector evidence before treating broader DEV runtime maintenance as current.
- Backup root: `/home/shaun/.athanor/backups/runtime-ownership/dev-ssh-access/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/runbooks/rebuild-dev.md`

- Target units: `governed `ssh dev` access path`, `explicit raw-host fallback blessing record`

### Preflight Commands

- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- ssh dev "hostname && whoami"
- ssh shaun@192.168.1.189 "hostname && whoami"
- python scripts/validate_platform_contract.py

### Exact Steps

- Capture the current desktop SSH config plus any DEV-side access material needed for recovery under /home/shaun/.athanor/backups/runtime-ownership/dev-ssh-access/<timestamp> before mutation.
- Verify the canonical DEV host mapping, preferred username, intended key path, and any blessed fallback record instead of editing aliases from memory.
- Restore one governed access path so either `ssh dev` succeeds again or the raw-host fallback is intentionally blessed and documented as the supported recovery path.
- Refresh truth inventory and runtime ownership reports immediately after access is restored so the collector output stops carrying stale reachability failure evidence.

### Verification Commands

- ssh dev "hostname && whoami && ls -1 /home/shaun/.athanor"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the previous desktop SSH config and any DEV-side authorized-key or access material captured under the timestamped backup root.
- Re-run `ssh dev` and the truth refresh sequence to confirm the prior access posture is back in place.
- Leave the packet in ready-for-approval state until a new bounded access repair is explicitly reviewed.

## foundry-agents-runtime-alignment-packet

- Label: `FOUNDRY athanor-agents runtime alignment packet`
- Status: `executed`
- Lane: `foundry-agents-compose`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `foundry`
- Goal: Reconcile the live /opt/athanor/agents source tree and imported `athanor_agents` module path with implementation authority when the truth collector reports a source/runtime mismatch.
- Lane next action: Keep `foundry-agents-compose-deploy-packet` as the ordinary update path, but treat the current blocker as the narrower `foundry-agents-runtime-alignment-packet`: prove the governed `/opt/athanor/agents/src/athanor_agents` tree matches the approved implementation tree and that the imported module path is only the image-layout result of that same build before any manual runtime patching or site-packages edits.
- Backup root: `/opt/athanor/backups/agents-runtime-alignment/<timestamp>`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/TRUTH-DRIFT-REPORT.md`, `scripts/deploy-agents.sh`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `projects/agents/src/athanor_agents` | `/opt/athanor/agents/src/athanor_agents` | `athanor-agents` |
| `projects/agents/src/athanor_agents` | `/usr/local/lib/python3.12/site-packages/athanor_agents` | `athanor-agents` |

### Preflight Commands

- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"
- ssh foundry "docker exec athanor-agents python3 -c \"import json, pathlib, athanor_agents; print(json.dumps({'module': str(pathlib.Path(athanor_agents.__file__).resolve())}))\""
- python scripts/validate_platform_contract.py

### Exact Steps

- Capture a timestamped backup root under /opt/athanor/backups/agents-runtime-alignment/<timestamp> and preserve the current /opt/athanor/agents bundle, the live source tree, and the imported module-path evidence before mutation.
- Replace the governed /opt/athanor/agents build context from implementation authority with scripts/deploy-agents.sh instead of patching /usr/local/lib/python3.12/site-packages by hand.
- Rebuild and recreate athanor-agents, then verify that `/opt/athanor/agents/src/athanor_agents` matches the approved implementation tree and that the imported module path is only the image-layout result of that same build.
- If the mismatch persists after rebuild, capture the stale layer, source-tree, or import-path evidence in the packet output and stop instead of applying ad hoc hotfixes inside the running container.

### Verification Commands

- ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"
- ssh foundry "curl -sS http://localhost:9000/health"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets --report drift
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up /opt/athanor/agents bundle from /opt/athanor/backups/agents-runtime-alignment/<timestamp>.
- Rebuild and restart athanor-agents from the restored compose root.
- Re-run the same truth refresh and validator sequence to confirm the runtime tree returned to the pre-packet state.
