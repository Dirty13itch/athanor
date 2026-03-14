#!/usr/bin/env bash
# health-check-all.sh — Check all Athanor service health endpoints
# Usage: scripts/health-check-all.sh [-q] [-j]
#   -q  Quiet mode: only show failures
#   -j  JSON output (no colors, machine-readable)
set -euo pipefail

QUIET=false
JSON=false
while getopts "qj" opt; do
  case $opt in
    q) QUIET=true ;;
    j) JSON=true ;;
    *) echo "Usage: $0 [-q] [-j]" >&2; exit 1 ;;
  esac
done

# Colors (disabled if not a terminal or JSON mode)
if [[ -t 1 ]] && ! $JSON; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[0;33m'
  BOLD='\033[1m'
  NC='\033[0m'
else
  GREEN='' RED='' YELLOW='' BOLD='' NC=''
fi

# Service definitions: NAME|URL|METHOD
# METHOD: http (curl GET), tcp (nc check), redis (redis-cli ping)
SERVICES=(
  "Coordinator vLLM|http://192.168.1.244:8000/health|http"
  "Coder vLLM|http://192.168.1.244:8006/health|http"
  "Agent Server|http://192.168.1.244:9000/health|http"
  "Worker vLLM|http://192.168.1.225:8000/health|http"
  "Dashboard|http://192.168.1.225:3001|http"
  "EoBQ|http://192.168.1.225:3002|http"
  "LiteLLM|http://192.168.1.203:4000/health/readiness|http"
  "Grafana|http://192.168.1.203:3000/api/health|http"
  "Prometheus|http://192.168.1.203:9090/-/healthy|http"
  "LangFuse|http://192.168.1.203:3030|http"
  "Qdrant|http://192.168.1.203:6333/healthz|http"
  "Neo4j|http://192.168.1.203:7474|http"
  "Redis|192.168.1.203:6379|redis"
  "Embedding|http://192.168.1.189:8001/health|http"
  "Reranker|http://192.168.1.189:8003/health|http"
)

TOTAL=0
UP=0
DOWN=0
RESULTS=()

check_http() {
  local url="$1"
  local start end status latency
  start=$(date +%s%N)
  status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || echo "000")
  end=$(date +%s%N)
  latency=$(( (end - start) / 1000000 ))

  if [[ "$status" -ge 200 && "$status" -lt 400 ]]; then
    echo "UP|${latency}ms"
  else
    echo "DOWN|${latency}ms"
  fi
}

check_redis() {
  local hostport="$1"
  local host="${hostport%%:*}"
  local port="${hostport##*:}"
  local start end latency result

  start=$(date +%s%N)
  if command -v redis-cli &>/dev/null; then
    result=$(redis-cli -h "$host" -p "$port" ping 2>/dev/null || echo "FAIL")
  else
    result=$(echo "PING" | nc -w 3 "$host" "$port" 2>/dev/null || echo "FAIL")
  fi
  end=$(date +%s%N)
  latency=$(( (end - start) / 1000000 ))

  if [[ "$result" == *"PONG"* ]]; then
    echo "UP|${latency}ms"
  else
    echo "DOWN|${latency}ms"
  fi
}

# Header
if ! $JSON; then
  printf "${BOLD}%-20s %-45s %-8s %s${NC}\n" "Service" "URL" "Status" "Latency"
  printf "%-20s %-45s %-8s %s\n" "-------" "---" "------" "-------"
fi

for entry in "${SERVICES[@]}"; do
  IFS='|' read -r name url method <<< "$entry"
  TOTAL=$((TOTAL + 1))

  case "$method" in
    http)  result=$(check_http "$url") ;;
    redis) result=$(check_redis "$url") ;;
    *)     result="DOWN|0ms" ;;
  esac

  status="${result%%|*}"
  latency="${result##*|}"

  if [[ "$status" == "UP" ]]; then
    UP=$((UP + 1))
    color="$GREEN"
  else
    DOWN=$((DOWN + 1))
    color="$RED"
  fi

  if $JSON; then
    RESULTS+=("{\"name\":\"$name\",\"url\":\"$url\",\"status\":\"$status\",\"latency\":\"$latency\"}")
  else
    if $QUIET && [[ "$status" == "UP" ]]; then
      continue
    fi
    printf "%-20s %-45s ${color}%-8s${NC} %s\n" "$name" "$url" "$status" "$latency"
  fi
done

# Summary
if $JSON; then
  joined=$(IFS=,; echo "${RESULTS[*]}")
  echo "{\"total\":$TOTAL,\"up\":$UP,\"down\":$DOWN,\"services\":[$joined]}"
else
  echo ""
  if [[ $DOWN -eq 0 ]]; then
    printf "${GREEN}All $TOTAL services UP${NC}\n"
  else
    printf "${RED}$DOWN/$TOTAL services DOWN${NC}\n"
  fi
fi

# Exit code: 0 if all up, 1 if any down
[[ $DOWN -eq 0 ]]
