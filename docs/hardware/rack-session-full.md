# Rack Session — Full Linear Walkthrough

**Everything in one pass: Node 1 storage/GPU + DEV refresh + VAULT↔Node 2 board swap.**

**State entering this doc:** Phase 1 ✅ done (10GbE confirmed, 9.42 Gbps). Node 1 is powered off. Everything else running.

**Time estimate:** 3–4 hours.

---

## PRE-WORK — Do This Before Any More Shutdowns

### Back up VAULT Unraid config

Option A (remote, right now):
```bash
python scripts/vault-ssh.py "tar czf /tmp/unraid-backup-$(date +%Y%m%d).tar.gz /boot/config"
```

Option B (Unraid UI): **Tools → Flash Backup → Download** — saves config ZIP to your PC. Not bootable, but preserves all container/share/pool config.

Option C (bootable clone — best, requires physical access): Insert a second USB stick into VAULT, then:
```bash
python scripts/vault-ssh.py "lsblk -d -o NAME,SIZE,MODEL | grep -v loop"
# Identify the USB stick (e.g., sdb), then:
python scripts/vault-ssh.py "dd if=/dev/sda of=/dev/sdb bs=4M status=progress"
```

---

## ROUND 1 — Node 1 + DEV

### Step 1 — Shut down DEV

Save everything open. **Shut down Windows completely** (not sleep, not hibernate).

Unplug DEV power from wall. Open case.

---

### Step 2 — Pull RTX 3060 from DEV

Disconnect PCIe power cable(s). Press the PCIe slot release latch. Lift out the 3060.

Set aside — it goes into Node 1.

---

### Step 3 — Install in DEV while the case is open

- **RX 5700 XT** — in the x16 slot the 3060 vacated
- **Intel X540-T2** — in any remaining PCIe x8 or x16 slot

Close DEV. Plug power back in. Let Windows boot while you work on Node 1.

---

### Step 4 — Node 1 physical work (chassis already open)

**Photograph everything before touching cables** — GPU positions, cable routing, all of it.

#### 4a — Samsung 990 PRO reseat

Locate the M.2 slot on the ROMED8-2T (two M.2 slots on this board). The primary slot shares PCIe lanes with PCIE2 — if a GPU is in PCIE2, the M.2 may be disabled in BIOS (handled in Step 5b).

Physically: push the 990 PRO firmly until it clicks, secure the retention screw.

#### 4b — Hyper M.2 X16 Gen5 adapter

**Do NOT put it in PCIE2** (PCIE2 shares lanes with the M.2 slot — double conflict). Use any other available x16 slot.

Seat firmly. You can install the T700 drives now or after BIOS — drives won't be harmed either way.

#### 4c — 4× Crucial T700 4TB into the adapter

Seat all four T700s into the Hyper M.2 adapter slots. This is 16 TB of Gen5 NVMe.

#### 4d — RTX 3060

Look at remaining PCIe slots after 4× 5070 Ti and Hyper M.2 adapter. Find a slot with at least 2 slot-widths of clearance. If tight, use the last slot (end of board nearest PSU).

Connect PCIe power — RTX 3060 uses one 8-pin (or 12-pin via adapter, depends on card).

**Power budget:** 4×250W + 240W EPYC + 170W RTX 3060 + 80W misc ≈ 1,440W → within Corsair 1600W. ✓

Close the chassis.

---

### Step 5 — Node 1 BIOS (before booting OS)

Power on Node 1. Press **Del** or **F2** to enter BIOS.

#### 5a — PCIe bifurcation for Hyper M.2 adapter

Navigate to:
```
Advanced → Chipset Configuration → North Bridge → IIO Configuration
```

Find the IOU entry for the slot where you installed the Hyper M.2 adapter. Change from `x16` to **`x4 x4 x4 x4`**.

> If unsure which IOU maps to which slot: set x4x4x4x4 on all free IOUs — won't hurt anything, can tune later.

#### 5b — Samsung 990 PRO M.2 slot

Still in BIOS:
```
Advanced → PCIe/PCI Subsystem Settings
```

Look for M.2 slot configuration. If the 990 PRO slot is disabled or sharing lanes with a PCIe slot, enable it explicitly. If there's a "disable PCIE2 to enable M.2" option, take it — PCIE2 doesn't have anything critical.

#### 5c — Boot order

