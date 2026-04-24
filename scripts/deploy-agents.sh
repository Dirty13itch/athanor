#!/usr/bin/env bash
# Deploy agent server to FOUNDRY - sync, build, restart
# Usage: ./scripts/deploy-agents.sh [--no-build] [--project-only]

# Source cluster config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FOUNDRY="${ATHANOR_FOUNDRY_SSH_HOST:-foundry}"
REMOTE_DIR="/opt/athanor/agents"
REMOTE_WORKSPACE_ROOT="/opt/athanor"
SRC_DIR="${REPO_DIR}/projects/agents"
AGENT_URL="${ATHANOR_AGENT_SERVER_URL:-${AGENT_SERVER_URL}}"
BACKUP_ROOT="/opt/athanor/backups/agents/$(date +%Y%m%d-%H%M%S)"
NO_BUILD=0
PROJECT_ONLY=0
SSH_OPTS=(
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o ServerAliveInterval=15
    -o ServerAliveCountMax=2
)
REMOTE_STEP_TIMEOUT="10m"
REMOTE_BUILD_TIMEOUT="30m"
REMOTE_LOG_TIMEOUT="2m"
LOCAL_SYNC_ARCHIVE="$(mktemp "${TMPDIR:-/tmp}/athanor-agents-sync.XXXXXX.tar")"
DEVSTACK_PROOF_ROOT_RELATIVE="$(python3 "${REPO_DIR}/scripts/proof_workspace_contract.py" devstack-root)"

mapfile -t PROOF_WORKSPACE_SYNC_PATHS < <(python3 "${REPO_DIR}/scripts/proof_workspace_contract.py" repo-sync-paths)
mapfile -t DEVSTACK_PROOF_SYNC_PATHS < <(python3 "${REPO_DIR}/scripts/proof_workspace_contract.py" devstack-sync-paths)

cleanup() {
    rm -f "${LOCAL_SYNC_ARCHIVE}"
}

trap cleanup EXIT

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build)
            NO_BUILD=1
            shift
            ;;
        --project-only)
            PROJECT_ONLY=1
            shift
            ;;
        *)
            echo "Usage: ./scripts/deploy-agents.sh [--no-build] [--project-only]"
            exit 2
            ;;
    esac
done

echo "=== Deploying Athanor Agent Server to FOUNDRY ==="

# Back up current compose root
echo "[1/4] Backing up current compose root..."
ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"sudo mkdir -p '${BACKUP_ROOT}' && if [ -d '${REMOTE_DIR}' ]; then sudo cp -a '${REMOTE_DIR}' '${BACKUP_ROOT}/agents'; fi\""

# Sync source code and build-context inputs
echo "[2/4] Syncing source..."
ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"mkdir -p '${REMOTE_DIR}' && rm -rf '${REMOTE_DIR}/src' '${REMOTE_DIR}/config' '${REMOTE_DIR}/Dockerfile' '${REMOTE_DIR}/pyproject.toml' '${REMOTE_DIR}/docker-compose.yml'\""
tar \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "${SRC_DIR}" \
    -cf "${LOCAL_SYNC_ARCHIVE}" \
    src \
    config \
    Dockerfile \
    pyproject.toml \
    docker-compose.yml
scp "${SSH_OPTS[@]}" "${LOCAL_SYNC_ARCHIVE}" "${FOUNDRY}:/tmp/athanor-agents-sync.tar"
ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"cd '${REMOTE_DIR}' && tar -xf /tmp/athanor-agents-sync.tar && rm -f /tmp/athanor-agents-sync.tar\""

echo "[2b/4] Syncing shared control-plane config and truth inventory..."
if [[ "${PROJECT_ONLY}" == "1" ]]; then
    echo "[2b/4] Skipped shared control-plane sync (--project-only)"
