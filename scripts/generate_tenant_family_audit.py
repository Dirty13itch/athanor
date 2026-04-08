from __future__ import annotations

import json
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "tenant-family-audit-latest.json"
INTERESTING_HASH_FILES = ("package.json", "PROJECT.md", "AGENTS.md", "next.config.ts", "tsconfig.json")
EXCLUDED_FILE_DELTA_SEGMENTS = {".git", "node_modules", ".next", "__pycache__", "coverage", "dist", "build"}


def _run_git(path: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    return completed.stdout.strip()


def _path_metadata(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    metadata: dict[str, Any] = {
        "path": path.as_posix(),
        "exists": path.exists(),
        "is_git": False,
        "top_level_entries": [],
    }
    if not path.exists():
        return metadata

    metadata["top_level_entries"] = sorted(entry.name for entry in path.iterdir())[:25]
    hash_summary: dict[str, str | None] = {}
    for relative_path in INTERESTING_HASH_FILES:
        candidate = path / relative_path
        if candidate.exists() and candidate.is_file():
            hash_summary[relative_path] = hashlib.sha256(candidate.read_bytes()).hexdigest()[:16]
        else:
            hash_summary[relative_path] = None
    metadata["hash_summary"] = hash_summary

    git_dir = path / ".git"
    if not git_dir.exists():
        return metadata

    status_lines = _run_git(path, "status", "--short", "--branch").splitlines()
    branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    head = _run_git(path, "rev-parse", "--short", "HEAD")
    origin = _run_git(path, "remote", "get-url", "origin")
    dirty_files = [line for line in status_lines[1:] if line.strip()]
    dirty_paths = [line[3:].strip() for line in dirty_files if len(line) >= 4]

    metadata.update(
        {
            "is_git": True,
            "branch": branch,
            "head": head,
            "origin": origin,
            "status_preview": status_lines[:15],
            "dirty_file_count": len(dirty_files),
            "dirty_files": dirty_paths[:30],
            "has_origin": bool(origin),
        }
    )
    return metadata


def _family_summary(root_metadata: dict[str, Any], member_metadata: list[dict[str, Any]]) -> str:
    if all(item["metadata"].get("is_git") for item in member_metadata):
        return (
            "Git-backed tenant family with multiple sibling worktree lanes. "
            "Preserve branches first, then decide merge or freeze order."
        )

    nongit_members = [item for item in member_metadata if not item["metadata"].get("is_git")]
    if root_metadata.get("is_git") and nongit_members:
        return (
            "Primary root is the only git-backed workspace. "
            "Sibling variants are non-git duplicate trees and should be treated as preservation/archive candidates unless they hold unique artifacts."
        )

    return "Mixed tenant family requiring manual preservation and consolidation review."


def _annotate_git_divergence(
    root_metadata: dict[str, Any], member_rows: list[dict[str, Any]]
) -> None:
    if not root_metadata.get("is_git"):
        return

    root_path = Path(str(root_metadata["path"]))
    root_head = str(root_metadata.get("head") or "")
    if not root_head:
        return

    for member in member_rows:
        metadata = member["metadata"]
        if not metadata.get("is_git"):
            continue
        member_path = Path(str(metadata["path"]))
        member_head = str(metadata.get("head") or "")
        if not member_head:
            continue
        counts = _run_git(member_path, "rev-list", "--left-right", "--count", f"{root_head}...{member_head}").split()
        if len(counts) == 2 and all(item.isdigit() for item in counts):
            metadata["behind_root"] = int(counts[0])
            metadata["ahead_root"] = int(counts[1])


def _root_hash_delta_summary(root_metadata: dict[str, Any], member_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root_hashes = dict(root_metadata.get("hash_summary") or {})
    summary: list[dict[str, Any]] = []
    for member in member_rows:
        member_hashes = dict(member["metadata"].get("hash_summary") or {})
        differing_files = sorted(
            relative_path
            for relative_path in INTERESTING_HASH_FILES
            if root_hashes.get(relative_path) != member_hashes.get(relative_path)
        )
        summary.append(
            {
                "id": member["id"],
                "differing_hash_files": differing_files,
            }
        )
    return summary


def _collect_file_set(path: Path) -> set[str]:
    file_set: set[str] = set()
    if not path.exists():
        return file_set
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(path)
        if any(segment in EXCLUDED_FILE_DELTA_SEGMENTS for segment in relative.parts):
            continue
        file_set.add(relative.as_posix())
    return file_set


def _file_delta_summary(root_metadata: dict[str, Any], member_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root_path = Path(str(root_metadata["path"]))
    root_files = _collect_file_set(root_path)
    summary: list[dict[str, Any]] = []
    for member in member_rows:
        member_path = Path(str(member["metadata"]["path"]))
        member_files = _collect_file_set(member_path)
        summary.append(
            {
                "id": member["id"],
                "only_vs_root": sorted(member_files - root_files)[:30],
                "missing_vs_root": sorted(root_files - member_files)[:30],
            }
        )
    return summary


def _direct_replay_risk_summary(root_metadata: dict[str, Any], member_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not root_metadata.get("is_git"):
        return []

    root_path = Path(str(root_metadata["path"]))
    root_head = str(root_metadata.get("head") or "")
    root_dirty = set(root_metadata.get("dirty_files") or [])
    summary: list[dict[str, Any]] = []

    for member in member_rows:
        metadata = member["metadata"]
        if not metadata.get("is_git"):
            summary.append(
                {
                    "id": member["id"],
                    "direct_replay_risk": "not-applicable",
                    "overlapping_dirty_paths": [],
                }
            )
            continue

        member_head = str(metadata.get("head") or "")
        if not root_head or not member_head:
            summary.append(
                {
                    "id": member["id"],
                    "direct_replay_risk": "unknown",
                    "overlapping_dirty_paths": [],
                }
            )
            continue

        changed_paths = set(_run_git(root_path, "diff", "--name-only", f"{root_head}..{member_head}").splitlines())
        overlaps = sorted(root_dirty & changed_paths)
        summary.append(
            {
                "id": member["id"],
                "direct_replay_risk": "high" if overlaps else "low",
                "overlapping_dirty_paths": overlaps[:20],
            }
        )

    return summary


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    sources = [dict(entry) for entry in registry.get("sources", []) if isinstance(entry, dict)]
    source_by_id = {str(entry.get("id") or ""): entry for entry in sources}

    families: list[dict[str, Any]] = []
    for source in sources:
        if str(source.get("ecosystem_role") or "") != "tenant":
            continue
        if source.get("duplicate_of"):
            continue

        root_id = str(source.get("id") or "")
        members = [entry for entry in sources if str(entry.get("duplicate_of") or "") == root_id]
        if not members:
            continue

        root_metadata = _path_metadata(str(source.get("path") or ""))
        member_rows = []
        for member in sorted(members, key=lambda item: str(item.get("path") or "").lower()):
            member_rows.append(
                {
                    "id": str(member.get("id") or ""),
                    "name": str(member.get("name") or ""),
                    "authority_status": str(member.get("authority_status") or ""),
                    "review_status": str(member.get("review_status") or ""),
                    "default_disposition": str(member.get("default_disposition") or ""),
                    "preservation_status": str(member.get("preservation_status") or ""),
                    "shaun_decision_required": bool(member.get("shaun_decision_required")),
                    "notes": list(member.get("notes") or []),
                    "metadata": _path_metadata(str(member.get("path") or "")),
                }
            )

        _annotate_git_divergence(root_metadata, member_rows)

        family = {
            "root_id": root_id,
            "root_name": str(source.get("name") or ""),
            "github_repo": source.get("github_repo"),
            "root_authority_status": str(source.get("authority_status") or ""),
            "root_review_status": str(source.get("review_status") or ""),
            "root_default_disposition": str(source.get("default_disposition") or ""),
            "root_preservation_status": str(source.get("preservation_status") or ""),
            "root_shaun_decision_required": bool(source.get("shaun_decision_required")),
            "root_notes": list(source.get("notes") or []),
            "root_metadata": root_metadata,
            "member_count": len(member_rows),
            "members": member_rows,
        }
        family["summary"] = _family_summary(root_metadata, member_rows)
        family["hash_delta_summary"] = _root_hash_delta_summary(root_metadata, member_rows)
        family["file_delta_summary"] = _file_delta_summary(root_metadata, member_rows)
        family["direct_replay_risk_summary"] = _direct_replay_risk_summary(root_metadata, member_rows)
        families.append(family)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "family_count": len(families),
        "families": families,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
