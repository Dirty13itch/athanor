# Node 1 GPU Power Wiring Guide
**MSI MEG Ai1600T PCIE5 → 5 GPUs**
**Print this document for rack session reference**

---

## Quick Reference Card

| GPU Slot | GPU Model | Power Source | Cables Required |
|----------|-----------|--------------|-----------------|
| **Slot 1** | RTX 4090 | PSU native 12V-2x6 port #1 | 1× 12VHPWR cable |
| **Slot 2** | RTX 5070 Ti | PSU native 12V-2x6 port #2 | 1× 12VHPWR cable |
| **Slot 3** | RTX 5070 Ti | PSU PCIe ports #1 + #2 | 3× 8-pin via adapter |
| **Slot 4** | RTX 5070 Ti | PSU PCIe ports #2 + #3 | 3× 8-pin via adapter |
| **Slot 5** | RTX 5070 Ti | PSU PCIe ports #4 + #5 | 3× 8-pin via adapter |
| **Slot 6** | RTX 3060 (optional) | PSU PCIe port #5 | 1× 8-pin |

**Total PSU Ports Used:** 2× 12V-2x6 + 5× PCIe 8-pin = **7 ports**

---

## PSU Port Layout (Back Panel)

```
MSI MEG Ai1600T PCIE5 Back Panel (modular ports)

┌─────────────────────────────────────────────────────┐
│                                                     │
│  [ATX 24-pin]  [EPS #1]  [EPS #2]                  │
│                                                     │
│  [12V-2x6 #1]  [12V-2x6 #2]                        │  ← Native 12VHPWR
│                                                     │
│  [PCIe #1]  [PCIe #2]  [PCIe #3]  [PCIe #4]  [#5]  │  ← 8-pin PCIe
│                                                     │
│  [SATA/Molex ports...]                             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Wiring Diagram

### Native 12VHPWR Connections (Direct)

```
PSU Back                  Cable                  GPU

