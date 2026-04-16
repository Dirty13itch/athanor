from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "preservation-latest.json"
WINDOWS_GIT_EXE = Path('/mnt/c/Program Files/Git/cmd/git.exe')
GIT_PROBE_TIMEOUT_SECONDS = 10


def _resolve_source_path(path_value: str) -> Path:
    normalized = str(path_value).strip().replace('\\', '/')
    if normalized.startswith('/mnt/'):
        return Path(normalized)
    if normalized.startswith('C:/'):
        return Path('/mnt/c') / normalized.removeprefix('C:/')
    return Path(normalized)


def _to_windows_path(path: Path) -> str | None:
    normalized = path.as_posix()
    if not normalized.startswith('/mnt/c/'):
        return None
    suffix = normalized.removeprefix('/mnt/c/').replace('/', '\\')
    return f'C:\\{suffix}'


def _git_command(path: Path, *args: str) -> list[str]:
    windows_path = _to_windows_path(path)
    if windows_path and WINDOWS_GIT_EXE.exists():
        return [str(WINDOWS_GIT_EXE), '-C', windows_path, *args]
    return ['git', '-C', str(path), *args]


def _run_git_command(path: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            _git_command(path, *args),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=GIT_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None


def _git_snapshot(path: Path) -> dict[str, Any]:
    has_git = (path / '.git').exists()
    if not has_git:
        return {'git_repository': False}

    branch_result = _run_git_command(path, 'rev-parse', '--abbrev-ref', 'HEAD')
    head_result = _run_git_command(path, 'rev-parse', 'HEAD')
    status_result = _run_git_command(path, 'status', '--porcelain')
    tracking_result = _run_git_command(path, 'status', '--short', '--branch')
    probe_results = (branch_result, head_result, status_result, tracking_result)
    git_status_incomplete = any(result is None for result in probe_results)

    branch = branch_result.stdout.strip() if branch_result and branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result and head_result.returncode == 0 else None
    status_lines = [line.rstrip() for line in status_result.stdout.splitlines() if line.strip()] if status_result and status_result.returncode == 0 else []
    tracked_modified: list[str] = []
    untracked: list[str] = []
    for line in status_lines:
        if line.startswith('?? '):
            untracked.append(line[3:])
        elif len(line) >= 4:
            tracked_modified.append(line[3:])

    tracking_line = (
        tracking_result.stdout.splitlines()[0].strip()
        if tracking_result and tracking_result.returncode == 0 and tracking_result.stdout.splitlines()
        else ''
    )

    return {
        'git_repository': True,
        'branch': branch,
        'head': head,
        'tracking': tracking_line,
        'tracked_modified': tracked_modified,
        'untracked': untracked,
        'git_status_incomplete': git_status_incomplete,
    }


def _non_git_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {'exists': False}

    try:
        top_level_entries = sorted(item.name for item in path.iterdir())
    except (PermissionError, FileNotFoundError, OSError):
        return {'exists': True, 'top_level_entry_count': None, 'top_level_entries_preview': []}
    return {
        'exists': True,
        'top_level_entry_count': len(top_level_entries),
        'top_level_entries_preview': top_level_entries[:40],
    }


def _snapshot_source(entry: dict[str, Any]) -> dict[str, Any]:
    source_id = str(entry.get('id') or '')
    path_value = str(entry.get('path') or '')
    source_kind = str(entry.get('source_kind') or '')
    snapshot: dict[str, Any] = {
        'id': source_id,
        'name': str(entry.get('name') or ''),
        'path': path_value,
        'source_kind': source_kind,
        'ecosystem_role': str(entry.get('ecosystem_role') or ''),
        'default_disposition': str(entry.get('default_disposition') or ''),
    }

    if path_value.startswith('http://') or path_value.startswith('https://'):
        snapshot['remote_only'] = True
        return snapshot

    source_path = _resolve_source_path(path_value)
    snapshot['resolved_path'] = source_path.as_posix()
    snapshot['exists'] = source_path.exists()
    if not source_path.exists():
        return snapshot

    git_snapshot = _git_snapshot(source_path)
    if git_snapshot.get('git_repository'):
        snapshot.update(git_snapshot)
    else:
        snapshot.update(_non_git_snapshot(source_path))

    return snapshot


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    sources = [dict(item) for item in registry.get('sources', []) if isinstance(item, dict)]

    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_registry_version': str(registry.get('version') or ''),
        'source_count': len(sources),
        'sources': [_snapshot_source(entry) for entry in sources],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding='utf-8')
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
