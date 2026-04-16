# Runtime Ownership Report

Generated from `config/automation-backbone/runtime-ownership-contract.json` plus the cached truth snapshot in `reports/truth-inventory/latest.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-16.2`
- Cached truth snapshot: `2026-04-16T15:23:28.419424+00:00`
- Promotion gate: `runtime_ownership_maturity`
- Goal: Make runtime ownership explicit enough that host-level maintenance no longer depends on undocumented operator memory.
- Implementation authority: `desk-main` -> `C:/Athanor`
- Runtime authority: `dev-runtime-repo` -> `/home/shaun/repos/athanor`
- Runtime state roots: `dev-opt-athanor`, `dev-state`, `dev-systemd`, `dev-cron`, `vault-boot-config`, `vault-appdata`, `vault-appdatacache`, `vault-docker-root`, `foundry-opt-athanor`, `workshop-opt-athanor`
- Ownership lanes tracked: `16`
- Execution packets tracked: `17`

| Criterion status | Count |
| --- | --- |
| `met` | 5 |

## Repo Evidence

- Implementation dirty file count: `207`
- DEV runtime probe: `unable to reach DEV via ssh`
- DEV SSH targets attempted: `dev`, `shaun@192.168.1.189`
- DEV SSH failure samples: `dev` -> `Traceback (most recent call last):`, `shaun@192.168.1.189` -> `shaun@192.168.1.189: Permission denied (publickey,password).`
- FOUNDRY compose root matches expected: `True`
- FOUNDRY build root clean: `True`
- FOUNDRY runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`
- Runtime source-tree mismatches: `1`
- Site-packages import is expected image layout; treat source-tree mismatch, not the import location alone, as the blocker.
- Active alignment blocker: `src/athanor_agents`

## Ownership Lanes

| Lane | Host | Mode | Status | Owner roots | Packet | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `dev-runtime-repo-systemd` | `dev` | `repo_worktree_mirror` | `active` | `dev-runtime-repo`, `dev-systemd` | `dev-runtime-repo-sync-packet` | Keep the executed dev-runtime-repo-sync-packet as the governed resync path for future repo-root maintenance. The 2026-04-08 execution left /home/shaun/repos/athanor mirror-clean at commit 5148170 with athanor-brain, athanor-classifier, athanor-quality-gate, and athanor-sentinel healthy; athanor-overnight.service remains outside the immediate mirror-clean verification window because it rewrites tracked generated artifacts. |
| `dev-dashboard-compose` | `dev` | `opt_compose_service` | `active` | `dev-opt-athanor`, `dev-runtime-repo` | `dev-dashboard-compose-deploy-packet` | Use the dev-dashboard-compose-deploy-packet and scripts/deploy-dashboard.sh as the only ordinary dashboard update path; keep athanor-dashboard.service masked as a recovery-only shadow. |
| `dev-heartbeat-opt` | `dev` | `opt_systemd_service` | `active` | `dev-opt-athanor`, `dev-systemd` | `dev-heartbeat-opt-deploy-packet` | Use the executed heartbeat deploy packet as the governed replacement path for future /opt/athanor/heartbeat updates. |
| `dev-runtime-state` | `dev` | `host_state_surface` | `active` | `dev-state`, `dev-systemd`, `dev-cron`, `dev-logs` | `dev-runtime-ssh-access-recovery-packet` | Keep this lane on access-path recovery only until either the governed `ssh dev` path or an explicitly blessed raw-host fallback is restored through `dev-runtime-ssh-access-recovery-packet`, then refresh collector evidence before treating broader DEV runtime maintenance as current. |
| `desk-goose-operator-shell` | `desk` | `host_state_surface` | `active` | `desk-main`, `athanor-devstack` | `desk-goose-operator-shell-rollout-packet` | Treat the DESK Goose helper as the adopted bounded shell path; keep future shell-path changes packet-backed through desk-goose-operator-shell-rollout-packet instead of drifting through workstation-local defaults. |
| `foundry-agents-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-agents-compose-deploy-packet` | Keep `foundry-agents-compose-deploy-packet` as the ordinary update path, but treat the current blocker as the narrower `foundry-agents-runtime-alignment-packet`: prove the governed `/opt/athanor/agents/src/athanor_agents` tree matches the approved implementation tree and that the imported module path is only the image-layout result of that same build before any manual runtime patching or site-packages edits. |
| `foundry-graphrag-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-graphrag-compose-deploy-packet` | Keep the executed foundry-graphrag-compose-deploy-packet as the governed runtime update path for future GraphRAG changes; the runtime and promotion eval are already green, so the remaining boundary is packet review and adoption acceptance for widening beyond shadow-tier evidence. |
| `foundry-gpu-orchestrator-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-gpu-orchestrator-compose-deploy-packet` | Use scripts/deploy-gpu-orchestrator.sh as the governed update path for future FOUNDRY GPU Orchestrator changes; the bounded scheduler surface should roll through foundry-gpu-orchestrator-scheduler-state-rollout-packet so /scheduler/state, write-capability posture, and scheduler request/preload/release route presence are verified explicitly before the lane advances beyond offline proof. |
| `foundry-watchdog-runtime-guard` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-watchdog-runtime-guard-rollout-packet` | Maintain the executed live canary as the packet-backed watchdog lane, keep operator-envelope and protected-service boundaries intact, and reopen only for a later production widening or rollback. |
| `foundry-vllm-compose` | `foundry` | `opt_compose_service` | `active` | `foundry-opt-athanor` | `foundry-vllm-compose-reconciliation-packet` | Keep the FOUNDRY compose root packet-backed, but treat :8100 as the canonical healthy text lane and :8000 as degraded nonblocking lineage until a future bounded packet either restores real completion health or retires the coordinator lane explicitly. |
| `workshop-control-surface-compose` | `workshop` | `opt_compose_service` | `retired` | `workshop-opt-athanor` | `workshop-control-surface-compose-reconciliation-packet` | Keep the live Workshop dashboard shadow and ws-pty bridge healthy and treat any future compose or source change as packet-backed runtime work; the 2026-04-08 backup-first reconcile pass synced the source bundles, replaced /opt/athanor/dashboard/docker-compose.yml from implementation authority, and re-probed both :3001 and :3100/health at 200. |
| `workshop-vllm-compose` | `workshop` | `opt_compose_service` | `active` | `workshop-opt-athanor` | `workshop-vllm-compose-reconciliation-packet` | Keep this lane retired and rely on Workshop ComfyUI plus vllm-vision as the active Workshop data-plane surfaces unless a future packet deliberately restores a real :8010 worker runtime. |
| `workshop-product-compose` | `workshop` | `opt_compose_service` | `active` | `workshop-opt-athanor` | `none` | Keep these roots explicit and split them into narrower per-surface repair packets only when a specific Workshop product or creative service is intentionally reconciled. |
| `vault-litellm-config` | `vault` | `vault_host_state` | `active` | `vault-appdata`, `vault-docker-root` | `vault-litellm-config-reconciliation-packet` | Keep the executed VAULT LiteLLM config packet as the governed update path for future routing changes; the 2026-04-08 reprobe showed /mnt/user/appdata/litellm/config.yaml identical to implementation authority, the litellm container healthy, and provider-auth follow-through narrowed to the separate missing-secret and upstream-auth lane. |
| `vault-prometheus-config` | `vault` | `vault_host_state` | `active` | `vault-appdata`, `vault-docker-root` | `vault-prometheus-config-reconciliation-packet` | Keep the executed vault-prometheus-config-reconciliation-packet as the governed update path; the 2026-04-08 reprobe showed both Prometheus config surfaces identical to implementation authority and the Prometheus container healthy after restart. |
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
- Next action: Keep the executed dev-runtime-repo-sync-packet as the governed resync path for future repo-root maintenance. The 2026-04-08 execution left /home/shaun/repos/athanor mirror-clean at commit 5148170 with athanor-brain, athanor-classifier, athanor-quality-gate, and athanor-sentinel healthy; athanor-overnight.service remains outside the immediate mirror-clean verification window because it rewrites tracked generated artifacts.
- Packet status: `retired`
- Packet approval type: `runtime_host_reconfiguration`

