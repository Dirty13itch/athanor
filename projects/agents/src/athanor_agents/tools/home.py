import httpx
from langchain_core.tools import tool

from ..services import registry

HA_URL = registry.home_assistant_api_url


def _ha_headers() -> dict:
    return dict(registry.home_assistant_headers)


def _ha_get(path: str) -> dict | list:
    resp = httpx.get(f"{HA_URL}{path}", headers=_ha_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def _ha_post(path: str, json_data: dict | None = None) -> dict | list:
    resp = httpx.post(
        f"{HA_URL}{path}", headers=_ha_headers(), json=json_data or {}, timeout=10
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


# --- Entity Tools ---


@tool
def get_ha_states() -> str:
    """Get a summary of all Home Assistant entities grouped by domain. Shows counts and key entities."""
    try:
        states = _ha_get("/states")
        domains: dict[str, list] = {}
        for s in states:
            domain = s["entity_id"].split(".")[0]
            domains.setdefault(domain, []).append(s)

        lines = [f"Home Assistant: {len(states)} entities across {len(domains)} domains"]
        for domain, entities in sorted(domains.items()):
            lines.append(f"  {domain}: {len(entities)} entities")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching HA states: {e}"


@tool
def get_entity_state(entity_id: str) -> str:
    """Get the current state and attributes of a specific Home Assistant entity by its entity_id (e.g., 'light.living_room', 'switch.office_fan')."""
    try:
        state = _ha_get(f"/states/{entity_id}")
        attrs = state.get("attributes", {})
        friendly = attrs.get("friendly_name", entity_id)
        lines = [
            f"{friendly} ({entity_id})",
            f"  State: {state.get('state', '?')}",
            f"  Last changed: {state.get('last_changed', '?')}",
        ]
        for key, val in attrs.items():
            if key != "friendly_name":
                lines.append(f"  {key}: {val}")
        return "\n".join(lines)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Entity '{entity_id}' not found."
        return f"Error fetching entity: {e}"
    except Exception as e:
        return f"Error fetching entity: {e}"


@tool
def find_entities(query: str) -> str:
    """Search for Home Assistant entities by name or domain. Use partial matching — e.g., 'light', 'kitchen', 'temperature'."""
    try:
        states = _ha_get("/states")
        query_lower = query.lower()
        matches = []
        for s in states:
            eid = s["entity_id"]
            name = s.get("attributes", {}).get("friendly_name", "")
            if query_lower in eid.lower() or query_lower in name.lower():
                matches.append(
                    f"  {eid}: {s.get('state', '?')} — {name}"
                )
        if not matches:
            return f"No entities matching '{query}'."
        lines = [f"Entities matching '{query}' ({len(matches)} found):"]
        lines.extend(matches[:30])
        if len(matches) > 30:
            lines.append(f"  ... and {len(matches) - 30} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching entities: {e}"


# --- Control Tools ---


@tool
def call_ha_service(domain: str, service: str, entity_id: str) -> str:
    """Call a Home Assistant service on an entity. Common examples:
    - domain='light', service='turn_on', entity_id='light.living_room'
    - domain='light', service='turn_off', entity_id='light.kitchen'
    - domain='switch', service='toggle', entity_id='switch.office_fan'
    - domain='climate', service='set_temperature', entity_id='climate.thermostat'
    """
    try:
        data = {"entity_id": entity_id}
        _ha_post(f"/services/{domain}/{service}", data)
        # Read back the new state
        state = _ha_get(f"/states/{entity_id}")
        name = state.get("attributes", {}).get("friendly_name", entity_id)
        return f"Called {domain}.{service} on {name}. New state: {state.get('state', '?')}"
    except httpx.HTTPStatusError as e:
        return f"Service call failed: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Error calling service: {e}"


@tool
def set_light_brightness(entity_id: str, brightness_pct: int) -> str:
    """Set a light's brightness to a specific percentage (0-100). Entity must be a light."""
    try:
        data = {"entity_id": entity_id, "brightness_pct": max(0, min(100, brightness_pct))}
        _ha_post("/services/light/turn_on", data)
        state = _ha_get(f"/states/{entity_id}")
        name = state.get("attributes", {}).get("friendly_name", entity_id)
        actual = state.get("attributes", {}).get("brightness", 0)
        return f"Set {name} brightness to {brightness_pct}% (actual: {round(actual / 255 * 100)}%)"
    except Exception as e:
        return f"Error setting brightness: {e}"


@tool
def set_climate_temperature(entity_id: str, temperature: float) -> str:
    """Set a thermostat/climate entity to a specific temperature in its configured unit."""
    try:
        data = {"entity_id": entity_id, "temperature": temperature}
        _ha_post("/services/climate/set_temperature", data)
        state = _ha_get(f"/states/{entity_id}")
        name = state.get("attributes", {}).get("friendly_name", entity_id)
        current = state.get("attributes", {}).get("current_temperature", "?")
        target = state.get("attributes", {}).get("temperature", "?")
        return f"{name}: target set to {target}°, current: {current}°"
    except Exception as e:
        return f"Error setting temperature: {e}"


# --- Automation Tools ---


@tool
def list_automations() -> str:
    """List all Home Assistant automations with their current state (on/off) and last triggered time."""
    try:
        states = _ha_get("/states")
        automations = [s for s in states if s["entity_id"].startswith("automation.")]
        if not automations:
            return "No automations configured."
        lines = [f"Automations ({len(automations)}):"]
        for a in sorted(automations, key=lambda x: x["entity_id"]):
            name = a.get("attributes", {}).get("friendly_name", a["entity_id"])
            state = a.get("state", "?")
            last = a.get("attributes", {}).get("last_triggered", "never")
            lines.append(f"  {name}: {state} (last: {last})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing automations: {e}"


@tool
def trigger_automation(entity_id: str) -> str:
    """Manually trigger a Home Assistant automation by its entity_id."""
    try:
        _ha_post("/services/automation/trigger", {"entity_id": entity_id})
        return f"Triggered automation: {entity_id}"
    except Exception as e:
        return f"Error triggering automation: {e}"


# --- Scene and History Tools ---


@tool
def activate_scene(entity_id: str) -> str:
    """Activate a Home Assistant scene by its entity_id (e.g., 'scene.movie_night')."""
    try:
        _ha_post("/services/scene/turn_on", {"entity_id": entity_id})
        return f"Activated scene: {entity_id}"
    except Exception as e:
        return f"Error activating scene: {e}"


@tool
def get_entity_history(entity_id: str, hours: int = 24) -> str:
    """Get recent state history for an entity over the last N hours. Useful for trend analysis."""
    from datetime import datetime, timedelta, timezone

    try:
        start = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        resp = httpx.get(
            f"{HA_URL}/history/period/{start}",
            headers=_ha_headers(),
            params={"filter_entity_id": entity_id, "minimal_response": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data or not data[0]:
            return f"No history for {entity_id} in last {hours}h."

        entries = data[0]
        lines = [f"History for {entity_id} (last {hours}h, {len(entries)} entries):"]
        # Show up to 20 most recent entries
        for entry in entries[-20:]:
            ts = entry.get("last_changed", "?")
            state = entry.get("state", "?")
            lines.append(f"  {ts}: {state}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching history: {e}"


@tool
def get_network_devices() -> str:
    """List devices on the network via Home Assistant device tracker. Shows which devices are home/away."""
    try:
        states = _ha_get("/states")
        trackers = [s for s in states if s["entity_id"].startswith("device_tracker.")]
        if not trackers:
            return "No device trackers configured."

        home = [t for t in trackers if t.get("state") == "home"]
        away = [t for t in trackers if t.get("state") != "home"]

        lines = [f"Network Devices ({len(trackers)} total, {len(home)} home):"]
        if home:
            lines.append("  Home:")
            for t in home:
                name = t.get("attributes", {}).get("friendly_name", t["entity_id"])
                ip = t.get("attributes", {}).get("ip", "")
                lines.append(f"    {name}" + (f" ({ip})" if ip else ""))
        if away:
            lines.append(f"  Away/Offline: {len(away)} devices")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching device trackers: {e}"


HOME_TOOLS = [
    get_ha_states,
    get_entity_state,
    find_entities,
    call_ha_service,
    set_light_brightness,
    set_climate_temperature,
    list_automations,
    trigger_automation,
    activate_scene,
    get_entity_history,
    get_network_devices,
]
