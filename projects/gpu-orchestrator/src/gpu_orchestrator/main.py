"""Athanor GPU Orchestrator -- manages GPU state, vLLM sleep/wake, and Ollama time-sharing.

Phase 2 implementation per ADR-018: GPU monitoring, TTL auto-sleep, manual controls.
Updated 2026-03-23: WORKSHOP worker zone migrated from vLLM to Ollama with native
keep_alive time-sharing (OLLAMA_KEEP_ALIVE=10m). Ollama auto-unloads idle models,
freeing VRAM for ComfyUI without external polling.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response

from .config import settings
from .gpu import (
    GpuMetrics,
    OllamaModelState,
    SleepState,
    VllmInstance,
    check_ollama_health,
    check_ollama_loaded,
    check_vllm_health,
    check_vllm_sleeping,
    fetch_all_gpu_metrics,
    sleep_vllm,
    unload_ollama_model,
    wake_vllm,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --- Zone Definitions ---


class ZoneState(str, Enum):
    ACTIVE = "active"       # GPU in use, workload running
    SLEEPING = "sleeping"   # Model unloaded / vLLM sleeping, VRAM freed
    AVAILABLE = "available" # GPU available for scheduling
    OFFLINE = "offline"     # Node or GPU unreachable


@dataclass
class Zone:
    """A logical GPU allocation zone."""

    name: str
    node: str
    gpus: list[int]
    vllm_url: str | None
    default_workload: str
    sleep_ttl: int  # seconds of idle before auto-sleep
    runtime: str = "vllm"  # "vllm" or "ollama"
    ollama_url: str | None = None
    state: ZoneState = ZoneState.ACTIVE
    last_request_at: float = field(default_factory=time.time)
    vllm_instance: VllmInstance | None = None
    ollama_models: list[OllamaModelState] = field(default_factory=list)
    gpu_metrics: list[GpuMetrics] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "node": self.node,
            "gpus": self.gpus,
            "default_workload": self.default_workload,
            "state": self.state.value,
            "runtime": self.runtime,
            "sleep_ttl": self.sleep_ttl,
            "idle_seconds": round(time.time() - self.last_request_at),
            "ttl_remaining": max(0, self.sleep_ttl - int(time.time() - self.last_request_at)),
            "vllm": self.vllm_instance.to_dict() if self.vllm_instance else None,
            "gpu_metrics": [g.to_dict() for g in self.gpu_metrics],
        }
        if self.runtime == "ollama":
            d["ollama_models"] = [m.to_dict() for m in self.ollama_models]
        return d


# Zone configuration -- updated 2026-03-23
# WORKSHOP GPU 0 (RTX 5090): Ollama sovereign model time-shared with ComfyUI.
# Ollama KEEP_ALIVE=10m handles auto-unload; no vLLM sleep/wake polling needed.
ZONES: dict[str, Zone] = {
    "coordinator": Zone(
        name="coordinator",
        node="node1",
        gpus=[0, 1, 3, 4],
        vllm_url=settings.vllm_node1_url,
        default_workload="vLLM Qwen3.5-27B-FP8 TP=4 (coordinator)",
        sleep_ttl=1800,  # 30 min
        runtime="vllm",
    ),
    "coder": Zone(
        name="coder",
        node="node1",
        gpus=[2],
        vllm_url=settings.vllm_coder_url,
        default_workload="vLLM qwen3-coder-30b (coder)",
        sleep_ttl=1800,  # 30 min
        runtime="vllm",
    ),
    "worker": Zone(
        name="worker",
        node="node2",
        gpus=[0],
        vllm_url=None,  # No vLLM -- Ollama handles model lifecycle
        default_workload="Ollama qwen3.5-abliterated:35b / ComfyUI (time-shared via keep_alive=10m)",
        sleep_ttl=600,  # 10 min -- matches OLLAMA_KEEP_ALIVE
        runtime="ollama",
        ollama_url=settings.ollama_url,
    ),
}


# --- Prometheus Metrics ---


gpu_utilization = Gauge(
    "athanor_gpu_utilization_percent",
    "GPU compute utilization percentage",
    ["node", "gpu_index", "gpu_name"],
)
gpu_vram_used = Gauge(
    "athanor_gpu_vram_used_mb",
    "GPU VRAM used in MB",
    ["node", "gpu_index", "gpu_name"],
)
gpu_vram_total = Gauge(
    "athanor_gpu_vram_total_mb",
    "GPU VRAM total in MB",
    ["node", "gpu_index", "gpu_name"],
)
gpu_temperature = Gauge(
    "athanor_gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["node", "gpu_index", "gpu_name"],
)
gpu_power = Gauge(
    "athanor_gpu_power_watts",
    "GPU power draw in watts",
    ["node", "gpu_index", "gpu_name"],
)
zone_state_gauge = Gauge(
    "athanor_zone_state",
    "Zone state (1=active, 2=sleeping, 3=available, 0=offline)",
    ["zone"],
)
zone_idle_seconds = Gauge(
    "athanor_zone_idle_seconds",
    "Seconds since last request to zone",
    ["zone"],
)
ollama_model_loaded = Gauge(
    "athanor_ollama_model_loaded",
    "Whether an Ollama model is loaded in VRAM (1=yes, 0=no)",
    ["zone", "model"],
)
ollama_model_vram_gb = Gauge(
    "athanor_ollama_model_vram_gb",
    "VRAM used by loaded Ollama model in GB",
    ["zone", "model"],
)
sleep_events = Counter(
    "athanor_gpu_sleep_events_total",
    "Total sleep events",
    ["zone", "trigger"],  # trigger: ttl, manual
)
wake_events = Counter(
    "athanor_gpu_wake_events_total",
    "Total wake events",
    ["zone", "trigger"],  # trigger: request, manual
)
sleep_wake_duration = Histogram(
    "athanor_gpu_sleep_wake_duration_seconds",
    "Duration of sleep/wake operations",
    ["zone", "operation"],
)

STATE_VALUES = {
    ZoneState.ACTIVE: 1,
    ZoneState.SLEEPING: 2,
    ZoneState.AVAILABLE: 3,
    ZoneState.OFFLINE: 0,
}


def update_prometheus_metrics():
    """Update Prometheus gauges from current zone state."""
    for zone in ZONES.values():
        zone_state_gauge.labels(zone=zone.name).set(STATE_VALUES.get(zone.state, 0))
        zone_idle_seconds.labels(zone=zone.name).set(time.time() - zone.last_request_at)

        for gm in zone.gpu_metrics:
            labels = {
                "node": gm.node,
                "gpu_index": str(gm.gpu_index),
                "gpu_name": gm.gpu_name,
            }
            gpu_utilization.labels(**labels).set(gm.utilization_pct)
            gpu_vram_used.labels(**labels).set(gm.vram_used_mb)
            gpu_vram_total.labels(**labels).set(gm.vram_total_mb)
            gpu_temperature.labels(**labels).set(gm.temperature_c)
            gpu_power.labels(**labels).set(gm.power_watts)

        # Ollama model metrics
        if zone.runtime == "ollama":
            for m in zone.ollama_models:
                ollama_model_loaded.labels(zone=zone.name, model=m.name).set(
                    1.0 if m.loaded else 0.0
                )
                ollama_model_vram_gb.labels(zone=zone.name, model=m.name).set(m.vram_gb)


# --- Redis State Persistence ---


REDIS_KEY_PREFIX = "athanor:gpu:"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def save_zone_state(zone: Zone):
    """Persist zone state to Redis."""
    r = await get_redis()
    key = f"{REDIS_KEY_PREFIX}{zone.name}"
    data = {
        "state": zone.state.value,
        "last_request_at": str(zone.last_request_at),
    }
    await r.hset(key, mapping=data)


async def load_zone_state(zone: Zone):
    """Load zone state from Redis (if available)."""
    r = await get_redis()
    key = f"{REDIS_KEY_PREFIX}{zone.name}"
    data = await r.hgetall(key)
    if data:
        try:
            zone.state = ZoneState(data.get("state", "active"))
            zone.last_request_at = float(data.get("last_request_at", time.time()))
        except (ValueError, TypeError):
            pass


# --- Background Tasks ---


_monitor_task: asyncio.Task | None = None
_scheduler_task: asyncio.Task | None = None
_running = False


async def monitor_loop():
    """Poll GPU metrics from DCGM-exporter every 10 seconds."""
    while _running:
        try:
            all_metrics = await fetch_all_gpu_metrics()

            for zone in ZONES.values():
                node_metrics = all_metrics.get(zone.node, [])
                zone.gpu_metrics = [
                    m for m in node_metrics if m.gpu_index in zone.gpus
                ]

                if zone.runtime == "ollama" and zone.ollama_url:
                    # Ollama-managed zone: check model load state via /api/ps
                    models = await check_ollama_loaded(zone.ollama_url)
                    zone.ollama_models = models

                    if models:
                        # At least one model loaded -- zone is active
                        zone.state = ZoneState.ACTIVE
                    else:
                        # No models loaded -- VRAM is free (available for ComfyUI)
                        healthy = await check_ollama_health(zone.ollama_url)
                        if healthy:
                            zone.state = ZoneState.AVAILABLE
                        else:
                            zone.state = ZoneState.OFFLINE

                elif zone.vllm_url:
                    # vLLM-managed zone: check sleep state
                    if zone.vllm_instance is None:
                        zone.vllm_instance = VllmInstance(
                            name=zone.default_workload,
                            url=zone.vllm_url,
                            node=zone.node,
                            gpus=zone.gpus,
                        )
                    sleep_state = await check_vllm_sleeping(zone.vllm_url)
                    zone.vllm_instance.sleep_state = sleep_state
                    zone.vllm_instance.last_checked_at = time.time()

                    # Sync zone state from vLLM
                    if sleep_state == SleepState.SLEEPING:
                        zone.state = ZoneState.SLEEPING
                    elif sleep_state == SleepState.AWAKE:
                        zone.state = ZoneState.ACTIVE
                    elif sleep_state == SleepState.UNAVAILABLE:
                        healthy = await check_vllm_health(zone.vllm_url)
                        if healthy:
                            zone.state = ZoneState.ACTIVE
                        else:
                            zone.state = ZoneState.OFFLINE
                else:
                    # No runtime configured -- check if node is reachable via metrics
                    if zone.gpu_metrics:
                        zone.state = ZoneState.ACTIVE
                    else:
                        zone.state = ZoneState.OFFLINE

                await save_zone_state(zone)

            update_prometheus_metrics()

        except Exception as e:
            logger.error("Monitor loop error: %s", e)

        await asyncio.sleep(10)


async def scheduler_loop():
    """TTL-based auto-sleep: check idle zones every 30 seconds.

    For vLLM zones: sends /sleep API call.
    For Ollama zones: no action needed -- Ollama's native KEEP_ALIVE handles unloading.
    """
    while _running:
        try:
            now = time.time()

            for zone in ZONES.values():
                # Only auto-sleep active vLLM zones (Ollama handles its own TTL)
                if zone.runtime == "ollama":
                    continue  # Ollama KEEP_ALIVE=10m handles this natively
                if zone.state != ZoneState.ACTIVE or zone.vllm_url is None:
                    continue

                idle_seconds = now - zone.last_request_at
                if idle_seconds >= zone.sleep_ttl:
                    logger.info(
                        "Zone %s idle for %ds (TTL: %ds) -- triggering sleep",
                        zone.name, int(idle_seconds), zone.sleep_ttl,
                    )
                    start = time.time()
                    success = await sleep_vllm(zone.vllm_url, level=1)
                    duration = time.time() - start

                    if success:
                        zone.state = ZoneState.SLEEPING
                        sleep_events.labels(zone=zone.name, trigger="ttl").inc()
                        sleep_wake_duration.labels(
                            zone=zone.name, operation="sleep"
                        ).observe(duration)
                        await save_zone_state(zone)

        except Exception as e:
            logger.error("Scheduler loop error: %s", e)

        await asyncio.sleep(30)


async def start_background_tasks():
    """Start monitoring and scheduling loops."""
    global _monitor_task, _scheduler_task, _running
    _running = True

    # Load persisted state
    for zone in ZONES.values():
        await load_zone_state(zone)

    _monitor_task = asyncio.create_task(monitor_loop())
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info("Background tasks started (monitor=10s, scheduler=30s)")


async def stop_background_tasks():
    """Stop background loops."""
    global _running
    _running = False
    if _monitor_task:
        _monitor_task.cancel()
    if _scheduler_task:
        _scheduler_task.cancel()
    if _redis:
        await _redis.aclose()
    logger.info("Background tasks stopped")


# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_background_tasks()
    yield
    await stop_background_tasks()


app = FastAPI(
    title="Athanor GPU Orchestrator",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check."""
    zones_up = sum(1 for z in ZONES.values() if z.state != ZoneState.OFFLINE)
    return {
        "status": "ok",
        "zones_total": len(ZONES),
        "zones_up": zones_up,
    }


