# Rack Session Checklist

**Goal:** 5GbE everywhere, EXPO on Node 2, Node 1 storage + 5th GPU, DEV refresh, VAULT ↔ Node 2 motherboard swap.

**RAM note:** 192 GB is NOT achievable with current hardware. TRX50 AERO D has 4 DIMM slots (not 8) and requires DDR5 RDIMM only — G.Skill non-ECC UDIMMs are incompatible. Node 2 will have 128 GB DDR5 ECC RDIMM post-swap (same 4× Kingston KF556R28RBE2-32 sticks, same capacity, better CPU). To reach 192 GB would require buying 4× 48 GB DDR5 RDIMMs (~$600-800).

**Confirmed hardware:**
- Node 1 PSU: Corsair 1600W
- Node 2 PSU: MSI 1600W (handles 7960X + RTX 5090 + RTX 4090 at full load)
- All parts in-hand. Zero purchases required for this session.

**Estimated time:** 3–4 hours for the full session including swap.

---

## Pre-Session (Remote, Before Touching Hardware)

- [x] Screenshot VAULT Unraid → Main → array disk assignments — captured (Unraid2.PNG)
- [x] Screenshot VAULT Unraid → Settings → Network Settings — captured (Unraid1.PNG)
- **VAULT current MAC: `10:FF:E0:3E:8F:1E`** (bond0, active-backup eth0+eth1)
- **IP method: DHCP reservation in UniFi** (not static in Unraid) — tied to this MAC
  - After X870E install: VAULT will get a new random IP on first boot (new MACs)
  - Fix: log in via JetKVM (.80) → Unraid Settings → Network Settings → configure static 192.168.1.203 directly, OR update UniFi DHCP reservation to new X870E MAC
  - X870E has Aquantia 5GbE + Intel 2.5GbE — bonding config may need rebuild with new interface names
- VAULT NVMe pool assignments confirmed via SSH — exact mapping:
  - **nvme1n1** = `CT4000T700SSD5_2423E8B78B09` → **/mnt/appdatacache** (T700 4TB)
  - **nvme0n1** = `CT1000P310SSD8_25064E23123B` → **/mnt/docker** (P310 1TB)
  - **nvme2n1** = `CT1000P310SSD8_25074E225AF9` → **/mnt/transcode** (P310 1TB)
  - **nvme3n1** = `CT1000P310SSD8_25074E227551` → **/mnt/vms** (P310 1TB)
  - After X870E install device paths may shift — reassign using serial numbers above in Unraid UI → Main → Pools