### Live systemd evidence

| Unit | Working directories | ExecStart | EnvFiles |
| --- | --- | --- | --- |
| `/home/shaun/repos/athanor` | none | none | 0 |
| `athanor-brain.service` | none | none | 0 |
| `athanor-classifier.service` | none | none | 0 |
| `athanor-quality-gate.service` | none | none | 0 |
| `athanor-sentinel.service` | none | none | 0 |
| `athanor-overnight.service` | none | none | 0 |

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
- Container status: `Up 43 hours`
- Compose working dir: `/opt/athanor/dashboard`
- Legacy service state: `inactive` / `dead`
- Legacy unit file state: `masked`
- Legacy service root-cause hint: `none`
- Runtime probe status: `200`
- Canonical probe status: `200`

| Control file | Impl -> runtime repo | Impl -> deploy root | Runtime repo -> deploy root |
| --- | --- | --- | --- |
| `Dockerfile` | `True` | `True` | `True` |
| `docker-compose.yml` | `False` | `True` | `False` |

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

- Unit file state: `unknown`
- Working directories: none
- ExecStart: none
- EnvFiles: `0`
- Deployed script exists: `False`
- Host-local env exists: `False`
- Runtime venv exists: `False`
- Implementation matches deploy root: `False`

## dev-runtime-state

