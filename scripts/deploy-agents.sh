#!/usr/bin/env bash
# Deploy agent server to FOUNDRY - sync, build, restart
# Usage: ./scripts/deploy-agents.sh [--no-build]

# Source cluster config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FOUNDRY="${ATHANOR_FOUNDRY_SSH_HOST:-foundry}"
REMOTE_DIR="/opt/athanor/agents"
SRC_DIR="${REPO_DIR}/projects/agents"
AGENT_URL="${ATHANOR_AGENT_SERVER_URL:-${AGENT_SERVER_URL}}"
BACKUP_ROOT="/opt/athanor/backups/agents/$(date +%Y%m%d-%H%M%S)"

echo "=== Deploying Athanor Agent Server to FOUNDRY ==="

# Back up current compose root
echo "[1/4] Backing up current compose root..."
ssh "${FOUNDRY}" "sudo mkdir -p '${BACKUP_ROOT}' && if [ -d '${REMOTE_DIR}' ]; then sudo cp -a '${REMOTE_DIR}' '${BACKUP_ROOT}/agents'; fi"

# Sync source code and build-context inputs
echo "[2/4] Syncing source..."
ssh "${FOUNDRY}" "mkdir -p '${REMOTE_DIR}' && rm -rf '${REMOTE_DIR}/src' '${REMOTE_DIR}/config' '${REMOTE_DIR}/Dockerfile' '${REMOTE_DIR}/pyproject.toml' '${REMOTE_DIR}/docker-compose.yml'"
tar \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "${SRC_DIR}" \
    -cf - \
    src \
    config \
    Dockerfile \
    pyproject.toml \
    docker-compose.yml \
    | ssh "${FOUNDRY}" "cd '${REMOTE_DIR}' && tar -xf -"

if [[ "${1:-}" == "--no-build" ]]; then
    echo "[3/4] Skipped (--no-build)"
    echo "[4/4] Code synced - container not rebuilt"
    exit 0
fi

# Rebuild and restart
echo "[3/4] Building and restarting..."
ssh "${FOUNDRY}" "cd ${REMOTE_DIR} && docker compose build -q && docker compose up -d"

# Wait for health
echo "[4/4] Verifying health..."
for i in $(seq 1 20); do
    if curl -sf "${AGENT_URL%/}/health" > /dev/null 2>&1; then
        AGENTS=$(curl -s "${AGENT_URL%/}/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"agents\"])} agents healthy')")
        echo "=== Deploy complete - ${AGENTS} ==="
        exit 0
    fi
    sleep 2
done

echo "ERROR: Agent server did not become healthy within 40s"
ssh "${FOUNDRY}" "docker logs athanor-agents --tail 20"
exit 1
