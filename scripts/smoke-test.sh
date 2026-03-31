#!/usr/bin/env bash
# Smoke test - verifies critical endpoints
# Exit 0 = all pass, Exit 1 = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

SECRET_DIR="${ATHANOR_SECRET_DIR:-$HOME/.secrets}"
LITELLM_KEY_FILE="${ATHANOR_LITELLM_MASTER_KEY_FILE:-$SECRET_DIR/litellm-master-key}"
LITELLM_HEADER=""
if [ -r "${LITELLM_KEY_FILE}" ]; then
  LITELLM_HEADER="Authorization: Bearer $(tr -d '\r\n' < "${LITELLM_KEY_FILE}")"
fi

FAILS=0

check() {
  local name="$1" url="$2" timeout="${3:-5}" header="${4:-}"
  status=$(curl -sf -o /dev/null -w "%{http_code}" --max-time "$timeout" ${header:+-H "$header"} "$url" 2>/dev/null)
  if [ "$status" = "200" ]; then
    printf "  OK  %s\n" "$name"
  else
    printf "FAIL  %s (HTTP %s)\n" "$name" "$status"
    FAILS=$((FAILS + 1))
  fi
}

echo "=== Smoke Test $(date -Iseconds) ==="
check "Gateway"           "${GATEWAY_URL}/health"
check "Memory"            "${MEMORY_URL}/health"
check "Command Center runtime fallback" "${DASHBOARD_URL}/api/operator/session"
check "Quality Gate"      "${QUALITY_GATE_URL}/health"
check "Embedding"         "${EMBEDDING_URL}/v1/models"
check "Reranker"          "${RERANKER_URL}/v1/models"
check "Semantic Router"   "${SEMANTIC_ROUTER_URL}/health"
check "Subscription Burn" "${SUBSCRIPTION_BURN_URL}/health"
check "LiteLLM"           "${LITELLM_URL}/health" 10 "${LITELLM_HEADER}"
check "Qdrant"            "${QDRANT_URL}/collections"
check "Prometheus"        "${PROMETHEUS_URL}/-/healthy"
check "Grafana"           "${GRAFANA_URL}/api/health"
check "Agent Server"      "${AGENT_SERVER_URL}/health"
check "vLLM Coord"        "${VLLM_COORDINATOR_URL}/health" 10
check "vLLM Coder"        "${VLLM_CODER_URL}/health" 10
check "Ollama Workshop"   "${OLLAMA_WORKSHOP_URL}/api/tags"
check "ComfyUI"           "${COMFYUI_URL}/system_stats"
check "ntfy"              "${NTFY_URL}/v1/health"

echo "=== $FAILS failures ==="
exit $((FAILS > 0))
