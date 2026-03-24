# ADR-013: Security Architecture

**Date:** 2026-02-24
**Status:** Accepted
**Depends on:** ADR-002 (Network Architecture), ADR-001 (Base Platform)

---

## Context

Athanor hosts uncensored AI models and adult content on hardware that may eventually be remotely accessible. Security must be baked in from the start, but this is a one-person homelab — the security model must be operationally simple. Enterprise-grade solutions are wrong here. Pragmatic, layered, and maintainable is the target.

---

## Threat Model

### What we're protecting against:

- Someone on the LAN querying uncensored models without authorization
- A compromised IoT device pivoting to inference endpoints
- An exposed service on the internet being discovered by scanners
- Secrets (API keys, VPN credentials) leaking through git or Docker Compose files

### What we're NOT designing for:

- Nation-state actors
- Insider threats (it's one person)
- Five nines of security compliance

---

## Decision

### Four-layer defense with VLAN segmentation as the backbone.

#### Layer 1: Network Boundary

- UniFi firewall blocks ALL inbound traffic except WireGuard (UDP 51820)
- **No port forwarding to any internal service — ever**
- All remote access tunnels through WireGuard to VAULT
- WireGuard clients get routed to the SERVICES VLAN only — they cannot reach INFERENCE or MGMT VLANs directly

```ini
# /etc/wireguard/wg0.conf on VAULT
[Interface]
Address = 10.10.50.1/24
ListenPort = 51820
PrivateKey = <VAULT_PRIVATE_KEY>

[Peer]  # Shaun's phone
PublicKey = <PHONE_PUBLIC_KEY>
AllowedIPs = 10.10.50.2/32

[Peer]  # Shaun's laptop (remote)
PublicKey = <LAPTOP_PUBLIC_KEY>
AllowedIPs = 10.10.50.3/32
```

#### Layer 2: Service Authentication

- vLLM instances bind to 10GbE data plane only — not accessible from 1GbE home network
- Dashboard requires authentication (session-based or basic auth)
- API endpoints require API keys for service-to-service calls
- LiteLLM proxy (VAULT:4000) authenticates with the vaulted `ATHANOR_LITELLM_API_KEY`
- Unraid web UI restricted to management VLAN only

#### Layer 3: Secrets Management

```
/etc/athanor/secrets/
├── vllm.env            # model paths, config
├── wireguard.env        # WG private keys
├── docker-credentials   # registry tokens if needed
├── nordvpn.env          # VPN service credentials
└── .env                 # node-specific secrets
```

- File permissions: `chmod 600`, owned by `root:docker`
- Docker Compose references secrets via `env_file:` — never inline
- Secrets directory excluded from git (`.gitignore`)
- Ansible vault for credentials that need to be in IaC (`ansible/group_vars/all/secrets.vault.yml`)
- **No secrets in the Athanor repository — ever**

#### Layer 4: VLAN Segmentation (Target)

| VLAN | Purpose | Members | Access |
|------|---------|---------|--------|
| INFERENCE | GPU inference endpoints | Node 1, Node 2 vLLM ports | Agent server only |
| DATA | 10GbE model staging, NFS | Node 1, Node 2, VAULT | Internal only |
| SERVICES | User-facing (dashboard, HA, Plex) | All nodes service ports | LAN + WireGuard |
| MGMT | Node management, SSH, IPMI | All nodes SSH | LAN admin only |
| HOME | IoT, WiFi, streaming clients | APs, Lutron, clients | Internet + SERVICES |

**Key rule:** HOME VLAN cannot reach INFERENCE VLAN. A compromised smart bulb cannot query uncensored models.

---

## Implementation Priority

1. Secrets in `.env` files with restricted permissions (done — Ansible vault active)
2. UFW firewall on all nodes (done — Ansible common role)
3. LiteLLM API key authentication (done — VAULT:4000)
4. WireGuard on VAULT (before any remote access)
5. VLAN segmentation (when 10GbE switch is configured)
6. API authentication on all endpoints (before dashboard goes live)

---

## Current State (2026-02-24)

- UFW active on Node 1 and Node 2 with explicit port allowances
- Ansible vault encrypts sensitive credentials
- LiteLLM authenticates with API key
- SSH key-based auth only (no password auth on compute nodes)
- WireGuard not yet deployed
- VLANs not yet configured (flat network)

---

## Risks

- **Flat network until VLANs.** All devices share a network segment. IoT devices can theoretically reach inference endpoints. Mitigated by UFW on nodes blocking non-whitelisted ports.
- **WireGuard key management.** Single point of failure for remote access. Mitigated by having multiple peers (phone + laptop) and physical access as backup.
- **Ansible vault password.** Stored in memory during runs. Not a concern for a single-operator system.

---

## Sources

- [WireGuard on Unraid](https://wiki.unraid.net/WireGuard_Quickstart)
- [UniFi VLAN configuration](https://help.ui.com/hc/en-us/articles/219654457)
- [UFW documentation](https://help.ubuntu.com/community/UFW)
