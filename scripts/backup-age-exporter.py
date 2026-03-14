#!/usr/bin/env python3
"""Expose backup freshness metrics for Prometheus.

Auto-discovers backup targets by glob patterns across /mnt. Designed
to run on VAULT where all backup directories are accessible.

Metrics:
    athanor_backup_age_seconds{target="...",path="..."}
    athanor_backup_latest_mtime_seconds{target="...",path="..."}
    athanor_backup_target_found{target="..."}

Usage:
    ./backup-age-exporter.py
    BACKUP_EXPORTER_PORT=9199 ./backup-age-exporter.py

Port: 9199 (default, overridable via BACKUP_EXPORTER_PORT)
"""

from __future__ import annotations

import glob
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable


PORT = int(os.getenv("BACKUP_EXPORTER_PORT", "9199"))
DEFAULT_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("postgres", ("/mnt/user/data/backups/postgres/**/*",)),
    ("stash", ("/mnt/user/data/backups/stash/**/*",)),
    ("athanor", ("/mnt/user/data/backups/athanor/**/*",)),
    ("qdrant", ("/mnt/user/data/backups/qdrant/**/*",)),
    ("neo4j", ("/mnt/user/data/backups/neo4j/**/*",)),
    ("field_inspect", ("/mnt/user/Backups/field-inspect/**/*",)),
    ("flash_config", ("/mnt/user/Backups/pre_disassembly_Unraid_*/flash_config_*.tar.gz",)),
)


def iter_matches(patterns: Iterable[str]) -> Iterable[Path]:
    seen: set[str] = set()
    for pattern in patterns:
        for match in glob.iglob(pattern, recursive=True):
            if match in seen:
                continue
            seen.add(match)
            candidate = Path(match)
            if candidate.exists():
                yield candidate


def newest_mtime(patterns: Iterable[str]) -> tuple[float | None, str | None]:
    latest_value: float | None = None
    latest_path: str | None = None
    for candidate in iter_matches(patterns):
        try:
            stat = candidate.stat()
        except OSError:
            continue
        mtime = stat.st_mtime
        if latest_value is None or mtime > latest_value:
            latest_value = mtime
            latest_path = str(candidate)
    return latest_value, latest_path


def render_metrics() -> bytes:
    now = time.time()
    lines = [
        "# HELP athanor_backup_age_seconds Age of the newest backup artifact for a target.",
        "# TYPE athanor_backup_age_seconds gauge",
        "# HELP athanor_backup_latest_mtime_seconds Unix mtime of the newest backup artifact for a target.",
        "# TYPE athanor_backup_latest_mtime_seconds gauge",
        "# HELP athanor_backup_target_found Whether at least one backup artifact was found for a target.",
        "# TYPE athanor_backup_target_found gauge",
    ]

    for target, patterns in DEFAULT_TARGETS:
        latest_mtime, latest_path = newest_mtime(patterns)
        if latest_mtime is None:
            lines.append(f'athanor_backup_age_seconds{{target="{target}",path="missing"}} +Inf')
            lines.append(f'athanor_backup_latest_mtime_seconds{{target="{target}",path="missing"}} 0')
            lines.append(f'athanor_backup_target_found{{target="{target}"}} 0')
            continue

        age = max(now - latest_mtime, 0)
        path = latest_path.replace("\\", "\\\\").replace('"', '\\"') if latest_path else "unknown"
        lines.append(f'athanor_backup_age_seconds{{target="{target}",path="{path}"}} {age:.0f}')
        lines.append(f'athanor_backup_latest_mtime_seconds{{target="{target}",path="{path}"}} {latest_mtime:.0f}')
        lines.append(f'athanor_backup_target_found{{target="{target}"}} 1')

    lines.append("")
    return "\n".join(lines).encode("utf-8")


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in {"/metrics", "/"}:
            self.send_response(404)
            self.end_headers()
            return

        body = render_metrics()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        print(f"[{timestamp}] {fmt % args}")


def main() -> int:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), MetricsHandler)
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] Backup age exporter on :{PORT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