- Label: `DEV runtime state surfaces`
- Host: `dev`
- Status: `active`
- Mode: `host_state_surface`
- Owner roots: `dev-state -> /home/shaun/.athanor`, `dev-systemd -> /etc/systemd/system/athanor-*`, `dev-cron -> /etc/cron.d/athanor-* and /var/spool/cron/crontabs/shaun`, `dev-logs -> /var/log/athanor`
- Source root: `none`
- Runtime scope: Live DEV host-state estate for runtime envfiles, work queues, systemd units, cron definitions, and service logs; the current blocker is regaining the governed SSH access path needed to inspect or mutate it safely.
- Source paths: none
- Runtime paths: `/home/shaun/.athanor`, `/etc/systemd/system/athanor-*`, `/etc/cron.d/athanor-*`, `/var/log/athanor`
- Active surfaces: `/home/shaun/.athanor/runtime.env`, `/home/shaun/.athanor/systemd`, `athanor-* systemd estate`, `athanor-* cron estate`
- Execution packet: `dev-runtime-ssh-access-recovery-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/runbooks/local-runtime-env.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh dev "ls -1 /home/shaun/.athanor && systemctl list-unit-files 'athanor-*' --no-legend && ls -1 /etc/cron.d/athanor-* 2>/dev/null"`
- Rollback contract: Capture timestamped backups under /home/shaun/.athanor/backups/runtime-state/<timestamp>/ before mutating envfiles, cron, or service units.
- Approval boundary: Systemd, cron, and other host-level state mutations remain approval-gated.
- Next action: Keep this lane on access-path recovery only until either the governed `ssh dev` path or an explicitly blessed raw-host fallback is restored through `dev-runtime-ssh-access-recovery-packet`, then refresh collector evidence before treating broader DEV runtime maintenance as current.
- Packet status: `ready_for_approval`
- Packet approval type: `runtime_host_reconfiguration`

### Live runtime-state evidence

- /opt entries: none
- /home/shaun/.athanor entries: none
- Cron files: none

## desk-goose-operator-shell

- Label: `DESK Goose operator-shell lane`
- Host: `desk`
- Status: `active`
- Mode: `host_state_surface`
- Owner roots: `desk-main -> C:/Athanor`, `athanor-devstack -> C:/athanor-devstack`
- Source root: `desk-main`
- Runtime scope: Bounded DESK Goose helper and local shell-state contract that pins the adopted Athanor shell path to the intended LiteLLM DeepSeek lane without letting Goose become a parallel control plane.
- Source paths: `scripts/run-goose-athanor-shell.ps1`, `config/automation-backbone/lane-selection-matrix.json`, `config/automation-backbone/failure-routing-matrix.json`, `docs/operations/ATHANOR-OPERATING-SYSTEM.md`
- Runtime paths: `C:/Users/Shaun/AppData/Local/Athanor/operator-shell/run-goose-athanor-shell.ps1`, `C:/Users/Shaun/AppData/Roaming/Block/goose/config`
- Active surfaces: `goose CLI headless runner`, `Athanor-pinned Goose shell helper`, `DESK Goose local config root`
- Execution packet: `desk-goose-operator-shell-rollout-packet`
- Evidence: `reports/truth-inventory/goose-operator-shell-formal-eval.json`, `reports/truth-inventory/goose-operator-shell-promptfoo-results.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/ATHANOR-OPERATING-SYSTEM.md`, `scripts/run-goose-athanor-shell.ps1`
- Verification commands: `powershell -ExecutionPolicy Bypass -File .\scripts\run-goose-athanor-shell.ps1 run --text "Reply with READY only." --no-session --no-profile --quiet --output-format text --max-turns 1`, `python scripts/run_capability_pilot_formal_eval.py --run-id goose-operator-shell-lane-eval-2026q2`, `python scripts/validate_platform_contract.py`
- Rollback contract: Remove the DESK Goose helper from the local operator-shell path, restore direct terminal plus specialist CLI routing as the default shell path, and keep Goose-specific state outside Athanor adopted truth.
- Approval boundary: Changing the DESK Goose helper, fallback contract, or local Goose runtime defaults remains packet-gated.
- Next action: Treat the DESK Goose helper as the adopted bounded shell path; keep future shell-path changes packet-backed through desk-goose-operator-shell-rollout-packet instead of drifting through workstation-local defaults.
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

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
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-agents.sh`, `docs/operations/TRUTH-DRIFT-REPORT.md`
- Verification commands: `ssh foundry "cd /opt/athanor/agents && docker compose ps athanor-agents"`, `ssh foundry "docker exec athanor-agents python3 -c \"import json, pathlib, athanor_agents, athanor_agents.bootstrap_state as bootstrap_state; print(json.dumps({'module': str(pathlib.Path(athanor_agents.__file__).resolve()), 'bootstrap_state': str(pathlib.Path(bootstrap_state.__file__).resolve())}))\""`, `ssh foundry "curl -sS http://localhost:9000/health"`
- Rollback contract: Preserve the previous /opt/athanor/agents bundle under /opt/athanor/backups/agents/<timestamp>/ before replacement, and rebuild the compose lane from that backup if the rollout regresses.
- Approval boundary: Replacing /opt/athanor/agents contents or rebuilding the live athanor-agents container remains approval-gated.
- Next action: Keep `foundry-agents-compose-deploy-packet` as the ordinary update path, but treat the current blocker as the narrower `foundry-agents-runtime-alignment-packet`: prove the governed `/opt/athanor/agents/src/athanor_agents` tree matches the approved implementation tree and that the imported module path is only the image-layout result of that same build before any manual runtime patching or site-packages edits.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `foundry-agents` | `identical` | `running` | `1/1` | .\reports\live\foundry-agents.runtime.json |
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

### Live FOUNDRY agents evidence

- Expected root exists: `True`
- Compose root matches expected: `True`
- Build root clean: `True`
- Nested source dir present: `False`
- bak-codex files: none
- Container running: `True`
- Container status: `Up 43 hours`
- Compose working dir: `/opt/athanor/agents`
- Compose config files: `/opt/athanor/agents/docker-compose.yml`
- Runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`
- Site-packages import: `True`
- Source mirrors: `/workspace/projects/agents/src/athanor_agents`, `/workspace/agents/src/athanor_agents`, `/app/src/athanor_agents`
- Runtime source-tree mismatches: `1`
- Site-packages import is expected image layout; treat source-tree mismatch, not the import location alone, as the blocker.
- Active alignment blocker: `src/athanor_agents`

