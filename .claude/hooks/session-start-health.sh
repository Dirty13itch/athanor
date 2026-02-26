#!/bin/bash
# SessionStart hook: Parallel health checks on all Athanor nodes
# Runs all SSH checks concurrently to avoid blocking (was 9s+ sequential)

echo "=== Athanor Health Check ==="

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Run all checks in parallel
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

# Wait for all with 5s overall timeout
TIMEOUT_PID=$$
(sleep 5 && kill -ALRM $TIMEOUT_PID 2>/dev/null) &
TIMER=$!

wait %1 %2 %3 2>/dev/null
kill $TIMER 2>/dev/null

# Print results
cat "$TMPDIR/n1" 2>/dev/null
cat "$TMPDIR/n2" 2>/dev/null
cat "$TMPDIR/vault" 2>/dev/null

echo "==========================="
