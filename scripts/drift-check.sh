#!/bin/bash
# Athanor Drift Check — 55+ service health checks
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

check "Memory service (DEV:8720)" \
    'curl -sf --max-time 5 http://192.168.1.189:8720/health'

check "Gateway (DEV:8700)" \
    'curl -sf --max-time 5 http://192.168.1.189:8700/health'

check "MIND (DEV:8710)" \
    'curl -sf --max-time 5 http://192.168.1.189:8710/health'

check "Perception (DEV:8730)" \
    'curl -sf --max-time 5 http://192.168.1.189:8730/health'

check "UI (DEV:3001)" \
    'curl -sf --max-time 5 http://192.168.1.189:3001/'

check "Embedding service (DEV:8001)" \
    'curl -sf --max-time 5 http://192.168.1.189:8001/health'

check "Reranker service (DEV:8003)" \
    'curl -sf --max-time 5 http://192.168.1.189:8003/health'

check "Subscription burn scheduler (DEV:8065)" \
    'curl -sf --max-time 5 http://192.168.1.189:8065/health'

check "OpenFang (DEV:4200)" \
    'curl -sf --max-time 5 http://192.168.1.189:4200/api/health'

check "Semantic Router (DEV:8060)" \
    'curl -sf --max-time 5 http://192.168.1.189:8060/health'

echo ""
echo "--- VAULT Services ---"

check "LiteLLM (VAULT:4000)" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" http://192.168.1.203:4000/health'

check "Qdrant (VAULT:6333)" \
    'curl -sf --max-time 5 http://192.168.1.203:6333/healthz'

check "Neo4j (VAULT:7687)" \
    'curl -sf --max-time 5 http://192.168.1.203:7474/'

check "Prometheus (VAULT:9090)" \
    'curl -sf --max-time 5 http://192.168.1.203:9090/-/healthy'

check "Grafana (VAULT:3000)" \
    'curl -sf --max-time 5 http://192.168.1.203:3000/api/health'

check "Stash (VAULT:9999)" \
    'curl -sf --max-time 5 http://192.168.1.203:9999/'

check "ntfy (VAULT:8880)" \
    'curl -sf --max-time 5 http://192.168.1.203:8880/v1/health'

check "n8n (VAULT:5678)" \
    'curl -sf --max-time 5 http://192.168.1.203:5678/healthz'

check "Langfuse (VAULT:3030)" \
    'curl -sf --max-time 5 http://192.168.1.203:3030/api/public/health'

check "Uptime Kuma (VAULT:3009)" \
    'curl -sf --max-time 5 http://192.168.1.203:3009/'

echo ""
echo "--- FOUNDRY Services ---"

check "Agent server (FOUNDRY:9000)" \
    'curl -sf --max-time 5 http://192.168.1.244:9000/health'

check "Voice pipeline (FOUNDRY:8250)" \
    'curl -sf --max-time 5 http://192.168.1.244:8250/health'

echo ""
echo "--- WORKSHOP Services ---"

check "ComfyUI (WORKSHOP:8188)" \
    'curl -sf --max-time 5 http://192.168.1.225:8188/'

echo ""
echo "--- Cross-Node / System State ---"

check "Memory consolidation cron exists" \
    'crontab -l 2>/dev/null | grep -q consolidat'

check "Auto_gen scanner running" \
    'curl -sf --max-time 5 http://192.168.1.189:8700/v1/generate/drops | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"scanner_running\",False) else 1)"'

check "Headscale mesh (DEV)" \
    'ping -c1 -W2 100.64.0.2 2>/dev/null'

check "Hindsight (DEV:8888)" \
    'curl -sf --max-time 5 http://192.168.1.189:8888/health 2>/dev/null || curl -sf --max-time 5 http://localhost:8888/ 2>/dev/null'

check "Heartbeat daemon" \
    'systemctl is-active athanor-heartbeat'

check "Gitea Actions Runner" \
    'systemctl is-active athanor-runner'

check "Open WebUI (DEV:3080)" \
    'curl -sf --max-time 5 http://192.168.1.189:3080/api/version'

check "Governor (DEV:8760)" \
    'curl -sf --max-time 5 http://192.168.1.189:8760/health'

# Classifier takes 45-55s on CPU -- increased timeout from 5s to 120s
check "Classifier (DEV:8740)" \
    'curl -sf --max-time 120 http://192.168.1.189:8740/health'

check "Arize Phoenix (DEV:6006)" \
    'curl -sf --max-time 5 http://192.168.1.189:6006/'

echo ""
echo "--- vLLM Endpoints ---"

check "vLLM coordinator health (FOUNDRY:8000)" \
    'curl -sf --max-time 10 http://192.168.1.244:8000/health'

check "vLLM coder health (FOUNDRY:8006)" \
    'curl -sf --max-time 10 http://192.168.1.244:8006/health'

check "Ollama sovereign (WORKSHOP:11434)"
    'curl -sf --max-time 10 http://192.168.1.225:11434/api/tags'

echo ""
echo "--- Agent & Model Checks ---"

