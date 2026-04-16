# Blocked Tasks

> **Status:** Archive only.
> **Current blocker truth is tracked here:** [`STATUS.md`](../../STATUS.md), [`scripts/session_restart_brief.py --refresh`](../../scripts/session_restart_brief.py), [`reports/truth-inventory/finish-scoreboard.json`](../../reports/truth-inventory/finish-scoreboard.json), [`reports/truth-inventory/runtime-packet-inbox.json`](../../reports/truth-inventory/runtime-packet-inbox.json), and [`docs/operations/CONTINUOUS-COMPLETION-BACKLOG.md`](../operations/CONTINUOUS-COMPLETION-BACKLOG.md)
> **Purpose:** preserve historical blocked-task context from earlier sessions without presenting the current operator queue or current approval-gated runtime inbox.

*Updated: 2026-03-14 (Session 56)*

Tasks that could not proceed in that earlier session without Shaun's physical presence, credentials, or browser access. They are historical blocker examples, not the live closure queue or current runtime packet set.

---

## Credentials Needed

### NordVPN Service Credentials
- **What**: Updated NordVPN token or service credentials for Gluetun VPN container
- **Blocks**: qBittorrent + Gluetun VPN deployment (compose file ready)
- **Priority**: Medium — media acquisition stack incomplete without it

### Anthropic API Key
- **What**: API key for cloud escalation in Quality Cascade
- **Blocks**: 8.5 (Quality Gating & Cascade — local → cloud auto-escalation)
- **Priority**: P1 — enables autonomous coding quality loops

### HuggingFace Token (optional)
- **What**: HF token for gated model access
- **Blocks**: Full-precision Flux dev model download (FP8 version already working)
- **Priority**: Low

---

## OAuth / Auth Flows

### Google Drive rclone OAuth
- **What**: Run `~/.local/bin/rclone config` on DEV to complete OAuth flow
- **Blocks**: 10.8 (Personal Data ~40% — Google Drive sync)
- **Priority**: Medium — unlocks significant personal data corpus

---

## Physical Rack Session (~15 min)

### Samsung 990 PRO 4TB (Node 1)
- **What**: Verify physical seat of NVMe drive or check BIOS M.2 slot settings
- **Blocks**: 4TB additional local storage on Node 1
- **Priority**: Medium

### BIOS: Enable EXPO (Node 2)
- **What**: Enable DDR5 EXPO profile in BIOS (3600 → 5600 MT/s)
- **Blocks**: Full memory bandwidth on Node 2
- **Priority**: Low — functional at 3600, performance improvement only

---

## Network Access

### Enable OpenSSH on DESK (.215)
- **What**: Enable OpenSSH Server on Windows 11 (`Settings > Apps > Optional Features > Add OpenSSH Server`) or expose WSL SSH
- **Blocks**: Cross-node session recovery, remote tmux access, claude-squad management from DEV
- **Priority**: P1 — DEV needs to reach all nodes for full ops center role

---

## Software Blockers

### Photo Analysis (VLM)
- **What**: Qwen3.5 multimodal support requires vLLM 0.17+ (currently nightly)
- **Blocks**: 10.10 (Photo Analysis — VLM-powered descriptions, EXIF extraction)
- **Priority**: P2 — waiting on upstream vLLM release

---

## Resolved (removed from active list)

| Item | When | How |
|------|------|-----|
| 5GbE Switch Migration | Session 12, 2026-02-24 | Cables moved, iperf3 verified 9.4+ Gbps |
| JetKVM ATX Power Cable | Session 3, 2026-02-16 | Reconnected during rack work |
| HA Onboarding | Session 13, 2026-02-24 | Completed in browser, 38 entities discovered |
| BMC Config (.216) | — | Deprioritized — SSH access sufficient for all current tasks |
| VAULT SSH (root key auth) | Session 56, 2026-03-14 | DEV ed25519 key added to VAULT authorized_keys (runtime + persistent `/boot/config/ssh/`). `ssh root@192.168.1.203` and `vault-ssh.py` both working. Docker MCP for VAULT functional (44 containers visible). |

---

## Purchases (Backlog)

| Item | Est. Cost | Blocks | Priority |
|------|-----------|--------|----------|
| Mining GPU enclosure (6-8 slot) | ~$100-200 | Phase 8 Node 1 → 6 GPU build | Backlog |
| Add2PSU adapter | ~$10-15 | Dual PSU sync for 6-GPU build | Backlog |
| PCIe riser cables (6x) | ~$30-50 | 6-GPU build | Backlog |
| 2x Mellanox ConnectX-3 FDR | ~$60 | InfiniBand inter-node link | Backlog |
| 1x QSFP+ FDR cable | ~$15 | InfiniBand inter-node link | Backlog |
