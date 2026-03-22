# DEV + Network Infrastructure Audit -- 2026-02-25

Auditor: Claude Opus 4.6 (automated)
Method: Local commands on WSL2, PowerShell via Windows interop, SSH to nodes, paramiko to VAULT
Previous audit: `docs/hardware/dev-audit-2026-02-14.md`

---

## Executive Summary

**6 inventory discrepancies found.** DEV hardware has changed significantly since the Feb 14 audit and does not match `docs/hardware/inventory.md`. The most impactful finding is the Ethernet link negotiating at **100 Mbps instead of 1 Gbps**, throttling all SSH/rsync workflows to the cluster. Additionally, WSL2 is severely resource-constrained (25% of host RAM, 33% of host CPU threads), and an RTX 3060 12GB GPU is sitting idle with CUDA available.

---

## SECTION 1: INVENTORY DISCREPANCIES

These items differ between physical reality (verified today) and the locked inventory docs.

| # | Component | Inventory Says | Reality (Verified) | Status | Impact |
|---|-----------|---------------|-------------------|--------|--------|
| 1 | **DEV GPU** | RX 5700 XT 8GB (inventory.md #10) | RTX 3060 12GB (nvidia-smi confirmed) | MISMATCH | RTX 3060 was listed as "Loose" -- it is installed in DEV |
| 2 | **RX 5700 XT** | In DEV (inventory.md #10) | Not present (Windows shows only RTX 3060 + Intel UHD 770) | MISMATCH | RX 5700 XT location unknown -- likely loose |
| 3 | **DEV RAM** | F5-5200J3636D32G 2x32GB DDR5-5200 CL36 (inventory.md #16-17) | F5-5600J4040D32G 2x32GB DDR5-5600 CL40 (PowerShell confirmed) | MISMATCH | The 5600 CL40 kit was listed as "Loose" (#18-19) |
| 4 | **DDR5-5200 kit** | In DEV (inventory.md #16-17) | Not present in DEV | MISMATCH | Location unknown -- swapped out, presumably loose |
| 5 | **DEV Storage** | "Unknown (assumed local drives)" (CURRENT-STATE.md) | 3 NVMe drives, 7TB total (see below) | MISMATCH | All 3 drives listed as "Loose" in inventory |
| 6 | **Samsung 970 EVO 250GB** | Listed as "Loose" (inventory.md #14) | Was in DEV on Feb 14 (E: drive), now absent | MISMATCH | Removed between Feb 14-25; status unknown |

### DEV Storage (Verified via PowerShell `Get-PhysicalDisk`)

| Drive | Model | Capacity | Interface | Inventory Status |
|-------|-------|----------|-----------|-----------------|
| Crucial CT4000P3PSSD8 | P3 Plus 4TB | 3.73 TB | NVMe Gen4 | Listed as Loose (#12) |
| Crucial CT2000P310SSD8 | P310 2TB | 1.86 TB | NVMe Gen4 | Listed as Loose (#13) |
| Crucial CT1000T700SSD3 | T700 1TB | 931 GB | NVMe Gen5 | Listed as Loose (#18) -- NEW since Feb 14 |

The Samsung 970 EVO 250GB (E: drive on Feb 14) is no longer detected. A Crucial T700 1TB Gen5 has been added since the last audit.

### Changes Since Feb 14 Audit

| Change | Old (Feb 14) | New (Feb 25) |
|--------|-------------|-------------|
| RAM | F5-5200J3636D32G DDR5-5200 CL36 | F5-5600J4040D32G DDR5-5600 CL40 |
| Storage added | -- | Crucial T700 1TB Gen5 |
| Storage removed | Samsung 970 EVO 250GB (E:) | Gone |
| Network | WiFi active (432 Mbps), Ethernet disconnected | Ethernet active (100 Mbps!), WiFi disconnected |

**Recommendation:** Inventory docs need updating with operator confirmation. The RX 5700 XT and DDR5-5200 kit need physical location verification.

---

## SECTION 2: DEV MACHINE AUDIT

### 2.1 System Identity

| Field | Value |
|-------|-------|
| Hostname (Windows) | DESKTOP-O436TIE |
| OS | Windows 11 IoT Enterprise LTSC (Build 26100) |
| WSL2 Distro | Ubuntu 24.04.4 LTS |
| WSL2 Kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Uptime | 1 day, 18:59 at time of audit |
| IP (Windows) | 192.168.1.215 (Ethernet) |
| IP (WSL2) | 192.168.1.167 (mirrored networking) |

### 2.2 CPU

| Field | Value | Notes |
|-------|-------|-------|
| Model | Intel Core i7-13700K | Matches inventory |
| Physical Cores | 16 (8P + 8E) | Verified via PowerShell |
| Logical Threads | 24 | Verified via PowerShell |
| WSL2 vCPUs | 8 (4 cores, 2 threads) | `.wslconfig` limits `processors=8` |
| WSL2 CPU % | 33% of host threads | Suboptimal for heavy builds |

**Assessment:** WSL2 sees only 8 of 24 threads. For Ansible runs, large git operations, and parallel SSH sessions this is adequate. For CPU-intensive compilation or data processing, this is a bottleneck. The P-cores vs E-cores distinction is lost in WSL -- it just sees 4 generic cores.

**Recommendation:** Increase `.wslconfig` processors to 16 (or remove the limit). Windows will still get CPU time via scheduling. The current limit wastes 16 threads.

### 2.3 Memory

| Field | Value | Notes |
|-------|-------|-------|
| Physical RAM | 64 GB DDR5-5600 (2x32GB G.Skill Ripjaws S5) | Verified via PowerShell |
| WSL2 Allocation | 16 GB (`.wslconfig memory=16GB`) | 25% of host |
| WSL2 Used | 3.8 GB of 16 GB | Plenty of headroom currently |
| WSL2 Swap | 4 GB (2.9 GB used = 72%) | Swap pressure is concerning |
| autoMemoryReclaim | gradual (enabled) | Good -- returns unused pages to host |

**Assessment:** 16 GB is tight for WSL2. Swap at 72% utilization indicates memory pressure has occurred. With Claude Code, Ansible, SSH sessions, and potential local Python work, 16 GB can become a bottleneck.

**Recommendation:** Increase to 32 GB (50% of host). Windows desktop use rarely needs more than 16-20 GB. Also increase swap to 8 GB. The `sparseVhd=true` and `autoMemoryReclaim=gradual` settings are good and should stay.

### 2.4 GPU

| Field | Value |
|-------|-------|
| Model | NVIDIA GeForce RTX 3060 |
| VRAM | 12 GB GDDR6 |
| Architecture | Ampere (sm_86) |
| Driver | 560.94 (CUDA 12.6) |
| Bus | PCIe 4.0 x16 (00000000:01:00.0) |
| Current State | Idle (0% util, 980 MiB used, 31C) |
| WSL2 Access | Yes -- via /dev/dxg, CUDA libs in /usr/lib/wsl/lib/ |
| Also Present | Intel UHD Graphics 770 (iGPU) |
| RX 5700 XT | **NOT PRESENT** (contradicts inventory) |

**Assessment:** This is a fully CUDA-capable GPU sitting completely idle. WSL2 has CUDA 12.6 access via the DirectX GPU paravirtualization layer. It cannot be used for display output in WSL (no /dev/dri), but CUDA compute works.

**Potential uses for the RTX 3060 12GB:**
1. **Local embedding/inference:** Run a small model (Qwen3-8B or similar) locally on DEV for instant-response coding assistance, avoiding network round-trips to Node 1.
2. **Local ComfyUI preview:** Test workflows before sending to Node 2's 5090.
3. **Development GPU testing:** Test CUDA code, container GPU passthrough, etc.
4. **Ollama:** Quick local inference for ad-hoc tasks without hitting the cluster.

**Current verdict:** Wasted. 12 GB of VRAM and an Ampere GPU doing nothing.

### 2.5 Storage

| Drive | Windows Mount | Capacity | Used | Free | Filesystem |
|-------|-------------|----------|------|------|-----------|
| Crucial P3 Plus 4TB (Gen4) | C:\ | 931 GB | 151 GB (17%) | 780 GB | NTFS |
| Crucial P310 2TB (Gen4) | D:\ | 3.7 TB | 390 GB (11%) | 3.3 TB | NTFS |
| Crucial T700 1TB (Gen5) | E:\ | 1.9 TB | 138 GB (8%) | 1.7 TB | NTFS |
| WSL2 ext4 vhdx | / | 1 TB | 7.2 GB (1%) | 949 GB | ext4 |

**Note:** The `df` output shows the Windows C:\ drive at 931 GB, not 3.7 TB. The P3 Plus 4TB shows as 3.7 TB on D:. The mapping appears to be: C: = T700 1TB, D: = P3 Plus 4TB, E: = P310 2TB. (This differs from the Feb 14 audit -- drives were reassigned.)

**WSL2 vhdx:** 1 TB allocated (sparse), only 7.2 GB used. The Athanor repo is 1.7 GB on the native ext4 filesystem -- good, not on a Windows mount.

**Local disk performance:** 2.8 GB/s sequential write on ext4 (tested with dd). Excellent for a development workstation.

**NFS Mounts:** None. DEV has no NFS mounts to VAULT. All file transfer is via SSH/rsync.

**NFS client package:** `nfs-common` is **not installed**. Cannot mount NFS even if desired.

**Assessment:** 5.8 TB free across all drives. Storage is not a constraint. The repo correctly lives on native ext4 (not /mnt/c), which avoids the massive I/O penalty of cross-filesystem access.

### 2.6 Network

| Adapter | Type | Link Speed | Status | Notes |
|---------|------|-----------|--------|-------|
| Intel I225-V (Ethernet) | 1GbE capable | **100 Mbps** | Connected | DEGRADED -- should be 1 Gbps |
| Intel Wi-Fi 6 AX200 | WiFi 6 | -- | Disconnected | Was primary on Feb 14 |
| Tailscale | Tunnel | 100 Gbps (virtual) | Running | Service active on Windows |
| vEthernet (FSE HostVnic) | Hyper-V | 10 Gbps (virtual) | Up | WSL2 networking |
| vEthernet (cowork-vm-vnet) | Hyper-V | 10 Gbps (virtual) | Up | Unknown VM |

**CRITICAL: Ethernet at 100 Mbps.** The Intel I225-V is a 1 Gbps NIC negotiating at 100 Mbps. Measured throughput confirms: **10.9 MB/s** (87 Mbps effective) to both Node 1 and Node 2. This is 10x slower than it should be.

**Possible causes:**
- Bad Ethernet cable (most likely -- Cat5 or damaged Cat5e/6)
- Switch port negotiation failure
- I225-V driver bug (known issues with early I225-V revisions)
- Damaged RJ45 connector

**Impact:** Every rsync deploy, SSH session, and Ansible run is throttled. A typical agent deploy (rsync src + rebuild) that should take 2-3 seconds takes 20-30 seconds.

**Ping latency (DEV to all nodes):**

| Target | IP | Latency | Status |
|--------|-----|---------|--------|
| Node 1 (Foundry) | 192.168.1.244 | 0.31 ms avg | OK |
| Node 2 (Workshop) | 192.168.1.225 | 0.49 ms avg | OK |
| VAULT | 192.168.1.203 | 0.65 ms avg | OK |
| UDM Pro (Gateway) | 192.168.1.1 | 0.27 ms avg | OK |

Latency is fine. The problem is purely bandwidth.

**WSL2 Networking Mode:** Mirrored (`networkingMode=mirrored` in .wslconfig). WSL2 gets its own LAN IP (192.168.1.167), not NAT'd behind the Windows IP. This is correct for a development workstation that needs direct LAN access.

**DNS:** Resolves via 10.255.255.254 (WSL2 internal DNS proxy). No reverse DNS for any node. No entries in /etc/hosts for cluster nodes.

**Tailscale:** Running on Windows (service confirmed) but **not needed** — Shaun confirmed remote access is not a requirement (2026-02-26). Should be uninstalled to free resources.

### 2.7 SSH Configuration

**Keys:**

| Key | Type | Purpose |
|-----|------|---------|
| id_ed25519 | Ed25519 | Primary identity |
| id_ed25519_wsl | Ed25519 | WSL-specific (unclear purpose -- duplicate?) |
| athanor_mgmt | Ed25519 | Cluster management key |
| mobile_key | Ed25519 | Mobile access (at ~/.ssh/mobile_key) |

**SSH Config (`~/.ssh/config`):**

| Alias | Host | User | Auth |
|-------|------|------|------|
| node1 | 192.168.1.244 | athanor | athanor_mgmt, id_ed25519 |
| node2 | 192.168.1.225 | athanor | athanor_mgmt, id_ed25519 |
| vault | 192.168.1.203 | root | id_ed25519, athanor_mgmt |

**SSH Connectivity:**

| Target | Method | Result |
|--------|--------|--------|
| node1 | `ssh node1` | OK -- hostname `core`, uptime 2d 12h |
| node2 | `ssh node2` | OK -- hostname `interface`, uptime 2d 4h |
| vault | `ssh vault` | DENIED -- Permission denied (publickey) |
| vault | `vault-ssh.py` | OK -- hostname `Unraid`, uptime 2d 14h |

**SSH Agent:** NOT running. `ssh-add -l` fails with "Could not open a connection to your authentication agent." No auto-start in `.bashrc` or `.profile`. Keys work because they're specified in `~/.ssh/config` directly.

**Authorized Keys:** Only the phone SSH key is authorized for inbound SSH to DEV.

**Assessment:** SSH config is functional but fragile. No ssh-agent means every new tmux pane that needs agent forwarding will fail. The VAULT native SSH denial is a known issue (documented in MEMORY.md).

**Recommendation:** Add ssh-agent auto-start to `.bashrc`:
```bash
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)" > /dev/null 2>&1
    ssh-add ~/.ssh/id_ed25519 ~/.ssh/athanor_mgmt 2>/dev/null
fi
```

### 2.8 Development Tools

| Tool | Version | Location | Notes |
|------|---------|----------|-------|
| Python | 3.12.3 | /usr/bin/python3 | Ubuntu 24.04 system Python |
| pip | 24.0 | /usr/bin/pip3 | System + user packages |
| Node.js | 22.22.0 | (system) | LTS, current |
| npm | 10.9.4 | (system) | Current |
| Git | 2.43.0 | /usr/bin/git | Adequate |
| GitHub CLI | Authenticated | GITHUB_TOKEN | Logged in as Dirty13itch |
| Ansible | 2.16.3 (core) | /usr/bin/ansible | For cluster management |
| Claude Code | 2.1.56 | ~/.local/bin/claude | Current |
| rsync | 3.2.7 | /usr/bin/rsync | For deploy workflows |
| tmux | (installed) | /usr/bin/tmux | Session: `athanor` (2 windows) |
| Docker | **NOT INSTALLED** | -- | Cannot build containers locally |
| uv | **NOT INSTALLED** | -- | Modern Python package manager missing |
| bun | **NOT INSTALLED** | -- | Fast JS runtime missing |
| jq | **NOT INSTALLED** | -- | JSON processing missing |
| htop | **NOT INSTALLED** | -- | System monitor missing |
| iperf3 | **NOT INSTALLED** | -- | Network testing missing |
| nfs-common | **NOT INSTALLED** | -- | NFS client missing |

**Python Packages (user-installed):**

| Package | Version | Purpose |
|---------|---------|---------|
| mcp | 1.26.0 | MCP bridge for Claude Code |
| paramiko | 4.0.0 | VAULT SSH (vault-ssh.py) |
| httpx | 0.28.1 | HTTP client |
| pydantic | 2.12.5 | Data validation |
| ansible | (system) | Cluster management |

**Claude Code Configuration:**
- 11 plugins enabled (code-review, feature-dev, hookify, pyright-lsp, security-guidance, etc.)
- 5 MCP servers configured: sequential-thinking, context7, grafana, filesystem, athanor-agents
- Agent teams experimental flag enabled
- Autocompact at 80%

**tmux Session:**
- Session `athanor` with 2 windows: `claude-` and `happy`

**Assessment:** The toolchain is adequate for an orchestrator role (SSH + Ansible + rsync to nodes, Claude Code for development). The lack of Docker means all container work must happen on remote nodes, which is fine given the current workflow. Missing `jq` is an annoyance for API debugging. Missing `uv` means Python dependency management is slower than it needs to be.

---

## SECTION 3: NETWORK INFRASTRUCTURE AUDIT

### 3.1 Node Link Speeds

| Node | Interface | Negotiated Speed | Switch | Expected |
|------|-----------|-----------------|--------|----------|
| Node 1 | enp66s0f0 (X550 #1) | 10 Gbps Full | USW Pro XG 10 PoE | 10 Gbps |
| Node 1 | enp66s0f1 (X550 #2) | 10 Gbps Full | USW Pro XG 10 PoE | 10 Gbps |
| Node 2 | eno1 (Marvell 5GbE) | 10 Gbps Full | USW Pro XG 10 PoE | 10 Gbps |
| Node 2 | enp71s0 (RTL8125 2.5GbE) | 2.5 Gbps Full | USW Pro 24 PoE | 2.5 Gbps |
| VAULT | bond0 (dual NIC) | 10 Gbps | USW Pro XG 10 PoE | 10 Gbps |
| **DEV** | **Intel I225-V** | **100 Mbps** | **Unknown port** | **1 Gbps** |

**CURRENT-STATE.md says** all servers are "currently on 1GbE switch." This is **wrong** -- Node 1, Node 2, and VAULT are all on the 5GbE switch (USW Pro XG 10 PoE) at full 10 Gbps. Only DEV appears to be degraded.

**Node 1 dual-NIC:** Both X550 ports are UP at 10 Gbps. This could support link aggregation or separate data/management planes. Currently both appear to be on the same switch.

**VAULT bonding:** eth0 + eth1 bonded as `bond0` at 10 Gbps. Good for NFS serving.

### 3.2 NFS Performance

| Path | Client | Write Speed | Protocol |
|------|--------|-------------|----------|
| /mnt/vault/data | Node 1 | 1.0 GB/s | NFSv4.2, TCP |
| /mnt/vault/data | Node 2 | 1.1 GB/s | NFSv4.2, TCP |
| /mnt/vault/* | DEV | N/A (no mounts) | -- |

NFS performance is excellent on the 5GbE fabric. Node 1 and Node 2 are using rsize/wsize=131072 (128K), soft mounts, NFSv4.2. This is well-tuned.

DEV has no NFS mounts and no NFS client installed. All file transfer uses rsync over SSH at 10.9 MB/s (limited by the 100 Mbps Ethernet link).

### 3.3 Bandwidth Matrix (Measured)

| From | To | Measured | Theoretical Max |
|------|-----|---------|-----------------|
| DEV | Node 1 | 10.9 MB/s (87 Mbps) | 125 MB/s (1 Gbps) |
| DEV | Node 2 | 10.9 MB/s (87 Mbps) | 125 MB/s (1 Gbps) |
| Node 1 | VAULT (NFS write) | 1.0 GB/s | 1.25 GB/s |
| Node 2 | VAULT (NFS write) | 1.1 GB/s | 1.25 GB/s |

### 3.4 UniFi Controller

The UDM Pro web UI at `https://192.168.1.1` is reachable. Running UniFi OS 3.0.1 on model UDMPRO. API requires authentication (no anonymous access).

### 3.5 Service Reachability from DEV

| Service | Target | Status |
|---------|--------|--------|
| vLLM (inference) | Node 1:8000 | Reachable (via SSH) |
| Agent Server | Node 1:9000 | Reachable (MCP bridge works) |
| Dashboard | Node 2:3001 | Reachable |
| Grafana | VAULT:3000 | Reachable (MCP server configured) |
| Prometheus | VAULT:9090 | Reachable |
| Home Assistant | VAULT:8123 | Reachable |

---

## SECTION 4: ASSESSMENT AND RECOMMENDATIONS

### Critical Issues (Fix Immediately)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | **Ethernet at 100 Mbps** | Every SSH/rsync deploy is 10x slower than it should be | Replace cable, check switch port, test with different port |
| 2 | **6 inventory mismatches** | Docs are wrong -- makes future planning unreliable | Update inventory.md after Shaun confirms physical state |

### High Priority (Fix This Week)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 3 | **WSL2 RAM: 16 GB (25%)** | Swap at 72%, memory pressure during heavy sessions | Set `memory=32GB` in `.wslconfig` |
| 4 | **WSL2 CPU: 8 threads (33%)** | Wasted compute for parallel operations | Set `processors=16` in `.wslconfig` (or remove limit) |
| 5 | **RTX 3060 idle** | 12 GB VRAM doing nothing, CUDA accessible | Install Ollama in WSL2 for local inference |
| 6 | **SSH agent not auto-starting** | Must manually run `eval $(ssh-agent)` each session | Add auto-start to `.bashrc` |

### Medium Priority (Improve When Convenient)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 7 | **No Docker on DEV** | Cannot build/test containers locally | Install Docker CE in WSL2 (not Docker Desktop) |
| 8 | **Missing tools: jq, htop, uv** | Minor workflow friction | `sudo apt install jq htop && pip3 install uv` |
| 9 | **No NFS mounts on DEV** | Must rsync everything, no direct model/data access | Install nfs-common, mount /mnt/vault/models read-only |
| 10 | **No /etc/hosts entries** | Must use IPs, no friendly names | Add node1/node2/vault to /etc/hosts (or WSL generateHosts) |
| 11 | **CURRENT-STATE.md network claims wrong** | Says nodes on 1GbE switch -- they are on 5GbE | Update doc |
| 12 | **DEV has 1GbE NIC only** | Even when cable is fixed, max 1 Gbps | Install loose X540-T2 5GbE NIC in DEV (6 loose 5GbE ports available) |

### Low Priority / Observations

| # | Item | Notes |
|---|------|-------|
| 13 | Tailscale running on Windows | Service active but not needed. **Uninstall recommended** (Shaun confirmed remote access not required 2026-02-26). |
| 14 | Hyper-V VM present | "cowork-vm-vnet" virtual switch exists. Unknown purpose. Consumes resources. |
| 15 | WSL2 sparse VHD + autoMemoryReclaim | Good settings, already enabled. |
| 16 | `id_ed25519_wsl` key | Purpose unclear -- potentially redundant with `id_ed25519`. |
| 17 | VAULT at 90% disk capacity | 146T/164T. Not DEV-specific but noted during audit. |

### Resource Waste Summary

| Resource | Amount Wasted | Recovery Action |
|----------|--------------|-----------------|
| RTX 3060 12GB VRAM | 100% idle | Run local Ollama or embedding model |
| CPU threads | 16 of 24 hidden from WSL | Increase .wslconfig processors |
| RAM | 48 GB unused by WSL | Increase .wslconfig memory |
| Bandwidth | 90% of 1GbE link | Fix cable/port (100 Mbps -> 1 Gbps) |
| 5GbE potential | 100% (1GbE NIC) | Install loose X540-T2 NIC |

---

## SECTION 5: VERIFIED HARDWARE SUMMARY

This is what DEV actually contains as of 2026-02-25.

```
DEV -- Shaun's Workstation (192.168.1.215 Windows / .167 WSL2)

Motherboard: Gigabyte Z690 AORUS ULTRA (LGA 1700, DDR5)
CPU:         Intel Core i7-13700K (16C/24T, 8P+8E, 3.4 GHz base)
RAM:         2x G.Skill Ripjaws S5 32GB DDR5-5600 CL40 = 64 GB
             (Part: F5-5600J4040D32G -- NOT the F5-5200 CL36 from inventory)

GPU:         NVIDIA GeForce RTX 3060 12GB GDDR6 (Ampere, sm_86)
             (NOT the RX 5700 XT from inventory)
iGPU:        Intel UHD Graphics 770

Storage:
  M.2_1: Crucial T700 1TB Gen5     (C:\, 780 GB free)  -- NEW since Feb 14
  M.2_2: Crucial P3 Plus 4TB Gen4  (D:\, 3.3 TB free)
  M.2_3: Crucial P310 2TB Gen4     (E:\, 1.7 TB free)
  WSL2:  1 TB ext4 vhdx            (/, 949 GB free)
  USB:   USB DISK 3.0 58GB         (WIN11-LTSC installer)

Network:
  Intel I225-V 1GbE      Connected at 100 Mbps (DEGRADED)
  Intel Wi-Fi 6 AX200    Disconnected
  Tailscale              Running (Windows service) — UNINSTALL (not needed per 2026-02-26)

PSU: Unidentified
Case: Unidentified

OS: Windows 11 IoT Enterprise LTSC (Build 26100)
WSL2: Ubuntu 24.04.4 LTS, kernel 6.6.87.2
```

---

## SECTION 6: CORRECTED LOOSE INVENTORY

If DEV's actual contents are confirmed, the loose inventory changes as follows.

**Moves OUT of loose (now in DEV):**
- RTX 3060 12GB (was listed as loose GPU)
- F5-5600J4040D32G 2x32GB DDR5-5600 CL40 (was listed as loose RAM #18-19)
- Crucial P3 Plus 4TB (was listed as loose NVMe #12)
- Crucial P310 2TB (was listed as loose NVMe #13)
- Crucial T700 1TB (was listed as loose NVMe #18)

**Moves INTO loose (removed from DEV):**
- RX 5700 XT 8GB (was listed as in DEV)
- F5-5200J3636D32G 2x32GB DDR5-5200 CL36 (was listed as in DEV)
- Samsung 970 EVO 250GB (was in DEV on Feb 14, now gone)

**Net effect on loose counts:**
- Loose GPUs: RTX 3060 removed, RX 5700 XT added (net: same count, different card)
- Loose RAM DDR5: 5600 CL40 kit removed, 5200 CL36 kit added (net: same count, different specs)
- Loose NVMe: 3 drives removed (P3 Plus 4TB, P310 2TB, T700 1TB), 970 EVO 250GB added
- Loose NVMe total: was 13 TB across 7+ drives, now ~7.75 TB (lost 7 TB to DEV, gained 250 GB)

---

## Appendix: Raw Data

### .wslconfig (C:\Users\Shaun\.wslconfig)
```ini
[wsl2]
memory=16GB
processors=8
swap=4GB
localhostForwarding=true
networkingMode=mirrored
vmIdleTimeout=-1

[experimental]
sparseVhd=true
autoMemoryReclaim=gradual
```

### /etc/wsl.conf
```ini
[boot]
systemd=true

[user]
default=shaun
```

### SSH Config (~/.ssh/config)
```
Host node1
    HostName 192.168.1.244
    User athanor
    IdentityFile ~/.ssh/athanor_mgmt
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no

Host node2
    HostName 192.168.1.225
    User athanor
    IdentityFile ~/.ssh/athanor_mgmt
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no

Host vault
    HostName 192.168.1.203
    User root
    IdentityFile ~/.ssh/id_ed25519
    IdentityFile ~/.ssh/athanor_mgmt
    StrictHostKeyChecking no
```

---

**Audit complete.** 2026-02-25T13:45:00-06:00