| Control path | Kind | Impl exists | Runtime exists | Impl -> runtime |
| --- | --- | --- | --- | --- |
| `Dockerfile` | `file` | `True` | `True` | `True` |
| `pyproject.toml` | `file` | `True` | `True` | `True` |
| `docker-compose.yml` | `file` | `True` | `True` | `True` |
| `config/subscription-routing-policy.yaml` | `file` | `True` | `True` | `True` |
| `src/athanor_agents` | `directory` | `True` | `True` | `False` |

## foundry-graphrag-compose

- Label: `FOUNDRY GraphRAG compose lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `athanor-devstack`
- Runtime scope: Active FOUNDRY GraphRAG retrieval deployment rooted at /opt/athanor/graphrag and serving the governed knowledge-subsystem proof surface on :9300.
- Source paths: `services/graphrag/Dockerfile`, `services/graphrag/docker-compose.yml`, `services/graphrag/main.py`, `services/graphrag/index_chunks.py`, `services/graphrag/index_json_registries.py`, `services/graphrag/requirements.txt`, `docs/promotion-packets/graphrag-hybrid-retrieval.md`
- Runtime paths: `/opt/athanor/graphrag/Dockerfile`, `/opt/athanor/graphrag/docker-compose.yml`, `/opt/athanor/graphrag/main.py`, `/opt/athanor/graphrag/index_chunks.py`, `/opt/athanor/graphrag/index_json_registries.py`, `/opt/athanor/graphrag/requirements.txt`
- Active surfaces: `athanor-graphrag container`, `/opt/athanor/graphrag compose bundle`, `http://foundry:9300/health`
- Execution packet: `foundry-graphrag-compose-deploy-packet`
- Evidence: `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/TRUTH-DRIFT-REPORT.md`, `reports/truth-inventory/provider-usage-evidence.json`
- Verification commands: `ssh foundry "cd /opt/athanor/graphrag && docker compose ps"`, `ssh foundry "docker inspect athanor-graphrag --format '{{.Name}}|{{.State.Status}}|{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}'"`, `ssh foundry "curl -sS --max-time 20 http://127.0.0.1:9300/health && curl -sS --max-time 20 http://127.0.0.1:9300/status"`, `python scripts/run_graphrag_promotion_eval.py`
- Rollback contract: Preserve the previous /opt/athanor/graphrag bundle under /opt/athanor/backups/graphrag/<timestamp>/ before replacement, and restore that bundle if the approved deploy regresses the GraphRAG retrieval surface or its Athanor integration path.
- Approval boundary: Replacing /opt/athanor/graphrag contents or rebuilding the live athanor-graphrag container remains approval-gated.
- Next action: Keep the executed foundry-graphrag-compose-deploy-packet as the governed runtime update path for future GraphRAG changes; the runtime and promotion eval are already green, so the remaining boundary is packet review and adoption acceptance for widening beyond shadow-tier evidence.
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## foundry-gpu-orchestrator-compose

