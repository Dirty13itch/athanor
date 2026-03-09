# MSI GPU RGB LED Control Protocol Research

**Date:** 2026-03-08
**Target Hardware:** MSI RTX 5070 Ti (subsystem 1462:5310, PCI device 10de:2C05)
**USB HID Device:** VID:PID 0db0:c9eb, 64-byte interrupt IN/OUT endpoints, no report ID

---

## Context

The MSI RTX 5070 Ti Gaming Trio (subsystem 1462:5310) exposes a USB HID device at
VID 0x0DB0 / PID 0xC9EB with 64-byte interrupt IN/OUT endpoints and no report ID.
Attempts to communicate with it (command 0x50 returns 00FE, command 0x52 gets no
response) have been unsuccessful. The question: is there a documented USB HID
protocol for MSI GPU RGB control, and what are the alternatives?

---

## Key Findings

### Finding 1: MSI GPU RGB Uses I2C at Address 0x68, Not USB HID

OpenRGB's `MSIGPUv2Controller` is the authoritative open-source implementation for
MSI GPU RGB control. It uses **I2C/SMBus at address 0x68** exclusively -- not USB HID.
The controller communicates with an ITE9 chip on the GPU board via the NVIDIA GPU's
I2C bus (port_id == 1).

**Protocol summary (from OpenRGB source):**
- I2C address: `0x68`
- Register read: `i2c_smbus_read_byte_data(dev, reg)`
- Register write: `i2c_smbus_write_byte_data(dev, reg, val)` with 20ms delay
- Block write: `i2c_smbus_write_i2c_block_data(dev, reg, len, val)` with 20ms delay
- Mode register: `0x22`
- Color registers: `0x30` (R), `0x31` (G), `0x32` (B) for zone 1
- Color block bases: `0x27`, `0x28`, `0x29` (three color blocks, BGR byte order)
- Brightness: `0x36` (range 1-5, multiplied by 20)
- Speed: `0x38` (0x00=min, 0x01=mid, 0x02=max)
- Save/commit: `0x3F` (write 0x00)
- Direction: `0x46` (0x00=right, 0x02=left)
- 18+ lighting modes, each with unique hex ID (0x01 through 0x1F)

