"""Local model status + GPU management API routes."""

import asyncio
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
_GPU_SWAP_SCRIPT = "/opt/athanor/gpu-swap.sh"


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
    """Execute GPU swap script on Workshop via SSH.

    Uses create_subprocess_exec (not shell) with validated mode argument.
    """
    proc = await asyncio.create_subprocess_exec(
        "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
        "athanor@192.168.1.225", f"{_GPU_SWAP_SCRIPT} {mode}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    output = stdout.decode().strip()
    if proc.returncode != 0:
        error = stderr.decode().strip()
        raise RuntimeError(f"GPU swap failed (exit {proc.returncode}): {error or output}")
    return {"mode": mode, "output": output}


@router.get("/gpu/workshop/status")
async def gpu_workshop_status():
    """Get current Workshop GPU allocation (inference vs creative mode)."""
    try:
        result = await _run_gpu_swap("status")
        lines = result["output"].split("\n")
        mode = "unknown"
        for line in lines:
            if line.startswith("MODE:"):
                mode = line.split(":", 1)[1].strip()
        return {"mode": mode, "detail": lines}
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
        logger.info("GPU swap to %s completed: %s", mode, result["output"][:200])
        return {"status": "ok", **result}
    except Exception as e:
        logger.error("GPU swap to %s failed: %s", mode, e)
        return {"status": "error", "error": str(e)}
