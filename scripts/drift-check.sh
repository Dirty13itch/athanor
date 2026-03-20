#!/bin/bash
# Athanor Drift Detection — verifies system matches architectural decisions
# Run: bash scripts/drift-check.sh


# Source cluster config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

PASS=0
FAIL=0
check() {
    if eval "$2" >/dev/null 2>&1; then
        echo "  PASS: $1"
        ((PASS++))
    else
        echo "  FAIL: $1"
        ((FAIL++))
    fi
}

echo "=== Drift Detection $(date) ==="
echo ""

echo "--- PRINCIPLE: Zero Anthropic API spending ---"
check "No ANTHROPIC_API_KEY in LiteLLM container" \
    '! ssh root@${VAULT_IP} "docker inspect litellm --format={{range\ .Config.Env}}{{println\ .}}{{end}}" 2>/dev/null | grep -q ANTHROPIC_API_KEY'
check "No anthropic entries in LiteLLM config" \
    '! ssh root@${VAULT_IP} grep -q anthropic /mnt/user/appdata/litellm/config.yaml 2>/dev/null'

echo ""
echo "--- PRINCIPLE: No subscription-CLI models in LiteLLM ---"
check "No OpenAI GPT models in LiteLLM" \
    '! ssh root@${VAULT_IP} grep -q "openai/gpt" /mnt/user/appdata/litellm/config.yaml 2>/dev/null'
check "No Gemini in LiteLLM" \
    '! ssh root@${VAULT_IP} grep -q "gemini/" /mnt/user/appdata/litellm/config.yaml 2>/dev/null'
check "No Kimi/Moonshot in LiteLLM" \
    '! ssh root@${VAULT_IP} grep -q "moonshot/" /mnt/user/appdata/litellm/config.yaml 2>/dev/null'
check "No Z.ai/GLM in LiteLLM" \
    '! ssh root@${VAULT_IP} grep -q "zai/" /mnt/user/appdata/litellm/config.yaml 2>/dev/null'
check "No OpenRouter in LiteLLM" \
    '! ssh root@${VAULT_IP} grep -q "openrouter/" /mnt/user/appdata/litellm/config.yaml 2>/dev/null'

echo ""
echo "--- PRINCIPLE: Local-only fallbacks ---"
check "No claude in fallback chains" \
    '! ssh root@${VAULT_IP} grep -A20 "fallbacks:" /mnt/user/appdata/litellm/config.yaml 2>/dev/null | grep -q "claude"'

echo ""
echo "--- INFRASTRUCTURE ---"
check "LiteLLM responding" \
    'curl -sf -H "Authorization: Bearer ${LITELLM_KEY}" ${LITELLM_URL}/health'
check "Gateway responding" \
    'curl -sf http://localhost:8700/health'
check "Dashboard serving" \
    'curl -sf http://localhost:3001/'
check "Subscription scheduler responding" \
    'curl -sf http://localhost:8065/health'
check "Semantic router responding" \
    'curl -sf http://localhost:8060/health'
check "Agent server responding" \
    'curl -sf ${AGENT_SERVER_URL}/health --connect-timeout 3'
check "OpenFang running" \
    'openfang status 2>&1 | grep -q running'

echo ""
echo "--- OVERNIGHT PIPELINE ---"
check "No ANTHROPIC_API_KEY in overnight script" \
    '! grep -q ANTHROPIC_API_KEY /home/shaun/bin/overnight-coding.sh'
check "Overnight script syntax valid" \
    'bash -n /home/shaun/bin/overnight-coding.sh'
check "aider in PATH" 'which aider'
check "gsd in PATH" 'which gsd'
check "codex in PATH" 'which codex'

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "No drift detected." || echo "DRIFT DETECTED"

# Send ntfy alert if drift detected
if [ "$FAIL" -gt 0 ]; then
    curl -s -H "Title: Drift Detected ($FAIL failures)" \
         -H "Priority: high" \
         -H "Tags: warning" \
         -d "Drift check found $FAIL issue(s). Run scripts/drift-check.sh for details." \
         ${NTFY_TOPIC_URL}
fi
