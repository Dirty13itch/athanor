#!/usr/bin/env bash
# Deploy dashboard to DEV through the active /opt compose lane.
# Usage: ./scripts/deploy-dashboard.sh [--no-build]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEV_HOST="${ATHANOR_DEV_SSH_HOST:-dev}"
SRC_DASHBOARD_DIR="${REPO_DIR}/projects/dashboard"
REMOTE_ROOT="/opt/athanor"
REMOTE_DASHBOARD_DIR="${REMOTE_ROOT}/dashboard"
BACKUP_ROOT="${REMOTE_ROOT}/backups/dashboard/$(date +%Y%m%d-%H%M%S)"
SESSION_URL="${COMMAND_CENTER_URL%/}/api/operator/session"
RUNTIME_URL="${DASHBOARD_URL%/}/api/operator/session"

echo "=== Deploying Athanor Dashboard to DEV ==="

echo "[1/4] Backing up current compose roots..."
ssh "${DEV_HOST}" "sudo mkdir -p '${BACKUP_ROOT}' && \
  if [ -d '${REMOTE_DASHBOARD_DIR}' ]; then sudo cp -a '${REMOTE_DASHBOARD_DIR}' '${BACKUP_ROOT}/dashboard'; fi"

echo "[2/4] Syncing dashboard sources..."
ssh "${DEV_HOST}" "mkdir -p '${REMOTE_DASHBOARD_DIR}' && find '${REMOTE_DASHBOARD_DIR}' -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} +"
tar \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='coverage' \
  --exclude='playwright-report' \
  --exclude='test-results' \
  --exclude='.next-playwright*' \
  --exclude='.fixture-debug*' \
  --exclude='.playwright-*' \
  --exclude='.tmp-playwright-*' \
  --exclude='output' \
  -C "${SRC_DASHBOARD_DIR}" \
  -cf - \
  . \
  | ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && tar -xf -"

if [[ "${1:-}" == "--no-build" ]]; then
  echo "[3/4] Skipped build/restart (--no-build)"
  echo "[4/4] Sources synced only"
  exit 0
fi

echo "[3/4] Rebuilding and restarting dashboard lane..."
ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && docker compose build dashboard && docker compose up -d dashboard"

echo "[4/4] Verifying dashboard health..."
for _ in $(seq 1 30); do
  runtime_code="$(curl -s -o /dev/null -w '%{http_code}' "${RUNTIME_URL}" || true)"
  session_code="$(curl -sk -o /dev/null -w '%{http_code}' "${SESSION_URL}" || true)"
  if [[ "${runtime_code}" == "200" && "${session_code}" == "200" ]]; then
    echo "=== Dashboard deploy complete - runtime ${runtime_code}, front door ${session_code} ==="
    exit 0
  fi
  sleep 2
done

echo "ERROR: dashboard did not become healthy within 60s"
ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && docker compose ps dashboard && docker logs athanor-dashboard --tail 50"
exit 1
