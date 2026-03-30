from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module(name: str, relative: str):
    service_dir = Path(__file__).resolve().parents[1]
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    module_path = service_dir / relative
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checks = _load_module("sentinel_checks", "checks.py")


def test_heartbeat_checks_use_topology_health_urls_for_canonical_services() -> None:
    heartbeat_map = dict(checks.HEARTBEAT_CHECKS)

    for service_id in (
        "gateway",
        "memory",
        "quality_gate",
        "dashboard",
        "embedding",
        "qdrant",
        "subscription_burn",
        "agent_server",
        "ollama_workshop",
        "comfyui",
    ):
        assert heartbeat_map[service_id] == checks.get_health_url(service_id)

    assert heartbeat_map["dashboard"].endswith("/api/overview")
    assert heartbeat_map["qdrant"].endswith("/collections")
    assert heartbeat_map["comfyui"].endswith("/system_stats")


def test_sentinel_uses_only_canonical_service_ids_for_heartbeat_checks() -> None:
    heartbeat_services = {name for name, _url in checks.HEARTBEAT_CHECKS}

    assert {"mind", "classifier", "brain", "draftsman", "open_webui"}.isdisjoint(heartbeat_services)
    assert "subscription_burn" in heartbeat_services
    assert "burn_scheduler" not in heartbeat_services
    assert "ollama_workshop" in heartbeat_services
    assert "ollama_sovereign" not in heartbeat_services
    assert checks.READINESS_SERVICES == (
        "vllm_coordinator",
        "vllm_coder",
        "ollama_workshop",
        "litellm",
        "embedding",
    )