@app.get("/status")
async def full_status():
    """Full GPU status across both nodes -- the primary debugging endpoint."""
    total_vram_used = 0.0
    total_vram_total = 0.0

    zones_data = {}
    for name, zone in ZONES.items():
        zones_data[name] = zone.to_dict()
        for gm in zone.gpu_metrics:
            total_vram_used += gm.vram_used_mb
            total_vram_total += gm.vram_total_mb

    return {
        "timestamp": time.time(),
        "summary": {
            "total_gpus": sum(len(z.gpus) for z in ZONES.values()),
            "zones_active": sum(1 for z in ZONES.values() if z.state == ZoneState.ACTIVE),
            "zones_sleeping": sum(1 for z in ZONES.values() if z.state == ZoneState.SLEEPING),
            "zones_available": sum(1 for z in ZONES.values() if z.state == ZoneState.AVAILABLE),
            "zones_offline": sum(1 for z in ZONES.values() if z.state == ZoneState.OFFLINE),
            "total_vram_used_mb": round(total_vram_used, 1),
            "total_vram_total_mb": round(total_vram_total, 1),
            "total_vram_utilization_pct": round(
                (total_vram_used / total_vram_total * 100) if total_vram_total > 0 else 0, 1
            ),
        },
        "zones": zones_data,
    }


