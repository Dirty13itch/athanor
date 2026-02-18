# Rack Session Checklist

**Goal:** 10GbE everywhere, EXPO on Node 2, Node 1 storage + 5th GPU, DEV refresh, VAULT ↔ Node 2 motherboard swap with 192 GB RAM.

**Confirmed hardware:**
- Node 1 PSU: Corsair 1600W
- Node 2 PSU: MSI 1600W (handles 7960X + RTX 5090 + RTX 4090 at full load)
- All parts in-hand. Zero purchases required for this session.

**Estimated time:** 3–4 hours for the full session including swap.

---

## Pre-Session (Remote, Before Touching Hardware)

- [ ] Screenshot VAULT Unraid → Main → array disk assignments (disk1–disk9)
- [ ] Screenshot VAULT Unraid → Pools → cache/appdata/docker/vms/transcode assignments
- [ ] Screenshot VAULT Unraid → Settings → Network Settings (record current MAC + IP)
- [ ] Clone Unraid boot USB to a second USB stick (insurance)
- [ ] On Node 2: `cat /etc/netplan/*.yaml` → save static IP config for reference
- [ ] On Node 2: `lsblk` → note which nvme device is the OS drive (nvme3n1, boot at /boot/efi)
- [ ] On Node 1: set GPU power limits before installing 3060
  ```bash
  nvidia-smi -pl 220 -i 0,1,2,3
  ```
  Then run a quick inference request and confirm tok/s is unchanged.
- [ ] Make power limits persistent (add to vLLM service startup or systemd unit)

---

## Phase 1 — Cable Moves (~20 min, no downtime)

All three servers have 10GbE onboard. They're just plugged into the wrong switch.

- [ ] Move **Node 1** ethernet → USW Pro XG 10 PoE
- [ ] Move **Node 2** ethernet → USW Pro XG 10 PoE
- [ ] Move **VAULT** ethernet → USW Pro XG 10 PoE (Aquantia AQC113C onboard, never connected to XG)
- [ ] Reconnect **JetKVM ATX power cable** on Node 2

**Verify:**
```bash
# From DEV or any machine after moves:
iperf3 -s &  # on VAULT
iperf3 -c 192.168.1.203  # from Node 1 — expect 9+ Gbps
iperf3 -c 192.168.1.203  # from Node 2 — expect 9+ Gbps
```

---

## Phase 2 — EXPO on Node 2 (~5 min, reboot)

Node 2 RAM is running at 3600 MT/s. Rated speed is 5600 MT/s. EXPO enables the XMP profile.

- [ ] Reboot Node 2 → enter BIOS (DEL or F2 at POST)
- [ ] Navigate to: AI Tweaker → DOCP/EXPO → Enable
- [ ] Select the 5600 MT/s profile
- [ ] Save and reboot
- [ ] Verify:
  ```bash
  sudo dmidecode -t memory | grep "Configured Memory Speed"
  # Should show 5600 MT/s (or 4800 MT/s minimum — anything above 3600 is a win)
  ```

---

## Phase 3 — Node 1 (~30–45 min, shutdown required)

```bash
docker stop $(docker ps -q) && sudo shutdown now
```

- [ ] Open Node 1 chassis
- [ ] **Photograph everything** before touching cables
- [ ] Read and photograph PSU label *(Corsair 1600W — already confirmed, still document model)*
- [ ] **Reseat Samsung 990 PRO 4TB** (M.2 slot — push until it clicks, secure screw)
- [ ] Install **1× Hyper M.2 X16 Gen5 adapter** in available PCIe x16 slot
- [ ] Install **4× Crucial T700 4TB Gen5** NVMe drives into the adapter (16 TB local NVMe)
- [ ] Assess physical clearance for 5th GPU (RTX 3060) — look at remaining PCIe slot spacing with 4× 5070 Ti installed
- [ ] If clearance is good: install **RTX 3060** in the free slot
  - Connect PCIe power cable(s)
  - 220W power limits already set — system stays within Corsair 1600W budget
- [ ] Close chassis, power on

**Verify:**
```bash
lsblk  # Samsung 990 PRO should appear (~3.6 TB)
        # 4x T700 should appear (~3.6 TB each)
nvidia-smi  # 5x GPUs if 3060 installed: 4x 5070 Ti + 1x 3060
```

---

## Phase 4 — DEV (~20 min, shutdown required)

- [ ] Shut down DEV (Windows)
- [ ] Open DEV chassis
- [ ] **Remove RTX 3060** (goes to Node 1 — or sits loose if Node 1 clearance was tight)
- [ ] Install **RX 5700 XT** (from loose inventory) — DEV keeps a display GPU
- [ ] Install **Intel X540-T2 dual-port 10GbE NIC** in PCIe slot
- [ ] Close chassis, power on Windows
- [ ] Connect DEV ethernet → USW Pro XG 10 PoE
- [ ] Verify 10GbE in Device Manager / `iperf3`
- [ ] If RTX 3060 not yet installed in Node 1: go do it now while DEV boots

