#!/usr/bin/env bash
# Post-deploy verification — run after any container restart/rebuild.
# Checks all critical endpoints and reports failures.
#
# Usage: ./verify-deploy.sh [--notify]
#   --notify: send failures to ntfy

set -euo pipefail

NOTIFY="${1:-}"
NTFY_URL="http://192.168.1.203:8880/athanor"
FAILURES=0
CHECKS=0

check() {
    local name="$1" url="$2" expected="${3:-200}"
    CHECKS=$((CHECKS + 1))
    local code
    code=$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
    code="${code: -3}"
    if [ "$code" = "$expected" ]; then
        echo "  ✅ $name: $code"
    else
        echo "  ❌ $name: $code (expected $expected)"
        FAILURES=$((FAILURES + 1))
    fi
}

check_json() {
    local name="$1" url="$2" field="$3"
    CHECKS=$((CHECKS + 1))
    local result
    result=$(curl -s --max-time 10 "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d$field)" 2>/dev/null || echo "FAIL")
    if [ "$result" != "FAIL" ] && [ -n "$result" ]; then
        echo "  ✅ $name: $result"
    else
        echo "  ❌ $name: unreachable or bad response"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "=== Athanor Deploy Verification ==="
echo ""

echo "Inference:"
check_json "Coordinator" "http://192.168.1.244:8000/v1/models" "['data'][0]['id']"
check_json "Coder"       "http://192.168.1.244:8006/v1/models" "['data'][0]['id']"
check_json "Worker"      "http://192.168.1.225:8010/v1/models" "['data'][0]['id']"
check_json "Embedding"   "http://192.168.1.189:8001/v1/models" "['data'][0]['id']"
check_json "Reranker"    "http://192.168.1.189:8003/v1/models" "['data'][0]['id']"

echo ""
echo "Agents:"
check_json "Agent Server" "http://192.168.1.244:9000/health" "['status']"

echo ""
echo "Web Apps:"
check "Dashboard"     "http://192.168.1.225:3001/"
check "Dashboard API" "http://192.168.1.225:3001/api/gpu"  # SSE stream verified via gpu route
check "EoBQ"          "http://192.168.1.225:3002/"
check "ComfyUI"       "http://192.168.1.225:8188/system_stats"
check "Ulrich"        "http://192.168.1.225:3003/"

echo ""
echo "Infrastructure:"
check_json "GPU Orchestrator" "http://192.168.1.244:9200/health" "['status']"
check "Qdrant"     "http://192.168.1.203:6333/healthz"
check "Prometheus" "http://192.168.1.203:9090/-/healthy"
check "Grafana"    "http://192.168.1.203:3000/api/health"
check "Kokoro TTS" "http://192.168.1.244:8200/v1/models"

echo ""
echo "=== Result: $CHECKS checks, $FAILURES failures ==="

if [ "$FAILURES" -gt 0 ]; then
    echo "⚠️  $FAILURES service(s) failed verification"
    if [ "$NOTIFY" = "--notify" ]; then
        curl -s -d "Deploy verification: $FAILURES/$CHECKS failed" "$NTFY_URL" > /dev/null 2>&1
    fi
    exit 1
else
    echo "✅ All services healthy"
    exit 0
fi
