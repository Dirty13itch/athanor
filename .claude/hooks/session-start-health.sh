#!/bin/bash
# SessionStart hook: quick cluster health check
# Tries the briefing API first (instant, from Redis heartbeats)
# Falls back to parallel SSH checks if briefing fails or returns empty

echo "=== Athanor Health Check ==="

# Fast path: briefing endpoint (agent server reads Redis heartbeats)
AGENT_SERVER_URL="${ATHANOR_AGENT_SERVER_URL:-http://${ATHANOR_NODE1_HOST:-192.168.1.244}:9000}"
BRIEFING=$(curl -sf --connect-timeout 2 --max-time 5 "${AGENT_SERVER_URL%/}/v1/briefing" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$BRIEFING" ]; then
  OUTPUT=$(echo "$BRIEFING" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    for s in d.get('sections', []):
        t = s.get('title', '')
        if t == 'Node Health':
            for item in s.get('items', []):
                print(f\"{item.get('node','?')}: {item.get('status','?')}, load={item.get('load','?')}, {item.get('models', '')}\")
        elif t == 'Alerts' and s.get('priority', 10) < 5:
            print(f\"ALERTS: {s.get('summary', 'unknown')}\")
        elif t == 'RSS News' and s.get('items'):
            total = sum(i.get('unread', 0) for i in s['items'])
            if total > 0:
                print(f\"RSS: {total} unread\")
except Exception:
    pass
" 2>/dev/null)

  if [ -n "$OUTPUT" ]; then
    echo "$OUTPUT"
    echo "==========================="
    exit 0
  fi
  # Fall through to SSH if briefing parsing produced no output
fi

# Slow path: parallel SSH (fallback if agent server is down or briefing is empty)
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

(
  N1=$(ssh -o ConnectTimeout=2 -o BatchMode=yes node1 'echo "UP" && nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1' 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "Foundry: $N1"
  else
    echo "Foundry: UNREACHABLE"
  fi
) > "$TMPDIR/n1" 2>&1 &

(
  N2=$(ssh -o ConnectTimeout=2 -o BatchMode=yes node2 'echo "UP" && nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null' 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "Workshop: $N2"
  else
    echo "Workshop: UNREACHABLE"
  fi
) > "$TMPDIR/n2" 2>&1 &

(
  V=$(ssh -o ConnectTimeout=2 -o BatchMode=yes vault 'echo "UP" && docker ps --format "{{.Names}}" 2>/dev/null | wc -l' 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "VAULT: $V containers"
  else
    echo "VAULT: UNREACHABLE"
  fi
) > "$TMPDIR/vault" 2>&1 &

(
  # DEV is local — always reachable
  GPU=$(nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
  CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l)
  if [ -n "$GPU" ]; then
    echo "DEV: UP, GPU: ${GPU}, ${CONTAINERS} containers"
  else
    echo "DEV: UP, ${CONTAINERS} containers"
  fi
) > "$TMPDIR/dev" 2>&1 &

# Wait with 5s timeout
TIMEOUT_PID=$$
(sleep 5 && kill -ALRM $TIMEOUT_PID 2>/dev/null) &
TIMER=$!

wait %1 %2 %3 %4 2>/dev/null
kill $TIMER 2>/dev/null

cat "$TMPDIR/n1" 2>/dev/null
cat "$TMPDIR/n2" 2>/dev/null
cat "$TMPDIR/vault" 2>/dev/null
cat "$TMPDIR/dev" 2>/dev/null

echo "==========================="
