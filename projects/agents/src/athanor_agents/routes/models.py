"""Local model status API routes."""

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
    {"id": "embedding", "name": "Qwen3-Embedding-0.6B", "node": "dev", "url": settings.embedding_url},
    {"id": "reranker", "name": "Reranker", "node": "dev", "url": settings.reranker_url},
]


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
