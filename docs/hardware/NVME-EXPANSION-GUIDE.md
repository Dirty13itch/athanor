# NVMe Expansion Guide - Detailed Slot Analysis
**Updated:** 2026-02-21
**Purpose:** Complete guide to available PCIe/M.2 slots and NVMe expansion options

---

## Quick Reference: What's Available

### Loose NVMe Drives (13.25 TB total)
```
Gen5 (1 TB):
  1× Crucial T700 1TB                               [1TB]

Gen4 (10 TB):
  1× Crucial P3 Plus 4TB                            [4TB]
  1× Crucial P310 2TB                               [2TB]
  4× Crucial P310 1TB                               [4TB total]

Gen3 (2.25 TB):
  1× Samsung 970 EVO Plus 1TB                       [1TB]
  1× WD Black SN750 1TB                             [1TB]
  1× Samsung 970 EVO 250GB                          [250GB]
```

### Loose Hyper M.2 Adapters
```
2× ASUS Hyper M.2 X16 Gen5 (4× M.2 slots each)
  - PCIe 5.0 x16 interface
  - Backwards compatible with Gen3/Gen4 drives
  - Each takes 1× PCIe slot, provides 4× M.2 slots
```

---

## Node 1 - ASRock Rack ROMED8-2T (SP3)

### Current M.2 Configuration
```
M.2_1: Crucial P3 4TB Gen3 (OS/system) ✓
M.2_2: Samsung 990 PRO 4TB Gen4 (models, not detected) ⚠️

Available M.2 slots: 0 (both used)
Total current capacity: 8 TB (when 990 PRO detected)
```

### PCIe Slot Layout (7 total)
```
┌──────────────────────────────────────────────────┐
│ ASRock Rack ROMED8-2T PCIe Topology              │
├──────────────────────────────────────────────────┤
│ Slot 1: PCIe 4.0 x16  → RTX 4090             ✓  │
│ Slot 2: PCIe 4.0 x16  → RTX 5070 Ti          ✓  │
│ Slot 3: PCIe 4.0 x8   → RTX 5070 Ti          ✓  │
│ Slot 4: PCIe 4.0 x8   → RTX 5070 Ti          ✓  │
│ Slot 5: PCIe 4.0 x8   → RTX 5070 Ti          ✓  │
│ Slot 6: PCIe 4.0 x8   → EMPTY                   │ ← Available
│ Slot 7: PCIe 4.0 x8   → EMPTY                   │ ← Available
└──────────────────────────────────────────────────┘

Available PCIe slots: 2 (Slot 6 + Slot 7)
Bandwidth per slot: 32 Gbps (8× Gen4 lanes) = ~4 GB/s
Note: x8 slots are sufficient for Hyper M.2 adapters
```

---

### Expansion Option 1A: Single Adapter - Uniform Drives
**Recommended for immediate deployment**

**Install:** 1× ASUS Hyper M.2 X16 Gen5 adapter
**Location:** PCIe Slot 6 (x8 physical, Gen4)
**Bandwidth:** 32 Gbps shared across 4 drives = ~4 GB/s total

