# ADR-010: Home Automation Integration

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/research/2026-02-15-home-automation.md](../research/2026-02-15-home-automation.md)
**Depends on:** ADR-001 (Base Platform), ADR-007 (Dashboard)

---

## Context

Athanor includes home automation as supporting infrastructure. Shaun has Lutron lighting, a UniFi network stack, and plans for additional smart devices. Home Assistant is the only open-source platform with the integration breadth needed. This ADR documents where HA runs, how it connects to existing hardware, and how it integrates with Athanor's dashboard and agent system.

---

## Decision

### Home Assistant Docker on VAULT with API access for dashboard and agents.

#### Deployment

Home Assistant runs as a Docker container on VAULT (Unraid) with host networking:

- **Image:** `homeassistant/home-assistant:stable`
- **Network:** Host mode (required for mDNS device discovery)
- **Config:** `/mnt/user/appdata/homeassistant:/config`
- **Port:** 8123 (HA default)
- **Always-on:** VAULT runs 24/7, HA runs 24/7

#### Hardware Integrations

| Device | Integration | Notes |
|--------|-------------|-------|
| Lutron controller (.158) | Native Lutron integration (Telnet) | RadioRA2 v12+ requires manual telnet user setup |
| UniFi Dream Machine Pro | Native UniFi integration | Presence detection, device tracking |
| USP PDU Pro | Via UniFi | Rack power monitoring per outlet |

#### Athanor Integrations

| Integration | Direction | Method |
|-------------|-----------|--------|
| Dashboard → HA | Read + write | HA REST/WebSocket API, long-lived access token |
| Home Agent → HA | Read + write | Same API, called from Node 1 over 5GbE |
| HA → Agents | Trigger | HA automations call agent API (webhook) |
| HA → Unraid | Read | ha-unraid integration (GraphQL API) |
| HA → vLLM | Read | Custom REST sensor for inference status |

---

## What This Enables

- **Lighting control** from Athanor's dashboard and via natural language ("dim the living room")
- **Presence-aware automations** — system reacts to who's home (via UniFi device tracking)
- **AI-optimized automation** — the Home Agent analyzes patterns and suggests improvements
- **Rack power monitoring** — USP PDU Pro data in HA shows per-device power consumption
- **Unified view** — home status on the same dashboard as AI, media, and system health

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| No home automation | Lutron and UniFi exist. Connecting them costs nothing and adds real value. |
| HA OS as VM | More features (add-ons) but heavier. Start with Docker — migrate to VM only if Zigbee/Z-Wave USB coordinators are needed. |
| Hubitat / SmartThings | Closed platforms, limited API access, no agent integration. |
| Node-RED only | Complementary to HA (can run as add-on), not a replacement for device management. |

---

## Risks

- **HA Docker limitations.** Some HA add-ons require HA OS (VM mode). Mitigated by starting with Docker and migrating only if needed. Core integrations (Lutron, UniFi, REST API) work in Docker.
- **Lutron Telnet credentials.** RadioRA2 v12+ changed default credentials. Requires manual configuration in the Lutron software. One-time setup.

---

## Sources

- [Home Assistant Lutron integration](https://www.home-assistant.io/integrations/lutron/)
- [Home Assistant UniFi integration](https://www.home-assistant.io/integrations/unifi/)
- [ha-unraid integration](https://github.com/ruaan-deysel/ha-unraid)
- [HA on Unraid guide](https://www.wundertech.net/how-to-set-up-home-assistant-on-unraid/)
