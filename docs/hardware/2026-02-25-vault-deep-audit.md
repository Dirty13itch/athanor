# VAULT Deep Audit -- 2026-02-25

Exhaustive hardware and service audit of VAULT (192.168.1.203). All data gathered via live SSH commands using `scripts/vault-ssh.py`.

**Auditor:** Claude (automated)
**Date:** 2026-02-25
**Uptime at audit:** 2 days, 14 hours
**OS:** Unraid 6.12.54 (kernel 6.12.54-Unraid)

---

## 1. CPU

| Field | Documented | Observed | Status |
|-------|-----------|----------|--------|
| Model | AMD Ryzen 9 9950X | AMD Ryzen 9 9950X 16-Core Processor | VERIFIED |
| Cores/Threads | 16C/32T | 16C/32T | VERIFIED |
| Socket | AM5 | AM5 (via motherboard) | VERIFIED |
| Architecture | Zen 5 | Family 26, Model 68 (Granite Ridge / Zen 5) | VERIFIED |
| Max Boost | 5.75 GHz | 5752 MHz | VERIFIED |
| TDP | 170W | Not directly measurable via SSH | -- |
| Governor | -- | `performance` | NOTED |
| Current scaling | -- | 27% (idle) | NOTED |
| L3 Cache | -- | 64 MiB (2 instances, 32 MiB per CCD) | NOTED |

**Assessment:** CPU is correctly documented and running in performance governor mode. At 27% scaling during idle, power management is working. 16C/32T is massive overkill for a storage/services server -- CPU utilization is near zero across all containers (highest: Redis at 0.27%, Neo4j at 0.53%). This is by design -- the 9950X was chosen for the AM5 platform and PCIe 5.0, not for compute demand.

---

## 2. Motherboard

| Field | Documented | Observed | Status |
|-------|-----------|----------|--------|
| Board | ASUS ProArt X870E-CREATOR WIFI | ASUSTeK ProArt X870E-CREATOR WIFI Rev 1.xx | VERIFIED |
| 5GbE | Aquantia 5GbE | AQtion AQC113CS 5GbE (confirmed) | VERIFIED |
| 2.5GbE | Intel 2.5GbE | Intel I226-V (confirmed) | VERIFIED |
| WiFi | WiFi 7 | MediaTek MT7927 (present, not audited for use) | VERIFIED |

---

## 3. Memory

| Field | Documented | Observed | Status |
|-------|-----------|----------|--------|
| Total | 128 GB DDR5 | 123.5 GiB (128 GB, correct after OS overhead) | VERIFIED |
| Configuration | 4x32GB | 4x 32 GB DDR5 (DIMM 0+1 Channel A, DIMM 0+1 Channel B) | VERIFIED |
| Speed | 5600 MT/s | 5600 MT/s configured | VERIFIED |
| Manufacturer | -- | Micron (all 4 sticks) | NOTED |
| Part Number | Micron CP32G60C40U5B.M8B3 | Matches Micron Bank 1, Hex 0x2C | VERIFIED |
| ECC | None (UDIMM) | Error Correction Type: None | VERIFIED |
| Swap | -- | 0 B (no swap configured) | NOTED |

**Memory usage:** 7.4 GiB used / 123.5 GiB total (6%). 115 GiB in buff/cache (filesystem cache for array), 116 GiB available. No swap. This is optimal -- the large RAM pool serves as read cache for the storage array.

**Top consumers:**
| Container | Memory |
|-----------|--------|
| Neo4j | 1.08 GiB |
| Plex | 1008 MiB |
| LiteLLM | 662 MiB |
| Home Assistant | 586 MiB |
| Grafana | 297 MiB |
| Prometheus | 225 MiB |
| Radarr | 172 MiB |
| Sonarr | 163 MiB |
| All others | < 130 MiB each |

**Total container memory:** ~4.3 GiB. Leaves ~119 GiB for filesystem cache. Excellent.

---

## 4. GPU

| Field | Documented | Observed | Status |
|-------|-----------|----------|--------|
| Model | Intel Arc A380 | Intel DG2 [Arc A380] rev 05 | VERIFIED |
| VRAM | 6 GB GDDR6 | Not directly queryable via SSH | -- |
| PCI Slot | -- | 03:00.0 (PCIe bridge at 01:00.0) | NOTED |
| Second GPU | -- | AMD Radeon (Granite Ridge iGPU, 7e:00.0) | NOTED |

