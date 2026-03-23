"""Capacity Planner — predict when resources run out."""
import httpx
from datetime import datetime, timedelta

PROMETHEUS = "http://192.168.1.203:9090"


def query_prometheus_range(query: str, hours: int = 168) -> list:
    """Query Prometheus range API for trend data (default 7 days)."""
    end = datetime.now()
    start = end - timedelta(hours=hours)
    try:
        r = httpx.get(f"{PROMETHEUS}/api/v1/query_range", params={
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": "1h",
        }, timeout=15)
        if r.status_code == 200:
            return r.json().get("data", {}).get("result", [])
    except Exception:
        pass
    return []


def predict_disk_full(mount_pattern: str = "appdatacache") -> dict:
    """Predict when a disk will be full based on usage trend."""
    results = query_prometheus_range(
        f'100 - (node_filesystem_avail_bytes{{mountpoint=~".*{mount_pattern}.*"}} / node_filesystem_size_bytes{{mountpoint=~".*{mount_pattern}.*"}} * 100)'
    )
    
    if not results or not results[0].get("values"):
        return {"error": "No data"}
    
    values = results[0]["values"]
    if len(values) < 24:  # Need at least 24 hours of data
        return {"error": "Insufficient data points"}
    
    # Simple linear regression
    times = [v[0] for v in values]
    usages = [float(v[1]) for v in values]
    
    n = len(times)
    sum_x = sum(times)
    sum_y = sum(usages)
    sum_xy = sum(t * u for t, u in zip(times, usages))
    sum_x2 = sum(t * t for t in times)
    
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return {"error": "Cannot calculate trend"}
    
    slope = (n * sum_xy - sum_x * sum_y) / denom  # % per second
    
    current_usage = usages[-1]
    remaining_pct = 100 - current_usage
    
    if slope <= 0:
        return {
            "current_pct": round(current_usage, 1),
            "trend": "stable_or_decreasing",
            "days_to_full": None,
            "slope_pct_per_day": round(slope * 86400, 2),
        }
    
    seconds_to_full = remaining_pct / slope
    days_to_full = seconds_to_full / 86400
    
    return {
        "current_pct": round(current_usage, 1),
        "trend": "increasing",
        "days_to_full": round(days_to_full, 1),
        "slope_pct_per_day": round(slope * 86400, 2),
        "alert": days_to_full < 14,
        "alert_message": f"Disk will be full in {days_to_full:.0f} days at current rate" if days_to_full < 14 else None,
    }


def detect_ram_leaks() -> list:
    """Detect services with monotonically increasing RAM usage."""
    # Look for processes where RSS grows steadily over 24h
    results = query_prometheus_range(
        'process_resident_memory_bytes',
        hours=24
    )
    
    leaks = []
    for r in results:
        values = r.get("values", [])
        if len(values) < 12:  # Need 12+ hours
            continue
        
        rss_values = [float(v[1]) for v in values]
        
        # Check if consistently growing (>80% of intervals are increases)
        increases = sum(1 for i in range(1, len(rss_values)) if rss_values[i] > rss_values[i-1])
        if increases / (len(rss_values) - 1) > 0.8:
            growth_mb = (rss_values[-1] - rss_values[0]) / 1e6
            if growth_mb > 50:  # Only flag if >50MB growth
                leaks.append({
                    "job": r["metric"].get("job", "unknown"),
                    "instance": r["metric"].get("instance", ""),
                    "growth_mb_24h": round(growth_mb, 1),
                    "current_mb": round(rss_values[-1] / 1e6, 1),
                })
    
    return leaks


def get_capacity_report() -> dict:
    """Full capacity analysis across the cluster."""
    from registry import get_gpu_state, get_disk_state, get_ram_state
    
    return {
        "generated_at": datetime.now().isoformat(),
        "gpu": get_gpu_state(),
        "disk": {
            "nvme0_trend": predict_disk_full("appdatacache"),
        },
        "ram": get_ram_state(),
        "ram_leaks": detect_ram_leaks(),
    }