- Label: `FOUNDRY GPU Orchestrator compose lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active FOUNDRY GPU Orchestrator deployment rooted at /opt/athanor/gpu-orchestrator and aligned to implementation authority after the governed 2026-04-08 redeploy.
- Source paths: `projects/gpu-orchestrator/Dockerfile`, `projects/gpu-orchestrator/pyproject.toml`, `projects/gpu-orchestrator/docker-compose.yml`, `projects/gpu-orchestrator/src/gpu_orchestrator`, `scripts/deploy-gpu-orchestrator.sh`
- Runtime paths: `/opt/athanor/gpu-orchestrator/Dockerfile`, `/opt/athanor/gpu-orchestrator/pyproject.toml`, `/opt/athanor/gpu-orchestrator/docker-compose.yml`, `/opt/athanor/gpu-orchestrator/src/gpu_orchestrator`
- Active surfaces: `gpu-orchestrator container`, `http://foundry:9200/health`, `http://foundry:9200/zones`
- Execution packet: `foundry-gpu-orchestrator-compose-deploy-packet`
- Evidence: `reports/deployment-drift/summary.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `scripts/deploy-gpu-orchestrator.sh`
- Verification commands: `ssh foundry "cd /opt/athanor/gpu-orchestrator && docker compose ps"`, `ssh foundry "curl -sS http://127.0.0.1:9200/health && curl -sS http://127.0.0.1:9200/zones"`
- Rollback contract: Preserve the previous /opt/athanor/gpu-orchestrator bundle under /opt/athanor/backups/gpu-orchestrator/<timestamp>/ before replacement, and restore it if the approved deploy regresses the active coordinator or zone-reporting surface.
- Approval boundary: Replacing /opt/athanor/gpu-orchestrator contents or rebuilding the live gpu-orchestrator container remains approval-gated.
- Next action: Use scripts/deploy-gpu-orchestrator.sh as the governed update path for future FOUNDRY GPU Orchestrator changes; the bounded scheduler surface should roll through foundry-gpu-orchestrator-scheduler-state-rollout-packet so /scheduler/state, write-capability posture, and scheduler request/preload/release route presence are verified explicitly before the lane advances beyond offline proof.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `foundry-gpu-orchestrator` | `different` | `running` | `1/1` | .\reports\live\foundry-gpu-orchestrator.runtime.json |
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## foundry-watchdog-runtime-guard

- Label: `FOUNDRY watchdog runtime-guard lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Athanor-owned FOUNDRY watchdog live canary bundle rooted at /opt/athanor/watchdog with operator-visible monitoring and bounded remediation controls. Runtime mutation is active through the executed packet and gate env contract, while protected-service and operator-envelope boundaries remain fail-closed.
- Source paths: `projects/agents/watchdog/Dockerfile`, `projects/agents/watchdog/docker-compose.yml`, `projects/agents/watchdog/main.py`, `projects/agents/watchdog/catalog.py`, `projects/agents/watchdog/remediation.py`, `projects/agents/watchdog/circuit.py`, `projects/agents/watchdog/requirements.txt`
- Runtime paths: `/opt/athanor/watchdog/Dockerfile`, `/opt/athanor/watchdog/docker-compose.yml`, `/opt/athanor/watchdog/main.py`, `/opt/athanor/watchdog/catalog.py`, `/opt/athanor/watchdog/remediation.py`, `/opt/athanor/watchdog/circuit.py`, `/opt/athanor/watchdog/requirements.txt`
- Active surfaces: `athanor-watchdog container`, `http://foundry:9301/health`, `http://foundry:9301/status`
- Execution packet: `foundry-watchdog-runtime-guard-rollout-packet`
- Evidence: `projects/agents/watchdog/README.md`, `projects/agents/tests/test_watchdog_runtime_guard.py`, `projects/agents/tests/test_watchdog_route_contract.py`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/OPERATOR_RUNBOOKS.md`
- Verification commands: `C:/Athanor/projects/agents/.venv/Scripts/python.exe -m pytest C:/Athanor/projects/agents/tests/test_watchdog_runtime_guard.py -q`, `C:/Athanor/projects/agents/.venv/Scripts/python.exe -m pytest C:/Athanor/projects/agents/tests/test_watchdog_route_contract.py -q`, `python scripts/validate_platform_contract.py`, `ssh foundry "cd /opt/athanor/watchdog && docker compose ps"`, `ssh foundry "curl -sS http://127.0.0.1:9301/health && curl -sS http://127.0.0.1:9301/status"`
- Rollback contract: Preserve the previous /opt/athanor/watchdog bundle under /opt/athanor/backups/watchdog/<timestamp>/ before replacement, and close the mutation gate or restore the prior bundle if the live canary widens scope or regresses the bounded monitoring/remediation surface.
- Approval boundary: Replacing /opt/athanor/watchdog contents, rebuilding the athanor-watchdog container, or widening protected-service or remediation scope remains approval-gated.
- Next action: Maintain the executed live canary as the packet-backed watchdog lane, keep operator-envelope and protected-service boundaries intact, and reopen only for a later production widening or rollback.
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## foundry-vllm-compose

- Label: `FOUNDRY llama-dolphin coder lane`
- Host: `foundry`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `foundry-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Active FOUNDRY vLLM compose root under /opt/athanor/vllm, with dolphin3-r1-24b on :8100 as the canonical healthy coder lane and the legacy coordinator lane on :8000 retained only as a degraded secondary surface.
- Source paths: `ansible/host_vars/core.yml`, `ansible/roles/vllm/defaults/main.yml`, `ansible/roles/vllm/templates/docker-compose.yml.j2`, `reports/rendered/foundry-vllm.rendered.yml`
- Runtime paths: `/opt/athanor/vllm/docker-compose.yml`
- Active surfaces: `vllm-coordinator container (degraded)`, `llama-dolphin container`, `http://foundry:8000/v1/models (list-only, completion-degraded)`, `http://foundry:8100/v1/models`
- Execution packet: `foundry-vllm-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/foundry-vllm.rendered.yml`, `reports/live/foundry-vllm.live.yml`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh foundry "cd /opt/athanor/vllm && docker compose ps"`, `ssh foundry "docker inspect llama-dolphin --format '{{json .Config.Cmd}}'"`, `ssh foundry "curl -sS http://localhost:8100/v1/models"`
- Rollback contract: Preserve the previous /opt/athanor/vllm bundle under /opt/athanor/backups/vllm/<timestamp>/ before replacing the compose root, and restore that bundle if the approved reconcile pass regresses the active coder or coordinator lanes.
- Approval boundary: Replacing /opt/athanor/vllm/docker-compose.yml or recreating the live FOUNDRY vLLM containers remains approval-gated.
- Next action: Keep the FOUNDRY compose root packet-backed, but treat :8100 as the canonical healthy text lane and :8000 as degraded nonblocking lineage until a future bounded packet either restores real completion health or retires the coordinator lane explicitly.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `foundry-vllm` | `identical` | `no_containers` | `0/0` | .\reports\live\foundry-vllm.runtime.json |
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## workshop-control-surface-compose

- Label: `WORKSHOP control-surface compose lane`
- Host: `workshop`
- Status: `retired`
- Mode: `opt_compose_service`
- Owner roots: `workshop-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Recovery-only Workshop dashboard shadow plus the live ws-pty-bridge compose bundle rooted under /opt/athanor/dashboard and /opt/athanor/ws-pty-bridge.
- Source paths: `ansible/host_vars/interface.yml`, `ansible/roles/dashboard/defaults/main.yml`, `ansible/roles/dashboard/tasks/main.yml`, `ansible/roles/dashboard/templates/docker-compose.yml.j2`, `projects/dashboard`, `projects/ws-pty-bridge`, `reports/rendered/workshop-dashboard.rendered.yml`
- Runtime paths: `/opt/athanor/dashboard/docker-compose.yml`, `/opt/athanor/ws-pty-bridge`
- Active surfaces: `athanor-dashboard container (shadow recovery)`, `athanor-ws-pty-bridge container`, `http://workshop:3001/`, `http://workshop:3100/health`
- Execution packet: `workshop-control-surface-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/workshop-dashboard.rendered.yml`, `reports/live/workshop-dashboard.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh workshop "cd /opt/athanor/dashboard && docker compose ps"`, `ssh workshop "docker inspect athanor-ws-pty-bridge --format '{{.Name}}|{{.State.Status}}'"`, `ssh workshop "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3100/health"`
- Rollback contract: Preserve the previous /opt/athanor/dashboard compose bundle and /opt/athanor/ws-pty-bridge source under /opt/athanor/backups/dashboard-shadow/<timestamp>/ before replacement, and restore both if the approved reconcile pass regresses bridge access or the shadow recovery surface.
- Approval boundary: Replacing Workshop control-surface compose roots or recreating the live dashboard shadow or ws-pty-bridge containers remains approval-gated.
- Next action: Keep the live Workshop dashboard shadow and ws-pty bridge healthy and treat any future compose or source change as packet-backed runtime work; the 2026-04-08 backup-first reconcile pass synced the source bundles, replaced /opt/athanor/dashboard/docker-compose.yml from implementation authority, and re-probed both :3001 and :3100/health at 200.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `workshop-dashboard` | `identical` | `running` | `2/2` | .\reports\live\workshop-dashboard.runtime.json |
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## workshop-vllm-compose

