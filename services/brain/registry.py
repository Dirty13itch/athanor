"""Resource Registry — knows what the cluster HAS and what models NEED."""
import json
import httpx
import time
from dataclasses import dataclass, field
from pathlib import Path

PROMETHEUS = "http://192.168.1.203:9090"
DCGM_ENDPOINTS = {
    "foundry": "http://192.168.1.244:9400",
    "workshop": "http://192.168.1.225:9400",
    "dev": "http://192.168.1.189:9400",
}

# Static hardware inventory
CLUSTER = {
    "foundry": {
        "ip": "192.168.1.244",
        "gpus": [
            {"id": 0, "name": "RTX 5070 Ti", "vram_gb": 16.3},
            {"id": 1, "name": "RTX 5070 Ti", "vram_gb": 16.3},
            {"id": 2, "name": "RTX 4090", "vram_gb": 24.6},
            {"id": 3, "name": "RTX 5070 Ti", "vram_gb": 16.3},
            {"id": 4, "name": "RTX 5070 Ti", "vram_gb": 16.3},
        ],
        "ram_gb": 256,
    },
    "workshop": {
        "ip": "192.168.1.225",
        "gpus": [
            {"id": 0, "name": "RTX 5090", "vram_gb": 32.6},
            {"id": 1, "name": "RTX 5060 Ti", "vram_gb": 16.3},
        ],
        "ram_gb": 128,
    },
    "dev": {
        "ip": "192.168.1.189",
        "gpus": [{"id": 0, "name": "RTX 5060 Ti", "vram_gb": 16.3}],
        "ram_gb": 60,
    },
    "vault": {
        "ip": "192.168.1.203",
        "gpus": [],
        "ram_gb": 123,
        "nvme_mounts": ["/mnt/appdatacache", "/mnt/transcode", "/mnt/docker"],
    },
}

# Known model requirements (calculated from actual deployments)
MODEL_SPECS = {
    "Qwen3.5-27B-FP8": {"weights_gb": 7.04, "overhead_gb": 2.0, "tp_size": 4, "node": "foundry", "port": 8000},
    "Devstral-Small-2-AWQ": {"weights_gb": 13.0, "overhead_gb": 2.0, "tp_size": 1, "node": "foundry", "port": 8006},
    "qwen35-abliterated-GGUF": {"weights_gb": 23.0, "overhead_gb": 5.0, "tp_size": 1, "node": "workshop", "port": 11434, "runtime": "ollama"},
    "qwen2.5-coder-7b": {"weights_gb": 4.7, "overhead_gb": 1.5, "tp_size": 1, "node": "workshop", "port": 11434, "runtime": "ollama"},
    "Qwen3-Embedding-0.6B": {"weights_gb": 1.2, "overhead_gb": 0.5, "tp_size": 1, "node": "dev", "port": 8001},
    "Qwen3-Reranker-0.6B": {"weights_gb": 1.2, "overhead_gb": 0.5, "tp_size": 1, "node": "dev", "port": 8003},
}


