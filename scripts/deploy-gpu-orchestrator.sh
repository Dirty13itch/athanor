#!/usr/bin/env bash
# Deploy GPU Orchestrator to FOUNDRY - sync, build, restart
# Usage: ./scripts/deploy-gpu-orchestrator.sh [--no-build]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FOUNDRY="${ATHANOR_FOUNDRY_SSH_HOST:-foundry}"
REMOTE_DIR="/opt/athanor/gpu-orchestrator"
SRC_DIR="${REPO_DIR}/projects/gpu-orchestrator"
BACKUP_ROOT="/opt/athanor/backups/gpu-orchestrator/$(date +%Y%m%d-%H%M%S)"
EXPECT_SCHEDULER_STATE="${GPU_ORCH_EXPECT_SCHEDULER_STATE:-0}"
EXPECT_SCHEDULER_MUTATION_SURFACE="${GPU_ORCH_EXPECT_SCHEDULER_MUTATION_SURFACE:-0}"

echo "=== Deploying Athanor GPU Orchestrator to FOUNDRY ==="

echo "[1/4] Backing up current compose root..."
ssh "${FOUNDRY}" "sudo mkdir -p '${BACKUP_ROOT}' && if [ -d '${REMOTE_DIR}' ]; then sudo cp -a '${REMOTE_DIR}' '${BACKUP_ROOT}/gpu-orchestrator'; fi"

echo "[2/4] Syncing source..."
ssh "${FOUNDRY}" "mkdir -p '${REMOTE_DIR}' && rm -rf '${REMOTE_DIR}/src' '${REMOTE_DIR}/Dockerfile' '${REMOTE_DIR}/pyproject.toml' '${REMOTE_DIR}/docker-compose.yml'"
tar \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "${SRC_DIR}" \
    -cf - \
    src \
    Dockerfile \
    pyproject.toml \
    docker-compose.yml \
    | ssh "${FOUNDRY}" "cd '${REMOTE_DIR}' && tar -xf -"

if [[ "${1:-}" == "--no-build" ]]; then
    echo "[3/4] Skipped (--no-build)"
    echo "[4/4] Code synced - container not rebuilt"
    exit 0
fi

echo "[3/4] Building and restarting..."
ssh "${FOUNDRY}" "cd '${REMOTE_DIR}' && docker compose build -q && docker compose up -d"

echo "[4/4] Verifying health..."
for i in $(seq 1 20); do
    if curl -sf "http://192.168.1.244:9200/health" > /dev/null 2>&1; then
        ZONES=$(curl -s "http://192.168.1.244:9200/zones" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"zones\"])} zones visible')")
        if [[ "${EXPECT_SCHEDULER_STATE}" == "1" ]]; then
            SCHEDULER_STATE_JSON=$(curl -sf "http://192.168.1.244:9200/scheduler/state" || true)
            if [[ -n "${SCHEDULER_STATE_JSON}" ]]; then
                if [[ "${EXPECT_SCHEDULER_MUTATION_SURFACE}" == "1" ]]; then
                    WRITE_CAPS_READY=$(printf '%s' "${SCHEDULER_STATE_JSON}" | python3 -c "import json,sys; payload=json.load(sys.stdin); caps=payload.get('write_capabilities') or {}; print('1' if all(bool(caps.get(name)) for name in ('request','preload','release')) else '0')")
                    REQUEST_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://192.168.1.244:9200/scheduler/request" || true)
                    PRELOAD_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://192.168.1.244:9200/scheduler/preload" || true)
                    RELEASE_CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://192.168.1.244:9200/scheduler/release" || true)
                    if [[ "${WRITE_CAPS_READY}" == "1" && "${REQUEST_CODE}" == "405" && "${PRELOAD_CODE}" == "405" && "${RELEASE_CODE}" == "405" ]]; then
                        echo "=== Deploy complete - ${ZONES}; scheduler mutation surface verified ==="
                        exit 0
                    fi
                else
                    echo "=== Deploy complete - ${ZONES}; scheduler/state verified ==="
                    exit 0
                fi
            fi
        else
            echo "=== Deploy complete - ${ZONES} ==="
            exit 0
        fi
    fi
    sleep 2
done

echo "ERROR: GPU Orchestrator did not become healthy within 40s"
ssh "${FOUNDRY}" "docker logs athanor-gpu-orchestrator --tail 40"
exit 1
