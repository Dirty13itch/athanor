# Home Agent ↔ Home Assistant Integration Spec

*Implementation detail for ADR-010 (Home Automation). Defines the MQTT event bus, topic structure, context-aware decision patterns, and proactive scheduling.*

---

## Architecture

```
Home Assistant → MQTT → Event Bus → Home Agent (LangGraph on Node 1)
                                          ↓
                                    Context evaluation:
                                    - Time of day
                                    - Who's home (occupancy)
                                    - Current activity (coding? EoBQ? sleeping?)
                                    - Weather conditions
                                    - Calendar events
                                    - Historical patterns
                                          ↓
                                    Decision/Action
                                          ↓
                                    MQTT → Home Assistant → Execute
```

The Home Agent is a triggered specialist — it activates when MQTT events arrive, processes them with full context awareness, and goes idle. It shares inference resources with other agents and only consumes GPU when there's something to decide.

---

## MQTT Broker

**Mosquitto** on VAULT as a Docker container. Lightweight, standard MQTT 5.0 broker.

Deploy alongside HA (blocked on HA onboarding completion).

---

## MQTT Topic Structure

```
athanor/ha/motion/living_room      → motion detected
athanor/ha/temperature/outside     → temperature reading
athanor/ha/occupancy/home          → presence detection
athanor/ha/light/living_room/state → current light state
athanor/ha/command/lights/living_room → {"brightness": 20, "color_temp": "warm"}
```

Inbound topics (HA → Agent): state changes, sensor readings, motion events.
Outbound topics (Agent → HA): commands to control devices.

---

## Context-Aware Decision Examples

| Event | Context | Decision |
|-------|---------|----------|
| Motion in living room at 11 PM | Home occupied | Dim lights to 20%, warm color temp. Don't turn on bright overhead. |
| Temperature dropping below 60°F | Nobody home | Don't adjust thermostat (save energy) |
| Shaun in creative session | EoBQ running on Node 2 | Suppress non-critical notifications, keep ambient lighting stable |
| Motion at 2 AM | Occupancy = asleep | It's the cat. Ignore. |
| Amanda arrives home | Phone connects to WiFi | Turn on entry lights, set living room to her preferred scene |

---

## Proactive Schedule

Every 5 minutes, the Home Agent does a proactive scan:
- Check environmental conditions (temperature, humidity, light levels)
- Look for patterns (regular events that shouldn't trigger novel responses)
- Anticipate needs before events trigger
- This is where pattern learning happens over time

---

## Hardware Integration

| Device | Integration | Notes |
|--------|-------------|-------|
| Lutron lighting system | Controller at 192.168.1.158 | RadioRA2 via HA Lutron integration |
| UniFi network | Dream Machine Pro | Device presence detection |
| Temperature/humidity sensors | Via HA integrations | TBD specific hardware |
| Future: Zigbee/Z-Wave | USB passthrough to VAULT | Coordinators when needed |

---

## Blockers

- HA onboarding not yet completed (http://192.168.1.203:8123)
- MQTT broker (Mosquitto) not yet deployed
- Home Agent is currently a skeleton in the agent framework
