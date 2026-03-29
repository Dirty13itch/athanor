#!/usr/bin/env bash
# Post-deploy verification — run after any container restart/rebuild.
# Checks all critical endpoints and reports failures.
#
# Usage: ./verify-deploy.sh [--notify]
#   --notify: send failures to ntfy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

NOTIFY="${1:-}"
EOQ_URL="${EOQ_URL:-http://${WORKSHOP_IP}:3002}"
ULRICH_URL="${ULRICH_URL:-http://${WORKSHOP_IP}:3003}"
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
check_json "Coordinator" "${VLLM_COORDINATOR_URL}/v1/models" "['data'][0]['id']"
check_json "Coder"       "${VLLM_CODER_URL}/v1/models" "['data'][0]['id']"
check_json "Worker"      "${VLLM_WORKER_URL}/v1/models" "['data'][0]['id']"
check_json "Embedding"   "${EMBEDDING_URL}/v1/models" "['data'][0]['id']"
check_json "Reranker"    "${RERANKER_URL}/v1/models" "['data'][0]['id']"

echo ""
echo "Agents:"
check_json "Agent Server" "${AGENT_SERVER_URL}/health" "['status']"

echo ""
echo "Web Apps:"
check "Command Center runtime fallback" "${DASHBOARD_URL}/api/operator/session"
check "EoBQ"          "${EOQ_URL}/"
check "ComfyUI"       "${COMFYUI_URL}/system_stats"
check "Ulrich"        "${ULRICH_URL}/"

echo ""
echo "Infrastructure:"
check_json "GPU Orchestrator" "${GPU_ORCHESTRATOR_URL}/health" "['status']"
check "Qdrant"     "${QDRANT_URL}/healthz"
check "Prometheus" "${PROMETHEUS_URL}/-/healthy"
check "Grafana"    "${GRAFANA_URL}/api/health"
check "Kokoro TTS" "${SPEACHES_URL}/v1/models"

echo ""
echo "=== Result: $CHECKS checks, $FAILURES failures ==="

if [ "$FAILURES" -gt 0 ]; then
    echo "⚠️  $FAILURES service(s) failed verification"
    if [ "$NOTIFY" = "--notify" ]; then
        curl -s -d "Deploy verification: $FAILURES/$CHECKS failed" "${NTFY_TOPIC_URL}" > /dev/null 2>&1
    fi
    exit 1
else
    echo "✅ All services healthy"
    exit 0
fi
