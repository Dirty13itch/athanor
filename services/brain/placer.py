"""Workload placement - decide which GPU/node is best for a given model or task."""
import logging

logger = logging.getLogger("brain.placer")

# Placement rules
PLACEMENT_RULES = {
    "sovereign": {"required_nodes": ["workshop"], "required_gpu": 0, "reason": "abliterated model only on WORKSHOP GPU 0"},
    "coding": {"preferred_nodes": ["foundry"], "reason": "Devstral on FOUNDRY 4090"},
    "reasoning": {"preferred_nodes": ["foundry"], "reason": "Qwen3.5-27B on FOUNDRY TP=4"},
    "embedding": {"required_nodes": ["dev"], "required_gpu": 0, "reason": "embedding model on DEV"},
    "creative": {"preferred_nodes": ["workshop"], "reason": "sovereign brain handles creative"},
    "comfyui": {"required_nodes": ["workshop"], "required_gpu": 0, "reason": "ComfyUI needs 5090"},
}


def recommend_placement(task_type: str, content_class: str = "cloud_safe") -> dict:
    """Recommend the best node/GPU for a task."""
    if content_class in ("sovereign_only", "refusal_sensitive"):
        return {
            "node": "workshop", "gpu": 0,
            "model": "huihui_ai/qwen3.5-abliterated:35b",
            "runtime": "ollama",
            "reason": "Sovereign content must use local abliterated model"
        }

    if task_type in ("coding", "code_review", "refactor"):
        return {
            "node": "foundry", "gpu": 2,
            "model": "Devstral-Small-2-AWQ",
            "runtime": "vllm",
            "reason": "Devstral is the coding specialist (68% SWE-bench)"
        }

    if task_type in ("reasoning", "architecture", "planning"):
        return {
            "node": "foundry", "gpus": [0, 1, 3, 4],
            "model": "Qwen3.5-27B-FP8",
            "runtime": "vllm",
            "reason": "Qwen3.5-27B is the reasoning model (TP=4)"
        }

    # Default: use the worker alias through LiteLLM
    return {
        "node": "workshop", "gpu": 0,
        "model": "worker",
        "runtime": "litellm",
        "reason": "Default worker model via LiteLLM"
    }


def find_best_gpu(model_requirements: dict, cluster_state: dict) -> dict:
    """Find the GPU with the most headroom for a given model."""
    needed = model_requirements.get("min_vram_gb", 0)
    best = None
    best_headroom = -1

    for node_name, node in cluster_state.items():
        for gpu in node.get("gpus", []):
            available = gpu.get("vram_free_gb", 0)
            headroom = available - needed
            if headroom > best_headroom:
                best_headroom = headroom
                best = {"node": node_name, "gpu": gpu["id"], "headroom_gb": round(headroom, 1)}

    if best and best_headroom > 0:
        return {"found": True, **best}
    return {"found": False, "reason": f"No GPU has {needed}GB free"}