**Driver status:** i915 kernel module loaded (3.8 MB, 3 references). `/dev/dri` devices present: card0, card1, renderD128, renderD129. The card0/renderD128 pair is the Arc A380; card1/renderD129 is the Ryzen iGPU.

**Plex transcoding:** Plex container has `/dev/dri` device passthrough (`rwm` permissions). The Arc A380 IS available for hardware transcoding (Intel QuickSync via i915). Plex also has `NVIDIA_DRIVER_CAPABILITIES` env var set, which is irrelevant (no NVIDIA GPU on VAULT) but harmless.

**Arc A380 utilization:** Near zero. Power draw: 13 mW. Fan: 99 RPM. Energy consumed: 784 kJ total since boot. The GPU is available for Plex transcoding but appears idle at audit time (no active transcode sessions).

**Recommendation:** The Arc A380 is properly configured for Plex hardware transcoding. It's doing its job. No action needed. The Ryzen iGPU (Granite Ridge) is unused and could theoretically be disabled in BIOS to save a few watts, but it's negligible.

---

## 5. Storage Array (CRITICAL)

### 5.1 Array Configuration

VAULT runs **Unraid** with a single parity configuration.

| Component | Details |
|-----------|---------|
| Array state | STARTED |
| Parity | 1x WDC WD241KFGX 22TB (sdc) |
| Data disks | 9 (disk1 through disk9) |
| Filesystem | XFS on all data disks |
| Total formatted | ~170T |
| User share (shfs) | 164T total |
| Used | 146T (90%) |
| Free | 18T |
| Sync errors | 0 |
| Last sync | 2026-02-15 (Tue) |

### 5.2 Per-Disk Status

| Slot | Device | Model | Raw Size | Used | Free | Usage | SMART | Temp | Power-On Hours | Errors |
|------|--------|-------|----------|------|------|-------|-------|------|----------------|--------|
| Parity | sdc | WDC WD241KFGX-68CNGN0 | 22 TB | -- | -- | -- | PASSED | 31C | 7,923 | 0 |
| disk1 | sdj | WDC WD181KFGX-68AFPN0 | 16 TB | 15T | 1.5T | 91% | PASSED | -- | 17,406 | 0 |
| disk2 | sdd | WDC WD181KFGX-68AFPN0 | 16 TB | 15T | 1.8T | 90% | PASSED | -- | 17,423 | 0 |
| disk3 | sdk | WDC WD201KFGX-68BKJN0 | 18 TB | 17T | 2.2T | 89% | PASSED | -- | 15,380 | 0 |
| disk4 | sdi | WDC WD201KFGX-68BKJN0 | 18 TB | 17T | 1.4T | 93% | PASSED | -- | 15,364 | 0 |
| disk5 | sdh | WDC WD201KFGX-68BKJN0 | 18 TB | 17T | 1.4T | 93% | PASSED | -- | 15,365 | 0 |
| disk6 | sdg | WDC WD201KFGX-68BKJN0 | 18 TB | 17T | 1.9T | 91% | PASSED | -- | 11,696 | 0 |
| disk7 | sdf | WDC WD201KFGX-68BKJN0 | 18 TB | 16T | 2.4T | 88% | PASSED | 32C | 8,308 | 0 |
| disk8 | sde | ST20000VE002-3G9101 | 18 TB | 16T | 2.8T | 85% | PASSED | 33C | 17,074 | 0 |
| disk9 | sdb | WDC WD241KFGX-68CNGN0 | 22 TB | 20T | 2.8T | 88% | PASSED | 32C | 7,923 | 0 |

**All 10 drives PASSED SMART health. Zero reallocated sectors, zero pending sectors, zero offline uncorrectable across the entire array.**

HDD temperatures: 31-33C. Excellent. Well within operating range.

Power-on hours: The two WD 16TB drives and the Seagate 18TB have the highest hours (~17,000 = ~1.9 years). The newer WD 22TB and some WD 18TB drives are at 7,900-11,700 hours. No drives are near concerning age thresholds.

### 5.3 INVENTORY DISCREPANCY -- HDD Slot Assignments

The inventory (`docs/hardware/inventory.md`) has **3 incorrect disk-to-slot mappings**:

