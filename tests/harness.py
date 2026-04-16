#!/usr/bin/env python3
"""Athanor cluster endpoint validation harness.

Evidence producer only; outputs from this harness are proof surfaces for endpoint verification, not runtime or queue authority.
Tests every inference and service endpoint across the cluster.
Writes results to logs/endpoint-tests/<timestamp>.json.
The JSON written by this harness is evidence output only; it does not establish queue posture, runtime authority, or adopted-system routing truth.

Usage:
    python3 tests/harness.py              # full test
    python3 tests/harness.py --quick      # health checks only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from runtime_env import load_runtime_env_contract

load_runtime_env_contract(
    env_names=[
        "ATHANOR_LITELLM_URL",
        "ATHANOR_LITELLM_API_KEY",
        "OPENAI_API_KEY",
    ]
)


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def host_port_from_url(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"http://{value}")
    return parsed.netloc or parsed.path


NODE1_HOST = env("ATHANOR_NODE1_HOST", "192.168.1.244")
NODE2_HOST = env("ATHANOR_NODE2_HOST", "192.168.1.225")
VAULT_HOST = env("ATHANOR_VAULT_HOST", "192.168.1.203")
DEV_HOST = env("ATHANOR_DEV_HOST", "192.168.1.189")
DEFAULT_EMBEDDING_URL = env("ATHANOR_VLLM_EMBEDDING_URL", f"http://{DEV_HOST}:8001")
DEFAULT_RERANKER_URL = env("ATHANOR_VLLM_RERANKER_URL", f"http://{DEV_HOST}:8003")

ENDPOINTS = {
    host_port_from_url(env("ATHANOR_VLLM_COORDINATOR_URL", f"http://{NODE1_HOST}:8000")): {
        "name": "vllm-coordinator",
        "model": "Qwen3.5-27B-FP8",
        "type": "vllm",
    },
    host_port_from_url(
        env("ATHANOR_VLLM_CODER_URL", env("ATHANOR_VLLM_UTILITY_URL", f"http://{NODE1_HOST}:8006"))
    ): {
        "name": "vllm-coder",
        "model": "Qwen3.5-35B-A3B-AWQ-4bit",
        "type": "vllm",
    },
    host_port_from_url(env("ATHANOR_AGENT_SERVER_URL", f"http://{NODE1_HOST}:9000")): {
        "name": "agent-server",
        "type": "agents",
    },
    host_port_from_url(env("ATHANOR_VLLM_WORKER_URL", f"http://{NODE2_HOST}:8000")): {
        "name": "vllm-worker",
        "model": "Qwen3.5-35B-A3B-AWQ-4bit",
        "type": "vllm",
    },
    host_port_from_url(env("ATHANOR_COMFYUI_URL", f"http://{NODE2_HOST}:8188")): {
        "name": "comfyui",
        "type": "comfyui",
    },
    host_port_from_url(env("ATHANOR_DASHBOARD_URL", "http://dev.athanor.local:3001")): {
        "name": "dashboard",
        "type": "http",
    },
    host_port_from_url(env("ATHANOR_LITELLM_URL", f"http://{VAULT_HOST}:4000")): {
        "name": "litellm",
        "type": "litellm",
    },
    host_port_from_url(env("ATHANOR_GRAFANA_URL", f"http://{VAULT_HOST}:3000")): {
        "name": "grafana",
        "type": "http",
    },
    host_port_from_url(env("ATHANOR_LANGFUSE_URL", f"http://{VAULT_HOST}:3030")): {
        "name": "langfuse",
        "type": "http",
    },
    host_port_from_url(DEFAULT_EMBEDDING_URL): {
        "name": "vllm-embedding",
        "model": "Qwen3-Embedding-0.6B",
        "type": "vllm",
    },
    host_port_from_url(DEFAULT_RERANKER_URL): {
        "name": "vllm-reranker",
        "model": "Qwen3-Reranker-0.6B",
        "type": "vllm",
    },
}

LITELLM_KEY = os.environ.get("ATHANOR_LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")


def timed_request(url, timeout=5, headers=None):
    """Make a request and return (response_body, latency_ms, error)."""
    req = Request(url, headers=headers or {})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            latency = (time.monotonic() - start) * 1000
            return body, latency, None
    except (URLError, TimeoutError, OSError) as e:
        latency = (time.monotonic() - start) * 1000
        return None, latency, str(e)


def test_vllm(host_port, info):
    """Test a vLLM endpoint: health + model list."""
    result = {"endpoint": host_port, **info, "checks": {}}

    body, lat, err = timed_request(f"http://{host_port}/health")
    result["checks"]["health"] = {"ok": err is None, "latency_ms": round(lat, 1), "error": err}

    body, lat, err = timed_request(f"http://{host_port}/v1/models")
    if body:
        models = [m["id"] for m in json.loads(body).get("data", [])]
        result["checks"]["models"] = {"ok": True, "models": models, "latency_ms": round(lat, 1)}
    else:
        result["checks"]["models"] = {"ok": False, "error": err, "latency_ms": round(lat, 1)}

    result["healthy"] = all(c["ok"] for c in result["checks"].values())
    return result


def test_agents(host_port, info):
    """Test the agent server health endpoint."""
    result = {"endpoint": host_port, **info, "checks": {}}
    body, lat, err = timed_request(f"http://{host_port}/health")
    if body:
        data = json.loads(body)
        result["checks"]["health"] = {
            "ok": data.get("status") == "ok",
            "agents": data.get("agents", []),
            "latency_ms": round(lat, 1),
        }
    else:
        result["checks"]["health"] = {"ok": False, "error": err, "latency_ms": round(lat, 1)}
    result["healthy"] = all(c["ok"] for c in result["checks"].values())
    return result


def test_litellm(host_port, info):
    """Test LiteLLM proxy: health + model routes."""
    result = {"endpoint": host_port, **info, "checks": {}}

    headers = {"Authorization": f"Bearer {LITELLM_KEY}"} if LITELLM_KEY else {}
    body, lat, err = timed_request(f"http://{host_port}/health/liveliness", headers=headers)
    result["checks"]["health"] = {"ok": err is None, "latency_ms": round(lat, 1), "error": err}

    if not LITELLM_KEY:
        result["checks"]["models"] = {
            "ok": True,
            "skipped": True,
            "error": "missing ATHANOR_LITELLM_API_KEY or OPENAI_API_KEY",
            "latency_ms": 0.0,
        }
        result["healthy"] = result["checks"]["health"]["ok"]
        return result

    body, lat, err = timed_request(f"http://{host_port}/v1/models", headers=headers)
    if body:
        models = [m["id"] for m in json.loads(body).get("data", [])]
        result["checks"]["models"] = {"ok": True, "models": models, "latency_ms": round(lat, 1)}
    else:
        result["checks"]["models"] = {"ok": False, "error": err, "latency_ms": round(lat, 1)}

    result["healthy"] = all(c["ok"] for c in result["checks"].values())
    return result


def test_http(host_port, info):
    """Test a generic HTTP endpoint."""
    result = {"endpoint": host_port, **info, "checks": {}}
    body, lat, err = timed_request(f"http://{host_port}/")
    result["checks"]["reachable"] = {"ok": err is None, "latency_ms": round(lat, 1), "error": err}
    result["healthy"] = err is None
    return result


def test_comfyui(host_port, info):
    """Test ComfyUI endpoint."""
    result = {"endpoint": host_port, **info, "checks": {}}
    body, lat, err = timed_request(f"http://{host_port}/system_stats")
    if body:
        result["checks"]["system_stats"] = {"ok": True, "latency_ms": round(lat, 1)}
    else:
        result["checks"]["system_stats"] = {"ok": False, "error": err, "latency_ms": round(lat, 1)}
    result["healthy"] = all(c["ok"] for c in result["checks"].values())
    return result


TESTERS = {
    "vllm": test_vllm,
    "agents": test_agents,
    "litellm": test_litellm,
    "http": test_http,
    "comfyui": test_comfyui,
}


def main():
    parser = argparse.ArgumentParser(description="Athanor endpoint validation")
    parser.add_argument("--quick", action="store_true", help="Health checks only, no completions")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    results = []
    for host_port, info in ENDPOINTS.items():
        tester = TESTERS.get(info["type"], test_http)
        results.append(tester(host_port, info))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "timestamp": timestamp,
        "surface_class": "evidence_only",
        "authority_note": "Endpoint test evidence only; consult registry-backed reports and the restart brief for current runtime authority.",
        "results": results,
    }

    # Save to log file
    log_dir = Path(__file__).parent.parent / "logs" / "endpoint-tests"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{timestamp}.json"
    log_file.write_text(json.dumps(report, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
        return

    # Pretty print
    healthy = sum(1 for r in results if r["healthy"])
    total = len(results)
    print(f"\nAthanor Endpoint Test — {timestamp}")
    print(f"{'=' * 60}")

    for r in results:
        status = "OK" if r["healthy"] else "FAIL"
        name = r.get("name", r["endpoint"])
        model = r.get("model", "")
        lat = max((c.get("latency_ms", 0) for c in r["checks"].values()), default=0)
        suffix = f" ({model})" if model else ""
        print(f"  [{status:>4}] {r['endpoint']:<22} {name}{suffix:<35} {lat:>6.0f}ms")

    print(f"{'=' * 60}")
    print(f"  {healthy}/{total} healthy — saved to {log_file.name}")

    sys.exit(0 if healthy == total else 1)


if __name__ == "__main__":
    main()