check "Agent Server: 9 agents online" \
    'curl -sf --max-time 5 -H "Authorization: Bearer $(cat /home/shaun/.secrets/agent-server-api-key)" http://192.168.1.244:9000/v1/agents | python3 -c "import sys,json; d=json.load(sys.stdin); agents=d if isinstance(d,list) else d.get(\"agents\",[]); sys.exit(0 if len(agents)>=9 else 1)"'

check "Ollama has FIM model (qwen2.5-coder)" \
    'curl -sf --max-time 5 http://192.168.1.225:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); names=[m[\"name\"] for m in d.get(\"models\",[])]; sys.exit(0 if any(\"qwen2.5-coder\" in n for n in names) else 1)"'

check "ComfyUI system stats (WORKSHOP:8188)" \
    'curl -sf --max-time 5 http://192.168.1.225:8188/system_stats'

check "Arize Phoenix HTTP 200 (DEV:6006)" \
    '[ "$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://192.168.1.189:6006/)" = "200" ]'

echo ""
echo "--- Governor Checks ---"

check "Governor SQLite WAL mode" \
    'python3 -c "
import sqlite3, glob, sys
dbs = glob.glob(\"/home/shaun/repos/athanor/services/governor/*.db\") + glob.glob(\"/home/shaun/repos/athanor/data/governor/*.db\")
if not dbs: sys.exit(1)
for db in dbs:
    c = sqlite3.connect(db)
    mode = c.execute(\"PRAGMA journal_mode\").fetchone()[0]
    c.close()
    if mode != \"wal\": sys.exit(1)
sys.exit(0)
"'

check "Governor >5 active subscriptions" \
    'curl -sf --max-time 5 http://192.168.1.189:8760/health | python3 -c "
import sys,json
d = json.load(sys.stdin)
subs = d.get(\"subscriptions\", {})
if isinstance(subs, dict):
    active = sum(1 for v in subs.values() if v == \"active\")
elif isinstance(subs, list):
    active = len(subs)
else:
    active = int(subs)
sys.exit(0 if active > 5 else 1)
"'

check "overnight.py compiles" \
    'python3 -m py_compile /home/shaun/repos/athanor/services/governor/overnight.py'

check "All Governor Python files compile" \
    'for f in /home/shaun/repos/athanor/services/governor/*.py; do python3 -m py_compile "$f" || exit 1; done'

echo ""
echo "--- Memory & Data Checks ---"

check "Memory 6 tiers OK" \
    'curl -sf --max-time 5 http://192.168.1.189:8720/health | python3 -c "
import sys,json
d = json.load(sys.stdin)
tiers = d.get(\"tiers\", d.get(\"memory_tiers\", {}))
if isinstance(tiers, dict):
    ok = all(v in (\"ok\",\"healthy\",True) for v in tiers.values())
    sys.exit(0 if ok and len(tiers) >= 6 else 1)
elif isinstance(tiers, list):
    sys.exit(0 if len(tiers) >= 6 else 1)
else:
    sys.exit(1)
"'

check "Qdrant >5000 points" \
    'python3 -c "
import sys,json,urllib.request
colls = json.loads(urllib.request.urlopen(\"http://192.168.1.203:6333/collections\", timeout=5).read())
names = [c[\"name\"] for c in colls.get(\"result\",{}).get(\"collections\",[])]
total = 0
for name in names:
    info = json.loads(urllib.request.urlopen(f\"http://192.168.1.203:6333/collections/{name}\", timeout=5).read())
    total += info.get(\"result\",{}).get(\"points_count\",0) or 0
sys.exit(0 if total > 5000 else 1)
"'

check "Neo4j HTTP accessible" \
    '[ "$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://192.168.1.203:7474/)" = "200" ]'

echo ""
echo "--- Monitoring Checks ---"

check "Prometheus >45 targets UP" \
    'curl -sf --max-time 5 http://192.168.1.203:9090/api/v1/targets | python3 -c "
import sys,json
d = json.load(sys.stdin)
active = d.get(\"data\",{}).get(\"activeTargets\",[])
up = sum(1 for t in active if t.get(\"health\")==\"up\")
sys.exit(0 if up > 45 else 1)
"'

check "DCGM metrics for 8 GPUs" \
    'curl -sf --max-time 5 "http://192.168.1.203:9090/api/v1/query?query=count(DCGM_FI_DEV_GPU_UTIL)" | python3 -c "
import sys,json
d = json.load(sys.stdin)
results = d.get(\"data\",{}).get(\"result\",[])
val = int(results[0][\"value\"][1]) if results else 0
sys.exit(0 if val >= 8 else 1)
"'

check "Grafana 7 dashboards" \
    'curl -sf --max-time 5 -u admin:admin "http://192.168.1.203:3000/api/search?type=dash-db" | python3 -c "
import sys,json
d = json.load(sys.stdin)
sys.exit(0 if len(d) >= 7 else 1)
"'

echo ""

# Additional services (Phase 13)
check "Brain: system intelligence (DEV:8780)" \
    'curl -sf --max-time 5 http://localhost:8780/health'

check "Draftsman service (DEV:8400)" \
    'curl -sf --max-time 5 http://localhost:8400/ -o /dev/null'



# Additional services (Phase 13)










check "Quality Gate (DEV:8790)"     'curl -sf --max-time 5 http://localhost:8790/health' 
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


