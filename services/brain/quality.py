"""Model quality routing — match tasks to the best model based on capability profiles."""

# Model capability profiles (built from Phase 11 quality probe data)
MODEL_PROFILES = {
    "Qwen3.5-27B-FP8": {
        "rating": 4, "max_context": 32768,
        "strengths": ["reasoning", "architecture", "multi-step", "docstrings", "type-hints"],
        "weaknesses": ["leaks thinking tokens", "slow first token (TP=4)"],
        "best_tasks": ["complex_coding", "system_design", "debugging", "refactoring"],
        "cost_tier": "free_local",
        "node": "foundry", "runtime": "vllm",
    },
    "Devstral-Small-2-AWQ": {
        "rating": 5, "max_context": 16384,
        "strengths": ["code_generation", "typescript", "react", "clean_architecture"],
        "weaknesses": ["limited_context_16k"],
        "best_tasks": ["frontend", "unit_tests", "component_design", "api_endpoints"],
        "cost_tier": "free_local",
        "node": "foundry", "runtime": "vllm",
    },
    "qwen35-abliterated-GGUF": {
        "rating": 4, "max_context": 8192,
        "strengths": ["creative_writing", "uncensored", "no_refusal", "literary_quality"],
        "weaknesses": ["needs_think_false", "slower_than_vllm", "limited_context_8k"],
        "best_tasks": ["eoq_content", "nsfw_creative", "character_profiles", "scene_writing", "creative_writing", "sovereign_creative", "creative"],
        "cost_tier": "free_local", "sovereign": True,
        "node": "workshop", "runtime": "ollama",
    },
    "deepseek-chat": {
        "rating": 4, "max_context": 128000,
        "strengths": ["math", "long_context", "batch_processing"],
        "weaknesses": ["cloud_latency", "rate_limited"],
        "best_tasks": ["batch_refactor", "documentation", "analysis"],
        "cost_tier": "cheap_cloud", "cost_per_mtok": 0.28,
    },
    "venice-uncensored": {
        "rating": 5, "max_context": 32000,
        "strengths": ["clean_output", "uncensored_cloud", "fast"],
        "best_tasks": ["sovereign_cloud_fallback", "creative"],
        "cost_tier": "cheap_cloud", "cost_per_mtok": 0.20, "sovereign": True,
    },
    "codestral": {
        "rating": 4, "max_context": 32000,
        "strengths": ["code_review", "fim_completion"],
        "best_tasks": ["code_review", "fim", "diff_analysis"],
        "cost_tier": "free_cloud",
    },
}


def recommend_model(task_type: str, complexity: str = "medium", content_class: str = "cloud_safe", context_needed: int = 4096) -> dict:
    """Recommend the best model for a task based on capability profiles."""
    candidates = []

    for model_id, profile in MODEL_PROFILES.items():
        score = 0
        reasons = []

        # Sovereign filter
        if content_class in ("sovereign_only", "refusal_sensitive"):
            if not profile.get("sovereign"):
                continue
            score += 20
            reasons.append("sovereign_capable")

        # Task type matching
        if task_type in profile.get("best_tasks", []):
            score += 15
            reasons.append(f"best_for_{task_type}")

        # Context requirement
        if context_needed > profile.get("max_context", 4096):
            continue  # Can't fit

        # Complexity matching
        if complexity == "high" and profile["rating"] >= 4:
            score += 10
        if complexity == "low" and profile.get("cost_tier") in ("free_local", "free_cloud"):
            score += 10
            reasons.append("cost_effective")

        # Base quality rating
        score += profile["rating"] * 2

        # Prefer local (free) over cloud (paid)
        if profile.get("cost_tier") == "free_local":
            score += 5

        candidates.append({
            "model": model_id, "score": score, "reasons": reasons,
            "rating": profile["rating"], "cost_tier": profile.get("cost_tier"),
            "node": profile.get("node"), "runtime": profile.get("runtime"),
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return {"model": "worker", "reason": "no matching model found, using default"}

    return candidates[0]
