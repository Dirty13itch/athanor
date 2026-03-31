# Athanor Rack Session — Field Manual

**Offline-usable. Assumes zero ability to ask questions.**
**Print this or load it on your phone before starting. Read it end to end before touching hardware.**

---

## Overview

Four machines. One session. The work breaks into two independent rounds that share no downtime window.

**Round 1 — Node 1 + DEV** (no swap, no coordination needed)
- Node 1: reseat Samsung 990 PRO, install Hyper M.2 adapter with 4x T700, install RTX 3060
- DEV: remove RTX 3060, install RX 5700 XT + Intel X540-T2 5GbE NIC

**Round 2 — The Big Swap** (VAULT and Node 2 simultaneously)
- VAULT: TRX50 + 7960X comes out, X870E + 9950X goes in
- Node 2: X870E + 9950X comes out, TRX50 + 7960X goes in
- GPUs stay in their respective cases (5090 + 4090 stay in RM52)
- NVMe drives and RAM swap with their boards

**End state:**
- Node 1: 990 PRO reseated, 4 TB T700 NVMe (4× 1TB) on Hyper M.2, RTX 3060 added
- Node 2: 7960X, 128 GB DDR5 ECC RDIMM, TRX50 AERO D
- VAULT: 9950X, 128 GB DDR5, X870E CREATOR WIFI
- DEV: RX 5700 XT, Intel X540-T2 5GbE
- Network: all servers on 5GbE XG switch

**Time estimate:** 3-4 hours total.

---

## TOOLS AND SUPPLIES NEEDED

- Phillips head screwdriver (medium, for M.2 screws, case screws, GPU retention)
- Zip ties or tape for cable management
- Painter's tape or masking tape for labels
- Permanent marker
- Anti-static wrist strap — use it
- Thermal paste (pea-sized amounts, 4 CPUs being reseated: 9950X and 7960X)
- Isopropyl alcohol (90%+) and lint-free cloth or coffee filter for CPU paste cleanup
- Phone or tablet for photos before disassembly — take these before every cable move

---

## PART ONE — COMPONENT IDENTIFICATION

This section tells you how to physically identify every part involved. Read it before opening any case.

### 1.1 — Identifying the Hyper M.2 X16 Gen5 Adapters (3 loose, use 1)

You have three identical ASUS Hyper M.2 X16 Gen5 cards. They are interchangeable. Pick any one.

**What it looks like:**
- A PCIe card, approximately half the length of a GPU, roughly 200mm long
- Has a large, flat PCB that is almost entirely populated by 4 M.2 slots arranged in a row
- Each M.2 slot has its own retention screw hole and a small retaining clip at the far end
- PCIe connector at the bottom edge is full-length x16 (same width as a GPU connector)
- Model silk-screened on the PCB: "Hyper M.2 X16 Gen 5 Card" or similar ASUS branding
- No active cooling required — passive heatspreader over the slot area
- You will install 4x T700 NVMe drives into this card

**The four M.2 slots on the card:**
- Labeled M2_1 through M2_4 (or similar) from edge to edge
- Supports M.2 2280 form factor (the standard 80mm long drive)
- Each slot has a small plastic retention clip at the drive tip end and a threaded standoff at the edge for the retaining screw

### 1.2 — Identifying the Crucial T700 NVMe Drives

**Crucial T700 (the Gen5 drives going into Node 1):**
- 4 loose, all identical, all **1TB each** (4TB total)
- Physical label reads "Crucial T700" with "PCIe Gen 5 NVMe" marking
- Form factor: M.2 2280 (22mm wide, 80mm long — standard size)
- Has a dark/black heatsink or label, distinct from the P310s
- Connector edge (the gold notch end): single M-key notch
- These are the FAST ones — Gen5, rated ~12,400 MB/s read
- They go into the Hyper M.2 adapter in Node 1

**Crucial P310 (the VAULT cache drives — do NOT confuse with T700):**
- 3 loose + 1 in VAULT = total pool: 4 drives (the in-VAULT one is separate from the 4TB T700)
- Actually there is 1x Crucial T700 4TB in VAULT (the appdata cache) plus 3x Crucial P310 1TB
- P310s are 1TB capacity (smaller than T700)
- P310 label reads "Crucial P310" with Gen4 marking
- Thinner, lighter construction than the T700s
- Keep the 3 VAULT P310s together as a group — they will follow the X870E board to VAULT

**Crucial T700 in VAULT (the existing one):**
- This is the 4TB T700 currently mounted in VAULT as the appdata cache pool
- It is NOT from the loose pile — it came out of VAULT itself
- Serial: 2423E8B78B09
- Label it APPDATA when you remove it — it travels with the NVMe group to the X870E in VAULT