| Slot | Inventory Says | Actually Is | Discrepancy |
|------|---------------|-------------|-------------|
| disk2 | ST20000VE002-3G9101 (Seagate 18TB) | WDC WD181KFGX-68AFPN0 (WD 16TB) | WRONG DRIVE |
| disk7 | WDC WD181KFGX-68AFPN0 (WD 16TB) | WDC WD201KFGX-68BKJN0 (WD 18TB) | WRONG DRIVE |
| disk8 | WDC WD201KFGX-68BKJN0 (WD 18TB) | ST20000VE002-3G9101 (Seagate 18TB) | WRONG DRIVE |

The total drive set is correct (2x WD 22TB, 2x WD 16TB, 5x WD 18TB, 1x Seagate 18TB), but three slot assignments are swapped in the inventory document.

**Corrected mapping for `inventory.md`:**
```
| # | Drive | Capacity | Currently In |
|---|-------|----------|-------------|
| 1 | WDC WD241KFGX-68CNGN0 (SZG8YZNM) | 22 TB | VAULT (parity, sdc) |
| 2 | WDC WD241KFGX-68CNGN0 (SZG25ANM) | 22 TB | VAULT (disk9, sdb) |
| 3 | WDC WD181KFGX-68AFPN0 (4BKNWZKH) | 16 TB | VAULT (disk1, sdj) |
| 4 | WDC WD181KFGX-68AFPN0 (4MHLVJHZ) | 16 TB | VAULT (disk2, sdd) |
| 5 | WDC WD201KFGX-68BKJN0 (9AHEG8AR) | 18 TB | VAULT (disk3, sdk) |
| 6 | WDC WD201KFGX-68BKJN0 (9AHE7HSR) | 18 TB | VAULT (disk4, sdi) |
| 7 | WDC WD201KFGX-68BKJN0 (9AHEP41R) | 18 TB | VAULT (disk5, sdh) |
| 8 | WDC WD201KFGX-68BKJN0 (9AHY9SAR) | 18 TB | VAULT (disk6, sdg) |
| 9 | WDC WD201KFGX-68BKJN0 (9BH41GUE) | 18 TB | VAULT (disk7, sdf) |
| 10 | ST20000VE002-3G9101 (ZVTC0DTH) | 18 TB | VAULT (disk8, sde) |
```

### 5.4 Storage Capacity Analysis

**The array is at 90% capacity (146T / 164T). This warrants attention.**

Most-full disks: disk4 (93%), disk5 (93%) -- only 1.4T free each.
Least-full disks: disk8 (85%, 2.8T free), disk7 (88%, 2.4T free).

Unraid's highwater allocation means new writes go to the disk with the most free space, but all disks are above 85%. Once any disk hits ~95%, writes may start failing for shares that can't split across disks.

**Action items:**
1. Monitor disk4/disk5 closely -- they will hit 95% first.
2. Plan for capacity expansion. The parity drive is 22TB, so data disks up to 22TB can be added. Adding a single 22TB WD Gold would add ~20T usable.
3. There is currently 1 empty array slot (disk10, state DISK_NP_DSBL in mdstat slot 29). The Unraid config shows `SYS_ARRAY_SLOTS=11`, meaning slots 0-10 (parity + 10 data). One slot is available for a new disk without reconfiguration.

### 5.5 NVMe Storage

| Device | Model | Size | Mount | Usage | Wear | Temp | Hours |
|--------|-------|------|-------|-------|------|------|-------|
| nvme0n1 | Samsung 990 EVO Plus 1TB | 932G | /mnt/appdatacache | 121G / 932G (13%) | 0% | 42C | 1,269 |
| nvme1n1 | Samsung 990 EVO Plus 1TB | 932G | /mnt/docker | 5.8M / 932G (~0%) | 0% | 35C | 2,489 |
| nvme2n1 | Crucial P310 1TB (CT1000P310SSD8) | 932G | /mnt/transcode | 5.8M / 932G (~0%) | 6% | 28C | 6,788 |
| nvme3n1 | Samsung 990 EVO Plus 1TB | 932G | /mnt/vms | 5.8M / 932G (~0%) | 0% | 34C | 1,102 |
| nvme4n1 | Samsung 990 EVO Plus 1TB | 932G | **NOT MOUNTED** | Ubuntu LVM partition | 0% | 36C | 941 |

