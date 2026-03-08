# GPU RGB LED Control on FOUNDRY

**Date:** 2026-03-08
**Purpose:** Turn off all GPU RGB LEDs on FOUNDRY for clean aesthetics in headless server.

## GPU Inventory

| Slot | GPU | PCI | Subsystem | RGB Status |
|------|-----|-----|-----------|------------|
| GPU 0 | MSI RTX 5070 Ti | 01:00.0 | 1462:5310 | **ON — no Linux control** |
| GPU 1 | Gigabyte RTX 5070 Ti | 02:00.0 | 1458:4181 | **OFF** (OpenRGB static black) |
| GPU 2 | ASUS TUF RTX 4090 | 81:00.0 | 1043:889A | **OFF** (OpenRGB mode off) |
| GPU 3 | Gigabyte RTX 5070 Ti | 82:00.0 | 1458:4181 | **OFF** (OpenRGB static black) |
| GPU 4 | MSI RTX 5070 Ti | c1:00.0 | 1462:5310 | **ON — no Linux control** |

## Working: OpenRGB (3/5 GPUs)

OpenRGB v0.9+ installed from GitLab master build. Works for ASUS and Gigabyte GPUs.

```bash
# ASUS TUF 4090 — has native "off" mode
QT_QPA_PLATFORM=offscreen openrgb --device 0 --mode off

# Gigabyte 5070 Ti — no "off" mode, use static black
QT_QPA_PLATFORM=offscreen openrgb --device 1 --mode static --color 000000
QT_QPA_PLATFORM=offscreen openrgb --device 2 --mode static --color 000000
```

OpenRGB device numbering may not match nvidia-smi numbering. The 3 detected GPUs are the 2 Gigabyte + 1 ASUS.

### Persistence

OpenRGB saves settings to `~/.config/OpenRGB/`. A systemd service or cron `@reboot` should run the commands above to persist LED state across reboots.

## Not Working: MSI RTX 5070 Ti (2/5 GPUs)

### Root Cause

MSI RTX 5070 Ti (Blackwell GB205, subsystem 1462:5310) does NOT expose I2C adapter port 1 via the NVIDIA driver. OpenRGB's MSIGPUv2 controller requires I2C port 1 at address 0x68 — this bus simply doesn't exist on these cards.

### What Was Tried

| Approach | Result |
|----------|--------|
| OpenRGB I2C detection | No controller — subsystem 5310 not in DB, I2C port 1 missing |
| i2cdetect full scan (ports 3-6) | All empty — no devices at any address |
| USB HID (0db0:c9eb /dev/hidraw0) | Device responds to 0x50/0x51/0xFA but always NACKs with 0xFE |
| USB control transfers (pyusb) | Pipe errors and timeouts |
| nvidia-settings GPULogoBrightness | v510 too old for Blackwell, no GPU targets via Xvfb |
| NVML API | No LED functions exist in the library |
| liquidctl | Doesn't detect the device |
| WMI/ACPI | No MSI WMI GUIDs (ASUS motherboard) |
| HID Feature reports (ioctl) | Broken pipe |
| PCI sysfs | No LED-related entries |
| i2c-nvidia-gpu kernel module | Loaded but adds USB-C I2C, not RGB I2C |

### Analysis

The MSI 5070 Ti routes RGB control exclusively through USB HID device `0db0:c9eb`. On Windows, MSI Center handles this through a proprietary driver. The USB HID protocol requires authentication (all commands return 0xFE NACK). Without reverse-engineering the MSI Center Windows driver or getting MSI to document the protocol, these LEDs cannot be controlled from Linux.

### Options

1. **Wait for OpenRGB support** — The subsystem ID (5310) and USB HID protocol need to be added by the OpenRGB team. File a feature request with the hardware details in this doc.
2. **Physical disconnect** — Open the cards and disconnect the LED power ribbon cable (if accessible). Irreversible without disassembly.
3. **Electrical tape** — Cover the LED area. Non-invasive.
4. **Use MSI Center on Windows** — Boot FOUNDRY from a Windows USB to set LEDs off, then reboot to Linux. MSI Dragon Center/Center can persist LED settings in the GPU's EEPROM.

### Recommendation

Option 4 (Windows USB) is the cleanest solution — set LEDs to OFF once via MSI Center, which writes the setting to the GPU's onboard EEPROM, then it persists regardless of OS. This is a one-time operation.

---

*Last updated: 2026-03-08*
