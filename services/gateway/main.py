"""Athanor Gateway - API Gateway with service health aggregation.
Port: 8780 on DEV
"""
import asyncio
from datetime import datetime

import httpx
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cluster_config import (
    AGENT_SERVER_URL, VLLM_CODER_URL, VLLM_COORDINATOR_URL,
    LITELLM_URL, LANGFUSE_URL, QDRANT_URL, COMFYUI_URL,
    WORKSHOP_HOST, DASHBOARD_URL,
)
from fastapi import FastAPI, Query, Response

app = FastAPI(title="Athanor Gateway", version="0.1.0")

SERVICES = {
    "coordinator": {"url": f"{AGENT_SERVER_URL}/health", "node": "foundry"},
    "coder": {"url": f"{VLLM_CODER_URL}/health", "node": "foundry"},
    "vllm-foundry": {"url": f"{VLLM_COORDINATOR_URL}/health", "node": "foundry"},
    "vllm-workshop": {"url": f"http://{WORKSHOP_HOST}:8000/health", "node": "workshop"},
    "litellm": {"url": f"{LITELLM_URL}/health", "node": "vault"},
    "langfuse": {"url": f"{LANGFUSE_URL}/api/public/health", "node": "vault"},
    "qdrant": {"url": f"{QDRANT_URL}/healthz", "node": "vault"},
    "governor": {"url": "http://127.0.0.1:8760/health", "node": "dev"},
    "embedding": {"url": "http://127.0.0.1:8001/health", "node": "dev"},
    "reranker": {"url": "http://127.0.0.1:8003/health", "node": "dev"},
    "dashboard": {"url": f"{DASHBOARD_URL}/api/health", "node": "dev"},
    "comfyui": {"url": f"{COMFYUI_URL}/system_stats", "node": "workshop"},
}

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


async def _check_service(name: str, info: dict) -> dict:
    """Probe a single service and return its health record."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(info["url"])
            return {
                "service": name,
                "node": info["node"],
                "status": "healthy" if resp.status_code < 400 else "degraded",
                "http_status": resp.status_code,
                "response_ms": round(resp.elapsed.total_seconds() * 1000),
            }
    except Exception as exc:
        return {
            "service": name,
            "node": info["node"],
            "status": "unreachable",
            "http_status": None,
            "response_ms": None,
            "error": str(exc)[:120],
        }


@app.get("/health")
async def health(
    response: Response,
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    all_checks = await asyncio.gather(
        *(_check_service(name, info) for name, info in SERVICES.items())
    )
    all_checks = sorted(all_checks, key=lambda c: c["service"])

    total = len(all_checks)
    page = all_checks[offset : offset + limit]

    healthy = sum(1 for c in all_checks if c["status"] == "healthy")

    response.headers["X-Total-Count"] = str(total)

    return {
        "status": "ok" if healthy == total else "degraded",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "healthy": healthy,
        "total": total,
        "limit": limit,
        "offset": offset,
        "services": page,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8780)
