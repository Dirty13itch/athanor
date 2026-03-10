#!/usr/bin/env python3
"""Athanor node heartbeat daemon.

Publishes GPU metrics, container status, and system load to Redis
every 10 seconds. Runs on each compute node (FOUNDRY, WORKSHOP, DEV).

Channels:
  athanor:heartbeat:<node>     — per-node health + metrics (SET, expires 30s)
  athanor:models:status        — model availability (PUBLISH)
  athanor:alerts               — OOM/crash events (PUBLISH)

Requirements: redis, pynvml (nvidia-ml-py3), psutil
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time

# Node identity from hostname or env
NODE_NAME = os.environ.get("ATHANOR_NODE", socket.gethostname())
REDIS_URL = (
    os.environ.get("ATHANOR_REDIS_URL")
    or os.environ.get("REDIS_URL")
    or f"redis://{os.environ.get('ATHANOR_VAULT_HOST', '192.168.1.203')}:6379/0"
)
INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "10"))

# vLLM endpoints to check on this node
VLLM_ENDPOINTS = json.loads(os.environ.get("VLLM_ENDPOINTS", "[]"))

_running = True


def _signal_handler(sig, frame):
    global _running
    _running = False


def get_gpu_metrics():
    """Get GPU metrics via nvidia-smi (no pynvml dependency)."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        )
        gpus = []
        for line in out.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 7:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "vram_used_mib": int(parts[2]),
                    "vram_total_mib": int(parts[3]),
                    "util_pct": int(parts[4]),
                    "temp_c": int(parts[5]),
                    "power_w": float(parts[6]),
                })
        return gpus
    except Exception as e:
        return [{"error": str(e)}]


def get_system_metrics():
    """Get basic system metrics without psutil."""
    metrics = {}
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            metrics["load_1m"] = float(parts[0])
            metrics["load_5m"] = float(parts[1])
            metrics["load_15m"] = float(parts[2])
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                key, val = line.split(":")
                meminfo[key.strip()] = int(val.strip().split()[0])
            metrics["ram_total_mb"] = meminfo.get("MemTotal", 0) // 1024
            metrics["ram_available_mb"] = meminfo.get("MemAvailable", 0) // 1024
    except Exception:
        pass
    return metrics


def check_vllm_endpoints():
    """Check local vLLM endpoint health."""
    from urllib.request import urlopen
    from urllib.error import URLError

    results = {}
    for ep in VLLM_ENDPOINTS:
        try:
            with urlopen(f"http://localhost:{ep['port']}/health", timeout=2) as resp:
                results[ep["name"]] = {"healthy": resp.status == 200, "model": ep.get("model", "")}
        except (URLError, OSError):
            results[ep["name"]] = {"healthy": False, "model": ep.get("model", "")}
    return results


def main():
    import redis

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print(f"[heartbeat] Connected to Redis, node={NODE_NAME}, interval={INTERVAL}s")

    prev_models = {}

    while _running:
        try:
            gpus = get_gpu_metrics()
            system = get_system_metrics()
            models = check_vllm_endpoints()

            heartbeat = {
                "node": NODE_NAME,
                "timestamp": time.time(),
                "gpus": gpus,
                "system": system,
                "models": models,
            }

            # SET with 30s expiry (3x interval = stale detection)
            r.set(f"athanor:heartbeat:{NODE_NAME}", json.dumps(heartbeat), ex=30)

            # Publish model status changes
            for name, status in models.items():
                prev = prev_models.get(name, {})
                if prev.get("healthy") != status["healthy"]:
                    event = "up" if status["healthy"] else "down"
                    r.publish("athanor:models:status", json.dumps({
                        "node": NODE_NAME, "model": name, "event": event,
                        "timestamp": time.time(),
                    }))
                    # Alert on model going down
                    if event == "down":
                        r.publish("athanor:alerts", json.dumps({
                            "node": NODE_NAME, "type": "model_down", "model": name,
                            "timestamp": time.time(),
                        }))

            prev_models = models

            # Check for GPU OOM indicators
            for gpu in gpus:
                if isinstance(gpu, dict) and gpu.get("vram_used_mib", 0) > 0:
                    util = gpu["vram_used_mib"] / max(gpu["vram_total_mib"], 1)
                    if util > 0.98:
                        r.publish("athanor:alerts", json.dumps({
                            "node": NODE_NAME, "type": "gpu_vram_critical",
                            "gpu_index": gpu["index"], "util_pct": round(util * 100, 1),
                            "timestamp": time.time(),
                        }))

        except redis.ConnectionError:
            print("[heartbeat] Redis connection lost, reconnecting...")
            time.sleep(5)
            try:
                r = redis.from_url(REDIS_URL, decode_responses=True)
                r.ping()
            except Exception:
                pass
        except Exception as e:
            print(f"[heartbeat] Error: {e}", file=sys.stderr)

        time.sleep(INTERVAL)

    print("[heartbeat] Shutting down")


if __name__ == "__main__":
    main()
