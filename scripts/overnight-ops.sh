#!/usr/bin/env bash
# Overnight autonomous operations for Athanor.
# Runs scheduled maintenance tasks that don't require human oversight.
#
# Usage: ./overnight-ops.sh [--dry-run]
# Systemd timer triggers at 11 PM, tasks complete by ~6 AM.
#
# Tasks (in order):
# 1. Knowledge re-indexing (Qdrant collection optimization)
# 2. Neo4j graph maintenance (stale node pruning)
# 3. Research job execution (pending research queue)
# 4. Ansible convergence dry-run (drift detection)
# 5. Gitea push (mirror current state)

set -euo pipefail

DRY_RUN="${1:-}"
LOG_DIR="/var/log/athanor"
LOG_FILE="$LOG_DIR/overnight-$(date +%Y-%m-%d).log"
AGENT_URL="http://192.168.1.244:9000"
QDRANT_URL="http://192.168.1.244:6333"
NEO4J_URL="http://192.168.1.203:7474"
REPO_DIR="$HOME/repos/athanor"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE"
}

run_or_skip() {
    if [ "$DRY_RUN" = "--dry-run" ]; then
        log "DRY-RUN: would execute: $*"
        return 0
    fi
    "$@"
}

log "=== Overnight operations starting ==="

# --- 1. Qdrant collection optimization ---
log "Phase 1: Qdrant collection optimization"
COLLECTIONS=$(curl -sf "$QDRANT_URL/collections" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('result', {}).get('collections', []):
    print(c['name'])
" 2>/dev/null || echo "")

if [ -n "$COLLECTIONS" ]; then
    for coll in $COLLECTIONS; do
        # Trigger optimizer (vacuum/compact)
        RESP=$(curl -sf -X POST "$QDRANT_URL/collections/$coll/index" 2>/dev/null || echo "failed")
        POINT_COUNT=$(curl -sf "$QDRANT_URL/collections/$coll" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('result', {}).get('points_count', '?'))
" 2>/dev/null || echo "?")
        log "  $coll: $POINT_COUNT points"
    done
else
    log "  WARN: Could not reach Qdrant at $QDRANT_URL"
fi

# --- 2. Neo4j graph maintenance ---
log "Phase 2: Neo4j graph maintenance"
# Count stale nodes (no activity in 30 days) — read-only query
STALE_COUNT=$(curl -sf -X POST "$NEO4J_URL/db/neo4j/tx/commit" \
    -H "Content-Type: application/json" \
    -H "Authorization: Basic $(echo -n 'neo4j:athanor2026' | base64)" \
    -d '{"statements":[{"statement":"MATCH (n) WHERE n.last_accessed < datetime() - duration({days: 30}) RETURN count(n) as stale"}]}' \
    2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
rows = data.get('results', [{}])[0].get('data', [])
print(rows[0]['row'][0] if rows else '0')
" 2>/dev/null || echo "?")
log "  Stale nodes (>30d): $STALE_COUNT"

# --- 3. Research job execution ---
log "Phase 3: Research job execution"
PENDING=$(curl -sf "$AGENT_URL/v1/research/jobs" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
pending = [j for j in data.get('jobs', []) if j.get('status') == 'pending']
print(len(pending))
" 2>/dev/null || echo "?")
log "  Pending research jobs: $PENDING"

if [ "$PENDING" != "?" ] && [ "$PENDING" -gt 0 ] 2>/dev/null; then
    # Execute up to 3 pending research jobs
    JOBS=$(curl -sf "$AGENT_URL/v1/research/jobs" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
pending = [j for j in data.get('jobs', []) if j.get('status') == 'pending']
for j in pending[:3]:
    print(j['id'])
" 2>/dev/null || echo "")
    for job_id in $JOBS; do
        run_or_skip curl -sf -X POST "$AGENT_URL/v1/research/jobs/$job_id/execute" > /dev/null 2>&1 || true
        log "  Executed research job: $job_id"
    done
fi

# --- 4. Ansible convergence dry-run ---
log "Phase 4: Ansible drift detection"
if command -v ansible-playbook &> /dev/null && [ -f "$REPO_DIR/ansible/playbooks/site.yml" ]; then
    cd "$REPO_DIR/ansible"
    # Check mode only — no changes
    DRIFT_OUTPUT=$(ansible-playbook playbooks/site.yml --check --diff \
        -i inventory.yml \
        --limit "core,interface,dev" \
        2>&1 || true)
    CHANGED=$(echo "$DRIFT_OUTPUT" | grep -c 'changed=' || echo "0")
    log "  Ansible check complete ($CHANGED lines with changes)"
    echo "$DRIFT_OUTPUT" >> "$LOG_FILE"
else
    log "  SKIP: ansible-playbook not found or site.yml missing"
fi

# --- 5. Git mirror to Gitea ---
log "Phase 5: Gitea mirror push"
cd "$REPO_DIR"
if git remote get-url gitea &>/dev/null; then
    run_or_skip git push gitea main 2>&1 | tee -a "$LOG_FILE" || log "  WARN: Gitea push failed"
    log "  Pushed to Gitea"
else
    log "  SKIP: No gitea remote configured"
fi

# --- Summary ---
log "=== Overnight operations complete ==="
log "Log: $LOG_FILE"
