from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "automation-backbone" / "reconciliation-source-registry.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "rfi-hers-primary-root-stabilization-latest.json"
RFI_ROOT_ID = "rfi-hers-rater-assistant-root"
RFI_ROOT_PATH = Path(r"C:\RFI & HERS Rater Assistant")
VALIDATION_COMMANDS = [
    "npm run typecheck",
    "npm run test",
    "python scripts/validate_settlers_ridge_packet.py",
    "powershell -ExecutionPolicy Bypass -File scripts/codex/validate-safe.ps1",
]


def _load_source_entry() -> dict[str, Any]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for entry in payload.get("sources", []):
        if isinstance(entry, dict) and str(entry.get("id") or "") == RFI_ROOT_ID:
            return dict(entry)
    raise RuntimeError(f"Unable to find {RFI_ROOT_ID} in {REGISTRY_PATH}")


def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(RFI_ROOT_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed with code {completed.returncode}: {(completed.stderr or completed.stdout).strip()}"
        )
    return completed.stdout.strip()


def _try_run_git(*args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(RFI_ROOT_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _status_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _run_git("status", "--porcelain").splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if not path:
            continue
        rows.append({"status": status, "path": path})
    return rows


def _classify_path(path: str) -> str:
    if path in {"AGENTS.md", "PROJECT.md", "package.json", ".gitignore", ".agents/system.md"}:
        return "repo_contracts_and_meta"
    if path.startswith("agents/"):
        return "operator_residue"
    if path.startswith("plans/active/") or path.startswith("docs/"):
        return "docs_and_runbooks"
    if path.startswith("data/projects/settlers-ridge/"):
        return "canonical_project_data"
    if path.startswith("scripts/"):
        return "generators_and_importers"
    if path.startswith("output/spreadsheet/"):
        return "workbook_outputs"
    return "operator_residue"


def _group_counts(paths: list[str]) -> dict[str, int]:
    grouped = Counter()
    for path in paths:
        parts = path.split("/")
        if len(parts) == 1:
            grouped[path] += 1
            continue
        grouped["/".join(parts[: min(3, len(parts))])] += 1
    return dict(sorted(grouped.items(), key=lambda item: (-item[1], item[0])))


def _execution_posture(dirty_count: int) -> str:
    if dirty_count == 0:
        return "clean_root_no_stabilization_needed"
    return "ready_for_ordered_stabilization"


def main() -> int:
    source_entry = _load_source_entry()
    status_rows = _status_rows()
    dirty_paths = [row["path"] for row in status_rows]
    tracked_dirty_paths = [row["path"] for row in status_rows if row["status"] != "??"]
    untracked_paths = [row["path"] for row in status_rows if row["status"] == "??"]

    buckets: dict[str, list[str]] = {
        "repo_contracts_and_meta": [],
        "docs_and_runbooks": [],
        "canonical_project_data": [],
        "generators_and_importers": [],
        "workbook_outputs": [],
        "operator_residue": [],
    }
    for path in dirty_paths:
        buckets[_classify_path(path)].append(path)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_id": RFI_ROOT_ID,
        "root_name": str(source_entry.get("name") or ""),
        "root_path": str(RFI_ROOT_PATH),
        "branch": _run_git("branch", "--show-current"),
        "head": _run_git("rev-parse", "--short", "HEAD"),
        "has_origin": bool(_try_run_git("remote", "get-url", "origin")),
        "execution_posture": _execution_posture(len(dirty_paths)),
        "authority_status": str(source_entry.get("authority_status") or ""),
        "review_status": str(source_entry.get("review_status") or ""),
        "default_disposition": str(source_entry.get("default_disposition") or ""),
        "preservation_status": str(source_entry.get("preservation_status") or ""),
        "dirty_file_count": len(dirty_paths),
        "tracked_dirty_count": len(tracked_dirty_paths),
        "untracked_count": len(untracked_paths),
        "dirty_paths": dirty_paths,
        "tracked_dirty_paths": tracked_dirty_paths,
        "untracked_paths": untracked_paths,
        "bucket_counts": {bucket: len(paths) for bucket, paths in buckets.items()},
        "bucket_group_counts": {bucket: _group_counts(paths) for bucket, paths in buckets.items()},
        "buckets": buckets,
        "recommended_tranche_order": [
            "repo_contracts_and_meta",
            "canonical_project_data",
            "generators_and_importers",
            "workbook_outputs",
            "docs_and_runbooks",
            "operator_residue",
        ],
        "validation_commands": VALIDATION_COMMANDS,
        "rules": [
            "Treat C:\\RFI & HERS Rater Assistant as the only repo-backed authority candidate in the family.",
            "Keep all C:\\CodexBuild\\rfi-hers-rater-assistant* variants governed by the duplicate-evidence packet, not as replay sources.",
            "Stabilize canonical project data and the scripts that generate or import workbook surfaces before treating workbook artifacts as final.",
            "Leave operator residue and stray agent-contract files for the last tranche; they do not outrank canonical data or generator stabilization.",
            "Use scripts/codex/validate-safe.ps1 when Windows path behavior blocks local validation in the root workspace.",
        ],
        "completion_condition": [
            "The primary root remains the only governed repo-backed authority candidate for the family.",
            "Dirty root changes are bucketed, preserved, and validated through the documented stabilization sequence instead of remaining as an unstructured dirty workspace.",
        ],
        "linked_packets": [
            "docs/operations/RFI-HERS-DUPLICATE-EVIDENCE-PACKET.md",
            "docs/operations/ATHANOR-TENANT-QUEUE.md",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
