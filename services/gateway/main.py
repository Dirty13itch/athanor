"""Athanor Gateway - API Gateway with service health aggregation.
Port: 8700 on DEV
"""
import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Query, Response

from _imports import (
    SERVICE_DEFINITIONS,
    get_health_url,
)

app = FastAPI(title="Athanor Gateway", version="0.1.0")
STARTED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

MONITORED_SERVICE_IDS = (
    "agent_server",
    "vllm_coder",
    "vllm_coordinator",
    "vllm_worker",
    "litellm",
    "langfuse",
    "qdrant",
    "embedding",
    "reranker",
    "dashboard",
    "comfyui",
    "quality_gate",
)

SERVICES = {
    service_id: {
        "url": get_health_url(service_id),
        "node": str(SERVICE_DEFINITIONS[service_id]["node"]),
    }
    for service_id in MONITORED_SERVICE_IDS
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


def _dependency_status(check: dict) -> str:
    status = str(check.get("status") or "").lower()
    if status == "healthy":
        return "healthy"
    if status == "degraded":
        return "degraded"
    if status == "unreachable":
        return "down"
    return "unknown"


def _dependency_detail(check: dict) -> str:
    http_status = check.get("http_status")
    response_ms = check.get("response_ms")
    if http_status is not None and response_ms is not None:
        return f"HTTP {http_status} in {response_ms}ms"
    if http_status is not None:
        return f"HTTP {http_status}"
    if check.get("error"):
        return str(check["error"])
    return ""


def build_health_snapshot(all_checks: list[dict], *, timestamp: str) -> dict:
    total = len(all_checks)
    healthy = sum(1 for check in all_checks if check.get("status") == "healthy")
    degraded = total - healthy
    status = "healthy" if degraded == 0 else "degraded"

    return {
        "service": "gateway",
        "version": app.version,
        "status": status,
        "auth_class": "internal_only",
        "dependencies": [
            {
                "id": str(check.get("service") or "unknown"),
                "status": _dependency_status(check),
                "required": True,
                "last_checked_at": timestamp,
                "detail": _dependency_detail(check),
            }
            for check in all_checks
        ],
        "last_error": None if degraded == 0 else f"{degraded} dependency checks degraded or unreachable",
        "started_at": STARTED_AT,
        "actions_allowed": [],
        "network_scope": "internal_only",
        "healthy": healthy,
        "total": total,
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
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    response.headers["X-Total-Count"] = str(total)

    return {
        **build_health_snapshot(all_checks, timestamp=timestamp),
        "timestamp": timestamp,
        "limit": limit,
        "offset": offset,
        "services": page,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8700)
