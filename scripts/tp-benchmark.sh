#!/bin/bash
# Live Throughput Benchmark — Phase 2 Model Stack
# Benchmarks existing vLLM endpoints without spinning new containers.
#
# Usage: ./scripts/tp-benchmark.sh [REQUESTS]
# Default: 10 requests per endpoint


# Source cluster config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REQUESTS="${1:-10}"
RESULTS="/tmp/tp-benchmark-$(date +%Y%m%d-%H%M%S).txt"

echo "Athanor Phase 2 — Live Throughput Benchmark" | tee "$RESULTS"
echo "============================================" | tee -a "$RESULTS"
echo "Requests per endpoint: $REQUESTS" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"

python3 << PYTHON
import json, sys, time

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

ENDPOINTS = {
    "coordinator (Qwen3.5-27B-FP8 TP=4)": {
        "url": "${VLLM_COORDINATOR_URL}/v1/completions",
        "model": "/models/Qwen3.5-27B-FP8",
    },
    "coder (Qwen3.5-35B-A3B-AWQ)": {
        "url": "${VLLM_CODER_URL}/v1/completions",
        "model": "devstral-small-2",
    },
    "worker (Qwen3.5-35B-A3B-AWQ)": {
        "url": "${VLLM_VISION_URL}/v1/completions",
        "model": "/models/Qwen3.5-35B-A3B-AWQ-4bit",
    },
}

PROMPT = "Explain the theory of relativity in detail, covering both special and general relativity."
NUM = int("$REQUESTS")
results = {}

for label, ep in ENDPOINTS.items():
    print(f"\n--- {label} ---")
    print(f"    {ep['url']}")

    # Quick health check
    try:
        r = requests.get(ep["url"].replace("/v1/completions", "/health"), timeout=3)
        if r.status_code != 200:
            print(f"    SKIP: endpoint unhealthy (status {r.status_code})")
            results[label] = {"avg_tps": 0, "status": "unhealthy"}
            continue
    except Exception as e:
        print(f"    SKIP: endpoint unreachable ({e})")
        results[label] = {"avg_tps": 0, "status": "unreachable"}
        continue

    times = []
    for i in range(NUM):
        try:
            start = time.time()
            resp = requests.post(ep["url"], json={
                "model": ep["model"],
                "prompt": PROMPT,
                "max_tokens": 256,
                "temperature": 0,
                "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
            }, timeout=120)
            elapsed = time.time() - start
            usage = resp.json().get("usage", {})
            tokens = usage.get("completion_tokens", 0)
            tps = tokens / elapsed if elapsed > 0 else 0
            times.append(tps)
            print(f"    [{i+1}/{NUM}] {tokens} tokens in {elapsed:.1f}s = {tps:.1f} tok/s")
        except Exception as e:
            print(f"    [{i+1}/{NUM}] ERROR: {e}")

    if times:
        avg = sum(times) / len(times)
        p50 = sorted(times)[len(times) // 2]
        print(f"    AVG: {avg:.1f} tok/s  |  P50: {p50:.1f} tok/s")
        results[label] = {"avg_tps": round(avg, 1), "p50_tps": round(p50, 1), "samples": len(times), "status": "ok"}
    else:
        results[label] = {"avg_tps": 0, "status": "no_results"}

print("\n============================================")
print("SUMMARY")
print("============================================")
for label, r in results.items():
    if r["status"] == "ok":
        print(f"  {label}: {r['avg_tps']} tok/s avg, {r['p50_tps']} tok/s p50 ({r['samples']} samples)")
    else:
        print(f"  {label}: {r['status']}")

# Save JSON results
with open("$RESULTS", "a") as f:
    f.write(json.dumps(results, indent=2))
PYTHON

echo ""
echo "Results saved to: $RESULTS"
