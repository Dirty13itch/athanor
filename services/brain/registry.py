"""Resource Registry — knows what the cluster HAS and what models NEED."""
import httpx
import logging

logger = logging.getLogger("brain.registry")

PROMETHEUS = "http://192.168.1.203:9090"

# ── Static hardware inventory ──────────────────────────────────────────
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
        "dcgm_port": 9400,
        "node_exporter_port": 9100,
    },
    "workshop": {
        "ip": "192.168.1.225",
        "gpus": [
            {"id": 0, "name": "RTX 5090", "vram_gb": 32.6, "shared": ["ollama_sovereign", "comfyui"]},
            {"id": 1, "name": "RTX 5060 Ti", "vram_gb": 16.3, "shared": ["ollama_fim", "aesthetic_scorer"]},
        ],
        "ram_gb": 128,
        "dcgm_port": 9400,
    },
    "dev": {
        "ip": "192.168.1.189",
        "gpus": [{"id": 0, "name": "RTX 5060 Ti", "vram_gb": 16.3, "shared": ["embedding", "reranker"]}],
        "ram_gb": 60,
    },
    "vault": {
        "ip": "192.168.1.203",
        "gpus": [],
        "ram_gb": 123,
        "disks": {"nvme0": 932, "nvme1": 932, "nvme2": 932, "array": 164000},
    },
}

# ── Known model requirements ───────────────────────────────────────────
MODELS = {
    "Qwen3.5-27B-FP8": {
        "weights_gb": 7.04, "overhead_gb": 2.0, "min_vram_gb": 10,
        "tp_size": 4, "node": "foundry", "gpus": [0, 1, 3, 4],
    },
    "Devstral-Small-2-AWQ": {
        "aliases": ["devstral-small-2", "coder"],
        "weights_gb": 13.0, "overhead_gb": 3.0, "min_vram_gb": 17,
        "tp_size": 1, "node": "foundry", "gpu": 2,
    },
    "qwen35-abliterated-GGUF": {
        "weights_gb": 18.5, "overhead_gb": 4.5, "min_vram_gb": 24,
        "tp_size": 1, "node": "workshop", "gpu": 0, "runtime": "ollama",
    },
    "qwen2.5-coder-7b": {
        "weights_gb": 4.7, "overhead_gb": 1.0, "min_vram_gb": 6,
        "tp_size": 1, "node": "workshop", "gpu": 1, "runtime": "ollama",
    },
    "Qwen3-Embedding-0.6B": {
        "weights_gb": 1.2, "overhead_gb": 0.5, "min_vram_gb": 2,
        "node": "dev", "gpu": 0,
    },
    "Qwen3-Reranker-0.6B": {
        "weights_gb": 1.2, "overhead_gb": 0.5, "min_vram_gb": 2,
        "node": "dev", "gpu": 0,
    },
}


