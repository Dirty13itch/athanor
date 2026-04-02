# VAULT Redis Repair Packet

Generated from the cached truth snapshot plus the read-only VAULT Redis audit by `scripts/generate_truth_inventory_reports.py`.
Do not edit manually.

- Cached truth snapshot: `2026-04-02T19:40:35.257979+00:00`
- Cached redis audit: `2026-04-02T19:40:35Z`
- Surface id: `vault-redis-persistence`
- Host: `vault`
- Runtime owner surface: `standalone_docker_container`
- Container: `redis`
- Container image: `redis:7-alpine`
- Restart policy: `unless-stopped`
- Data mount source: `/mnt/appdatacache/appdata/redis`
- Data mount destination: `/data`
- Reconciliation runbook: [redis-reconciliation.md](/C:/Athanor/docs/runbooks/redis-reconciliation.md)
- Companion snapshot: [latest.json](/C:/Athanor/reports/truth-inventory/latest.json)

## Current Runtime Truth

- Persistence blocker code: `healthy`
- Persistence blocker detail: Redis persistence audit is healthy.
- Latest temp-RDB no-space error: ``
- Latest background-save error: ``
- Latest cross-protocol warning: ``
- Temp-RDB no-space error count in audit tail: `0`
- Background-save error count in audit tail: `0`
- Cross-protocol warning count in audit tail: `0`
- Redis data directory size: `20.14 MiB`
- Filesystem device: `/dev/nvme0n1p1`
- Filesystem size: `931.51 GiB`
- Filesystem used: `929.92 GiB`
- Filesystem available: `179.37 MiB`
- Filesystem used percent: `100%`
- Filesystem mountpoint: `/mnt/appdatacache`
- Btrfs device allocated: `931.51GiB`
- Btrfs device unallocated: `1.02MiB`
- Btrfs free estimate: `179.37MiB	(min: 179.37MiB)`
- Next live action: No Redis repair action required.

## Largest Consumers On The Backing Filesystem

### /mnt/appdatacache

- `/mnt/appdatacache/appdata`: `347.94 GiB`
- `/mnt/appdatacache/backups`: `284.92 GiB`
- `/mnt/appdatacache/models`: `252.75 GiB`
- `/mnt/appdatacache/system`: `18.80 GiB`
- `/mnt/appdatacache/dev`: `3.80 GiB`
- `/mnt/appdatacache/databases`: `1.32 GiB`
- `/mnt/appdatacache/n8n`: `315.40 MiB`
- `/mnt/appdatacache/ulrich-energy-website`: `131.78 MiB`

### /mnt/appdatacache/appdata

- `/mnt/appdatacache/appdata/stash`: `309.79 GiB`
- `/mnt/appdatacache/appdata/plex`: `23.30 GiB`
- `/mnt/appdatacache/appdata/tdarr`: `3.97 GiB`
- `/mnt/appdatacache/appdata/loki`: `3.82 GiB`
- `/mnt/appdatacache/appdata/prometheus`: `3.72 GiB`
- `/mnt/appdatacache/appdata/Field Inspect`: `1.45 GiB`
- `/mnt/appdatacache/appdata/sonarr`: `951.61 MiB`
- `/mnt/appdatacache/appdata/neo4j`: `521.32 MiB`

### /mnt/appdatacache/backups (top files)

- `/mnt/appdatacache/backups/stash_2026-04-02.tar.gz`: `264.14 GiB`
- `/mnt/appdatacache/backups/plex_2026-04-02.tar.gz`: `19.55 GiB`
- `/mnt/appdatacache/backups/sonarr_2026-04-02.tar.gz`: `386.25 MiB`
- `/mnt/appdatacache/backups/sonarr_2026-04-01.tar.gz`: `378.86 MiB`
- `/mnt/appdatacache/backups/sonarr_2026-03-31.tar.gz`: `360.51 MiB`
- `/mnt/appdatacache/backups/homeassistant_2026-04-01.tar.gz`: `13.65 MiB`
- `/mnt/appdatacache/backups/homeassistant_2026-03-31.tar.gz`: `13.28 MiB`
- `/mnt/appdatacache/backups/homeassistant_2026-04-02.tar.gz`: `12.41 MiB`

### /mnt/appdatacache/appdata/stash/generated

- `/mnt/appdatacache/appdata/stash/generated/screenshots`: `122.14 GiB`
- `/mnt/appdatacache/appdata/stash/generated/thumbnails`: `82.96 GiB`
- `/mnt/appdatacache/appdata/stash/generated/vtt`: `57.77 GiB`
- `/mnt/appdatacache/appdata/stash/generated/markers`: `30.80 GiB`
- `/mnt/appdatacache/appdata/stash/generated/blobs`: `11.49 GiB`
- `/mnt/appdatacache/appdata/stash/generated/transcodes`: `0 B`
- `/mnt/appdatacache/appdata/stash/generated/download_stage`: `0 B`
- `/mnt/appdatacache/appdata/stash/generated/interactive_heatmaps`: `0 B`

### /mnt/appdatacache/models/comfyui

- `/mnt/appdatacache/models/comfyui/checkpoints`: `78.74 GiB`
- `/mnt/appdatacache/models/comfyui/unet`: `61.39 GiB`
- `/mnt/appdatacache/models/comfyui/clip`: `17.33 GiB`
- `/mnt/appdatacache/models/comfyui/text_encoders`: `12.30 GiB`
- `/mnt/appdatacache/models/comfyui/loras`: `10.57 GiB`
- `/mnt/appdatacache/models/comfyui/infinite_you`: `6.13 GiB`
- `/mnt/appdatacache/models/comfyui/clip_vision`: `2.35 GiB`
- `/mnt/appdatacache/models/comfyui/controlnet`: `2.33 GiB`

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
