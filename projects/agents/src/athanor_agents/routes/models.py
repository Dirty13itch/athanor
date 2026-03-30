"""Local model status + GPU management API routes."""

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..config import settings
from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])

VLLM_ENDPOINTS = [
    {"id": "coordinator", "name": "Qwen3.5-27B-FP8", "node": "foundry", "url": settings.coordinator_url},
    {"id": "coder", "name": "devstral-small-2", "node": "foundry", "url": settings.coder_url},
    {"id": "worker", "name": "Qwen3.5-35B-A3B-AWQ-4bit", "node": "workshop", "url": settings.worker_url},
    {"id": "vision", "name": "Qwen3-VL-8B-Instruct-FP8", "node": "workshop", "url": settings.vision_url},
    {"id": "embedding", "name": "Qwen3-Embedding-0.6B", "node": "dev", "url": settings.embedding_url},
    {"id": "reranker", "name": "Reranker", "node": "dev", "url": settings.reranker_url},
]

_DASHBOARD_GPU_SWAP_URL = f"{settings.dashboard_url}/api/gpu/swap"


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    candidate = build_operator_action(body, default_reason=default_reason)
    try:
        action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service="agent-server",
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


@router.get("/models/local")
async def local_models():
    """List locally-deployed vLLM models with health status."""
    models = []

    async with httpx.AsyncClient(timeout=3.0) as client:
        for ep in VLLM_ENDPOINTS:
            model_info = {
                "id": ep["id"],
                "name": ep["name"],
                "node": ep["node"],
                "url": ep["url"],
                "status": "unknown",
            }
            try:
                resp = await client.get(f"{ep['url']}/health")
                model_info["status"] = "online" if resp.status_code == 200 else "degraded"
            except Exception:
                model_info["status"] = "offline"

            try:
                resp = await client.get(f"{ep['url']}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data"):
                        model_data = data["data"][0]
                        model_info["model_id"] = model_data.get("id", "")
                        model_info["max_model_len"] = model_data.get("max_model_len")
            except Exception:
                pass

            models.append(model_info)

    online_count = sum(1 for m in models if m["status"] == "online")
    return {"models": models, "count": len(models), "online": online_count}


async def _run_gpu_swap(mode: str) -> dict:
    """Execute GPU swap via Dashboard API on Workshop."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        if mode == "status":
            resp = await client.get(_DASHBOARD_GPU_SWAP_URL)
        else:
            resp = await client.post(_DASHBOARD_GPU_SWAP_URL, json={"mode": mode})
        resp.raise_for_status()
        return resp.json()


@router.get("/gpu/workshop/status")
async def gpu_workshop_status():
    """Get current Workshop GPU allocation (inference vs creative mode)."""
    try:
        return await _run_gpu_swap("status")
    except Exception as exc:
        logger.error("GPU status check failed: %s", exc)
        return {"mode": "unknown", "error": str(exc)}


@router.post("/gpu/workshop/swap/{mode}")
async def gpu_workshop_swap(mode: str, request: Request):
    """Swap Workshop 5090 between inference and creative mode."""
    _, action, denial = await _load_operator_body(
        request,
        route="/v1/gpu/workshop/swap/{mode}",
        action_class="admin",
        default_reason=f"Requested workshop GPU swap to {mode}",
    )
    if denial:
        return denial

    if mode not in ("creative", "inference"):
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/gpu/workshop/swap/{mode}",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail=f"Invalid mode '{mode}'. Use 'creative' or 'inference'.",
            target=mode,
        )
        return {"error": f"Invalid mode '{mode}'. Use 'creative' or 'inference'."}
    try:
        result = await _run_gpu_swap(mode)
        output = str(result.get("output", "") or "")
        logger.info("GPU swap to %s completed: %s", mode, output[:200])
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/gpu/workshop/swap/{mode}",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Requested workshop GPU swap to {mode}",
            target=mode,
        )
        return result
    except Exception as exc:
        logger.error("GPU swap to %s failed: %s", mode, exc)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/gpu/workshop/swap/{mode}",
            action_class="admin",
            decision="denied",
            status_code=500,
            action=action,
            detail=str(exc),
            target=mode,
        )
        return {"status": "error", "error": str(exc)}
