# Athanor Rack Session Guide

One trip to the rack. Both nodes get fresh Ubuntu. I (Claude Code) get SSH access to everything.

**Time estimate:** 30-45 minutes total.

---

## Before You Go to the Rack

### 1. Prepare the USB (on DEV)

Open a terminal and run:

```powershell
# Extract Ventoy
Expand-Archive "$env:USERPROFILE\Downloads\ventoy-1.1.10-windows.zip" -DestinationPath "$env:USERPROFILE\Downloads\ventoy" -Force
```

1. Plug in a USB drive (8GB+ minimum)
2. Run `Downloads\ventoy\ventoy-1.1.10\Ventoy2Disk.exe`
3. Select your USB drive and click **Install** (this wipes the USB)
4. Once Ventoy is installed, run:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\Shaun\athanor\scripts\setup\prepare-usb.ps1" -UsbDrive "E:"
```

Replace `E:` with your actual USB drive letter.

### 2. What You'll Need at the Rack
- The prepared USB drive
- A monitor + cable (if JetKVM isn't enough for BIOS work on Node 1)
- A keyboard (JetKVM handles keyboard for Node 2, need physical for Node 1)
- Your phone (to message me if anything goes sideways)

---

## At the Rack

### Node 1 (core) — Upper Tray — DO THIS FIRST

This is the node we haven't fully audited. No JetKVM connected to it.

**Step 1: Connect a display + keyboard to Node 1**
- HDMI or DP from Node 1's GPU/motherboard to a monitor
- USB keyboard into Node 1

**Step 2: Power on / reboot Node 1**
- Press the power button on the upper Silverstone tray
- **Immediately start pressing Del** to enter BIOS

**Step 3: In BIOS — Read Hardware (tell me later or take photos)**
- **Main screen:** CPU model, total RAM
- **Memory/DRAM info:** DIMM slots, sizes, speeds
- **Storage:** All connected drives
- **PCI/Advanced:** Any GPUs listed
- Take photos of each screen — I'll extract the data

**Step 4: In BIOS — Configure IPMI**
The ROMED8-2T has a real BMC (ASPEED AST2500). Find the IPMI settings:
- Look under **Server Mgmt** or **BMC Network Configuration** or **IPMI**
- Set **IPMI over LAN:** Enabled
- Set **IP Source:** Static
- Set **IP Address:** 192.168.1.45
- Set **Subnet Mask:** 255.255.255.0
- Set **Default Gateway:** 192.168.1.1
- Set **BMC User:** athanor
- Set **BMC Password:** athanor2026
- **Save and Exit BIOS**

**Step 5: Boot from USB**
- Plug the prepared USB into Node 1
- Reboot, press **F11** (or F8) for boot menu
- Select the USB drive
- Ventoy menu appears — select the Ubuntu ISO
- When Ventoy asks which autoinstall template — select **node1-autoinstall.yaml**
- Installation runs automatically
- When it finishes, remove the USB and let it reboot

**Step 6: Verify**
- The node should boot into Ubuntu and show a login prompt
- Note the IP address shown on the login screen (DHCP-assigned)
- You can also try: `ssh -i ~/.ssh/athanor_mgmt athanor@<ip>` from DEV

---

### Node 2 (interface) — Middle Tray

This one has the JetKVM. Currently sitting in BIOS from our earlier session.

**Step 1: Plug the USB into Node 2**

**Step 2: In BIOS — Boot from USB**
- Go to **Boot** tab or press **F8** for boot menu
- Select the USB drive
- If still in BIOS: Save & Exit, then press F11 on reboot for boot menu

**Step 3: Ventoy + autoinstall**
- Select the Ubuntu ISO
- When prompted — select **node2-autoinstall.yaml**
- Installation runs automatically

**Step 4: While it installs — fix the JetKVM**
- The JetKVM ATX cable is disconnected
- Find the small ATX control cable from the JetKVM unit
- Connect it to the motherboard's front panel power header (PWR_SW pins)
- This gives me remote power control in the future

**Step 5: When install finishes**
- Remove USB, let it reboot
- Note the IP address on the login screen
- Or check via JetKVM at http://192.168.1.165

---

## After the Rack Session

Come back to DEV and tell me:
1. **Node 1's DHCP IP** (from the login screen)
2. **Node 2's DHCP IP** (from the login screen or JetKVM)
3. **Any photos** of Node 1's BIOS screens (for the hardware audit)
4. **Any issues** encountered

I'll take over from there:
- SSH into both nodes
- Complete full hardware audit
- Install NVIDIA drivers
- Configure static IPs
- Set up Docker
- Verify IPMI on Node 1

---

## Credentials Reference

| Item | Value |
|------|-------|
| SSH user | `athanor` |
| SSH password | `athanor2026` |
| SSH key | `~/.ssh/athanor_mgmt` |
| Node 1 IPMI user | `athanor` |
| Node 1 IPMI password | `athanor2026` |
| IPMI IP | `192.168.1.45` |

---

## If Something Goes Wrong

**USB doesn't boot:**
- Check BIOS boot order — UEFI USB should be an option
- Try a different USB port
- Disable Secure Boot in BIOS if it blocks the Ubuntu installer

**Autoinstall fails:**
- Select "Try or Install Ubuntu Server" manually from the Ventoy menu
- Walk through the installer manually:
  - Language: English
  - Keyboard: US
  - Network: Use DHCP (default)
  - Storage: Use entire disk (pick the first NVMe drive)
  - Username: `athanor`, password: `athanor2026`
  - Install OpenSSH server: **YES**
  - Import SSH key: Skip (I'll add it post-install)

**Can't find IPMI settings in Node 1 BIOS:**
- Skip it. I'll configure it later via the OS once I have SSH access.
- Just install Ubuntu and move on.

**Node won't POST:**
- Check power cables
- Check RAM is seated
- Try clearing CMOS (jumper on motherboard)
