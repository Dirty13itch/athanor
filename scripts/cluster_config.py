"""Athanor cluster topology loaded from the shared platform contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _candidate_topology_paths() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("ATHANOR_TOPOLOGY_PATH")
    if env_path:
        candidates.append(Path(env_path))

    repo_root = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            repo_root / "config" / "automation-backbone" / "platform-topology.json",
            Path("/app/config/automation-backbone/platform-topology.json"),
            Path("/opt/athanor/config/automation-backbone/platform-topology.json"),
        ]
    )
    return candidates


def _load_topology() -> dict[str, Any]:
    for path in _candidate_topology_paths():
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    checked = ", ".join(str(path) for path in _candidate_topology_paths())
    raise FileNotFoundError(f"Unable to resolve platform topology. Checked: {checked}")


def _first_env(names: list[str], default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def _default_url_env(service_id: str) -> str:
    return f"ATHANOR_{service_id.upper().replace('-', '_')}_URL"


def _build_url(service: dict[str, Any], node_hosts: dict[str, str]) -> str:
    override = _first_env([str(service.get("url_env") or _default_url_env(str(service["id"])))])
    if override:
        return override

    node_id = str(service["node"])
    scheme = str(service["scheme"])
    port = int(service["port"])
    path = str(service.get("path") or "")
    return f"{scheme}://{node_hosts[node_id]}:{port}{path}"


TOPOLOGY = _load_topology()
NODE_DEFINITIONS = {str(node["id"]): dict(node) for node in TOPOLOGY.get("nodes", [])}
SERVICE_DEFINITIONS = {str(service["id"]): dict(service) for service in TOPOLOGY.get("services", [])}

NODES = {
    node_id: _first_env(list(node.get("host_envs", [])), str(node.get("default_host") or ""))
    for node_id, node in NODE_DEFINITIONS.items()
}

DEV_HOST = NODES["dev"]
FOUNDRY_HOST = NODES["foundry"]
WORKSHOP_HOST = NODES["workshop"]
VAULT_HOST = NODES["vault"]
DESK_HOST = NODES["desk"]


def _read_secret(name: str, default: str = "") -> str:
    path = os.path.expanduser(f"~/.secrets/{name}")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    except FileNotFoundError:
        return default


LITELLM_KEY = os.environ.get("LITELLM_MASTER_KEY") or _read_secret("litellm-master-key")

SERVICES = {
    service_id: {
        **service,
        "url": _build_url(service, NODES),
    }
    for service_id, service in SERVICE_DEFINITIONS.items()
}


def get_url(service_name: str) -> str:
    """Get the URL for a service by name."""
    service = SERVICES.get(service_name)
    if isinstance(service, dict):
        return str(service["url"])
    raise KeyError(f"Unknown service: {service_name}")