**Populate with:**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter in Slot 6                │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial P310 1TB Gen4   [1TB] │ ← from loose
│ M.2 Slot 2: Crucial P310 1TB Gen4   [1TB] │ ← from loose
│ M.2 Slot 3: Crucial P310 1TB Gen4   [1TB] │ ← from loose
│ M.2 Slot 4: Crucial P310 1TB Gen4   [1TB] │ ← from loose
│                                            │
│ Total: +4 TB local NVMe                    │
│ Uses: All 4× P310 1TB drives              │
└────────────────────────────────────────────┘
```

**Use cases:**
- Hot model storage (frequently accessed models)
- vLLM temp data and caching
- Agent workspace directories
- Faster than NFS from VAULT

**Performance per drive:** ~1 GB/s sequential read
(Limited by x8 slot bandwidth sharing, but still very fast)

**Mount points:**
```
/mnt/nvme-fast/models     ← hot models
/mnt/nvme-fast/temp       ← inference temp data
/mnt/nvme-fast/agents     ← agent workspaces
/mnt/nvme-fast/cache      ← general cache
```

---

### Expansion Option 1B: Single Adapter - Mixed Capacity
**Maximum local capacity option**

**Install:** 1× ASUS Hyper M.2 X16 Gen5 adapter
**Location:** PCIe Slot 6 (x8 physical, Gen4)

**Populate with:**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter in Slot 6                │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial P3 Plus 4TB Gen4 [4TB]│ ← largest drive
│ M.2 Slot 2: Crucial P310 2TB Gen4    [2TB]│ ← medium drive
│ M.2 Slot 3: Crucial T700 1TB Gen5    [1TB]│ ← fastest drive
│ M.2 Slot 4: Samsung 970 EVO+ 1TB Gen3[1TB]│ ← older drive
│                                            │
│ Total: +8 TB local NVMe                    │
│ Uses: 4 best loose drives                  │
└────────────────────────────────────────────┘
```

**Use cases:**
- P3 Plus 4TB: Large model library
- P310 2TB: Overflow models
- T700 1TB: Frequently accessed (gets bottlenecked by x8 slot but still fastest)
- 970 EVO Plus 1TB: Older/archived models

**Performance considerations:**
- T700 Gen5 won't reach full speed (limited by Gen4 x8 slot)
- Still faster than anything else in the adapter
- Mixed generations OK - each drive independent

---

### Expansion Option 1C: Dual Adapters - Maximum Expansion
**For absolute maximum local storage**

**Install:** 2× ASUS Hyper M.2 X16 Gen5 adapters
**Locations:** PCIe Slot 6 + Slot 7
**Bandwidth:** 32 Gbps per adapter (independent channels)

**Adapter 1 (Slot 6) - Hot Models & Primary Storage:**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter #1 in Slot 6             │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial P3 Plus 4TB     [4TB] │ ← main model library
│ M.2 Slot 2: Crucial P310 2TB        [2TB] │ ← overflow models
│ M.2 Slot 3: Crucial T700 1TB        [1TB] │ ← hot models
│ M.2 Slot 4: Samsung 970 EVO+ 1TB    [1TB] │ ← archived models
│                                            │
│ Subtotal: 8 TB                             │
└────────────────────────────────────────────┘
```

**Adapter 2 (Slot 7) - Temp/Scratch/Workspace:**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter #2 in Slot 7             │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial P310 1TB        [1TB] │ ← vLLM temp data
│ M.2 Slot 2: Crucial P310 1TB        [1TB] │ ← Docker volumes
│ M.2 Slot 3: Crucial P310 1TB        [1TB] │ ← agent workspace
│ M.2 Slot 4: Crucial P310 1TB        [1TB] │ ← logs/cache
│                                            │
│ Subtotal: 4 TB                             │
└────────────────────────────────────────────┘
```

**Total Node 1 capacity:**
```
Existing:     8 TB (M.2_1 + M.2_2)
Adapter 1:   +8 TB (Slot 6)
Adapter 2:   +4 TB (Slot 7)
───────────────────
Grand Total: 20 TB local NVMe on Node 1
```

**Uses all loose drives:**
- 7× Gen4/Gen5 drives (all P3 Plus, P310, T700, 970 EVO Plus)
- Remaining: 2× Gen3 drives (WD Black SN750 1TB, Samsung 970 EVO 250GB)

**Mount structure:**
```
/mnt/nvme-models/         ← Adapter 1 (8TB, hot models)
  ├─ main/                ← P3 Plus 4TB
  ├─ overflow/            ← P310 2TB
  ├─ hot/                 ← T700 1TB
  └─ archive/             ← 970 EVO Plus 1TB

/mnt/nvme-scratch/        ← Adapter 2 (4TB, temp/workspace)
  ├─ vllm/                ← P310 1TB
  ├─ docker/              ← P310 1TB
  ├─ agents/              ← P310 1TB
  └─ cache/               ← P310 1TB
```

---

