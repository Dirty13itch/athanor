"""Layer 3: Lifecycle Manager - model loading/unloading via Ollama and Docker APIs.

Provides both sync helpers (for internal use) and async endpoint handlers
(for FastAPI routes). Tracks loaded models across Ollama and vLLM.
"""
import httpx
import time
import logging
from datetime import datetime, timezone

from registry import CLUSTER, MODELS, query_prometheus

logger = logging.getLogger("brain.lifecycle")

OLLAMA_ENDPOINTS = {
    "workshop": "http://192.168.1.225:11434",
}

VLLM_ENDPOINTS = [
    ("coordinator", "http://192.168.1.244:8000"),
    ("coder", "http://192.168.1.244:8006"),
    ("embedding", "http://192.168.1.189:8001"),
    ("reranker", "http://192.168.1.189:8003"),
]

# Track last access time per model (updated on list/load)
_last_access: dict[str, float] = {}


# -- Sync helpers (used internally and by other layers) --

def get_loaded_models() -> dict:
    """Query what models are actually loaded across the cluster (sync)."""
    loaded = {}

    try:
        r = httpx.get(f"{OLLAMA_ENDPOINTS['workshop']}/api/ps", timeout=5)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                name = m.get("name", "")
                loaded[name] = {
                    "node": "workshop", "runtime": "ollama",
                    "vram_gb": round(m.get("size_vram", 0) / 1e9, 2),
                    "size_gb": round(m.get("size", 0) / 1e9, 2),
                    "expires_at": m.get("expires_at", ""),
                    "digest": m.get("digest", "")[:12],
                }
                _last_access[name] = time.time()
    except Exception as e:
        logger.warning("Cannot query Ollama: %s", e)

    for label, url in VLLM_ENDPOINTS:
        try:
            r = httpx.get(f"{url}/v1/models", timeout=5)
            if r.status_code == 200:
                for m in r.json().get("data", []):
                    loaded[m["id"]] = {
                        "node": "foundry", "runtime": "vllm", "endpoint": url,
                    }
        except Exception:
            pass

    return loaded


def record_access(model_name: str):
    """Record that a model was just accessed (called by other layers)."""
    _last_access[model_name] = time.time()


def load_model(model_name: str, node: str = "workshop") -> dict:
    """Sync: pre-load a model into Ollama."""
    try:
        httpx.post(
            f"{OLLAMA_ENDPOINTS[node]}/api/generate",
            json={"model": model_name, "prompt": "", "keep_alive": "30m"},
            timeout=120,
        )
        _last_access[model_name] = time.time()
        return {"success": True, "model": model_name, "node": node}
    except Exception as e:
        return {"success": False, "error": str(e)}


def unload_model(model_name: str, node: str = "workshop") -> dict:
    """Sync: unload a model from Ollama."""
    try:
        httpx.post(
            f"{OLLAMA_ENDPOINTS[node]}/api/generate",
            json={"model": model_name, "keep_alive": 0},
            timeout=30,
        )
        _last_access.pop(model_name, None)
        return {"success": True, "model": model_name, "node": node}
    except Exception as e:
        return {"success": False, "error": str(e)}


def swap_models(unload_name: str, load_name: str, node: str = "workshop") -> dict:
    """Sync: unload one model and load another on the same node."""
    result = {"unload": None, "load": None}
    result["unload"] = unload_model(unload_name, node)
    if result["unload"].get("success"):
        result["load"] = load_model(load_name, node)
    return result


def get_idle_models(threshold_minutes: int = 120) -> list:
    """Sync: find models not accessed recently (from internal tracking)."""
    now = time.time()
    idle = []
    for model, last in _last_access.items():
        idle_min = (now - last) / 60
        if idle_min > threshold_minutes:
            idle.append({"model": model, "idle_minutes": round(idle_min)})
    return idle


# -- Async handlers (called by FastAPI endpoints) --

