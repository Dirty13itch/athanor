"""Athanor System Brain — cluster-wide intelligence layer.

Layers 1-2: Resource Registry + Capacity Planner.
Layers 3-4: Lifecycle Manager + Workload Placer.
Port 8780 on DEV, 30s resource refresh, 5min capacity refresh.
"""
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

from auth import build_contract
from operator_contract import build_operator_action, emit_operator_audit_event, require_operator_action
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
SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()
AUTH_CONTRACT = build_contract(service_name="brain")

# ── Cached state ───────────────────────────────────────────────────────
_state: dict = {
    "resources": {},
    "predictions": {},
    "updated_at": None,
}
_health_state: dict[str, str | None] = {
    "resource_last_checked_at": None,
    "resource_error": None,
    "capacity_last_checked_at": None,
    "capacity_error": None,
}

scheduler = BackgroundScheduler()


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
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


def refresh_state():
    """Periodic refresh of cluster resource state (every 30s)."""
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        _state["resources"] = get_cluster_state()
        _state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _health_state["resource_last_checked_at"] = checked_at
        _health_state["resource_error"] = None
        gpu_count = len(_state["resources"].get("gpu", {}))
        logger.info("State refreshed: %d GPUs tracked", gpu_count)
    except Exception as e:
        _health_state["resource_last_checked_at"] = checked_at
        _health_state["resource_error"] = str(e)
        logger.error("State refresh failed: %s", e)


def refresh_capacity():
    """Periodic capacity trend analysis (every 5min)."""
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        _state["predictions"] = get_capacity_report()
        _health_state["capacity_last_checked_at"] = checked_at
        _health_state["capacity_error"] = None
        logger.info("Capacity report refreshed")
    except Exception as e:
        _health_state["capacity_last_checked_at"] = checked_at
        _health_state["capacity_error"] = str(e)
        logger.error("Capacity refresh failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    AUTH_CONTRACT.validate_startup()
    refresh_state()
    refresh_capacity()
    scheduler.add_job(refresh_state, "interval", seconds=30, id="refresh_state")
    scheduler.add_job(refresh_capacity, "interval", minutes=5, id="refresh_capacity")
    scheduler.start()
    logger.info("Brain started — 30s state / 5min capacity refresh")
    yield
    scheduler.shutdown()


app = FastAPI(title="Athanor System Brain", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def bearer_auth_middleware(request: Request, call_next):
    denial = AUTH_CONTRACT.authorize(request)
    if denial is not None:
        return denial
    return await call_next(request)


# ── Layer 1-2: Resource Registry + Capacity Planner ────────────────────

@app.get("/health")
def health():
    dependencies = [
        {
            "id": "resource-refresh",
            "status": "down" if _health_state["resource_error"] else "healthy",
            "required": True,
            "last_checked_at": _health_state["resource_last_checked_at"] or SERVICE_STARTED_AT,
            "detail": _health_state["resource_error"] or f"{len(_state.get('resources', {}).get('gpu', {}))} GPUs tracked",
        },
        {
            "id": "capacity-refresh",
            "status": "down" if _health_state["capacity_error"] else "healthy",
            "required": True,
            "last_checked_at": _health_state["capacity_last_checked_at"] or SERVICE_STARTED_AT,
            "detail": _health_state["capacity_error"] or "Capacity report cached",
        },
        {
            "id": "scheduler",
            "status": "healthy" if getattr(scheduler, "running", False) else "down",
            "required": True,
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "detail": "30s state refresh / 5m capacity refresh",
        },
    ]
    degraded = any(dependency["status"] != "healthy" for dependency in dependencies if dependency["required"])
    last_error = next(
        (dependency["detail"] for dependency in dependencies if dependency["status"] != "healthy"),
        None,
    )
    return {
        "service": "brain",
        "version": app.version,
        "status": "degraded" if degraded else "healthy",
        "auth_class": "admin",
        "dependencies": dependencies,
        "last_error": last_error,
        "started_at": SERVICE_STARTED_AT,
        "actions_allowed": [
            "lifecycle.load",
            "lifecycle.unload",
            "lifecycle.swap-for-comfyui",
        ],
        "port": 8780,
    }


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
async def lifecycle_load(request: Request, model: str, keep_alive: str = "5m"):
    """Load a model into Ollama VRAM."""
    _body, action, denial = await _load_operator_body(
        request,
        route="/lifecycle/load",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial

    try:
        result = await async_load_model(model, keep_alive)
    except Exception as exc:
        await emit_operator_audit_event(
            route="/lifecycle/load",
            action_class="admin",
            decision="denied",
            status_code=500,
            action=action,
            detail=str(exc)[:160],
            target=model,
            metadata={"keep_alive": keep_alive},
        )
        raise

    await emit_operator_audit_event(
        route="/lifecycle/load",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        target=model,
        metadata={"keep_alive": keep_alive},
    )
    return result


@app.post("/lifecycle/unload")
async def lifecycle_unload(request: Request, model: str):
    """Unload a model from Ollama VRAM."""
    _body, action, denial = await _load_operator_body(
        request,
        route="/lifecycle/unload",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial

    try:
        result = await async_unload_model(model)
    except Exception as exc:
        await emit_operator_audit_event(
            route="/lifecycle/unload",
            action_class="admin",
            decision="denied",
            status_code=500,
            action=action,
            detail=str(exc)[:160],
            target=model,
        )
        raise

    await emit_operator_audit_event(
        route="/lifecycle/unload",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        target=model,
    )
    return result


@app.get("/lifecycle/idle")
async def lifecycle_idle(minutes: int = 30):
    """List models idle for longer than N minutes."""
    return await async_get_idle_models(minutes)


@app.post("/lifecycle/swap-for-comfyui")
async def lifecycle_swap(request: Request):
    """Unload sovereign model to free VRAM for ComfyUI on WORKSHOP GPU 0."""
    from_model = "huihui_ai/qwen3.5-abliterated:35b"
    to_model = "none"
    _body, action, denial = await _load_operator_body(
        request,
        route="/lifecycle/swap-for-comfyui",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial

    try:
        result = await swap_models(from_model, to_model)
    except Exception as exc:
        await emit_operator_audit_event(
            route="/lifecycle/swap-for-comfyui",
            action_class="admin",
            decision="denied",
            status_code=500,
            action=action,
            detail=str(exc)[:160],
            target=f"{from_model}->{to_model}",
        )
        raise

    await emit_operator_audit_event(
        route="/lifecycle/swap-for-comfyui",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        target=f"{from_model}->{to_model}",
    )
    return result


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
