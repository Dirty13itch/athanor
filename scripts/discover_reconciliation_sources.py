from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "discovery-latest.json"
SCAN_ROOT = Path("C:/")
MAX_DEPTH = 3

REPO_MARKERS = {".git"}
STRONG_MARKERS = {"AGENTS.md", "PROJECT.md"}
WEAK_MARKERS = {".agents", ".claude", ".codex", "CLAUDE.md"}
MANIFEST_MARKERS = {"package.json", "pyproject.toml"}
SUPPORTING_REPO_MARKERS = {"docker-compose.yml", "Makefile", "netlify.toml", "vercel.json"}
ALL_MARKERS = REPO_MARKERS | STRONG_MARKERS | WEAK_MARKERS | MANIFEST_MARKERS | SUPPORTING_REPO_MARKERS

EXCLUDED_ROOTS = {
    "C:/$Recycle.Bin",
    "C:/PerfLogs",
    "C:/Program Files",
    "C:/Program Files (x86)",
    "C:/ProgramData",
    "C:/System Volume Information",
    "C:/Users/Default",
    "C:/Users/Public",
    "C:/Windows",
}
NON_CANDIDATE_ROOTS = {
    "C:/Users/Shaun",
}
EXCLUDED_SEGMENTS = {
    ".agents",
    ".cache",
    ".claude",
    ".codex",
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "AppData",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}


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


def _is_excluded(path: Path) -> bool:
    normalized = path.as_posix()
    if normalized in EXCLUDED_ROOTS:
        return True
    return any(part in EXCLUDED_SEGMENTS for part in path.parts)


def _iter_directories(path: Path, depth: int) -> Iterator[tuple[Path, int]]:
    if depth > MAX_DEPTH or _is_excluded(path):
        return

    yield path, depth

    if depth == MAX_DEPTH:
        return

    try:
        children = sorted(
            (child for child in path.iterdir() if child.is_dir()),
            key=lambda item: item.name.lower(),
        )
    except (PermissionError, FileNotFoundError, OSError):
        return

    for child in children:
        yield from _iter_directories(child, depth + 1)


def _read_package_name(path: Path) -> str | None:
    package_path = path / "package.json"
    if not package_path.is_file():
        return None

    try:
        payload = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    package_name = payload.get("name")
    return str(package_name) if isinstance(package_name, str) and package_name.strip() else None


def _read_pyproject_name(path: Path) -> str | None:
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    try:
        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None

    project = payload.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str) and name.strip():
            return name

    tool = payload.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            name = poetry.get("name")
            if isinstance(name, str) and name.strip():
                return name

    return None


def _git_snapshot(path: Path) -> dict[str, Any]:
    if not (path / ".git").exists():
        return {"git_repository": False}

    branch_result = _run_git_command(path, "rev-parse", "--abbrev-ref", "HEAD")
    head_result = _run_git_command(path, "rev-parse", "HEAD")
    status_result = _run_git_command(path, "status", "--short", "--branch")

    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    tracking_line = status_result.stdout.splitlines()[0].strip() if status_result.stdout.splitlines() else ""

    return {
        "git_repository": True,
        "branch": branch,
        "head": head,
        "tracking": tracking_line,
    }


def _indicators_for(path: Path) -> list[str]:
    indicators = [marker for marker in sorted(ALL_MARKERS) if (path / marker).exists()]
    return indicators


def _qualifies(indicators: list[str]) -> bool:
    indicator_set = set(indicators)
    if indicator_set & STRONG_MARKERS:
        return True
    if indicator_set & REPO_MARKERS and indicator_set & (
        WEAK_MARKERS | MANIFEST_MARKERS | STRONG_MARKERS | SUPPORTING_REPO_MARKERS
    ):
        return True
    if indicator_set & WEAK_MARKERS and indicator_set & MANIFEST_MARKERS:
        return True
    return False


def _candidate_record(path: Path, depth: int, registry_paths: set[str]) -> dict[str, Any]:
    indicators = _indicators_for(path)
    manifest_name = _read_package_name(path) or _read_pyproject_name(path)
    record: dict[str, Any] = {
        "path": path.as_posix(),
        "depth": depth,
        "indicators": indicators,
        "known_in_source_registry": path.as_posix() in registry_paths,
        "manifest_name": manifest_name,
    }
    record.update(_git_snapshot(path))
    return record


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry_paths = {
        str(item.get("path"))
        for item in registry.get("sources", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }

    candidates: list[dict[str, Any]] = []
    for path, depth in _iter_directories(SCAN_ROOT, 0):
        if path.as_posix() in NON_CANDIDATE_ROOTS:
            continue
        indicators = _indicators_for(path)
        if not indicators or not _qualifies(indicators):
            continue
        candidates.append(_candidate_record(path, depth, registry_paths))

    candidates.sort(key=lambda item: (item["depth"], item["path"].lower()))
    unmatched = [item for item in candidates if not item["known_in_source_registry"]]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_root": SCAN_ROOT.as_posix(),
        "max_depth": MAX_DEPTH,
        "candidate_count": len(candidates),
        "unmatched_candidate_count": len(unmatched),
        "candidates": candidates,
        "unmatched_candidates": unmatched,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
