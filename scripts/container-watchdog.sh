#!/usr/bin/env bash
# Container health watchdog for Unraid/VAULT.
# Detects containers stuck in restart loops or with failed health checks,
# and restarts them. Designed to run as a cron job every 5 minutes.
#
# Usage: ./container-watchdog.sh
# Cron:  */5 * * * * /opt/athanor/scripts/container-watchdog.sh >> /var/log/container-watchdog.log 2>&1

set -euo pipefail

LOG_PREFIX="[$(date -Iseconds)] watchdog:"

# Media containers (original scope — Unraid shfs issues)
MEDIA_CONTAINERS="plex sonarr radarr tautulli homeassistant"

# Infrastructure containers (added Phase 4h — critical services)
INFRA_CONTAINERS="redis postgres litellm neo4j"

# Cooldown file for infrastructure restarts (prevent flapping)
COOLDOWN_DIR="/tmp/watchdog-cooldown"
COOLDOWN_SECONDS=60
mkdir -p "$COOLDOWN_DIR"

restart_count=0

check_container() {
    local CONTAINER="$1"
    local IS_INFRA="${2:-false}"

    # Skip if container doesn't exist
    if ! docker inspect "$CONTAINER" &>/dev/null; then
        return
    fi

    STATUS=$(docker inspect --format '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
    HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER" 2>/dev/null || echo "unknown")
    RESTARTING=$(docker inspect --format '{{.State.Restarting}}' "$CONTAINER" 2>/dev/null || echo "false")

    # Check for containers stuck restarting
    if [ "$RESTARTING" = "true" ]; then
        if check_cooldown "$CONTAINER" "$IS_INFRA"; then
            echo "$LOG_PREFIX $CONTAINER is stuck restarting — forcing restart"
            docker restart "$CONTAINER" 2>/dev/null || true
            restart_count=$((restart_count + 1))
            notify_restart "$CONTAINER" "stuck restarting"
        fi
        return
    fi

    # Check for unhealthy containers
    if [ "$HEALTH" = "unhealthy" ]; then
        if check_cooldown "$CONTAINER" "$IS_INFRA"; then
            echo "$LOG_PREFIX $CONTAINER is unhealthy — restarting"
            docker restart "$CONTAINER" 2>/dev/null || true
            restart_count=$((restart_count + 1))
            notify_restart "$CONTAINER" "unhealthy"
        fi
        return
    fi

    # Check for exited containers that should be running
    if [ "$STATUS" = "exited" ] || [ "$STATUS" = "dead" ]; then
        if check_cooldown "$CONTAINER" "$IS_INFRA"; then
            echo "$LOG_PREFIX $CONTAINER is $STATUS — starting"
            docker start "$CONTAINER" 2>/dev/null || true
            restart_count=$((restart_count + 1))
            notify_restart "$CONTAINER" "$STATUS"
        fi
        return
    fi

    # Check for containers that are running but have recent fatal patterns in logs
    if [ "$STATUS" = "running" ]; then
        LAST_LOG=$(docker logs "$CONTAINER" --tail 3 2>&1 || true)
        if echo "$LAST_LOG" | grep -qiE "Non-recoverable failure|Cannot write to the data directory|Read/write access is required"; then
            if check_cooldown "$CONTAINER" "$IS_INFRA"; then
                echo "$LOG_PREFIX $CONTAINER has fatal error in logs — restarting"
                docker restart "$CONTAINER" 2>/dev/null || true
                restart_count=$((restart_count + 1))
                notify_restart "$CONTAINER" "fatal log pattern"
            fi
            return
        fi
    fi
}

check_cooldown() {
    local CONTAINER="$1"
    local IS_INFRA="$2"

    # Media containers: no cooldown (restart immediately)
    if [ "$IS_INFRA" = "false" ]; then
        return 0
    fi

    # Infrastructure containers: 60s cooldown between restarts
    local COOLDOWN_FILE="$COOLDOWN_DIR/$CONTAINER"
    if [ -f "$COOLDOWN_FILE" ]; then
        local LAST_RESTART
        LAST_RESTART=$(cat "$COOLDOWN_FILE")
        local NOW
        NOW=$(date +%s)
        local ELAPSED=$((NOW - LAST_RESTART))
        if [ "$ELAPSED" -lt "$COOLDOWN_SECONDS" ]; then
            echo "$LOG_PREFIX $CONTAINER in cooldown (${ELAPSED}s/${COOLDOWN_SECONDS}s) — skipping"
            return 1
        fi
    fi

    # Record this restart
    date +%s > "$COOLDOWN_FILE"
    return 0
}

notify_restart() {
    local CONTAINER="$1"
    local REASON="$2"

    # Send ntfy notification for infrastructure restarts
    if command -v curl &>/dev/null; then
        curl -s -o /dev/null \
            -H "Title: Watchdog: $CONTAINER restarted" \
            -H "Priority: high" \
            -H "Tags: warning,robot" \
            -d "$CONTAINER restarted by watchdog. Reason: $REASON" \
            "http://localhost:8880/athanor" 2>/dev/null || true
    fi
}

# Check media containers
for CONTAINER in $MEDIA_CONTAINERS; do
    check_container "$CONTAINER" "false"
done

# Check infrastructure containers
for CONTAINER in $INFRA_CONTAINERS; do
    check_container "$CONTAINER" "true"
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
