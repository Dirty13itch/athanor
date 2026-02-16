# Storage Architecture

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-003 (Storage Architecture)
**Depends on:** ADR-001 (Base Platform), ADR-002 (Network Architecture)

---

## The Question

Where should data live in Athanor? How do AI models, game assets, media, and working files move between VAULT's bulk storage and the compute nodes' GPUs?

This decision determines:
- How fast models load into VRAM (seconds vs minutes)
- Whether VAULT's 10GbE connection actually delivers 10GbE speed (spoiler: not always)
- What to do with 11 NVMe drives and 3 Hyper M.2 adapters sitting loose on a shelf
- How much runway VAULT has before it needs more capacity

---

## Current State

### What's Installed

| Machine | Storage | Capacity | Speed | Notes |
|---------|---------|----------|-------|-------|
| **Node 1** | 1x Crucial P3 4TB NVMe (OS) + 1x Samsung 990 PRO 4TB (not detected in audit — verify seat/BIOS) | 8 TB | 3.5-7.5 GB/s | 0-1 empty M.2 slots (depends on 990 PRO status). 2 free PCIe slots (after 4 GPUs + IB card). |
| **Node 2** | 4x Samsung 990 EVO Plus 1TB NVMe | 4 TB | ~5 GB/s | OS on one drive. 3 drives have old Talos partitions (wipe). No free slots after GPUs + IB. |
| **VAULT NVMe** | 1x T700 3.6TB + 3x P310 ~1TB each | ~6.5 TB | Up to 12 GB/s (T700) | Mostly empty. T700 is cache pool (761GB used). P310s allocated to docker/transcode/vms but unused. |
| **VAULT HDD** | 10x WD/Seagate 16-22TB (Unraid parity array) | 164 TB usable | 150-250 MB/s per file | 90% full (18TB free). No striping — reads come from single drive. |
| **DEV** | 3x NVMe (4TB + 2TB + 250GB) | ~6.25 TB | — | 1 empty M.2 slot. Not a server. |

### What's Loose (Not Installed)

| Item | Qty | Capacity | Notes |
|------|-----|----------|-------|
| Crucial T700 1TB NVMe (Gen5) | 4 | 4 TB | Fastest drives available. PCIe 5.0. |
| Crucial P310 1TB NVMe (Gen4, DRAM-less) | 5 | 5 TB | Good bulk NVMe. |
| Samsung 970 EVO Plus 1TB (Gen3) | 1 | 1 TB | |
| WD Black SN750 1TB (Gen3) | 1 | 1 TB | |
| **ASUS Hyper M.2 X16 Gen5 adapter** | **3** | **12 NVMe slots total** | Each holds 4 NVMe drives in one PCIe x16 slot. |
| LSI SAS9300-16i HBA | 1 | 16 SAS/SATA ports | For HDD expansion if needed. |

**Total loose NVMe: ~11 drives, ~11 TB. Plus 3 adapters that can hold 12 drives.**

This is significant unused capability.

---

## The Speed Reality

The ADR-002 research doc estimated model loading times based on network speed. That was incomplete. The actual bottleneck depends on **where the file sits on VAULT**, not just the network:

| Source | Read Speed | 70B FP16 (140 GB) | 70B Q4 (40 GB) | Flux (12 GB) |
|--------|-----------|-------------------|-----------------|---------------|
| VAULT HDD (single drive) | 150-250 MB/s | **9-15 min** | 2.5-4.5 min | 48-80 sec |
| VAULT NVMe over NFS/10GbE | ~1.1 GB/s (network limited) | **2.1 min** | 36 sec | 11 sec |
| Local NVMe on compute node | 3-7 GB/s | **20-47 sec** | 6-13 sec | 2-4 sec |

**Key insight:** Unraid doesn't stripe reads across drives. Each file lives on a single HDD. A 20TB WD Gold does ~200 MB/s sequential. The 10GbE link can do 1.1 GB/s, but the HDD can only feed it at 200 MB/s. **10GbE is wasted if the file is on spinning disk.**

For AI model loading to benefit from 10GbE, models must be on VAULT's NVMe — not the HDD array.

