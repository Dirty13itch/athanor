#!/usr/bin/env bash
# Deploy dashboard to DEV through the active /opt compose lane.
# Usage: ./scripts/deploy-dashboard.sh [--no-build]
# On DESK PowerShell, prefer ./scripts/deploy-dashboard.ps1 to bypass the WindowsApps bash shim.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cluster_config.sh"

set -euo pipefail

REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEV_HOST="${ATHANOR_DEV_SSH_HOST:-dev}"
SRC_DASHBOARD_DIR="${REPO_DIR}/projects/dashboard"
REMOTE_ROOT="/opt/athanor"
REMOTE_DASHBOARD_DIR="${REMOTE_ROOT}/dashboard"
REMOTE_REPORTS_DIR="${REMOTE_ROOT}/reports"
REMOTE_TRUTH_INVENTORY_DIR="${REMOTE_REPORTS_DIR}/truth-inventory"
BACKUP_ROOT="${REMOTE_ROOT}/backups/dashboard/$(date +%Y%m%d-%H%M%S)"
SESSION_URL="${COMMAND_CENTER_URL%/}/api/operator/session"
RUNTIME_URL="${DASHBOARD_URL%/}/api/operator/session"
ROOT_URL="${COMMAND_CENTER_URL%/}/"
RUNTIME_BASE="${DASHBOARD_URL%/}"
READY_TIMEOUT_SECONDS="${DASHBOARD_READY_TIMEOUT_SECONDS:-120}"
READY_API_PROBE_TIMEOUT_SECONDS="${DASHBOARD_READY_API_PROBE_TIMEOUT_SECONDS:-8}"
READY_FRONTDOOR_PROBE_TIMEOUT_SECONDS="${DASHBOARD_READY_FRONTDOOR_PROBE_TIMEOUT_SECONDS:-15}"
READY_CONNECT_TIMEOUT_SECONDS="${DASHBOARD_READY_CONNECT_TIMEOUT_SECONDS:-3}"

