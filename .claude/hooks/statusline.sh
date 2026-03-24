#!/bin/bash
# Status line script: Shows node health from Redis heartbeats
# Called by Claude Code status line configuration

# Quick Redis check for heartbeats (with 2s timeout)
REDIS_URL="${ATHANOR_REDIS_URL:-${REDIS_URL:-}}"
REDIS_HOST="${ATHANOR_REDIS_HOST:-${ATHANOR_VAULT_HOST:-192.168.1.203}}"
REDIS_PORT="${ATHANOR_REDIS_PORT:-${REDIS_PORT:-6379}}"
REDIS_PASS="${ATHANOR_REDIS_PASSWORD:-${REDIS_PASSWORD:-}}"

redis_ttl() {
  local key="$1"
  local cmd=(redis-cli --no-auth-warning)

  if [ -n "$REDIS_URL" ]; then
    cmd+=(-u "$REDIS_URL")
  else
    cmd+=(-h "$REDIS_HOST" -p "$REDIS_PORT")
    if [ -n "$REDIS_PASS" ]; then
      cmd+=(-a "$REDIS_PASS")
    fi
  fi

  "${cmd[@]}" TTL "$key" 2>/dev/null || echo "-2"
}

nodes=""
for node in foundry workshop dev; do
  ttl=$(redis_ttl "athanor:heartbeat:$node")
  if [ "$ttl" -gt 0 ] 2>/dev/null; then
    nodes="$nodes ${node:0:1}:UP"
  else
    nodes="$nodes ${node:0:1}:--"
  fi
done

# Git branch
branch=$(git branch --show-current 2>/dev/null)
dirty=$(git status --short 2>/dev/null | wc -l)

echo "Nodes:$nodes | $branch${dirty:+ ($dirty dirty)}"