- Label: `WORKSHOP vLLM compose lane`
- Host: `workshop`
- Status: `active`
- Mode: `opt_compose_service`
- Owner roots: `workshop-opt-athanor -> /opt/athanor`
- Source root: `desk-main`
- Runtime scope: Retired Workshop vLLM worker lineage rooted at /opt/athanor/vllm-node2. The old :8010 worker contract is no longer a live runtime because the pinned model directory is absent and the container crashes on startup.
- Source paths: `ansible/host_vars/interface.yml`, `ansible/roles/vllm/defaults/main.yml`, `ansible/roles/vllm/templates/docker-compose.yml.j2`, `reports/rendered/workshop-vllm.rendered.yml`
- Runtime paths: `/opt/athanor/vllm-node2/docker-compose.yml`
- Active surfaces: `/opt/athanor/vllm-node2 compose lineage`, `retired Workshop :8010 worker contract`
- Execution packet: `workshop-vllm-compose-reconciliation-packet`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/workshop-vllm.rendered.yml`, `reports/live/workshop-vllm.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`
- Verification commands: `ssh workshop "cd /opt/athanor/vllm-node2 && docker compose ps"`, `ssh workshop "docker inspect vllm-node2 --format '{{json .Config.Cmd}}'"`, `ssh workshop "curl -sS http://127.0.0.1:8010/v1/models"`
- Rollback contract: Restore the previous /opt/athanor/vllm-node2 compose bundle only if a future bounded packet intentionally revives a real worker lane with an existing model path and passing live probes.
- Approval boundary: Restoring /opt/athanor/vllm-node2 as a live Workshop worker lane remains packet-gated until a real model path exists and the lane reproves healthy.
- Next action: Keep this lane retired and rely on Workshop ComfyUI plus vllm-vision as the active Workshop data-plane surfaces unless a future packet deliberately restores a real :8010 worker runtime.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `workshop-vllm` | `identical` | `not_running` | `0/1` | .\reports\live\workshop-vllm.runtime.json |

### Workshop runtime interpretation

- Model-deployment truth keeps `workshop-worker` `drifted` on `http://192.168.1.225:8010/v1/models`.
- 2026-04-14 restore attempt left vllm-node2 crash-looping because /mnt/vault/models/Qwen3.5-35B-A3B-AWQ-4bit is absent; live Workshop runtime is ComfyUI plus vllm-vision, not a reachable :8010 worker lane
- The currently aligned Workshop model lane is `workshop-vision` on `http://192.168.1.225:8012/v1/models`.
- Operator-side `workshop_worker_api` probing currently reports `URLError: timed out`.
- Treat the `:8010` Workshop worker as restore-or-retire debt until Athanor runtime truth explicitly restores it or retires it.
- Packet status: `executed`
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

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `workshop-comfyui` | `different` | `running` | `1/1` | .\reports\live\workshop-comfyui.runtime.json |
| `workshop-eoq` | `different` | `running` | `1/1` | .\reports\live\workshop-eoq.runtime.json |
| `workshop-open-webui` | `different` | `running` | `1/1` | .\reports\live\workshop-open-webui.runtime.json |
| `workshop-ulrich-energy` | `different` | `running` | `1/1` | .\reports\live\workshop-ulrich-energy.runtime.json |

