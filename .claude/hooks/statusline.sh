#!/bin/bash
# Status line script: Shows node health from Redis heartbeats
# Called by Claude Code status line configuration

# Quick Redis check for heartbeats (with 2s timeout)
REDIS_HOST="192.168.1.203"
REDIS_PASS="Jv1Vg9HAML2jHGWjFnTCcIsqSzqZfIQz"

nodes=""
for node in foundry workshop dev; do
  ttl=$(redis-cli -h "$REDIS_HOST" -a "$REDIS_PASS" --no-auth-warning TTL "athanor:heartbeat:$node" 2>/dev/null)
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
