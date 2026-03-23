"""Layer 4: Workload Placer - intelligent GPU placement and migration suggestions."""
import logging
from typing import Optional

from registry import CLUSTER, MODELS, get_gpu_state, can_fit

logger = logging.getLogger("brain.placer")


def _parse_gpu_states() -> list[dict]:
    """Get a flat list of GPUs with computed free VRAM from live metrics."""
    gpu_state = get_gpu_state()
    gpus = []
    for key, gpu in gpu_state.items():
        node = gpu.get("node", key.split(":")[0])
        gpu_id = gpu.get("gpu_id", 0)
        total_mb = gpu.get("vram_total_mb", 0)
        used_mb = gpu.get("vram_used_mb", 0)
        free_gb = gpu.get("vram_free_gb", round((total_mb - used_mb) / 1024, 2))

        # Resolve GPU name from static inventory
        gpu_name = "unknown"
        node_info = CLUSTER.get(node, {})
        for g in node_info.get("gpus", []):
            if g["id"] == gpu_id:
                gpu_name = g["name"]
                break

        gpus.append({
            "node": node,
            "gpu_id": gpu_id,
            "name": gpu_name,
            "vram_total_gb": round(total_mb / 1024, 2) if total_mb else 0,
            "vram_used_gb": round(used_mb / 1024, 2) if used_mb else 0,
            "vram_free_gb": free_gb,
            "usage_pct": round(used_mb / total_mb * 100, 1) if total_mb > 0 else 0,
            "temp_c": gpu.get("temp_c"),
            "power_w": gpu.get("power_w"),
        })
    return gpus


def recommend_placement(model_id: str) -> dict:
    """Given a model, find the best GPU with enough VRAM.

    Ranking:
    1. Must have enough free VRAM (weights + overhead)
    2. Prefer lowest utilization (spread load)
    3. Prefer the node the model is already specced for (locality bonus)
    """
    spec = MODELS.get(model_id)
    if not spec:
        return {"error": f"Unknown model: {model_id}", "candidates": []}

    needed_gb = spec["weights_gb"] + spec["overhead_gb"]
    preferred_node = spec.get("node")
    tp_size = spec.get("tp_size", 1)

    gpus = _parse_gpu_states()

    if tp_size > 1:
        return _recommend_tp_placement(model_id, needed_gb, tp_size, preferred_node, gpus)

    candidates = []
    for gpu in gpus:
        if gpu["vram_free_gb"] >= needed_gb:
            score = 100 - gpu["usage_pct"]
            if gpu["node"] == preferred_node:
                score += 20
            candidates.append({**gpu, "score": round(score, 1)})

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return {
            "model": model_id,
            "needed_gb": needed_gb,
            "error": f"No single GPU has {needed_gb:.1f}GB free",
            "candidates": [],
            "all_gpus": gpus,
        }

    best = candidates[0]
    return {
        "model": model_id,
        "needed_gb": needed_gb,
        "recommended": {
            "node": best["node"],
            "gpu_id": best["gpu_id"],
            "gpu_name": best["name"],
            "vram_free_gb": best["vram_free_gb"],
            "headroom_gb": round(best["vram_free_gb"] - needed_gb, 2),
            "score": best["score"],
        },
        "alternatives": candidates[1:5],
    }


def _recommend_tp_placement(
    model_id: str, needed_gb: float, tp_size: int,
    preferred_node: Optional[str], gpus: list[dict]
) -> dict:
    """Handle tensor-parallel placement across multiple GPUs on one node."""
    per_gpu_gb = needed_gb / tp_size

    by_node: dict[str, list[dict]] = {}
    for gpu in gpus:
        by_node.setdefault(gpu["node"], []).append(gpu)

    candidates = []
    for node, node_gpus in by_node.items():
        eligible = [g for g in node_gpus if g["vram_free_gb"] >= per_gpu_gb]
        if len(eligible) >= tp_size:
            eligible.sort(key=lambda x: x["vram_free_gb"], reverse=True)
            selected = eligible[:tp_size]
            avg_free = sum(g["vram_free_gb"] for g in selected) / tp_size
            score = avg_free - per_gpu_gb
            if node == preferred_node:
                score += 10
            candidates.append({
                "node": node,
                "gpus": [{"gpu_id": g["gpu_id"], "vram_free_gb": g["vram_free_gb"]} for g in selected],
                "per_gpu_needed_gb": round(per_gpu_gb, 2),
                "score": round(score, 2),
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return {
            "model": model_id,
            "needed_gb": needed_gb,
            "tp_size": tp_size,
            "error": f"No node has {tp_size} GPUs with {per_gpu_gb:.1f}GB free each",
            "candidates": [],
        }

    return {
        "model": model_id,
        "needed_gb": needed_gb,
        "tp_size": tp_size,
        "recommended": candidates[0],
        "alternatives": candidates[1:],
    }


def find_available_gpu(min_vram_gb: float = 8.0) -> list[dict]:
    """Scan all GPUs across all nodes, return those with enough free VRAM."""
    gpus = _parse_gpu_states()
    available = [g for g in gpus if g["vram_free_gb"] >= min_vram_gb]
    available.sort(key=lambda x: x["vram_free_gb"], reverse=True)
    return available


def suggest_migrations() -> list[dict]:
    """Identify GPUs at >90% where another has >50% free - suggest rebalancing."""
    gpus = _parse_gpu_states()
    overloaded = [g for g in gpus if g["usage_pct"] > 90]
    underloaded = [g for g in gpus if g["usage_pct"] < 50 and g["vram_free_gb"] > 8]

    suggestions = []
    for hot in overloaded:
        for cold in underloaded:
            if hot["node"] == cold["node"] and hot["gpu_id"] == cold["gpu_id"]:
                continue
            suggestions.append({
                "reason": f"{hot['node']}:GPU{hot['gpu_id']} at {hot['usage_pct']}% "
                          f"while {cold['node']}:GPU{cold['gpu_id']} at {cold['usage_pct']}%",
                "hot_gpu": {
                    "node": hot["node"], "gpu_id": hot["gpu_id"],
                    "name": hot["name"], "usage_pct": hot["usage_pct"],
                },
                "cold_gpu": {
                    "node": cold["node"], "gpu_id": cold["gpu_id"],
                    "name": cold["name"], "vram_free_gb": cold["vram_free_gb"],
                },
            })

    return suggestions