### 5.6 INVENTORY DISCREPANCY -- NVMe Drives

The inventory (`docs/hardware/inventory.md`) claims VAULT has:
- Items #3-6: 4x Samsung 990 EVO Plus (in X870E M.2 slots)
- Items #8-11: 4x Crucial P310 (in Hyper M.2 Gen5 adapter)
- **Total documented: 8 NVMe drives in VAULT**

Reality: **5 NVMe drives detected** (4x Samsung 990 EVO Plus + 1x Crucial P310).

**3 Crucial P310 drives are unaccounted for.** Either they are not installed in the Hyper M.2 adapter (only 1 of 4 slots populated) or they are physically present but not detected. Given that only one CT1000P310SSD8 appears in `lsblk`, the most likely explanation is that only 1 Crucial P310 was installed and the other 3 remain loose or were reallocated.

### 5.7 NVMe Utilization Concern

Three of the five NVMe drives are virtually **empty**:
- `/mnt/docker` (nvme1n1): 5.8 MB used. Unraid Docker uses a 20G loop image on the `system` share, not this mount directly. This drive appears to be allocated but unused by Docker.
- `/mnt/transcode` (nvme2n1): 5.8 MB used. Plex transcode directory -- only populated during active transcoding.
- `/mnt/vms` (nvme3n1): 5.8 MB used. VMs are enabled in Unraid config but no VMs appear to be running.

Additionally, **nvme4n1** has an Ubuntu LVM partition (928.5G) that is not mounted and appears to be a leftover installation. This is a fully wasted 1TB NVMe drive.

**Recommendation:**
- nvme4n1: Wipe the Ubuntu partitions and either add to the Unraid pool or repurpose as a second cache drive.
- nvme1n1 (docker) and nvme3n1 (VMs): Consider whether dedicated mounts are justified. If VMs won't be used, free up nvme3n1.

### 5.8 Docker Storage

Docker uses a 20G loop image (`/mnt/user/system/docker/docker.img`) with overlay2 backing. Currently 9.3G used (48%). The docker image lives on the `system` share which uses `appdatacache` pool (nvme0n1).

This is a standard Unraid Docker configuration. The 20G limit is adequate for 15 containers.

---

## 6. Network

### 6.1 Interfaces

| Interface | Type | Speed | Status | Notes |
|-----------|------|-------|--------|-------|
| eth0 | Aquantia AQC113CS 5GbE | 10,000 Mb/s | UP, slave of bond0 | Primary NIC |
| eth1 | Intel I226-V 2.5GbE | 2,500 Mb/s | UP, slave of bond0 | Secondary NIC |
| bond0 | Bond (eth0 + eth1) | 10,000 Mb/s | UP, master of br0 | Active-backup likely |
| br0 | Bridge (over bond0) | -- | UP | 192.168.1.203/24 |
| docker0 | Docker bridge | -- | UP | 172.17.0.1/16 |
| virbr0 | Libvirt bridge | -- | DOWN (no-carrier) | 192.168.122.1/24, unused |

**MTU:** 1500 on all interfaces (no jumbo frames).

**Assessment:** The bond of 5GbE + 2.5GbE is functional but the 2.5G NIC contributes nothing meaningful in active-backup mode. In balance modes it would cap at 2.5G for its traffic. The primary 5GbE link is the one doing all the heavy lifting for NFS serving.

**Optimization opportunity:** Enable jumbo frames (MTU 9000) on eth0/bond0/br0 and the corresponding switch port on the USW Pro XG 10. This would reduce CPU overhead for NFS traffic and improve throughput by ~10-15% for large sequential transfers. Requires matching MTU on Node 1 and Node 2 NFS clients.

### 6.2 NFS Exports

| Export | Path | Security | Host Restriction | Options |
|--------|------|----------|-----------------|---------|
| system | /mnt/user/system | public | `<world>` (any) | async, rw, root_squash, all_squash |
| models | /mnt/user/models | public | `<world>` (any) | async, rw, root_squash, all_squash |
| data | /mnt/user/data | public | `<world>` (any) | async, rw, root_squash, all_squash |

**Security note:** All three NFS exports are world-readable/writable with no host restrictions. This is acceptable on a trusted home LAN with no untrusted devices, but adding host restrictions (e.g., `192.168.1.0/24` or specific node IPs) would be a low-effort hardening measure.

