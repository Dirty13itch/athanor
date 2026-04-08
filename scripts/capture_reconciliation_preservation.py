from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "preservation-latest.json"


def _run_git_command(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


def _git_snapshot(path: Path) -> dict[str, Any]:
    has_git = (path / ".git").exists()
    if not has_git:
        return {"git_repository": False}

    branch_result = _run_git_command(path, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

    head_result = _run_git_command(path, "rev-parse", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None

    status_result = _run_git_command(path, "status", "--porcelain")
    status_lines = [line.rstrip() for line in status_result.stdout.splitlines() if line.strip()]
    tracked_modified: list[str] = []
    untracked: list[str] = []
    for line in status_lines:
        if line.startswith("?? "):
            untracked.append(line[3:])
        elif len(line) >= 4:
            tracked_modified.append(line[3:])

    tracking_result = _run_git_command(path, "status", "--short", "--branch")
    tracking_line = tracking_result.stdout.splitlines()[0].strip() if tracking_result.stdout.splitlines() else ""

    return {
        "git_repository": True,
        "branch": branch,
        "head": head,
        "tracking": tracking_line,
        "tracked_modified": tracked_modified,
        "untracked": untracked,
    }


def _non_git_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}

    top_level_entries = sorted(item.name for item in path.iterdir())
    return {
        "exists": True,
        "top_level_entry_count": len(top_level_entries),
        "top_level_entries_preview": top_level_entries[:40],
    }


def _snapshot_source(entry: dict[str, Any]) -> dict[str, Any]:
    source_id = str(entry.get("id") or "")
    path_value = str(entry.get("path") or "")
    source_kind = str(entry.get("source_kind") or "")
    snapshot: dict[str, Any] = {
        "id": source_id,
        "name": str(entry.get("name") or ""),
        "path": path_value,
        "source_kind": source_kind,
        "ecosystem_role": str(entry.get("ecosystem_role") or ""),
        "default_disposition": str(entry.get("default_disposition") or ""),
    }

    if path_value.startswith("http://") or path_value.startswith("https://"):
        snapshot["remote_only"] = True
        return snapshot

    source_path = Path(path_value)
    snapshot["exists"] = source_path.exists()
    if not source_path.exists():
        return snapshot

    git_snapshot = _git_snapshot(source_path)
    if git_snapshot.get("git_repository"):
        snapshot.update(git_snapshot)
    else:
        snapshot.update(_non_git_snapshot(source_path))

    return snapshot


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    sources = [dict(item) for item in registry.get("sources", []) if isinstance(item, dict)]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_registry_version": str(registry.get("version") or ""),
        "source_count": len(sources),
        "sources": [_snapshot_source(entry) for entry in sources],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
