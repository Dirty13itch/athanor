from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import settings


def _default_agent_descriptor_path() -> Path:
    target_parts = ("config", "automation-backbone", "agent-descriptor-registry.json")
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return candidate
    return Path("/workspace/config/automation-backbone/agent-descriptor-registry.json")


def _resolve_agent_descriptor_path() -> Path:
    configured = str(settings.agent_descriptor_path or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_agent_descriptor_path()


@lru_cache(maxsize=1)
def load_agent_descriptor_registry() -> dict[str, Any]:
    path = _resolve_agent_descriptor_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    agents = data.get("agents")
    if not isinstance(agents, list):
        raise ValueError(f"Agent descriptor registry at {path} must contain an 'agents' list")
    return data


def reset_agent_descriptor_registry_cache() -> None:
    load_agent_descriptor_registry.cache_clear()


def get_agent_descriptors() -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for item in load_agent_descriptor_registry().get("agents", []):
        if isinstance(item, dict) and item.get("id"):
            descriptors.append(dict(item))
    return descriptors


def get_live_agent_descriptors() -> list[dict[str, Any]]:
    return [
        descriptor
        for descriptor in get_agent_descriptors()
        if str(descriptor.get("status") or "").strip().lower() == "live"
    ]


def get_agent_descriptor(agent_id: str) -> dict[str, Any] | None:
    for descriptor in get_agent_descriptors():
        if str(descriptor.get("id") or "") == agent_id:
            return descriptor
    return None


def build_agent_metadata() -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for descriptor in get_live_agent_descriptors():
        agent_id = str(descriptor["id"])
        entry = {
            "description": str(descriptor.get("description") or ""),
            "tools": [str(tool) for tool in descriptor.get("tools", []) if str(tool).strip()],
            "type": str(descriptor.get("type") or "reactive"),
            "owner_domains": [
                str(domain)
                for domain in descriptor.get("owner_domains", [])
                if str(domain).strip()
            ],
            "support_domains": [
                str(domain)
                for domain in descriptor.get("support_domains", [])
                if str(domain).strip()
            ],
        }
        cadence = str(descriptor.get("cadence") or "").strip()
        if cadence and cadence not in {"event-driven", "on-demand"}:
            entry["schedule"] = cadence
        metadata[agent_id] = entry
    return metadata
