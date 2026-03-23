#!/bin/bash
# Smoke test — verifies top 20 critical endpoints
# Exit 0 = all pass, Exit 1 = failures
FAILS=0
check() {
  local name="$1" url="$2" timeout="${3:-5}"
  status=$(curl -sf -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null)
  if [ "$status" = "200" ]; then printf "  OK  %s\n" "$name"; else printf "FAIL  %s (HTTP %s)\n" "$name" "$status"; FAILS=$((FAILS+1)); fi
}
echo "=== Smoke Test $(date -Iseconds) ==="
check "Gateway"         "http://localhost:8700/health"
check "MIND"            "http://localhost:8710/health"
check "Memory"          "http://localhost:8720/health"
check "Governor"        "http://localhost:8760/health"
check "Dashboard"       "http://localhost:3001/"
check "Embedding"       "http://localhost:8001/v1/models"
check "Reranker"        "http://localhost:8003/v1/models"
check "Semantic Router" "http://localhost:8060/health"
check "Burn Scheduler"  "http://localhost:8065/health"
check "LiteLLM"         "http://192.168.1.203:4000/health" 10
check "Qdrant"          "http://192.168.1.203:6333/healthz"
check "Prometheus"      "http://192.168.1.203:9090/-/healthy"
check "Grafana"         "http://192.168.1.203:3000/api/health"
check "Agent Server"    "http://192.168.1.244:9000/health"
check "vLLM Coord"      "http://192.168.1.244:8000/health" 10
check "vLLM Coder"      "http://192.168.1.244:8006/health" 10
check "vLLM Sovereign"  "http://192.168.1.225:8010/health" 10
check "ComfyUI"         "http://192.168.1.225:8188/system_stats"
check "Ollama"          "http://192.168.1.225:11434/api/tags"
check "ntfy"            "http://192.168.1.203:8880/v1/health"
echo "=== $FAILS failures ==="
exit $((FAILS > 0))
