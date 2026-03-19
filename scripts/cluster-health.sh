#!/bin/bash
# Athanor Cluster Health Check — runs every 5 min via systemd timer
ALERT="http://192.168.1.203:8880/athanor"

# Check each node is reachable
for node in foundry workshop vault; do
    if \! ssh -o ConnectTimeout=5 -o BatchMode=yes $node "echo ok" &>/dev/null; then
        curl -s -H "Content-Type: application/json" -d "{\"title\":\"NODE DOWN\",\"message\":\"$node unreachable\",\"priority\":5}" $ALERT
    fi
done

# Check critical containers on FOUNDRY
DOWN=$(ssh -o ConnectTimeout=5 foundry "docker ps --filter status=exited --format {{.Names}}" 2>/dev/null | grep -E "vllm|athanor" | head -5)
if [ -n "$DOWN" ]; then
    curl -s -H "Content-Type: application/json" -d "{\"title\":\"Container Down\",\"message\":\"$DOWN\",\"priority\":4}" $ALERT
fi

# Check VAULT disk
DISK_PCT=$(ssh -o ConnectTimeout=5 root@192.168.1.203 "df /mnt/user | tail -1 | awk {print } | tr -d %" 2>/dev/null)
if [ -n "$DISK_PCT" ] && [ "$DISK_PCT" -gt 90 ]; then
    curl -s -H "Content-Type: application/json" -d "{\"title\":\"DISK WARNING\",\"message\":\"VAULT array at ${DISK_PCT}%\",\"priority\":4}" $ALERT
fi

# Check GPU temps on FOUNDRY
GPU_TEMP=$(ssh -o ConnectTimeout=5 foundry "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader | sort -rn | head -1" 2>/dev/null)
if [ -n "$GPU_TEMP" ] && [ "$GPU_TEMP" -gt 85 ]; then
    curl -s -H "Content-Type: application/json" -d "{\"title\":\"GPU HOT\",\"message\":\"FOUNDRY GPU at ${GPU_TEMP}C\",\"priority\":5}" $ALERT
fi

# Daily drift check (runs once per day when called with --drift or at first run after 6am)
DRIFT_FLAG="/tmp/athanor-drift-last-run"
run_drift_check() {
    local SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -x "$SCRIPT_DIR/drift-check.sh" ]; then
        echo "Running daily drift check..."
        bash "$SCRIPT_DIR/drift-check.sh"
        date +%Y-%m-%d > "$DRIFT_FLAG"
    fi
}

if [ "$1" = "--drift" ]; then
    run_drift_check
elif [ -f "$DRIFT_FLAG" ]; then
    LAST_RUN=$(cat "$DRIFT_FLAG" 2>/dev/null)
    TODAY=$(date +%Y-%m-%d)
    HOUR=$(date +%H)
    # Auto-trigger drift check once daily after 6am if not yet run today
    if [ "$LAST_RUN" != "$TODAY" ] && [ "$HOUR" -ge 6 ]; then
        run_drift_check
    fi
else
    # First run ever - only trigger after 6am
    HOUR=$(date +%H)
    if [ "$HOUR" -ge 6 ]; then
        run_drift_check
    fi
fi