### Workshop runtime interpretation

- Operator-side Open WebUI probing currently reports `200`.
- ComfyUI is still running locally on WORKSHOP under `/opt/athanor/comfyui`.
- Operator-side ComfyUI probing currently reports `200`, so this is a reachability problem rather than a missing container.
- Use this lane to retire or deliberately restore Open WebUI, and treat ComfyUI as a reachability repair path instead of a dead-service resurrection.

## vault-litellm-config

- Label: `VAULT LiteLLM config lane`
- Host: `vault`
- Status: `active`
- Mode: `vault_host_state`
- Owner roots: `vault-appdata -> /mnt/user/appdata`, `vault-docker-root -> /mnt/docker`
- Source root: `desk-main`
- Runtime scope: Live VAULT LiteLLM proxy config and container state rooted at /mnt/user/appdata/litellm/config.yaml, aligned to implementation authority after the governed 2026-04-08 reconcile pass and still subject to packet-backed maintenance for future changes.
- Source paths: `ansible/host_vars/vault.yml`, `ansible/roles/vault-litellm/defaults/main.yml`, `ansible/roles/vault-litellm/templates/litellm_config.yaml.j2`, `reports/rendered/vault-litellm-config.rendered.yaml`
- Runtime paths: `/mnt/user/appdata/litellm/config.yaml`
- Active surfaces: `litellm container`, `/mnt/user/appdata/litellm/config.yaml`, `http://vault:4000/health`
- Execution packet: `vault-litellm-config-reconciliation-packet`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/vault-litellm-config.rendered.yaml`, `reports/live/vault-litellm-config.live.yaml`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/VAULT-LITELLM-AUTH-REPAIR-PACKET.md`
- Verification commands: `python scripts/vault-ssh.py "docker inspect litellm --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"`, `python scripts/vault-ssh.py "test -f /mnt/user/appdata/litellm/config.yaml && sed -n '1,120p' /mnt/user/appdata/litellm/config.yaml"`, `python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:4000/health"`
- Rollback contract: Back up the current /mnt/user/appdata/litellm/config.yaml plus the current litellm container definition before replacing the config, and restore both if the approved reconcile pass regresses routing or auth posture.
- Approval boundary: Mutating /mnt/user/appdata/litellm/config.yaml or recreating the live litellm container on VAULT remains approval-gated.
- Next action: Keep the executed VAULT LiteLLM config packet as the governed update path for future routing changes; the 2026-04-08 reprobe showed /mnt/user/appdata/litellm/config.yaml identical to implementation authority, the litellm container healthy, and provider-auth follow-through narrowed to the separate missing-secret and upstream-auth lane.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `vault-litellm` | `different` | `not_applicable` | `0/0` | none |
- Packet status: `executed`
- Packet approval type: `runtime_host_reconfiguration`

## vault-prometheus-config

