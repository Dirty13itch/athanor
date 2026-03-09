---
description: Audit a node's hardware by connecting to it and discovering what's installed. Produces a complete hardware inventory.
allowed-tools: Bash(ssh:*), Bash(curl:*), Bash(ping:*), Bash(nmap:*), Bash(cat:*), Bash(powershell:*), Read, Write, Edit
---

Audit the hardware on: $ARGUMENTS

If the target is "vault":
- SSH via `python3 scripts/vault-ssh.py` (paramiko — credentials in vault-password file)
- Run: cat /proc/cpuinfo, free -h, lspci -nn, lsblk, ip addr, nvidia-smi (if available)
- Check Unraid dashboard API if accessible
- Inventory all Docker containers running

If the target is "node1":
- SSH to athanor@192.168.1.244 using athanor_mgmt key
- Run: lscpu, free -h, lspci -nn, lsblk, ip addr, nvidia-smi, docker ps
- Check GPU power limits: nvidia-smi -q -d POWER

If the target is "node2":
- SSH to athanor@192.168.1.225 using athanor_mgmt key
- Same commands as node1

If the target is "dev":
- This is the local Linux machine (Ryzen 9 9900X, RTX 5060 Ti)
- Run locally: lscpu, free -h, lspci -nn, lsblk, ip addr, nvidia-smi, docker ps

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
