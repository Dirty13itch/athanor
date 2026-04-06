# VAULT Redis Repair Packet

Generated from the cached truth snapshot plus the read-only VAULT Redis audit by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Cached truth snapshot: `2026-04-03T03:48:09.972834+00:00`
- Cached redis audit: `2026-04-03T03:47:59Z`
- Surface id: `vault-redis-persistence`
- Host: `vault`
- Runtime owner surface: `standalone_docker_container`
- Container: `redis`
- Container image: ``
- Restart policy: ``
- Data mount source: ``
- Data mount destination: `/data`
- Reconciliation runbook: [redis-reconciliation.md](/C:/Athanor/docs/runbooks/redis-reconciliation.md)
- Companion snapshot: [latest.json](/C:/Athanor/reports/truth-inventory/latest.json)

## Current Runtime Truth

- Persistence blocker code: `probe_failed`
- Persistence blocker detail: SSH error: Authentication failed.
- Latest temp-RDB no-space error: ``
- Latest background-save error: ``
- Latest cross-protocol warning: ``
- Temp-RDB no-space error count in audit tail: `0`
- Background-save error count in audit tail: `0`
- Cross-protocol warning count in audit tail: `0`
- Redis data directory size: `unknown`
- Filesystem device: `unknown`
- Filesystem size: `unknown`
- Filesystem used: `unknown`
- Filesystem available: `unknown`
- Filesystem used percent: `unknown`
- Filesystem mountpoint: `unknown`
- Btrfs device allocated: `unknown`
- Btrfs device unallocated: `unknown`
- Btrfs free estimate: `unknown`
- Next live action: Re-run the VAULT Redis audit and verify docker inspect plus filesystem probes on VAULT.

## Largest Consumers On The Backing Filesystem

### /mnt/appdatacache

- No appdatacache consumer census is available in the current audit.

### /mnt/appdatacache/appdata

- No appdata consumer census is available in the current audit.

### /mnt/appdatacache/backups (top files)

- No backup-file census is available in the current audit.

### /mnt/appdatacache/appdata/stash/generated

- No stash/generated consumer census is available in the current audit.

### /mnt/appdatacache/models/comfyui

- No ComfyUI model census is available in the current audit.

## Interpretation

The live blocker is not Redis logical drift. It is Redis persistence failure on VAULT: Redis cannot create temporary RDB files on the current `/data` backing store.
The new storage census shows the pressure is not coming from Redis itself. Redis is roughly tens of megabytes, while the backing volume is dominated by `appdata`, `models`, `backups`, and `system`, and within `appdata` the largest paths are `stash`, `plex`, `tdarr`, `loki`, and `prometheus`.
The current lowest-risk recovery candidates are the dated `backups` tarballs, especially the large `stash_*` and `plex_*` archives, because they can be moved or pruned before touching live `stash/generated` artifacts or live ComfyUI model weights.
The repeated `Possible SECURITY ATTACK` warnings from FOUNDRY were a separate health-probe bug. Those warnings stopped after the agent health probe was changed to use a real Redis `PING`, so they are no longer the primary blocker.

## Approved Maintenance Sequence

1. Re-run the read-only Redis audit and confirm the blocker is still `rdb_temp_file_no_space` before touching VAULT runtime state.
2. Confirm the `/data` bind mount and backing filesystem posture on VAULT, including current filesystem availability and Btrfs allocation state.
3. Recover or expand allocatable space on the backing appdatacache filesystem. Start with the least disruptive high-yield targets in `/mnt/appdatacache/backups`, especially the dated `stash_*` and `plex_*` tarballs, before touching live `stash/generated` artifacts or live ComfyUI model weights.
4. Once space has been recovered, verify Redis can create temp RDB files again and that `BGSAVE` or the next automatic save completes without `MISCONF`.
5. Only if persistence remains blocked after space recovery, treat container relocation, bind-mount change, or Redis data-path reconfiguration as a separate approved maintenance step.
6. Re-run the Redis audit, truth collector, generated reports, and live health probe so the dependency blocker clears from evidence instead of operator memory.

## Read-Only Verification Commands

```powershell
python scripts/vault_redis_audit.py --write reports/truth-inventory/vault-redis-audit.json
python scripts/collect_truth_inventory.py
python scripts/generate_truth_inventory_reports.py --report vault_redis_repair_packet
python scripts/validate_platform_contract.py
ssh foundry "curl -sS http://localhost:9000/health"
```

## Live Repair Commands To Use During The Approved Maintenance Window

```powershell
python scripts/vault-ssh.py "docker inspect redis > /mnt/user/appdata/redis/redis.inspect.$(date +%Y%m%d-%H%M%S).json"
python scripts/vault-ssh.py "df -h /mnt/appdatacache /mnt/appdatacache/appdata/redis"
python scripts/vault-ssh.py "btrfs filesystem usage /mnt/appdatacache"
python scripts/vault-ssh.py "du -x -B1 -d1 /mnt/appdatacache 2>/dev/null | sort -n | tail -12"
python scripts/vault-ssh.py "du -x -B1 -d1 /mnt/appdatacache/appdata 2>/dev/null | sort -n | tail -15"
python scripts/vault-ssh.py "du -sh /mnt/appdatacache/appdata/redis"
python scripts/vault-ssh.py "docker exec redis redis-cli LASTSAVE"
python scripts/vault-ssh.py "docker exec redis redis-cli INFO persistence"
```
