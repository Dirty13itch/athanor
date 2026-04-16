# ADR-016: Remote Access via Tailscale

**Date:** 2026-02-24
**Status:** Superseded (2026-02-26) — Remote access deprioritized. Tailscale not needed.
**Research:** `docs/archive/research/2026-02-24-remote-access.md`

> **2026-02-26 Update:** Shaun decided Tailscale is not needed. Remote access is not a current requirement. If it becomes one in the future, re-evaluate from scratch — the landscape will have changed. This ADR is preserved as decision history per convention.

## Context

Shaun needs reliable remote access to the homelab from mobile and laptop. Requirements:

- SSH to all 4 nodes from anywhere
- Web dashboards (Grafana, Dashboard, Open WebUI, HA) accessible remotely
- Must work behind CGNAT (common with US residential ISPs)
- Zero exposed ports to the public internet
- One-person operable: simple to set up, debug, maintain

## Options Evaluated

1. **Tailscale** — Managed WireGuard mesh with NAT traversal
2. **Raw WireGuard** — Native on UDM Pro, best performance, but fails behind CGNAT
3. **Cloudflare Tunnel** — Outbound-only HTTP proxy, poor SSH experience
4. **Headscale** — Self-hosted Tailscale control plane, unnecessary complexity
5. **NetBird** — Open-source mesh, unreliable iOS client

Full analysis with benchmarks and sources in the research doc.

## Decision

**Tailscale with UDM Pro as subnet router.**

Install Tailscale on the UniFi Dream Machine Pro via community package ([SierraSoftworks/tailscale-udm](https://github.com/SierraSoftworks/tailscale-udm)). Advertise `192.168.1.0/24` as a subnet route. Individual nodes do NOT need Tailscale installed.

## Rationale

1. **CGNAT-proof.** Works regardless of ISP configuration. No port forwarding needed.
2. **Single install point.** One package on the UDM Pro gives access to the entire LAN. Zero software on compute nodes.
3. **Mobile SSH works.** SSH to `192.168.1.244` (or MagicDNS hostname) directly from any mobile SSH client.
4. **Zero exposed ports.** All connections are outbound from UDM Pro to Tailscale's coordination servers.
5. **Free.** Personal plan: 3 users, 100 devices. Well within limits.
6. **~30 minutes to deploy.** Install on UDM Pro, approve subnet route, install mobile app, done.

### Why not raw WireGuard?

Best performance (native on UDM Pro, ~1ms overhead) but fails completely behind CGNAT. If Shaun confirms a real public IP, raw WireGuard becomes a viable primary with Tailscale as fallback — but starting with Tailscale alone is simpler and more resilient.

## Implementation

Requires Shaun (SSH into UDM Pro, create Tailscale account):

1. Create Tailscale account at tailscale.com
2. SSH into UDM Pro: `ssh root@192.168.1.1`
3. Install: `curl -fsSL https://raw.githubusercontent.com/SierraSoftworks/tailscale-udm/main/install.sh | sh`
4. Configure: `tailscale up --advertise-routes="192.168.1.0/24" --snat-subnet-routes=false --accept-routes --reset`
5. Approve subnet route in Tailscale admin console
6. Install Tailscale on phone, sign in
7. Configure mobile SSH client hosts using 192.168.1.x IPs

**Fallback:** If UDM Pro community package breaks on firmware update, install Tailscale directly on VAULT as subnet router (5-minute recovery).

## Consequences

- Dependency on Tailscale's coordination servers (existing connections survive outages)
- Community UDM Pro package may break on firmware updates (mitigated by VAULT fallback)
- All web dashboards accessible remotely without per-service configuration
- Enables mobile monitoring and emergency response from anywhere