**The `async` mount option** means NFS writes are acknowledged before they hit disk. This improves performance but means data could be lost on a power failure. For a homelab this is an acceptable tradeoff -- the parity rebuild would recover from disk failure, and a UPS (USP PDU Pro in rack) protects against power loss.

---

## 7. Containers

### 7.1 Container Inventory

15 containers running. MEMORY.md says "13 VAULT containers" -- the 2 voice containers (wyoming-piper, wyoming-openwakeword) added in Session 18 were not counted.

| # | Container | Image | Uptime | CPU % | Memory | Purpose |
|---|-----------|-------|--------|-------|--------|---------|
| 1 | prometheus | prom/prometheus:latest | 26h | 0.00% | 225 MiB | Metrics collection (5 targets) |
| 2 | grafana | grafana/grafana:latest | 26h | 0.25% | 297 MiB | Dashboards |
| 3 | sonarr | linuxserver/sonarr:latest | 26h | 0.03% | 163 MiB | TV management |
| 4 | radarr | linuxserver/radarr:latest | 26h | 0.03% | 172 MiB | Movie management |
| 5 | prowlarr | linuxserver/prowlarr:latest | 26h | 0.03% | 122 MiB | Indexer manager |
| 6 | sabnzbd | linuxserver/sabnzbd:latest | 26h | 0.03% | 57 MiB | Usenet downloader |
| 7 | tautulli | linuxserver/tautulli:latest | 26h | 0.02% | 68 MiB | Plex analytics |
| 8 | stash | stashapp/stash:latest | 26h | 0.09% | 55 MiB | Adult content organizer |
| 9 | homeassistant | home-assistant:stable | 18h | 0.10% | 586 MiB | Home automation |
| 10 | plex | linuxserver/plex:latest | 18h | 0.18% | 1008 MiB | Media server |
| 11 | neo4j | neo4j:5-community | 21h | 0.53% | 1.08 GiB | Graph database |
| 12 | litellm | litellm:main-v1.81.9-stable | 23h | 0.13% | 662 MiB | LLM proxy |
| 13 | redis | redis:7-alpine | 17h | 0.27% | 13.9 MiB | KV store / workspace |
| 14 | wyoming-piper | rhasspy/wyoming-piper | 12h | 0.00% | 35.6 MiB | TTS service |
| 15 | wyoming-openwakeword | rhasspy/wyoming-openwakeword | 12h | 0.00% | 30.9 MiB | Wake word detection |

**All 15 containers healthy (Up state).** Total CPU: ~1.7%. Total memory: ~4.3 GiB.

**Missing expected container:** qBittorrent is not running. This is a known blocker (requires NordVPN credentials from Shaun).

**Not on VAULT:** Qdrant runs on Node 1, not VAULT. This is correct per architecture -- Qdrant benefits from proximity to the agents and vLLM on Node 1.

### 7.2 Container Resource Assessment

No containers have resource limits configured (all show `123.5 GiB` as memory limit = full host RAM). For a homelab this is acceptable, but if Neo4j or Plex ever has a memory leak, it could consume all available RAM and impact the filesystem cache that the storage array depends on.

**Low-priority recommendation:** Set memory limits on the heaviest containers:
- Neo4j: `--memory=4g` (uses ~1G, headroom for queries)
- Plex: `--memory=4g` (uses ~1G, headroom for transcoding)
- LiteLLM: `--memory=2g` (uses ~660M)

---

## 8. Service Health

### 8.1 Redis

| Metric | Value | Assessment |
|--------|-------|------------|
| Version | 7.4.8 | Current |
| Uptime | 16.6 hours | Stable |
| Used memory | 1.40 MB | Minimal |
| Max memory | 512 MB | Appropriate |
| Eviction policy | allkeys-lru | Correct |
| Keys | 9 | Expected |
| Fragmentation ratio | 4.26 | High (see below) |
| Persistence | AOF | Enabled |

**Redis keys:**
```
athanor:gpu:flex_1
athanor:gpu:flex_2
athanor:gpu:creative
athanor:gpu:primary_inference
athanor:tasks
athanor:agents:registry
athanor:workspace
athanor:scheduler:last_run
athanor:workspace:history
```

