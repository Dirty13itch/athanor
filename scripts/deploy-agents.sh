#!/usr/bin/env bash
# Deploy agent changes from local repo to Node 1 and rebuild
# Usage: ./scripts/deploy-agents.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="${HOME}/.ssh/athanor_mgmt"
NODE1="athanor@192.168.1.244"
REMOTE_DIR="/opt/athanor/agents"
SRC_DIR="${REPO_DIR}/services/node1/agents"

echo "=== Deploying agents to Node 1 ==="

# Sync source code
echo "Syncing source..."
rsync -avz --delete \
    --exclude='__pycache__' \
    --exclude='.pyc' \
    -e "ssh -i ${SSH_KEY}" \
    "${SRC_DIR}/src/" "${NODE1}:${REMOTE_DIR}/src/"

# Sync build files
echo "Syncing build files..."
for f in Dockerfile pyproject.toml; do
    scp -i "${SSH_KEY}" "${SRC_DIR}/${f}" "${NODE1}:${REMOTE_DIR}/${f}"
done

# Rebuild and restart
echo "Rebuilding container..."
ssh -i "${SSH_KEY}" "${NODE1}" "cd ${REMOTE_DIR} && docker compose up -d --build"

# Wait for health
echo "Waiting for agent server..."
for i in $(seq 1 30); do
    if ssh -i "${SSH_KEY}" "${NODE1}" "curl -sf http://localhost:9000/v1/models" > /dev/null 2>&1; then
        echo "Agent server healthy!"
        ssh -i "${SSH_KEY}" "${NODE1}" "curl -s http://localhost:9000/v1/models" | python3 -m json.tool
        exit 0
    fi
    sleep 2
done

echo "ERROR: Agent server did not become healthy within 60s"
ssh -i "${SSH_KEY}" "${NODE1}" "docker logs athanor-agents --tail 20"
exit 1
