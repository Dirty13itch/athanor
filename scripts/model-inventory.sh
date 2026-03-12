#!/usr/bin/env bash
# Athanor model inventory — scans NFS and reports what's available vs loaded
# Usage: bash scripts/model-inventory.sh

set -euo pipefail

VAULT_HOST="${ATHANOR_VAULT_HOST:-192.168.1.203}"
FOUNDRY_HOST="${ATHANOR_NODE1_HOST:-192.168.1.244}"
WORKSHOP_HOST="${ATHANOR_NODE2_HOST:-192.168.1.225}"
DEV_HOST="${ATHANOR_DEV_HOST:-192.168.1.189}"
LITELLM_URL="${ATHANOR_LITELLM_URL:-http://${VAULT_HOST}:4000}"
LITELLM_KEY="${ATHANOR_LITELLM_API_KEY:-${LITELLM_API_KEY:-${OPENAI_API_KEY:-}}}"
COORDINATOR_URL="${ATHANOR_VLLM_COORDINATOR_URL:-http://${FOUNDRY_HOST}:8000}"
CODER_URL="${ATHANOR_VLLM_CODER_URL:-${ATHANOR_VLLM_UTILITY_URL:-http://${FOUNDRY_HOST}:8006}}"
WORKER_URL="${ATHANOR_VLLM_WORKER_URL:-http://${WORKSHOP_HOST}:8000}"
EMBEDDING_URL="${ATHANOR_VLLM_EMBEDDING_URL:-http://${DEV_HOST}:8001}"
RERANKER_URL="${ATHANOR_VLLM_RERANKER_URL:-http://${DEV_HOST}:8003}"

if [ -z "${LITELLM_KEY}" ]; then
    echo "ERROR: set ATHANOR_LITELLM_API_KEY, LITELLM_API_KEY, or OPENAI_API_KEY before running model-inventory.sh" >&2
    exit 1
fi

echo "============================================"
echo "ATHANOR MODEL INVENTORY"
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================"

# 1. Models on NFS
echo ""
echo "--- Models on NFS (/mnt/vault/models/) ---"
ssh -o ConnectTimeout=5 root@${VAULT_HOST} \
    "for d in /mnt/user/models/*/; do
        name=\$(basename \"\$d\")
        size=\$(du -sh \"\$d\" 2>/dev/null | cut -f1)
        echo \"  \$size  \$name\"
    done" 2>/dev/null || echo "  (SSH to VAULT failed)"

# 2. LiteLLM registered models
echo ""
echo "--- LiteLLM registered models ---"
curl -s -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('data', []):
        print(f\"  {m['id']}\")
except: print('  (LiteLLM unreachable)')
" || echo "  (LiteLLM unreachable)"

# 3. vLLM loaded models per node
echo ""
echo "--- vLLM loaded models ---"
RUNTIMES=(
    "Foundry Coordinator|${COORDINATOR_URL}"
    "Foundry Coder|${CODER_URL}"
    "Workshop Worker|${WORKER_URL}"
    "DEV Embedding|${EMBEDDING_URL}"
    "DEV Reranker|${RERANKER_URL}"
)

for runtime in "${RUNTIMES[@]}"; do
    IFS='|' read -r name base_url <<< "$runtime"
    models=$(curl -s "${base_url%/}/v1/models" 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('data', []):
        print(m['id'])
except: pass
" 2>/dev/null)
    if [ -n "$models" ]; then
        echo "  ${name} (${base_url}): ${models}"
    else
        echo "  ${name} (${base_url}): (not serving / unreachable)"
    fi
done

echo ""
echo "============================================"