**Fragmentation ratio of 4.26** is high but not concerning at 1.4 MB absolute usage. This is typical for Redis with very small datasets -- jemalloc allocates in blocks larger than needed. At this scale it wastes perhaps 4 MB, which is irrelevant.

**Assessment:** Redis is healthy and dramatically underutilized. 1.4 MB of 512 MB is 0.27% usage. It's doing exactly what it should -- lightweight workspace state for the GWT system and GPU orchestrator.

### 8.2 Neo4j

| Metric | Value |
|--------|-------|
| HTTP | 200 OK (port 7474) |
| Bolt | port 7687 |
| Appdata size | 517 MB |
| Nodes | 39 (8 Agent, 24 Service, 4 Node, 3 Project) |
| Relationships | 43 (25 RUNS_ON, 8 DEPENDS_ON, 5 MANAGES, 3 ROUTES_TO, 2 USES) |

**Assessment:** Verified. Node and relationship counts match documented state exactly. Database is small and healthy. 517 MB on disk for a 39-node graph is fine.

### 8.3 Prometheus

| Metric | Value |
|--------|-------|
| Scrape targets | 5 (all UP) |
| Appdata size | 178 MB |

**Targets:**
| Target | Health | URL |
|--------|--------|-----|
| node1-gpu | UP | 192.168.1.244:9400/metrics |
| node1-node | UP | 192.168.1.244:9100/metrics |
| node2-gpu | UP | 192.168.1.225:9400/metrics |
| node2-node | UP | 192.168.1.225:9100/metrics |
| prometheus | UP | localhost:9090/metrics |

**Assessment:** All 5 targets healthy. Note: there is no VAULT node-exporter target. VAULT's own system metrics are not being scraped. This is a monitoring gap.

**Recommendation:** Add a VAULT node-exporter instance and scrape target to monitor VAULT disk usage, CPU, memory, and network from Prometheus/Grafana. This is especially important given the array is at 90% capacity.

### 8.4 Home Assistant

| Metric | Value |
|--------|-------|
| HTTP | 200 OK (port 8123) |
| Entities | 43 (per docs) |
| Appdata size | 4.7 MB |

**Warnings in logs:**
- Auth failures from 192.168.1.225 (Node 2 dashboard) and 192.168.1.167 (DEV/WSL). These are known issues from the dashboard health checks using stale/invalid tokens.
- Chromecast connection failures to 192.168.1.166 (TV). The TV may be powered off or unreachable.

### 8.5 LiteLLM

| Metric | Value |
|--------|-------|
| Version | v1.81.9-stable |
| Status | Active, proxying requests |
| Models routed | `reasoning` -> Qwen3-32B-AWQ (Node 1), `embedding` -> Qwen3-Embedding-0.6B (Node 1) |

**Active and processing requests at audit time.** The model name mismatch warnings in the logs are cosmetic -- LiteLLM correctly overrides the downstream model name to match the alias.

### 8.6 Plex

| Metric | Value |
|--------|-------|
| HTTP | 302 redirect (normal for /web) |
| GPU passthrough | /dev/dri (Arc A380) -- enabled |
| Appdata size | 7.5 GB (largest single appdata) |
| Network mode | host |

**Assessment:** Plex is the heaviest single service on VAULT by appdata size. The 7.5 GB footprint is primarily metadata, thumbnails, and chapter images (logs show active chapter thumbnail generation). Hardware transcoding via Arc A380 is configured and available.

---

## 9. Backups

### 9.1 Scheduled Backups

| Backup | Schedule | Target | Status |
|--------|----------|--------|--------|
| Neo4j Cypher export | 03:15 daily | /mnt/user/backups/athanor/neo4j/ | RUNNING -- today's backup confirmed |
| Appdata tar.gz | 03:30 daily | /mnt/user/backups/athanor/appdata/ | RUNNING -- today's backup confirmed |
| Qdrant snapshots | 03:00 daily | /mnt/user/backups/athanor/qdrant/ | **EMPTY -- 0 files** |

### 9.2 BACKUP GAP -- Qdrant

The `/mnt/user/backups/athanor/qdrant/` directory exists but is **completely empty**. Per MEMORY.md, the Qdrant backup runs from Node 1's crontab at 03:00 and targets VAULT via NFS. Either:
1. Node 1's crontab isn't running the backup, or
2. The NFS path mapping is wrong, or
3. The backup script has an error.

