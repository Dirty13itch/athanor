# ADR-003: Storage Architecture

**Date:** 2026-02-15
**Status:** Proposed
**Research:** [docs/research/2026-02-15-storage-architecture.md](../research/2026-02-15-storage-architecture.md)
**Depends on:** ADR-001 (Base Platform), ADR-002 (Network Architecture)

---

## Context

Athanor has 23 NVMe drives (31.75 TB), a 164 TB HDD parity array on VAULT, and 3 Hyper M.2 adapters — but most of the NVMe capacity is either in the wrong place or sitting on a shelf. The compute nodes that need fast storage the most (for loading AI models into VRAM) are underutilizing what they have: Node 1 has 2x 4 TB drives (8 TB, though one wasn't detected in the audit — needs reseat/BIOS check), Node 2 has 4x 1 TB.

Meanwhile, 11 NVMe drives (11 TB) and 3 Hyper M.2 X16 Gen5 adapters (12 NVMe slots) are loose. Installing them costs nothing.

The other critical insight: VAULT's HDD array reads at 150-250 MB/s per file (Unraid reads from a single drive, no striping). The 10GbE link from ADR-002 can do 1.1 GB/s — but only if the source file is on NVMe. **Serving AI models from VAULT's HDD array wastes the 10GbE network.** Models must be on NVMe, either locally on the compute node or on VAULT's NVMe cache.

---

## Decision

### Three-tier storage hierarchy

```
┌─────────────────────────────────────────────┐
│  Tier 1: Local NVMe (per compute node)      │  Hot models, OS, Docker, active projects
│  Node 1: 16 TB  │  Node 2: 4 TB             │  3-7 GB/s reads
└─────────────────────────────────────────────┘
                    ▲ rsync / pull
┌─────────────────────────────────────────────┐
│  Tier 2: VAULT NVMe (over NFS/10GbE)       │  Model repository, warm storage
│  ~6.5 TB (expandable to ~9.5 TB)            │  ~1.1 GB/s over network
│  Unraid share with "cache: prefer"          │
└─────────────────────────────────────────────┘
                    ▲ mover (only if NVMe full)
┌─────────────────────────────────────────────┐
│  Tier 3: VAULT HDD Array (over NFS)        │  Media, archives, datasets, cold models
│  164 TB usable (18 TB free, 90% full)       │  150-250 MB/s per file
│  Unraid parity-protected                    │
└─────────────────────────────────────────────┘
```

### Node 1 local NVMe expansion

Node 1 has 2 free PCIe 4.0 x16 slots (after 4 GPUs + InfiniBand). The ROMED8-2T has 2 M.2 slots — one holds the Crucial P3 OS drive, the other should hold a Samsung 990 PRO 4TB that wasn't detected during the audit (needs reseat or BIOS M.2 enable).

| Slot | What Goes In | Drives | Added Capacity |
|------|-------------|--------|----------------|
| M.2 #2 (motherboard) | Samsung 990 PRO 4TB (verify/reseat) | 1 | +4 TB |
| PCIe slot → Hyper M.2 #1 | 4x Crucial T700 1TB (Gen5) | 4 | +4 TB |
| PCIe slot → Hyper M.2 #2 | 4x Crucial P310 1TB (Gen4) | 4 | +4 TB |

**Node 1 total: 4 TB existing (P3 OS) + 4 TB (990 PRO) + 8 TB (adapters) = 16 TB local NVMe.**

The Gen5 Hyper M.2 adapters are backward-compatible in Gen4 slots. Each adapter shares PCIe 4.0 x16 bandwidth (~32 GB/s) across 4 drives — more than enough for sequential model loading.

Cost: $0. All hardware already owned.

### Node 2 local NVMe

No expansion possible (InfiniBand takes the only free slot). Wipe the 3 drives with old Talos partitions to reclaim ~3 TB usable space.

**Node 2 total: 4 TB (fixed).** Sufficient for ComfyUI checkpoints (7-24 GB each), EoBQ working files, Docker volumes, and cached models for 2 GPUs.

### VAULT model share

Create a dedicated Unraid share for AI models with **"cache: prefer"** setting. This keeps model files on VAULT's NVMe cache pool and only moves them to HDD if the cache runs out of space.

| Share | Cache Setting | Backing Storage | Purpose |
|-------|--------------|-----------------|---------|
| `models` | **Cache: Prefer** | NVMe → HDD overflow | AI model repository |
| `media` | Cache: No | HDD array | Media library (Plex, Stash) |
| `shared` | Cache: Yes | NVMe write → HDD via mover | General shared files |
| `backups` | Cache: No | HDD array | Backups |

NFS exports restricted to data VLAN (10.0.10.0/24).

### VAULT NVMe expansion (optional, deferred)

After allocating 9 drives to Node 1, 3 loose NVMe remain (1x P310 + 1x 970 EVO Plus + 1x WD Black SN750 = 3 TB). Plus 1 unused Hyper M.2 adapter. These can go into VAULT if the model share outgrows the existing ~6.5 TB NVMe cache. Not urgent — 6.5 TB holds many large models.

### NFS mounts on compute nodes

Systemd automount (not fstab) to handle VAULT reboots gracefully and avoid stale NFS handles.

| Mount Point | VAULT Source | Backed By | Purpose |
|-------------|-------------|-----------|---------|
| `/mnt/vault/models` | `models` share | NVMe (cache: prefer) | Model repository (~1.1 GB/s) |
| `/mnt/vault/media` | `media` share | HDD array | Media access |
| `/mnt/vault/shared` | `shared` share | NVMe → HDD | General files |

Mount options: `hard,intr,rsize=1048576,wsize=1048576,noatime,nfsvers=4`

### Local storage layout on compute nodes

```
/               ← OS (existing NVMe)
/data/          ← Local fast storage root
/data/models/   ← Hot model cache (rsync'd from VAULT or downloaded directly)
/data/docker/   ← Docker volumes, images, container state
/data/projects/ ← Active project working files (EoBQ assets, etc.)
/mnt/vault/     ← NFS mounts to VAULT (models, media, shared)
```

### Model sync strategy

No distributed filesystem. No Ceph, GlusterFS, or MinIO.

- **VAULT `models` share** is the canonical repository. Every model lives here.
- **Local `/data/models/`** is a cache. Populated by rsync, a simple script, or direct download.
- **Directory convention** organizes models by type:

```
models/
  llm/
    llama-3.1-70b-instruct-fp16/
    llama-3.1-70b-instruct-q4/
    mistral-7b-v0.3/
  diffusion/
    flux-dev/
    sdxl-base/
  lora/
    custom-trained/
  embeddings/
    ...
```

No model registry or database. Files on disk, organized by convention, managed by Ansible or a sync script.

---

## Full NVMe Allocation

All 23 drives accounted for:

| # | Drive | Gen | Capacity | Allocation |
|---|-------|-----|----------|------------|
| 1 | Crucial P3 | Gen3 | 4 TB | Node 1 — OS (existing, detected) |
| 2 | Samsung 990 PRO (MZ-V9P4T0) | Gen4 | 4 TB | Node 1 — M.2 #2 (verify seat/BIOS — not detected in audit) |
| 3-5 | Samsung 990 EVO Plus (x3) | Gen4 | 3 TB | Node 2 — local storage (wipe Talos partitions) |
| 6 | Samsung 990 EVO Plus | Gen4 | 1 TB | Node 2 — OS (existing) |
| 7 | Crucial T700 | Gen5 | 3.6 TB | VAULT — cache pool (existing) |
| 8-10 | Crucial P310 (x3) | Gen4 | ~3 TB | VAULT — docker/transcode/vms (existing, consider consolidating into cache pool) |
| 11 | Crucial P3 Plus | Gen4 | 4 TB | DEV — C: (existing, unchanged) |
| 12 | Crucial P310 | Gen4 | 2 TB | DEV — D: (existing, unchanged) |
| 13 | Samsung 970 EVO | Gen3 | 250 GB | DEV — E: (existing, unchanged) |
| 14-17 | Crucial T700 (x4) | Gen5 | 4 TB | **Node 1 — Hyper M.2 adapter #1** |
| 18-21 | Crucial P310 (x4) | Gen4 | 4 TB | **Node 1 — Hyper M.2 adapter #2** |
| 22 | Crucial P310 | Gen4 | 1 TB | Spare / future VAULT NVMe expansion |
| 23 | Samsung 970 EVO Plus | Gen3 | 1 TB | Spare / future VAULT NVMe expansion |
| 24 | WD Black SN750 | Gen3 | 1 TB | Spare / future VAULT NVMe expansion |

**Hyper M.2 adapters:** 2 of 3 used (Node 1). 1 spare for future VAULT expansion.
**Spare NVMe:** 3 drives (3 TB) available for VAULT cache expansion if needed.

---

## Model Loading Times After This Architecture

| Scenario | Speed | 70B FP16 (140 GB) | 70B Q4 (40 GB) | Flux (12 GB) |
|----------|-------|-------------------|-----------------|---------------|
| From local NVMe | 3-7 GB/s | 20-47 sec | 6-13 sec | 2-4 sec |
| From VAULT NVMe over NFS/10GbE | ~1.1 GB/s | ~2 min | ~36 sec | ~11 sec |
| From VAULT HDD (avoid for models) | 150-250 MB/s | 9-15 min | 2.5-4.5 min | 48-80 sec |

Hot models load from local NVMe in under a minute. Warm models from VAULT NVMe in ~2 minutes. Both are fine for inference workloads where models load once and stay resident in VRAM.

---

## What To Buy When Needed

| Item | Trigger | Est. Cost |
|------|---------|-----------|
| 1-2x 24 TB HDD (WD Gold / Ultrastar) | VAULT reaches ~95% full | ~$400-800 |
| Larger NVMe for Node 2 (2-4 TB) | 4 TB local proves tight | ~$100-200 |
| Parity drive upgrade (24 TB) | Only if adding data drives larger than current 22 TB parity | ~$400 |

No storage purchases are needed now. The loose hardware covers immediate needs.

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Distributed filesystem (Ceph, GlusterFS) | Massive operational complexity for one person. Requires dedicated OSDs, monitors, metadata servers. Debugging Ceph is a full-time job. NFS + local NVMe is simpler and faster for this scale. |
| All models on VAULT HDD via NFS | Wastes 10GbE — HDD reads at 150-250 MB/s. Model loading takes 9-15 min for large models. Defeats the purpose of fast networking. |
| All models local only (no NFS) | Node 1 has 16 TB which could hold many models, but no canonical source of truth across nodes. New model downloads must be managed per node. VAULT's capacity is wasted. NFS hybrid is more flexible. |
| MinIO / S3-compatible object store | Over-engineering. Models are files read sequentially. Object store adds HTTP overhead, API complexity, and another service to maintain. No benefit over NFS for this access pattern. |
| iSCSI instead of NFS | Block-level protocol — can't share the same volume across multiple nodes simultaneously without a cluster filesystem on top. NFS is simpler for shared read access. |

---

## Risks

- **Hyper M.2 thermal throttling in Node 1:** 8 NVMe drives in a server chassis generate heat. The Silverstone RM52 needs adequate airflow over the Hyper M.2 adapters. Monitor temps after install.
- **VAULT NVMe cache churn:** If the model share outgrows VAULT's NVMe, the mover pushes cold models to HDD. Loading them later is slow. Mitigate by monitoring cache usage and expanding with the spare Hyper M.2 adapter + loose drives if needed.
- **VAULT at 90% HDD capacity:** 18 TB free. Media growth will consume this. Plan for 1-2 new HDDs within the next year.

---

## Sources

- [Unraid array architecture — single-drive reads](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/array/overview/)
- [Unraid cache share behavior](https://docs.unraid.net/unraid-os/using-unraid-to/manage-storage/cache/overview/)
- [Unraid NFS configuration guide](https://gist.github.com/pbarone/1f783a94a69aecd2eac49d9b77df0ceb)
- [Unraid 10GbE NFS performance](https://forums.unraid.net/topic/120776-10gbe-performance/)
- [Unraid performance tuning wiki](https://wiki.unraid.net/Improving_unRAID_Performance)
