# Remote Access for Athanor Homelab

**Date:** 2026-02-24
**Status:** Research complete, recommendation ready
**Author:** Research Agent

---

## Context

Athanor is a 4-node homelab (3 Linux servers + 1 Windows/WSL2 workstation) on a flat 192.168.1.0/24 subnet behind a UniFi Dream Machine Pro. The operator (Shaun) needs reliable remote access for:

- SSH to all nodes from mobile and laptop
- Web dashboards: Grafana (:3000 on VAULT), Dashboard (:3001 on Node 2), Open WebUI (:3000 on Node 2), Home Assistant (:8123 on VAULT)
- Must work behind CGNAT or changing IPs (common with US residential ISPs)
- One-person operation: simple to set up, debug, and maintain
- Minimal attack surface (no exposed ports to the public internet)

### CGNAT Detection

Before choosing a solution, verify whether Shaun's ISP uses CGNAT:

1. Log into UDM Pro at 192.168.1.1 -> Settings -> Internet -> check WAN IP
2. Visit https://whatismyip.com from any device on the LAN
3. If the WAN IP and public IP **differ**, the ISP uses CGNAT
4. If the WAN IP starts with `100.64.x.x` through `100.127.x.x`, that is CGNAT address space

This matters because raw WireGuard and UDM Pro's built-in VPN server both require a reachable public IP. Tailscale, Cloudflare Tunnel, and NetBird work regardless of CGNAT.

---

## Options Evaluated

### 1. Tailscale (Managed WireGuard Mesh)

**What it is:** A managed overlay network built on WireGuard. Tailscale handles key exchange, NAT traversal, and coordination. Traffic flows peer-to-peer when possible; falls back to DERP relay servers when NAT traversal fails.

**Setup complexity:** Low. Install the client on each device (or one subnet router), authenticate via SSO. No firewall rules, no port forwarding, no certificates to manage. Takes 15-30 minutes for a full homelab.

**CGNAT compatibility:** Excellent. Tailscale's NAT traversal achieves direct P2P connections >90% of the time in typical conditions. When traversal fails (symmetric NAT behind CGNAT), DERP relays provide guaranteed connectivity. Works on every ISP configuration including double NAT and CGNAT.

