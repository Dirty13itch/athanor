#!/usr/bin/env bash
# Athanor model inventory — scans NFS and reports what's available vs loaded
# Usage: bash scripts/model-inventory.sh

set -euo pipefail

VAULT_HOST="192.168.1.203"
LITELLM_URL="http://${VAULT_HOST}:4000"
LITELLM_KEY="${ATHANOR_LITELLM_API_KEY:-${LITELLM_API_KEY:-${OPENAI_API_KEY:-}}}"
FOUNDRY_HOST="192.168.1.244"
WORKSHOP_HOST="192.168.1.225"

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
curl -s -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" 2>/dev/null \
    | python3 -c "
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
for node in "FOUNDRY:${FOUNDRY_HOST}:8000" "WORKSHOP:${WORKSHOP_HOST}:8000"; do
    IFS=: read -r name host port <<< "$node"
    models=$(curl -s "http://${host}:${port}/v1/models" 2>/dev/null \
        | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('data', []):
        print(m['id'])
except: pass
" 2>/dev/null)
    if [ -n "$models" ]; then
        echo "  ${name} (${host}:${port}): ${models}"
    else
        echo "  ${name} (${host}:${port}): (not serving / unreachable)"
    fi
done

echo ""
echo "============================================"