@app.get("/gpu/{zone_name}")
async def zone_status(zone_name: str):
    """Get status for a specific GPU zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found. Available: {list(ZONES.keys())}"},
        )
    return zone.to_dict()


@app.post("/gpu/{zone_name}/sleep")
async def zone_sleep(zone_name: str, level: int = 1):
    """Manually put a zone to sleep (unload models)."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )

    if zone.runtime == "ollama" and zone.ollama_url:
        # Ollama zone: unload all loaded models
        if not zone.ollama_models:
            return {"status": "already_sleeping", "zone": zone_name, "runtime": "ollama"}

        unloaded = []
        for m in zone.ollama_models:
            if m.loaded:
                success = await unload_ollama_model(zone.ollama_url, m.name)
                if success:
                    unloaded.append(m.name)

        if unloaded:
            zone.state = ZoneState.AVAILABLE
            zone.ollama_models = []
            sleep_events.labels(zone=zone_name, trigger="manual").inc()
            await save_zone_state(zone)
            return {
                "status": "sleeping",
                "zone": zone_name,
                "runtime": "ollama",
                "unloaded": unloaded,
            }
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to unload Ollama models in zone '{zone_name}'"},
        )

    # vLLM zone
    if not zone.vllm_url:
        return JSONResponse(
            status_code=400,
            content={"error": f"Zone '{zone_name}' has no vLLM instance"},
        )
    if zone.state == ZoneState.SLEEPING:
        return {"status": "already_sleeping", "zone": zone_name}

    start = time.time()
    success = await sleep_vllm(zone.vllm_url, level=level)
    duration = time.time() - start

    if success:
        zone.state = ZoneState.SLEEPING
        sleep_events.labels(zone=zone_name, trigger="manual").inc()
        sleep_wake_duration.labels(zone=zone_name, operation="sleep").observe(duration)
        await save_zone_state(zone)
        return {
            "status": "sleeping",
            "zone": zone_name,
            "level": level,
            "duration_seconds": round(duration, 3),
        }
    return JSONResponse(
        status_code=500,
        content={"error": f"Failed to sleep zone '{zone_name}'. Check vLLM logs."},
    )