probe_http_code() {
  local url="$1"
  local max_time_seconds="${2:-${READY_API_PROBE_TIMEOUT_SECONDS}}"
  local -a curl_args=(
    -sS
    --connect-timeout "${READY_CONNECT_TIMEOUT_SECONDS}"
    --max-time "${max_time_seconds}"
    -o /dev/null
    -w '%{http_code}'
  )
  if [[ "${url}" == https://* ]]; then
    curl_args+=( -k )
  fi

  local code
  code="$(curl "${curl_args[@]}" "${url}" 2>/dev/null || echo "000")"
  code="${code: -3}"
  printf '%s' "${code}"
}

warmup_url() {
  local url="$1"
  local max_time_seconds="${2:-${READY_API_PROBE_TIMEOUT_SECONDS}}"
  local -a curl_args=(
    -sS
    --connect-timeout "${READY_CONNECT_TIMEOUT_SECONDS}"
    --max-time "${max_time_seconds}"
    -o /dev/null
  )
  if [[ "${url}" == https://* ]]; then
    curl_args+=( -k )
  fi

  curl "${curl_args[@]}" "${url}" >/dev/null 2>&1 || true
}

verify_dashboard_health() {
  local -a labels=(
    "runtime session"
    "runtime summary"
    "runtime governance"
    "runtime master-atlas"
    "front door root"
    "front door session"
  )
  local -a urls=(
    "${RUNTIME_URL}"
    "${RUNTIME_BASE}/api/operator/summary"
    "${RUNTIME_BASE}/api/operator/governance"
    "${RUNTIME_BASE}/api/master-atlas"
    "${ROOT_URL}"
    "${SESSION_URL}"
  )
  local -a timeouts=(
    "${READY_API_PROBE_TIMEOUT_SECONDS}"
    "${READY_API_PROBE_TIMEOUT_SECONDS}"
    "${READY_API_PROBE_TIMEOUT_SECONDS}"
    "${READY_API_PROBE_TIMEOUT_SECONDS}"
    "${READY_FRONTDOOR_PROBE_TIMEOUT_SECONDS}"
    "${READY_FRONTDOOR_PROBE_TIMEOUT_SECONDS}"
  )

  local ready=1
  local line
  for i in "${!labels[@]}"; do
    local code
    code="$(probe_http_code "${urls[$i]}" "${timeouts[$i]}")"
    line="${labels[$i]}=${code}"
    if [[ "${code}" != "200" ]]; then
      ready=0
    fi
    printf '%s\n' "${line}"
  done

  if [[ "${ready}" -eq 1 ]]; then
    return 0
  fi
  return 1
}

wait_for_dashboard_health() {
  local attempt
  for attempt in $(seq 1 $((READY_TIMEOUT_SECONDS / 2))); do
    warmup_url "${ROOT_URL}" "${READY_FRONTDOOR_PROBE_TIMEOUT_SECONDS}"
    warmup_url "${RUNTIME_URL}" "${READY_API_PROBE_TIMEOUT_SECONDS}"
    warmup_url "${RUNTIME_BASE}/api/operator/governance" "${READY_API_PROBE_TIMEOUT_SECONDS}"
    warmup_url "${RUNTIME_BASE}/api/operator/summary" "${READY_API_PROBE_TIMEOUT_SECONDS}"
    warmup_url "${RUNTIME_BASE}/api/master-atlas" "${READY_API_PROBE_TIMEOUT_SECONDS}"

    readiness_report="$(verify_dashboard_health)"
    if printf '%s\n' "${readiness_report}" | awk -F= '$2 != "200" { exit 1 }'; then
      printf '%s\n' "${readiness_report}"
      return 0
    fi
    printf '[pending] %s\n' "${readiness_report}"
    sleep 2
  done

  return 1
}

echo "=== Deploying Athanor Dashboard to DEV ==="

if [[ "${1:-}" == "--check-ready" ]]; then
  echo "[0/1] Checking dashboard readiness only..."
  if wait_for_dashboard_health; then
    echo "=== Dashboard readiness check passed ==="
    exit 0
  fi
  echo "ERROR: dashboard readiness check failed"
  ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && docker compose ps dashboard && docker logs athanor-dashboard --tail 50"
  exit 1
fi

echo "[1/4] Backing up current compose roots..."
ssh "${DEV_HOST}" "sudo mkdir -p '${BACKUP_ROOT}' && \
  if [ -d '${REMOTE_DASHBOARD_DIR}' ]; then sudo cp -a '${REMOTE_DASHBOARD_DIR}' '${BACKUP_ROOT}/dashboard'; fi && \
  if [ -d '${REMOTE_TRUTH_INVENTORY_DIR}' ]; then sudo cp -a '${REMOTE_TRUTH_INVENTORY_DIR}' '${BACKUP_ROOT}/truth-inventory'; fi"

echo "[2/4] Syncing dashboard sources..."
ARCHIVE_BASENAME="athanor-dashboard-sync.tar"
LOCAL_ARCHIVE="$(mktemp "${TMPDIR:-/tmp}/${ARCHIVE_BASENAME}.XXXXXX")"
REMOTE_ARCHIVE="/tmp/${ARCHIVE_BASENAME}"
cleanup() {
  rm -f "${LOCAL_ARCHIVE}"
}
trap cleanup EXIT

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
  -cf "${LOCAL_ARCHIVE}" \
  .
scp "${LOCAL_ARCHIVE}" "${DEV_HOST}:${REMOTE_ARCHIVE}"
ssh "${DEV_HOST}" "mkdir -p '${REMOTE_DASHBOARD_DIR}' && find '${REMOTE_DASHBOARD_DIR}' -mindepth 1 -maxdepth 1 ! -name '.env' -exec rm -rf {} + && tar -xf '${REMOTE_ARCHIVE}' -C '${REMOTE_DASHBOARD_DIR}' && rm -f '${REMOTE_ARCHIVE}'"
if [[ -d "${REPO_DIR}/reports/truth-inventory" ]]; then
  echo "[2b/4] Syncing truth inventory..."
  tar -C "${REPO_DIR}/reports" -cf - truth-inventory \
    | ssh "${DEV_HOST}" "sudo mkdir -p '${REMOTE_REPORTS_DIR}' && sudo rm -rf '${REMOTE_TRUTH_INVENTORY_DIR}' && sudo tar -xf - -C '${REMOTE_REPORTS_DIR}'"
fi

if [[ "${1:-}" == "--no-build" ]]; then
  echo "[3/4] Skipped build/restart (--no-build)"
  echo "[4/4] Sources synced only"
  exit 0
fi

echo "[3/4] Rebuilding and restarting dashboard lane..."
ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && docker compose build dashboard && docker compose up -d dashboard"

echo "[4/4] Verifying dashboard health..."
if wait_for_dashboard_health && python3 "${REPO_DIR}/scripts/tests/live-dashboard-smoke.py" --scope command-center-final-form --insecure --skip-chat; then
  echo "=== Dashboard deploy complete ==="
  exit 0
fi
echo "ERROR: dashboard did not become healthy within ${READY_TIMEOUT_SECONDS}s"
ssh "${DEV_HOST}" "cd '${REMOTE_DASHBOARD_DIR}' && docker compose ps dashboard && docker logs athanor-dashboard --tail 50"
exit 1
