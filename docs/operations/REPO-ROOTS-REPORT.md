# Repo Roots Report

Generated from `config/automation-backbone/repo-roots-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-06.1`
- Roots tracked: `17`

| Root | Host | Authority | Status | Scope |
| --- | --- | --- | --- | --- |
| `desk-main` | `desk` | `implementation-authority` | `active` | durable config, contracts, inventories, validators, and canonical current-state docs |
| `dev-runtime-repo` | `dev` | `runtime-authority` | `active` | live deployed repo and service runtime truth |
| `dev-opt-athanor` | `dev` | `runtime-state` | `active` | deployed application code and support assets |
| `dev-state` | `dev` | `runtime-state` | `active` | operator and service state |
| `dev-systemd` | `dev` | `runtime-state` | `active` | service unit definitions |
| `dev-cron` | `dev` | `runtime-state` | `active` | cron definitions |
| `dev-logs` | `dev` | `runtime-state` | `active` | service logs |
| `vault-boot-config` | `vault` | `runtime-state` | `active` | persistent Unraid host config, SSH authority, and Docker service settings |
| `vault-appdata` | `vault` | `runtime-state` | `active` | persistent container configs, service state, and operator-managed backups |
| `vault-appdatacache` | `vault` | `runtime-state` | `active` | high-throughput cache, model storage, service volumes, and Redis persistence pressure surface |
| `vault-docker-root` | `vault` | `runtime-state` | `active` | directory-mode Docker root for VAULT containers |
| `foundry-opt-athanor` | `foundry` | `runtime-state` | `active` | deployed compose bundles, runtime source mirrors, and active athanor-agents deployment state |
| `workshop-opt-athanor` | `workshop` | `runtime-state` | `active` | deployed compose bundles and supporting assets for Workshop control-surface, creative, and tenant runtimes |
| `athanor-next` | `desk` | `incubation` | `active` | parallel next-gen experimentation |
| `athanor-devstack` | `desk` | `build-system` | `active` | strategy, prototype services, proving harnesses, migration work, and promotion packets for future Athanor capabilities |
| `codex-home` | `desk` | `operator-local` | `active` | global assistant behavior, automations, migration audits, and workstation-local control surfaces |
| `desk-legacy` | `desk` | `vestigial` | `inactive` | historical root |

## desk-main

- Path: `C:/Athanor`
- Host: `desk`
- Authority: `implementation-authority`
- Notes: `Primary code and control-plane root.`
- Local dirty file count: `3`
- Local dirty sample: ` M config/automation-backbone/completion-program-registry.json`, ` M scripts/tests/test_write_steady_state_status.py`, ` M scripts/write_steady_state_status.py`

## dev-runtime-repo

- Path: `/home/shaun/repos/athanor`
- Host: `dev`
- Authority: `runtime-authority`
- Notes: `Runtime and deployment root until deployment is mirror-clean.`, `Observed 2026-04-02 runtime probe shows the retired governor-facade caller set still mirror-clean with zero sync-required runtime-owned callers.`, `Repo-root systemd services on DEV still launch from this root while the active command-center container is deployed from /opt/athanor/dashboard.`, `Broader runtime-owned deployment surfaces still live across the DEV runtime repo and /opt/athanor, but the runtime-ownership contract now governs that split explicitly so it is governed maintenance rather than a promotion blocker.`
- DEV runtime probe: `unable to reach DEV via ssh`
- DEV SSH targets attempted: `dev`, `shaun@192.168.1.189`
- DEV SSH failure samples: `dev` -> `Traceback (most recent call last):`, `shaun@192.168.1.189` -> `shaun@192.168.1.189: Permission denied (publickey,password).`

## dev-opt-athanor

- Path: `/opt/athanor`
- Host: `dev`
- Authority: `runtime-state`
- Notes: `Observed 2026-04-02 entries include the active dashboard compose bundle, heartbeat runtime, draftsman, and helper scripts.`, `The active dashboard container now runs from /opt/athanor/dashboard even though the legacy athanor-dashboard.service unit still points at the runtime repo and remains inactive.`

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

## vault-boot-config

- Path: `/boot/config`
- Host: `vault`
- Authority: `runtime-state`
- Notes: `Root SSH authority is persisted under /boot/config/ssh/root/authorized_keys.`, `Observed 2026-04-02 operator access restoration now keeps VAULT maintenance reachable through repo-owned SSH helpers instead of browser-only terminal access.`

