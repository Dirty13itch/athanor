"""Athanor Sentinel -- Check definitions and runners."""

import time
import httpx
from dataclasses import dataclass, field
from pathlib import Path

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

HEARTBEAT_CHECKS = [
    ("gateway", "http://localhost:8700/health"),
    ("mind", "http://localhost:8710/health"),
    ("memory", "http://localhost:8720/health"),
    ("governor", "http://localhost:8760/health"),
    ("classifier", "http://localhost:8740/health"),
    ("dashboard", "http://localhost:3001/"),
    ("embedding", "http://localhost:8001/v1/models"),
    ("reranker", "http://localhost:8003/v1/models"),
    ("semantic_router", "http://localhost:8060/health"),
    ("burn_scheduler", "http://localhost:8065/health"),
    ("litellm", "http://192.168.1.203:4000/health"),
    ("qdrant", "http://192.168.1.203:6333/healthz"),
    ("prometheus", "http://192.168.1.203:9090/-/healthy"),
    ("ntfy", "http://192.168.1.203:8880/v1/health"),
    ("agent_server", "http://192.168.1.244:9000/health"),
    ("vllm_coordinator", "http://192.168.1.244:8000/health"),
    ("vllm_coder", "http://192.168.1.244:8006/health"),
    ("ollama_sovereign", "http://192.168.1.225:11434/api/tags"),
    ("comfyui", "http://192.168.1.225:8188/system_stats"),
    ("ollama", "http://192.168.1.225:11434/api/tags"),
]

# Services that need Authorization header
AUTH_SERVICES = {"litellm", "agent_server"}

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
        if name in ("vllm_coordinator", "vllm_coder", "vllm_sovereign"):
            port_map = {
                "vllm_coordinator": ("192.168.1.244", 8000),
                "vllm_coder": ("192.168.1.244", 8006),
                "vllm_sovereign": ("192.168.1.225", 8010),
            }
            host, port = port_map[name]
            r = httpx.post(
                f"http://{host}:{port}/v1/completions",
                json={"model": "default", "prompt": "Hi", "max_tokens": 1},
                timeout=30.0,
            )
            passed = r.status_code == 200 and "choices" in r.text
            detail = f"HTTP {r.status_code}"

        elif name == "litellm":
            key = _get_litellm_key()
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            r = httpx.post(
                "http://192.168.1.203:4000/v1/completions",
                json={"model": "worker", "prompt": "Hi", "max_tokens": 1},
                headers=headers,
                timeout=30.0,
            )
            passed = r.status_code == 200 and "choices" in r.text
            detail = f"HTTP {r.status_code}"

        elif name == "embedding":
            r = httpx.post(
                "http://localhost:8001/v1/embeddings",
                json={"model": "default", "input": "test"},
                timeout=15.0,
            )
            passed = r.status_code == 200 and "data" in r.text
            detail = f"HTTP {r.status_code}"

        elif name == "governor":
            r = httpx.get("http://localhost:8760/health", timeout=10.0)
            passed = r.status_code == 200
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
        r = httpx.get("http://192.168.1.244:9000/v1/agents", headers=agent_headers, timeout=15.0)
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

    # Dashboard -> Governor queue
    start = time.monotonic()
    try:
        r = httpx.get("http://localhost:8760/api/governor/queue", timeout=10.0)
        latency = (time.monotonic() - start) * 1000
        passed = r.status_code == 200
        detail = f"HTTP {r.status_code}"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        passed = False
        detail = str(exc)[:200]
    results.append(CheckResult(
        service="governor_queue", tier="integration",
        passed=passed, latency_ms=round(latency, 1), detail=detail,
    ))

    # Memory -> Qdrant collections
    start = time.monotonic()
    try:
        r = httpx.get("http://192.168.1.203:6333/collections", timeout=10.0)
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
            "http://192.168.1.203:8880/athanor",
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
