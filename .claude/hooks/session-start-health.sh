#!/bin/bash
# SessionStart hook: Quick health checks on all Athanor nodes
# Injects status summary into session context

echo "=== Athanor Health Check ==="

# Node 1
N1=$(ssh -o ConnectTimeout=3 -o BatchMode=yes node1 'echo "UP" && nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1' 2>/dev/null)
if [ $? -eq 0 ]; then
  echo "Node 1 (core): $N1"
else
  echo "Node 1 (core): UNREACHABLE"
fi

# Node 2
N2=$(ssh -o ConnectTimeout=3 -o BatchMode=yes node2 'echo "UP" && nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null' 2>/dev/null)
if [ $? -eq 0 ]; then
  echo "Node 2 (interface): $N2"
else
  echo "Node 2 (interface): UNREACHABLE"
fi

# VAULT
V=$(ssh -o ConnectTimeout=3 -o BatchMode=yes vault 'echo "UP" && docker ps --format "{{.Names}}" 2>/dev/null | wc -l' 2>/dev/null)
if [ $? -eq 0 ]; then
  echo "VAULT: $V containers"
else
  echo "VAULT: UNREACHABLE"
fi

echo "==========================="
