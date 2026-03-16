# ADR: Remote Mobile Access to Command Center

## Status: Proposed

## Context
Shaun needs always-on mobile access to the Command Center (workshop:3001) when away from home. Requirements:
- Zero maintenance — never turn anything on/off
- Works as a phone app/shortcut
- Self-hosted (no cloud dependency)

## Decision
**Headscale + Tailscale client + PWA**

### Architecture
1. **Headscale** (VAULT container) — self-hosted Tailscale-compatible coordination server
2. **Tailscale client** on each node (VAULT, WORKSHOP, FOUNDRY, DEV)
3. **Tailscale app** on phone — set to "Always On VPN" in OS settings
4. **PWA shortcut** on phone home screen → `http://workshop:3001`

### Why Headscale over alternatives
| Option | Self-hosted | Zero maintenance | No port forward | Works behind CGNAT |
|--------|------------|-----------------|-----------------|-------------------|
| Headscale + Tailscale | Yes | Yes | Yes | Yes |
| WireGuard | Yes | Mostly | No (needs port forward) | No |
| Cloudflare Tunnel | No (SaaS) | Yes | Yes | Yes |
| Tailscale (cloud) | No (SaaS coord) | Yes | Yes | Yes |

Headscale is the only option that is fully self-hosted AND requires no port forwarding or DDNS.

### Implementation
1. Deploy Headscale container on VAULT
2. Register VAULT, WORKSHOP as nodes via `tailscale up --login-server=http://vault:8080`
3. Install Tailscale on phone, point to Headscale
4. Enable "Always On VPN" in phone settings
5. Open workshop:3001 in phone browser, "Add to Home Screen"

### Consequences
- All traffic between phone and home goes through encrypted WireGuard tunnel
- Phone can access any home service (dashboard, EoBQ, ComfyUI, Grafana)
- Headscale needs to be accessible from the internet — requires ONE port forward (UDP 41641) or DERP relay
- Alternative: use Headscale's built-in DERP relay (no port forward, slight latency increase)

## Blocked On
- Shaun to decide if port forwarding is acceptable or DERP relay preferred
