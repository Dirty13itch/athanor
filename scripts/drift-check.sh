#!/bin/bash
# Athanor Drift Check — 25 service health checks
# Exits 0 if all pass, 1 if any fail. Sends ntfy alert on failure.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

# Read LiteLLM master key from secrets file if available
if [ -f /home/shaun/.secrets/litellm-master-key ]; then
    LITELLM_KEY="$(cat /home/shaun/.secrets/litellm-master-key | tr -d '\n')"
fi

PASS=0
FAIL=0
FAILURES=""

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        printf "  PASS [%02d] %s\n" $((PASS+FAIL+1)) "$name"
        ((PASS++))
    else
        printf "  FAIL [%02d] %s\n" $((PASS+FAIL+1)) "$name"
        ((FAIL++))
        FAILURES="${FAILURES}  - ${name}\n"
    fi
}

echo "=== Athanor Drift Check $(date) ==="
echo ""
echo "--- DEV Services ---"

# 1. Memory service
check "Memory service (DEV:8720)" \
    'curl -sf --max-time 5 http://192.168.1.189:8720/health'

# 2. Gateway
check "Gateway (DEV:8700)" \
    'curl -sf --max-time 5 http://192.168.1.189:8700/health'

# 3. MIND
check "MIND (DEV:8710)" \
    'curl -sf --max-time 5 http://192.168.1.189:8710/health'

# 4. Perception
check "Perception (DEV:8730)" \
    'curl -sf --max-time 5 http://192.168.1.189:8730/health'

# 5. UI
check "UI (DEV:3001)" \
    'curl -sf --max-time 5 http://192.168.1.189:3001/'

# 6. Embedding
check "Embedding service (DEV:8001)" \
    'curl -sf --max-time 5 http://192.168.1.189:8001/health'

# 7. Reranker
check "Reranker service (DEV:8003)" \
    'curl -sf --max-time 5 http://192.168.1.189:8003/health'

# 8. Subscription burn scheduler
check "Subscription burn scheduler (DEV:8065)" \
    'curl -sf --max-time 5 http://192.168.1.189:8065/health'

# 9. OpenFang
check "OpenFang (DEV:4200)" \
    'curl -sf --max-time 5 http://192.168.1.189:4200/api/health'

# 10. Semantic Router
check "Semantic Router (DEV:8060)" \
    'curl -sf --max-time 5 http://192.168.1.189:8060/health'

echo ""
echo "--- VAULT Services ---"

# 11. LiteLLM
check "LiteLLM (VAULT:4000)" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" http://192.168.1.203:4000/health'

# 12. Qdrant
check "Qdrant (VAULT:6333)" \
    'curl -sf --max-time 5 http://192.168.1.203:6333/healthz'

# 13. Neo4j
check "Neo4j (VAULT:7687)" \
    'curl -sf --max-time 5 http://192.168.1.203:7474/'

# 14. Prometheus
check "Prometheus (VAULT:9090)" \
    'curl -sf --max-time 5 http://192.168.1.203:9090/-/healthy'

# 15. Grafana
check "Grafana (VAULT:3000)" \
    'curl -sf --max-time 5 http://192.168.1.203:3000/api/health'

# 16. Stash
check "Stash (VAULT:9999)" \
    'curl -sf --max-time 5 http://192.168.1.203:9999/'

# 17. ntfy
check "ntfy (VAULT:8880)" \
    'curl -sf --max-time 5 http://192.168.1.203:8880/v1/health'

# 18. n8n
check "n8n (VAULT:5678)" \
    'curl -sf --max-time 5 http://192.168.1.203:5678/healthz'

echo ""
echo "--- FOUNDRY Services ---"

# 19. Agent server
check "Agent server (FOUNDRY:9000)" \
    'curl -sf --max-time 5 http://192.168.1.244:9000/health'

# 20. Agent server: 9 agents online
#n# 21. Agent server scheduler running
#check "Agent server scheduler" \n    'curl -sf --max-time 5 http://192.168.1.244:9000/health | python3 -c "import sys,json; sys.exit(0 if json.load(sys.stdin).get(\"status\") == \"ok\" else 1)"'
#check "Agent server: 9 agents online" \
#n# 21. Agent server scheduler running
#    'curl -sf --max-time 5 http://192.168.1.244:9000/health | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if len(d.get(\"agents\",[]))>=9 else 1)"'
#

