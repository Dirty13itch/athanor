"""Cost optimization — track spending and recommend cheapest adequate model."""
from datetime import datetime, timezone

# Subscription tracking
SUBSCRIPTIONS = {
    "claude-max": {"monthly_cost": 200, "status": "active"},
    "chatgpt-pro": {"monthly_cost": 200, "status": "active"},
    "copilot-pro-plus": {"monthly_cost": 39, "status": "needs_auth"},
    "kimi-code": {"monthly_cost": 19, "status": "active"},
    "glm-zai": {"monthly_cost": 30, "status": "active"},
    "gemini-pro": {"monthly_cost": 20, "status": "needs_auth"},
}

CLOUD_COSTS = {
    "deepseek-chat": 0.28,  # $/MTok
    "venice-uncensored": 0.20,
    "codestral": 0.0,  # free tier
}


def get_cost_summary() -> dict:
    """Summarize monthly costs and burn rates."""
    now = datetime.now(timezone.utc)
    days_in_month = 30
    day_of_month = now.day
    days_remaining = days_in_month - day_of_month

    total_monthly = sum(s["monthly_cost"] for s in SUBSCRIPTIONS.values() if s["status"] == "active")
    daily_burn = total_monthly / days_in_month

    return {
        "total_monthly": total_monthly,
        "daily_burn": round(daily_burn, 2),
        "day_of_month": day_of_month,
        "days_remaining": days_remaining,
        "projected_spend": total_monthly,  # Fixed cost subs
        "active_subs": sum(1 for s in SUBSCRIPTIONS.values() if s["status"] == "active"),
        "local_inference_cost": 0,  # Electricity only, not tracked yet
    }


def recommend_cheapest(task_type: str, min_quality: int = 3) -> dict:
    """Find the cheapest model that meets minimum quality for a task type."""
    from quality import MODEL_PROFILES

    candidates = []
    for model_id, profile in MODEL_PROFILES.items():
        if profile["rating"] < min_quality:
            continue
        if task_type in profile.get("best_tasks", []) or task_type in profile.get("strengths", []):
            cost = profile.get("cost_per_mtok", 0)  # 0 = local/free
            candidates.append({"model": model_id, "cost_per_mtok": cost, "rating": profile["rating"]})

    candidates.sort(key=lambda x: (x["cost_per_mtok"], -x["rating"]))
    return candidates[0] if candidates else {"model": "worker", "cost_per_mtok": 0}
