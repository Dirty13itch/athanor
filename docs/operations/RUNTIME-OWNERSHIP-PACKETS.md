# Runtime Ownership Packets

Generated from `config/automation-backbone/runtime-ownership-packets.json`, `config/automation-backbone/runtime-ownership-contract.json`, and the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Registry version: `2026-04-02.3`
- Cached truth snapshot: `2026-04-02T18:04:39.550896+00:00`
- Packets tracked: `4`

| Packet | Status | Lane | Approval type | Goal |
| --- | --- | --- | --- | --- |
| `dev-runtime-repo-sync-packet` | `ready_for_approval` | `dev-runtime-repo-systemd` | `runtime_host_reconfiguration` | Make the implementation-authority to DEV runtime-repo sync path explicit for the repo-root systemd estate instead of treating the runtime repo as generic dirty drift. |
| `dev-dashboard-shadow-retirement-packet` | `executed` | `dev-dashboard-compose` | `systemd_runtime_change` | Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path. |
| `dev-heartbeat-opt-deploy-packet` | `executed` | `dev-heartbeat-opt` | `runtime_host_reconfiguration` | Make the source-to-/opt heartbeat bundle replacement explicit so the live athanor-heartbeat.service lane no longer depends on undocumented manual copy steps. |
| `foundry-agents-compose-deploy-packet` | `ready_for_approval` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Make the repo-owned athanor-agents deploy path explicit so FOUNDRY updates replace the full compose build context and stop relying on ad hoc site-packages hotfixes. |

## dev-runtime-repo-sync-packet

- Label: `DEV runtime repo sync packet`
- Status: `ready_for_approval`
- Lane: `dev-runtime-repo-systemd`
- Approval type: `runtime_host_reconfiguration` (Runtime host reconfiguration)
- Host: `dev`
- Goal: Make the implementation-authority to DEV runtime-repo sync path explicit for the repo-root systemd estate instead of treating the runtime repo as generic dirty drift.
- Lane next action: Review and approve the dev-runtime-repo-sync-packet before replacing runtime-owned files on DEV.
- Backup root: `/home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>`
- Evidence: `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`

| Source path | Runtime path | Restart units |
| --- | --- | --- |
| `services/brain` | `/home/shaun/repos/athanor/services/brain` | `athanor-brain.service` |
| `services/classifier` | `/home/shaun/repos/athanor/services/classifier` | `athanor-classifier.service` |
| `services/quality-gate` | `/home/shaun/repos/athanor/services/quality-gate` | `athanor-quality-gate.service` |
| `services/sentinel` | `/home/shaun/repos/athanor/services/sentinel` | `athanor-sentinel.service` |
| `scripts/overnight-ops.sh` | `/home/shaun/repos/athanor/scripts/overnight-ops.sh` | `athanor-overnight.service` |

### Live evidence

- DEV runtime repo head: `511d1cb`
- DEV runtime dirty file count: `428`

### Preflight Commands

- python scripts/validate_platform_contract.py
- ssh dev "git -C /home/shaun/repos/athanor rev-parse --short HEAD && git -C /home/shaun/repos/athanor status --short | wc -l"
- ssh dev "systemctl show athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service athanor-overnight.service --property=WorkingDirectory,ExecStart --no-pager"

### Exact Steps

- Create a timestamped backup root under /home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync/<timestamp>.
- Back up each runtime-owned target before replacement, preserving permissions and timestamps where possible.
- Replace only the declared runtime targets from implementation authority into /home/shaun/repos/athanor.
- Restart or reload only the affected services after their owned paths are replaced.
- Refresh the truth snapshot and generated reports immediately after the sync.

### Verification Commands

- ssh dev "systemctl is-active athanor-brain.service athanor-classifier.service athanor-quality-gate.service athanor-sentinel.service athanor-overnight.service"
- python scripts/collect_truth_inventory.py --write reports/truth-inventory/latest.json
- python scripts/generate_truth_inventory_reports.py --report repo_roots --report runtime_ownership --report runtime_ownership_packets
- python scripts/validate_platform_contract.py

### Rollback Steps

- Restore the backed up runtime-owned paths from the timestamped backup root.
- Restart only the affected services after the restore.
- Re-run the same truth refresh and validator sequence to confirm rollback.

## dev-dashboard-shadow-retirement-packet

- Label: `DEV dashboard shadow retirement packet`
- Status: `executed`
- Lane: `dev-dashboard-compose`
- Approval type: `systemd_runtime_change` (Systemd runtime change)
- Host: `dev`
- Goal: Retire or explicitly downgrade the inactive athanor-dashboard.service unit so the active /opt/athanor/dashboard compose lane is the only ordinary dashboard deployment path.
- Lane next action: Keep athanor-dashboard.service masked as a recovery-only shadow; the active /opt/athanor/dashboard compose lane is the sole ordinary dashboard path.
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
- Status: `ready_for_approval`
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
- Build root clean: `False`
- Nested source dir present: `True`
- bak-codex files: `src/athanor_agents/athanor_agents/command_hierarchy.py.bak-codex`, `src/athanor_agents/athanor_agents/server.py.bak-codex`, `src/athanor_agents/command_hierarchy.py.bak-codex`, `src/athanor_agents/server.py.bak-codex`
- Container running: `True`
- Container status: `Up 2 hours`
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
