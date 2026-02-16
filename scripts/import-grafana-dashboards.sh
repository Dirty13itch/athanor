#!/bin/bash
# Import Grafana dashboards on VAULT
# Run this on VAULT directly

GRAFANA_URL="http://admin:athanor2026@localhost:3000"

# Import DCGM dashboard #12239
echo "Importing DCGM dashboard..."
jq -n --slurpfile dash /tmp/dcgm-dashboard.json \
  '{"dashboard": $dash[0], "overwrite": true, "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}], "folderId": 0}' \
  | curl -s -X POST "${GRAFANA_URL}/api/dashboards/import" \
    -H "Content-Type: application/json" -d @-
echo ""
echo "--- DCGM done ---"

# Import Node Exporter Full dashboard #1860
echo "Importing Node Exporter Full dashboard..."
jq -n --slurpfile dash /tmp/node-exporter-dashboard.json \
  '{"dashboard": $dash[0], "overwrite": true, "inputs": [{"name": "DS_PROMETHEUS", "type": "datasource", "pluginId": "prometheus", "value": "Prometheus"}], "folderId": 0}' \
  | curl -s -X POST "${GRAFANA_URL}/api/dashboards/import" \
    -H "Content-Type: application/json" -d @-
echo ""
echo "--- Node Exporter Full done ---"