## Node 2 - Gigabyte TRX50 AERO D (sTR5)

### Current M.2 Configuration
```
M.2_1: Crucial T700 4TB Gen5 (OS/system)    ✓
M.2_2: Crucial T700 1TB Gen5 (Docker)       ✓
M.2_3: Crucial T700 1TB Gen5 (Temp)         ✓
M.2_4: Crucial T700 1TB Gen5 (ComfyUI)      ✓

Available M.2 slots: 0 (all 4 onboard slots used)
Total current capacity: 7 TB (all Gen5, blazing fast)
```

### PCIe Slot Configuration (Verified Specs)

**Gigabyte TRX50 AERO D Official Specifications:**
- **3× PCIe 5.0 x16 slots** (all full x16 electrical)
- **4× M.2 PCIe 5.0 slots** (onboard, all used)
- E-ATX form factor

**Current PCIe slot usage:**
```
┌──────────────────────────────────────────────────┐
│ Gigabyte TRX50 AERO D PCIe Layout               │
│ (3× PCIe 5.0 x16 slots, all full x16 lanes)     │
├──────────────────────────────────────────────────┤
│ Slot 1: PCIe 5.0 x16  → RTX 5090             ✓  │
│ Slot 2: PCIe 5.0 x16  → RTX 5060 Ti          ✓  │
│ Slot 3: PCIe 5.0 x16  → EMPTY                   │ ← AVAILABLE
└──────────────────────────────────────────────────┘

Available slots: 1× PCIe 5.0 x16 (Slot 3)
Bandwidth: 64 Gbps (16× Gen5 lanes) = ~8 GB/s
Perfect for: Hyper M.2 adapter with 4× NVMe drives
```

### Expansion Option: One Perfect PCIe 5.0 x16 Slot Available!

**TRX50 AERO D Slot 3 is ideal for NVMe expansion**

**Install:** 1× ASUS Hyper M.2 X16 Gen5 adapter
**Location:** Slot 3 (PCIe 5.0 x16, full x16 electrical lanes)
**Bandwidth:** 64 Gbps (16× Gen5 lanes) = ~8 GB/s total
**Perfect fit:** All 4 drives can run at full speed simultaneously

**Populate with (HIGH VALUE - TRX50 is perfect for this!):**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter in Slot 3 (x16 Gen5!)    │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial P3 Plus 4TB Gen4 [4TB]│ ← ComfyUI models
│ M.2 Slot 2: Crucial P310 2TB Gen4    [2TB]│ ← workflows
│ M.2 Slot 3: Samsung 970 EVO+ 1TB Gen3[1TB]│ ← temp/renders
│ M.2 Slot 4: WD Black SN750 1TB Gen3  [1TB]│ ← backups
│                                            │
│ Total: +8 TB                               │
└────────────────────────────────────────────┘
```

**Performance:** Full Gen5 x16 bandwidth = 64 Gbps = ~8 GB/s
- Each drive gets plenty of bandwidth
- No bottleneck even with all 4 drives active

**Analysis:**
- Node 2 already has 7 TB Gen5, but TRX50 has slots to spare
- ComfyUI would LOVE 4TB of local model storage
- **Recommendation:** GOOD option - TRX50 has the PCIe lanes

---

## VAULT - ASUS ProArt X870E-CREATOR WIFI (AM5)

### Current M.2 Configuration

**Motherboard slots (4× M.2):**
```
M.2_1: Samsung 990 EVO Plus 1TB Gen4        ✓
M.2_2: Samsung 990 EVO Plus 1TB Gen4        ✓
M.2_3: Samsung 990 EVO Plus 1TB Gen4        ✓
M.2_4: Samsung 990 EVO Plus 1TB Gen4        ✓

Available M.2 slots: 0 (all 4 used)
Total: 4 TB cache pool
```

**Existing Hyper M.2 adapter (PCIe Slot 3):**
```
Adapter Slot 1: Crucial P310 1TB Gen4       ✓
Adapter Slot 2: Crucial P310 1TB Gen4       ✓
Adapter Slot 3: Crucial P310 1TB Gen4       ✓
Adapter Slot 4: Crucial P310 1TB Gen4       ✓