**UDM Pro support:** Yes, via community package [SierraSoftworks/tailscale-udm](https://github.com/SierraSoftworks/tailscale-udm). As of January 2025, the package switched to kernel-mode (TUN) networking by default, enabling subnet route advertising. Configuration:

```bash
# Install on UDM Pro (SSH into it)
curl -fsSL https://raw.githubusercontent.com/SierraSoftworks/tailscale-udm/main/install.sh | sh

# Advertise entire LAN as subnet route
tailscale up --advertise-routes="192.168.1.0/24" --snat-subnet-routes=false --accept-routes --reset
```

Then approve the routes in the Tailscale admin console. This means individual nodes do NOT need Tailscale installed -- the UDM Pro acts as the gateway. One install point, one thing to maintain.

**Important caveat:** The tailscale-udm package is community-maintained (not Ubiquiti or Tailscale official). UniFi OS firmware updates can break it, requiring reinstallation. The package uses systemd on UniFi OS 2.x+ and survives reboots, but major firmware upgrades need testing.

**Mobile client support:** Excellent. Native iOS and Android apps, well-maintained, reliable. SSH to the Tailscale IP (100.x.y.z) or MagicDNS hostname from any mobile SSH client.

**MagicDNS / Split DNS:** Tailscale's MagicDNS automatically assigns DNS names to all devices (e.g., `node1.tailnet-name.ts.net`). Split DNS can route queries for a custom domain (e.g., `*.athanor.local`) to an internal DNS server through the Tailscale tunnel. This means you can access `grafana.athanor.local:3000` from your phone without remembering IPs.

**Performance overhead:**
- Direct P2P connection: 1-3ms added latency (WireGuard encryption only)
- DERP relay: 15-80ms added latency depending on relay location
- Throughput: Linux kernel mode achieves near-wire-speed. Tailscale has demonstrated >10 Gbps on Linux with kernel optimizations.
- SSH feels identical to local for direct connections. Relay connections add noticeable but usable latency.

**Subnet router performance:** On Linux with kernel mode, subnet routing overhead is ~13% throughput reduction in typical configurations. The UDM Pro's ARM processor handles this fine for the bandwidth levels involved (SSH, web dashboards, not bulk transfers).

**Monthly cost:** $0. The free Personal plan includes 3 users and 100 devices. A one-person homelab with ~10 devices is well within limits. The free plan includes subnet routers, MagicDNS, ACLs, and all features relevant here. If Shaun wants to share access with Amanda (e.g., HA dashboard), that is user #2 of 3.

**Risks and maintenance burden:**
- Dependency on Tailscale's coordination servers (if they go down, existing connections persist but new ones cannot be established)
- Community UDM Pro package may break on firmware updates
- Tailscale the company could change free tier terms (though they have [publicly committed](https://tailscale.com/blog/free-plan) to keeping it free for personal use)
- Minimal maintenance: auto-updates on most platforms, keys auto-rotate

---

### 2. Raw WireGuard (Self-Hosted)

**What it is:** Direct WireGuard tunnel with manual key management and configuration. The UDM Pro has native WireGuard VPN server support in UniFi OS 4.x / Network 8.x.

**Setup complexity:** Medium. The UDM Pro's built-in WireGuard server provides a UI-based setup (Settings -> VPN -> WireGuard). Generate client configs, export QR codes for mobile. More setup than Tailscale but well-documented.

**CGNAT compatibility:** FAILS. WireGuard requires a reachable endpoint. If Shaun's ISP uses CGNAT, the UDM Pro's WAN IP is not publicly routable, and WireGuard connections from outside cannot reach it. DDNS does not help because the issue is routability, not name resolution. IPv6 could work if available, but many US ISPs don't provide it on residential connections.

**UDM Pro support:** Native. Built into UniFi OS since ~2023. No third-party packages needed. Configure entirely through the UniFi web interface. This is the cleanest integration of any option.

**Mobile client support:** Good. Official WireGuard app on iOS and Android. Import config via QR code. WireGuard runs as a system VPN, then SSH normally through any SSH client.

**Performance overhead:** Lowest of any option. WireGuard kernel module adds ~1ms latency and negligible throughput overhead. No relay servers, no coordination layer. Direct encrypted tunnel.

**Monthly cost:** $0. Entirely self-hosted.

**Risks and maintenance burden:**
- **Blocked by CGNAT** -- this is a showstopper if the ISP uses CGNAT
- Requires a static IP or working DDNS for the WAN address
- Key rotation is manual (no automatic key management)
- If UDM Pro reboots and gets a new WAN IP, clients need updated configs (unless DDNS is configured)
- No NAT traversal -- only works with direct routability
- No MagicDNS -- must use raw IPs or maintain your own DNS

---

### 3. Cloudflare Tunnel (HTTP/S Zero-Trust Proxy)

**What it is:** An outbound-only tunnel from your network to Cloudflare's edge. Cloudflare proxies inbound requests to your services. Primarily designed for HTTP/S services. SSH support exists but requires either browser-based terminal or cloudflared on the client side.

**Setup complexity:** Medium. Requires a domain name on Cloudflare (free). Install `cloudflared` daemon on one server, create tunnel, map hostnames to services. Each web service needs its own public hostname (e.g., `grafana.yourdomain.com`, `ha.yourdomain.com`).

**CGNAT compatibility:** Excellent. `cloudflared` makes outbound-only connections to Cloudflare's edge. Works behind any NAT, CGNAT, firewall, or restrictive network.

**UDM Pro support:** Not applicable. `cloudflared` runs on a Linux server, not on the UDM Pro. You would install it on VAULT or Node 1.

**Mobile client support:** Mixed.
- **Web dashboards:** Excellent. Access via any browser with Cloudflare Access authentication. No app needed.
- **SSH:** Poor for daily use. Two options: (a) browser-based SSH terminal (laggy), or (b) install `cloudflared` on the client device as a proxy, then SSH through it. Neither is a clean mobile SSH experience.

**Performance overhead:**
- All traffic routes through Cloudflare's edge (15-45ms added latency depending on proximity)
- No peer-to-peer connections -- every packet goes through Cloudflare
- SSH feels noticeably slower than local, especially for interactive use
- Web dashboards are fine -- the latency is acceptable for HTTP

**Monthly cost:** $0 for free tier (50 tunnels, unlimited bandwidth). Requires a domain ($10-15/year for a .com if Shaun doesn't already have one).

**TOS considerations:** Cloudflare [updated their TOS](https://blog.cloudflare.com/updated-tos/) to move the old Section 2.8 content restriction to a CDN-specific section. Tunnel usage for non-CDN traffic (SSH, web apps) appears to be permitted. However, streaming video (e.g., Plex) through a Cloudflare Tunnel remains in a grey area -- the restriction now applies specifically to CDN-cached content, but community consensus is to avoid high-bandwidth media streaming through free tunnels.

**Risks and maintenance burden:**
- SSH workflow is clunky -- not a good fit for mobile SSH usage
- Every service needs explicit hostname mapping (no blanket LAN access)
- Cloudflare sees all your traffic (unencrypted at their edge)
- Domain name required
- `cloudflared` process must stay running; if it crashes, all remote access is lost
- No LAN-wide access (each service exposed individually)

---

### 4. Headscale (Self-Hosted Tailscale Control Plane)

**What it is:** An open-source reimplementation of Tailscale's coordination server. Uses standard Tailscale clients but replaces Tailscale's cloud infrastructure with your own server.

**Setup complexity:** High. Requires:
- A server with a public IP (VPS or home server with port forwarding) to run the Headscale control plane
- DNS configuration and TLS certificates
- Docker or bare-metal deployment of Headscale
- Manual ACL configuration (YAML files instead of Tailscale's web UI)
- Client configuration requires entering custom control server URL (hidden in debug menus on mobile)

**CGNAT compatibility:** Problematic. Headscale itself needs a publicly reachable IP to serve as the control plane. If Shaun's home connection is behind CGNAT, he would need a VPS ($5-10/month) to host Headscale. The embedded DERP server also needs to be reachable. This largely defeats the purpose vs. just using Tailscale's free tier.

**UDM Pro support:** Same as Tailscale (community tailscale-udm package), but client configuration is more complex because you must specify the custom control server URL.

**Mobile client support:** Uses standard Tailscale clients with modified control server. iOS client requires navigating to a hidden debug menu to change the control server URL. Works, but onboarding is fiddly.

**Performance overhead:** Identical to Tailscale for data plane (same WireGuard protocol, same client). Control plane latency depends on where you host Headscale.

**Monthly cost:** $0 if self-hosted at home (but requires public IP). $5-10/month for a VPS if behind CGNAT.

**Risks and maintenance burden:**
- Single point of failure (your Headscale server). If it goes down, no new connections can be established.
- You are responsible for updates, security patches, TLS certificate renewal, and backups
- Missing features vs. Tailscale: no Funnel, no Serve, no network flow logs, no dynamic ACLs
- The Headscale project, while active (0.26+), is maintained by a small team
- [XDA article](https://www.xda-developers.com/headscale-instead-of-tailscale-brings-headaches/): "I switched to Headscale instead of Tailscale, but most people probably shouldn't"
- For a one-person homelab, this adds operational burden with no meaningful benefit over Tailscale's free tier

---

### 5. NetBird (Open-Source WireGuard Mesh)

**What it is:** Open-source WireGuard-based mesh VPN with zero-trust networking features. Similar to Tailscale conceptually but fully open-source (Apache 2.0). Can be self-hosted or used as a managed service.

**Setup complexity:** Medium. Managed service is similar to Tailscale (install client, authenticate). Self-hosted requires deploying the management server, STUN/TURN servers, and signal server.

**CGNAT compatibility:** Good. Uses ICE protocol (same as WebRTC) for NAT traversal. Falls back to TURN relay servers. Supports QUIC and WebSocket transports for restrictive networks.

**UDM Pro support:** No native or community package for UDM Pro. Would need to install NetBird on individual nodes or a dedicated Linux box as a gateway.

**Mobile client support:** Weak. The iOS app has been described as "the single least reliable application" by users, with reported issues including:
- Background disconnections
- Battery drain
- Crashes and hangs
- Version lag (iOS client significantly behind desktop releases, e.g., 0.45.1 beta vs 0.51.2 current)
- Android app is better but still has reported stability issues

This is a significant concern for mobile-first remote access.

**Subnet routing:** Supported ("Subnet Gateway" feature), but requires a Linux host as the gateway -- cannot run on UDM Pro.

**Performance overhead:** Similar to Tailscale (WireGuard-based). Direct connections are fast; relay connections add latency.

**Monthly cost:** $0 for managed service (5 users, 100 devices on free tier). $0 for self-hosted (unlimited).

**Risks and maintenance burden:**
- Mobile app quality is a real problem for a mobile-first use case
- Smaller community than Tailscale (though growing -- $10M Series A in Jan 2026)
- No UDM Pro integration means more devices to manage
- Self-hosted option adds significant operational overhead
- Younger project with fewer battle-tested deployments

---

## Comparison Matrix

| Criterion | Tailscale | Raw WireGuard | Cloudflare Tunnel | Headscale | NetBird |
|-----------|-----------|---------------|-------------------|-----------|---------|
| **Setup time** | 15-30 min | 30-60 min | 45-90 min | 2-4 hours | 30-60 min |
| **CGNAT compatible** | Yes | **NO** | Yes | Needs VPS | Yes |
| **UDM Pro support** | Community pkg | Native | N/A (runs on server) | Community pkg | No |
| **Subnet router on UDM Pro** | Yes (kernel mode) | N/A (native VPN) | No (per-service) | Yes (kernel mode) | No |
| **Mobile SSH** | Excellent | Good | Poor | OK (fiddly setup) | Poor (unstable app) |
| **Mobile web dashboards** | Excellent | Good | Excellent | OK | Poor |
| **SSH latency overhead** | 1-3ms (direct) | ~1ms | 15-45ms | 1-3ms (direct) | 1-3ms (direct) |
| **MagicDNS / auto naming** | Yes | No | Via hostnames | Limited | Yes |
| **Monthly cost** | $0 | $0 | $0 + domain | $0-10 | $0 |
| **Attack surface** | None (no open ports) | 1 port (51820) | None (outbound only) | 1+ ports on VPS | None (outbound only) |
| **Maintenance burden** | Minimal | Low | Medium | High | Medium |
| **LAN-wide access** | Yes (subnet route) | Yes (split tunnel) | No (per-service) | Yes (subnet route) | Yes (subnet gw) |
| **Vendor lock-in risk** | Medium (proprietary control) | None | Medium (Cloudflare) | None (open source) | Low (open source) |
| **Survives firmware update** | Community pkg may break | Native (survives) | N/A | Community pkg may break | N/A |
| **Plex/media streaming** | Fine (direct WG) | Fine (direct WG) | TOS grey area | Fine (direct WG) | Fine (direct WG) |

---

## Specific Questions Answered

### Can Tailscale run on UDM Pro as a subnet router?

**Yes.** The [SierraSoftworks/tailscale-udm](https://github.com/SierraSoftworks/tailscale-udm) community package installs Tailscale on UniFi OS 2.x+ devices. As of January 2025, it defaults to kernel-mode (TUN) networking, which enables subnet route advertising. You run `tailscale up --advertise-routes="192.168.1.0/24"` and approve the route in the Tailscale admin console. After that, any Tailscale client can reach any device on 192.168.1.0/24 through the UDM Pro without installing Tailscale on individual nodes.

**Caveats:**
- Community-maintained, not officially supported by Ubiquiti or Tailscale
- Major UniFi OS firmware updates may require reinstallation
- Survives reboots (systemd service) but not guaranteed across firmware upgrades
- The UDM Pro's ARM CPU handles subnet routing fine for SSH/web traffic but would bottleneck on sustained high-bandwidth transfers

**Mitigation for firmware breakage:** If the community package breaks, install Tailscale directly on one Linux node (e.g., VAULT, since it's always on) as a fallback subnet router. This is a 5-minute recovery.

### Does Tailscale's free tier cover this use case?

**Yes, completely.** The free Personal plan includes:
- 3 users (Shaun + Amanda + 1 spare)
- 100 devices (this homelab uses ~5-10)
- Subnet routers, MagicDNS, ACLs, key rotation
- All features except enterprise admin controls

Tailscale has [publicly stated](https://tailscale.com/blog/free-plan) that the personal free plan will remain free. If Shaun ever needs a 4th user, the Personal Plus plan is $5/month for 6 users.

### Is there a way to use WireGuard on UDM Pro without third-party firmware?

**Yes.** UniFi OS 4.x / Network 8.x includes a native WireGuard VPN server. It is configured entirely through the UniFi web interface: Settings -> VPN -> Create New -> WireGuard. Client configs can be exported as QR codes for mobile. No third-party firmware or packages needed.

**However:** This only works if the UDM Pro has a publicly reachable IP. If the ISP uses CGNAT, native WireGuard is unusable for inbound connections. DDNS solves the changing-IP problem but not the CGNAT problem.

### What's the latency overhead for SSH over Tailscale vs raw WireGuard?

| Scenario | Added Latency | Notes |
|----------|--------------|-------|
| Raw WireGuard (direct) | ~1ms | Kernel-mode encryption only |
| Tailscale (direct P2P) | 1-3ms | WireGuard + coordination overhead |
| Tailscale (DERP relay) | 15-80ms | Varies by relay proximity; typical US = 20-40ms |
| Cloudflare Tunnel SSH | 15-45ms | Always proxied through edge |

For interactive SSH, anything under 50ms is indistinguishable from local for typing. The 1-3ms difference between raw WireGuard and Tailscale direct is imperceptible. DERP relay adds noticeable latency but is still usable for SSH. The relay fallback occurs <10% of the time in typical US residential configurations.

---

## Recommendation

**Primary: Tailscale with UDM Pro as subnet router.**

Rationale:

1. **CGNAT-proof.** Works regardless of ISP configuration. No need to know or care whether the ISP uses CGNAT, changes IPs, or blocks ports.

2. **Single install point.** Tailscale on the UDM Pro as a subnet router means zero software to install or maintain on Node 1, Node 2, VAULT, or DEV. One package, one device, entire LAN accessible.

3. **Mobile SSH is seamless.** SSH to `node1` by MagicDNS name or Tailscale IP from any mobile SSH client.

4. **Zero exposed ports.** No port forwarding, no public endpoints, no firewall holes. All connections are outbound from the UDM Pro to Tailscale's coordination servers.

5. **Free.** The Personal plan covers everything needed. No VPS, no domain name, no subscription.

6. **Web dashboard access.** Connect to Tailscale on phone/laptop, then browse to `192.168.1.203:3000` (Grafana), `192.168.1.225:3001` (Dashboard), etc. With MagicDNS + split DNS, these could become `grafana.athanor.local`, `dashboard.athanor.local`, etc.

7. **One-person operable.** Setup is 15-30 minutes. No keys to rotate manually, no certificates to renew, no VPS to maintain. If something breaks, `tailscale status` tells you what. The debugging surface is small.

**Fallback plan:** If the community UDM Pro package breaks on a firmware update, install Tailscale directly on VAULT (always-on Unraid box) as a subnet router. Takes 5 minutes, identical functionality, just runs on VAULT instead of the gateway.

### Why not the others?

- **Raw WireGuard:** Best performance and simplest architecture, but fails completely behind CGNAT. If Shaun confirms his ISP provides a real public IP, this becomes a viable alternative (and is already built into the UDM Pro). But it is fragile against ISP changes -- many US ISPs are moving to CGNAT.
- **Cloudflare Tunnel:** Great for exposing web services publicly, but poor SSH experience. Also requires per-service configuration (no blanket LAN access) and puts Cloudflare in the middle of all traffic.
- **Headscale:** All the operational burden of self-hosting with no benefit over Tailscale's free tier for a one-person homelab. The XDA article summarizes it well: "most people probably shouldn't."
- **NetBird:** Promising technology but iOS app instability is a dealbreaker for mobile-first remote access. Worth revisiting in 12-18 months as the product matures post-Series A.

### Implementation Steps

1. **Check CGNAT status** (5 min): Compare UDM Pro WAN IP with whatismyip.com result. This determines whether raw WireGuard is even an option.

2. **Create Tailscale account** (2 min): Sign up at tailscale.com with personal email.

3. **Install Tailscale on UDM Pro** (10 min):
   ```bash
   # SSH into UDM Pro
   ssh root@192.168.1.1

   # Install tailscale-udm
   curl -fsSL https://raw.githubusercontent.com/SierraSoftworks/tailscale-udm/main/install.sh | sh

   # Authenticate and advertise subnet
   tailscale up --advertise-routes="192.168.1.0/24" --snat-subnet-routes=false --accept-routes --reset
   # Follow the auth URL printed to terminal
   ```

4. **Approve subnet route** (2 min): Go to Tailscale admin console -> Machines -> UDM Pro -> approve route for 192.168.1.0/24.

5. **Install Tailscale on phone** (5 min): Download from App Store / Play Store, sign in with same account.

6. **Configure mobile SSH client** (5 min): Add hosts using 192.168.1.x IPs (accessible via subnet route). Test SSH to each node.

7. **Optional: Configure MagicDNS** (10 min): In Tailscale admin console -> DNS -> enable MagicDNS. Optionally configure split DNS for a custom domain pointing to an internal DNS server.

8. **Optional: Install on DEV as backup** (5 min): Install Tailscale on the WSL2 instance so DEV is directly reachable even when away from home, independent of the UDM Pro subnet route.

Total setup time: ~30-40 minutes for full deployment.

---

## Hybrid Option Worth Considering

If Shaun confirms he has a real public IP (no CGNAT), the optimal setup might be:

- **UDM Pro native WireGuard** as primary (zero maintenance, survives firmware updates, best performance)
- **Tailscale on VAULT** as fallback (in case ISP switches to CGNAT in the future, or for scenarios where WireGuard is blocked by network policy)

This provides the reliability of native WireGuard with the CGNAT insurance of Tailscale. But this is two systems to understand and maintain, which conflicts with the one-person-scale principle. Start with Tailscale alone; add native WireGuard only if there is a concrete need.

---

## Sources

- [SierraSoftworks/tailscale-udm - GitHub](https://github.com/SierraSoftworks/tailscale-udm) -- Community package for running Tailscale on UDM Pro
- [Tailscale Pricing](https://tailscale.com/pricing) -- Free Personal plan: 3 users, 100 devices
- [How Tailscale's free plan stays free](https://tailscale.com/blog/free-plan) -- Tailscale's commitment to free personal tier
- [Tailscale NAT traversal improvements](https://tailscale.com/blog/nat-traversal-improvements-pt-1) -- >90% direct P2P success rate
- [Tailscale Performance best practices](https://tailscale.com/kb/1320/performance-best-practices) -- Kernel vs userspace, throughput optimization
- [Kernel vs. netstack subnet routing](https://tailscale.com/kb/1177/kernel-vs-userspace-routers/) -- Performance comparison for subnet routers
- [Tailscale MagicDNS](https://tailscale.com/kb/1081/magicdns) -- Automatic DNS naming for devices
- [Tailscale Split DNS](https://tailscale.com/learn/why-split-dns) -- Route internal DNS queries through tunnel
- [Surpassing 10Gb/s with Tailscale](https://tailscale.com/blog/more-throughput) -- Linux kernel mode performance
- [UniFi Gateway WireGuard VPN Server - Ubiquiti Help Center](https://help.ui.com/hc/en-us/articles/115005445768-UniFi-Gateway-WireGuard-VPN-Server) -- Native WireGuard on UniFi
- [UDM Pro as WireGuard VPN server (2025)](https://www.nodinrogers.com/post/2025-07-22-wireguard-vpn-server/) -- Updated setup guide
- [Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) -- Official documentation
- [Cloudflare SSH via Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/) -- SSH access methods
- [Cloudflare TOS update (goodbye Section 2.8)](https://blog.cloudflare.com/updated-tos/) -- Updated content restrictions
- [Headscale - GitHub](https://github.com/juanfont/headscale) -- Self-hosted Tailscale control plane
- [I switched to Headscale instead of Tailscale, but most people probably shouldn't - XDA](https://www.xda-developers.com/headscale-instead-of-tailscale-brings-headaches/) -- Honest assessment of Headscale tradeoffs
- [Headscale vs Tailscale: The Self-Hosting Trade-Off](https://imdmonitor.com/headscale-vs-tailscale-the-self-hosting-trade-off-20251026/) -- Feature and operational comparison
- [NetBird - GitHub](https://github.com/netbirdio/netbird) -- Open-source WireGuard mesh
- [NetBird iOS client issues - Forum](https://forum.netbird.io/t/state-of-ios-client/132/1) -- User reports of iOS app instability
- [NetBird $10M Series A - Tech.eu](https://tech.eu/2026/01/13/netbird-announces-10m-series-a-to-expand-open-source-vpn-alternative/) -- Funding and growth
- [Tailscale + tmux on iPhone](https://petesena.medium.com/how-to-run-claude-code-from-your-iphone-using-tailscale-termius-and-tmux-2e16d0e5f68b) -- Mobile SSH workflow
- [WireGuard vs Tailscale performance - Contabo](https://contabo.com/blog/wireguard-vs-tailscale/) -- Benchmark comparison
- [Cloudflare Tunnel vs ngrok vs Tailscale - DEV Community](https://dev.to/mechcloud_academy/cloudflare-tunnel-vs-ngrok-vs-tailscale-choosing-the-right-secure-tunneling-solution-4inm) -- Latency comparison
- [CGNAT detection methods - PureVPN](https://www.purevpn.com/blog/how-to-check-whether-or-not-your-isp-performs-cgnat/) -- How to check for CGNAT
