"""Home Assistant status endpoint for dashboard consumption."""

import logging

import httpx
from fastapi import APIRouter

from ..config import settings
from ..services import ServiceRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["home"])

_registry = ServiceRegistry(settings)


@router.get("/home/summary")
async def home_summary():
    """Lightweight HA summary: entity counts, key sensor states, automation stats."""
    base = settings.home_assistant_url
    headers = _registry.home_assistant_headers

    if not settings.ha_token:
        return {
            "online": False,
            "configured": False,
            "error": "No HA token configured",
        }

    result: dict = {
        "online": False,
        "configured": True,
        "entities": 0,
        "automations": {"total": 0, "on": 0},
        "lights": {"total": 0, "on": 0},
        "climate": [],
        "sensors": [],
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check reachability
        try:
            resp = await client.get(f"{base}/api/", headers=headers)
            result["online"] = resp.status_code == 200
        except Exception:
            return result

        if not result["online"]:
            return result

        # Fetch all states
        try:
            resp = await client.get(f"{base}/api/states", headers=headers)
            if resp.status_code != 200:
                result["error"] = f"states returned {resp.status_code}"
                return result

            states = resp.json()
            result["entities"] = len(states)

            # Aggregate by domain
            for entity in states:
                eid = entity.get("entity_id", "")
                state = entity.get("state", "")
                attrs = entity.get("attributes", {})
                friendly = attrs.get("friendly_name", eid)

                if eid.startswith("automation."):
                    result["automations"]["total"] += 1
                    if state == "on":
                        result["automations"]["on"] += 1

                elif eid.startswith("light."):
                    result["lights"]["total"] += 1
                    if state == "on":
                        result["lights"]["on"] += 1

                elif eid.startswith("climate."):
                    result["climate"].append({
                        "id": eid,
                        "name": friendly,
                        "state": state,
                        "temperature": attrs.get("temperature"),
                        "current_temperature": attrs.get("current_temperature"),
                        "hvac_action": attrs.get("hvac_action"),
                    })

                elif eid.startswith("sensor.") and any(
                    k in eid for k in ("temperature", "humidity", "power", "energy")
                ):
                    if state not in ("unavailable", "unknown"):
                        result["sensors"].append({
                            "id": eid,
                            "name": friendly,
                            "state": state,
                            "unit": attrs.get("unit_of_measurement", ""),
                        })

            # Limit sensors to most interesting 20
            result["sensors"] = result["sensors"][:20]

        except Exception as e:
            logger.error("Failed to fetch HA states: %s", e)
            result["error"] = str(e)

    return result
