# VAULT Storage Architecture

*NVMe and HDD allocation on VAULT (.203)*

Last updated: 2026-03-14

---

## NVMe Layout (5x ~1TB)

| NVMe | Model | Pool | Mount | Used | Free | Purpose |
|------|-------|------|-------|------|------|---------|
| nvme0 | Samsung 990 EVO+ 1TB | appdata | `/mnt/appdatacache` | 607G (66%) | 322G | Container configs, databases |
| nvme1 | Crucial P310 1TB | transcode | `/mnt/transcode` | 4.7G (1%) | 925G | Plex transcode scratch |
| nvme2 | Samsung 990 EVO+ 1TB | vms | `/mnt/vms` | ~0 | 930G | **Repurposed:** backup staging, overflow |
| nvme3 | Samsung 990 EVO+ 1TB | docker | `/var/lib/docker` | 117G (13%) | 810G | Docker images, layers, build cache |
| nvme4 | Samsung 990 EVO+ 1TB | fastdata | `/mnt/fastdata` | ~0 | 930G | **New pool:** fast data, DB overflow |

**Total NVMe:** ~4.6TB. **Available fast storage:** 2.78TB (nvme1 + nvme2 + nvme4).

### Appdata Consumers (nvme0)

| Service | Size | Growth Rate | Notes |
|---------|------|-------------|-------|
| Stash | 79G | Low (metadata only) | Largest consumer |
| Plex | 12G | Slow | Metadata, thumbnails |
| Prometheus | 1.8G | Slow (15d retention) | Time-series DB |
| Loki | 840M | Slow | Log aggregation |
| Neo4j | 520M | Slow | Knowledge graph |
| Redis | 59M | Minimal | State/cache |
| Other (17 services) | ~2G | Minimal | Configs only |

### HDD Array (9 disks, 164TB raw)

| Disk | Size | Used | Free |
|------|------|------|------|
| disk1-2 | 17T ea | 14-15T (86-88%) | 2.1-2.5T |
| disk3-8 | 19T ea | 15-16T (82-87%) | 2.6-3.4T |
| disk9 | 22T | 19T (85%) | 3.4T |
| **Total (shfs)** | **164T** | **139T (85%)** | **26T** |

---

## Executed Changes (Session 59)

### nvme4: Reclaimed from orphaned Ubuntu

Ubuntu LVM install (dead weight, unmounted) was fully wiped and repurposed:

1. LVM teardown: `lvremove` → `vgremove` → `pvremove`
2. Partition table wiped, new GPT + single partition created
3. Formatted as btrfs (`mkfs.btrfs -f -L fastdata`)
4. Unraid pool config created: `/boot/config/pools/fastdata.cfg`
5. Mount persisted in `/boot/config/go`

**Directory structure:**
```
/mnt/fastdata/
├── backups/
│   ├── staging/    # NVMe-speed backup writes before HDD copy
│   └── snapshots/  # Point-in-time database snapshots
├── databases/      # DB overflow if appdata fills
└── cache/          # CI artifacts, build cache
```

### nvme2: Repurposed from unused VMs pool

Pool was completely empty (no VMs run on VAULT). Pool name remains "vms" in Unraid (renaming requires array stop, not worth downtime). Repurposed with new directory structure:

```
/mnt/vms/
├── backup-staging/  # Secondary backup staging
├── db-overflow/     # Database overflow
├── build-cache/     # Docker/CI build artifacts
└── model-cache/     # Model weights if needed for A380 inference
```

### nvme1: Kept as transcode (no change)

Plex uses this for transcoding scratch space. Usage is bursty (low average, high peak during concurrent streams). Dedicated NVMe prevents I/O contention with appdata. 925G headroom is appropriate — transcode of multiple 4K HDR streams can consume significant temporary space.

---

## Pool Allocation Strategy

| Pool | Drive(s) | Capacity | Primary Use | Secondary Use |
|------|----------|----------|-------------|---------------|
| **appdata** | nvme0 | 932G | All container configs + databases | — |
| **docker** | nvme3 | 932G | Docker images, layers, build cache | — |
| **fastdata** | nvme4 | 932G | Backup staging, DB snapshots | CI artifacts |
| **vms** | nvme2 | 932G | Backup overflow, model cache | Build cache |
| **transcode** | nvme1 | 932G | Plex transcode scratch | — |

### Why Not Merge nvme2 + nvme4?

Merging into a multi-disk btrfs pool requires stopping the Unraid array (taking down all 44 containers). The benefit (1.86TB contiguous vs 2x 930G separate) doesn't justify the downtime. Both drives are individually large enough for any single workload. If a future use case genuinely needs >930G contiguous NVMe space, merge then.

---

## Autonomous Maintenance

| Job | Schedule | Script | Location |
|-----|----------|--------|----------|
| Container watchdog | */5 min | `container-watchdog.sh` | VAULT cron |
| Docker prune | Monthly (1st, 3AM) | inline | VAULT `/boot/config/go` |
| Backup rotation | Per-service (7-14d) | `backup-*.sh` | VAULT cron |
| Disk usage alerts | Continuous | Prometheus rules | Grafana |
| Appdata monitoring | Continuous | Prometheus | Alert at 85% |

---

## Future Considerations

1. **Backup staging migration:** Route backup scripts to write to `/mnt/fastdata/backups/staging/` first, then async-copy to HDD. Faster backup windows, reduced HDD I/O during backups.
2. **Array growth:** At 85%, ~2 years until 90% at current growth. Next expansion: replace smallest disks (17T) with 22T+.
3. **Model cache:** If A380 inference becomes useful, cache model weights on `/mnt/vms/model-cache/` for fast loading.
4. **Pool merge:** If a workload needs >930G contiguous NVMe, merge nvme2+nvme4 during a planned maintenance window.
