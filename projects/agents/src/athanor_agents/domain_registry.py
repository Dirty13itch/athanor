from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import settings


def _default_domain_packet_path() -> Path:
    target_parts = ("config", "automation-backbone", "domain-packets-registry.json")
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return candidate
    return Path("/workspace/config/automation-backbone/domain-packets-registry.json")


def _resolve_domain_packet_path() -> Path:
    configured = str(settings.domain_packet_path or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_domain_packet_path()


@lru_cache(maxsize=1)
def load_domain_packet_registry() -> dict[str, Any]:
    path = _resolve_domain_packet_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    domains = data.get("domains")
    if not isinstance(domains, list):
        raise ValueError(f"Domain packet registry at {path} must contain a 'domains' list")
    return data


def reset_domain_packet_registry_cache() -> None:
    load_domain_packet_registry.cache_clear()


def get_domain_packets() -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for item in load_domain_packet_registry().get("domains", []):
        if isinstance(item, dict) and item.get("id"):
            packets.append(dict(item))
    return packets


def get_live_domain_packets() -> list[dict[str, Any]]:
    return [
        packet
        for packet in get_domain_packets()
        if str(packet.get("status") or "").strip().lower() == "live"
    ]


def get_domain_packet(domain_id: str) -> dict[str, Any] | None:
    for packet in get_domain_packets():
        if str(packet.get("id") or "") == domain_id:
            return packet
    return None


def build_domain_metadata() -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    for packet in get_live_domain_packets():
        metadata.append(
            {
                "id": str(packet["id"]),
                "label": str(packet.get("label") or packet["id"]),
                "description": str(packet.get("description") or ""),
                "owner_agent": str(packet.get("owner_agent") or ""),
                "support_agents": [
                    str(agent)
                    for agent in packet.get("support_agents", [])
                    if str(agent).strip()
                ],
                "systems": [
                    str(system)
                    for system in packet.get("systems", [])
                    if str(system).strip()
                ],
                "surfaces": [
                    str(surface)
                    for surface in packet.get("surfaces", [])
                    if str(surface).strip()
                ],
                "status": str(packet.get("status") or "planned"),
            }
        )
    return metadata
