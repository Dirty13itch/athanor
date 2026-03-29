#!/usr/bin/env bash
# Athanor Drift Check - service health checks
# Exits 0 if all pass, 1 if any fail.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

export ATHANOR_REPO_ROOT="${REPO_ROOT}"

SECRET_DIR="${ATHANOR_SECRET_DIR:-$HOME/.secrets}"
LITELLM_KEY_FILE="${ATHANOR_LITELLM_MASTER_KEY_FILE:-$SECRET_DIR/litellm-master-key}"
AGENT_KEY_FILE="${ATHANOR_AGENT_SERVER_API_KEY_FILE:-$SECRET_DIR/agent-server-api-key}"

if [ -r "${LITELLM_KEY_FILE}" ]; then
    LITELLM_KEY="$(tr -d '\r\n' < "${LITELLM_KEY_FILE}")"
fi

AGENT_SERVER_KEY=""
if [ -r "${AGENT_KEY_FILE}" ]; then
    AGENT_SERVER_KEY="$(tr -d '\r\n' < "${AGENT_KEY_FILE}")"
fi

HINDSIGHT_URL="${HINDSIGHT_URL:-http://${DEV_IP}:8888}"
ARIZE_PHOENIX_URL="${ARIZE_PHOENIX_URL:-http://${DEV_IP}:6006}"

PASS=0
FAIL=0
FAILURES=""

check() {
    local name="$1"
    local cmd="$2"
    if eval "${cmd}" >/dev/null 2>&1; then
        printf "  PASS [%02d] %s\n" $((PASS + FAIL + 1)) "${name}"
        ((PASS++))
    else
        printf "  FAIL [%02d] %s\n" $((PASS + FAIL + 1)) "${name}"
        ((FAIL++))
        FAILURES+="${name}"$'\n'
    fi
}

echo "=== Athanor Drift Check $(date) ==="
echo ""
echo "--- DEV Services ---"

check "Memory service (DEV:8720)" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health"'

check "Gateway (DEV:8700)" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/health"'

check "Command Center runtime fallback (DEV:3001)" \
    'curl -sf --max-time 5 "${DASHBOARD_URL}/api/operator/session"'

check "Embedding service (DEV:8001)" \
    'curl -sf --max-time 5 "${EMBEDDING_URL}/health"'

check "Reranker service (DEV:8003)" \
    'curl -sf --max-time 5 "${RERANKER_URL}/health"'

check "Subscription Burn (DEV:8065)" \
    'curl -sf --max-time 5 "${SUBSCRIPTION_BURN_URL}/health"'

check "OpenFang (DEV:4200)" \
    'curl -sf --max-time 5 "${OPENFANG_URL}/api/health"'

check "Semantic Router (DEV:8060)" \
    'curl -sf --max-time 5 "${SEMANTIC_ROUTER_URL}/health"'

echo ""
echo "--- VAULT Services ---"

check "LiteLLM (VAULT:4000)" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/health"'

check "Qdrant (VAULT:6333)" \
    'curl -sf --max-time 5 "${QDRANT_URL}/collections"'

check "Neo4j (VAULT:7687)" \
    'curl -sf --max-time 5 "${NEO4J_HTTP_URL}/"'

check "Prometheus (VAULT:9090)" \
    'curl -sf --max-time 5 "${PROMETHEUS_URL}/-/healthy"'

check "Grafana (VAULT:3000)" \
    'curl -sf --max-time 5 "${GRAFANA_URL}/api/health"'

check "Stash (VAULT:9999)" \
    'curl -sf --max-time 5 "${STASH_URL}/"'

check "ntfy (VAULT:8880)" \
    'curl -sf --max-time 5 "${NTFY_URL}/v1/health"'

check "n8n (VAULT:5678)" \
    'curl -sf --max-time 5 "${N8N_URL}/healthz"'

check "Langfuse (VAULT:3030)" \
    'curl -sf --max-time 5 "${LANGFUSE_URL}/api/public/health"'

check "Uptime Kuma (VAULT:3009)" \
    'curl -sf --max-time 5 "${UPTIME_KUMA_URL}/"'

echo ""
echo "--- FOUNDRY Services ---"

check "Agent server (FOUNDRY:9000)" \
    'curl -sf --max-time 5 "${AGENT_SERVER_URL}/health"'

check "Voice pipeline (FOUNDRY:8250)" \
    'curl -sf --max-time 5 "http://${FOUNDRY_IP}:8250/health"'

echo ""
echo "--- WORKSHOP Services ---"

check "ComfyUI (WORKSHOP:8188)" \
    'curl -sf --max-time 5 "${COMFYUI_URL}/system_stats"'