async def list_loaded_models() -> dict:
    """Async version: query Ollama + vLLM for loaded models."""
    loaded = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{OLLAMA_ENDPOINTS['workshop']}/api/ps")
            r.raise_for_status()
            data = r.json()

        for m in data.get("models", []):
            name = m.get("name", "")
            loaded.append({
                "name": name,
                "size_gb": round(m.get("size", 0) / 1e9, 2),
                "vram_gb": round(m.get("size_vram", 0) / 1e9, 2),
                "expires_at": m.get("expires_at", ""),
                "digest": m.get("digest", "")[:12],
                "runtime": "ollama",
                "node": "workshop",
            })
            _last_access[name] = time.time()
    except Exception as e:
        logger.error("Ollama query failed: %s", e)

    for label, url in VLLM_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{url}/v1/models")
                if r.status_code == 200:
                    for m in r.json().get("data", []):
                        loaded.append({
                            "name": m["id"],
                            "runtime": "vllm",
                            "node": "foundry",
                            "endpoint": url,
                        })
        except Exception:
            pass

    return {"loaded": loaded}


async def async_load_model(model_name: str, keep_alive: str = "5m") -> dict:
    """Async: load a model into Ollama VRAM."""
    logger.info("Loading model: %s (keep_alive=%s)", model_name, keep_alive)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{OLLAMA_ENDPOINTS['workshop']}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": keep_alive},
            )
            r.raise_for_status()

        _last_access[model_name] = time.time()
        return {"status": "loaded", "model": model_name, "keep_alive": keep_alive}
    except Exception as e:
        logger.error("Failed to load %s: %s", model_name, e)
        return {"status": "error", "model": model_name, "error": str(e)}


async def async_unload_model(model_name: str) -> dict:
    """Async: unload a model from Ollama VRAM (keep_alive=0)."""
    logger.info("Unloading model: %s", model_name)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{OLLAMA_ENDPOINTS['workshop']}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": "0"},
            )
            r.raise_for_status()

        _last_access.pop(model_name, None)
        return {"status": "unloaded", "model": model_name}
    except Exception as e:
        logger.error("Failed to unload %s: %s", model_name, e)
        return {"status": "error", "model": model_name, "error": str(e)}


async def async_get_idle_models(idle_minutes: int = 30) -> list:
    """Find Ollama models idle for longer than N minutes."""
    now = time.time()
    threshold = now - (idle_minutes * 60)
    idle = []

    loaded = await list_loaded_models()
    for m in loaded.get("loaded", []):
        if m.get("runtime") != "ollama":
            continue
        name = m.get("name", "")
        if not name:
            continue
        last_used = _last_access.get(name, 0)

        if last_used == 0:
            prom_query = 'ollama_request_duration_seconds_count{model="' + name + '"}'
            results = query_prometheus(prom_query)
            if results:
                last_used = float(results[0].get("value", [0, 0])[0])

        if last_used < threshold:
            idle.append({
                "name": name,
                "vram_gb": m.get("vram_gb", 0),
                "idle_minutes": round((now - last_used) / 60, 1) if last_used > 0 else None,
            })

    return idle


async def swap_for_comfyui() -> dict:
    """Unload sovereign model from WORKSHOP GPU 0 to free VRAM for ComfyUI."""
    results = {"unloaded": [], "errors": [], "freed_vram_gb": 0}

    loaded = await list_loaded_models()
    ollama_loaded = [m for m in loaded.get("loaded", []) if m.get("runtime") == "ollama"]

    targets = [m for m in ollama_loaded if m.get("vram_gb", 0) > 10]
    if not targets:
        targets = [
            m for m in ollama_loaded
            if any(p in m.get("name", "").lower() for p in ["qwen3", "abliterated"])
        ]

    for m in targets:
        name = m["name"]
        result = await async_unload_model(name)
        if result["status"] == "unloaded":
            results["unloaded"].append(name)
            results["freed_vram_gb"] += m.get("vram_gb", 0)
        else:
            results["errors"].append(result)

    if not results["unloaded"] and not results["errors"]:
        results["message"] = "No sovereign models found loaded on WORKSHOP"

    return results
