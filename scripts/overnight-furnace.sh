#!/usr/bin/env bash
set -euo pipefail

# overnight-furnace.sh — Nightly deep work sessions via claude-squad
#
# The self-feeding furnace runs while Shaun sleeps. Launches parallel
# Claude Code sessions, each focused on a different improvement area.
# Uses the Claude Max subscription (Sonnet 80% of the time for quota).
#
# Schedule: Daily at 2:00 AM CST via cron on DEV (.189)
# Duration: Max 3 hours per session, all sessions killed by 6:00 AM
#
# Cron entry:
#   0 2 * * * /opt/athanor/scripts/overnight-furnace.sh >> /var/log/athanor-overnight.log 2>&1

LOG="/var/log/athanor-overnight.log"
REPO="/opt/athanor"
MAX_DURATION="3h"

log() { echo "$(date -Iseconds) [overnight] $1" | tee -a "$LOG"; }

log "=== Overnight Furnace Starting ==="
log "Working directory: $REPO"

cd "$REPO" || { log "FATAL: Cannot cd to $REPO"; exit 1; }

# Pull latest code
git pull --rebase origin main 2>&1 | tail -3 || true

# Session 1: Dashboard quality audit
# Reads each subpage, checks for issues, writes review docs
log "Launching session: dashboard-audit"
cs -p "claude --dangerously-skip-permissions" -y &
DASHBOARD_PID=$!

# Wait for sessions to initialize
sleep 10

# Session 2: Agent server improvements
# Reviews Python code, adds type hints, fixes error handling
log "Launching session: agent-improvements"
cs -p "claude --dangerously-skip-permissions" -y &
AGENT_PID=$!

sleep 10

# Session 3: Infrastructure drift check
# Compares Ansible roles against live state, fixes drift
log "Launching session: infra-drift"
cs -p "claude --dangerously-skip-permissions" -y &
INFRA_PID=$!

log "All 3 sessions launched. PIDs: $DASHBOARD_PID $AGENT_PID $INFRA_PID"
log "Will kill at 6:00 AM (max $MAX_DURATION)"

# Wait for max duration or 6:00 AM, whichever comes first
KILL_TIME=$(date -d "today 06:00" +%s 2>/dev/null || date -d "tomorrow 06:00" +%s)
NOW=$(date +%s)
SLEEP_SECS=$((KILL_TIME - NOW))

if [ "$SLEEP_SECS" -gt 0 ] && [ "$SLEEP_SECS" -lt 14400 ]; then
    log "Sleeping $SLEEP_SECS seconds until 6:00 AM"
    sleep "$SLEEP_SECS"
fi

# Kill all sessions
log "Killing overnight sessions"
kill "$DASHBOARD_PID" "$AGENT_PID" "$INFRA_PID" 2>/dev/null || true
sleep 5
kill -9 "$DASHBOARD_PID" "$AGENT_PID" "$INFRA_PID" 2>/dev/null || true

# Push any commits made by overnight sessions
log "Pushing overnight commits"
git push origin main 2>&1 | tail -3 || true

log "=== Overnight Furnace Complete ==="
