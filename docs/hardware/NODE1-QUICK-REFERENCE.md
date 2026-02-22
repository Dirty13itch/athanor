# Node 1 GPU Power - Quick Reference Card
**Print this page for rack-side reference**

---

## Port Mapping (PSU → GPU)

| PSU Port | Cable | GPU Slot | GPU Model | Connection Type |
|----------|-------|----------|-----------|-----------------|
| **12V-2x6 #1** | Native | **Slot 1** | RTX 4090 | Direct → GPU |
| **12V-2x6 #2** | Native | **Slot 2** | RTX 5070 Ti | Direct → GPU |
| **PCIe #1** | 8-pin (both) | **Slot 3** | RTX 5070 Ti | 2 of 3 adapter inputs |
| **PCIe #2** | 8-pin (both) | **Slot 3 & 4** | RTX 5070 Ti | Shared: 1 to Slot 3, 1 to Slot 4 |
| **PCIe #3** | 8-pin (both) | **Slot 4** | RTX 5070 Ti | 2 of 3 adapter inputs |
| **PCIe #4** | 8-pin (both) | **Slot 5** | RTX 5070 Ti | 2 of 3 adapter inputs |
| **PCIe #5** | 8-pin (both) | **Slot 5 & 6** | 5070 Ti + 3060 | 1 to Slot 5, 1 to Slot 6 |

---

## Adapter Wiring Detail

**Each RTX 5070 Ti adapter needs 3× 8-pin inputs:**

```
Slot 3 Adapter:  Cable A conn1 + Cable A conn2 + Cable B conn1
Slot 4 Adapter:  Cable B conn2 + Cable C conn1 + Cable C conn2
Slot 5 Adapter:  Cable D conn1 + Cable D conn2 + Cable E conn1
```

---

## Installation Order

1. **PSU OFF** (back switch)
2. Connect all cables to **PSU ports first**
3. Connect Slot 1 & 2 (native 12VHPWR)
4. Build Slot 3 adapter (3× 8-pin → adapter → GPU)
5. Build Slot 4 adapter (3× 8-pin → adapter → GPU)
6. Build Slot 5 adapter (3× 8-pin → adapter → GPU)
7. Connect Slot 6 (single 8-pin to RTX 3060)
8. **Visual inspection** (all seated, no loose)
9. **PSU ON**, boot with 1 GPU first

---

## Power-On Test Sequence

| Step | GPUs Connected | Command | Expected Result |
|------|----------------|---------|-----------------|
| 1 | Slot 1 only | `nvidia-smi` | 1 GPU: RTX 4090 |
| 2 | Slot 1 + 2 | `nvidia-smi` | 2 GPUs |
| 3 | Slot 1-3 | `nvidia-smi` | 3 GPUs |
| 4 | All (1-5 or 1-6) | `nvidia-smi` | All GPUs detected |

**After final boot, set power limits:**

```bash
sudo nvidia-smi -i 0 -pl 320  # RTX 4090
sudo nvidia-smi -i 1,2,3,4 -pl 240  # All RTX 5070 Ti
sudo nvidia-smi -i 5 -pl 200  # RTX 3060 (if installed)
```

---

## Safety Checklist

**Before PSU ON:**
- [ ] All 12VHPWR connections **clicked** into place
- [ ] All 3× adapter inputs connected per GPU (9 total for 3 adapters)
- [ ] All PSU modular ports seated firmly
- [ ] No cables blocking fans
- [ ] Motherboard 24-pin + CPU 8-pin connected

**After boot:**
- [ ] All GPUs show in `nvidia-smi`
- [ ] No errors in `sudo dmesg | grep -i pcie`
- [ ] Power draw <50W per GPU at idle

---

## Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| GPU not detected | Reseat adapter, verify all 3× 8-pins connected |
| Won't POST | Enable "Above 4G Decoding" in BIOS |
| PSU shuts down | Set power limits immediately after boot |
| Adapter hot | Normal if warm, STOP if too hot to touch |

---

## Expected Power Draw

| Component | Stock | Optimized | Count | Total Optimized |
|-----------|-------|-----------|-------|-----------------|
| EPYC 7663 | 240W | 180W | 1 | 180W |
| RTX 4090 | 450W | 320W | 1 | 320W |
| RTX 5070 Ti | 300W | 240W | 4 | 960W |
| RTX 3060 | 170W | 200W | 1 | 200W |
| Motherboard + RAM | - | 60W | - | 60W |
| **Total** | **1,950W** | **1,520W** | - | **1,520W** |

**PSU capacity:** 1,600W
**Utilization:** 95%
**Headroom:** 80W (safe)

---

**Full documentation:** `/home/shaun/athanor/docs/hardware/NODE1-GPU-POWER-WIRING.md`