Total: 4 TB fast cache
```

**Combined VAULT NVMe:** 8 TB across 8 drives

### PCIe Slot Configuration (Estimated)

**From inventory:** "2 (1x 5.0 x16, 1x 4.0 x16)"

**Typical ProArt X870E layout:**
```
┌──────────────────────────────────────────────────┐
│ ASUS ProArt X870E PCIe Topology                 │
├──────────────────────────────────────────────────┤
│ Slot 1: PCIe 5.0 x16  → Arc A380             ✓  │
│ Slot 2: PCIe 4.0 x16  → EMPTY or SAS HBA        │ ← Check
└──────────────────────────────────────────────────┘

Limited PCIe slots on X870E (AM5 platform limitation)
Need to verify: How is SAS HBA connected? USB? PCIe?
```

### Expansion Option: Second Hyper M.2 Adapter

**Install:** 1× ASUS Hyper M.2 X16 Gen5 adapter
**Location:** PCIe Slot 4 (x8 or x16 if available)
**Purpose:** Expand Unraid cache tier for media workflows

**Populate with:**
```
┌────────────────────────────────────────────┐
│ Hyper M.2 Adapter #2 in Slot 4             │
├────────────────────────────────────────────┤
│ M.2 Slot 1: Crucial T700 1TB Gen5    [1TB]│ ← fastest tier
│ M.2 Slot 2: Crucial P310 1TB Gen4    [1TB]│ ← from Node 1 leftovers
│ M.2 Slot 3: Samsung 970 EVO+ 1TB Gen3[1TB]│ ← from loose
│ M.2 Slot 4: WD Black SN750 1TB Gen3  [1TB]│ ← from loose
│                                            │
│ Total: +4 TB cache                         │
└────────────────────────────────────────────┘
```

**Unraid cache configuration:**
```
Primary cache pool (existing):
  Pool 1: 4× Samsung 990 EVO Plus 1TB = 4 TB
    Use: Docker containers, appdata, VMs
    Config: RAID1 mirror for redundancy