[12V-2x6 #1] ─────── [12VHPWR cable] ─────── [RTX 4090 Slot 1]

[12V-2x6 #2] ─────── [12VHPWR cable] ─────── [RTX 5070 Ti Slot 2]
```

---

### Adapter Connections (3× 8-pin per GPU)

**Slot 3 - RTX 5070 Ti #2:**
```
PSU Back                Cable              Adapter            GPU

[PCIe #1] ───┬─ 8-pin connector 1 ───┐
             └─ 8-pin connector 2 ───┤
                                     ├─→ [Adapter] ──→ [Slot 3]
[PCIe #2] ───┬─ 8-pin connector 1 ───┘
             └─ 8-pin connector 2 (unused here)
```

**Slot 4 - RTX 5070 Ti #3:**
```
PSU Back                Cable              Adapter            GPU

[PCIe #2] ───┬─ 8-pin connector 1 (to Slot 3)
             └─ 8-pin connector 2 ───┐
                                     │
[PCIe #3] ───┬─ 8-pin connector 1 ───┤
             └─ 8-pin connector 2 ───┼─→ [Adapter] ──→ [Slot 4]
                                     │
                                     └─ (3 inputs total)
```

**Slot 5 - RTX 5070 Ti #4:**
```
PSU Back                Cable              Adapter            GPU

[PCIe #4] ───┬─ 8-pin connector 1 ───┐
             └─ 8-pin connector 2 ───┼─→ [Adapter] ──→ [Slot 5]
                                     │
[PCIe #5] ───┬─ 8-pin connector 1 ───┘
             └─ 8-pin connector 2 ──────→ [RTX 3060 Slot 6]
```

---

## Step-by-Step Installation

### Phase 1: Pre-Flight Checks

**□ PSU switched OFF** (switch at back)
**□ All GPUs physically installed** in motherboard slots
**□ Retention clips engaged** on all PCIe slots
**□ Materials ready:**
- [ ] 2× native 12V-2x6 cables (from PSU box)
- [ ] 5× PCIe 8-pin cables (from PSU box)
- [ ] 3× adapters (from RTX 5070 Ti boxes)
- [ ] Cable ties or velcro straps
- [ ] Flashlight (for PSU port labels)

---

### Phase 2: PSU Port Connections (PSU → Cables)

**Connect cables to PSU modular ports FIRST (easier access):**

1. **12V-2x6 Port #1** ← Insert native 12VHPWR cable (for RTX 4090)
2. **12V-2x6 Port #2** ← Insert native 12VHPWR cable (for 5070 Ti Slot 2)
3. **PCIe Port #1** ← Insert 8-pin cable "A" (for Slot 3 adapter)
4. **PCIe Port #2** ← Insert 8-pin cable "B" (shared Slot 3/4)
5. **PCIe Port #3** ← Insert 8-pin cable "C" (for Slot 4 adapter)
6. **PCIe Port #4** ← Insert 8-pin cable "D" (for Slot 5 adapter)
7. **PCIe Port #5** ← Insert 8-pin cable "E" (Slot 5 + 3060)

**Verify:** All cables seated firmly with no wiggle at PSU port.

---

### Phase 3: GPU Connections (Cables → GPUs)

#### **Slot 1 - RTX 4090** (Direct Native)
- Route 12V-2x6 cable from PSU port #1 to Slot 1
- Plug into GPU 12VHPWR socket
- **Listen for CLICK** (connector locks in place)
- Verify no wiggle

#### **Slot 2 - RTX 5070 Ti #1** (Direct Native)
- Route 12V-2x6 cable from PSU port #2 to Slot 2
- Plug into GPU 12VHPWR socket
- **Listen for CLICK**
- Verify no wiggle

#### **Slot 3 - RTX 5070 Ti #2** (3× 8-pin Adapter)
1. Take adapter from GPU box
2. Connect **3× 8-pin sockets** on adapter to:
   - Cable A connector 1 (from PCIe port #1)
   - Cable A connector 2 (from PCIe port #1)
   - Cable B connector 1 (from PCIe port #2)
3. Plug adapter 12VHPWR end into GPU
4. Verify all 3× 8-pins seated, adapter locked into GPU

#### **Slot 4 - RTX 5070 Ti #3** (3× 8-pin Adapter)
1. Take second adapter from GPU box
2. Connect **3× 8-pin sockets** on adapter to:
   - Cable B connector 2 (from PCIe port #2) ← shares with Slot 3
   - Cable C connector 1 (from PCIe port #3)
   - Cable C connector 2 (from PCIe port #3)
3. Plug adapter 12VHPWR end into GPU
4. Verify all 3× 8-pins seated, adapter locked into GPU

#### **Slot 5 - RTX 5070 Ti #4** (3× 8-pin Adapter)
1. Take third adapter from GPU box
2. Connect **3× 8-pin sockets** on adapter to:
   - Cable D connector 1 (from PCIe port #4)
   - Cable D connector 2 (from PCIe port #4)
   - Cable E connector 1 (from PCIe port #5)
3. Plug adapter 12VHPWR end into GPU
4. Verify all 3× 8-pins seated, adapter locked into GPU

#### **Slot 6 - RTX 3060** (Optional, Single 8-pin)
- Connect Cable E connector 2 (from PCIe port #5) to GPU 8-pin socket
- Verify seated firmly

---

### Phase 4: Cable Management

**Route cables cleanly:**
- Keep cables away from CPU cooler
- Avoid blocking GPU intake fans
- Use cable ties to bundle parallel runs
- Leave slack near GPU for serviceability
- No sharp bends at connectors

**Label adapters (optional):**
- Tape label on each adapter: "Slot 3", "Slot 4", "Slot 5"
- Helps during future maintenance

---

### Phase 5: Pre-Power Inspection

**□ All GPU power connectors seated** (click/lock engaged)
**□ All PSU modular ports seated** (no loose cables at PSU)
**□ All 3× adapter inputs connected** (9 total 8-pins for 3 adapters)
**□ No cables blocking fans** (GPU or case)
**□ No cables touching heatsinks** or hot components
**□ Motherboard 24-pin connected**
**□ CPU 8-pin EPS connected**

---

## Power-On Sequence

### First Boot (1 GPU Test)

**Disconnect all GPUs except RTX 4090:**
1. PSU ON (switch at back)
2. Press power button
3. Watch for POST
4. Enter BIOS or boot to OS
5. Verify RTX 4090 detected

```bash
# In OS:
nvidia-smi
# Should show 1 GPU: RTX 4090
```

6. Power off completely

---

### Second Boot (2 GPU Test)

**Reconnect Slot 2 (5070 Ti) only:**
1. PSU ON
2. Boot to OS
3. Verify both GPUs detected

```bash
nvidia-smi
# Should show:
# GPU 0: RTX 4090
# GPU 1: RTX 5070 Ti
```

4. Power off

---

### Third Boot (3 GPU Test)

**Reconnect Slot 3 (5070 Ti with adapter):**
1. PSU ON
2. Boot to OS
3. Verify 3 GPUs detected

```bash
nvidia-smi
# Should show 3 GPUs
```

4. Check for adapter issues:

```bash
sudo dmesg | grep -i "pcie\|gpu"
# Look for any power-related errors
```

5. Power off

---

### Final Boot (All 5-6 GPUs)

**Reconnect Slots 4, 5, and optionally 6:**
1. PSU ON
2. Boot to OS
3. Verify all GPUs detected

```bash
nvidia-smi
# Should show all 5 or 6 GPUs with correct models
```

4. Check power draw at idle:

```bash
nvidia-smi dmon -s p -c 1
# All GPUs should be <50W at idle
```

5. Set power limits:

```bash
# RTX 5070 Ti cards (optimized 240W)
sudo nvidia-smi -i 1 -pl 240
sudo nvidia-smi -i 2 -pl 240
sudo nvidia-smi -i 3 -pl 240
sudo nvidia-smi -i 4 -pl 240

# RTX 4090 (optimized 320W)
sudo nvidia-smi -i 0 -pl 320

# RTX 3060 (optimized 200W)
sudo nvidia-smi -i 5 -pl 200
```

---

## Troubleshooting

### Problem: GPU not detected after connection

**Possible causes:**
- [ ] Adapter not fully seated in GPU (should click)
- [ ] One or more 8-pin cables loose at adapter
- [ ] Cable not seated at PSU modular port
- [ ] PCIe slot not fully engaged (reseat GPU)

**Fix:**
1. Power off completely (PSU switch OFF)
2. Reseat all connections for that GPU
3. Verify 12VHPWR sense pins aligned (tiny pins on side)
4. Try native 12VHPWR cable on that GPU to isolate adapter vs GPU issue

---

### Problem: System won't POST with all GPUs

**Possible causes:**
- [ ] Motherboard BIOS needs "Above 4G Decoding" enabled
- [ ] Insufficient PCIe lane assignment
- [ ] Power budget exceeded (should not happen with limits set)

**Fix:**
1. Boot with 2-3 GPUs
2. Enter BIOS
3. Enable "Above 4G Decoding" (usually under Advanced → PCI Subsystem)
4. Enable "Resizable BAR" if available
5. Save and reboot with all GPUs

---

### Problem: PSU shuts down under load

**Possible causes:**
- [ ] Power limits not set (GPUs drawing stock power)
- [ ] Overcurrent protection triggered
- [ ] Loose cable at PSU port

**Fix:**
1. Boot and immediately set power limits (see commands above)
2. Re-verify all PSU modular port connections
3. Test with fewer GPUs to isolate problematic cable

---

### Problem: Adapter gets hot

**Expected behavior:**
- Adapters will be warm under load (60-80°C)
- This is normal for 240W through adapter

**Abnormal behavior:**
- Adapter too hot to touch (>100°C)
- Smell of burning plastic
- Discoloration of connectors

**Fix:**
1. Immediately power off
2. Check all 3× 8-pin cables fully seated
3. Verify using GPU-included adapter, not third-party
4. Replace adapter if damaged

---

## Power Budget Verification

**After all GPUs connected and power limits set:**

```bash
# Install stress testing tool
sudo apt install stress-ng

# Run GPU stress test (5 minutes)
stress-ng --vm 8 --vm-bytes 80% --timeout 300s &
watch -n 1 nvidia-smi

# Monitor:
# - GPU power draw should stay at limits (240W, 320W, etc.)
# - Temperatures should stabilize <85°C
# - No GPUs throttling (GPU MHz stable)
# - PSU should not shut down
```

**Expected total power under full load:**
- Node 1 system: ~1,520W (95% of 1,600W PSU)
- PSU should remain stable
- If PSU shuts down: lower power limits or remove 1 GPU

---

## Post-Installation Checklist

**□ All GPUs detected** (`nvidia-smi` shows all)
**□ Power limits set** (240W, 320W, 200W)
**□ Stress test passed** (5 min full load, stable)
**□ Temperatures normal** (<85°C under load)
**□ No POST errors** (boot is clean)
**□ No dmesg errors** (PCIe/power related)
**□ Cables secured** (cable management complete)
**□ Documentation updated** (BUILD-ROADMAP.md)

---

## Quick Command Reference

```bash
# List all GPUs
nvidia-smi

# Monitor power draw live
watch -n 1 nvidia-smi

# Monitor power, temp, utilization
nvidia-smi dmon -s ptu

# Set power limit (example: GPU 1 to 240W)
sudo nvidia-smi -i 1 -pl 240

# Check PCIe errors
sudo dmesg | grep -i pcie

# Verify GPU PCIe link speed
nvidia-smi -q | grep -A 5 "PCIe"
```

---

## Notes

**Why daisy-chain is safe for adapters:**
- RTX 5070 Ti @ 240W ÷ 3 inputs = 80W per 8-pin
- 8-pin rated for 150W
- Safety margin: 47% headroom per connector
- Daisy-chain cable (2 connectors) = 160W total (53% of 300W cable rating)

**Why NOT safe to daisy-chain without adapter:**
- RTX 5070 Ti stock @ 300W on 2× 8-pins = 150W per connector
- Running at 100% of connector rating (no margin)
- Daisy-chain would route 300W through single cable (100% of rating)

**Adapter distributes load → safe to use both connectors on one cable.**

---

**Document Status:** FIELD-READY
**Last Updated:** 2026-02-21
**Next Review:** After successful Node 1 rack session

**Print this document before rack session. Keep with you during installation.**