else
    ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"sudo mkdir -p '${REMOTE_WORKSPACE_ROOT}/config' '${REMOTE_WORKSPACE_ROOT}/reports'\""
    tar \
        -C "${REPO_DIR}/config" \
        -cf - \
        automation-backbone \
        | ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"rm -rf ~/automation-backbone.sync && mkdir -p ~/automation-backbone.sync && cd ~ && tar -xf - && sudo rm -rf '${REMOTE_WORKSPACE_ROOT}/config/automation-backbone' && sudo cp -a ~/automation-backbone '${REMOTE_WORKSPACE_ROOT}/config/automation-backbone' && rm -rf ~/automation-backbone\""

    if [[ -d "${REPO_DIR}/reports/truth-inventory" ]]; then
        tar \
            -C "${REPO_DIR}/reports" \
            -cf - \
            truth-inventory \
            | ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"rm -rf ~/truth-inventory.sync && mkdir -p ~/truth-inventory.sync && cd ~ && tar -xf - && sudo rm -rf '${REMOTE_WORKSPACE_ROOT}/reports/truth-inventory' && sudo cp -a ~/truth-inventory '${REMOTE_WORKSPACE_ROOT}/reports/truth-inventory' && rm -rf ~/truth-inventory\""
    fi
fi

echo "[2c/4] Syncing governed proof scripts..."
tar \
    -C "${REPO_DIR}" \
    -cf - \
    scripts \
    | ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc \"cd '${REMOTE_WORKSPACE_ROOT}' && tar -xf -\""

sync_workspace_item() {
    local source_root="$1"
    local relative_path="$2"
    local remote_root="$3"
    local remote_path="${remote_root}/${relative_path}"
    local remote_parent
    remote_parent="$(dirname "${remote_path}")"

    tar \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='node_modules' \
        --exclude='.next' \
        --exclude='.next-playwright-*' \
        --exclude='dist' \
        --exclude='build' \
        -C "${source_root}" \
        -cf - "${relative_path}" \
        | ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_STEP_TIMEOUT} bash -lc 'set -euo pipefail; tmpdir=\$(mktemp -d ~/athanor-proof-sync.XXXXXX); cd \"\$tmpdir\"; tar -xf -; sudo rm -rf \"${remote_path}\"; sudo mkdir -p \"${remote_parent}\"; sudo cp -a \"\$tmpdir/${relative_path}\" \"${remote_path}\"; rm -rf \"\$tmpdir\"'"
}

echo "[2d/4] Syncing proof workspace surface..."
if [[ "${PROJECT_ONLY}" == "1" ]]; then
    echo "[2d/4] Skipped proof workspace sync (--project-only)"
else
    for relative_path in "${PROOF_WORKSPACE_SYNC_PATHS[@]}"; do
        sync_workspace_item "${REPO_DIR}" "${relative_path}" "${REMOTE_WORKSPACE_ROOT}"
    done

    if [[ -d "/mnt/c/athanor-devstack" ]]; then
        for relative_path in "${DEVSTACK_PROOF_SYNC_PATHS[@]}"; do
            sync_workspace_item "/mnt/c/athanor-devstack" "${relative_path}" "${REMOTE_WORKSPACE_ROOT}/${DEVSTACK_PROOF_ROOT_RELATIVE}"
        done
    else
        echo "[2d/4] WARNING: /mnt/c/athanor-devstack missing; devstack proof mirror not updated"
    fi
fi

if [[ "${NO_BUILD}" == "1" ]]; then
    echo "[3/4] Skipped (--no-build)"
    echo "[4/4] Code synced - container not rebuilt"
    exit 0
fi

# Rebuild and restart
echo "[3/4] Building and restarting..."
ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_BUILD_TIMEOUT} bash -lc \"cd ${REMOTE_DIR} && docker compose build -q && docker compose up -d\""

# Wait for health
echo "[4/4] Verifying health..."
for i in $(seq 1 20); do
    if curl -sf --max-time 10 "${AGENT_URL%/}/v1/agents" > /dev/null 2>&1; then
        AGENTS=$(curl -sS --max-time 10 "${AGENT_URL%/}/v1/agents" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d.get(\"agents\", []))} agents healthy')")
        echo "=== Deploy complete - ${AGENTS} ==="
        exit 0
    fi
    sleep 2
done

echo "ERROR: Agent server did not become healthy within 40s"
ssh "${SSH_OPTS[@]}" "${FOUNDRY}" "timeout --preserve-status --kill-after=30s ${REMOTE_LOG_TIMEOUT} bash -lc \"docker logs athanor-agents --tail 20\""
exit 1
