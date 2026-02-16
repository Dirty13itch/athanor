# Home Automation Integration

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-010 (Home Automation Integration)
**Depends on:** ADR-001 (Base Platform), ADR-007 (Dashboard)

---

## The Question

How does Home Assistant fit into Athanor? Where does it run, how does it integrate with the dashboard and agents, and what's the relationship with existing smart home hardware?

---

## This Is a Nearly Forced Decision

Per ADR-004, Home Assistant runs on VAULT (always-on, Docker). The hardware (Lutron, UniFi, smart devices) already exists. Home Assistant is the only viable open-source home automation platform with the integration breadth Athanor needs. There is no real alternative evaluation needed.

---

## Existing Hardware

| Device | IP / Protocol | Integration |
|--------|--------------|-------------|
| Lutron lighting controller | 192.168.1.158 / Telnet | [HA Lutron integration](https://www.home-assistant.io/integrations/lutron/) — requires `lutron` user (check RadioRA2 version) |
| UniFi Dream Machine Pro | 192.168.1.1 / API | [HA UniFi integration](https://www.home-assistant.io/integrations/unifi/) — device tracking, presence detection |
| USP PDU Pro | Via UniFi | Power monitoring per outlet (rack power) |
| Multiple U6 APs | Via UniFi | WiFi device tracking |
| Smart devices (TBD) | Various | Added as discovered |

---

## Deployment

**Docker container on VAULT** (Unraid Community Apps):

```yaml
# Unraid Docker template or docker-compose
services:
  homeassistant:
    image: homeassistant/home-assistant:stable
    network_mode: host  # Required for mDNS device discovery
    volumes:
      - /mnt/user/appdata/homeassistant:/config
    environment:
      - TZ=America/Chicago
    restart: unless-stopped
```

`network_mode: host` is important — HA needs direct network access for mDNS discovery (Lutron, Chromecast, etc.) and multicast protocols. Running in host mode on VAULT puts HA on the same network as all devices.

**Alternatively:** HA OS as a VM on Unraid for full add-on support. Docker is simpler but some HA add-ons (Zigbee, Z-Wave) require VM mode. Start with Docker, migrate to VM only if add-on requirements demand it.

---

## Integrations

### Existing
- **Lutron** — lighting control, scene management. HA's native integration connects via Telnet to the Lutron controller. Note: RadioRA2 v12+ requires adding a telnet user manually.
- **UniFi** — device presence detection (who's home), network status. HA connects to the Dream Machine Pro's API.

### Future (as devices are added)
- **Zigbee / Z-Wave** — if smart devices using these protocols are added, requires a USB coordinator (Zigbee2MQTT or ZHA)
- **Matter / Thread** — emerging standard, HA has native support
- **Climate control** — thermostat integration when applicable
- **Sensors** — motion, door, temperature, humidity

### Athanor-Specific
- **Unraid monitoring** — [ha-unraid integration](https://github.com/ruaan-deysel/ha-unraid) monitors Unraid server health (CPU, RAM, disk, VMs, containers). Recent rewrite uses Unraid's GraphQL API (v2025.12.0+).
- **vLLM status** — custom REST sensor checking vLLM health endpoints
- **Agent triggers** — HA automations can trigger Athanor agents (e.g., "when Shaun arrives home, tell the home agent to activate presence mode")

---

## Dashboard Integration (ADR-007)

Athanor's dashboard includes a Home panel that shows:
- Current lighting state and quick controls
- Presence detection (who's home)
- Climate summary
- Recent automation activity

Data comes from HA's REST API (`http://vault:8123/api/`) or WebSocket API for real-time updates. HA provides long-lived access tokens for authentication.

The Home Agent (ADR-008) uses the same API to query and control HA programmatically.

---

## Agent Integration (ADR-008)

The Home Agent on Node 1 connects to HA's API over 10GbE:

| Agent Action | HA API |
|-------------|--------|
| Query device states | `GET /api/states` |
| Control devices | `POST /api/services/{domain}/{service}` |
| Read automation history | `GET /api/history/period` |
| Trigger automations | `POST /api/services/automation/trigger` |

The Home Agent can:
- Analyze lighting usage patterns and suggest optimizations
- Respond to natural language commands ("dim the living room lights")
- Create or modify automations based on preferences
- Monitor energy usage (via USP PDU Pro) and report

---

## Recommendation

1. **Home Assistant Docker on VAULT** — install via Unraid CA, host networking mode
2. **Lutron integration** — connect to controller at .158, configure telnet user
3. **UniFi integration** — connect to Dream Machine Pro for presence detection
4. **ha-unraid integration** — monitor VAULT health from HA
5. **HA API exposed to Node 1/Node 2** — for dashboard and agent integration
6. **Start simple** — basic automations first, agent-driven optimization later

---

## Sources

- [Home Assistant Lutron integration](https://www.home-assistant.io/integrations/lutron/)
- [Home Assistant UniFi integration](https://www.home-assistant.io/integrations/unifi/)
- [ha-unraid GitHub](https://github.com/ruaan-deysel/ha-unraid)
- [HA on Unraid setup guide](https://www.wundertech.net/how-to-set-up-home-assistant-on-unraid/)
- [HA REST API docs](https://developers.home-assistant.io/docs/api/rest/)