Verify Crucial P3 Plus (OS NVMe) is first in boot order. Save and exit.

---

### Step 6 — Node 1 OS verify

```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244

# All drives
lsblk -d -o NAME,SIZE,MODEL,SERIAL
# Expect:
#   Crucial P3 Plus — OS drive (~3.6 TB)
#   Samsung 990 PRO — ~3.6 TB  (if missing: BIOS M.2 issue, go back to Step 5b)
#   4× Crucial T700 — 4× ~3.6 TB  (if missing: bifurcation not set, go back to Step 5a)

# GPUs
nvidia-smi
# Expect: 4× RTX 5070 Ti + 1× RTX 3060 = 5 GPUs total

# vLLM still running?
docker ps | grep vllm
```

Node 1 done. ✅

---

### Step 7 — DEV verify (Windows should be booted by now)

Connect DEV ethernet to **USW Pro XG 10 PoE** using one of the X540-T2 RJ45 ports.

In Windows:
- Device Manager → Network Adapters → Intel X540 should appear (auto-installs drivers)
- Optional test from WSL2: `iperf3 -c 192.168.1.244` — expect ~9 Gbps

DEV done. ✅

---

## ROUND 2 — The Big Swap

### Step 8 — Confirm pre-swap checklist

- [ ] VAULT config backed up ✅
- [ ] Node 1 fully verified (drives + GPUs) ✅
- [ ] DEV on 10GbE ✅
- [ ] NVMe pool serial assignments known (from below)

**VAULT NVMe serials (needed for Unraid reassignment after swap):**

| Drive | Serial | Pool |
|-------|--------|------|
| Crucial T700 4TB | `2423E8B78B09` | appdata cache |
| Crucial P310 1TB | `25064E23123B` | docker |
| Crucial P310 1TB | `25074E225AF9` | transcode |
| Crucial P310 1TB | `25074E227551` | vms |

---

### Step 9 — Shut down Node 2 and VAULT