---

## Phase 5 — The Swap (VAULT + Node 2, ~2–3 hours)

**Do not start this phase without completing pre-session screenshots.**

### 5a — Shutdown both machines

**Node 2:**
```bash
docker stop $(docker ps -q) && sudo shutdown now
```

**VAULT** (via Unraid UI or SSH):
```bash
# SSH: docker stop $(docker ps -q) && poweroff
# Or: Unraid UI → Main → Stop Array → Power Off
```

---

### 5b — VAULT disassembly (TRX50 + 7960X leaving)

- [ ] Open VAULT chassis
- [ ] **Photograph all connections** (HBA cables, NVMe, GPU, front panel)
- [ ] Remove **Arc A380** GPU → set aside (stays with VAULT identity, goes into X870E)
- [ ] Remove **LSI SAS3224 HBA** → disconnect from board side only, leave SATA/SAS cables routed in chassis
- [ ] Remove **4× Crucial NVMe drives** → label each:
  - `T700` = appdata cache (nvme1n1, /mnt/appdatacache)
  - `P310-docker` (nvme0n1, /mnt/docker)
  - `P310-vms` (nvme3n1, /mnt/vms)
  - `P310-transcode` (nvme2n1, /mnt/transcode)
- [ ] Remove **4× Kingston DDR5 ECC** RAM → set aside (going to Node 2/TRX50)
- [ ] Remove CPU cooler
- [ ] Remove **TRX50 AERO D + 7960X** → set aside (going to Node 2 chassis)

---

### 5c — Node 2 disassembly (X870E + 9950X leaving)

