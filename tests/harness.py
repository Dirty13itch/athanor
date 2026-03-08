#!/usr/bin/env python3
"""Athanor cluster endpoint validation harness.

Tests every inference and service endpoint across the cluster.
Writes results to logs/endpoint-tests/<timestamp>.json.

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
from urllib.request import urlopen, Request
from urllib.error import URLError

ENDPOINTS = {
    "foundry:8000": {"name": "vllm-reasoning", "model": "Qwen3-32B-AWQ", "type": "vllm"},
    "foundry:8002": {"name": "vllm-coding", "model": "GLM-4.7-Flash-GPTQ-4bit", "type": "vllm"},
    "foundry:8004": {"name": "vllm-creative", "model": "Huihui-Qwen3-8B", "type": "vllm"},
    "foundry:9000": {"name": "agent-server", "type": "agents"},
    "workshop:8000": {"name": "vllm-worker", "model": "Qwen3.5-35B-A3B-AWQ-4bit", "type": "vllm"},
    "workshop:8188": {"name": "comfyui", "type": "comfyui"},
    "workshop:3001": {"name": "dashboard", "type": "http"},
    "vault:4000": {"name": "litellm", "type": "litellm"},
    "vault:3000": {"name": "grafana", "type": "http"},
    "vault:3030": {"name": "langfuse", "type": "http"},
    "localhost:8001": {"name": "vllm-embedding", "model": "Qwen3-Embedding-0.6B", "type": "vllm"},
    "localhost:8003": {"name": "vllm-reranker", "model": "Qwen3-Reranker-0.6B", "type": "vllm"},
}

LITELLM_KEY = os.environ.get("OPENAI_API_KEY", "sk-athanor-litellm-2026")


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

    headers = {"Authorization": f"Bearer {LITELLM_KEY}"}
    body, lat, err = timed_request(f"http://{host_port}/health", headers=headers)
    result["checks"]["health"] = {"ok": err is None, "latency_ms": round(lat, 1), "error": err}

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
    report = {"timestamp": timestamp, "results": results}

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
