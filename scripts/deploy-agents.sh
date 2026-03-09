#!/usr/bin/env bash
# Deploy agent server to FOUNDRY — sync, build, restart
# Usage: ./scripts/deploy-agents.sh [--no-build]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FOUNDRY="foundry"
REMOTE_DIR="/opt/athanor/agents"
SRC_DIR="${REPO_DIR}/projects/agents"

echo "=== Deploying Athanor Agent Server to FOUNDRY ==="

# Sync source code
echo "[1/3] Syncing source..."
rsync -avz --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "${SRC_DIR}/src/" "${FOUNDRY}:${REMOTE_DIR}/src/"

# Sync build files
rsync -avz \
    "${SRC_DIR}/Dockerfile" \
    "${SRC_DIR}/pyproject.toml" \
    "${SRC_DIR}/docker-compose.yml" \
    "${FOUNDRY}:${REMOTE_DIR}/"

if [[ "${1:-}" == "--no-build" ]]; then
    echo "[2/3] Skipped (--no-build)"
    echo "[3/3] Code synced — container not rebuilt"
    exit 0
fi

# Rebuild and restart
echo "[2/3] Building and restarting..."
ssh "${FOUNDRY}" "cd ${REMOTE_DIR} && docker compose build -q && docker compose up -d"

# Wait for health
echo "[3/3] Verifying health..."
for i in $(seq 1 20); do
    if curl -sf http://192.168.1.244:9000/health > /dev/null 2>&1; then
        AGENTS=$(curl -s http://192.168.1.244:9000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"agents\"])} agents healthy')")
        echo "=== Deploy complete — ${AGENTS} ==="
        exit 0
    fi
    sleep 2
done

echo "ERROR: Agent server did not become healthy within 40s"
ssh "${FOUNDRY}" "docker logs athanor-agents --tail 20"
exit 1
