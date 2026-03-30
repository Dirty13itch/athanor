"""Shared cluster configuration for services from the platform topology contract."""

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
VAULT_HOST = NODES["vault"]
FOUNDRY_HOST = NODES["foundry"]
WORKSHOP_HOST = NODES["workshop"]
DESK_HOST = NODES["desk"]

SERVICES = {
    service_id: _build_url(service, NODES)
    for service_id, service in SERVICE_DEFINITIONS.items()
}

QDRANT_URL = SERVICES["qdrant"]
LITELLM_URL = SERVICES["litellm"]
NEO4J_URL = SERVICES["neo4j"]
NEO4J_HTTP_URL = SERVICES["neo4j_http"]
PROMETHEUS_URL = SERVICES["prometheus"]
GRAFANA_URL = SERVICES["grafana"]
EMBEDDING_URL = SERVICES["embedding"]
RERANKER_URL = SERVICES["reranker"]
AGENT_SERVER_URL = SERVICES["agent_server"]
GPU_ORCHESTRATOR_URL = SERVICES["gpu_orchestrator"]
WS_PTY_BRIDGE_URL = SERVICES["ws_pty_bridge"]
QUALITY_GATE_URL = SERVICES["quality_gate"]
NTFY_URL = SERVICES["ntfy"]
NTFY_TOPIC_URL = SERVICES["ntfy_topic"]
LANGFUSE_URL = SERVICES["langfuse"]
REDIS_URL = SERVICES["redis"]
DASHBOARD_URL = SERVICES["dashboard"]
COMFYUI_URL = SERVICES["comfyui"]
OLLAMA_WORKSHOP_URL = SERVICES["ollama_workshop"]
VLLM_COORDINATOR_URL = SERVICES["vllm_coordinator"]
VLLM_CODER_URL = SERVICES["vllm_coder"]
VLLM_WORKER_URL = SERVICES["vllm_worker"]
STASH_URL = SERVICES["stash"]
SPEACHES_URL = SERVICES["speaches"]
SPEECHES_URL = SPEACHES_URL
GATEWAY_URL = SERVICES["gateway"]
MEMORY_URL = SERVICES["memory"]
SEMANTIC_ROUTER_URL = SERVICES["semantic_router"]
UPTIME_KUMA_URL = SERVICES["uptime_kuma"]
MINIFLUX_URL = SERVICES["miniflux"]
OPENFANG_URL = SERVICES["openfang"]


def get_url(service_name: str) -> str:
    """Get the URL for a service by name."""
    url = SERVICES.get(service_name)
    if url is not None:
        return url
    raise KeyError(f"Unknown service: {service_name}")


def get_service_definition(service_name: str) -> dict[str, Any]:
    """Return the topology definition for a known service."""
    service = SERVICE_DEFINITIONS.get(service_name)
    if service is not None:
        return service
    raise KeyError(f"Unknown service: {service_name}")


def get_health_url(service_name: str) -> str:
    """Return the canonical health/readiness URL owned by the topology registry."""
    service = get_service_definition(service_name)
    health_path = str(service.get("health_path") or "")
    base_url = get_url(service_name)
    if not health_path:
        return base_url
    if base_url.endswith(health_path):
        return base_url
    return f"{base_url}{health_path}"