Existing fast cache (Hyper M.2 #1):
  Pool 2: 4× Crucial P310 1TB = 4 TB
    Use: Media downloads, temp files
    Config: RAID0 for speed

New fast cache (Hyper M.2 #2):
  Pool 3: 4× mixed drives = 4 TB
    Use: Transcode temp, Plex metadata cache
    Config: RAID0 for speed

Total VAULT cache: 12 TB across 3 pools
```

**Use cases:**
- **T700 1TB:** Plex transcode buffer (highest IOPS)
- **P310 1TB:** Sonarr/Radarr temp processing
- **970 EVO Plus 1TB:** ComfyUI model cache (accessed from Node 2)
- **WD Black SN750 1TB:** General overflow cache

---

## Recommended Deployment Strategy

### Phase 1: Immediate (This Rack Session)

**Node 1 only - Conservative start**

1. **Install:** 1× Hyper M.2 adapter in Node 1 Slot 6
2. **Populate:** 4× Crucial P310 1TB (all identical drives)
3. **Result:** +4 TB fast local storage on Node 1
4. **Uses:** Clean, uniform config - easy to manage
5. **Keep:** 1× Hyper M.2 adapter + 7× other drives for future

**Installation steps:**
```bash
# 1. Power off Node 1
ssh athanor@192.168.1.244 "sudo shutdown now"

# 2. Physical installation:
#    - Install Hyper M.2 adapter in PCIe Slot 6
#    - Install 4× Crucial P310 1TB drives in adapter
#    - Verify all drives seated properly

# 3. Power on, verify detection
ssh athanor@192.168.1.244 "lsblk | grep nvme"
# Should show 6 NVMe drives (2 existing + 4 new)

# 4. Create filesystem
ssh athanor@192.168.1.244 << 'EOF'
  # Create RAID0 array for speed
  sudo mdadm --create /dev/md0 --level=0 --raid-devices=4 \
    /dev/nvme2n1 /dev/nvme3n1 /dev/nvme4n1 /dev/nvme5n1

  # Format as ext4
  sudo mkfs.ext4 /dev/md0

  # Create mount point
  sudo mkdir -p /mnt/nvme-fast

  # Add to fstab
  echo "/dev/md0 /mnt/nvme-fast ext4 defaults 0 0" | sudo tee -a /etc/fstab

  # Mount
  sudo mount /mnt/nvme-fast
EOF

# 5. Verify
ssh athanor@192.168.1.244 "df -h /mnt/nvme-fast"
# Should show ~4TB available
```

---

### Phase 2: Future (With Dual PSU, Phase C)

**Node 1 - Maximum expansion**

1. **Install:** 2nd Hyper M.2 adapter in Node 1 Slot 7
2. **Populate:** All remaining large drives
   - Crucial P3 Plus 4TB
   - Crucial P310 2TB
   - Crucial T700 1TB
   - Samsung 970 EVO Plus 1TB
3. **Result:** +8 TB additional local storage
4. **Node 1 Total:** 20 TB local NVMe

**Or alternatively:**

**VAULT - Enhanced cache**

1. **Install:** 2nd Hyper M.2 adapter in VAULT Slot 4
2. **Populate:** Mixed drives for tiered cache
3. **Result:** +4 TB Unraid cache
4. **VAULT Total:** 12 TB cache

---

## Verification Commands

### Check PCIe Slots Available

**Node 1:**
```bash
ssh athanor@192.168.1.244 << 'EOF'
  echo "=== PCIe Devices ==="
  lspci | grep -E "VGA|PCI bridge|Non-Volatile"

  echo -e "\n=== PCIe Slot Details ==="
  sudo lspci -vv | grep -A 10 "PCI bridge"

  echo -e "\n=== Current NVMe Drives ==="
  lsblk | grep nvme
EOF
```

**Node 2:**
```bash
ssh athanor@192.168.1.225 << 'EOF'
  echo "=== PCIe Devices ==="
  lspci | grep -i "pci bridge"

  echo -e "\n=== M.2 Slots Used ==="
  lsblk | grep nvme | wc -l
  echo "Should be 4 (all M.2 slots used)"
EOF
```

**VAULT:**
```bash
python scripts/vault-ssh.py "lspci | grep -i 'pci bridge'"
python scripts/vault-ssh.py "lsblk | grep nvme"
```

---

## My Final Recommendation

### **For This Rack Session:**

**Deploy:** Option 1A (Single adapter, 4× P310 1TB on Node 1)

**Why:**
1. ✅ Clean, uniform config (all drives identical)
2. ✅ Adds 4 TB fast local storage exactly where needed
3. ✅ Uses all 4 identical P310 drives (no mixing)
4. ✅ Keeps options open (1 adapter + 7 drives in reserve)
5. ✅ Easy to manage (single RAID0 array)
6. ✅ Sufficient for current workloads

**What this unlocks:**
- Local hot model storage (no NFS latency)
- vLLM temp data cache
- Agent workspace directories
- Docker volume storage

**Total Node 1 after this:**
```
M.2_1: Crucial P3 4TB (OS)                  [4TB]
M.2_2: Samsung 990 PRO 4TB (models)         [4TB]
Slot 6 Adapter: 4× P310 1TB (hot storage)   [4TB]
─────────────────────────────────────────────────
Total: 12 TB local NVMe
```

**Save for later:**
- 1× Hyper M.2 adapter
- 1× Crucial P3 Plus 4TB
- 1× Crucial P310 2TB
- 1× Crucial T700 1TB
- 1× Samsung 970 EVO Plus 1TB
- 2× Gen3 drives (WD Black, Samsung 970 EVO 250GB)

**Deploy these when:**
- Dual PSU installed (more power headroom)
- Need for additional local capacity emerges
- VAULT cache expansion becomes priority

---

**Document Status:** READY FOR DEPLOYMENT
**Last Updated:** 2026-02-21
**Next Review:** After Hyper M.2 installation
