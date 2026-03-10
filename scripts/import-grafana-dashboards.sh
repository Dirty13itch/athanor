#!/bin/bash
# Import Grafana dashboards on VAULT
# Run this on VAULT directly

set -euo pipefail

GRAFANA_URL="${ATHANOR_GRAFANA_URL:-${GRAFANA_URL:-http://localhost:3000}}"
GRAFANA_USER="${ATHANOR_GRAFANA_USER:-${GRAFANA_USER:-admin}}"
GRAFANA_PASSWORD="${ATHANOR_GRAFANA_PASSWORD:-${GRAFANA_PASSWORD:-}}"

if [ -z "$GRAFANA_PASSWORD" ]; then
  echo "ERROR: Set ATHANOR_GRAFANA_PASSWORD or GRAFANA_PASSWORD before importing dashboards." >&2
  exit 1
fi

CURL_AUTH=(-u "${GRAFANA_USER}:${GRAFANA_PASSWORD}")

# Import DCGM dashboard #12239
echo "Importing DCGM dashboard..."
jq -n --slurpfile dash /tmp/dcgm-dashboard.json \
  '{"dashboard": $dash[0], "overwrite": true, "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}], "folderId": 0}' \
  | curl -s "${CURL_AUTH[@]}" -X POST "${GRAFANA_URL}/api/dashboards/import" \
    -H "Content-Type: application/json" -d @-
echo ""
echo "--- DCGM done ---"

# Import Node Exporter Full dashboard #1860
echo "Importing Node Exporter Full dashboard..."
jq -n --slurpfile dash /tmp/node-exporter-dashboard.json \
  '{"dashboard": $dash[0], "overwrite": true, "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}], "folderId": 0}' \
  | curl -s "${CURL_AUTH[@]}" -X POST "${GRAFANA_URL}/api/dashboards/import" \
    -H "Content-Type: application/json" -d @-
echo ""
echo "--- Node Exporter Full done ---"