Sources: [Unraid array docs](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/array/overview/), [Unraid performance wiki](https://wiki.unraid.net/Improving_unRAID_Performance), [Unraid forum: 10GbE performance](https://forums.unraid.net/topic/120776-10gbe-performance/)

---

## What Needs Storage (And How Fast)

### Latency-sensitive (needs fast storage)

| Workload | Access Pattern | Size | Where It Should Live |
|----------|---------------|------|---------------------|
| AI model loading into VRAM | Large sequential read, once per model swap | 4-140 GB per model | Local NVMe (hot) or VAULT NVMe over NFS (warm) |
| ComfyUI checkpoint loading | Large sequential read, per workflow change | 7-24 GB per checkpoint | Local NVMe on Node 2 (frequent swaps during creative work) |
| Docker images + container volumes | Random I/O, always | 10-100 GB per node | Local NVMe (always) |
| EoBQ game assets (development) | Mixed read/write during iteration | Varies, growing | Local NVMe on whichever node runs the game engine |
| LoRA training datasets | Sequential read during training | 1-50 GB per dataset | Local NVMe during training, VAULT for archival |

### Latency-tolerant (bulk storage fine)

| Workload | Access Pattern | Size | Where It Should Live |
|----------|---------------|------|---------------------|
| Media library (Plex) | Sequential read, single stream ~100 Mbps | 146+ TB | VAULT HDD array. Even HDD speed vastly exceeds streaming needs. |
| Adult content library (Stash) | Sequential read/random browse | Portion of media library | VAULT HDD array. Same as media. |
| Model archive (cold/unused models) | Rare access | Grows over time | VAULT HDD array. |
| Backups | Write-once, rare read | Varies | VAULT HDD array. |
| Datasets (archival) | Rare access | Varies | VAULT HDD array. |

---

## Storage Architecture: Three Tiers

```
┌─────────────────────────────────────────┐
│  Tier 0: VRAM (GPU Memory)              │  ← Models loaded and running
│  Node 1: 64 GB │ Node 2: 56 GB         │     Fastest. Limited.
│  Combined: 120 GB                       │     Not "storage" — the destination.
└─────────────────────────────────────────┘
                    ▲ model load
┌─────────────────────────────────────────┐
│  Tier 1: Local NVMe (per compute node)  │  ← Hot models, OS, Docker, active projects
│  Node 1: 4 TB → expandable to ~13 TB   │     3-7 GB/s reads
│  Node 2: 4 TB (fixed)                  │     Fastest storage tier
└─────────────────────────────────────────┘
                    ▲ rsync / cache fill
┌─────────────────────────────────────────┐
│  Tier 2: VAULT NVMe (over NFS/10GbE)   │  ← Model repository, warm cache
│  Currently ~6.5 TB (expandable)         │     ~1.1 GB/s over network
│  "cache: prefer" share in Unraid        │     Models stay on NVMe unless full
└─────────────────────────────────────────┘
                    ▲ mover (only if NVMe full)
┌─────────────────────────────────────────┐
│  Tier 3: VAULT HDD Array (over NFS)    │  ← Everything permanent: media, archives, cold models
│  164 TB (90% full, 18 TB free)          │     150-250 MB/s per file
│  Unraid parity-protected               │     Bulk. Slow for large reads.
└─────────────────────────────────────────┘
```

### How data flows between tiers

**Models:**
1. Downloaded or created → lands on VAULT model share (Tier 2 NVMe, "cache: prefer")
2. Frequently used models → synced to local NVMe on the compute node that runs them (Tier 1)
3. If VAULT NVMe fills up → Unraid mover pushes coldest models to HDD array (Tier 3)
4. When a model is needed → loaded from local NVMe (fast) or VAULT NFS (slower but fine for infrequent swaps)

**Media:** Stays on VAULT HDD array. Plex streams at ~100 Mbps. HDDs handle this trivially.

**Docker/OS:** Always local NVMe. Never on NFS.

**Game assets (EoBQ):** Working copies on local NVMe. Canonical copies on VAULT.

### Sync strategy

No distributed filesystem. No Ceph, GlusterFS, or MinIO. Just:

- **NFS mounts** from VAULT to each compute node (Tier 2 and Tier 3 accessible to both nodes)
- **rsync** (or a simple script) to pull hot models from VAULT NVMe to local NVMe
- **Directory convention** for model organization — no database, no registry

```
# VAULT model share (NFS export)
/mnt/user/models/
  llm/
    llama-3.1-70b-instruct-fp16/
    llama-3.1-70b-instruct-q4/
    mistral-7b-v0.3/
    ...
  diffusion/
    flux-dev/
    sdxl-base/
    ...
  lora/
    custom-trained/
    ...
  embeddings/
    ...

# Compute node local cache (Tier 1)
/data/models/   ← symlink or rsync target, mirrors subset of VAULT
```

This is boring and that's the point. It's understandable, debuggable, and fixable by one person.

---

## NFS Configuration

### VAULT side (Unraid)

Create a dedicated share for AI models:

| Share | Cache Setting | Purpose |
|-------|--------------|---------|
| `models` | **Cache: Prefer** | AI models. Stays on NVMe unless cache is full. |
| `media` | Cache: No | Media library. Reads from HDD array directly. |
| `shared` | Cache: Yes | General shared files. Write to NVMe, mover pushes to HDD. |
| `backups` | Cache: No | Backups. Direct to HDD. |

NFS exports restricted to data VLAN subnet (10.0.10.0/24).

**"Cache: Prefer" behavior:** Files written to this share land on the NVMe cache pool. The mover only pushes them to HDD if the cache is running low on space. For a model repository, this means models stay on fast NVMe as long as there's room. ([Unraid cache docs](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/cache/overview/))

### Compute node side (Ubuntu)

Systemd automount, not `/etc/fstab`. This handles VAULT reboots and mover-induced stale handles gracefully.

```ini
# /etc/systemd/system/mnt-vault-models.mount
[Mount]
What=vault.athanor.local:/mnt/user/models
Where=/mnt/vault/models
Type=nfs
Options=hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4

# /etc/systemd/system/mnt-vault-models.automount
[Automount]
Where=/mnt/vault/models
TimeoutIdleSec=0
```

Mount points on each compute node:

| Mount | Source | Used For |
|-------|--------|----------|
| `/mnt/vault/models` | VAULT `models` share (NVMe-backed) | Model repository |
| `/mnt/vault/media` | VAULT `media` share (HDD) | Media access (Plex, Stash) |
| `/mnt/vault/shared` | VAULT `shared` share | General file sharing |
| `/data/` | Local NVMe | OS, Docker, hot models, project files |

Sources: [NFS config guide for Unraid](https://gist.github.com/pbarone/1f783a94a69aecd2eac49d9b77df0ceb), [Unraid NFS stale handle fix](https://forums.unraid.net/topic/120776-10gbe-performance/)

---

## Local NVMe Expansion: Using the Loose Hardware

### Node 1 — Major expansion possible

Node 1 has 2 free PCIe slots after GPUs (4x 5070 Ti) and InfiniBand. It also has a Samsung 990 PRO 4TB that wasn't detected in the audit — needs physical verification (reseat or BIOS M.2 enable). The ROMED8-2T has 2 M.2 slots; one holds the P3 OS drive.

| Slot | Install | Drives | Capacity |
|------|---------|--------|----------|
| M.2 #2 (motherboard) | Samsung 990 PRO 4TB (verify/reseat) | 1 | +4 TB (already owned) |
| PCIe slot → Hyper M.2 adapter #1 | 4x Crucial T700 1TB (Gen5) | 4 | +4 TB |
| PCIe slot → Hyper M.2 adapter #2 | 4x Crucial P310 1TB (Gen4) | 4 | +4 TB |

**Node 1 total: 4 TB (P3 OS) + 4 TB (990 PRO) + 8 TB (adapters) = 16 TB local NVMe.**

The Hyper M.2 Gen5 adapters are PCIe backward-compatible. In Node 1's PCIe 4.0 x16 slots, they run at Gen4 speeds (~32 GB/s shared across 4 drives). Each drive still gets more bandwidth than it can use for sequential reads. T700s would be slightly limited (they can do 12 GB/s natively, get ~8 GB/s in shared x16), but P310s run at full speed.

Cost: **$0.** All hardware is already owned.

### Node 2 — No expansion, but sufficient

All M.2 slots occupied. Only PCIe slot goes to InfiniBand. 4 TB local NVMe is fixed.

After wiping the 3 Talos-era drives: ~3 TB usable for models, ComfyUI checkpoints, EoBQ assets, Docker volumes. The OS drive has ~930 GB free as well.

4 TB is adequate for Node 2's workloads. ComfyUI checkpoints are 7-24 GB each — dozens fit. Node 2 runs fewer simultaneous models than Node 1 (2 GPUs vs 4).

### VAULT — Optional expansion

Remaining loose hardware after Node 1:
- 1x P310 1TB + 1x 970 EVO Plus 1TB + 1x WD Black SN750 1TB = 3 drives
- 1x Hyper M.2 adapter unused

Could install in VAULT to expand NVMe cache from ~6.5 TB to ~9.5 TB. Worth doing if the model repository outgrows 6.5 TB. Not urgent — 6.5 TB holds dozens of large models.

---

## What New Parts Could Unlock

### High priority

| Item | Cost | What It Unlocks |
|------|------|-----------------|
| **WD Gold / Ultrastar 24TB HDD** (1-2x) | ~$400-800 | VAULT is 90% full. Each drive adds ~24 TB usable capacity. Buys years of media growth. |

### Nice to have

| Item | Cost | What It Unlocks |
|------|------|-----------------|
| WD Gold / Ultrastar 24TB HDD (parity upgrade) | ~$400 | Current parity is 22TB. Replacing with 24TB parity allows adding 24TB data drives. Only needed if adding drives larger than 22TB. |
| 2TB or 4TB Gen4/Gen5 NVMe (for Node 2) | ~$100-200 | Replace one of Node 2's 1TB drives with a larger one. Gains local capacity without needing a new slot. |

### Not worth buying

| Item | Why Not |
|------|---------|
| Enterprise SAS SSDs | Expensive, slower than NVMe, need HBA. NVMe is better in every way for this use case. |
| Distributed filesystem appliance | Over-engineering. NFS + local NVMe is simpler and sufficient. |
| More Hyper M.2 adapters | Already have 3 (only using 2 for Node 1). One spare is enough. |

---

## Open Questions

1. **VAULT NVMe pool reconfiguration** — The current P310s are assigned to docker/transcode/vms shares but are empty. Should they be consolidated into the cache pool alongside the T700 to create a larger unified NVMe tier? This is an Unraid configuration decision during implementation.

2. **Node 2 drive replacement** — One option: replace a 1TB 990 EVO Plus with a 2-4TB drive for more local capacity. Depends on whether 4TB proves tight. Monitor before buying.

3. **VAULT share structure** — Exact share names, paths, and permissions are implementation details. The architecture (NVMe-backed model share, HDD for media, NFS to compute nodes) is what matters.

4. **Backup strategy** — Not addressed here. VAULT's Unraid parity protects against single drive failure. Off-site or cross-node backup is a separate topic if needed.

---

## Recommendation

**Three-tier storage with NFS and local NVMe caching.** No distributed filesystem.

1. **VAULT is the canonical store** for all persistent data. Models, media, datasets, backups — everything permanent lives here.
2. **VAULT model share uses "cache: prefer"** so AI models stay on NVMe. Served over NFS/10GbE at ~1.1 GB/s.
3. **Compute nodes have local NVMe** for OS, Docker, and hot model cache. Node 1 expands to 16 TB (990 PRO + 2 Hyper M.2 adapters with 8 NVMe drives). Node 2 stays at 4 TB.
4. **NFS via systemd automount** on compute nodes. Handles VAULT reboots gracefully.
5. **rsync or script** to cache hot models from VAULT to local NVMe. No exotic tooling.
6. **Directory convention** for model organization. No database or registry.
7. **Buy 1-2x 24TB HDDs** for VAULT when capacity gets tight (currently 90% full).

This gives every workload the speed it needs without complexity Shaun can't debug alone.

---

## Sources

- [Unraid array architecture (no striped reads)](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/array/overview/)
- [Unraid cache behavior docs](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/cache/overview/)
- [Unraid performance wiki](https://wiki.unraid.net/Improving_unRAID_Performance)
- [Unraid NFS configuration guide](https://gist.github.com/pbarone/1f783a94a69aecd2eac49d9b77df0ceb)
- [Unraid 10GbE performance forum thread](https://forums.unraid.net/topic/120776-10gbe-performance/)
- [NVMe cache write speed on 10GbE (Unraid forums)](https://forums.unraid.net/topic/128084-solved-slow-write-speed-to-nvme-cache-drive-on-10g-network-possible-network-issue/)
