# Node SSH

SSH into Athanor infrastructure nodes and run commands.

## Connection Details

| Node | Host | User | Key | Alias |
|------|------|------|-----|-------|
| Node 1 (core) | 192.168.1.244 | athanor | ~/.ssh/athanor_mgmt | `ssh node1` |
| Node 2 (interface) | 192.168.1.225 | athanor | ~/.ssh/athanor_mgmt | `ssh node2` |
| VAULT (Unraid) | 192.168.1.203 | root | ~/.ssh/id_ed25519 | `ssh vault` |

SSH config is at `~/.ssh/config` with all three hosts defined.

## Usage

```bash
# Simple command
ssh node1 'nvidia-smi'

# Multiple commands
ssh node1 'echo "=== GPU ===" && nvidia-smi && echo "=== DOCKER ===" && docker ps'

# VAULT (dropbear) — if SSH key not loaded, use paramiko:
python scripts/vault-ssh.py "docker ps"
```

## Common Validation Commands

```bash
# GPU health
ssh node1 'nvidia-smi'
ssh node2 'nvidia-smi'

# Docker containers
ssh node1 'docker ps -a'
ssh node2 'docker ps -a'
ssh vault 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# System resources
ssh node1 'free -h && df -h /'
ssh node2 'free -h && df -h /'

# GPU topology
ssh node1 'nvidia-smi topo -m'
ssh node2 'nvidia-smi topo -m'

# NFS mounts
ssh node1 'mount | grep nfs'
ssh node2 'mount | grep nfs'

# Service health
ssh node1 'curl -s http://localhost:8000/health 2>/dev/null || echo "vLLM not running"'
ssh node2 'curl -s http://localhost:8188/api/system_stats 2>/dev/null || echo "ComfyUI not running"'
```

## Sudo

Both nodes have passwordless sudo for user `athanor`. VAULT is root.

## Key Notes

- VAULT uses dropbear (Unraid default) — native SSH may hang on password prompt. Use paramiko script if key auth fails.
- EPYC server (Node 1) takes ~3 minutes to POST after reboot (224 GB ECC RAM check).
- JetKVM .165 is connected to Node 2 (not Node 1 despite bookmark labels).
- JetKVM .80 is connected to VAULT.
