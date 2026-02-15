# Network Reachability Report — 2026-02-14

Tested from DEV (192.168.1.215 via Wi-Fi).

## Summary

| Target | IP | Ping | Access Method | Status |
|--------|-----|------|---------------|--------|
| **VAULT** (Unraid) | 192.168.1.203 | OK | SSH (port 22) | **Audited** — root/password + ed25519 key installed |
| **Node 1** | 192.168.1.244 | OK | — | **No open ports** — all services down |
| **Node 1** (2nd NIC) | 192.168.1.245 | OK | — | **No open ports** — not IPMI as expected |
| **Node 2** | 192.168.1.10 | OK | Talos API (50000) | **Needs valid TLS certs** — old Kaizen certs rejected |
| **JetKVM (Node 1)** | 192.168.1.165 | OK | HTTP (80) | **Accessible** — web UI responds |
| **JetKVM (VAULT)** | 192.168.1.80 | OK | HTTP (80) | **Accessible** — web UI responds |

## Detail

### VAULT (192.168.1.203)

- **AUDITED** — see vault-audit-2026-02-14.md
- IP was .139 pre-boot, changed to .203 after full boot (DHCP or config change)
- SSH key installed, password auth confirmed working
- Unraid 7.2.0, Threadripper 7960X, 128 GB DDR5, 164 TB array

### Node 1 (192.168.1.244 / .245)

- .244 = Talos OS (pings, no open ports — Talos API not running on this node)
- .245 = IPMI (ASRock Rack ROMED8-2T BMC). Pings at 170ms but no HTTP/HTTPS/623 ports open during this session. BMC may need full power cycle to boot properly.
- JetKVM at 192.168.1.165 confirmed working — used to read Talos dashboard
- Shaun has "Core IPMI" bookmark — exact IP TBD (likely .245)
- **Next session:** After clean reboot, try IPMI at .245 again (HTTPS + port 623)

### Node 2 (192.168.1.10)

- Talos API (port 50000) was intermittently responding — went unreachable later in session
- Talos config: IP 10.10.10.10/24 with dual gateways, controlplane role
- IPMI reportedly at 192.168.1.65 — completely unreachable (no ping). ASUS ProArt boards typically lack built-in IPMI, so this may be a separate device that's powered off or disconnected.
- Kaizen talosconfig certs are valid (not expired) but fail with Ed25519 verification error on Windows. Worked partially from VAULT (connected but timed out reaching node).
- **Next session:** After clean reboot, try IPMI at .65 and talosctl from DEV/VAULT

### JetKVMs

Both JetKVMs respond on HTTP — these are the remote KVM units attached to Node 1 and VAULT. They provide screen/keyboard/mouse access to the physical consoles.

- **JetKVM Node 1** — http://192.168.1.165 — can see Node 1's console
- **JetKVM VAULT** — http://192.168.1.80 — can see VAULT's console

## Talos CLI

- `talosctl` v1.12.4 is installed at `C:\Users\Shaun\bin\talosctl`
- No `~/.talos/` config directory exists
- Old config at `C:\Users\Shaun\kaizen-core\talosconfig` — empty endpoints, stale certs
- Config was generated for cluster "kaizen-core"

## What We Can Audit Right Now

1. **DEV** — fully audited (see dev-audit-2026-02-14.md)
2. **JetKVM screens** — visible via browser but can't extract hardware data programmatically

## What Needs Shaun's Help

1. **VAULT** — provide root SSH password, or set up SSH key auth
2. **Node 1** — check JetKVM screen at http://192.168.1.165 to see what state it's in
3. **Node 2** — either provide valid Talos certs or confirm we can wipe it