- [ ] Clone Unraid boot USB to a second USB stick (insurance)
- [x] On Node 2: `cat /etc/netplan/*.yaml` → interface **enp13s0**, static 192.168.1.225/24, gateway .1
- [x] On Node 2: `lsblk` → OS drive is **nvme3n1** (has /boot/efi, /boot, / — LVM)
- [x] On Node 1: set GPU power limits before installing 3060
  - Min power limit on 5070 Ti is **250W** (not 220W — that's below hardware minimum)
  - 4 × 250W + EPYC 240W + RTX 3060 170W + mobo/misc ~80W ≈ 1,440W → within 1,600W budget
  ```bash
  sudo nvidia-smi -pm 1 && sudo nvidia-smi -pl 250 -i 0,1,2,3
  ```
- [x] Make power limits persistent — `nvidia-power-limits.service` systemd unit deployed and enabled on Node 1

---

## Phase 1 — Cable Moves (~20 min, no downtime)

All three servers have 5GbE onboard. They're just plugged into the wrong switch.

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

## Phase 2 — EXPO *(deferred — handled in Phase 7.5)*

**SKIP this phase.** Node 2's current X870E board is going to VAULT during Phase 5. Rebooting Node 2 just to enable EXPO on a board that's leaving wastes a cycle and creates unnecessary risk before the swap.

EXPO is enabled for both boards in their final positions during **Phase 7.5 BIOS Configuration** (post-swap):
- Node 2 (TRX50 + Kingston RDIMMs): EXPO → 5600 MT/s
- VAULT (X870E + Micron DDR5): EXPO → rated speed (4800–5600 MT/s depending on profile)

---

## Phase 3 — Node 1 (~30–45 min, shutdown required)

```bash
# Before shutdown — audit all installed NVMe drives (may find a 2nd 4TB drive)
lsblk -d -o NAME,SIZE,MODEL,SERIAL | grep -E 'nvme|disk'
sudo shutdown now
```

- [ ] Open Node 1 chassis
- [ ] **Photograph everything** before touching cables
- [ ] Read and photograph PSU label *(Corsair 1600W — already confirmed, still document model)*
- [ ] **Catalog any NVMe drives already installed** — look at M.2 slots, note serials on label. Expected: Crucial P3 Plus (OS) + Samsung 990 PRO slot. If a 2nd 4TB drive is present, document it.
- [ ] **Reseat Samsung 990 PRO 4TB** (M.2 slot — push until it clicks, secure screw)
  - If still not detected after boot: check BIOS → Advanced → M.2 configuration. The 990 PRO slot may share PCIe lanes with a GPU slot — lane sharing must be disabled or the M.2 slot explicitly enabled.
- [ ] Install **1× Hyper M.2 X16 Gen5 adapter** in available PCIe x16 slot
  - **Critical:** This adapter requires PCIe bifurcation (x4x4x4x4) configured in BIOS. Without it, only slot 0 will be addressable. Set this in BIOS before first OS boot (see Phase 7.5).
- [ ] Install **4× Crucial T700 4TB Gen5** NVMe drives into the adapter (16 TB local NVMe)
- [ ] Assess physical clearance for 5th GPU (RTX 3060) — look at remaining PCIe slot spacing with 4× 5070 Ti installed
- [ ] If clearance is good: install **RTX 3060** in the free slot
  - Connect PCIe power cable(s)
  - 250W power limits already set and persistent (nvidia-power-limits.service) — 4×250+240+170+80≈1,440W, within 1,600W budget
- [ ] Close chassis, **boot into BIOS first** (see Phase 7.5 Node 1 section):
  - Set PCIe bifurcation on Hyper M.2 slot → x4x4x4x4
  - Verify M.2 Samsung slot is enabled (not sharing lanes with GPU slots)
  - Save and boot to OS

**Verify:**
```bash
lsblk  # Samsung 990 PRO should appear (~3.6 TB)
        # 4x T700 should appear (~3.6 TB each via Hyper M.2 adapter)
        # If T700s missing: PCIe bifurcation not set — go back to BIOS
        # If 990 PRO missing: BIOS M.2 slot config issue — check lane sharing
nvidia-smi  # 5x GPUs if 3060 installed: 4x 5070 Ti + 1x 3060
```

---

## Phase 4 — DEV (~20 min, shutdown required)

- [ ] Shut down DEV (Windows)
- [ ] Open DEV chassis
- [ ] **Remove RTX 3060** (goes to Node 1 — or sits loose if Node 1 clearance was tight)
- [ ] Install **RX 5700 XT** (from loose inventory) — DEV keeps a display GPU
- [ ] Install **Intel X540-T2 dual-port 5GbE NIC** in PCIe slot
- [ ] Close chassis, power on Windows
- [ ] Connect DEV ethernet → USW Pro XG 10 PoE
- [ ] Verify 5GbE in Device Manager / `iperf3`
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
- [ ] Install **RAM — 4 DIMM config (128 GB DDR5 ECC RDIMM):**
  - 4× Kingston KF556R28RBE2-32 DDR5 ECC RDIMM 32 GB from VAULT
  - Slots: DDR5_A1, DDR5_B1, DDR5_C1, DDR5_D1 (all 4 slots — board is fully populated)
  - **The G.Skill F5-5600J4040D32GX2 kit is NOT compatible** — UDIMMs will not POST on TRX50
  - TRX50 requires DDR5 RDIMM exclusively (per Gigabyte manual + Kingston population rules)
  - 192 GB target is not achievable with current hardware; would require 4× 48 GB RDIMMs
- [ ] Reseat **RTX 5090** in PCIe slot 1 (x16) — connect 16-pin power
- [ ] Reseat **RTX 4090** in PCIe slot 2 (x16) — connect PCIe power
- [ ] Install **4× Samsung 990 EVO Plus** NVMe in TRX50 M.2 slots (Node 2's Ubuntu OS drives)
- [ ] **Power connections — critical:**
  - ATX 24-pin
  - **2× 8-pin EPS** CPU connectors (7960X requires both — verify MSI 1600W cables)
  - PCIe power for both GPUs
- [ ] Connect front panel headers, case fans, USB headers
- [ ] **Reconnect JetKVM ATX power cable** to TRX50 ATX header (was on X870E — move it over)
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
- [ ] **Fix network** (VAULT's old MAC was `10:FF:E0:3E:8F:1E` — X870E will have a different MAC, IP will be random):
  - Option A (easiest): Unraid → Settings → Network Settings → change IPv4 assignment from Automatic to Static → set 192.168.1.203/24, gateway 192.168.1.1
  - Option B: Note new X870E MAC from Network Settings, update UniFi DHCP reservation to new MAC
  - Old bonding config (eth0+eth1 active-backup) may not apply to new interface names — simplest is single interface static
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
  free -h             # should show ~128 GB DDR5 ECC RDIMM (4× Kingston 32 GB)
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
# 5GbE throughput — run from DEV or any node
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

## Phase 7.5 — BIOS Configuration

Do these on first boot (or before first OS boot where noted). All are persistent settings.

### Node 1 (EPYC SP3 — unchanged board, new hardware installed)

- [ ] **PCIe bifurcation** — Required for Hyper M.2 X16 Gen5 adapter
  - BIOS → Advanced → PCIe/PCI Subsystem Settings → find the x16 slot hosting the adapter
  - Set bifurcation: **x4 x4 x4 x4** (enables all 4 M.2 slots on the adapter)
  - Without this, only 1 of 4 T700 drives will appear in OS
- [ ] **M.2 slot enable** — If Samsung 990 PRO still missing after reseat
  - BIOS → Advanced → M.2 configuration → ensure the 990 PRO slot is enabled
  - Some EPYC boards disable M.2 slots when GPU PCIe lanes conflict — disable lane sharing
  - Note which slot the 990 PRO is in; confirm it's not sharing bandwidth with a GPU slot
- [ ] Save and exit → boot to OS → run verify commands from Phase 3

### Node 2 (TRX50 AERO D — new board post-swap)

- [ ] **EXPO / memory speed**
  - BIOS → Advanced → Memory Configuration → EXPO: **Enable**
  - Select **5600 MT/s** profile (Kingston RDIMMs are rated DDR5-5600)
  - If instability: drop to 5200 or 4800 and retry
- [ ] **Fan curves** — TRX50 is large chassis, reconfigure for RM52 case
  - BIOS → Hardware Monitor → fan curves for CPU fan + chassis fans
  - Target: silent at idle, ramp aggressively above 70°C
- [ ] **PCIe slot config** — ensure x16 slots for 5090 and 4090 are both at x16 (not shared)
- [ ] Save, reboot, verify:
  ```bash
  sudo dmidecode -t memory | grep "Configured Memory Speed"
  # Should show 5600 MT/s
  ```

### VAULT (X870E CREATOR — new board post-swap)

- [ ] **Static IP** — set before or immediately after boot (DHCP will give wrong IP with new MAC)
  - Option A (preferred): BIOS/Unraid → see Phase 6 network recovery steps
  - Option B: Set in BIOS if X870E has built-in IP config (unlikely — do it in Unraid UI)
- [ ] **EXPO / memory speed**
  - BIOS → AMD CBS → Memory → EXPO: **Enable**
  - Select rated profile for Micron DDR5 (check sticker on sticks for rated speed)
- [ ] **Storage controller** — ensure LSI HBA PCIe slot is recognized
  - BIOS → Advanced → PCIe → verify the HBA slot is x8 or x16 (not limited to x4)
- [ ] **Boot order** — Unraid boots from USB; ensure USB is first in boot order
  - SanDisk Cruzer Glide should appear as USB device
- [ ] Save and exit → Unraid boots → verify array and pools

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| Node 2 Ubuntu boot fails on TRX50 (GRUB/initrd issue) | JetKVM (.165) for console; reinstall Ubuntu if needed — NVMe OS drives are separate from data |
| Hyper M.2 T700s invisible (PCIe bifurcation not set) | Boot Node 1 BIOS → set x4x4x4x4 bifurcation on adapter slot → reboot |
| VAULT Unraid won't boot on X870E | JetKVM (.80) for console; re-flash Unraid USB if needed |
| NVMe pool assignments wrong in Unraid | Reassign manually in UI — data is intact, just path changes |
| Node 2 network interface name changes | Fix netplan — TRX50 has same Aquantia driver, likely same name |
| Node 1 RTX 3060 won't fit physically | Defer to Phase 8 GPU enclosure build |

---

## End State

| System | Before | After |
|--------|--------|-------|
| **Node 1** | 990 PRO missing, no extra NVMe | 990 PRO reseated, 16 TB T700 NVMe, RTX 3060 (if fits) |
| **Node 2** | 9950X, 128 GB @ 3600 MT/s, X870E | 7960X, 128 GB DDR5 ECC RDIMM, TRX50 AERO D, same GPUs |
| **VAULT** | 7960X, 128 GB DDR5 ECC, TRX50 | 9950X, 128 GB DDR5, X870E |
| **DEV** | RTX 3060, 1GbE | RX 5700 XT, 5GbE |
| **Network** | All servers on 1GbE management switch | All servers on 5GbE XG switch |

**What's still deferred:** RTX 3060 → Node 1 (if physical fit was tight), Add2PSU for Phase 8 dual-PSU, GPU enclosure purchase, InfiniBand cards.