**Node 2:**
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225
docker stop $(docker ps -q)
sudo shutdown now
```

**VAULT:**
```bash
python scripts/vault-ssh.py "docker stop \$(docker ps -q); poweroff"
# Or: Unraid UI → Main → Stop Array → Power Off
```

Wait for both to fully power off before opening cases.

---

### Step 10 — VAULT disassembly

Open VAULT chassis. **Photograph all cable connections before touching anything.**

Remove in this order:
1. **Arc A380** GPU → set aside (stays with VAULT, goes into X870E)
2. **LSI SAS3224 HBA** → disconnect from board side only, leave SATA/SAS cables routed in chassis
3. **4× Crucial NVMe drives** → label each:
   - T700 = **APPDATA**
   - P310 #1 = **DOCKER**
   - P310 #2 = **TRANSCODE**
   - P310 #3 = **VMS**
4. **4× Kingston DDR5 ECC RDIMM** → set aside (going to Node 2 / TRX50)
5. CPU cooler → remove
6. **TRX50 AERO D + 7960X** → remove board → set aside (going to Node 2 chassis)

---

### Step 11 — Node 2 disassembly

Open Node 2 chassis (RM52 middle tray). **Photograph all cable connections.**

Remove in this order:
1. **RTX 5090** → set aside (stays in RM52, goes back on TRX50)
2. **RTX 4090** → set aside (stays in RM52, goes back on TRX50)
3. **4× Samsung 990 EVO Plus** → label by slot position (these are Node 2's Ubuntu OS drives)
4. **4× Micron DDR5 UDIMM** → set aside (going to VAULT / X870E)
5. CPU cooler → remove
6. **X870E CREATOR WIFI + 9950X** → remove board → set aside (going to VAULT chassis)

---

### Step 12 — Build Node 2 with TRX50

Install TRX50 AERO D in RM52 chassis (ATX mounting — standard).

**Build order:**
1. Mount **TRX50 AERO D** in chassis
2. Install **7960X** CPU — sTR5 zero-insertion-force socket, align triangle markers, no force needed
3. Apply thermal paste, mount CPU cooler — confirm bracket is sTR5 compatible
4. Install **4× Kingston DDR5 ECC RDIMM** in slots **DDR5_A1, DDR5_B1, DDR5_C1, DDR5_D1** (all four — board is fully populated at 4 sticks)
5. Install **RTX 5090** in PCIe slot 1 (primary x16) → connect 16-pin power cable
6. Install **RTX 4090** in PCIe slot 2 (secondary x16) → connect PCIe power
7. Install **4× Samsung 990 EVO Plus** in TRX50 M.2 slots (Ubuntu OS drives)
8. **Power connections — critical:**
   - ATX 24-pin
   - **2× 8-pin EPS** CPU connectors — 7960X requires BOTH (check MSI 1600W has both)
   - PCIe power for both GPUs
9. Front panel headers, case fans, USB headers
10. **Move JetKVM ATX power cable** to TRX50 ATX header (was on X870E)

Do not power on yet.

---

### Step 13 — Build VAULT with X870E

Install X870E CREATOR WIFI in VAULT chassis (ATX — standard).

**Build order:**
1. Mount **X870E CREATOR WIFI** in chassis
2. Install **9950X** CPU — AM5 socket, align triangle markers
3. Apply thermal paste, mount CPU cooler — AM5 bracket
4. Install **4× Micron DDR5 UDIMM** — fill all 4 slots
5. Install **Arc A380** GPU
6. Install **LSI SAS3224 HBA** → reconnect SATA/SAS cables
7. Install **4× Crucial NVMe** drives in X870E M.2 slots — match labels (Unraid reassigns by serial, so exact slot doesn't matter):
   - APPDATA, DOCKER, TRANSCODE, VMS
8. **Power connections:**
   - ATX 24-pin
   - 1× 8-pin EPS (9950X — single connector sufficient)
   - PCIe power for Arc A380
9. Front panel headers, case fans
10. **Insert Unraid boot USB** (SanDisk Cruzer Glide 28.7 GB) — this is the OS

---

## ROUND 3 — Boot and Recovery

### Step 14 — Boot VAULT first

Power on VAULT. Watch via **JetKVM at 192.168.1.80** if needed.

Unraid boots from USB. New board = new MAC addresses = DHCP gives a random IP. Fix network first.

**In Unraid UI (access via JetKVM if needed):**
- Wait for boot to complete
- **Settings → Network Settings**
- Change from Automatic (DHCP) to **Static**
- IP: `192.168.1.203` | Netmask: `255.255.255.0` | Gateway: `192.168.1.1` | DNS: `192.168.1.1`
- Old bonding config (eth0+eth1 active-backup) likely doesn't apply with new NICs — use single interface for now
- Apply and reconnect

Verify network from WSL2:
```bash
python scripts/vault-ssh.py "ip addr show"
```

**Start array and verify pools:**
- Unraid UI → **Main → Start Array**
- All 9 data HDDs should mount (they didn't move)
- Check **Pools** → appdata, docker, vms, transcode
- If any NVMe pool shows wrong device: click pool → reassign by serial number (table in Step 8)
- **Settings → Docker → Start** (or confirm auto-start)

**Verify services:**
```
http://192.168.1.203:8989   ← Sonarr
http://192.168.1.203:7878   ← Radarr
http://192.168.1.203:9090   ← Prometheus
http://192.168.1.203:3000   ← Grafana
http://192.168.1.203:32400  ← Plex
```

VAULT done. ✅

---

### Step 15 — Boot Node 2

Power on Node 2 (TRX50). Watch via **JetKVM at 192.168.1.165** if needed.

Ubuntu should boot from Samsung 990 EVO Plus. Both X870E and TRX50 have Marvell/Aquantia 10GbE NICs using the same `atlantic` kernel driver — Ubuntu will load it automatically. Interface name may change.

**If SSH works:**
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225

nvidia-smi          # RTX 5090 + RTX 4090 — both visible
free -h             # ~128 GB DDR5 ECC RDIMM (4× Kingston 32 GB)
lsblk               # 4× Samsung 990 EVO Plus (Ubuntu OS)
docker ps           # all services running
```

Restart services if needed:
```bash
cd ~/services && docker compose up -d
```

---

**If SSH fails — network interface name changed:**

Use JetKVM (.165) for console access. Log in, then:
```bash
ip link
# Note the new interface name (e.g., enp6s0 instead of enp13s0)

sudo nano /etc/netplan/50-cloud-init.yaml
# Change the interface name to match what ip link shows

sudo netplan apply
```

---

**If Ubuntu won't boot at all:**