**This needs investigation on Node 1.** Qdrant contains 1,203 knowledge chunks, conversation history, activity logs, and preferences -- all irreplaceable data.

### 9.3 Backup Sizes

Today's appdata backup totals (per service):

| Service | Size | Notes |
|---------|------|-------|
| Plex | 6.8 GB | Dominates backup set |
| Prometheus | 77 MB | Tar warnings (live TSDB) |
| Grafana | 22 MB | |
| Sonarr | 688 KB | |
| Prowlarr | 693 KB | |
| Neo4j (appdata copy) | 544 KB | |
| Radarr | 435 KB | |
| Home Assistant | 304 KB | |
| Stash | 44 KB | |
| Tautulli | 7.1 KB | |
| SABnzbd | 3.0 KB | |

**Retention:** 3 copies per service. Total backup footprint: ~21 GB (3x ~7GB). Stored on the array itself, which is at 90%. This is fine for now but won't scale if the array fills up.

### 9.4 Missing from Backups

The following containers have appdata but are NOT explicitly listed in backup output:
- **Redis** -- appdata is 6.1 MB. Redis AOF persistence exists but redis appdata is not in the backup list. **Gap.**
- **LiteLLM** -- appdata is 4 KB. Negligible but not backed up. Trivially reconstructable from config.
- **wyoming-piper** and **wyoming-openwakeword** -- voice model data is in `/mnt/user/appdata/voice` (61 MB). Not listed in backup output.

**Recommendation:** Verify that `backup-appdata.sh` includes redis, litellm, and voice appdata directories.

---

## 10. Thermal Summary

| Component | Temperature | Assessment |
|-----------|-------------|------------|
| CPU (k10temp) | 49.5C | Excellent |
| System (SYSTIN) | 30.0C | Excellent |
| CPU board (CPUTIN) | 36.5C | Excellent |
| TSI0 (CPU package) | 49.8C | Excellent |
| HDD array | 31-33C | Excellent |
| NVMe (appdatacache) | 42C | Good (warmest NVMe) |
| NVMe (docker) | 35C | Good |
| NVMe (transcode/P310) | 28C | Excellent |
| NVMe (VMs) | 34C | Good |
| NVMe (Ubuntu/unused) | 36C | Good |
| Arc A380 iGPU edge | 42C | Good (near idle) |
| 5GbE NIC (Aquantia) | 63C | Warm but within spec |
| Ryzen iGPU | 42C (edge) | Good |

**Fan speeds:** fan1: 863 RPM, fan2: 964 RPM, fan4: 643 RPM, fan5: 662 RPM, fan6: 657 RPM. Two fans (fan3, fan7) report 0 RPM -- likely unpopulated headers.

**Intrusion sensor:** intrusion1 reports ALARM. This is typically a chassis intrusion header that isn't connected or the case has been opened. Not a real concern.

**Assessment:** All temperatures are well within safe operating ranges. The 5GbE NIC at 63C is the warmest component but this is normal for Aquantia controllers under load.

---

## 11. User Shares Layout

```
/mnt/user/
  appdata/        -- Container configs (on appdatacache NVMe)
  backups/        -- Athanor backup target
  Backups/        -- Separate backup share (note capital B)
  data/           -- Primary data share (media, models, downloads)
  domains/        -- VM disk images
  hydra/          -- Legacy (unused?)
  isos/           -- VM ISOs (empty)
  models/         -- AI model storage (NFS exported)
  system/         -- Docker image, libvirt image
  unraidshare/    -- Default Unraid share
  auditforecaster/ -- Unknown / legacy
```

**Media breakdown under /mnt/user/data/media/:**
```
Movies/          -- Movies library
TV/              -- TV library
movies/          -- Second movies directory (lowercase)
tv/              -- Second TV directory (lowercase)
music/           -- Music library
adult/           -- Stash library (noted as empty in MEMORY.md)
downloads/       -- Download staging
media/           -- Nested media dir
converted/       -- Transcoded output
_transcode_queue/ -- Queue dir
vault/           -- Unknown
```

**Note:** There are both `Movies/` and `movies/`, and both `TV/` and `tv/`. This is likely because Unraid's XFS is case-sensitive. One pair may be active and the other legacy. Worth investigating to avoid confusion.

---

## 12. Discrepancy Summary

