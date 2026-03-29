# ADR: Remote Mobile Access to Command Center

## Status: Ready to implement

## Context
Shaun needs always-on mobile access to the Athanor Command Center (`https://athanor.local/`) when away from home. The canonical front door is now live on DEV behind Caddy; the remaining client-side gap is hostname rollout, so the temporary runtime fallback stays `http://dev.athanor.local:3001/` until every operator device resolves the canonical host. Requirements:
- Zero maintenance — never turn anything on/off
- Works as a phone app/shortcut
- Self-hosted (no cloud dependency)

## Decision
**UDM Pro WireGuard VPN + PWA**

The UDM Pro already has a built-in WireGuard VPN server. No additional software needed.

### Setup Steps
1. **UDM Pro**: Settings → VPN → WireGuard Server
   - Enable WireGuard server
   - Set DNS to local DNS or 1.1.1.1
   - Create a client profile for phone
   - Download/export the `.conf` file
2. **Phone**: Install WireGuard app (iOS/Android)
   - Import the `.conf` file (scan QR or file transfer)
   - Enable "Always On VPN" in phone OS settings:
     - Android: Settings → Network → VPN → WireGuard → Always On
     - iOS: Settings → VPN → WireGuard → Connect On Demand → enable for all networks
3. **PWA**: Open `https://athanor.local/` in phone browser
   - If the current client still lacks the `athanor.local` host alias, use `http://dev.athanor.local:3001/` as the temporary runtime fallback
   - iOS: Share → Add to Home Screen
   - Android: Menu → Add to Home Screen / Install App
   - App installs with Athanor icon, opens standalone (no browser chrome)

### Why This Over Alternatives
| Option | Extra software | Port forward | Self-hosted | Complexity |
|--------|---------------|-------------|-------------|------------|
| **UDM Pro WireGuard** | None | Auto-managed by UDM | Yes | Low |
| Headscale + Tailscale | Headscale container + Tailscale on nodes | No | Yes | Medium |
| Plain WireGuard on VAULT | WireGuard server | Manual | Yes | Medium |
| Cloudflare Tunnel | cloudflared container | No | No (SaaS) | Low |

UDM Pro is the clear winner — zero new software, auto-managed port forwarding, hardware Shaun already owns.

### Network Details
- UDM Pro handles NAT traversal and dynamic DNS automatically
- UniFi's built-in DDNS: `*.ui.direct` (optional, or use custom domain)
- WireGuard uses UDP 51820 (auto-opened by UDM Pro firewall)
- All home services accessible through the tunnel: `athanor.local`, DEV command-center runtime `dev.athanor.local:3001`, EoBQ:3002, Grafana:3000, ComfyUI:8188

### Consequences
- Phone always has secure, encrypted access to entire home LAN
- No additional containers, no maintenance, no subscription
- PWA on home screen = opens like native app, receives push notifications
- Battery impact: WireGuard is extremely efficient (< 1% battery per day)

## Implementation
Shaun task: enable WireGuard server on UDM Pro, create phone client profile.
