#!/usr/bin/env bash
# Write backup age metrics in Prometheus textfile collector format.
# Outputs to stdout; redirect to .prom file for node_exporter pickup.
#
# Deployed via cron every 15 minutes:
#   */15 * * * * /opt/athanor/scripts/backup-age-metrics.sh > /var/lib/node_exporter/textfile_collector/backup_age.prom
#
# Metrics produced:
#   athanor_backup_age_seconds{target="qdrant"}  - age of newest Qdrant snapshot
#   athanor_backup_age_seconds{target="appdata"}  - age of newest appdata backup
#   athanor_backup_last_success_timestamp{target=...} - epoch of newest backup

set -euo pipefail

NOW=$(date +%s)

# Detect which backup directories exist on this host and report accordingly.

# --- Qdrant backups (FOUNDRY writes to NFS, files also visible from VAULT) ---
QDRANT_BACKUP_DIR="/mnt/vault/data/backups/athanor/qdrant"
if [ -d "$QDRANT_BACKUP_DIR" ]; then
    NEWEST_QDRANT=$(find "$QDRANT_BACKUP_DIR" -name "*.snapshot" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
    if [ -n "$NEWEST_QDRANT" ]; then
        QDRANT_MTIME=${NEWEST_QDRANT%.*}
        QDRANT_AGE=$((NOW - QDRANT_MTIME))
        echo "# HELP athanor_backup_age_seconds Age of the most recent backup in seconds."
        echo "# TYPE athanor_backup_age_seconds gauge"
        echo "athanor_backup_age_seconds{target=\"qdrant\"} ${QDRANT_AGE}"
        echo "# HELP athanor_backup_last_success_timestamp Unix timestamp of the most recent backup."
        echo "# TYPE athanor_backup_last_success_timestamp gauge"
        echo "athanor_backup_last_success_timestamp{target=\"qdrant\"} ${QDRANT_MTIME}"
    else
        # Directory exists but no snapshots found — report max age to trigger alert
        echo "# HELP athanor_backup_age_seconds Age of the most recent backup in seconds."
        echo "# TYPE athanor_backup_age_seconds gauge"
        echo "athanor_backup_age_seconds{target=\"qdrant\"} 999999"
        echo "# HELP athanor_backup_last_success_timestamp Unix timestamp of the most recent backup."
        echo "# TYPE athanor_backup_last_success_timestamp gauge"
        echo "athanor_backup_last_success_timestamp{target=\"qdrant\"} 0"
    fi
fi

# --- Appdata backups (VAULT only) ---
APPDATA_BACKUP_DIR="/mnt/appdatacache/backups"
if [ -d "$APPDATA_BACKUP_DIR" ]; then
    NEWEST_APPDATA=$(find "$APPDATA_BACKUP_DIR" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
    if [ -n "$NEWEST_APPDATA" ]; then
        APPDATA_MTIME=${NEWEST_APPDATA%.*}
        APPDATA_AGE=$((NOW - APPDATA_MTIME))
        # Only emit HELP/TYPE if not already emitted above
        if [ ! -d "$QDRANT_BACKUP_DIR" ]; then
            echo "# HELP athanor_backup_age_seconds Age of the most recent backup in seconds."
            echo "# TYPE athanor_backup_age_seconds gauge"
        fi
        echo "athanor_backup_age_seconds{target=\"appdata\"} ${APPDATA_AGE}"
        if [ ! -d "$QDRANT_BACKUP_DIR" ]; then
            echo "# HELP athanor_backup_last_success_timestamp Unix timestamp of the most recent backup."
            echo "# TYPE athanor_backup_last_success_timestamp gauge"
        fi
        echo "athanor_backup_last_success_timestamp{target=\"appdata\"} ${APPDATA_MTIME}"
    else
        if [ ! -d "$QDRANT_BACKUP_DIR" ]; then
            echo "# HELP athanor_backup_age_seconds Age of the most recent backup in seconds."
            echo "# TYPE athanor_backup_age_seconds gauge"
        fi
        echo "athanor_backup_age_seconds{target=\"appdata\"} 999999"
        if [ ! -d "$QDRANT_BACKUP_DIR" ]; then
            echo "# HELP athanor_backup_last_success_timestamp Unix timestamp of the most recent backup."
            echo "# TYPE athanor_backup_last_success_timestamp gauge"
        fi
        echo "athanor_backup_last_success_timestamp{target=\"appdata\"} 0"
    fi
fi
