"""Athanor Sentinel — Continuous Health Monitor.

3-tier testing pyramid with circuit breakers:
  Tier 1 (60s):  Heartbeat — HTTP liveness
  Tier 2 (5min): Readiness — functional probes
  Tier 3 (15min): Integration — cross-service connectivity

Prometheus metrics + ntfy alerting on consecutive failures.
"""

import time
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler

from checks import (
    HEARTBEAT_CHECKS,
    CheckResult,
    run_heartbeat,
    run_readiness,
    run_integration,
    send_ntfy_alert,
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# Latest results keyed by (tier, service)
results: dict[tuple[str, str], CheckResult] = {}
results_lock = threading.Lock()

# Consecutive failure counters for alerting
consecutive_failures: dict[tuple[str, str], int] = {}

# Track which services passed each tier (circuit breaker)
tier1_passed: set[str] = set()
tier2_passed: set[str] = set()

STARTED_AT = time.time()

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

prom_check = Gauge(
    "athanor_sentinel_check",
    "Check pass/fail (1=pass, 0=fail)",
    ["tier", "service", "status"],
)
prom_latency = Gauge(
    "athanor_sentinel_latency_ms",
    "Check latency in milliseconds",
    ["tier", "service"],
)
prom_tier_pass_rate = Gauge(
    "athanor_sentinel_tier_pass_rate",
    "Pass rate for a tier (0.0-1.0)",
    ["tier"],
)

# ---------------------------------------------------------------------------
# Tier runners
# ---------------------------------------------------------------------------

def _record(result: CheckResult):
    key = (result.tier, result.service)
    with results_lock:
        results[key] = result

    # Prometheus
    status_label = "pass" if result.passed else "fail"
    prom_check.labels(tier=result.tier, service=result.service, status=status_label).set(
        1 if result.passed else 0
    )
    prom_latency.labels(tier=result.tier, service=result.service).set(result.latency_ms)

    # Consecutive failure tracking
    if not result.passed:
        consecutive_failures[key] = consecutive_failures.get(key, 0) + 1
    else:
        consecutive_failures[key] = 0


def _update_tier_rate(tier: str):
    with results_lock:
        tier_results = [v for k, v in results.items() if k[0] == tier]
    if not tier_results:
        return
    passed = sum(1 for r in tier_results if r.passed)
    rate = passed / len(tier_results)
    prom_tier_pass_rate.labels(tier=tier).set(round(rate, 4))


def tick_heartbeat():
    """Tier 1: run every 60 seconds."""
    global tier1_passed
    passed_set = set()

    for name, url in HEARTBEAT_CHECKS:
        result = run_heartbeat(name, url)
        _record(result)

        if result.passed:
            passed_set.add(name)

        # Alert after 3 consecutive heartbeat failures
        key = ("heartbeat", name)
        if consecutive_failures.get(key, 0) >= 3:
            send_ntfy_alert(name, f"SENTINEL: {name} is DOWN")
            # Reset so we don't spam — will re-alert after another 3
            consecutive_failures[key] = 0

    tier1_passed = passed_set
    _update_tier_rate("heartbeat")


def tick_readiness():
    """Tier 2: run every 5 minutes. Only check services that passed Tier 1."""
    global tier2_passed
    passed_set = set()

    # Only run readiness for services that have a specific readiness check
    # AND passed heartbeat
    readiness_services = [
        "vllm_coordinator", "vllm_coder", "vllm_sovereign",
        "litellm", "embedding", "governor",
    ]

    for name in readiness_services:
        if name not in tier1_passed:
            # Circuit breaker: skip if heartbeat failed
            _record(CheckResult(
                service=name, tier="readiness", passed=False,
                latency_ms=0, detail="skipped: heartbeat failed",
            ))
            continue

        result = run_readiness(name)
        _record(result)

        if result.passed:
            passed_set.add(name)

        # Alert after 2 consecutive readiness failures
        key = ("readiness", name)
        if consecutive_failures.get(key, 0) >= 2:
            send_ntfy_alert(name, f"SENTINEL: {name} readiness FAILING")
            consecutive_failures[key] = 0

    tier2_passed = passed_set
    _update_tier_rate("readiness")


def tick_integration():
    """Tier 3: run every 15 minutes. Only if relevant Tier 2 checks passed."""
    integration_results = run_integration()
    for result in integration_results:
        _record(result)
    _update_tier_rate("integration")


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(tick_heartbeat, "interval", seconds=60, )
    scheduler.add_job(tick_readiness, "interval", minutes=5, )
    scheduler.add_job(tick_integration, "interval", minutes=15, )
    scheduler.start()

    # Run Tier 1 immediately on startup
    threading.Thread(target=tick_heartbeat, daemon=True).start()

    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Athanor Sentinel", version="1.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "uptime_s": round(time.time() - STARTED_AT, 1)}


@app.get("/status")
def status():
    with results_lock:
        snapshot = dict(results)

    tiers = {}
    for (tier, service), result in snapshot.items():
        tiers.setdefault(tier, []).append({
            "service": result.service,
            "passed": result.passed,
            "latency_ms": result.latency_ms,
            "detail": result.detail,
            "timestamp": result.timestamp,
        })

    # Summary counts
    summary = {}
    for tier, checks in tiers.items():
        total = len(checks)
        passed = sum(1 for c in checks if c["passed"])
        summary[tier] = {"total": total, "passed": passed, "failed": total - passed}

    return {
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "summary": summary,
        "tiers": tiers,
    }


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
