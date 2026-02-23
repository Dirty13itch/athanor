#!/bin/bash
# PreCompact hook: Save critical session state before context compaction
# Writes current working state to a temp file that can be re-read after compaction

STATE_FILE="/tmp/athanor-session-state.md"

cat > "$STATE_FILE" << 'EOF'
# Athanor Session State (Pre-Compaction Snapshot)

## Key Context
- SSH: node1 (192.168.1.244), node2 (192.168.1.225), vault (192.168.1.203)
- SSH config at ~/.ssh/config with aliases
- All nodes have passwordless SSH via athanor_mgmt and id_ed25519 keys
- VAULT uses dropbear; fallback: python scripts/vault-ssh.py

## Current Infrastructure State
- Node 1: Ubuntu 24.04, 4x RTX 5070 Ti + RTX 4090 (88 GB VRAM), vLLM (Qwen3-32B-AWQ TP=4), Agent Server ✅
- Node 2: Ubuntu 24.04, RTX 5090 + RTX 5060 Ti (48 GB VRAM), vLLM (Qwen3-14B-AWQ), ComfyUI, Dashboard, Open WebUI ✅
- VAULT: Unraid, Prometheus, Grafana, Plex, *arr stack, Stash, Home Assistant ✅
- NFS mounted on both nodes at /mnt/vault/{models,data,appdata} ✅
- Ansible IaC tree covers all services: ansible-playbook playbooks/site.yml

## Read These Files for Full Context
- CLAUDE.md
- docs/BUILD-ROADMAP.md
- docs/VISION.md
- .claude/skills/ (all files)
EOF

echo "Session state saved to $STATE_FILE"
