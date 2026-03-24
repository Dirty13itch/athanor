---
name: Network Diagnostics
description: Network troubleshooting across Athanor nodes — MTU, latency, bandwidth, DNS, NFS, connectivity.
---

# Network Diagnostics

## Node Connectivity Matrix

| From → To | IP | Port | Protocol | Service |
|-----------|----|----|----------|---------|
| DEV → Node 1 | .244 | 22/9000/9200/8001/8200 | SSH/HTTP | SSH, Agents, GPU Orch, Embedding, TTS |
| DEV → Node 2 | .225 | 22/3001/3002/3100 | SSH/HTTP/WS | SSH, Dashboard, EoBQ, ws-pty |
| DEV → VAULT | .203 | 22/4000/6379/9090/3000 | SSH/HTTP | SSH, LiteLLM, Redis, Prometheus, Grafana |
| Node 1 → VAULT | .203 | 2049/4000/6333/7687 | NFS/HTTP | NFS, LiteLLM, Qdrant, Neo4j |
| Node 2 → VAULT | .203 | 2049 | NFS | NFS models |
| Node 2 → Node 1 | .244 | 22/9000 | SSH/HTTP | SSH, Agent API |

## Quick Checks

```bash
# Ping all nodes (2 packets each)
for host in 192.168.1.244 192.168.1.225 192.168.1.203; do
  echo -n "$host: "; ping -c 2 -W 1 "$host" 2>/dev/null | tail -1
done

# MTU verification (should pass with 8972 for jumbo frames)
ping -c 1 -M do -s 8972 192.168.1.244  # Node 1
ping -c 1 -M do -s 8972 192.168.1.225  # Node 2

# NFS mount health
ssh node1 'stat /mnt/vault/models/ > /dev/null 2>&1 && echo "NFS OK" || echo "NFS STALE"'

# 10GbE link speed
ssh node1 'ethtool eno1 2>/dev/null | grep Speed'
ssh node2 'ethtool eno1 2>/dev/null | grep Speed'
```

## NFS Stale Handle Recovery
```bash
# On the affected node:
sudo umount -f /mnt/vault/models
sudo umount -f /mnt/vault/data
sudo mount -a
# Verify:
ls /mnt/vault/models/ | head -3
```

## Bandwidth Test
```bash
# Install iperf3 if needed, run server on one node, client on another
ssh node1 'iperf3 -s -D'  # Start server
ssh node2 'iperf3 -c 192.168.1.244 -t 5'  # Run client
ssh node1 'pkill iperf3'  # Cleanup
# Expect: ~9.4 Gbps on 10GbE with jumbo frames
```

## Known Issues
- DEV ethernet at 100 Mbps (bad cable, should be 1 Gbps)
- VAULT SSH hangs with native ssh — use `python3 scripts/vault-ssh.py`
- MTU 9000 on Node 1 was set directly (not Ansible-managed yet)
