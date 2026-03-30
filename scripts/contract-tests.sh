#!/usr/bin/env bash
# Athanor Contract Tests — frozen interface enforcement
# Verifies that key API contracts have not changed unexpectedly.
# Exits 0 if all contracts hold. Exits 1 on any violation.
# Can run standalone or be sourced from drift-check.sh.
#
# Usage:
#   ./contract-tests.sh              # standalone
#   ./contract-tests.sh --quiet      # suppress per-check output (summary only)
#   source contract-tests.sh         # include results in parent script variables
#
# Integration with drift-check.sh:
#   Add near the bottom of drift-check.sh:
#     source "$(dirname "$0")/contract-tests.sh" --quiet
#     FAIL=$((FAIL + CONTRACT_FAIL))
#     PASS=$((PASS + CONTRACT_PASS))
#     FAILURES="${FAILURES}${CONTRACT_FAILURES}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

SECRET_DIR="${ATHANOR_SECRET_DIR:-$HOME/.secrets}"
LITELLM_KEY_FILE="${ATHANOR_LITELLM_MASTER_KEY_FILE:-$SECRET_DIR/litellm-master-key}"
LITELLM_KEY="${LITELLM_MASTER_KEY:-}"

# Read LiteLLM key
if [ -z "${LITELLM_KEY}" ] && [ -f "${LITELLM_KEY_FILE}" ]; then
    LITELLM_KEY="$(tr -d '\n' < "${LITELLM_KEY_FILE}")"
fi

QUIET=false
[[ "$1" == "--quiet" ]] && QUIET=true

CONTRACT_PASS=0
CONTRACT_FAIL=0
CONTRACT_SKIP=0
CONTRACT_FAILURES=""

cpass() {
    ((CONTRACT_PASS++))
    $QUIET || printf "  PASS [CONTRACT] %s\n" "$1"
}

cfail() {
    ((CONTRACT_FAIL++))
    CONTRACT_FAILURES="${CONTRACT_FAILURES}  - [CONTRACT] ${1}\n"
    $QUIET || printf "  FAIL [CONTRACT] %s\n" "$1"
}

cskip() {
    ((CONTRACT_SKIP++))
    $QUIET || printf "  SKIP [CONTRACT] %s\n" "$1"
}

contract() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        cpass "$name"
    else
        cfail "$name"
    fi
}

$QUIET || echo ""
$QUIET || echo "=== Athanor Contract Tests $(date) ==="
$QUIET || echo ""
$QUIET || echo "--- Memory API (DEV:8720) ---"

# CONTRACT: Memory health response must have status=ok
contract "Memory /health returns status=ok" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"status\")==\"ok\" else 1)"'

# CONTRACT: Memory health response must include service=memory
contract "Memory /health includes service=memory" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"service\")==\"memory\" else 1)"'

# CONTRACT: Memory version field must exist and be non-empty
contract "Memory /health has version field" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"version\") else 1)"'

