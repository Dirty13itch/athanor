"""Athanor Sentinel -- Check definitions and runners."""

import time
import httpx
from dataclasses import dataclass, field
from pathlib import Path

from _imports import (
    AGENT_SERVER_URL,
    FOUNDRY_HOST,
    LITELLM_URL,
    NTFY_URL,
    OLLAMA_WORKSHOP_URL,
    PROMETHEUS_URL,
    QDRANT_URL,
    SERVICE_DEFINITIONS,
    VAULT_HOST,
    VLLM_CODER_URL,
    VLLM_COORDINATOR_URL,
    WORKSHOP_HOST,
    get_health_url,
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_LITELLM_KEY = ""


def _get_litellm_key() -> str:
    global _LITELLM_KEY
    if not _LITELLM_KEY:
        try:
            _LITELLM_KEY = Path("/home/shaun/.secrets/litellm-master-key").read_text().strip()
        except Exception:
            _LITELLM_KEY = ""
    return _LITELLM_KEY


_AGENT_KEY = ""


def _get_agent_key() -> str:
    global _AGENT_KEY
    if not _AGENT_KEY:
        try:
            _AGENT_KEY = Path("/home/shaun/.secrets/agent-server-api-key").read_text().strip()
        except Exception:
            _AGENT_KEY = ""
    return _AGENT_KEY


# ---------------------------------------------------------------------------
# Tier 1: Heartbeat -- is it alive?
# ---------------------------------------------------------------------------

HEARTBEAT_SERVICE_IDS = (
    "gateway",
    "memory",
    "quality_gate",
    "dashboard",
    "embedding",
    "reranker",
    "semantic_router",
    "subscription_burn",
    "litellm",
    "qdrant",
    "prometheus",
    "agent_server",
    "vllm_coordinator",
    "vllm_coder",
    "ollama_workshop",
    "comfyui",
)

HEARTBEAT_CHECKS = [
    (service_id, get_health_url(service_id))
    for service_id in HEARTBEAT_SERVICE_IDS
    if str(SERVICE_DEFINITIONS[service_id].get("health_path") or "")
]

# Services that need Authorization header
AUTH_SERVICES = {"litellm", "agent_server"}

READINESS_SERVICES = (
    "vllm_coordinator",
    "vllm_coder",
    "ollama_workshop",
    "litellm",
    "embedding",
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    service: str
    tier: str
    passed: bool
    latency_ms: float
    detail: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


def run_heartbeat(name: str, url: str, timeout: float = 5.0) -> CheckResult:
    """Tier 1: simple HTTP GET, any 2xx = pass."""
    start = time.monotonic()
    try:
        headers = {}
        if name in AUTH_SERVICES:
            if name == "agent_server":
                key = _get_agent_key()
            else:
                key = _get_litellm_key()
            if key:
                headers["Authorization"] = f"Bearer {key}"
        r = httpx.get(url, timeout=timeout, follow_redirects=True, headers=headers)
        latency = (time.monotonic() - start) * 1000
        passed = r.status_code < 400
        detail = f"HTTP {r.status_code}"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        passed = False
        detail = str(exc)[:200]
    return CheckResult(
        service=name, tier="heartbeat", passed=passed,
        latency_ms=round(latency, 1), detail=detail,
    )


def run_readiness(name: str) -> CheckResult:
    """Tier 2: functional probe per service type."""
    start = time.monotonic()
    try:
        if name in ("vllm_coordinator", "vllm_coder", "ollama_workshop"):
            port_map = {
                "vllm_coordinator": (FOUNDRY_HOST, 8000, "/models/Qwen3.5-27B-FP8"),
                "vllm_coder": (FOUNDRY_HOST, 8006, "devstral-small-2"),
                "ollama_workshop": (WORKSHOP_HOST, 11434, "huihui_ai/qwen3.5-abliterated:35b"),
            }
            host, port, model_name = port_map[name]
            if port == 11434:  # Ollama
                r = httpx.post(
                    f"http://{host}:{port}/api/generate",
                    json={"model": model_name, "prompt": "Hi", "stream": False, "think": False, "options": {"num_predict": 1}},
                    timeout=30.0,
                )
                passed = r.status_code == 200 and "response" in r.text
            else:  # vLLM
                r = httpx.post(
                    f"http://{host}:{port}/v1/chat/completions",
                    json={"model": model_name, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                    timeout=30.0,
                )
                passed = r.status_code == 200 and "choices" in r.text
            detail = f"HTTP {r.status_code}"

        elif name == "litellm":
            key = _get_litellm_key()
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            r = httpx.post(
                f"{LITELLM_URL}/v1/completions",
                json={"model": "worker", "prompt": "Hi", "max_tokens": 1},
                headers=headers,
                timeout=30.0,
            )
            passed = r.status_code == 200 and "choices" in r.text
            detail = f"HTTP {r.status_code}"

        elif name == "embedding":
            r = httpx.post(
                "http://localhost:8001/v1/embeddings",
                json={"model": "/models/Qwen3-Embedding-0.6B", "input": "test"},
                timeout=15.0,
            )
            passed = r.status_code == 200 and "data" in r.text
            detail = f"HTTP {r.status_code}"

        else:
            return CheckResult(
                service=name, tier="readiness", passed=True,
                latency_ms=0, detail="no specific readiness check",
            )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        return CheckResult(
            service=name, tier="readiness", passed=False,
            latency_ms=round(latency, 1), detail=str(exc)[:200],
        )

    latency = (time.monotonic() - start) * 1000
    return CheckResult(
        service=name, tier="readiness", passed=passed,
        latency_ms=round(latency, 1), detail=detail,
    )


def run_integration() -> list[CheckResult]:
    """Tier 3: cross-service connectivity checks."""
    results = []

    # Dashboard -> Agent Server
    start = time.monotonic()
    try:
        agent_headers = {"Authorization": f"Bearer {_get_agent_key()}"} if _get_agent_key() else {}
        r = httpx.get(f"{AGENT_SERVER_URL}/v1/agents", headers=agent_headers, timeout=15.0)
        latency = (time.monotonic() - start) * 1000
        passed = r.status_code == 200
        detail = f"HTTP {r.status_code}"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        passed = False
        detail = str(exc)[:200]
    results.append(CheckResult(
        service="agent_server_agents", tier="integration",
        passed=passed, latency_ms=round(latency, 1), detail=detail,
    ))

    # Dashboard -> canonical task engine
    start = time.monotonic()
    try:
        agent_headers = {"Authorization": f"Bearer {_get_agent_key()}"} if _get_agent_key() else {}
        r = httpx.get(f"{AGENT_SERVER_URL}/v1/tasks/stats", headers=agent_headers, timeout=10.0)
        latency = (time.monotonic() - start) * 1000
        passed = r.status_code == 200
        detail = f"HTTP {r.status_code}"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        passed = False
        detail = str(exc)[:200]
    results.append(CheckResult(
        service="task_engine_stats", tier="integration",
        passed=passed, latency_ms=round(latency, 1), detail=detail,
    ))

    # Memory -> Qdrant collections
    start = time.monotonic()
    try:
        r = httpx.get(f"{QDRANT_URL}/collections", timeout=10.0)
        latency = (time.monotonic() - start) * 1000
        data = r.json()
        count = len(data.get("result", {}).get("collections", []))
        passed = r.status_code == 200 and count > 0
        detail = f"{count} collections"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        passed = False
        detail = str(exc)[:200]
    results.append(CheckResult(
        service="qdrant_collections", tier="integration",
        passed=passed, latency_ms=round(latency, 1), detail=detail,
    ))

    return results


def send_ntfy_alert(service: str, message: str):
    """Fire ntfy notification."""
    try:
        httpx.post(
            f"{NTFY_URL}/athanor",
            json={
                "topic": "athanor",
                "title": "Sentinel Alert",
                "message": message,
                "priority": 4,
                "tags": ["warning", "sentinel"],
            },
            timeout=5.0,
        )
    except Exception:
        pass  # Don't let alerting failures break the monitor
