"""Metrics routes — learning, agent performance, inference, context."""

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from ..config import settings

logger = logging.getLogger("athanor.metrics")

router = APIRouter(prefix="/v1", tags=["metrics"])


@router.get("/learning/metrics")
async def learning_metrics():
    """Aggregated metrics showing whether the system is actually learning.

    Collects from: semantic cache, circuit breakers, preference learning,
    trust scores, routing stats, diagnosis patterns, consolidation stats.
    """
    metrics = {}

    # 1. Semantic cache performance
    try:
        from ..semantic_cache import get_semantic_cache
        cache = get_semantic_cache()
        stats = await cache.get_stats()
        metrics["cache"] = {
            "total_entries": stats.get("entries", 0),
            "collection": stats.get("collection", "llm_cache"),
            "similarity_threshold": stats.get("similarity_threshold", 0.93),
        }
    except Exception as e:
        logger.debug("Learning metrics cache stats failed: %s", e)
        metrics["cache"] = None

    # 2. Circuit breaker health
    try:
        from ..circuit_breaker import get_circuit_breakers
        breakers = get_circuit_breakers()
        states = breakers.get_all_stats()
        metrics["circuits"] = {
            "services": len(states),
            "open": sum(1 for s in states.values() if s.get("state") == "open"),
            "half_open": sum(1 for s in states.values() if s.get("state") == "half_open"),
            "closed": sum(1 for s in states.values() if s.get("state") == "closed"),
            "total_failures": sum(s.get("failures", 0) for s in states.values()),
        }
    except Exception as e:
        logger.debug("Learning metrics circuits failed: %s", e)
        metrics["circuits"] = None

    # 3. Preference learning convergence
    try:
        from ..preferences import get_all_preferences
        prefs = await get_all_preferences()
        if prefs:
            total_entries = prefs.get("total_entries", 0)
            task_types = prefs.get("task_types", {})
            all_models = [m for models in task_types.values() for m in models]
            total_samples = sum(m.get("interactions", 0) for m in all_models)
            avg_score = sum(m.get("score", 0) for m in all_models) / max(len(all_models), 1) if all_models else 0
            metrics["preferences"] = {
                "model_task_pairs": total_entries,
                "task_types": len(task_types),
                "total_samples": total_samples,
                "avg_score": round(avg_score, 3),
                "converged": sum(1 for m in all_models if m.get("interactions", 0) >= prefs.get("min_samples", 3)),
            }
        else:
            metrics["preferences"] = {"model_task_pairs": 0, "total_samples": 0}
    except Exception as e:
        logger.debug("Learning metrics preferences failed: %s", e)
        metrics["preferences"] = None

    # 4. Trust scores
    try:
        from ..goals import compute_trust_scores
        trust = await compute_trust_scores()
        if trust:
            avg_trust = sum(t.get("trust_score", 0) for t in trust.values()) / max(len(trust), 1)
            metrics["trust"] = {
                "agents_tracked": len(trust),
                "avg_trust_score": round(avg_trust, 3),
                "high_trust": sum(1 for t in trust.values() if t.get("trust_score", 0) > 0.7),
                "low_trust": sum(1 for t in trust.values() if t.get("trust_score", 0) < 0.3),
            }
        else:
            metrics["trust"] = {"agents_tracked": 0}
    except Exception as e:
        logger.debug("Learning metrics trust failed: %s", e)
        metrics["trust"] = None

    # 5. Diagnosis patterns
    try:
        from ..diagnosis import get_diagnosis_engine
        diag = get_diagnosis_engine()
        report = diag.analyze(hours=24)
        metrics["diagnosis"] = {
            "recent_failures": report.total_failures,
            "patterns_detected": len(report.top_patterns),
            "recommendations": len(report.recommendations),
            "health_score": report.health_score,
            "trend": report.trend,
        }
    except Exception as e:
        logger.debug("Learning metrics diagnosis failed: %s", e)
        metrics["diagnosis"] = None

    # 6. Consolidation (memory hygiene)
    try:
        from ..consolidation import get_collection_stats
        cstats = await get_collection_stats()
        total_points = sum(c.get("count", 0) for c in cstats.values()) if isinstance(cstats, dict) else 0
        metrics["memory"] = {
            "collections": len(cstats) if isinstance(cstats, dict) else 0,
            "total_points": total_points,
        }
    except Exception as e:
        logger.debug("Learning metrics memory failed: %s", e)
        metrics["memory"] = None

    # 7. Task execution stats
    try:
        from ..tasks import get_task_stats
        tstats = await get_task_stats()
        metrics["tasks"] = {
            "total": tstats.get("total", 0),
            "completed": tstats.get("by_status", {}).get("completed", 0),
            "failed": tstats.get("by_status", {}).get("failed", 0),
            "success_rate": round(
                tstats.get("by_status", {}).get("completed", 0) /
                max(tstats.get("total", 1), 1), 3
            ),
        }
    except Exception as e:
        logger.debug("Learning metrics tasks failed: %s", e)
        metrics["tasks"] = None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "summary": _compute_learning_summary(metrics),
    }


