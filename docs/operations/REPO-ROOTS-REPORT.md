# Repo Roots Report

Generated from `config/automation-backbone/repo-roots-registry.json` by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

## Summary

- Registry version: `2026-04-02.5`
- Roots tracked: `14`

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
| `athanor-next` | `desk` | `incubation` | `active` | parallel next-gen experimentation |
| `desk-legacy` | `desk` | `vestigial` | `inactive` | historical root |

## desk-main

- Path: `C:/Athanor`
- Host: `desk`
- Authority: `implementation-authority`
- Notes: `Primary code and control-plane authority.`
- Local dirty file count: `0`
- Local dirty sample: none

## dev-runtime-repo

- Path: `/home/shaun/repos/athanor`
- Host: `dev`
- Authority: `runtime-authority`
- Notes: `Runtime and deployment authority until deployment is mirror-clean.`, `Observed 2026-04-02 runtime probe shows the retired governor-facade caller set still mirror-clean with zero sync-required runtime-owned callers.`, `Repo-root systemd services on DEV still launch from this root while the active command-center container is deployed from /opt/athanor/dashboard.`, `Broader runtime-owned deployment surfaces still live across the DEV runtime repo and /opt/athanor, but the runtime-ownership contract now governs that split explicitly so it is governed maintenance rather than a promotion blocker.`
- Runtime dirty file count: `0`
- Runtime dirty sample: none

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

- `implementation-runtime-split` (medium): Implementation truth, runtime authority, and deployed runtime state still live in different roots. The runtime-ownership contract now governs that split explicitly, so it remains governed maintenance debt rather than a full-system autonomy blocker.

## Retired Drift

- `dev-governor-facade-runtime-lag` (medium): The 2026-03-29 DEV cutover retired athanor-governor.service, removed the :8760 listener, and synced the mapped runtime-owned helper consumers back to implementation authority.
- `foundry-agents-package-source-split` (medium): The FOUNDRY athanor-agents lane is now governed explicitly as a compose deployment rooted at /opt/athanor/agents. Imports from /usr/local/lib/python3.12/site-packages/athanor_agents are expected image layout, and ordinary updates must go through the repo-owned compose deploy path instead of ad hoc site-packages hotfixes.
