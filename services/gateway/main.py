"""Athanor Gateway - API Gateway with service health aggregation.
Port: 8780 on DEV
"""
import asyncio
from datetime import datetime

import httpx
from fastapi import FastAPI, Query, Response

app = FastAPI(title="Athanor Gateway", version="0.1.0")

SERVICES = {
    "coordinator": {"url": "http://192.168.1.244:9000/health", "node": "foundry"},
    "coder": {"url": "http://192.168.1.244:8006/health", "node": "foundry"},
    "vllm-foundry": {"url": "http://192.168.1.244:8000/health", "node": "foundry"},
    "vllm-workshop": {"url": "http://192.168.1.225:8000/health", "node": "workshop"},
    "litellm": {"url": "http://192.168.1.203:4000/health", "node": "vault"},
    "langfuse": {"url": "http://192.168.1.203:3030/api/public/health", "node": "vault"},
    "qdrant": {"url": "http://192.168.1.203:6333/healthz", "node": "vault"},
    "governor": {"url": "http://127.0.0.1:8760/health", "node": "dev"},
    "embedding": {"url": "http://127.0.0.1:8001/health", "node": "dev"},
    "reranker": {"url": "http://127.0.0.1:8003/health", "node": "dev"},
    "dashboard": {"url": "http://192.168.1.225:3001/api/health", "node": "workshop"},
    "comfyui": {"url": "http://192.168.1.225:8188/system_stats", "node": "workshop"},
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
