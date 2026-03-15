# Node SSH

SSH into Athanor infrastructure nodes and run commands.

## Connection Details

| Node | Host | User | Key | Alias |
|------|------|------|-----|-------|
| Foundry | 192.168.1.244 | athanor | ~/.ssh/athanor_mgmt | `ssh node1` |
| Workshop | 192.168.1.225 | athanor | ~/.ssh/athanor_mgmt | `ssh node2` |
| VAULT | 192.168.1.203 | root | ~/.ssh/id_ed25519 | `ssh vault` |
| DEV | local | shaun | — | localhost |

SSH config is at `~/.ssh/config` with all three remote hosts defined.

## Quick Commands

```bash
# Simple command
ssh node1 'nvidia-smi'

# Multiple commands
ssh node1 'echo "=== GPU ===" && nvidia-smi && echo "=== DOCKER ===" && docker ps'

# VAULT — if SSH hangs, use paramiko wrapper:
python3 scripts/vault-ssh.py "docker ps"
```

## All-Node Parallel Check

```bash
# GPU status across all nodes (parallel, 3s timeout)
for node in node1 node2; do
  ssh -o ConnectTimeout=3 -o BatchMode=yes $node 'echo "=== '$node' ===" && nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits' &
done
echo "=== DEV ===" && nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null
wait

# Container counts per node (parallel)
for node in node1 node2 vault; do
  ssh -o ConnectTimeout=3 -o BatchMode=yes $node 'echo "'$node': $(docker ps -q | wc -l) containers"' &
done
wait
```

## Critical Service Health Per Node

```bash
# Foundry: vLLM + agents
ssh node1 'curl -sf http://localhost:8000/health && echo " vLLM-coord OK" || echo "vLLM-coord DOWN"; curl -sf http://localhost:8006/health && echo " vLLM-coder OK" || echo "vLLM-coder DOWN"; curl -sf http://localhost:9000/health && echo " Agents OK" || echo "Agents DOWN"'

# Workshop: vLLM + Dashboard
ssh node2 'curl -sf http://localhost:8000/health && echo " vLLM OK" || echo "vLLM DOWN"; curl -sf http://localhost:3001/api/health 2>/dev/null && echo " Dashboard OK" || echo "Dashboard DOWN"'

# VAULT: LiteLLM + Redis + Qdrant
ssh vault 'curl -sf http://localhost:4000/health && echo " LiteLLM OK" || echo "LiteLLM DOWN"; redis-cli ping 2>/dev/null || echo "Redis DOWN"; curl -sf http://localhost:6333/collections && echo " Qdrant OK" || echo "Qdrant DOWN"'

# DEV: Embedding + Reranker
curl -sf http://localhost:8001/health && echo "Embedding OK" || echo "Embedding DOWN"
curl -sf http://localhost:8003/health && echo "Reranker OK" || echo "Reranker DOWN"
```

## NFS Mount Status

```bash
# Check NFS mounts on compute nodes
ssh node1 'mount | grep nfs && echo "NFS OK" || echo "No NFS mounts"'
ssh node2 'mount | grep nfs && echo "NFS OK" || echo "No NFS mounts"'

# Fix stale NFS handle (after VAULT reboot)
# ssh node1 'sudo umount -f /mnt/vault/models && sudo mount -a'
```

## Log Retrieval

```bash
# vLLM logs (recent errors)
ssh node1 'docker logs vllm-coordinator --tail 50 2>&1 | grep -i error'
ssh node1 'docker logs vllm-coder --tail 50 2>&1 | grep -i error'
ssh node2 'docker logs vllm-worker --tail 50 2>&1 | grep -i error'

# Agent server logs
ssh node1 'docker logs athanor-agents --tail 100 2>&1'

# Container crash logs
ssh vault 'docker ps -a --filter "status=exited" --format "{{.Names}}\t{{.Status}}"'
```

## Sudo

Both compute nodes have passwordless sudo for user `athanor`. VAULT is root.

## Key Notes

- VAULT uses dropbear (Unraid default) — native SSH may hang. Use paramiko script if key auth fails.
- EPYC server (Foundry) takes ~3 min to POST after reboot (224 GB ECC RAM check).
- JetKVM .165 is connected to Workshop. JetKVM .80 is connected to VAULT.