def query_prometheus(query: str) -> list:
    """Query Prometheus instant API."""
    try:
        r = httpx.get(f"{PROMETHEUS}/api/v1/query", params={"query": query}, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", {}).get("result", [])
    except Exception:
        pass
    return []


def get_gpu_state() -> dict:
    """Get real-time VRAM usage across all GPUs via Prometheus DCGM metrics."""
    gpus = {}
    
    util_results = query_prometheus("DCGM_FI_DEV_GPU_UTIL")
    mem_used = query_prometheus("DCGM_FI_DEV_FB_USED")
    mem_total = query_prometheus("DCGM_FI_DEV_FB_FREE + DCGM_FI_DEV_FB_USED")
    temp = query_prometheus("DCGM_FI_DEV_GPU_TEMP")
    power = query_prometheus("DCGM_FI_DEV_POWER_USAGE")
    
    for r in mem_used:
        instance = r["metric"].get("instance", "")
        gpu_id = r["metric"].get("gpu", "")
        key = f"{instance}:{gpu_id}"
        gpus.setdefault(key, {"instance": instance, "gpu_id": gpu_id})
        gpus[key]["vram_used_mb"] = float(r["value"][1])
    
    for r in mem_total:
        instance = r["metric"].get("instance", "")
        gpu_id = r["metric"].get("gpu", "")
        key = f"{instance}:{gpu_id}"
        gpus.setdefault(key, {"instance": instance, "gpu_id": gpu_id})
        gpus[key]["vram_total_mb"] = float(r["value"][1])
    
    for r in temp:
        instance = r["metric"].get("instance", "")
        gpu_id = r["metric"].get("gpu", "")
        key = f"{instance}:{gpu_id}"
        if key in gpus:
            gpus[key]["temp_c"] = float(r["value"][1])
    
    for r in power:
        instance = r["metric"].get("instance", "")
        gpu_id = r["metric"].get("gpu", "")
        key = f"{instance}:{gpu_id}"
        if key in gpus:
            gpus[key]["power_w"] = float(r["value"][1])
    
    return gpus


def get_disk_state() -> dict:
    """Get disk usage across nodes via Prometheus node_exporter."""
    disks = {}
    # node_filesystem_avail_bytes and node_filesystem_size_bytes
    avail = query_prometheus('node_filesystem_avail_bytes{fstype!="tmpfs",fstype!="overlay"}')
    size = query_prometheus('node_filesystem_size_bytes{fstype!="tmpfs",fstype!="overlay"}')
    
    for r in avail:
        mount = r["metric"].get("mountpoint", "")
        instance = r["metric"].get("instance", "")
        key = f"{instance}:{mount}"
        disks.setdefault(key, {"instance": instance, "mount": mount})
        disks[key]["avail_gb"] = float(r["value"][1]) / 1e9
    
    for r in size:
        mount = r["metric"].get("mountpoint", "")
        instance = r["metric"].get("instance", "")
        key = f"{instance}:{mount}"
        if key in disks:
            disks[key]["total_gb"] = float(r["value"][1]) / 1e9
            disks[key]["used_pct"] = round(100 * (1 - disks[key]["avail_gb"] / disks[key]["total_gb"]), 1)
    
    return disks


def get_ram_state() -> dict:
    """Get RAM usage per node via Prometheus."""
    ram = {}
    total = query_prometheus("node_memory_MemTotal_bytes")
    avail = query_prometheus("node_memory_MemAvailable_bytes")
    
    for r in total:
        instance = r["metric"].get("instance", "")
        ram.setdefault(instance, {})
        ram[instance]["total_gb"] = float(r["value"][1]) / 1e9
    
    for r in avail:
        instance = r["metric"].get("instance", "")
        if instance in ram:
            ram[instance]["available_gb"] = float(r["value"][1]) / 1e9
            ram[instance]["used_pct"] = round(100 * (1 - ram[instance]["available_gb"] / ram[instance]["total_gb"]), 1)
    
    return ram


def can_fit(model_id: str, target_node: str, target_gpu: int = 0) -> dict:
    """Check if a model can fit on a specific GPU BEFORE attempting to load."""
    spec = MODEL_SPECS.get(model_id)
    if not spec:
        return {"fit": False, "reason": f"Unknown model: {model_id}"}
    
    needed_gb = spec["weights_gb"] + spec["overhead_gb"]
    
    # Get live GPU state
    gpu_state = get_gpu_state()
    node_ip = CLUSTER.get(target_node, {}).get("ip", "")
    
    # Find the target GPU
    target_key = None
    for key, gpu in gpu_state.items():
        if node_ip in gpu["instance"] and gpu["gpu_id"] == str(target_gpu):
            target_key = key
            break
    
    if not target_key:
        return {"fit": False, "reason": f"GPU {target_node}:{target_gpu} not found in metrics"}
    
    gpu = gpu_state[target_key]
    available_gb = (gpu.get("vram_total_mb", 0) - gpu.get("vram_used_mb", 0)) / 1024
    
    if needed_gb > available_gb:
        return {
            "fit": False,
            "needed_gb": round(needed_gb, 1),
            "available_gb": round(available_gb, 1),
            "reason": f"Need {needed_gb:.1f}GB but only {available_gb:.1f}GB free",
        }
    
    return {
        "fit": True,
        "needed_gb": round(needed_gb, 1),
        "available_gb": round(available_gb, 1),
        "headroom_gb": round(available_gb - needed_gb, 1),
    }
