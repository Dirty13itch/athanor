"""Local model status + GPU management API routes."""

import logging

import httpx
from fastapi import APIRouter

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])

VLLM_ENDPOINTS = [
    {"id": "coordinator", "name": "Qwen3.5-27B-FP8", "node": "foundry", "url": settings.coordinator_url},
    {"id": "coder", "name": "Qwen3.5-35B-A3B-AWQ-4bit", "node": "foundry", "url": settings.coder_url},
    {"id": "worker", "name": "Qwen3.5-35B-A3B-AWQ", "node": "workshop", "url": settings.worker_url},
    {"id": "vision", "name": "Qwen3-VL-8B-Instruct-FP8", "node": "workshop", "url": settings.vision_url},
    {"id": "embedding", "name": "Qwen3-Embedding-0.6B", "node": "dev", "url": settings.embedding_url},
    {"id": "reranker", "name": "Reranker", "node": "dev", "url": settings.reranker_url},
]

# Workshop 5090 GPU swap — time-sharing between vLLM worker and ComfyUI
# Swap is executed via Dashboard API (runs on Workshop, has local access)
_DASHBOARD_GPU_SWAP_URL = f"{settings.dashboard_url}/api/gpu/swap"


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

            # Try to get model info from /v1/models
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
    except Exception as e:
        logger.error("GPU status check failed: %s", e)
        return {"mode": "unknown", "error": str(e)}


@router.post("/gpu/workshop/swap/{mode}")
async def gpu_workshop_swap(mode: str):
    """Swap Workshop 5090 between inference and creative mode.

    Modes:
      - creative: Stop vLLM worker, start ComfyUI (Flux + PuLID)
      - inference: Stop ComfyUI, start vLLM worker
    """
    if mode not in ("creative", "inference"):
        return {"error": f"Invalid mode '{mode}'. Use 'creative' or 'inference'."}
    try:
        result = await _run_gpu_swap(mode)
        output = result.get("output", "")
        logger.info("GPU swap to %s completed: %s", mode, output[:200])
        return result
    except Exception as e:
        logger.error("GPU swap to %s failed: %s", mode, e)
        return {"status": "error", "error": str(e)}
