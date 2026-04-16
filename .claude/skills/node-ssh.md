# Node SSH

SSH into Athanor infrastructure nodes and run commands. Treat this as governed bootstrap guidance only, not the source of runtime authority. Verify current node/runtime posture in `python scripts/session_restart_brief.py --refresh`, `docs/operations/RUNTIME-OWNERSHIP-REPORT.md`, and the current topology/runtime reports before assuming any host, alias, or service state below is still live.

## Connection Details

| Node | Host | User | Key | Alias |
|------|------|------|-----|-------|
| FOUNDRY (core) | 192.168.1.244 | athanor | ~/.ssh/athanor_mgmt | `ssh foundry` |
| WORKSHOP (interface) | 192.168.1.225 | athanor | ~/.ssh/athanor_mgmt | `ssh workshop` |
| VAULT (Unraid) | 192.168.1.203 | root | ~/.ssh/id_ed25519 | `ssh vault` |

SSH config is at `~/.ssh/config` with the governed `foundry`, `workshop`, and `vault` aliases defined. Prefer those aliases only after the restart brief and runtime ownership surfaces confirm the host mapping, and use raw-IP fallback as recovery-only behavior.

## Usage

```bash
# Simple command
ssh foundry 'nvidia-smi'

# Multiple commands
ssh foundry 'echo "=== GPU ===" && nvidia-smi && echo "=== DOCKER ===" && docker ps'

# VAULT (dropbear) — if SSH key not loaded, use paramiko:
python scripts/vault-ssh.py "docker ps"
```

## Common Validation Commands

```bash
# GPU health
ssh foundry 'nvidia-smi'
ssh workshop 'nvidia-smi'

# Docker containers
ssh foundry 'docker ps -a'
ssh workshop 'docker ps -a'
ssh vault 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# System resources
ssh foundry 'free -h && df -h /'
ssh workshop 'free -h && df -h /'

# GPU topology
ssh foundry 'nvidia-smi topo -m'
ssh workshop 'nvidia-smi topo -m'

# NFS mounts
ssh foundry 'mount | grep nfs'
ssh workshop 'mount | grep nfs'

# Service health
ssh foundry 'curl -s http://localhost:8000/health 2>/dev/null || echo "vLLM not running"'
ssh workshop 'curl -s http://localhost:8188/api/system_stats 2>/dev/null || echo "ComfyUI not running"'
```

## Sudo

Both nodes have passwordless sudo for user `athanor`. VAULT is root.

## Key Notes

- VAULT uses dropbear (Unraid default) — native SSH may hang on password prompt. Use paramiko script if key auth fails.
- FOUNDRY takes ~3 minutes to POST after reboot (224 GB ECC RAM check).
- JetKVM .165 is connected to WORKSHOP (not FOUNDRY despite old bookmark labels).
- JetKVM .80 is connected to VAULT.