# 22. Voice pipeline
check "Voice pipeline (FOUNDRY:8250)" \
    'curl -sf --max-time 5 http://192.168.1.244:8250/health'

echo ""
echo "--- WORKSHOP Services ---"

# 23. ComfyUI
check "ComfyUI (WORKSHOP:8188)" \
    'curl -sf --max-time 5 http://192.168.1.225:8188/'

echo ""
echo "--- System State ---"

# 24. Memory consolidation cron exists
check "Memory consolidation cron exists" \
    'crontab -l 2>/dev/null | grep -q consolidat'

# 25. Auto_gen scanner running
check "Auto_gen scanner running" \
    'curl -sf --max-time 5 http://192.168.1.189:8700/v1/generate/drops | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"scanner_running\",False) else 1)"'


echo ""
echo "--- NEW: Infrastructure Checks ---"

# 26. vLLM coordinator (FOUNDRY:8000)
check "vLLM coordinator (FOUNDRY:8000)" \
    'curl -sf --max-time 10 http://192.168.1.244:8000/v1/models'

# 27. vLLM coder (FOUNDRY:8006)
check "vLLM coder (FOUNDRY:8006)" \
    'curl -sf --max-time 10 http://192.168.1.244:8006/v1/models'

# 28. vLLM worker (WORKSHOP:8010)
check "vLLM worker (WORKSHOP:8010)" \
    'curl -sf --max-time 10 http://192.168.1.225:8010/v1/models'

# 29. Ollama (WORKSHOP:11434)
check "Ollama (WORKSHOP:11434)" \
    'curl -sf --max-time 5 http://192.168.1.225:11434/'

# 30. Langfuse (VAULT:3030)
check "Langfuse (VAULT:3030)" \
    'curl -sf --max-time 5 http://192.168.1.203:3030/api/public/health'

# 31. Uptime Kuma (VAULT:3009)
check "Uptime Kuma (VAULT:3009)" \
    'curl -sf --max-time 5 http://192.168.1.203:3009/'

# 32. Headscale mesh (DEV:100.64.0.1)
check "Headscale mesh (DEV)" \
    'ping -c1 -W2 100.64.0.2 2>/dev/null'

# 33. Hindsight (DEV:8888)
check "Hindsight (DEV:8888)" \
    'curl -sf --max-time 5 http://192.168.1.189:8888/health 2>/dev/null || curl -sf --max-time 5 http://localhost:8888/ 2>/dev/null'

# 34. Heartbeat daemon
check "Heartbeat daemon" \
    'systemctl is-active athanor-heartbeat'

# 35. Gitea Actions Runner
check "Gitea Actions Runner" \
    'systemctl is-active athanor-runner'


# 36. Open WebUI
check "Open WebUI (DEV:3080)"     'curl -sf --max-time 5 http://192.168.1.189:3080/api/version'
# 37. Governor
check "Governor (DEV:8760)"     'curl -sf --max-time 5 http://192.168.1.189:8760/health'
# 38. Classifier
check "Classifier (DEV:8740)"     'curl -sf --max-time 5 http://192.168.1.189:8740/health'
# 39. Arize Phoenix
check "Arize Phoenix (DEV:6006)"     'curl -sf --max-time 5 http://192.168.1.189:6006/'

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed out of $((PASS+FAIL)) checks ==="

if [ "$FAIL" -eq 0 ]; then
    echo "All checks passed. No drift detected."
    exit 0
else
    echo "DRIFT DETECTED: ${FAIL} check(s) failed:"
    printf "%b" "$FAILURES"
    # Send ntfy alert
    ALERT_BODY="${FAIL} of $((PASS+FAIL)) checks failed:\n${FAILURES}"
    curl -s \
         -H "Title: Drift Check Failed" \
         -H "Priority: high" \
         -H "Tags: warning,athanor" \
         -d "$(printf '%b' "$ALERT_BODY")" \
         http://192.168.1.203:8880/athanor-alerts >/dev/null 2>&1
    exit 1
fi

echo ""
echo "--- NEW: Infrastructure Checks ---"

