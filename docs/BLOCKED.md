# Blocked Tasks

*Updated: 2026-02-16*

Tasks that cannot proceed without Shaun's physical presence, credentials, or browser access.

---

## Browser Tasks (~10 min)

### Home Assistant Onboarding
- **URL**: http://192.168.1.203:8123
- **What**: Complete initial setup wizard in browser
- **Blocks**: Home Agent development, Lutron/UniFi integration, HA MCP server
- **Priority**: High — unlocks three downstream tasks

### Add Agent Server to Open WebUI
- **URL**: Open WebUI → Settings → Connections → OpenAI
- **What**: Add URL `http://192.168.1.244:9000/v1`, Key: `not-needed`
- **Blocks**: Agent access from Open WebUI chat interface
- **Priority**: Medium

---

## Credentials Needed

### NordVPN Service Credentials
- **What**: Updated NordVPN token or service credentials for Gluetun VPN container
- **Blocks**: qBittorrent + Gluetun VPN deployment (compose file ready)
- **Priority**: Medium — media acquisition stack incomplete without it

### HuggingFace Token (optional)
- **What**: HF token for gated model access
- **Blocks**: Full-precision Flux dev model download (FP8 version already working)
- **Priority**: Low

---

## Physical Rack Session (~20 min)

### 10GbE Switch Migration
- **What**: Move Node 1 + Node 2 ethernet cables from USW Pro 24 PoE to USW Pro XG 10 PoE
- **Blocks**: 10GbE throughput between nodes, iperf3 verification
- **Priority**: High — 10x bandwidth for NFS and inter-node traffic

### Samsung 990 PRO 4TB (Node 1)
- **What**: Verify physical seat of NVMe drive or check BIOS M.2 slot settings
- **Blocks**: 4TB additional local storage on Node 1
- **Priority**: Medium

### JetKVM ATX Power Cable (Node 2)
- **What**: Reconnect ATX power cable for remote power control
- **Blocks**: Remote power management of Node 2
- **Priority**: Low

### BIOS: Enable EXPO (Node 2)
- **What**: Enable DDR5 EXPO profile in BIOS (3600 → 5600 MT/s)
- **Blocks**: Full memory bandwidth on Node 2
- **Priority**: Low — functional at 3600, performance improvement only

---

## Purchases Required

| Item | Est. Cost | Blocks | Priority |
|------|-----------|--------|----------|
| Mining GPU enclosure (6-8 slot) | ~$100-200 | Phase 8 Node 1 → 6 GPU build | High (when ready) |
| Add2PSU adapter | ~$10-15 | Dual PSU sync for 6-GPU build | High (when ready) |
| PCIe riser cables (6x) | ~$30-50 | 6-GPU build | High (when ready) |
| 2x Mellanox ConnectX-3 FDR | ~$60 | InfiniBand inter-node link | Medium |
| 1x QSFP+ FDR cable | ~$15 | InfiniBand inter-node link | Medium |

---

## BMC Configuration (.216)

- **Status**: HTTP responds (301 redirect), IPMI with default admin/admin fails
- **What**: Need to identify correct credentials or reset BMC
- **Blocks**: Remote power/BIOS management of Node 1
- **Priority**: Low — SSH access works fine for now
- **Note**: Investigating remotely — may resolve without physical access