## vault-appdata

- Path: `/mnt/user/appdata`
- Host: `vault`
- Authority: `runtime-state`
- Notes: `LiteLLM config and backups live under /mnt/user/appdata/litellm.`, `Service-specific state and maintenance packets now reference this root explicitly instead of assuming operator memory.`

## vault-appdatacache

- Path: `/mnt/appdatacache`
- Host: `vault`
- Authority: `runtime-state`
- Notes: `Observed 2026-04-02 Redis persistence audit reads Docker data, backups, stash-generated artifacts, and ComfyUI model pressure from this root.`, `Redis recovered, but historical no-space persistence evidence and current top consumers still live here.`

## vault-docker-root

- Path: `/mnt/docker`
- Host: `vault`
- Authority: `runtime-state`
- Notes: `Observed 2026-04-02 recovery confirms VAULT Docker runs in directory mode at /mnt/docker, not docker.img.`, `The disabled array HDD was not the Docker root blocker; Docker root is the NVMe-backed Btrfs mount.`

## foundry-opt-athanor

- Path: `/opt/athanor`
- Host: `foundry`
- Authority: `runtime-state`
- Notes: `Observed 2026-04-02 FOUNDRY runtime probe shows the live athanor-agents compose bundle rooted at /opt/athanor/agents.`, `The installed Python package under /usr/local/lib/python3.12/site-packages/athanor_agents is the expected image layout for this lane, while /workspace remains a read-only runtime mirror.`
- Compose root matches expected: `True`
- Build root clean: `True`
- Container running: `True`
- Runtime import path: `/usr/local/lib/python3.12/site-packages/athanor_agents/__init__.py`
- Runtime source-tree mismatches: `1`
- Site-packages import is expected image layout; treat source-tree mismatch, not the import location alone, as the blocker.
- Active alignment blocker: `src/athanor_agents`

## workshop-opt-athanor

- Path: `/opt/athanor`
- Host: `workshop`
- Authority: `runtime-state`
- Notes: `Observed deployment-drift evidence covers live Workshop compose roots under /opt/athanor/dashboard, /opt/athanor/ws-pty-bridge, /opt/athanor/vllm-node2, /opt/athanor/open-webui, /opt/athanor/comfyui, /opt/athanor/eoq, and /opt/athanor/ulrich-energy.`, `The Workshop dashboard root is not the canonical command center anymore, but it still carries the live ws-pty-bridge surface and recovery-only dashboard state.`

## athanor-next

- Path: `C:/Users/Shaun/dev/athanor-next`
- Host: `desk`
- Authority: `incubation`
- Notes: `Cannot silently become primary.`

## athanor-devstack

- Path: `C:/athanor-devstack`
- Host: `desk`
- Authority: `build-system`
- Notes: `Primary capability forge for future Athanor development.`, `Cannot define live operational truth without an explicit promotion packet and Athanor-side canonical representation.`

## codex-home

- Path: `C:/Users/Shaun/.codex`
- Host: `desk`
- Authority: `operator-local`
- Notes: `Operator-local and cross-repo only.`, `Must not silently become Athanor or devstack project truth.`

## desk-legacy

- Path: `C:/Users/Shaun/athanor`
- Host: `desk`
- Authority: `vestigial`
- Notes: `Treat as non-authoritative unless explicitly promoted.`

## Known Drift

- `implementation-runtime-split` (medium): Implementation truth, runtime authority, and deployed runtime state still live in different roots. The runtime-ownership contract now governs that split explicitly, so it remains governed maintenance debt rather than a full-system autonomy blocker.
- `workshop-runtime-surface-drift` (medium): Workshop runtime compose surfaces are now explicit roots, but several live configs under /opt/athanor still drift from implementation authority and require governed per-surface reconciliation instead of ad hoc node memory.

## Retired Drift

- `dev-governor-facade-runtime-lag` (medium): The 2026-03-29 DEV cutover retired athanor-governor.service, removed the :8760 listener, and synced the mapped runtime-owned helper consumers back to implementation authority.
- `foundry-agents-package-source-split` (medium): The FOUNDRY athanor-agents lane is now governed explicitly as a compose deployment rooted at /opt/athanor/agents. Imports from /usr/local/lib/python3.12/site-packages/athanor_agents are expected image layout, and ordinary updates must go through the repo-owned compose deploy path instead of ad hoc site-packages hotfixes.
