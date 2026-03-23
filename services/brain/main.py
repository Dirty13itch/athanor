"""Athanor System Brain — cluster-wide intelligence layer.

Layers 1-2: Resource Registry + Capacity Planner.
Layers 3-4: Lifecycle Manager + Workload Placer.
Port 8780 on DEV, 30s resource refresh, 5min capacity refresh.
"""
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from registry import CLUSTER, MODELS, can_fit, get_cluster_state
from capacity import predict_disk_full, detect_memory_leaks, get_capacity_report
from lifecycle import (
    get_loaded_models, async_load_model, async_unload_model,
    async_get_idle_models, swap_models,
)
from placer import recommend_placement, find_available_gpu, suggest_migrations
from quality import recommend_model, MODEL_PROFILES
from cost import get_cost_summary
from advisor import generate_briefing


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain")

# ── Cached state ───────────────────────────────────────────────────────
_state: dict = {
    "resources": {},
    "predictions": {},
    "updated_at": None,
}

scheduler = BackgroundScheduler()


def refresh_state():
    """Periodic refresh of cluster resource state (every 30s)."""
    try:
        _state["resources"] = get_cluster_state()
        _state["updated_at"] = datetime.now(timezone.utc).isoformat()
        gpu_count = len(_state["resources"].get("gpu", {}))
        logger.info("State refreshed: %d GPUs tracked", gpu_count)
    except Exception as e:
        logger.error("State refresh failed: %s", e)


def refresh_capacity():
    """Periodic capacity trend analysis (every 5min)."""
    try:
        _state["predictions"] = get_capacity_report()
        logger.info("Capacity report refreshed")
    except Exception as e:
        logger.error("Capacity refresh failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    refresh_state()
    refresh_capacity()
    scheduler.add_job(refresh_state, "interval", seconds=30, id="refresh_state")
    scheduler.add_job(refresh_capacity, "interval", minutes=5, id="refresh_capacity")
    scheduler.start()
    logger.info("Brain started — 30s state / 5min capacity refresh")
    yield
    scheduler.shutdown()


app = FastAPI(title="Athanor System Brain", version="0.1.0", lifespan=lifespan)


# ── Layer 1-2: Resource Registry + Capacity Planner ────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "brain", "port": 8780}


@app.get("/status")
def status():
    """Full cached state — resources + predictions + timestamp."""
    return _state


@app.get("/resources")
def resources():
    """Live cluster resource state (GPU/RAM/disk)."""
    return get_cluster_state()


@app.get("/can-fit")
def check_fit(model: str, node: str, gpu: int = 0):
    """Pre-flight check: can this model fit on this GPU?"""
    return can_fit(model, node, gpu)


@app.get("/capacity")
def capacity():
    """Capacity trends and predictions."""
    return _state.get("predictions", {})


@app.get("/gpu")
def gpu_state():
    """Real-time GPU state from cache."""
    return _state.get("resources", {}).get("gpu", {})


@app.get("/ram")
def ram_state():
    """RAM usage per node from cache."""
    return _state.get("resources", {}).get("ram", {})


@app.get("/disk")
def disk_state():
    """Disk usage from cache."""
    return _state.get("resources", {}).get("disk", {})


@app.get("/models")
def models():
    """Known model requirements."""
    return MODELS


@app.get("/cluster")
def cluster():
    """Static cluster hardware inventory."""
    return CLUSTER


# ── Layer 3: Lifecycle Manager ─────────────────────────────────────────

@app.get("/lifecycle/loaded")
async def lifecycle_loaded():
    """List all currently loaded models (Ollama + vLLM)."""
    return get_loaded_models()


@app.post("/lifecycle/load")
async def lifecycle_load(model: str, keep_alive: str = "5m"):
    """Load a model into Ollama VRAM."""
    return await async_load_model(model, keep_alive)


@app.post("/lifecycle/unload")
async def lifecycle_unload(model: str):
    """Unload a model from Ollama VRAM."""
    return await async_unload_model(model)


@app.get("/lifecycle/idle")
async def lifecycle_idle(minutes: int = 30):
    """List models idle for longer than N minutes."""
    return await async_get_idle_models(minutes)


@app.post("/lifecycle/swap-for-comfyui")
async def lifecycle_swap():
    """Unload sovereign model to free VRAM for ComfyUI on WORKSHOP GPU 0."""
    return await swap_models("huihui_ai/qwen3.5-abliterated:35b", "none")


# ── Layer 4: Workload Placer ───────────────────────────────────────────

@app.get("/placer/recommend")
def placer_recommend(model: str):
    """Recommend best GPU placement for a model."""
    return recommend_placement(model)


@app.get("/placer/available")
def placer_available(min_vram_gb: float = 8.0):
    """List GPUs with at least N GB free VRAM."""
    return find_available_gpu(min_vram_gb)


@app.get("/placer/migrations")
def placer_migrations():
    """Suggest model migrations to rebalance GPU load."""
    return suggest_migrations()


# -- Layers 5-7: Quality Router + Cost + Advisor --

@app.get("/quality/recommend")
def quality_recommend(task_type: str = "coding", complexity: str = "medium", content_class: str = "cloud_safe"):
    return recommend_model(task_type, complexity, content_class)

@app.get("/quality/profiles")
def quality_profiles():
    return MODEL_PROFILES

@app.get("/cost/summary")
def cost_summary():
    return get_cost_summary()

@app.get("/advisor/briefing")
def advisor_briefing():
    return generate_briefing(
        _state.get("resources", {}),
        _state.get("predictions", {}),
        {},
        get_cost_summary()
    )
