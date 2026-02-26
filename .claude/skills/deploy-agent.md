---
name: Deploy Agent Server
description: Complete procedure for deploying the Athanor agent server to Node 1. Rsync, build, restart, verify.
disable-model-invocation: true
---

# Deploy Agent Server

Complete deployment procedure for the agent server on Node 1 (192.168.1.244:9000).

## Pre-Deploy Checks

```bash
# Verify Node 1 is reachable
ssh node1 'echo OK'

# Check current status
ssh node1 'docker ps --filter name=athanor-agents --format "{{.Names}} {{.Status}}"'
curl -sf http://192.168.1.244:9000/health | jq .
```

## Deploy Steps

### 1. Rsync Source Code
```bash
# Always rsync from repo root
rsync -avz --delete \
  projects/agents/src/ \
  node1:/opt/athanor/agents/src/
```

### 2. Rsync Dependencies (only if changed)
```bash
# Only needed when pyproject.toml or docker-compose.yml changed
rsync -avz \
  projects/agents/pyproject.toml \
  projects/agents/docker-compose.yml \
  node1:/opt/athanor/agents/
```

### 3. Build & Restart
```bash
ssh node1 'cd /opt/athanor/agents && docker compose build --no-cache && docker compose up -d'
```

### 4. Verify
```bash
# Wait for startup (agent server takes ~10s to initialize)
sleep 10

# Health check
curl -sf http://192.168.1.244:9000/health | jq .

# Check all agents loaded
curl -sf http://192.168.1.244:9000/v1/agents | jq '.agents | length'
# Expected: 8

# Quick inference test
curl -sf http://192.168.1.244:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"general-assistant","message":"ping","stream":false}' | jq .status
```

## Rollback

If deploy fails:
```bash
# Check logs
ssh node1 'docker logs --tail 100 athanor-agents 2>&1'

# Restart without rebuild (uses previous image)
ssh node1 'cd /opt/athanor/agents && docker compose up -d'
```

## Gotchas
- `build --no-cache` is required when Python deps change (Docker layer cache won't pick up pip changes)
- Agent server uses InMemorySaver — restart loses all conversation context
- LiteLLM at VAULT:4000 must be healthy for agents to function
- `<think>` blocks from Qwen3 are stripped in server before delivery
