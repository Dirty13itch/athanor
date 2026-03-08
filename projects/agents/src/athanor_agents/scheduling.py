"""Inference-Aware Agent Scheduling

Queries vLLM Prometheus metrics to determine GPU load before spawning agent
tasks. Latency-sensitive agents (home, general) get priority. Batch agents
(research, data-curator) throttle when GPU is busy.

Architecture:
    - Queries Prometheus for vLLM queue depth and GPU utilization
    - Classifies agents as latency-sensitive or batch
    - Throttles batch agent task execution when GPUs are heavily loaded
    - Exposes load state via /v1/scheduling/status endpoint
"""

import logging
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)

# Agent priority classes
LATENCY_SENSITIVE = {"general-assistant", "home-agent", "media-agent"}
BATCH_AGENTS = {"research-agent", "data-curator", "knowledge-agent", "coding-agent"}
CREATIVE_AGENTS = {"creative-agent", "stash-agent"}

# Thresholds
GPU_UTIL_HIGH = 80  # % — above this, throttle batch agents
GPU_UTIL_CRITICAL = 95  # % — above this, only latency-sensitive agents run
VLLM_QUEUE_DEPTH_HIGH = 5  # pending requests — throttle batch
VLLM_QUEUE_DEPTH_CRITICAL = 15  # pending requests — only urgent


async def get_inference_load() -> dict:
    """Query Prometheus for current vLLM and GPU load metrics.

    Returns dict with:
        gpu_util: average GPU utilization across inference GPUs (0-100)
        vllm_queue_depth: total pending requests across vLLM instances
        vllm_running: total running requests
        timestamp: when metrics were fetched
    """
    result = {
        "gpu_util": 0.0,
        "vllm_queue_depth": 0,
        "vllm_running": 0,
        "timestamp": time.time(),
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=3) as client:
            # GPU utilization (inference GPUs only — Foundry + Workshop)
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": 'avg(DCGM_FI_DEV_GPU_UTIL{instance=~"192.168.1.(244|225).*"})'},
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if results:
                result["gpu_util"] = float(results[0]["value"][1])

            # vLLM pending requests (queue depth)
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": 'sum(vllm:num_requests_waiting) or vector(0)'},
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if results:
                result["vllm_queue_depth"] = int(float(results[0]["value"][1]))

            # vLLM running requests
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": 'sum(vllm:num_requests_running) or vector(0)'},
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            if results:
                result["vllm_running"] = int(float(results[0]["value"][1]))

    except Exception as e:
        logger.warning("Failed to fetch inference load: %s", e)
        result["error"] = str(e)

    return result


def should_execute_task(agent: str, load: dict) -> tuple[bool, str]:
    """Determine whether an agent task should execute given current load.

    Returns (should_run, reason).
    """
    gpu_util = load.get("gpu_util", 0)
    queue_depth = load.get("vllm_queue_depth", 0)

    # Latency-sensitive agents always run
    if agent in LATENCY_SENSITIVE:
        return True, "latency-sensitive agent — always allowed"

    # Critical GPU load — only latency-sensitive agents
    if gpu_util >= GPU_UTIL_CRITICAL or queue_depth >= VLLM_QUEUE_DEPTH_CRITICAL:
        return False, f"critical load (GPU={gpu_util:.0f}%, queue={queue_depth}) — batch deferred"

    # High GPU load — throttle batch agents
    if gpu_util >= GPU_UTIL_HIGH or queue_depth >= VLLM_QUEUE_DEPTH_HIGH:
        if agent in BATCH_AGENTS:
            return False, f"high load (GPU={gpu_util:.0f}%, queue={queue_depth}) — batch throttled"
        # Creative agents can still run under high load
        return True, "creative agent — allowed under high load"

    # Normal load — all agents run
    return True, "normal load — all agents allowed"


async def get_scheduling_status() -> dict:
    """Get current scheduling state for monitoring."""
    load = await get_inference_load()
    return {
        "load": load,
        "thresholds": {
            "gpu_util_high": GPU_UTIL_HIGH,
            "gpu_util_critical": GPU_UTIL_CRITICAL,
            "queue_depth_high": VLLM_QUEUE_DEPTH_HIGH,
            "queue_depth_critical": VLLM_QUEUE_DEPTH_CRITICAL,
        },
        "agent_classes": {
            "latency_sensitive": sorted(LATENCY_SENSITIVE),
            "batch": sorted(BATCH_AGENTS),
            "creative": sorted(CREATIVE_AGENTS),
        },
    }
