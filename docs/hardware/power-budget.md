# Power Budget

**Analysis of PSU capacity vs. component power draw for node assignment planning.**

---

## PSU Inventory

| PSU | Wattage | Efficiency | 12VHPWR Native | Form Factor |
|-----|---------|------------|-----------------|-------------|
| MSI MEG Ai1600T PCIE5 | 1,600 W | Titanium | ✅ Yes (2× 16-pin) | ATX |
| Corsair AX1600i | 1,600 W | Titanium | ❌ No (8-pin only) | ATX |
| Corsair RM1000e | 1,000 W | Gold | ❌ No | ATX |
| Corsair SF1000L | 1,000 W | Gold | ❌ No | SFX-L |
| Corsair SF750 | 750 W | Platinum | ❌ No | SFX |

**Total capacity: 5,950W**

---

## GPU Power Requirements

| GPU | Typical Draw | Peak Draw | Power Connector |
|-----|-------------|-----------|-----------------|
| RTX 5090 | 575 W | 901 W (transient spike) | 1× 16-pin 12VHPWR |
| RTX 4090 | 450 W | ~500 W | 1× 16-pin 12VHPWR |
| RTX 5070 Ti (×4) | 300 W each | ~350 W each | 1× 16-pin 12VHPWR each |
| RTX 3060 | 170 W | ~200 W | 1× 8-pin |
| Arc A380 | 75 W | ~90 W | 1× 6-pin |

---

## 12VHPWR Adapter Notes

The **Corsair AX1600i** predates the 12VHPWR standard. For nodes using 5070 Ti cards with this PSU:
- Check if 5070 Ti retail boxes include 2× 8-pin → 16-pin adapter cables
- If not: purchase Corsair 12VHPWR Type 4 cables (~$25 each) or CableMod equivalents
- Need up to 4 adapter cables for 4× 5070 Ti cards

The **MSI MEG Ai1600T** has native 16-pin connectors — no adapters needed.

---

## CPU Power Requirements

| CPU | PBP / TDP | PPT (Max) |
|-----|-----------|-----------|
| Threadripper 7960X | 350 W | ~400 W |
| EPYC 7663 | 240 W | ~280 W |
| Ryzen 9 9950X | 170 W | ~200 W |

---

## Recommended PSU-to-Node Assignments

Based on the D1 node layout (see `03-architecture/node-topology.md`):

| Node | PSU | Capacity | GPUs | Est. Peak Load | Headroom |
|------|-----|----------|------|-----------------|----------|
| NEXUS | MSI MEG Ai1600T | 1,600 W | 5090 + 4090 | ~1,450 W | 9% |
| COMPUTE | Corsair AX1600i | 1,600 W | 4× 5070 Ti | ~1,100 W | 31% |
| VAULT | Corsair RM1000e | 1,000 W | Arc A380 | ~400 W | 60% |
| WORKER | Corsair SF1000L | 1,000 W | 3060 | ~775 W | 22% |
| Spare | Corsair SF750 | 750 W | None | — | — |

**⚠️ NEXUS headroom is tight at 9%.** The 5090's transient spikes to 901W are a concern. Monitor for PSU OCP trips. The Ai1600T's Titanium efficiency and high transient handling should manage this, but it's the tightest link in the chain.

---

## Circuit Requirements

| Resource | Recommendation |
|----------|---------------|
| Dedicated circuits | 2× 20A / 240V recommended |
| UPS | 4,000 VA minimum for graceful shutdown |
| Total heat dissipation | ~11,000+ BTU/hour at full load |
| Cooling | Ensure adequate room ventilation / AC capacity |

---

*Last updated: February 2026*