| # | Category | Issue | Severity | Action |
|---|----------|-------|----------|--------|
| 1 | Inventory | HDD disk2/disk7/disk8 slot assignments wrong in inventory.md | MEDIUM | Update inventory.md with corrected serial-to-slot mapping |
| 2 | Inventory | Inventory claims 8 NVMe in VAULT, only 5 detected | HIGH | Verify where the 3 missing Crucial P310 drives are |
| 3 | Docs | MEMORY.md says "13 VAULT containers" -- actual count is 15 | LOW | Update to 15 (voice containers added in Session 18) |
| 4 | Backup | Qdrant backup directory on VAULT is empty (0 files) | HIGH | Investigate Node 1 crontab and backup-qdrant.sh |
| 5 | Backup | Redis, LiteLLM, and voice appdata may not be in backup script | MEDIUM | Verify backup-appdata.sh service list |
| 6 | Monitoring | No VAULT node-exporter -- VAULT itself is unmonitored in Prometheus | MEDIUM | Deploy node-exporter on VAULT, add scrape target |
| 7 | Storage | nvme4n1 has unused Ubuntu LVM partition (1TB wasted) | LOW | Wipe and repurpose |
| 8 | Storage | Array at 90% capacity, disk4/disk5 at 93% | HIGH | Plan capacity expansion (1 free slot available) |
| 9 | Network | NFS exports have no host restrictions | LOW | Add host whitelist for hardening |
| 10 | Network | MTU 1500 (no jumbo frames) on 5GbE links | LOW | Consider MTU 9000 for NFS performance |
| 11 | Home Assistant | Auth failures from Node 2 and DEV dashboard health checks | LOW | Already known, stale tokens |
| 12 | Home Assistant | Chromecast connection failures to TV (.166) | LOW | TV likely powered off |

---

## 13. Recommendations (Priority Order)

### HIGH Priority

1. **Investigate Qdrant backups** -- The knowledge base (1,203 chunks), conversation history, activity logs, and preferences are currently unbacked-up. Check Node 1 crontab and `scripts/backup-qdrant.sh`. This is the single most important finding.

2. **Plan storage expansion** -- 18T free at 90% utilization. At current fill rates, disk4 and disk5 will hit 95% within months. Options:
   - Add a 22TB WD Gold/Red Pro to the empty disk10 slot (~$350, adds ~20T usable)
   - Replace the two 16TB drives with 22TB drives (+12T usable, requires parity rebuild per drive)
   - Both (adds ~32T usable)

3. **Locate 3 missing Crucial P310 1TB drives** -- Inventory says 4x P310 in VAULT's Hyper M.2 adapter, but only 1 is detected. Are the other 3 in the adapter but not detected? Are they loose? Were they moved to another node?

### MEDIUM Priority

4. **Deploy VAULT node-exporter** -- VAULT is the storage backbone but its own metrics (disk space, CPU, memory, network) are not being scraped by Prometheus. Critical blind spot.

5. **Verify backup-appdata.sh includes all services** -- Redis (6.1 MB) and voice services (61 MB) should be backed up.

6. **Update inventory.md** -- Fix the 3 HDD slot assignments and NVMe count to match reality.

### LOW Priority

7. **Wipe nvme4n1 Ubuntu partition** -- 1TB NVMe sitting unused with a leftover Ubuntu install. Could be added to the appdata cache pool or used for VM storage.

8. **Enable jumbo frames** -- MTU 9000 on VAULT, switch, and NFS clients for ~10-15% NFS throughput improvement on large transfers.

9. **Set container memory limits** -- Protect filesystem cache from runaway containers.

10. **Clean up duplicate media directories** -- Investigate why both `Movies/` and `movies/` exist under /mnt/user/data/media/.

---

## 14. Overall Assessment

VAULT is a well-configured Unraid storage server that is doing its job effectively. All drives are healthy with zero errors. All 15 containers are running and responsive. Temperatures are excellent. The 9950X is massively overpowered for the workload but that's by design (AM5 platform for expandability).

The three critical findings are:
1. **Qdrant backups are not landing on VAULT** -- investigate immediately
2. **Array at 90%** -- plan capacity expansion in the next 1-2 months
3. **NVMe inventory mismatch** -- 3 drives documented as installed are not detected

Everything else is operating within normal parameters for a well-maintained homelab storage node.