# CONTRACT: All 6 canonical tiers present in health response
contract "Memory /health has all 6 tiers (working,episodic,semantic,procedural,resource,vault)" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
tiers=d.get(\"tiers\",{})
required={\"working\",\"episodic\",\"semantic\",\"procedural\",\"resource\",\"vault\"}
missing=required-set(tiers.keys())
sys.exit(0 if not missing else 1)
"'

# CONTRACT: All memory tier statuses must be ok
contract "Memory /health all tier statuses are ok" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
tiers=d.get(\"tiers\",{})
bad=[k for k,v in tiers.items() if v!=\"ok\"]
sys.exit(0 if not bad else 1)
"'

# CONTRACT: Memory stats endpoint must return all 6 tiers
contract "Memory /v1/memory/stats returns all 6 tiers" \
    'curl -sf --max-time 5 "${MEMORY_URL}/v1/memory/stats" | python3 -c "
import sys,json
d=json.load(sys.stdin)
required={\"working\",\"episodic\",\"semantic\",\"procedural\",\"resource\",\"vault\"}
missing=required-set(d.keys())
sys.exit(0 if not missing else 1)
"'

# CONTRACT: /v1/memory/store endpoint exists (POST returns 4xx not 404)
contract "Memory /v1/memory/store endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -X POST "${MEMORY_URL}/v1/memory/store" -H "Content-Type: application/json" -d "{}"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

# CONTRACT: /v1/search endpoint exists
contract "Memory /v1/search endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -X POST "${MEMORY_URL}/v1/search" -H "Content-Type: application/json" -d "{}"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

$QUIET || echo ""
$QUIET || echo "--- Gateway API (DEV:8700) ---"

# CONTRACT: Gateway health response uses the shared health status vocabulary
contract "Gateway /health returns shared health status" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"status\") in {\"ok\",\"healthy\",\"degraded\"} else 1)"'

# CONTRACT: Gateway health includes service=gateway
contract "Gateway /health includes service=gateway" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"service\")==\"gateway\" else 1)"'

# CONTRACT: Gateway version field present
contract "Gateway /health has version field" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"version\") else 1)"'

# CONTRACT: Gateway /v1/models endpoint exists and returns JSON
contract "Gateway /v1/models returns JSON" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/v1/models" | python3 -c "import sys,json; json.load(sys.stdin); sys.exit(0)"'

# CONTRACT: Gateway OpenAPI spec is reachable
contract "Gateway /openapi.json is reachable" \
    'curl -sf --max-time 5 "${GATEWAY_URL}/openapi.json" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if \"paths\" in d else 1)"'

$QUIET || echo ""
$QUIET || echo "--- Agent Server (FOUNDRY:9000) ---"

# CONTRACT: Agent server health returns status=healthy
contract "Agent server /health returns status=healthy" \
    'curl -sf --max-time 10 "${AGENT_SERVER_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"status\")==\"healthy\" else 1)"'

# CONTRACT: Agent count must equal 9
contract "Agent server reports exactly 9 agents" \
    'curl -sf --max-time 10 "${AGENT_SERVER_URL}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get(\"agent_count\")==9 else 1)"'

# CONTRACT: All 9 expected agents are present by name
contract "Agent server has all 9 expected agent names" \
    'curl -sf --max-time 10 "${AGENT_SERVER_URL}/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
expected={\"general-assistant\",\"media-agent\",\"research-agent\",\"creative-agent\",
           \"knowledge-agent\",\"home-agent\",\"coding-agent\",\"stash-agent\",\"data-curator\"}
present=set(d.get(\"agents\",[]))
missing=expected-present
sys.exit(0 if not missing else 1)
"'

# CONTRACT: Agent server OpenAPI spec reachable (auth not required for docs)
contract "Agent server /openapi.json is reachable" \
    'curl -sf --max-time 10 "${AGENT_SERVER_URL}/openapi.json" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if \"paths\" in d else 1)"'

# CONTRACT: /v1/chat/completions endpoint exists (returns auth error, not 404)
contract "Agent server /v1/chat/completions endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -X POST "${AGENT_SERVER_URL}/v1/chat/completions" -H "Content-Type: application/json" -d "{}"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

$QUIET || echo ""
$QUIET || echo "--- LiteLLM (VAULT:4000) ---"

if [[ -n "${LITELLM_KEY:-}" ]]; then
contract "LiteLLM /health reachable with master key" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/health" >/dev/null'

contract "LiteLLM has reasoning model alias" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ids=[m[\"id\"] for m in d.get(\"data\",[])]
sys.exit(0 if \"reasoning\" in ids else 1)
"'

contract "LiteLLM has coding model alias" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ids=[m[\"id\"] for m in d.get(\"data\",[])]
sys.exit(0 if \"coding\" in ids else 1)
"'

contract "LiteLLM has worker model alias" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ids=[m[\"id\"] for m in d.get(\"data\",[])]
sys.exit(0 if \"worker\" in ids else 1)
"'

# CONTRACT: LiteLLM model count >= 15 (we have 20+; dramatic drop is a signal)
contract "LiteLLM has >= 15 model aliases" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
count=len(d.get(\"data\",[]))
sys.exit(0 if count >= 15 else 1)
"'

contract "LiteLLM /metrics/ endpoint responds" \
    'curl -sf --max-time 5 -H "Authorization: Bearer ${LITELLM_KEY}" "${LITELLM_URL}/metrics/" | grep -q "litellm"'
else
    cskip "LiteLLM /health reachable with master key"
    cskip "LiteLLM has reasoning model alias"
    cskip "LiteLLM has coding model alias"
    cskip "LiteLLM has worker model alias"
    cskip "LiteLLM has >= 15 model aliases"
    cskip "LiteLLM /metrics/ endpoint responds"
fi

$QUIET || echo ""
$QUIET || echo "--- Supporting Services ---"

# CONTRACT: Qdrant health endpoint returns ok
contract "Qdrant /healthz returns ok" \
    'curl -sf --max-time 5 "${QDRANT_URL}/healthz" | grep -qi "ok\|true\|healthy\|passed"'

# CONTRACT: Qdrant collections endpoint reachable
contract "Qdrant /collections endpoint reachable" \
    'curl -sf --max-time 5 "${QDRANT_URL}/collections" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if \"result\" in d else 1)"'

# CONTRACT: Memory backends (qdrant + meilisearch) both ok per health response
contract "Memory backends qdrant+meilisearch both ok" \
    'curl -sf --max-time 5 "${MEMORY_URL}/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
backends=d.get(\"backends\",{})
bad=[k for k,v in backends.items() if v!=\"ok\"]
sys.exit(0 if not bad else 1)
"'

# CONTRACT: Embedding service responds on DEV:8001
contract "Embedding service (DEV:8001) health ok" \
    'curl -sf --max-time 5 "${EMBEDDING_URL}/health" >/dev/null'

# CONTRACT: Reranker service responds on DEV:8003
contract "Reranker service (DEV:8003) health ok" \
    'curl -sf --max-time 5 "${RERANKER_URL}/health" >/dev/null'

$QUIET || echo ""
$QUIET || echo "--- Interface Shape Contracts ---"

# CONTRACT: Memory /v1/ingest endpoint exists (critical ingest path)
contract "Memory /v1/ingest endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -X POST "${MEMORY_URL}/v1/ingest" -H "Content-Type: application/json" -d "{}"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

# CONTRACT: Memory /v1/collections endpoint exists
contract "Memory /v1/collections endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${MEMORY_URL}/v1/collections"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

# CONTRACT: Gateway /v1/chat/completions endpoint exists (core LLM routing path)
contract "Gateway /v1/chat/completions endpoint exists" \
    'CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -X POST "${GATEWAY_URL}/v1/chat/completions" -H "Content-Type: application/json" -d "{}"); [ "$CODE" != "404" ] && [ "$CODE" != "000" ]'

# CONTRACT: OpenFang health endpoint responds
contract "OpenFang API (DEV:4200) health ok" \
    'curl -sf --max-time 5 "${OPENFANG_URL}/api/health" >/dev/null'

# CONTRACT: Subscription Burn health responds
contract "Subscription Burn (DEV:8065) health ok" \
    'curl -sf --max-time 5 "${SUBSCRIPTION_BURN_URL}/health" >/dev/null'

$QUIET || echo ""
$QUIET || echo "=== Contract Test Results: ${CONTRACT_PASS} passed, ${CONTRACT_FAIL} failed, ${CONTRACT_SKIP} skipped out of $((CONTRACT_PASS+CONTRACT_FAIL+CONTRACT_SKIP)) checks ==="

if [ "$CONTRACT_FAIL" -eq 0 ]; then
    $QUIET || echo "All contracts hold."
else
    $QUIET || echo "CONTRACT VIOLATIONS: ${CONTRACT_FAIL} check(s) failed:"
    $QUIET || printf "%b" "$CONTRACT_FAILURES"

    # Send ntfy alert only when running standalone (not sourced into drift-check)
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
        ALERT_BODY="Contract tests: ${CONTRACT_FAIL} of $((CONTRACT_PASS+CONTRACT_FAIL)) checks failed:\n${CONTRACT_FAILURES}"
        curl -s \
             -H "Title: Contract Tests Failed" \
             -H "Priority: high" \
             -H "Tags: warning,athanor,contracts" \
             -d "$(printf '%b' "$ALERT_BODY")" \
             "${NTFY_URL}/athanor-alerts" >/dev/null 2>&1
    fi
fi

# Export counts for drift-check.sh integration
export CONTRACT_PASS CONTRACT_FAIL CONTRACT_SKIP CONTRACT_FAILURES

# Exit non-zero only when running as main script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    [ "$CONTRACT_FAIL" -eq 0 ] && exit 0 || exit 1
fi
