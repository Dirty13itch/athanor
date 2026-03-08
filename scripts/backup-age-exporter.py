#!/usr/bin/env python3
"""Prometheus exporter for Athanor backup freshness.

Checks backup file modification times and exposes metrics via HTTP
in Prometheus text format. Designed to run on VAULT where all backup
directories are accessible (Qdrant via NFS, Neo4j and appdata locally).

Metrics:
    athanor_backup_age_seconds{type="...",node="..."}
    athanor_backup_last_success_timestamp{type="...",node="..."}

Usage:
    ./backup-age-exporter.py [-h] [-p PORT] [-i INTERVAL]

Port: 9199 (default)
"""

import glob
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Backup targets ──────────────────────────────────────────────────
# Each entry: (type, node, directory, file_glob_pattern)
# All paths are as seen from VAULT (where this exporter runs).
BACKUP_TARGETS = [
    {
        "type": "qdrant",
        "node": "foundry",
        # FOUNDRY writes via NFS. On VAULT, visible at either path.
        "directory": "/mnt/user/data/backups/athanor/qdrant",
        "fallback_directory": "/mnt/vault/data/backups/athanor/qdrant",
        "pattern": "*.snapshot",
    },
    {
        "type": "neo4j",
        "node": "vault",
        "directory": "/mnt/user/backups/athanor/neo4j",
        "pattern": "graph_*.cypher",
    },
    {
        "type": "appdata",
        "node": "vault",
        "directory": "/mnt/user/backups/athanor/appdata",
        "pattern": "*.tar.gz",
    },
]


def find_newest_mtime(target):
    """Return mtime of the newest file matching pattern, or None.

    Checks primary directory first, then fallback_directory if defined.
    """
    dirs_to_check = [target["directory"]]
    if "fallback_directory" in target:
        dirs_to_check.append(target["fallback_directory"])

    for directory in dirs_to_check:
        if not os.path.isdir(directory):
            continue
        search = os.path.join(directory, target["pattern"])
        files = glob.glob(search)
        if files:
            return max(os.path.getmtime(f) for f in files)
    return None


def collect_metrics():
    """Build Prometheus text exposition output."""
    now = time.time()
    lines = []

    lines.append("# HELP athanor_backup_age_seconds Age of the most recent backup in seconds.")
    lines.append("# TYPE athanor_backup_age_seconds gauge")

    for target in BACKUP_TARGETS:
        label = f'type="{target["type"]}",node="{target["node"]}"'
        mtime = find_newest_mtime(target)
        if mtime is not None:
            age = int(now - mtime)
            lines.append(f"athanor_backup_age_seconds{{{label}}} {age}")
        else:
            # Directory missing or empty — report sentinel to trigger alert
            lines.append(f"athanor_backup_age_seconds{{{label}}} 999999")

    lines.append("")
    lines.append("# HELP athanor_backup_last_success_timestamp Unix timestamp of the most recent backup.")
    lines.append("# TYPE athanor_backup_last_success_timestamp gauge")

    for target in BACKUP_TARGETS:
        label = f'type="{target["type"]}",node="{target["node"]}"'
        mtime = find_newest_mtime(target)
        if mtime is not None:
            lines.append(f"athanor_backup_last_success_timestamp{{{label}}} {int(mtime)}")
        else:
            lines.append(f"athanor_backup_last_success_timestamp{{{label}}} 0")

    lines.append("")
    lines.append("# HELP athanor_backup_exporter_up Whether the backup age exporter is running.")
    lines.append("# TYPE athanor_backup_exporter_up gauge")
    lines.append("athanor_backup_exporter_up 1")
    lines.append("")

    return "\n".join(lines)


class MetricsHandler(BaseHTTPRequestHandler):
    """Serve Prometheus metrics on /metrics, health on /."""

    def do_GET(self):
        if self.path == "/metrics":
            body = collect_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/":
            body = b"athanor-backup-exporter\n/metrics\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        """Log to stderr with timestamp."""
        print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {fmt % args}", file=sys.stderr)


def main():
    """Parse args and start the metrics HTTP server."""
    port = 9199
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("-p", "--port"):
            if i + 1 < len(args):
                port = int(args[i + 1])
                i += 2
                continue
            else:
                print("ERROR: --port requires a value", file=sys.stderr)
                sys.exit(2)
        elif args[i] in ("-h", "--help"):
            print(__doc__)
            print("  -p, --port PORT   HTTP port (default: 9199)")
            print("  -h, --help        Show this help message")
            sys.exit(0)
        else:
            print(f"ERROR: Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(2)

    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] Backup age exporter listening on :{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] Shutting down", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    main()
