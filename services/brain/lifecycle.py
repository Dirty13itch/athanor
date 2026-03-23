"""Model lifecycle management - load, unload, swap across cluster GPUs."""
import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger("brain.lifecycle")

# Track what is loaded where
_model_state: dict[str, dict] = {}
# Track last access time per model
_last_access: dict[str, float] = {}

OLLAMA_ENDPOINTS = {
    "workshop": "http://192.168.1.225:11434",
}


def get_loaded_models() -> dict:
    """Query what models are actually loaded across the cluster."""
    loaded = {}

    # Check Ollama on WORKSHOP
    try:
        r = httpx.get(f"{OLLAMA_ENDPOINTS['workshop']}/api/ps", timeout=5)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                loaded[m["name"]] = {
                    "node": "workshop", "runtime": "ollama",
                    "vram_gb": m.get("size_vram", 0) / 1e9,
                    "loaded_at": m.get("expires_at", ""),
                }
    except Exception as e:
        logger.warning(f"Cannot query Ollama: {e}")

    # Check vLLM endpoints
    for name, url in [("coordinator", "http://192.168.1.244:8000"), ("coder", "http://192.168.1.244:8006")]:
        try:
            r = httpx.get(f"{url}/v1/models", timeout=5)
            if r.status_code == 200:
                for m in r.json().get("data", []):
                    loaded[m["id"]] = {"node": "foundry", "runtime": "vllm", "url": url}
        except Exception:
            pass

    return loaded


def unload_model(model_name: str, node: str = "workshop") -> dict:
    """Unload a model from Ollama to free VRAM."""
    try:
        r = httpx.post(
            f"{OLLAMA_ENDPOINTS[node]}/api/generate",
            json={"model": model_name, "keep_alive": 0},
            timeout=30
        )
        return {"success": True, "model": model_name, "node": node}
    except Exception as e:
        return {"success": False, "error": str(e)}


def load_model(model_name: str, node: str = "workshop") -> dict:
    """Pre-load a model into Ollama (warm it up)."""
    try:
        r = httpx.post(
            f"{OLLAMA_ENDPOINTS[node]}/api/generate",
            json={"model": model_name, "prompt": "", "keep_alive": "30m"},
            timeout=120
        )
        return {"success": True, "model": model_name, "node": node}
    except Exception as e:
        return {"success": False, "error": str(e)}


def swap_models(unload: str, load: str, node: str = "workshop") -> dict:
    """Unload one model and load another on the same node."""
    result = {"unload": None, "load": None}
    result["unload"] = unload_model(unload, node)
    if result["unload"]["success"]:
        result["load"] = load_model(load, node)
    return result


def get_idle_models(threshold_minutes: int = 120) -> list:
    """Find models that have not been accessed recently."""
    now = datetime.now(timezone.utc).timestamp()
    idle = []
    for model, last in _last_access.items():
        idle_min = (now - last) / 60
        if idle_min > threshold_minutes:
            idle.append({"model": model, "idle_minutes": round(idle_min)})
    return idle


def record_access(model_name: str):
    """Record that a model was just accessed (called by other layers)."""
    _last_access[model_name] = datetime.now(timezone.utc).timestamp()
