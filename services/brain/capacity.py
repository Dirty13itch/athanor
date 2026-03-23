"""Capacity Planner — predict when resources run out."""
import httpx
import numpy as np
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("brain.capacity")

PROMETHEUS = "http://192.168.1.203:9090"


def query_prometheus_range(query: str, hours: int = 168) -> list:
    """Query Prometheus range API for trend data (default 7 days)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    try:
        r = httpx.get(
            f"{PROMETHEUS}/api/v1/query_range",
            params={
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": "1h",
            },
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("data", {}).get("result", [])
    except Exception as e:
        logger.warning("Prometheus range query failed: %s — %s", query[:60], e)
    return []


def predict_disk_full(node: str, mount: str) -> dict:
    """Predict when a disk reaches 95% based on 7-day trend.

    Uses linear regression on node_filesystem_avail_bytes.
    Returns days_to_full, current_pct, trend_gb_per_day.
    """
    query = (
        f'node_filesystem_avail_bytes{{mountpoint=~".*{mount}.*"}}'
    )
    results = query_prometheus_range(query, hours=168)  # 7 days

    if not results or not results[0].get("values"):
        return {"error": "No data", "node": node, "mount": mount}

    values = results[0]["values"]
    if len(values) < 24:
        return {"error": "Insufficient data (<24 points)", "node": node, "mount": mount}

    times = np.array([float(v[0]) for v in values])
    avail_bytes = np.array([float(v[1]) for v in values])

    # Get total size from the latest instant query
    size_results = httpx.get(
        f"{PROMETHEUS}/api/v1/query",
        params={"query": f'node_filesystem_size_bytes{{mountpoint=~".*{mount}.*"}}'},
        timeout=10,
    ).json().get("data", {}).get("result", [])

    if not size_results:
        return {"error": "Cannot determine disk size", "node": node, "mount": mount}

    total_bytes = float(size_results[0]["value"][1])
    current_used_pct = round(100 * (1 - avail_bytes[-1] / total_bytes), 1)

    # Linear regression: avail_bytes = slope * time + intercept
    coeffs = np.polyfit(times, avail_bytes, 1)
    slope_bytes_per_sec = coeffs[0]
    trend_gb_per_day = round((-slope_bytes_per_sec * 86400) / 1e9, 2)  # negative slope = disk filling

    if slope_bytes_per_sec >= 0:
        # Disk is stable or freeing space
        return {
            "node": node,
            "mount": mount,
            "current_pct": current_used_pct,
            "trend": "stable_or_decreasing",
            "trend_gb_per_day": trend_gb_per_day,
            "days_to_full": None,
            "alert": False,
        }

    # Predict when avail_bytes reaches 5% of total (95% full)
    threshold = total_bytes * 0.05
    current_avail = avail_bytes[-1]
    bytes_until_full = current_avail - threshold

    if bytes_until_full <= 0:
        return {
            "node": node,
            "mount": mount,
            "current_pct": current_used_pct,
            "trend": "critical",
            "trend_gb_per_day": trend_gb_per_day,
            "days_to_full": 0,
            "alert": True,
            "alert_message": f"{mount} is at {current_used_pct}% — already past 95% threshold",
        }

    seconds_to_full = bytes_until_full / abs(slope_bytes_per_sec)
    days_to_full = round(seconds_to_full / 86400, 1)

    return {
        "node": node,
        "mount": mount,
        "current_pct": current_used_pct,
        "trend": "increasing",
        "trend_gb_per_day": trend_gb_per_day,
        "days_to_full": days_to_full,
        "alert": days_to_full < 14,
        "alert_message": (
            f"{mount} will be 95% full in {days_to_full:.0f} days at current rate"
            if days_to_full < 14
            else None
        ),
    }


def detect_memory_leaks() -> list:
    """Detect services with monotonically increasing RAM over 3 days.

    Returns services with >10MB/day growth.
    """
    results = query_prometheus_range("process_resident_memory_bytes", hours=72)

    leaks = []
    for r in results:
        values = r.get("values", [])
        if len(values) < 24:
            continue

        times = np.array([float(v[0]) for v in values])
        rss = np.array([float(v[1]) for v in values])

        # Linear regression for growth rate
        coeffs = np.polyfit(times, rss, 1)
        slope_bytes_per_sec = coeffs[0]
        growth_mb_per_day = slope_bytes_per_sec * 86400 / 1e6

        if growth_mb_per_day < 10:
            continue

        # Check monotonicity (>75% of intervals are increases)
        diffs = np.diff(rss)
        pct_increasing = np.sum(diffs > 0) / len(diffs)
        if pct_increasing < 0.75:
            continue

        leaks.append({
            "job": r["metric"].get("job", "unknown"),
            "instance": r["metric"].get("instance", ""),
            "growth_mb_per_day": round(growth_mb_per_day, 1),
            "current_mb": round(rss[-1] / 1e6, 1),
            "monotonicity": round(pct_increasing, 2),
        })

    leaks.sort(key=lambda x: x["growth_mb_per_day"], reverse=True)
    return leaks


def detect_gpu_overheating() -> list:
    """Detect GPUs with sustained high temperature over 24h."""
    results = query_prometheus_range("DCGM_FI_DEV_GPU_TEMP", hours=24)

    alerts = []
    for r in results:
        values = r.get("values", [])
        if len(values) < 12:
            continue

        temps = np.array([float(v[1]) for v in values])
        avg_temp = float(np.mean(temps))
        max_temp = float(np.max(temps))
        pct_above_80 = float(np.sum(temps > 80) / len(temps))

        if avg_temp > 75 or pct_above_80 > 0.1:
            alerts.append({
                "instance": r["metric"].get("instance", ""),
                "gpu": r["metric"].get("gpu", ""),
                "avg_temp_c": round(avg_temp, 1),
                "max_temp_c": round(max_temp, 1),
                "pct_above_80c": round(pct_above_80 * 100, 1),
            })

    return alerts


def get_capacity_report() -> dict:
    """Full capacity analysis across the cluster."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disk_predictions": {
            "vault_appdatacache": predict_disk_full("vault", "appdatacache"),
        },
        "memory_leaks": detect_memory_leaks(),
        "gpu_thermal": detect_gpu_overheating(),
    }