**Source:** `Controllers/MSIGPUController/MSIGPUv2Controller/` in
[OpenRGB](https://github.com/CalcProgrammer1/OpenRGB)

### Finding 2: RTX 5070 Ti IS Supported in OpenRGB (But Your Subsystem ID Is Missing)

OpenRGB's `MSIGPUv2ControllerDetect.cpp` already includes RTX 5070 Ti entries:

| Constant | Value | Model |
|----------|-------|-------|
| `NVIDIA_RTX5070TI_DEV` | `0x2C05` | NVIDIA RTX 5070 Ti (GB205) |
| `MSI_RTX5070TI_GAMING_TRIO_SUB_DEV` | `0x5315` | MSI Gaming Trio OC Plus |
| `MSI_RTX5070TI_VANGUARD_SOC_SUB_DEV` | `0x5314` | MSI Vanguard SOC |

**Your card's subsystem ID is `0x5310`**, which is NOT in OpenRGB's detection list.
The linux-hardware.org database confirms `pci:10de-2c05-1462-5310` is a valid MSI
RTX 5070 Ti variant. This is a simple device ID omission -- the protocol at 0x68
should be identical since all MSI RTX 50 series GPUs use the same ITE9 controller.

### Finding 3: The USB HID Device 0db0:c9eb Is NOT the RGB Controller

VID `0x0DB0` is MSI's USB HID vendor ID, used across their product line:
- Motherboard Mystic Light: `0x0DB0:0x0076` (feature reports, report ID 0x51, 761-byte buffer)
- Motherboard Dynamic Dashboard: `0x0DB0:0x84DF`
- Various other motherboard peripherals: `0x0DB0:0x0B58`, etc.

The PID `0xC9EB` does not appear in any database, forum post, or source code
searched. It is likely **a different MSI on-card microcontroller** -- possibly for
fan control, thermal monitoring, or an internal dashboard/status function. It is
**not** the RGB LED controller.

### Finding 4: SignalRGB Confirms Per-LED I2C Protocol for MSI 5000 Series

SignalRGB's changelog (v2.5.6, July 2025) states: "Improved MSI 4000/5000 Series
initialization, and added a legacy single color control option for those who have
performance issues with the new per-led protocol."

The NVIDIA open-gpu-kernel-modules issue #1026 documents that RTX 5080 has 44 LEDs
and RTX 5070 Ti has 41 LEDs, controlled via 7-byte I2C block transfers per LED at up
to 60 Hz. On Linux, continuous I2C access causes severe performance degradation
(120+ FPS drops to ~10 FPS) due to a driver bug in the open kernel modules. This
issue does not occur on Windows.

### Finding 5: The I2C Path Should Work on Blackwell (GB205)

Despite the initial assumption that Blackwell doesn't expose I2C adapter 1, the
evidence indicates otherwise:
- OpenRGB's detection code explicitly requires `port_id == 1` for NVIDIA GPUs
- RTX 5070 Ti and 5080 are listed in OpenRGB's detection code (merged to master)
- The NVIDIA open-gpu-kernel-modules issue #1026 confirms I2C operations work on
  RTX 5070 Ti/5080/5090 on Linux (the issue is performance, not access)

If `i2cdetect` shows no adapters, the likely causes are:
1. Missing `i2c-dev` kernel module (`modprobe i2c-dev`)
2. Using the proprietary NVIDIA driver instead of the open kernel modules
   (RTX 50 series requires nvidia-open-dkms, driver >= 570.86.16)
3. Permission issues on `/dev/i2c-*` devices

---

## Options for RGB Control

### Option A: I2C via OpenRGB (Recommended)

**Approach:** Build OpenRGB from master, add subsystem ID 0x5310 to detection, use
I2C at address 0x68.

**Steps:**
1. Ensure `i2c-dev` kernel module is loaded
2. Verify NVIDIA open kernel modules (not proprietary) are in use
3. Run `i2cdetect -l` to find NVIDIA GPU I2C adapters
4. Probe address 0x68: `i2cdetect -y <bus_number>`
5. If 0x68 responds, add `0x5310` to `pci_ids.h` and `MSIGPUv2ControllerDetect.cpp`
6. Build and run OpenRGB

**Pros:** Proven protocol, community-maintained, 18+ lighting modes, per-LED control
**Cons:** I2C performance bug on Linux causes FPS drops during continuous control;
single-shot color changes should be fine

### Option B: Direct I2C Control Script (Lightweight)

**Approach:** Use `i2c-tools` or Python `smbus2` to write directly to I2C registers.

**Minimal example to set static red:**
```python
import smbus2
bus = smbus2.SMBus(BUS_NUMBER)  # Find via i2cdetect -l
addr = 0x68
bus.write_byte_data(addr, 0x22, 0x01)  # Mode: static
bus.write_byte_data(addr, 0x30, 0xFF)  # Red
bus.write_byte_data(addr, 0x31, 0x00)  # Green
bus.write_byte_data(addr, 0x32, 0x00)  # Blue
bus.write_byte_data(addr, 0x36, 100)   # Brightness (max)
bus.write_byte_data(addr, 0x3F, 0x00)  # Commit/save
```

**Pros:** Zero dependencies, fast one-shot, no FPS impact
**Cons:** Must discover correct I2C bus number, limited to basic operations

### Option C: Reverse Engineer the USB HID Device (0db0:c9eb)

**Approach:** Capture USB traffic from MSI Center on Windows, decode the protocol.

**Steps:**
1. Install MSI Center + Mystic Light on Windows with this GPU
2. Run Wireshark with USBPcap or use USBlyzer
3. Capture traffic while changing RGB settings
4. Analyze the 64-byte HID packets

**Pros:** Could reveal a secondary control path independent of I2C
**Cons:** No existing documentation, VID:PID not in any database, likely not the RGB
controller, significant effort with uncertain payoff

---

## Recommendation

**Go with Option A or B -- I2C at address 0x68.**

The USB HID device at 0db0:c9eb is almost certainly not the RGB controller. Every
piece of evidence points to I2C as the interface:
- OpenRGB uses I2C for all MSI GPUs (v1 and v2 controllers)
- SignalRGB uses per-LED I2C for MSI 5000 series
- The RTX 5070 Ti is already in OpenRGB's detection code (just missing your subsystem ID)
- The protocol registers are well-documented

**Immediate next step:** Verify I2C access on FOUNDRY:
```bash
# On FOUNDRY (.244)
sudo modprobe i2c-dev
i2cdetect -l | grep -i nvidia
# Find the bus with port 1, then:
sudo i2cdetect -y <bus_number>
# Look for address 0x68
```

If address 0x68 responds, you have full RGB control available. If it doesn't, the
issue is likely the NVIDIA driver version or kernel module type (open vs proprietary).

---

## Sources

- [OpenRGB MSIGPUv2Controller source](https://github.com/CalcProgrammer1/OpenRGB/tree/master/Controllers/MSIGPUController/MSIGPUv2Controller)
- [OpenRGB pci_ids.h (RTX 5070 Ti device IDs)](https://github.com/CalcProgrammer1/OpenRGB/blob/master/pci_ids/pci_ids.h)
- [OpenRGB Issue #5018: MSI RTX 5070 Ti GAMING TRIO OC](https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/5018)
- [OpenRGB Issue #4705: MSI RTX 5070 Ti GAMING TRIO OC PLUS](https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/4705)
- [NVIDIA open-gpu-kernel-modules #1026: I2C lag on RTX 5080](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1026)
- [NVIDIA open-gpu-kernel-modules #41: I2C driver issues](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/41)
- [SignalRGB Changelog v2.5.6: MSI 4000/5000 series per-LED](https://docs.signalrgb.com/changelogs/)
- [msi-mystic-light-x870e: Reverse-engineered motherboard HID protocol](https://github.com/nmelo/msi-mystic-light-x870e)
- [linux-hardware.org: pci:10de-2c05-1462-5310](https://linux-hardware.org/?id=pci:10de-2c05-1462-5310)
- [OpenRGB Reverse Engineering Wiki](https://openrgb-wiki.readthedocs.io/en/latest/reverse-engineering/Reverse-Engineering/)
- [SimoDax MSI-mystic-light-tool](https://github.com/SimoDax/MSI-mystic-light-tool)
- [OpenRGB I2C/SMBus Communication (DeepWiki)](https://deepwiki.com/CalcProgrammer1/OpenRGB/3.3-i2csmbus-communication)