def query_prometheus(query: str) -> list:
    """Query Prometheus instant API."""
    try:
        r = httpx.get(
            f"{PROMETHEUS}/api/v1/query",
            params={"query": query},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("data", {}).get("result", [])
    except Exception as e:
        logger.warning("Prometheus query failed: %s — %s", query[:60], e)
    return []


def _instance_to_node(instance: str) -> str:
    """Map Prometheus instance label to node name."""
    for name, info in CLUSTER.items():
        if info["ip"] in instance:
            return name
    return instance


def get_gpu_state() -> dict:
    """Per-GPU VRAM, temp, power via Prometheus DCGM metrics."""
    gpus = {}

    mem_used = query_prometheus("DCGM_FI_DEV_FB_USED")
    mem_free = query_prometheus("DCGM_FI_DEV_FB_FREE")
    temp = query_prometheus("DCGM_FI_DEV_GPU_TEMP")
    power = query_prometheus("DCGM_FI_DEV_POWER_USAGE")

    for r in mem_used:
        inst = r["metric"].get("instance", "")
        gid = r["metric"].get("gpu", "")
        node = _instance_to_node(inst)
        key = f"{node}:gpu{gid}"
        gpus.setdefault(key, {"node": node, "gpu_id": int(gid)})
        gpus[key]["vram_used_mb"] = float(r["value"][1])

    for r in mem_free:
        inst = r["metric"].get("instance", "")
        gid = r["metric"].get("gpu", "")
        node = _instance_to_node(inst)
        key = f"{node}:gpu{gid}"
        gpus.setdefault(key, {"node": node, "gpu_id": int(gid)})
        gpus[key]["vram_free_mb"] = float(r["value"][1])
        used = gpus[key].get("vram_used_mb", 0)
        gpus[key]["vram_total_mb"] = used + float(r["value"][1])
        gpus[key]["vram_free_gb"] = round(float(r["value"][1]) / 1024, 2)

    for r in temp:
        inst = r["metric"].get("instance", "")
        gid = r["metric"].get("gpu", "")
        node = _instance_to_node(inst)
        key = f"{node}:gpu{gid}"
        if key in gpus:
            gpus[key]["temp_c"] = float(r["value"][1])

    for r in power:
        inst = r["metric"].get("instance", "")
        gid = r["metric"].get("gpu", "")
        node = _instance_to_node(inst)
        key = f"{node}:gpu{gid}"
        if key in gpus:
            gpus[key]["power_w"] = round(float(r["value"][1]), 1)

    return gpus


def get_ram_state() -> dict:
    """RAM usage per node via Prometheus node_exporter."""
    ram = {}
    total = query_prometheus("node_memory_MemTotal_bytes")
    avail = query_prometheus("node_memory_MemAvailable_bytes")

    for r in total:
        inst = r["metric"].get("instance", "")
        node = _instance_to_node(inst)
        ram.setdefault(node, {})
        ram[node]["total_gb"] = round(float(r["value"][1]) / 1e9, 1)

    for r in avail:
        inst = r["metric"].get("instance", "")
        node = _instance_to_node(inst)
        if node in ram:
            avail_gb = float(r["value"][1]) / 1e9
            ram[node]["available_gb"] = round(avail_gb, 1)
            ram[node]["used_pct"] = round(
                100 * (1 - avail_gb / (ram[node]["total_gb"] or 1)), 1
            )

    return ram


def get_disk_state() -> dict:
    """Disk usage via Prometheus node_exporter."""
    disks = {}
    avail = query_prometheus(
        'node_filesystem_avail_bytes{fstype!="tmpfs",fstype!="overlay"}'
    )
    size = query_prometheus(
        'node_filesystem_size_bytes{fstype!="tmpfs",fstype!="overlay"}'
    )

    for r in avail:
        mount = r["metric"].get("mountpoint", "")
        inst = r["metric"].get("instance", "")
        node = _instance_to_node(inst)
        key = f"{node}:{mount}"
        disks.setdefault(key, {"node": node, "mount": mount})
        disks[key]["avail_gb"] = round(float(r["value"][1]) / 1e9, 1)

    for r in size:
        mount = r["metric"].get("mountpoint", "")
        inst = r["metric"].get("instance", "")
        node = _instance_to_node(inst)
        key = f"{node}:{mount}"
        if key in disks:
            total = float(r["value"][1]) / 1e9
            disks[key]["total_gb"] = round(total, 1)
            disks[key]["used_pct"] = round(
                100 * (1 - disks[key]["avail_gb"] / (total or 1)), 1
            )

    return disks


def get_cluster_state() -> dict:
    """Aggregate live state: GPUs + RAM + disk."""
    return {
        "gpu": get_gpu_state(),
        "ram": get_ram_state(),
        "disk": get_disk_state(),
    }


def get_gpu_for_node(node: str, gpu_id: int) -> dict | None:
    """Get live state for a specific GPU."""
    state = get_gpu_state()
    key = f"{node}:gpu{gpu_id}"
    return state.get(key)


def can_fit(model_id: str, target_node: str, target_gpu: int = 0) -> dict:
    """Pre-flight check: can this model fit on a specific GPU?"""
    model = MODELS.get(model_id)
    if not model:
        return {"fit": False, "reason": f"Unknown model: {model_id}"}

    needed = model["weights_gb"] + model["overhead_gb"]
    gpu_state = get_gpu_for_node(target_node, target_gpu)

    if not gpu_state:
        # Fall back to static spec if Prometheus is down
        node_info = CLUSTER.get(target_node)
        if not node_info:
            return {"fit": False, "reason": f"Unknown node: {target_node}"}
        gpu_specs = [g for g in node_info.get("gpus", []) if g["id"] == target_gpu]
        if not gpu_specs:
            return {"fit": False, "reason": f"No GPU {target_gpu} on {target_node}"}
        return {
            "fit": needed <= gpu_specs[0]["vram_gb"],
            "needed_gb": round(needed, 1),
            "available_gb": gpu_specs[0]["vram_gb"],
            "note": "Using static spec (Prometheus unavailable)",
        }

    available = gpu_state.get("vram_free_gb", 0)

    if needed > available:
        return {
            "fit": False,
            "needed_gb": round(needed, 1),
            "available_gb": round(available, 1),
            "reason": f"Need {needed:.1f}GB but only {available:.1f}GB free",
        }

    return {
        "fit": True,
        "needed_gb": round(needed, 1),
        "available_gb": round(available, 1),
        "headroom_gb": round(available - needed, 1),
    }
