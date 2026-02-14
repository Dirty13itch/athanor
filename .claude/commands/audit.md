---
description: Audit a node's hardware by connecting to it and discovering what's installed. Produces a complete hardware inventory.
allowed-tools: Bash(ssh:*), Bash(curl:*), Bash(talosctl:*), Bash(ping:*), Bash(nmap:*), Bash(cat:*), Bash(powershell:*), Read, Write, Edit, mcp__desktop-commander__*
---

Audit the hardware on: $ARGUMENTS

Use Desktop Commander for persistent SSH sessions when possible — it maintains state between commands unlike basic bash.

If the target is "unraid" or "vault":
- SSH to 192.168.1.139
- Run: cat /proc/cpuinfo, free -h, lspci -nn, lsblk, ip addr, nvidia-smi (if available)
- Check Unraid dashboard API if accessible
- Inventory all Docker containers running

If the target is "node1":
- Try talosctl against 192.168.1.244 or .245
- Run: talosctl get members, talosctl get cpu, talosctl get memory, talosctl get blockdevices
- If talosctl fails, try SSH or note what access method is needed
- Check IPMI at the ASRock Q270 Pro BTC+ interface

If the target is "node2":
- Try talosctl against 192.168.1.10
- Same commands as node1

If the target is "dev":
- This is the local Windows machine — use powershell commands
- Get-ComputerInfo, Get-CimInstance Win32_Processor, GPU info via nvidia-smi or Get-CimInstance Win32_VideoController

If the target is "network":
- Scan the subnet: nmap -sn 192.168.1.0/24
- Document all discovered devices
- Cross-reference with known devices from VISION.md
- Check UniFi controller API if accessible

For any target:
1. Document everything discovered
2. Save to docs/hardware/{target}-audit-YYYY-MM-DD.md
3. Include: CPU model/cores/threads, RAM amount/type, GPUs with VRAM, all storage devices with sizes, all network interfaces with speeds and MACs, any other notable hardware
4. Flag anything unexpected or that contradicts prior assumptions
5. Do NOT guess or fill in from memory — only report what the audit actually discovers
