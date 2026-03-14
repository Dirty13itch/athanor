# VAULT Storage Architecture

*Design document for NVMe and HDD allocation on VAULT (.203)*

Last updated: 2026-03-14

---

## Current Layout

### NVMe Drives (5x ~1TB)

| NVMe | Model | Mount | Used | Free | Purpose |
|------|-------|-------|------|------|---------|
| nvme0 | Samsung 990 EVO+ 1TB | `/mnt/appdatacache` | 605G (66%) | 324G | Appdata — all container configs, databases |
| nvme1 | Samsung 990 EVO+ 1TB | `/mnt/transcode` | 4.7G (1%) | 925G | Plex transcode scratch space |
| nvme2 | Samsung 990 EVO+ 1TB | `/mnt/vms` | 5.8M (0%) | 930G | VM images — **completely unused** |
| nvme3 | Crucial P310 1TB | `/var/lib/docker` | 116G (13%) | 811G | Docker images, layers, build cache |
| nvme4 | Samsung 990 EVO+ 1TB | *(unmounted)* | — | — | Orphaned Ubuntu LVM install — **dead weight** |

**Total NVMe capacity:** ~4.6TB. **Actually utilized:** ~726G (16%). **Wasted:** ~2.85TB on nvme1/nvme2/nvme4.

### HDD Array (9 disks, 164TB raw)

| Disk | Size | Used | Free |
|------|------|------|------|
| disk1 | 17T | 15T (88%) | 2.1T |
| disk2 | 17T | 14T (86%) | 2.5T |
| disk3-8 | 19T ea | 15-16T (82-87%) | 2.6-3.4T |
| disk9 | 22T | 19T (85%) | 3.4T |
| **Total (shfs)** | **164T** | **139T (85%)** | **26T** |

### Appdata Consumers (nvme0)

| Service | Size | Growth Rate | Notes |
|---------|------|-------------|-------|
| Stash | 79G | Low (metadata only) | Largest consumer by far |
| Plex | 12G | Slow | Metadata, thumbnails |
| Prometheus | 1.8G | Slow (15d retention) | Time-series DB |
| Loki | 840M | Slow | Log aggregation |
| Neo4j | 520M | Slow | Knowledge graph |
| Redis | 59M | Minimal | State/cache |
| Other (17 services) | ~2G | Minimal | Configs only |

---

## Problems

1. **3 NVMe drives are effectively wasted:**
   - nvme1 (transcode): 925G free, only used during active Plex transcoding — maybe hours per week
   - nvme2 (VMs): 930G free, completely unused — no VMs run on VAULT
   - nvme4: Orphaned Ubuntu install, not even mounted by Unraid

2. **No separation of concerns on appdata (nvme0):**
   - Stash (79G media metadata) shares the same drive as Prometheus, Neo4j, Redis
   - A runaway Stash import could starve database services
   - No I/O isolation between latency-sensitive databases and bulk metadata

3. **Array at 85%:** Comfortable now but worth monitoring. At typical growth (~5-10TB/year from media), you'd hit 90% in 1-2 years.

4. **Docker images accumulate:** CI pipelines (field-inspect) produce candidate images that aren't cleaned up. Added to Docker prune TODO.

---

## Recommended Changes

### Option A: Minimal (Reclaim nvme4)

Format nvme4, add to Unraid as a second cache pool. Use it for:
- Database backups (currently on HDD array — slow for point-in-time recovery)
- Docker build cache overflow

**Effort:** 15 min in Unraid UI. **Impact:** Recover 1TB NVMe. Physical: Shaun wipes the Ubuntu partition via Unraid.

### Option B: Restructure Cache Pools (Recommended)

Reorganize NVMe into purpose-built Unraid cache pools:

| Pool | Drives | Mount | Purpose |
|------|--------|-------|---------|
| **appdata** | nvme0 | `/mnt/appdatacache` | Container configs + databases (keep as-is) |
| **docker** | nvme3 | `/var/lib/docker` | Docker images/layers (keep as-is) |
| **fast-data** | nvme2 + nvme4 | `/mnt/fast` | Databases that need NVMe I/O: backup staging, Qdrant snapshots, LangFuse ClickHouse |
| **transcode** | nvme1 | `/mnt/transcode` | Plex transcode (keep as-is, or merge into fast-data) |

This gives 1.86TB of fast-data pool for:
- Backup staging (write backups to NVMe, async-copy to HDD)
- Database overflow (if Stash or Prometheus grows beyond expectations)
- CI artifacts and build cache
- Model cache (if we ever run inference on VAULT's A380)

**Effort:** 1-2 hours. Shaun formats nvme4 via Unraid UI, creates new cache pool, moves shares.

### Option C: Maximum Consolidation

Merge nvme1 + nvme2 + nvme4 into a single 2.8TB BTRFS pool. Use for everything that currently doesn't have dedicated NVMe (backups, fast-data, overflow). Keep nvme0 (appdata) and nvme3 (docker) as-is.

**Effort:** Same as B but with a 3-drive pool.

---

## Autonomous Maintenance

The container-watchdog.sh (deployed) handles crash-loop recovery. Additional automated maintenance:

- **Docker prune cron:** Monthly cleanup of unused images/build cache (prevents nvme3 bloat)
- **Backup rotation:** Already deployed (7-14 day retention per service)
- **Disk usage alerts:** Prometheus alerts at 85%/95% on `/mnt/user` (already deployed)
- **Appdata monitoring:** Could add nvme0 usage alert (currently at 66%, no urgency)

---

## Decision Needed (Shaun)

1. Can I format nvme4 (orphaned Ubuntu)? This is destructive but the partition is dead.
2. Preference between Option A/B/C for cache pool restructuring?
3. Any data on nvme2 (/mnt/vms) that should be preserved before repurposing?
