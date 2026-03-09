#!/bin/bash
# SessionStart hook: Quick cluster health check
# Tries briefing API first (instant, from Redis heartbeats)
# Falls back to parallel SSH checks if agent server is down

echo "=== Athanor Health Check ==="

# Fast path: briefing endpoint (agent server → Redis heartbeats)
BRIEFING=$(curl -sf --connect-timeout 2 --max-time 5 http://192.168.1.244:9000/v1/briefing 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$BRIEFING" ]; then
  echo "$BRIEFING" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for s in d.get('sections', []):
    t = s['title']
    if t == 'Node Health':
        for item in s['items']:
            print(f\"{item['node']}: {item['status']}, load={item['load']}, {item.get('models','')}\")
    elif t == 'Alerts' and s['priority'] < 5:
        print(f\"ALERTS: {s['summary']}\")
    elif t == 'RSS News' and s['items']:
        total = sum(i.get('unread',0) for i in s['items'])
        print(f\"RSS: {total} unread\")
" 2>/dev/null
  echo "==========================="
  exit 0
fi

# Slow path: parallel SSH (fallback if agent server is down)
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

# Wait with 5s timeout
TIMEOUT_PID=$$
(sleep 5 && kill -ALRM $TIMEOUT_PID 2>/dev/null) &
TIMER=$!

wait %1 %2 %3 2>/dev/null
kill $TIMER 2>/dev/null

cat "$TMPDIR/n1" 2>/dev/null
cat "$TMPDIR/n2" 2>/dev/null
cat "$TMPDIR/vault" 2>/dev/null

echo "==========================="