- Label: `VAULT Prometheus config lane`
- Host: `vault`
- Status: `active`
- Mode: `vault_host_state`
- Owner roots: `vault-appdata -> /mnt/user/appdata`, `vault-docker-root -> /mnt/docker`
- Source root: `desk-main`
- Runtime scope: Live VAULT Prometheus scrape config rooted at /mnt/user/appdata/prometheus/prometheus.yml, aligned to implementation authority after the governed reconcile pass and still subject to packet-backed maintenance for future changes.
- Source paths: `ansible/host_vars/vault.yml`, `ansible/roles/vault-monitoring/defaults/main.yml`, `ansible/roles/vault-monitoring/templates/prometheus.yml.j2`, `ansible/roles/vault-monitoring/templates/alert-rules.yml.j2`, `reports/rendered/vault-prometheus.rendered.yml`, `reports/rendered/vault-alert-rules.rendered.yml`
- Runtime paths: `/mnt/user/appdata/prometheus/prometheus.yml`, `/mnt/user/appdata/prometheus/alert-rules.yml`
- Active surfaces: `prometheus container`, `/mnt/user/appdata/prometheus/prometheus.yml`, `/mnt/user/appdata/prometheus/alert-rules.yml`, `http://vault:9090/-/healthy`
- Execution packet: `vault-prometheus-config-reconciliation-packet`
- Evidence: `reports/deployment-drift/summary.md`, `reports/rendered/vault-prometheus.rendered.yml`, `reports/rendered/vault-alert-rules.rendered.yml`, `reports/live/vault-prometheus.live.yml`, `reports/live/vault-alert-rules.live.yml`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md`, `docs/operations/ATHANOR-RECONCILIATION-PACKET.md`
- Verification commands: `python scripts/vault-ssh.py "docker inspect prometheus --format '{{.Name}}|{{.State.Status}}|{{.HostConfig.RestartPolicy.Name}}'"`, `python scripts/vault-ssh.py "test -f /mnt/user/appdata/prometheus/prometheus.yml && sed -n '1,220p' /mnt/user/appdata/prometheus/prometheus.yml"`, `python scripts/vault-ssh.py "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9090/-/healthy"`
- Rollback contract: Back up the current /mnt/user/appdata/prometheus/prometheus.yml, /mnt/user/appdata/prometheus/alert-rules.yml, and the current Prometheus container definition before replacement, and restore them if the approved reconcile pass regresses monitoring coverage or the Prometheus service state.
- Approval boundary: Mutating /mnt/user/appdata/prometheus/prometheus.yml or /mnt/user/appdata/prometheus/alert-rules.yml, or recreating the live Prometheus container on VAULT, remains approval-gated.
- Next action: Keep the executed vault-prometheus-config-reconciliation-packet as the governed update path; the 2026-04-08 reprobe showed both Prometheus config surfaces identical to implementation authority and the Prometheus container healthy after restart.

### Latest deployment drift evidence

| Comparison | Drift | Runtime | Containers | Runtime evidence |
| --- | --- | --- | --- | --- |
| `vault-alert-rules` | `identical` | `not_applicable` | `0/0` | none |
| `vault-prometheus` | `different` | `not_applicable` | `0/0` | none |
- Packet status: `executed`
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
- Evidence: `reports/truth-inventory/vault-redis-audit.json`, `reports/truth-inventory/vault-litellm-env-audit.json`, `docs/operations/REPO-ROOTS-REPORT.md`, `scripts/vault-ssh.py`
- Verification commands: `python scripts/vault-ssh.py "echo CONNECTED && hostname"`, `python scripts/vault_redis_audit.py --write reports/truth-inventory/vault-redis-audit.json`
- Rollback contract: Back up /boot/config and any targeted appdata bundle before mutating live VAULT runtime state.
- Approval boundary: VAULT Docker, env, and host-level mutations remain approval-gated.
- Next action: Keep VAULT maintenance reachable through repo-owned SSH helpers and route specific config drift through the named LiteLLM and Prometheus packets instead of generic host-state edits.

## Promotion Criteria

| Criterion | Status | Requirement | Evidence |
| --- | --- | --- | --- |
| `live_surface_mapping_complete` | `met` | Every live DEV, WORKSHOP, FOUNDRY, and VAULT runtime surface relevant to Athanor has one declared ownership lane. | `config/automation-backbone/runtime-ownership-contract.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `vault_operator_access_non_browser` | `met` | VAULT maintenance must be reachable through repo-owned helpers instead of depending on the browser terminal. | `scripts/vault-ssh.py`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md` |
| `dashboard_shadow_unit_retired_or_recovery_only` | `met` | The inactive athanor-dashboard.service unit must be explicitly retired or downgraded to recovery-only so it cannot be mistaken for the active dashboard deployment path. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `repo_to_runtime_sync_packet_explicit` | `met` | The code path from C:/Athanor to /home/shaun/repos/athanor must have one explicit sync packet with verification and rollback instead of generic dirty-repo drift. | `docs/operations/REPO-ROOTS-REPORT.md`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |
| `opt_root_deploy_contract_complete` | `met` | Each active /opt/athanor surface on DEV, WORKSHOP, and FOUNDRY must declare source path, deploy mode, verification, and rollback contract. | `reports/truth-inventory/latest.json`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, `config/automation-backbone/runtime-ownership-packets.json`, `docs/operations/RUNTIME-OWNERSHIP-PACKETS.md` |

## Execution Packets

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
| `dev-runtime-ssh-access-recovery-packet` | `ready_for_approval` | `dev-runtime-state` | `runtime_host_reconfiguration` | Restore one governed DEV SSH access path so truth collection, runtime verification, and repo-root maintenance no longer depend on a broken alias or remembered fallback guesses. |
| `foundry-agents-runtime-alignment-packet` | `ready_for_approval` | `foundry-agents-compose` | `runtime_host_reconfiguration` | Reconcile the live /opt/athanor/agents source tree and imported `athanor_agents` module path with implementation authority when the truth collector reports a source/runtime mismatch. |