def _compute_learning_summary(metrics: dict) -> dict:
    """Compute a high-level learning health score from aggregated metrics."""
    scores = []
    signals = []

    # Cache: higher hit rate = more learning
    if metrics.get("cache") and metrics["cache"].get("total_entries", 0) > 0:
        hit_rate = metrics["cache"].get("hit_rate", 0)
        scores.append(min(hit_rate * 2, 1.0))  # 50% hit rate = perfect score
        if hit_rate > 0.1:
            signals.append(f"Cache hit rate {hit_rate:.0%}")

    # Preferences: more converged pairs = more learning
    if metrics.get("preferences") and metrics["preferences"].get("model_task_pairs", 0) > 0:
        convergence = metrics["preferences"]["converged"] / max(metrics["preferences"]["model_task_pairs"], 1)
        scores.append(convergence)
        if convergence > 0.5:
            signals.append(f"{metrics['preferences']['converged']} preference pairs converged")

    # Trust: high average = system is reliable
    if metrics.get("trust") and metrics["trust"].get("agents_tracked", 0) > 0:
        avg_trust = metrics["trust"].get("avg_trust_score", 0)
        scores.append(avg_trust)
        if avg_trust > 0.6:
            signals.append(f"Avg trust score {avg_trust:.2f}")

    # Tasks: success rate
    if metrics.get("tasks") and metrics["tasks"].get("total", 0) > 0:
        sr = metrics["tasks"].get("success_rate", 0)
        scores.append(sr)
        if sr > 0.8:
            signals.append(f"Task success rate {sr:.0%}")

    # Diagnosis: fewer failures = healthier
    if metrics.get("diagnosis"):
        failures = metrics["diagnosis"].get("recent_failures", 0)
        failure_score = max(1.0 - (failures / 50), 0)  # 50+ failures = 0
        scores.append(failure_score)

    overall = round(sum(scores) / max(len(scores), 1), 3) if scores else 0.0
    return {
        "overall_health": overall,
        "data_points": len(scores),
        "positive_signals": signals,
        "assessment": (
            "thriving" if overall > 0.8 else
            "healthy" if overall > 0.6 else
            "developing" if overall > 0.3 else
            "cold_start"
        ),
    }


@router.get("/metrics/agents")
async def agent_metrics():
    """Per-agent performance metrics for dashboard display."""
    from ..agents import get_agent_info
    from ..routing import get_cost_tracker

    agents_info = get_agent_info()
    cost = get_cost_tracker().summary()
    agent_ids = [a["id"] for a in agents_info]

    # Get activity counts per agent (uses agent ID, e.g., "general-assistant")
    activity_by_agent = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for aid in agent_ids:
                resp = await client.post(
                    f"{settings.qdrant_url}/collections/activity/points/count",
                    json={"filter": {"must": [{"key": "agent", "match": {"value": aid}}]}},
                )
                if resp.status_code == 200:
                    activity_by_agent[aid] = resp.json().get("result", {}).get("count", 0)
    except Exception as e:
        logger.debug("Agent status activity fetch failed: %s", e)

    # Get trust scores
    trust_by_agent = {}
    try:
        from ..goals import compute_trust_scores
        trust = await compute_trust_scores()
        if trust:
            trust_by_agent = {k: v.get("trust_score", 0) for k, v in trust.items()}
    except Exception as e:
        logger.debug("Agent status trust fetch failed: %s", e)

    # Get task stats per agent
    task_by_agent = {}
    try:
        from ..tasks import get_task_stats

        tstats = await get_task_stats()
        task_by_agent = {
            str(agent_id): {"total": int(total or 0)}
            for agent_id, total in dict(tstats.get("by_agent") or {}).items()
        }
    except Exception as e:
        logger.debug("Agent status task stats failed: %s", e)

    result = []
    for info in agents_info:
        aid = info["id"]
        result.append({
            "id": aid,
            "name": info["name"],
            "type": info.get("type", "reactive"),
            "status": info.get("status", "unknown"),
            "tools_count": len(info.get("tools", [])),
            "interactions": activity_by_agent.get(aid, 0),
            "trust_score": trust_by_agent.get(aid, None),
            "tasks": task_by_agent.get(aid, {}),
        })

    return {
        "agents": result,
        "cost": cost,
    }


@router.get("/metrics/inference")
async def inference_metrics():
    """Inference layer metrics — prefix cache, KV cache, throughput."""
    metrics = {}

    # Query vLLM Prometheus metrics via Prometheus
    queries = {
        "prefix_cache_hit_rate": 'rate(vllm:prefix_cache_hits_total[5m]) / rate(vllm:prefix_cache_queries_total[5m])',
        "kv_cache_usage": 'vllm:kv_cache_usage_perc',
        "requests_running": 'vllm:num_requests_running',
        "requests_waiting": 'vllm:num_requests_waiting',
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for key, query in queries.items():
                resp = await client.get(
                    f"{settings.prometheus_url}/api/v1/query",
                    params={"query": query},
                )
                if resp.status_code == 200:
                    results = resp.json().get("data", {}).get("result", [])
                    metrics[key] = [
                        {
                            "model": r["metric"].get("model_name", "?"),
                            "instance": r["metric"].get("instance", "?"),
                            "value": float(r["value"][1]) if r["value"][1] != "NaN" else None,
                        }
                        for r in results
                    ]
    except Exception as e:
        metrics["error"] = str(e)

    return metrics


@router.get("/metrics/context")
async def context_metrics():
    """Context enrichment latency stats from in-memory ring buffer."""
    from ..context import get_latency_stats

    return get_latency_stats()