@app.post("/gpu/{zone_name}/wake")
async def zone_wake(zone_name: str):
    """Manually wake a sleeping zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )

    if zone.runtime == "ollama":
        # Ollama zones wake on-demand when a request comes in.
        # Nothing to do here -- the next inference request will load the model.
        return {
            "status": "ok",
            "zone": zone_name,
            "runtime": "ollama",
            "message": "Ollama models load on-demand. Next inference request will load the model.",
        }

    if not zone.vllm_url:
        return JSONResponse(
            status_code=400,
            content={"error": f"Zone '{zone_name}' has no vLLM instance"},
        )
    if zone.state == ZoneState.ACTIVE:
        return {"status": "already_awake", "zone": zone_name}

    start = time.time()
    success = await wake_vllm(zone.vllm_url)
    duration = time.time() - start

    if success:
        zone.state = ZoneState.ACTIVE
        zone.last_request_at = time.time()
        wake_events.labels(zone=zone_name, trigger="manual").inc()
        sleep_wake_duration.labels(zone=zone_name, operation="wake").observe(duration)
        await save_zone_state(zone)
        return {
            "status": "awake",
            "zone": zone_name,
            "duration_seconds": round(duration, 3),
        }
    return JSONResponse(
        status_code=500,
        content={"error": f"Failed to wake zone '{zone_name}'. Check vLLM logs."},
    )


@app.post("/gpu/{zone_name}/touch")
async def zone_touch(zone_name: str):
    """Reset the idle timer for a zone (mark it as recently used).

    Call this when routing a request through a zone to prevent auto-sleep.
    """
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    zone.last_request_at = time.time()
    await save_zone_state(zone)
    return {"status": "touched", "zone": zone_name, "last_request_at": zone.last_request_at}


@app.get("/gpu/{zone_name}/ttl")
async def zone_ttl(zone_name: str):
    """Get TTL configuration and remaining time for a zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    idle = time.time() - zone.last_request_at
    return {
        "zone": zone_name,
        "runtime": zone.runtime,
        "sleep_ttl": zone.sleep_ttl,
        "idle_seconds": round(idle),
        "ttl_remaining": max(0, zone.sleep_ttl - int(idle)),
        "auto_sleep_mechanism": (
            "Ollama native KEEP_ALIVE=10m" if zone.runtime == "ollama"
            else "GPU orchestrator TTL polling"
        ),
    }


@app.put("/gpu/{zone_name}/ttl")
async def set_zone_ttl(zone_name: str, request: Request):
    """Update TTL for a zone. Body: {"sleep_ttl": 1800}"""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    body = await request.json()
    new_ttl = body.get("sleep_ttl")
    if new_ttl is None or not isinstance(new_ttl, (int, float)) or new_ttl < 60:
        return JSONResponse(
            status_code=400,
            content={"error": "sleep_ttl must be a number >= 60 seconds"},
        )
    zone.sleep_ttl = int(new_ttl)
    return {"zone": zone_name, "sleep_ttl": zone.sleep_ttl}


@app.get("/zones")
async def list_zones():
    """List all GPU zones with summary info."""
    return {
        "zones": [
            {
                "name": z.name,
                "node": z.node,
                "gpus": z.gpus,
                "state": z.state.value,
                "runtime": z.runtime,
                "workload": z.default_workload,
                "idle_seconds": round(time.time() - z.last_request_at),
            }
            for z in ZONES.values()
        ]
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    update_prometheus_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def main():
    import uvicorn

    logger.info("Starting GPU Orchestrator on %s:%d", settings.host, settings.port)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
