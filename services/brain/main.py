"""Athanor System Brain — cluster-wide intelligence layer."""
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import time
import logging

from registry import (
    CLUSTER, MODEL_SPECS, can_fit,
    get_gpu_state, get_disk_state, get_ram_state,
)
from capacity import get_capacity_report, predict_disk_full, detect_ram_leaks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain")

# Cache for expensive queries
_cache = {"gpu": {}, "disk": {}, "ram": {}, "capacity": {}, "updated_at": 0}


def refresh_state():
    """Periodic refresh of cluster resource state."""
    try:
        _cache["gpu"] = get_gpu_state()
        _cache["disk"] = get_disk_state()
        _cache["ram"] = get_ram_state()
        _cache["updated_at"] = time.time()
        logger.info("State refreshed: %d GPUs, %d disks", len(_cache["gpu"]), len(_cache["disk"]))
    except Exception as e:
        logger.error("State refresh failed: %s", e)


def refresh_capacity():
    """Periodic capacity trend analysis."""
    try:
        _cache["capacity"] = get_capacity_report()
        logger.info("Capacity report refreshed")
    except Exception as e:
        logger.error("Capacity refresh failed: %s", e)


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    refresh_state()
    scheduler.add_job(refresh_state, "interval", seconds=30)
    scheduler.add_job(refresh_capacity, "interval", minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Athanor System Brain", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "cache_age_s": round(time.time() - _cache["updated_at"], 1)}


@app.get("/status")
def status():
    """Full cluster resource state."""
    return {
        "cluster": CLUSTER,
        "gpu_state": _cache.get("gpu", {}),
        "disk_state": _cache.get("disk", {}),
        "ram_state": _cache.get("ram", {}),
        "models": MODEL_SPECS,
        "updated_at": _cache.get("updated_at", 0),
    }


@app.get("/can-fit")
def check_fit(model: str, node: str, gpu: int = 0):
    """Pre-flight check: can this model fit on this GPU?"""
    return can_fit(model, node, gpu)


@app.get("/capacity")
def capacity():
    """Capacity trends and predictions."""
    return _cache.get("capacity", {})


@app.get("/gpu")
def gpu_state():
    """Real-time GPU state across all nodes."""
    return _cache.get("gpu", {})


@app.get("/disk")
def disk_state():
    """Disk usage and trends."""
    return {
        "current": _cache.get("disk", {}),
        "predictions": {
            "nvme0": predict_disk_full("appdatacache"),
        },
    }


@app.get("/ram")
def ram_state():
    """RAM usage per node + leak detection."""
    return {
        "current": _cache.get("ram", {}),
        "leaks": detect_ram_leaks(),
    }


@app.get("/models")
def models():
    """Known model requirements."""
    return MODEL_SPECS