- [ ] Open Node 2 chassis (RM52)
- [ ] **Photograph all connections**
- [ ] Remove **RTX 5090** → set aside (stays in RM52 chassis, reinstalls on TRX50)
- [ ] Remove **RTX 4090** → set aside (stays in RM52 chassis, reinstalls on TRX50)
- [ ] Remove **4× Samsung 990 EVO Plus** NVMe → label by slot position (these are Node 2's Ubuntu OS drives)
- [ ] Remove **4× Micron DDR5** RAM → set aside (going to VAULT/X870E)
- [ ] Remove CPU cooler
- [ ] Remove **X870E CREATOR + 9950X** → set aside (going to VAULT chassis)

---

### 5d — Build Node 2 with TRX50

- [ ] Mount **TRX50 AERO D** in RM52 chassis (ATX form factor, standard mounting)
- [ ] Install **7960X** CPU — align triangle markers, zero-insertion-force socket
- [ ] Apply thermal paste, install **CPU cooler** (Threadripper mount — verify cooler bracket matches sTR5)
- [ ] Install **RAM — 6 DIMM config (192 GB):**
  - 4× Kingston DDR5 ECC 32 GB → slots currently populated (A/C/E/G or per manual)
  - 2× G.Skill DDR5 non-ECC 32 GB → 2 of the remaining empty slots
  - **Refer to TRX50 AERO D manual for recommended 6-DIMM slot config**
  - ECC will be disabled in mixed mode — system should still POST and run stably
  - If it refuses to POST: remove G.Skill sticks, run 128 GB ECC only for now
- [ ] Reseat **RTX 5090** in PCIe slot 1 (x16) — connect 16-pin power
- [ ] Reseat **RTX 4090** in PCIe slot 2 (x16) — connect PCIe power
- [ ] Install **4× Samsung 990 EVO Plus** NVMe in TRX50 M.2 slots (Node 2's Ubuntu OS drives)
- [ ] **Power connections — critical:**
  - ATX 24-pin
  - **2× 8-pin EPS** CPU connectors (7960X requires both — verify MSI 1600W cables)
  - PCIe power for both GPUs
- [ ] Connect front panel headers, case fans, USB headers
- [ ] Do not power on yet

---

### 5e — Build VAULT with X870E

- [ ] Mount **X870E CREATOR WIFI** in VAULT chassis (ATX)
- [ ] Install **9950X** CPU
- [ ] Apply thermal paste, install **CPU cooler** (AM5 mount — verify bracket)
- [ ] Install **4× Micron DDR5 32 GB** RAM (128 GB) in X870E DIMM slots
  - X870E has 4 slots — fill all 4 for dual-channel
- [ ] Install **Arc A380** GPU
- [ ] Install **LSI SAS3224 HBA** → reconnect SATA/SAS cables to it
- [ ] Install **4× Crucial NVMe** drives in X870E M.2 slots (4 slots confirmed available):
  - Match labels to pools (T700 → appdata cache, P310 × 3 → docker/vms/transcode)
  - Exact slot doesn't matter — Unraid will re-assign by device path in UI
- [ ] Power connections:
  - ATX 24-pin
  - 1× 8-pin EPS (9950X — 170W TDP, single connector sufficient)
  - PCIe power for Arc A380
- [ ] Connect front panel headers, case fans
- [ ] Plug in **Unraid boot USB** (SanDisk Cruzer Glide 28.7 GB) — this is the OS

---

## Phase 6 — Boot and Recovery

### Boot VAULT first

- [ ] Power on VAULT
- [ ] Monitor via JetKVM (.80) if needed
- [ ] Unraid should boot from USB — new hardware, same OS
- [ ] **Fix MAC address:** Unraid → Settings → Network Settings → update interface MAC or switch to DHCP then re-set static 192.168.1.203
- [ ] Main → **Start Array** — all 9 data disks should mount (they didn't move)
- [ ] Check Pools: appdata, docker, vms, transcode — reassign NVMe devices if needed
- [ ] Start Docker: Settings → Docker → Start (or auto-starts)
- [ ] Verify services accessible:
  - Sonarr: http://192.168.1.203:8989
  - Radarr: http://192.168.1.203:7878
  - Plex: http://192.168.1.203:32400
  - Grafana: http://192.168.1.203:3000

### Boot Node 2

- [ ] Power on Node 2 (TRX50)
- [ ] Monitor via JetKVM (.165) if HDMI/SSH fails
- [ ] Ubuntu should boot from Samsung 990 EVO Plus — GRUB handles hardware change
- [ ] If networking is broken (new NIC name):
  ```bash
  ip link  # note new interface name
  # Edit netplan to match new name
  sudo nano /etc/netplan/50-cloud-init.yaml
  sudo netplan apply
  ```
  TRX50 also has Aquantia onboard (same driver) — interface name may stay the same
- [ ] Verify:
  ```bash
  nvidia-smi          # RTX 5090 + RTX 4090 visible
  free -h             # should show ~192 GB (or 128 GB if G.Skill sticks were pulled)
  sudo dmidecode -t memory | grep "Configured Memory"
  docker ps           # all services running
  ```
- [ ] Restart vLLM and agent services if needed:
  ```bash
  cd ~/services && docker compose up -d
  ```

---

## Phase 7 — Full Verification

```bash
# 10GbE throughput — run from DEV or any node
iperf3 -c 192.168.1.244  # Node 1
iperf3 -c 192.168.1.225  # Node 2
iperf3 -c 192.168.1.203  # VAULT

# NFS still works
ls /mnt/vault/models
ls /mnt/vault/data

# Node 1 storage
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "lsblk | grep -E 'nvme|disk'"
# Expect: Crucial P3 (OS) + Samsung 990 PRO + 4x T700 + (optionally) 990 EVO for model cache

# Node 2 GPU + RAM
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225 "nvidia-smi && free -h"

# Grafana — verify all metrics flowing
# http://192.168.1.203:3000 → Athanor Overview dashboard
```

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| TRX50 won't POST with mixed ECC + non-ECC RAM | Pull G.Skill sticks, run 128 GB ECC only |
| Node 2 Ubuntu boot fails on TRX50 | JetKVM (.165) for console; reinstall Ubuntu if needed (NVMe drives are data only) |
| VAULT Unraid won't boot on X870E | JetKVM (.80) for console; re-flash Unraid USB if needed |
| NVMe pool assignments wrong in Unraid | Reassign manually in UI — data is intact, just path changes |
| Node 2 network interface name changes | Fix netplan — TRX50 has same Aquantia driver, likely same name |
| Node 1 RTX 3060 won't fit physically | Defer to Phase 8 GPU enclosure build |

---

## End State

| System | Before | After |
|--------|--------|-------|
| **Node 1** | 990 PRO missing, no extra NVMe | 990 PRO reseated, 16 TB T700 NVMe, RTX 3060 (if fits) |
| **Node 2** | 9950X, 128 GB @ 3600 MT/s, X870E | 7960X, 192 GB DDR5, TRX50 AERO D, same GPUs |
| **VAULT** | 7960X, 128 GB DDR5 ECC, TRX50 | 9950X, 128 GB DDR5, X870E |
| **DEV** | RTX 3060, 1GbE | RX 5700 XT, 10GbE |
| **Network** | All servers on 1GbE management switch | All servers on 10GbE XG switch |

**What's still deferred:** RTX 3060 → Node 1 (if physical fit was tight), Add2PSU for Phase 8 dual-PSU, GPU enclosure purchase, InfiniBand cards.