Enter UEFI setup (Del/F2 at POST):
- Set boot order: NVMe first (look for Ubuntu EFI entry on Samsung 990 EVO Plus)
- If no Ubuntu entry listed: go to UEFI Shell and boot manually:
  ```
  fs0:\EFI\ubuntu\grubx64.efi
  ```
  Then from running Ubuntu: `sudo grub-install` to register with the new UEFI.

Node 2 done. ✅

---

### Step 16 — BIOS Configuration

#### Node 2 (TRX50 AERO D) — EXPO

Reboot Node 2. Press **Del** at POST.

```
Gigabyte BIOS → MIT tab (Memory Intelligence Tweaker)
  → Advanced Memory Settings
  → XMP/EXPO Profile: EXPO I → 5600 MT/s
```

If MIT tab isn't visible: try **Settings → AMD CBS → Memory → EXPO**.

Save and reboot. Verify:
```bash
sudo dmidecode -t memory | grep "Configured Memory Speed"
# Should show: 5600 MT/s
```

If instability after enabling: drop to 5200 MT/s and retry.

Also set fan curves while in BIOS: **Hardware Monitor** → ramp above 70°C.

#### VAULT (X870E CREATOR) — EXPO + boot order

Reboot VAULT (Unraid UI → System → Reboot). Press **Del** at POST.

```
ASUS BIOS → Extreme Tweaker (or AI Tweaker)
  → EXPO/XMP: Enable
  → Select rated profile for Micron DDR5 (check sticker on sticks for rated speed)
```

Also verify:
- Boot order: USB device (SanDisk Cruzer) is first
- Advanced → PCIe → LSI HBA slot is at x8 (not limited to x4)

Save and reboot. Verify Unraid boots normally, array starts.

#### Node 1 — No changes needed

Bifurcation and M.2 were already set in Step 5. Already verified in Step 6.

---

### Step 17 — Full Verification

From DEV (WSL2) or any machine:

```bash
# 10GbE to all nodes
iperf3 -c 192.168.1.244   # Node 1 — expect 9+ Gbps
iperf3 -c 192.168.1.225   # Node 2 — expect 9+ Gbps
iperf3 -c 192.168.1.203   # VAULT  — expect 9+ Gbps

# NFS still working
ls /mnt/vault/models
ls /mnt/vault/data

# Node 1 storage + GPUs
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "lsblk && nvidia-smi"
# Expect: P3 Plus (OS) + 990 PRO + 4× T700 + 5× GPUs (4× 5070 Ti + 3060)

# Node 2 GPUs + RAM
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225 "nvidia-smi && free -h"
# Expect: RTX 5090 + RTX 4090 + 128 GB DDR5 @ 5600 MT/s

# Grafana — all metrics flowing
# http://192.168.1.203:3000 → Athanor Overview dashboard
```

---

## Quick Reference

| Step | What | If it goes wrong |
|------|------|-----------------|
| 5a | Node 1 bifurcation | T700s missing → BIOS → IIO Config → x4x4x4x4 |
| 5b | Node 1 M.2 slot | 990 PRO missing → BIOS → disable PCIE2 lane sharing |
| 12 | Build Node 2 | Missing EPS connector → MSI 1600W needs both 8-pin CPU cables |
| 13 | Build VAULT | Boot USB not found → verify USB inserted, set boot order |
| 14 | VAULT network | Wrong IP → JetKVM (.80) → Unraid → Settings → Static IP |
| 14 | VAULT pools | Wrong NVMe assignment → reassign by serial in Unraid UI |
| 15 | Node 2 network | NIC name changed → JetKVM (.165) → fix netplan |
| 15 | Node 2 no boot | UEFI boot order wrong → set NVMe first → reboot |
| 16 | EXPO instability | Drop TRX50 to 5200 MT/s |

---

## End State

| System | Before | After |
|--------|--------|-------|
| **Node 1** | 990 PRO missing, no extra NVMe | 990 PRO reseated, 16 TB T700 NVMe, RTX 3060 |
| **Node 2** | 9950X, 128 GB DDR5 @ 3600, X870E | 7960X, 128 GB DDR5 ECC @ 5600, TRX50 AERO D |
| **VAULT** | 7960X, 128 GB DDR5 ECC, TRX50 | 9950X, 128 GB DDR5, X870E CREATOR |
| **DEV** | RTX 3060, 1GbE | RX 5700 XT, 10GbE (X540-T2) |
| **Network** | All servers on 1GbE management switch | All servers on 10GbE XG switch |
