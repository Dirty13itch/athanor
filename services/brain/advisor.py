"""Morning advisor — generates proactive recommendations."""
from datetime import datetime, timezone


def generate_briefing(resources: dict, predictions: dict, models: dict, costs: dict) -> dict:
    """Generate a morning briefing with actionable recommendations."""
    items = []
    severity_counts = {"critical": 0, "warning": 0, "info": 0}

    # Check disk predictions
    disk = predictions.get("disk", {})
    if disk.get("days_to_full") and disk["days_to_full"] < 30:
        severity = "critical" if disk["days_to_full"] < 7 else "warning"
        items.append({
            "severity": severity,
            "category": "capacity",
            "message": f"Disk fills in {disk['days_to_full']} days at current rate ({disk.get('current_pct', '?')}% used)",
            "action": "Prune backups or increase retention cleanup frequency",
        })
        severity_counts[severity] += 1

    # Check memory leaks
    for leak in predictions.get("memory_leaks", []):
        items.append({
            "severity": "warning",
            "category": "memory",
            "message": f"{leak['service']} growing {leak['growth_mb_per_day']}MB/day (now {leak['current_mb']}MB)",
            "action": f"Investigate {leak['service']} for memory leaks, consider restart",
        })
        severity_counts["warning"] += 1

    # Check GPU utilization
    for node_name, node in resources.items():
        for gpu in node.get("gpus", []):
            if gpu.get("temperature", 0) > 80:
                items.append({
                    "severity": "warning",
                    "category": "thermal",
                    "message": f"{node_name} GPU {gpu['id']} at {gpu['temperature']}°C",
                    "action": "Check cooling, consider reducing workload",
                })
                severity_counts["warning"] += 1

    # Check idle models
    try:
        from lifecycle import get_idle_models
        idle = get_idle_models(threshold_minutes=120)
    except (ImportError, Exception):
        idle = []

    if idle:
        idle_names = [m["model"] for m in idle[:3]]
        vram_recoverable = sum(m.get("vram_gb", 0) for m in idle)
        items.append({
            "severity": "info",
            "category": "efficiency",
            "message": f"{len(idle)} models idle >2h: {', '.join(idle_names)}",
            "action": f"Consider unloading to free ~{vram_recoverable:.1f}GB VRAM",
        })
        severity_counts["info"] += 1

    # Cost summary
    items.append({
        "severity": "info",
        "category": "cost",
        "message": f"Monthly burn: ${costs.get('total_monthly', 0)}/mo, {costs.get('active_subs', 0)} active subscriptions",
        "action": None,
    })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "severity_counts": severity_counts,
        "items": items,
    }