**Samsung 990 PRO (Node 1's missing drive):**
- Already in Node 1's M.2 slot — or should be — just likely not seated properly
- Label reads "Samsung 990 PRO"
- Gen4 NVMe, 4TB capacity
- This drive does NOT move — it stays in Node 1

**Samsung 990 EVO Plus (Node 2's Ubuntu OS drives):**
- 4x 1TB drives, currently in Node 2
- Label reads "Samsung 990 EVO Plus"
- These are Node 2's operating system drives — they travel with the TRX50 board to Node 2
- Keep all four together as a set

### 1.3 — Identifying GPUs

**RTX 5070 Ti (4x in Node 1) — stay in Node 1:**
- Two are MSI brand, two are Gigabyte brand
- All are RTX 5070 Ti, 16GB GDDR7
- Two-slot or three-slot cooler depending on card
- PCIe power: 16-pin (12VHPWR) connector — thick, squarish, 16 pins in two rows
- These DO NOT move — they stay in Node 1

**RTX 5090 (in Node 2) — stays in RM52 chassis:**
- PNY brand — look for PNY label/branding
- 32GB GDDR7, physically large (three-slot cooler minimum)
- Power: 16-pin 12VHPWR connector
- Goes from X870E slot → TRX50 slot 1 (same chassis, different board)

**RTX 4090 (in Node 2) — stays in RM52 chassis:**
- ASUS brand — look for ASUS ROG or TUF label
- 24GB GDDR6X, physically very large
- Power: likely 3x 8-pin PCIe OR a 16-pin adapter cable
- Goes from X870E slot → TRX50 slot 2 (same chassis, different board)

**RTX 3060 (in DEV) — moves to Node 1:**
- Modest two-slot card
- 12GB GDDR6
- Power: one 8-pin PCIe connector (standard)
- Comes OUT of DEV, goes INTO Node 1

**RX 5700 XT (loose) — goes into DEV:**
- ASUS ROG STRIX branding
- 8GB GDDR6, AMD GPU (red logo)
- Power: typically 2x 8-pin PCIe connectors
- Goes FROM loose pile INTO DEV

**Intel Arc A380 (in VAULT) — stays with VAULT identity:**
- Small card, single slot or minimal heatsink
- Intel branding/logo
- This stays with VAULT — it comes out of TRX50, goes into X870E (same physical chassis)

### 1.4 — Identifying RAM

**Samsung DDR4 ECC RDIMM (Node 1) — DO NOT MOVE:**
- 7 sticks, 32GB each
- Label: Samsung M393A4K40DB3-CWE
- DDR4 form factor (shorter than DDR5)
- These stay in Node 1 forever — they are DDR4 and nothing else uses DDR4 ECC RDIMM

**Micron DDR5 UDIMM (Node 2 → VAULT):**
- 4 sticks, 32GB each, 128GB total
- Label: Micron CP32G60C40U5B.M8B3
- DDR5, no heatspreader or minimal heatspreader
- Move FROM Node 2 X870E → VAULT X870E
- UDIMM type — no registration chip on edge

**Kingston DDR5 ECC RDIMM (VAULT → Node 2):**
- 4 sticks, 32GB each, 128GB total
- Label: Kingston KF556R28RBE2-32 (or similar — check for "KF5" prefix)
- DDR5, ECC, RDIMM — has registration chip (small chip on PCB near center)
- Move FROM VAULT TRX50 → Node 2 TRX50
- CRITICAL: These are RDIMM type. TRX50 AERO D only accepts RDIMM. Do not substitute.

**G.Skill DDR5 UDIMM (DEV) — DO NOT MOVE:**
- 2 sticks, 32GB each
- Label: G.Skill F5-5200J3636D32G
- Stay in DEV. Not involved in the swap.

**How to tell UDIMM from RDIMM:**
- Hold the stick horizontally, connector side down
- Look at the center of the PCB from the side
- RDIMM: has a small additional chip (the register/buffer) visible as an extra component
- UDIMM: the PCB is relatively flat on both sides between the DRAM chips
- When in doubt: check the label. "R" in the part number = RDIMM. "U" or no letter = UDIMM.

### 1.5 — Identifying the Intel X540-T2 NIC (loose, goes into DEV)

- A PCIe card with two RJ45 Ethernet ports on the bracket
- Reads "Intel Ethernet Server Adapter X540-T2" on the PCB or bracket
- PCIe x8 connector (shorter gold connector than x16)
- You have 3 similar cards — Intel X540-T2 and two SR-PT02-X540 clones
- Any of them will work — they're all X540 chipset, all dual-port 5GbE
- Pick any one for DEV

### 1.6 — Identifying the Unraid Boot USB

- SanDisk Cruzer Glide
- 28.7 GB capacity (shows as ~29 GB in OS)
- Black plastic body with red slider to extend USB connector
- This IS the operating system for VAULT — it does not contain data but Unraid's OS configuration is on it
- Currently plugged into VAULT
- Comes out of VAULT's TRX50 setup → goes into VAULT's X870E setup (same chassis, just moves with the OS)

---

## PART TWO — MOTHERBOARD LAYOUTS

Read the layout for each board you'll be working on. The slot positions matter.

### 2.1 — ASRock Rack ROMED8-2T (Node 1 — board stays, hardware is added)

**Form factor:** ATX (extended — server ATX, fits in RM52 upper tray)
**Socket:** SP3 (single EPYC socket)
**RAM:** 8x DIMM slots, DDR4 ECC RDIMM, currently 7 populated

**RAM slot layout (left to right facing board from front):**
```
[A1] [B1] [C1] [D1] [E1] [F1] [G1] [H1]
 32G   32G  32G  32G  32G  32G  32G  EMPTY
```
All Samsung M393A4K40DB3-CWE. Do not disturb.

**PCIe slot layout (top to bottom, numbered from CPU):**
```
PCIE1  — x16 slot (closest to CPU)
PCIE2  — x16 slot *** CRITICAL: AVOID FOR HYPER M.2 ***
PCIE3  — x8 slot
PCIE4  — x8 slot
PCIE5  — x16 slot
PCIE6  — x8 slot (may be blocked by GPU above)
PCIE7  — x8 slot (lowest, near PSU area)
```

**CRITICAL PCIe WARNING:**
PCIE2 shares PCIe lanes with the M.2 slot. If you install the Hyper M.2 adapter in PCIE2, it creates a double conflict: the adapter itself competes with the M.2 slot for lanes, and the M.2 is also already serving the Samsung 990 PRO. Use PCIE3 or PCIE5 instead.

**Actual GPU positions:** 4x RTX 5070 Ti currently occupy PCIE1, PCIE2 (or nearby), and two others. Before installing anything new, photograph the current layout and count which slots are occupied.

**M.2 slot locations on ROMED8-2T:**
- Two M.2 slots on the board
- One shares bandwidth with PCIE2 (the problematic one)
- The Samsung 990 PRO should be in the M.2 slot — verify it's seated, then enable it in BIOS

**BIOS key:** Delete or F2 at POST

### 2.2 — Gigabyte TRX50 AERO D (VAULT → Node 2)

**Form factor:** E-ATX
**Socket:** sTR5 (Threadripper)
**RAM:** 4x DIMM slots, DDR5 ECC RDIMM ONLY — no exceptions

**RAM slot layout:**
```
CPU
[DDR5_A1] [DDR5_B1] [DDR5_C1] [DDR5_D1]
```
All 4 slots get the 4x Kingston KF556R28RBE2-32 sticks.
The board does not support mixed RDIMM/UDIMM. Do not attempt to use the Micron or G.Skill sticks.

**PCIe slot layout (top to bottom):**
```
PCIEX16_1  — PCIe 5.0 x16 (primary GPU slot — RTX 5090 goes here)
PCIEX16_2  — PCIe 5.0 x16 (secondary GPU slot — RTX 4090 goes here)
[additional slots for HBA/cards as needed]
```

**M.2 slots:**
- Multiple M.2 slots available (exact count: 4+)
- 4x Samsung 990 EVO Plus (Node 2's Ubuntu drives) go here
- Slots are typically along the board edges and between GPU slots
- Look for connectors with small retention clips at the drive-tip end

**Power connectors — CRITICAL:**
- ATX 24-pin (large, main power)
- TWO 8-pin EPS CPU connectors — the 7960X has a 350W TDP and requires both
- Look for two 8-pin square connectors near the CPU socket area
- If you only connect one, the system may not POST or may not boot under load
- MSI 1600W PSU in Node 2 has both — find both cables

**Fan headers:**
- CPU fan header near CPU socket
- Multiple system fan headers around board edges
- Use the fan headers that match your cooler bracket

**BIOS key:** Delete at POST
**BIOS name:** Gigabyte UEFI BIOS

### 2.3 — ASUS ProArt X870E-CREATOR WIFI (Node 2 → VAULT)

**Form factor:** ATX
**Socket:** AM5 (Ryzen 9000 / 7000 series)
**RAM:** 4x DIMM slots, DDR5 UDIMM or RDIMM (consumer-friendly — accepts both)

**RAM slot layout:**
```
CPU
[A1] [A2] [B1] [B2]
```
Where A1/B1 are the slots farther from CPU, A2/B2 are closer.
The Micron DDR5 UDIMM sticks (coming from Node 2) go in all 4 slots.
For dual-channel with 4 sticks: populate all 4. No special configuration needed.

**PCIe slot layout:**
```
PCIEX16_1  — PCIe 5.0 x16 (top, nearest CPU — primary slot)
PCIEX16_2  — PCIe 4.0 x16 (secondary slot, lower)
```

For VAULT:
- Arc A380 goes in PCIEX16_1 (or whichever slot physically works with your HBA)
- LSI SAS3224 HBA goes in the other x16 or x8 slot
- Arc A380 is a low-power card — it can go in the secondary slot without issue

**M.2 slots:**
- At least 2 M.2 slots confirmed available (the board lists 2+ in specs)
- All 4 Crucial NVMe drives (T700 + 3x P310) go into M.2 slots
- If you run short of M.2 slots, use the T700 first (it's the appdata cache, most performance-sensitive)

**Power connectors:**
- ATX 24-pin
- ONE 8-pin EPS CPU connector (9950X is 170W TDP — one connector is sufficient)
- PCIe power for Arc A380 (may be single 8-pin or PCIe 6+2 pin)

**Boot order for Unraid:**
- Unraid boots from the SanDisk Cruzer USB — ensure USB is first in boot order
- In ASUS BIOS: Boot menu → Boot Override or Boot Priority → USB first

**BIOS key:** Delete or F2 at POST
**BIOS name:** ASUS UEFI BIOS (Extreme Tweaker tab for OC/EXPO)

---

## PART THREE — PHYSICAL PROCEDURES

How to perform each physical action. Read these before you need them.

### 3.1 — Removing a GPU

1. **Power off the machine and unplug power from the wall.** Wait 30 seconds for capacitors to discharge.
2. Open the case. Ground yourself by touching the metal case frame.
3. **Disconnect power cables first.** For 16-pin (12VHPWR): grip the connector body, not the wires, and pull straight out. There may be a small squeeze-tab on the connector — press it while pulling. For 8-pin: pinch the clip tab on the side and pull straight out.
4. **Locate the PCIe slot retention latch.** This is a small plastic lever at the far end of the PCIe slot (end away from the card's bracket). On most boards it requires pushing down or sideways to disengage. On some boards it is automatic. Look at it — the direction of release is usually molded into the plastic.
5. **Press the latch to release the card.** You should feel/hear a click as the latch moves. Keep it pressed.
6. **While holding the latch released, grip the GPU** by the top edge (heatsink fins) and the rear bracket. Do NOT grab by fans or power connectors.
7. Lift the card straight up and out of the slot. It should come out smoothly. If it feels stuck, recheck the latch — do not force it.
8. Set the GPU on a non-static surface (the anti-static bag it came in, or cardboard). Connector edge down is fine; don't stack GPUs.

**What you should feel:** Smooth resistance as the gold PCIe fingers slide out of the slot. No grinding, no snapping.

### 3.2 — Installing a GPU

1. Machine is powered off and unplugged.
2. Remove the appropriate PCIe slot cover bracket(s) from the case rear panel. A double-wide GPU needs two slot covers removed. A triple-slot GPU needs three.
3. Hold the GPU by the top edge and rear bracket. Do NOT touch the gold PCIe connector fingers.
4. Align the card: PCIe connector edge faces down, bracket faces the rear of the case. The gold connector should align directly above the PCIe slot opening.
5. Lower the card into position. The bracket rear slides into the case's bracket channel. The PCIe connector aligns with the slot.
6. Press down firmly and evenly across the length of the card. You will feel resistance from the slot contacts, then a click as the retention latch engages at the far end.
7. **Verify seating:** Look at the PCIe slot from the side. The gold connector edge should be fully inside the slot with no gap. The retention latch should be in the locked position.
8. Secure the bracket to the case with the bracket screw(s).
9. Connect power cables. For 16-pin (12VHPWR): align the connector (it is keyed — only one orientation works), push firmly until it seats and any lock tab clicks. For 8-pin: align the clip-tab side, push until it clicks.

**What you should feel:** A solid click when the retention latch engages. Power connectors click when fully seated.

**If the card won't seat:** Check that you have the right slot (x16 slots have longer openings). Check that no other card or cable is blocking the path. Never force a GPU into a slot.

### 3.3 — Removing an NVMe Drive

1. Machine powered off, unplugged.
2. Locate the M.2 slot. The drive is held at a 30-degree angle from the board by a retention screw at the drive-tip end.
3. Remove the retention screw (Phillips head, small). Turn counterclockwise. Hold the drive as you remove the last few turns — it will spring up slightly when free.
4. The drive will angle up to approximately 30 degrees. Slide it straight out of the M.2 connector by pulling it away from the connector end. Do not lever it.
5. Place the drive on a non-static surface, connector edge up. Label it immediately if there are multiple drives being removed.

**What you should feel:** The drive springs up slightly when the screw is removed. Slides out smoothly.

### 3.4 — Installing an NVMe Drive

1. Identify the M.2 slot type. M.2 slots have a notch cut at specific positions — M-key is the most common for NVMe and has a notch at one position along the gold connector. Your T700 and P310 drives are all M-key.
2. Look at the drive's gold connector edge. There is a notch cut into the gold fingers. This notch aligns with a key in the M.2 slot — it only goes in one way.
3. Insert the connector end of the drive into the M.2 slot at approximately a 30-degree angle (same angle as the slot's retention standoff height). Do NOT force it flat.
4. Push the connector fully into the slot. You will feel it seat. The drive should now be at approximately 30 degrees, with the tip end raised.
5. Press the tip of the drive down toward the board (the drive flexes slightly — this is normal) and hold it flat while threading the retention screw into the standoff.
6. Tighten the screw clockwise until snug. Do not overtighten — the screw threads in the plastic standoff strip easily.

**What you should feel:** Smooth insertion into the slot. The drive angle naturally matches the standoff height. Screw threads catch immediately.

**If the drive won't seat:** Verify notch alignment — flip the drive end for end and try again. Check that you're using an M.2 slot (not a different connector type). Verify the drive length (2280 = 80mm long; most drives are this length).

### 3.5 — Removing RAM

1. Machine powered off, unplugged.
2. Locate the DIMM slot. Both ends have plastic retention clips. Some boards have clips on both ends; some have a clip on one end and a fixed hook on the other.
3. Press the clip(s) outward simultaneously. They hinge outward to release.
4. The RAM stick will spring up slightly when released. Grip it by the top edge (between the DRAM chips) and pull it straight up and out.
5. If removing multiple sticks from a multi-channel system, keep the sticks together as a matched set and note which slot each came from (or don't — for this session, all sticks within each system are identical and interchangeable).

**What you should feel:** Clips hinge outward smoothly. Stick springs up with light pressure.

### 3.6 — Installing RAM

1. Identify the correct slots to populate. Check the motherboard layout section above for each board.
2. Open the retention clips by pressing them outward.
3. Hold the RAM stick by the top edge. Orient it so the notch on the connector edge aligns with the key in the slot. DDR4 and DDR5 have notches in different positions — they cannot be installed in the wrong socket type.
4. Align the stick directly above the slot. The notch must match.
5. Press down firmly and evenly along the length of the stick using your thumbs at both ends.
6. Continue pressing. The retention clips will spring closed automatically when the stick is fully seated.
7. Visually confirm both clips are in the fully vertical/locked position. A partially seated stick will have one or both clips not fully closed.

**What you should feel/hear:** A distinct click (or two clicks) as the retention clips engage. The stick should feel firmly locked with no play.

**If it won't seat:** Verify the notch alignment. Verify DDR type (DDR4 vs DDR5 — they are not interchangeable). Apply even pressure — not just on one end.

### 3.7 — Removing a CPU Cooler

**Before starting:** The cooler may be thermally bonded to the CPU if the paste has dried. Do not just yank it.

**For screwed-down coolers (most tower coolers, all TR5 coolers):**
1. Disconnect the fan power cable from the CPU fan header.
2. Loosen the mounting screws in a cross pattern (opposite corners alternately) — do not fully remove one before starting the others. Loosen each one a quarter turn at a time in sequence.
3. After all screws are loose, try to gently twist the cooler base left and right while lifting. This breaks the thermal paste bond. If it feels stuck, apply more twisting force — do not pull straight up as this can lift the CPU out of the socket with the cooler.
4. Once the paste bond breaks, lift the cooler straight off.
5. Set aside. The paste on the cooler base can be cleaned or left for now.

**Critical for sTR5 (Threadripper 7960X):**
- Threadripper coolers use a large bolt-through mounting system
- Remove the 4 corner screws in X pattern
- The CPU will stay in the socket (sTR5 has a retention mechanism)

**Critical for AM5 (Ryzen 9950X):**
- AM5 uses a standard AM5 bracket
- Remove the 4 mounting screws in X pattern
- The CPU frame holds the CPU in place after cooler removal

### 3.8 — Applying Thermal Paste and Installing Cooler

**Cleanup first:**
1. Use isopropyl alcohol (90%+) on a lint-free cloth to clean old paste off CPU IHS (integrated heat spreader — the metal top of the CPU) and cooler base.
2. Rub gently until no grey/silver residue remains. Let dry.

**Applying paste:**
1. Put a pea-sized dot (approximately 4mm diameter) of paste in the center of the CPU IHS.
2. Do not spread it manually — the cooler mounting pressure will spread it.
3. If using a very large CPU (like Threadripper 7960X with its large IHS), use a slightly larger blob or a thin line from edge to edge. The IHS is much larger than a standard desktop CPU.
4. Alternative: spread a thin, even layer across the entire IHS surface with a plastic card or gloved finger. Either method works.

**Mounting the cooler:**
1. Lower the cooler straight down onto the CPU — do not slide it.
2. Thread in the mounting screws by hand first on all corners before tightening any.
3. Tighten in a cross pattern (X pattern), a few turns at a time each, to apply even pressure.
4. Tighten until snug — not torqued down hard. The paste will spread as it heats.

### 3.9 — Removing a CPU (AM5 / sTR5)

**AM5 (Ryzen 9950X) — Zero Insertion Force:**
1. There is a retention arm beside the socket (like Intel but on AMD side).
2. Lift the retention arm upward to release.
3. Open the CPU retention frame.
4. The CPU can now be lifted straight up with no force needed.
5. Handle the CPU by edges — do not touch the contact pads on the bottom.
6. Store it in an anti-static container with pins/pads protected.

**sTR5 (Threadripper 7960X) — Torx screws:**
1. The sTR5 socket has a large retention frame held by 3 Torx T20 screws arranged around the socket.
2. Loosen the three Torx screws (counterclockwise) — there is a specific sequence: start with screw labeled "3", then "2", then "1" (or follow markings on the retention frame).
3. After loosening all three, the retention frame opens. Lift the CPU straight up.
4. Threadripper CPUs are very large — handle by edges with two hands.

### 3.10 — Installing a CPU

**AM5 (9950X going into X870E in VAULT):**
1. Look at the AM5 socket. There is a small triangle marker on one corner of the socket frame.
2. Look at the 9950X CPU. There is a small triangle marker on one corner of the CPU substrate.
3. These triangles must align when you lower the CPU into the socket.
4. Drop the CPU in — zero insertion force means it simply falls into place with correct alignment. Do not push down.
5. If it doesn't drop in smoothly: remove and check alignment. Never force it.
6. Lower the retention frame and engage the arm. Tighten the retention arm.

**sTR5 (7960X going into TRX50 in Node 2):**
1. The sTR5 socket has a very large land grid array (LGA) with many contacts.
2. Look for the alignment notches on the CPU edges — two different edge types (one side has a notch, the other does not).
3. Look at the socket — it mirrors the CPU shape. The CPU only fits one way.
4. Lower the CPU into the socket. It should fall in with zero force. If it doesn't: check orientation.
5. Close the retention frame. Tighten the three Torx T20 screws in sequence: labeled order on the frame (typically 1, 2, 3).
6. Do not overtighten — follow the sequence and stop when the frame is flat.

---

## PART FOUR — LABELING SCHEME

Label everything you remove before setting it aside. Use tape and marker.

### VAULT NVMe drives (label before removing):

```
T700 4TB        → Label: "APPDATA"     (serial: 2423E8B78B09)
P310 1TB #1     → Label: "DOCKER"      (serial: 25064E23123B)
P310 1TB #2     → Label: "TRANSCODE"   (serial: 25074E225AF9)
P310 1TB #3     → Label: "VMS"         (serial: 25074E227551)
```

The label tells you which Unraid pool this drive belongs to. After the swap, Unraid will reassign by serial number automatically, but having the label prevents confusion if you need to manually identify them.

### Node 2 NVMe drives:

```
nvme0n1    → Label: "N2-SLOT0" (Ubuntu OS? — check: it has old Talos partitions)
nvme1n1    → Label: "N2-SLOT1" (Ubuntu OS? — check)
nvme2n1    → Label: "N2-SLOT2" (Ubuntu OS? — check)
nvme3n1    → Label: "N2-SLOT3-OS" *** THIS ONE HAS UBUNTU INSTALLED ***
```

The OS is on nvme3n1 (serial S7U5NJ0Y101657H). Label it clearly. All four travel with the TRX50 to Node 2.

### RAM grouping:

Keep the 4x Kingston RDIMM sticks together as "VAULT RAM → N2". They're going from VAULT TRX50 to Node 2 TRX50.
Keep the 4x Micron UDIMM sticks together as "N2 RAM → VAULT". They're going from Node 2 X870E to VAULT X870E.
Rubber-band or bag each set.

---

## PART FIVE — DETAILED STEP BY STEP

### PRE-WORK — Remote, Do This Before Opening Any Case

These steps can and should be done while everything is still running.

**A. Back up VAULT Unraid config (from DEV or any machine):**
```bash
python scripts/vault-ssh.py "tar czf /tmp/unraid-backup-$(date +%Y%m%d).tar.gz /boot/config"
```
Then download the backup:
```bash
# Or use Unraid UI: Tools → Flash Backup → Download
```

**B. Screenshot VAULT array assignments:**
- Open browser: http://192.168.1.203
- Go to Main tab — screenshot the HDD array disk assignments
- Go to Settings → Network Settings — screenshot the network config
- Note VAULT's current MAC: bond0 = `10:FF:E0:3E:8F:1E` (this will change after board swap)

**C. Confirm NVMe serials are correct (they are, from audit — but verify if you want):**
```bash
python scripts/vault-ssh.py "nvme list"
```
Expected output includes:
- CT4000T700SSD5 — serial 2423E8B78B09 (T700, appdata)
- CT1000P310SSD8 — serial 25064E23123B (P310, docker)
- CT1000P310SSD8 — serial 25074E225AF9 (P310, transcode)
- CT1000P310SSD8 — serial 25074E227551 (P310, vms)

**D. Confirm Node 2 netplan config:**
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225 "cat /etc/netplan/*.yaml"
```
Note the interface name (currently enp13s0) and IP (192.168.1.225). After board swap, the interface name may change.

---

### ROUND 1 — NODE 1 WORK

#### Step R1-1: Shut down Node 1

```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244
sudo shutdown now
```

Wait for machine to fully power off (fans stop). Then unplug power from wall. Wait 30 seconds.

#### Step R1-2: Open Node 1 chassis

Node 1 is in the Silverstone RM52 upper tray. Open the chassis side panel.

**Photograph everything before touching cables.** GPU positions, cable routing, all of it. You need this reference.

#### Step R1-3: Reseat Samsung 990 PRO

Locate the M.2 slots on the ROMED8-2T. There are two M.2 slots on the board.

1. Find the Samsung 990 PRO — it should already be installed in one of the slots.
2. Remove the retention screw (see Section 3.3).
3. Remove the drive. Inspect the connector end for any debris or damage.
4. Reinsert firmly — push until the connector is fully seated, then press the drive flat and reinstall the retention screw.
5. **Verify:** The drive should lie flat with the retention screw holding the tip end down.

If the drive is not present at all: this indicates it was never installed or fell out. Install it now from loose parts.

**Note which M.2 slot the 990 PRO is in.** You will need this information in BIOS.

#### Step R1-4: Install Hyper M.2 Gen5 Adapter

Pick any one of the three Hyper M.2 Gen5 adapters.

1. **Choose the PCIe slot.** You cannot use PCIE2 (shares lanes with M.2). Look at which slots currently have GPUs. Count the available free slots. Use PCIE3 or PCIE5 (or any slot that is NOT PCIE2).
2. Remove the corresponding rear bracket slot cover(s) from the case.
3. Install the Hyper M.2 adapter as described in Section 3.2. The adapter is a standard PCIe card — install it exactly like you would a GPU.
4. Secure the bracket to the case.

**Inline verification:** The adapter should sit flat in the slot. The bracket should be flush with the rear panel. No cards above or below should be physically contacted.

**If physical clearance is tight with the RTX 5070 Ti cards:** The Hyper M.2 adapter does not have a heatsink extending up — it is a flat PCB. It should fit in adjacent slots to the GPUs. If the slot is physically blocked by a GPU heatsink extending over it, find a slot with clearance.

#### Step R1-5: Install T700 Drives into the Adapter

Install all 4× Crucial T700 1TB drives into the Hyper M.2 adapter's 4 M.2 slots (4TB total).

1. Follow the NVMe installation procedure in Section 3.4 for each drive.
2. All 4 drives are identical — slot order doesn't matter.
3. Ensure all 4 drives are fully seated and screws are tight.

**Inline verification:** Look at all 4 drives from the side. Each should be lying flat (not angled up). Each retention screw should be seated.

#### Step R1-6: Assess RTX 3060 clearance

Look at the remaining PCIe slots after 4x RTX 5070 Ti and the Hyper M.2 adapter.

The RTX 3060 is a two-slot card. It needs a slot with at least two slot-widths of physical clearance above it (below it in the case, near the PSU) OR two slot widths of empty space.

**If there is a usable slot:** Proceed to install RTX 3060 (below).

**If all slots are physically occupied or blocked:** The RTX 3060 installation is deferred. Close up Node 1 and continue. Document which slots are occupied and why there was no room.

#### Step R1-7: Install RTX 3060 (if clearance allows)

Skip this step until you've removed the RTX 3060 from DEV (see Round 1 DEV work). Come back here after.

1. Install the RTX 3060 following Section 3.2.
2. Connect the PCIe power cable (single 8-pin).
3. Secure the bracket.

**Power budget check:** 4x RTX 5070 Ti at 250W limit = 1,000W. EPYC 7663 = 240W. RTX 3060 = ~170W. Misc = ~80W. Total ≈ 1,490W, within Corsair 1600W budget.

#### Step R1-8: Close Node 1 and boot to BIOS

Do NOT boot to OS yet. Boot to BIOS first to configure bifurcation.

Power on Node 1. Press **Delete** (or F2) immediately and repeatedly at the Gigabyte/ASRock splash screen.

---

#### BIOS — Node 1 (ROMED8-2T)

**A. PCIe Bifurcation for Hyper M.2 Adapter (REQUIRED — without this, only 1 of 4 T700s will appear):**

Navigate to:
```
Advanced → Chipset Configuration → North Bridge → IIO Configuration
```

This menu lists "IOU" entries (I/O Units) that correspond to PCIe slots. Find the IOU for the slot where you installed the Hyper M.2 adapter.

You may need to match by slot number. The adapter is in PCIE3 or PCIE5 — find the corresponding IOU entry.

Change it from: `x16` (or `Auto`)
Change it to: **`x4 x4 x4 x4`**

This tells the CPU to address the slot as four x4 links, which matches the adapter's 4 M.2 ports.

**If unsure which IOU maps to which slot:** Set all free IOUs to `x4 x4 x4 x4`. This cannot hurt anything and you can tune it later.

**B. Samsung 990 PRO M.2 slot:**

Navigate to:
```
Advanced → PCIe/PCI Subsystem Settings
```
Look for M.2 configuration. If the 990 PRO slot is disabled or sharing lanes with PCIE2, enable it explicitly. The goal: the 990 PRO slot should be active and NOT sharing bandwidth with any GPU slot.

If there's an option labeled "M.2 slot enable" or "disable PCIE2 lane sharing" — enable/take it.

**C. Boot order:**

Verify the Crucial P3 Plus (OS NVMe) is first in boot order. This is the OS drive. It should already be set correctly, but confirm.

**D. Save and exit (F10 or navigate to Save & Exit → Save Changes and Reboot).**

---

#### Step R1-9: Verify Node 1

After boot, SSH in:
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244
```

**Check storage:**
```bash
lsblk -d -o NAME,SIZE,MODEL,SERIAL
```

Expected:
```
NAME    SIZE  MODEL          SERIAL
nvme0n1 3.6T  CT4000P3SSD8   2422E8B57188     ← Crucial P3 Plus (OS) ✓
nvme1n1 3.6T  MZ-V9P4T0      [some serial]    ← Samsung 990 PRO ✓
nvme2n1 3.6T  CT4000T700SSD5 [serial]         ← T700 #1 ✓
nvme3n1 3.6T  CT4000T700SSD5 [serial]         ← T700 #2 ✓
nvme4n1 3.6T  CT4000T700SSD5 [serial]         ← T700 #3 ✓
nvme5n1 3.6T  CT4000T700SSD5 [serial]         ← T700 #4 ✓
```

**If Samsung 990 PRO is missing:** BIOS M.2 slot issue. Reboot into BIOS → check the M.2 slot enable/lane sharing setting. Disable PCIE2 lane sharing, enable the M.2 slot explicitly.

**If T700s are missing (all 4 missing):** PCIe bifurcation not set. Reboot into BIOS → IIO Configuration → set `x4 x4 x4 x4` on the adapter's slot.

**If only 1 T700 is visible:** Bifurcation is partially set. Reboot into BIOS → verify you set the right IOU, set to `x4 x4 x4 x4`.

**Check GPUs:**
```bash
nvidia-smi
```

Expected: 4x RTX 5070 Ti listed. If RTX 3060 was installed, 5x total.

**Node 1 is complete when all drives and GPUs are visible.**

---

### ROUND 1 — DEV WORK

DEV work can overlap with Node 1 boot (do DEV while Node 1 boots to BIOS).

#### Step R1-DEV-1: Shut down DEV

Save everything open in Windows. **Shut down Windows completely** (Start → Shut down, not sleep/hibernate).

Unplug DEV power from wall. Open case. Ground yourself.

#### Step R1-DEV-2: Remove RTX 3060

1. Disconnect the 8-pin PCIe power cable.
2. Press the PCIe slot release latch.
3. Lift out the RTX 3060. See Section 3.1 for detailed procedure.
4. Set aside on anti-static surface — this card goes to Node 1 (go install it there after this step if Node 1 is still apart).

#### Step R1-DEV-3: Install RX 5700 XT

1. Remove the appropriate rear bracket slot cover(s) from DEV case.
2. Install the RX 5700 XT in the same x16 slot the 3060 vacated. See Section 3.2.
3. Connect PCIe power cables — the RX 5700 XT uses two 8-pin PCIe connectors.
4. Secure bracket.

#### Step R1-DEV-4: Install Intel X540-T2 NIC

1. Find an available PCIe x8 or x16 slot in DEV. The X540-T2 has an x8 PCIe connector.
2. Remove the bracket cover for that slot.
3. Install the card — it installs like any PCIe card, no power connector needed.
4. Secure bracket.

#### Step R1-DEV-5: Close DEV and power on

Plug power back in. Power on DEV. Let Windows boot.

Windows will auto-detect the X540-T2 and install drivers. This may take a few minutes.

**After boot:**
- Device Manager → Network Adapters → Intel X540 should appear
- Connect DEV ethernet cable to **USW Pro XG 10 PoE** switch (the 5GbE switch)
- Test: from WSL2 terminal: `iperf3 -c 192.168.1.244` — expect 9+ Gbps if Node 1 is also on the 5GbE switch

**If Intel X540 driver not found:** Windows should auto-download. If no internet, driver package can be downloaded from Intel's site. Part number: ixgbe or ixgben driver package.

---

### ROUND 2 — THE BIG SWAP

**Do not start Round 2 until Round 1 is complete and verified.**

Checklist before starting:
- [ ] Node 1 verified: 990 PRO + 4x T700 visible, correct GPU count
- [ ] DEV on 5GbE, working
- [ ] VAULT config backed up
- [ ] NVMe serials and labels known (see labeling scheme above)
- [ ] Photos taken of VAULT cable routing
- [ ] Photos taken of Node 2 cable routing

#### Step R2-1: Shut down Node 2

```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225
docker stop $(docker ps -q)
sudo shutdown now
```

Wait for full power off.

#### Step R2-2: Shut down VAULT

Via SSH:
```bash
python scripts/vault-ssh.py "docker stop \$(docker ps -q) && poweroff"
```

Or via Unraid UI: Main → Stop Array → Power Off.

**Wait for both machines to fully power off before opening either case.**

---

#### Step R2-3: VAULT disassembly

Open VAULT chassis. **Photograph all cable connections: HBA cables, NVMe slot positions, GPU slot, front panel headers.**

Remove in this order:

**A. Arc A380 GPU:**
1. Disconnect PCIe power (small 6-pin or 8-pin connector).
2. Press PCIe slot release latch.
3. Remove card. Set aside labeled "ARC A380 — VAULT GPU".

**B. LSI SAS3224 HBA:**
1. **Only disconnect from the motherboard side** — leave the SATA/SAS cables routed through the chassis. Those cables connect to the HDDs and you don't want to lose track of which goes where.
2. Press the PCIe slot release latch for the HBA slot.
3. Remove the HBA. The cables will be hanging from it on the drive side. Set the HBA down inside the chassis where it can rest with the cables attached.

**C. 4x Crucial NVMe drives — label before removing each one:**
1. Remove T700 (3.6TB drive) — label it **"APPDATA"**
2. Remove P310 from docker pool — label it **"DOCKER"**
3. Remove P310 from transcode pool — label it **"TRANSCODE"**
4. Remove P310 from vms pool — label it **"VMS"**

If you're not sure which is which from the slot: they are in M.2 slots and the serials are on the drive labels. The T700 is the larger capacity drive (3.6TB vs the P310's ~900GB). Check the printed label on the drive surface.

**D. Kingston DDR5 ECC RDIMM RAM (4 sticks):**
1. Press both retention clips on each DIMM slot outward.
2. Remove all 4 sticks. Bundle them together with a rubber band. Label group: "KINGSTON-ECC-RDIMM → N2".

**E. CPU cooler:**
See Section 3.7. Loosen in cross pattern, twist to break paste bond, lift off.

**F. TRX50 AERO D + 7960X:**
1. Disconnect all remaining board connections: ATX 24-pin, CPU 8-pin power connectors (there are two — disconnect both), front panel headers, USB headers, fan headers, any SATA connectors.
2. Remove the board mounting screws (typically 9 for ATX/E-ATX). Use the correct Phillips head.
3. Lift the board out of the chassis. **The 7960X stays in the socket — do not remove it unless the cooler hasn't already come off.** If the cooler is still attached, remove it before lifting the board (it would be too heavy/awkward otherwise).
4. Set the TRX50 board (with 7960X installed) on a non-static surface. Keep it flat.

**Leave the HDD cables routed in the chassis. You will reconnect the LSI HBA to a new board using these same cables.**

---

#### Step R2-4: Node 2 disassembly

Open Node 2 chassis (Silverstone RM52 middle tray). **Photograph all cable connections.**

Remove in this order:

**A. RTX 5090:**
1. Disconnect 16-pin 12VHPWR power cable.
2. Press PCIe slot release latch.
3. Remove card carefully — it's heavy and large. Use both hands. Set aside labeled "RTX 5090 — STAYS IN RM52".

**B. RTX 4090:**
1. Disconnect PCIe power (likely adapter cable or multi-8-pin).
2. Press PCIe slot release latch.
3. Remove card. Set aside labeled "RTX 4090 — STAYS IN RM52".

Both GPUs stay physically in the RM52 chassis — they get reinstalled on the TRX50 board.

**C. Samsung 990 EVO Plus NVMe (4 drives):**
1. Label each as you remove: "N2-SLOT0", "N2-SLOT1", "N2-SLOT2", "N2-SLOT3-OS" (OS is the one with /boot/efi, which is nvme3n1 serial S7U5NJ0Y101657H).
2. Remove all 4 following Section 3.3.
3. Keep them together as a set.

**D. Micron DDR5 UDIMM RAM (4 sticks):**
1. Remove all 4 sticks.
2. Bundle and label: "MICRON-UDIMM → VAULT".

**E. CPU cooler:**
Remove following Section 3.7. The 9950X will likely stay in socket after cooler removal.

**F. X870E CREATOR + 9950X:**
1. Disconnect all board connections: ATX 24-pin, CPU 8-pin power, front panel, USB, fan headers.
2. Remove board mounting screws.
3. Lift the X870E board out (with 9950X still in socket).
4. Set aside on non-static surface.

---

#### Step R2-5: Build Node 2 with TRX50

Install TRX50 AERO D (from VAULT) into RM52 middle tray chassis.

**Build order — follow exactly:**

**1. Mount TRX50 board in RM52 chassis:**
- TRX50 is E-ATX form factor — it's slightly wider than standard ATX
- Verify the RM52 tray has the correct standoff positions for E-ATX
- Install standoffs if needed — match the board's mounting holes
- Lower board into chassis, thread all mounting screws, snug down in star pattern

**2. Install 7960X CPU (it should already be in the TRX50 socket from VAULT):**
- If the CPU is NOT already in the socket (fell out during transport): see Section 3.10 for sTR5 installation
- If it IS in the socket: nothing to do — it stayed in place

**3. Apply thermal paste and mount CPU cooler:**
- Clean any old paste off the 7960X IHS and cooler base (isopropyl alcohol)
- Apply pea-sized dot of paste to 7960X IHS (the IHS is large — use a slightly larger amount or a thin line)
- Mount cooler following Section 3.8
- **Verify cooler bracket is sTR5 compatible** — do not use an AM4 or older Threadripper bracket. The 7960X uses sTR5 mounting holes (different spacing than TR4).
- Connect CPU fan power cable to CPU_FAN header

**4. Install Kingston DDR5 ECC RDIMM in TRX50:**

TRX50 AERO D DIMM slot positions:
```
Closest to CPU edge of board:
[DDR5_A1] [DDR5_B1] [DDR5_C1] [DDR5_D1]
```
- Install all 4 Kingston sticks (from VAULT)
- Open all clips, align stick (check notch), press firmly until both clips click
- **Verify:** All 4 clips are in the fully closed/vertical position on all sticks

**5. Install RTX 5090 in PCIEX16_1 (primary GPU slot — top slot):**
- Follow Section 3.2
- Connect 16-pin 12VHPWR power cable — push firmly until it seats (this connector requires real force)
- Secure bracket

**6. Install RTX 4090 in PCIEX16_2 (secondary slot):**
- Follow Section 3.2
- Connect PCIe power cable(s)
- Secure bracket

**7. Install Samsung 990 EVO Plus NVMe drives (Node 2's Ubuntu drives):**
- Install all 4 into available TRX50 M.2 slots
- Follow Section 3.4 for each drive
- The OS is on "N2-SLOT3-OS" — it doesn't matter which physical slot it goes into, but install it first so you know where it is
- All 4 drives are the Ubuntu OS drives — they all travel together

**8. Power connections — CRITICAL:**

Required connections for 7960X:
- ATX 24-pin power
- **2x 8-pin EPS CPU power** — the 7960X REQUIRES BOTH. Find both CPU power cables from the MSI 1600W PSU. They are labeled "CPU" and are the 8-pin square connectors (not the PCIe 8-pin connectors). The TRX50 has two 8-pin CPU headers.
- PCIe 16-pin power for RTX 5090
- PCIe power for RTX 4090

**If you only find one 8-pin CPU cable from the PSU:** Check if the PSU has a CPU cable with a splitter or a second coiled cable. The MSI 1600W definitely has two separate EPS cables — find the second one.

**9. Front panel, fans, USB:**
- Front panel header: power button, reset, HDD LED, power LED
- CPU fan header(s)
- Chassis fan headers
- Front panel USB headers

**10. JetKVM ATX power cable:**
The JetKVM at 192.168.1.165 needs to connect to Node 2's ATX power button header to be able to power the machine on/off remotely. This cable was previously on the X870E. Move it to the TRX50 ATX power header.

**Node 2 is built. Do NOT power on yet.**

---

#### Step R2-6: Build VAULT with X870E

Install X870E CREATOR WIFI (from Node 2) into VAULT chassis.

**Build order:**

**1. Mount X870E board in VAULT chassis:**
- ATX form factor — standard ATX standoffs
- Install standoffs if needed, then mount board
- Thread all mounting screws, snug down in star pattern

**2. Install 9950X CPU:**
- If CPU is still in the X870E socket: it stays there
- If CPU fell out: see Section 3.10 for AM5 installation
- Align the triangle marker on CPU with the triangle on the socket corner
- Zero insertion force — it drops in

**3. Apply thermal paste and mount CPU cooler:**
- Clean old paste from 9950X IHS and cooler base
- Apply pea-sized dot to 9950X IHS
- Mount cooler following Section 3.8
- **Verify cooler bracket is AM5 compatible** — AM5 uses a different mounting pattern than AM4. The bracket clips to the AM5 socket retention frame.
- Connect CPU fan to CPU_FAN header

**4. Install Micron DDR5 UDIMM in X870E:**

X870E CREATOR WIFI DIMM slot positions:
```
[A2] [A1] CPU [B1] [B2]
```
(Slots A1/B1 nearest CPU are the primary channels)
- Install all 4 Micron sticks (from Node 2)
- For 4-stick population: fill all 4 slots
- Open clips, check notch alignment, press until clips click
- Verify all clips are locked

**5. Install Arc A380 GPU:**
- Install in PCIEX16_1 (primary slot)
- Connect PCIe power if required (Arc A380 is low power — may not need a power connector, or uses a single 6-pin)
- Secure bracket

**6. Install LSI SAS3224 HBA:**
- The HBA was set aside inside the VAULT chassis with its SAS/SATA cables attached
- Install the HBA in a PCIe x8 or x16 slot (the HBA is x8)
- Reconnect the SAS/SATA cables to the HBA side (they were left routed through the chassis)
- The cable ends that connect to HDDs do not need to move — only the HBA board side connectors
- Secure bracket

**7. Install Crucial NVMe drives:**

Install in any available M.2 slots — order doesn't matter for Unraid (it reassigns by serial):
- APPDATA (T700 4TB) → any M.2 slot
- DOCKER (P310 1TB) → any M.2 slot
- TRANSCODE (P310 1TB) → any M.2 slot
- VMS (P310 1TB) → any M.2 slot

Follow Section 3.4 for each drive.

**8. Power connections:**
- ATX 24-pin
- **1x 8-pin EPS CPU power** (9950X is 170W — one connector sufficient)
- PCIe power for Arc A380 (if required by card)

**9. Front panel, fans, USB:**
- Power button, reset, LEDs
- CPU fan
- Chassis fans

**10. Insert Unraid boot USB:**
- SanDisk Cruzer Glide (the Unraid OS USB stick — currently in the old TRX50 setup, now needs to go here)
- Insert into any USB port. Preferably a rear USB port for stability (less likely to be bumped).

**VAULT is built.**

---

### ROUND 3 — BOOT AND RECOVERY

#### Step R3-1: Boot VAULT first

Power on VAULT.

Monitor via JetKVM at **192.168.1.80** if you need console access.

**Unraid should boot from the USB stick.** The splash screen will show "Unraid" and begin the boot process.

**VAULT will have a new MAC address.** The old IP was assigned via DHCP reservation tied to the old TRX50 MAC. The X870E has different MACs — VAULT will get a random DHCP IP on first boot.

**Fix network immediately after boot:**

Option A (Unraid UI — but you need to find the random IP first):
- Check your router (UniFi Dream Machine Pro) for a new DHCP lease to find the temporary IP
- Navigate to http://[temporary-ip] in a browser
- Settings → Network Settings → Change IPv4 assignment to Static
- Set: IP = 192.168.1.203, Netmask = 255.255.255.0, Gateway = 192.168.1.1, DNS = 192.168.1.1
- Apply → reconnect

Option B (JetKVM console — no network needed):
- Connect to JetKVM at 192.168.1.80 from your browser
- Access VAULT's console through the KVM interface
- Log in as root
- You can set the static IP from Unraid command line or navigate to the Unraid web console on localhost

**After network is set:**
```bash
python scripts/vault-ssh.py "ip addr show"
```
Should show 192.168.1.203 on the interface.

**Start array and verify pools:**
1. Open Unraid UI at http://192.168.1.203
2. Main → Start Array
3. All 9 data HDDs should mount automatically (they didn't move — same drives, same ports)
4. Check Pools section → appdata, docker, vms, transcode pools
5. If any pool shows the wrong device or is missing: click on the pool → reassign by serial number using the table:

| Pool | Drive | Serial |
|------|-------|--------|
| appdata | Crucial T700 4TB | 2423E8B78B09 |
| docker | Crucial P310 1TB | 25064E23123B |
| transcode | Crucial P310 1TB | 25074E225AF9 |
| vms | Crucial P310 1TB | 25074E227551 |

6. Settings → Docker → Start (or verify auto-start is on)

**Verify services:**
```
http://192.168.1.203:8989   ← Sonarr
http://192.168.1.203:7878   ← Radarr
http://192.168.1.203:9090   ← Prometheus
http://192.168.1.203:3000   ← Grafana
http://192.168.1.203:32400  ← Plex
```

---

#### Step R3-2: VAULT BIOS configuration (EXPO)

Reboot VAULT via Unraid UI → System → Reboot. Press **Delete** at POST.

**EXPO memory speed:**
```
ASUS BIOS → Extreme Tweaker tab (or AI Tweaker — same tab, same name on some ASUS versions)
  → XMP/EXPO: Enable
  → Select profile: the Micron DDR5 rated speed profile
```

Check the sticker on the Micron sticks for rated speed. The sticks are Micron CP32G60C40U5B.M8B3 — rated at 5600 MT/s (they were running at 3600 MT/s before because EXPO was not enabled).

Also verify:
- Boot order: USB (SanDisk Cruzer) is first
- PCIe: LSI HBA slot is at x8 (not limited to x4)

Save and exit. Verify Unraid boots, array starts normally.

**Verify EXPO worked:**
```bash
python scripts/vault-ssh.py "dmidecode -t memory | grep 'Configured Memory Speed'"
```
Should show 5600 MT/s (or the profile speed you selected).

---

#### Step R3-3: Boot Node 2 (TRX50)

Power on Node 2.

Monitor via JetKVM at **192.168.1.165** if you need console access.

Ubuntu should boot from the Samsung 990 EVO Plus drives. GRUB handles hardware changes gracefully.

**If SSH works normally:**
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225

nvidia-smi        # RTX 5090 (32GB) + RTX 4090 (24GB) — both should appear
free -h           # 128 GB DDR5 ECC RDIMM
lsblk             # 4x Samsung 990 EVO Plus drives
docker ps         # check services
```

**If SSH fails — network interface name changed:**

Use JetKVM console at 192.168.1.165:
```bash
ip link
# Note the new interface name (might be enp7s0 or similar instead of enp13s0)

sudo nano /etc/netplan/50-cloud-init.yaml
```

The file will look something like:
```yaml
network:
  ethernets:
    enp13s0:            ← change this to the new name from ip link
      dhcp4: no
      addresses: [192.168.1.225/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [192.168.1.1]
```

Change `enp13s0` to whatever name `ip link` showed. Save the file (Ctrl+X, Y, Enter in nano).

```bash
sudo netplan apply
```

Now SSH should work.

**If Ubuntu won't boot at all:**

Enter UEFI setup (Delete at POST):
- Check boot order: look for an entry for the Samsung 990 EVO Plus (it may appear as "Ubuntu" or as the NVMe device)
- Set it first
- Save and reboot

If Ubuntu entry is not listed at all:
- Go to UEFI Shell
- At the `Shell>` prompt:
  ```
  fs0:\EFI\ubuntu\grubx64.efi
  ```
  (Try fs0, fs1, fs2 if fs0 doesn't work — one of them has the Ubuntu EFI partition)
- Ubuntu will boot. Then from running Ubuntu:
  ```bash
  sudo grub-install /dev/[the NVMe OS drive]
  ```
  This registers Ubuntu with the new UEFI firmware.

**Restart services if needed:**
```bash
cd ~/services && docker compose up -d
```

---

#### Step R3-4: Node 2 BIOS configuration (EXPO)

Reboot Node 2. Press **Delete** at POST.

**EXPO memory speed:**
```
Gigabyte BIOS → MIT tab (Memory Intelligence Tweaker)
  → Advanced Memory Settings
  → XMP/EXPO Profile: EXPO I → 5600 MT/s
```

If MIT tab is not visible in the main tabs: try **Settings → AMD CBS → Memory → EXPO**.

Save and reboot.

**Verify EXPO worked:**
```bash
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225
sudo dmidecode -t memory | grep "Configured Memory Speed"
```
Should show 5600 MT/s.

**If instability after enabling EXPO (system crashes on boot or during POST):** Reboot into BIOS, drop the profile to 5200 MT/s and retry. If still unstable, try 4800 MT/s.

**While in BIOS — also set fan curves:**
- Hardware Monitor → fan speed settings
- Set fans to ramp above 70°C CPU temperature
- The 7960X is a hot CPU (350W TDP) — don't leave fan curves at "auto" without checking

---

### ROUND 4 — VERIFICATION

Run from DEV (WSL2) or any machine with SSH access:

```bash
# 5GbE throughput — install iperf3 if needed: sudo apt install iperf3
# On each target, start iperf3 server first if needed: iperf3 -s -D

iperf3 -c 192.168.1.244   # Node 1 — expect 9+ Gbps
iperf3 -c 192.168.1.225   # Node 2 — expect 9+ Gbps
iperf3 -c 192.168.1.203   # VAULT  — expect 9+ Gbps

# NFS mounts still accessible
ls /mnt/vault/models
ls /mnt/vault/data

# Node 1 full storage check
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "lsblk && nvidia-smi"
# Expect:
#   Crucial P3 Plus ~3.6TB (OS)
#   Samsung 990 PRO ~3.6TB
#   4x Crucial T700 ~3.6TB each
#   4x RTX 5070 Ti + 1x RTX 3060 (5 GPUs total, if 3060 was installed)

# Node 2 GPU + RAM
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225 "nvidia-smi && free -h && sudo dmidecode -t memory | grep 'Configured Memory Speed'"
# Expect:
#   RTX 5090 (32 GB) + RTX 4090 (24 GB)
#   ~128 GB RAM
#   5600 MT/s

# Grafana — check all dashboards have data
# http://192.168.1.203:3000 → Athanor Overview dashboard
# All nodes should be reporting metrics (node_exporter, dcgm-exporter)
```

---

## PART SIX — CRITICAL WARNINGS

These are the things that will waste your time if you forget them. Review these before starting each phase.

### WARNING 1 — DO NOT USE PCIE2 FOR THE HYPER M.2 ADAPTER (Node 1)
PCIE2 on the ROMED8-2T shares PCIe lanes with the M.2 slot. Putting the Hyper M.2 adapter in PCIE2 creates a double conflict. Use PCIE3, PCIE5, or any other slot. The adapter will appear to work but the 990 PRO will disappear, or neither will work correctly.

### WARNING 2 — TRX50 REQUIRES 2x 8-PIN EPS CPU CONNECTORS
The 7960X Threadripper is 350W TDP. The TRX50 has two 8-pin EPS headers near the CPU socket. You must connect both. The MSI 1600W PSU has two CPU cables — find both before closing the case. A missing EPS connector may cause boot failure, throttling, or unexpected shutdowns under load.

### WARNING 3 — TRX50 ACCEPTS ONLY DDR5 RDIMM
The Gigabyte TRX50 AERO D does not support UDIMMs. Do not install the Micron UDIMM sticks in the TRX50. They will not POST. Only the Kingston KF556R28RBE2-32 ECC RDIMM sticks are compatible. If you accidentally install UDIMMs and the system won't POST — remove them, install the Kingston RDIMMs.

### WARNING 4 — HANDLE COMPONENTS BY EDGES ONLY
- Processors: never touch the contact pads (bottom side) or the land grid array pins
- RAM: hold by the top edge between memory chips
- GPUs: hold by top edge and bracket — not fans, not power connectors
- NVMe: hold by edges — the gold connector fingers are sensitive
- Wear an anti-static wrist strap connected to a grounded metal chassis

### WARNING 5 — GRUB AND UNRAID BOOT FROM DIFFERENT DRIVES
- Node 2 Ubuntu boots from NVMe (Samsung 990 EVO Plus). If the UEFI boot order changes with new board, set it to NVMe first.
- VAULT Unraid boots from USB (SanDisk Cruzer). If Unraid doesn't boot, first check that the USB is plugged in, then check boot order.

### WARNING 6 — PCIe BIFURCATION IS REQUIRED FOR T700s TO APPEAR
Without setting x4x4x4x4 bifurcation in BIOS for the Hyper M.2 adapter slot, the OS will only see 1 of the 4 T700 drives. This is a BIOS-only setting — nothing in the OS can fix it. If T700s are missing after boot, reboot to BIOS.

### WARNING 7 — VAULT IP WILL CHANGE AFTER BOARD SWAP
VAULT's IP was assigned by DHCP reservation tied to the old TRX50 MAC. The X870E has different MACs. After boot, VAULT will have a random IP. Use JetKVM (.80) to access the console and set a static IP. This is expected and normal.

---

## PART SEVEN — QUICK REFERENCE TROUBLESHOOTING

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Samsung 990 PRO not visible in OS | BIOS M.2 slot disabled / lane sharing with PCIE2 | Reboot BIOS → PCIe/PCI settings → enable M.2 slot, disable lane sharing |
| Only 1 T700 visible (not 4) | PCIe bifurcation not set | Reboot BIOS → IIO Config → x4x4x4x4 for adapter slot |
| All T700s missing | Bifurcation not set OR adapter not seated | Check BIOS, also reseat the Hyper M.2 adapter |
| Node 2 won't POST (TRX50) | Wrong RAM type OR missing EPS cable | Check: only Kingston RDIMM in slots, both 8-pin EPS connected |
| Node 2 no boot after swap | Boot order wrong | UEFI → set Samsung 990 EVO Plus as first boot device |
| Node 2 boots but SSH fails | NIC interface name changed | JetKVM (.165) → ip link → fix netplan |
| VAULT random IP after boot | New board = new MAC, DHCP gives unknown IP | JetKVM (.80) → Unraid UI → Settings → Network → set static 192.168.1.203 |
| VAULT won't boot at all | USB not found OR boot order wrong | Verify SanDisk Cruzer USB is inserted → UEFI boot order → USB first |
| VAULT NVMe pool wrong device | Device paths shifted with new board | Unraid UI → Main → Pools → reassign by serial (see table above) |
| EXPO causes instability | Memory speed too aggressive | BIOS → drop from 5600 to 5200 MT/s |
| Node 2 RAM showing 4800 MT/s not 5600 | EXPO not enabled | TRX50 BIOS → MIT → EXPO I → 5600 MT/s |
| VAULT RAM showing 3600 MT/s | EXPO not enabled on X870E | ASUS BIOS → Extreme Tweaker → EXPO Enable |
| JetKVM can't power on Node 2 | ATX power cable not moved to TRX50 | Physical check: reconnect JetKVM ATX cable to TRX50 ATX power header |

---

## PART EIGHT — END STATE

When the session is complete, verify the following final state:

| System | CPU | Board | RAM | GPUs | NVMe |
|--------|-----|-------|-----|------|------|
| Node 1 | EPYC 7663 | ROMED8-2T | 224 GB DDR4 ECC | 4x RTX 5070 Ti + RTX 3060 | P3 Plus (OS) + 990 PRO + 4x T700 (16TB) |
| Node 2 | TR 7960X | TRX50 AERO D | 128 GB DDR5 ECC | RTX 5090 + RTX 4090 | 4x 990 EVO Plus (Ubuntu) |
| VAULT | Ryzen 9950X | X870E CREATOR | 128 GB DDR5 | Arc A380 | T700+3xP310 (Unraid pools) |
| DEV | i7-13700K | Z690 AORUS ULTRA | 64 GB DDR5 | RX 5700 XT | P3 Plus + P310 + 970 EVO |

**All servers on 5GbE (USW Pro XG 10 PoE) at 9+ Gbps.**

---

## PART NINE — SERIAL NUMBERS AND MAC ADDRESSES

Keep this section as reference for reassignment tasks.

### VAULT NVMe Drive Serials

| Drive Model | Serial | Unraid Pool |
|-------------|--------|-------------|
| Crucial T700 4TB | 2423E8B78B09 | appdata |
| Crucial P310 1TB | 25064E23123B | docker |
| Crucial P310 1TB | 25074E225AF9 | transcode |
| Crucial P310 1TB | 25074E227551 | vms |

### Node 2 NVMe Serials (Ubuntu OS drives)

| Device (old) | Serial | Notes |
|--------------|--------|-------|
| nvme0n1 | S7U5NJ0Y101678V | Old Talos partitions — not OS |
| nvme1n1 | S7U5NJ0Y101944A | Old Talos partitions — not OS |
| nvme2n1 | S7U5NJ0Y101756B | Old Talos partitions — not OS |
| nvme3n1 | S7U5NJ0Y101657H | **Ubuntu OS is here** |

### Network Addresses

| Machine | IP | Notes |
|---------|-----|-------|
| Node 1 | 192.168.1.244 (+ .246) | Static via netplan |
| Node 2 | 192.168.1.225 | Static via netplan |
| VAULT | 192.168.1.203 | DHCP reservation (old MAC) → set static after swap |
| DEV | 192.168.1.215 | WiFi |
| JetKVM (Node 2) | 192.168.1.165 | KVM access |
| JetKVM (VAULT) | 192.168.1.80 | KVM access |
| Node 1 BMC | 192.168.1.216 | IPMI, admin/admin |

---

## PART TEN — SSH AND ACCESS COMMANDS

Copy these onto your phone or print this page specifically.

```bash
# Node 1 SSH
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244

# Node 2 SSH
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225

# VAULT SSH (use the Python wrapper — native SSH hangs)
python scripts/vault-ssh.py "your command here"

# Quick GPU check
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "nvidia-smi"
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.225 "nvidia-smi"

# Quick storage check
ssh -i ~/.ssh/athanor_mgmt athanor@192.168.1.244 "lsblk -d -o NAME,SIZE,MODEL"

# Fix VAULT static IP (run on VAULT via JetKVM console)
# Navigate to: Unraid UI → Settings → Network Settings → Static → 192.168.1.203

# Fix Node 2 network interface name (run locally via JetKVM .165 if SSH fails)
ip link                                     # find new interface name
sudo nano /etc/netplan/50-cloud-init.yaml   # change interface name in file
sudo netplan apply                          # apply

# Restart all Node 2 services
cd ~/services && docker compose up -d

# Check VAULT services via SSH
python scripts/vault-ssh.py "docker ps"
```

---

*Field manual generated 2026-02-20. Based on audits completed 2026-02-14.*
*All hardware specs verified from audits — not assumed from memory.*