echo ""
echo "--- Cross-Node / System State ---"

check "Memory consolidation cron exists" \
    'crontab -l 2>/dev/null | grep -q consolidat'

check "Auto_gen scanner running" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/v1/generate/drops" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"scanner_running\", False) else 1)"'

check "Headscale mesh (DEV)" \
    'ping -c1 -W2 100.64.0.2 2>/dev/null'

check "Hindsight (DEV:8888)" \
    'curl -sf --max-time 5 "${HINDSIGHT_URL}/health" 2>/dev/null || curl -sf --max-time 5 "${HINDSIGHT_URL}/" 2>/dev/null'

check "Heartbeat daemon" \
    'systemctl is-active athanor-heartbeat'

check "Gitea Actions Runner" \
    'systemctl is-active athanor-runner'

check "Arize Phoenix (DEV:6006)" \
    'curl -sf --max-time 5 "${ARIZE_PHOENIX_URL}/"'

echo ""
echo "--- vLLM Endpoints ---"

check "vLLM coordinator health (FOUNDRY:8000)" \
    'curl -sf --max-time 10 "${VLLM_COORDINATOR_URL}/health"'

check "vLLM coder health (FOUNDRY:8006)" \
    'curl -sf --max-time 10 "${VLLM_CODER_URL}/health"'

check "Ollama workshop (WORKSHOP:11434)" \
    'curl -sf --max-time 10 "${OLLAMA_WORKSHOP_URL}/api/tags"'

echo ""
echo "--- Agent & Model Checks ---"

check "Agent Server: 9 agents online" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${AGENT_SERVER_KEY}" "${AGENT_SERVER_URL}/v1/agents" | python3 -c "import sys,json; d=json.load(sys.stdin); agents=d if isinstance(d, list) else d.get(\"agents\", []); sys.exit(0 if len(agents) >= 9 else 1)"'

check "Ollama has FIM model (qwen2.5-coder)" \
    'curl -sf --max-time 5 "${OLLAMA_WORKSHOP_URL}/api/tags" | python3 -c "import sys,json; d=json.load(sys.stdin); names=[m[\"name\"] for m in d.get(\"models\", [])]; sys.exit(0 if any(\"qwen2.5-coder\" in n for n in names) else 1)"'

check "ComfyUI system stats (WORKSHOP:8188)" \
    'curl -sf --max-time 5 "${COMFYUI_URL}/system_stats"'

check "Arize Phoenix HTTP 200 (DEV:6006)" \
    '[ "$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" "${ARIZE_PHOENIX_URL}/")" = "200" ]'

echo ""
echo "--- Retired Governor Facade Files ---"

GOVERNOR_HELPER_FILES=(
    "main.py"
    "overnight.py"
    "self_improve.py"
    "act_first.py"
    "status_report.py"
    "_imports.py"
)

for helper_file in "${GOVERNOR_HELPER_FILES[@]}"; do
    check "Governor helper ${helper_file} compiles" \
        "python3 -m py_compile \"${REPO_ROOT}/services/governor/${helper_file}\""
done

echo ""
echo "--- Memory & Data Checks ---"

check "Memory 6 tiers OK" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "import sys, json
d = json.load(sys.stdin)
tiers = d.get(\"tiers\", d.get(\"memory_tiers\", {}))
if isinstance(tiers, dict):
    ok = all(v in (\"ok\", \"healthy\", True) for v in tiers.values())
    sys.exit(0 if ok and len(tiers) >= 6 else 1)
elif isinstance(tiers, list):
    sys.exit(0 if len(tiers) >= 6 else 1)
else:
    sys.exit(1)"'

check "Qdrant >5000 points" \
    'python3 -c "import json, sys, urllib.request
colls = json.loads(urllib.request.urlopen(\"${QDRANT_URL}/collections\", timeout=5).read())
names = [c[\"name\"] for c in colls.get(\"result\", {}).get(\"collections\", [])]
total = 0
for name in names:
    info = json.loads(urllib.request.urlopen(f\"${QDRANT_URL}/collections/{name}\", timeout=5).read())
    total += info.get(\"result\", {}).get(\"points_count\", 0) or 0
sys.exit(0 if total > 5000 else 1)"'

check "Neo4j HTTP accessible" \
    '[ "$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" "${NEO4J_HTTP_URL}/")" = "200" ]'

if [ "${FAIL}" -gt 0 ]; then
    echo ""
    echo "Failed checks:"
    printf "%s" "${FAILURES}"
fi

echo ""
echo "=== Summary: ${PASS} passed, ${FAIL} failed ==="
exit $((FAIL > 0))
