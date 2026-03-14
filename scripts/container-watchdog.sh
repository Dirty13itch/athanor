#!/usr/bin/env bash
# Container health watchdog for Unraid/VAULT.
# Detects containers stuck in restart loops or with failed health checks,
# and restarts them. Designed to run as a cron job every 5 minutes.
#
# Usage: ./container-watchdog.sh
# Cron:  */5 * * * * /opt/athanor/scripts/container-watchdog.sh >> /var/log/container-watchdog.log 2>&1

set -euo pipefail

LOG_PREFIX="[$(date -Iseconds)] watchdog:"

# Containers to monitor (empty = all running containers)
# These are the ones we know can get stuck on Unraid
MONITORED="plex sonarr radarr tautulli homeassistant"

restart_count=0

for CONTAINER in $MONITORED; do
    # Skip if container doesn't exist
    if ! docker inspect "$CONTAINER" &>/dev/null; then
        continue
    fi

    STATUS=$(docker inspect --format '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
    HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER" 2>/dev/null || echo "unknown")
    RESTARTING=$(docker inspect --format '{{.State.Restarting}}' "$CONTAINER" 2>/dev/null || echo "false")

    # Check for containers stuck restarting
    if [ "$RESTARTING" = "true" ]; then
        echo "$LOG_PREFIX $CONTAINER is stuck restarting — forcing restart"
        docker restart "$CONTAINER" 2>/dev/null || true
        restart_count=$((restart_count + 1))
        continue
    fi

    # Check for unhealthy containers
    if [ "$HEALTH" = "unhealthy" ]; then
        echo "$LOG_PREFIX $CONTAINER is unhealthy — restarting"
        docker restart "$CONTAINER" 2>/dev/null || true
        restart_count=$((restart_count + 1))
        continue
    fi

    # Check for containers that are running but have recent OOM or error exits
    # by looking at the last log line for known fatal patterns
    if [ "$STATUS" = "running" ]; then
        LAST_LOG=$(docker logs "$CONTAINER" --tail 3 2>&1 || true)
        if echo "$LAST_LOG" | grep -qiE "Non-recoverable failure|Cannot write to the data directory|Read/write access is required"; then
            echo "$LOG_PREFIX $CONTAINER has fatal error in logs — restarting"
            docker restart "$CONTAINER" 2>/dev/null || true
            restart_count=$((restart_count + 1))
            continue
        fi
    fi
done

if [ "$restart_count" -gt 0 ]; then
    echo "$LOG_PREFIX restarted $restart_count container(s)"
else
    # Only log every hour to avoid noise (check minute)
    MINUTE=$(date +%M)
    if [ "$MINUTE" = "00" ] || [ "$MINUTE" = "05" ]; then
        echo "$LOG_PREFIX all monitored containers healthy"
    fi
fi
