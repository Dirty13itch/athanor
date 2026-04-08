from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    REPO_ROOT / "reports" / "reconciliation" / "field-inspect-operations-runtime-replay-latest.json"
)
FIELD_INSPECT_ROOT = Path(r"C:\Field Inspect")
PRIMARY_BRANCH = "codex/perpetual-coo-loop"
REPLAY_BRANCH = "codex/reconcile-operations-runtime"

SAFE_RUNTIME_PREFIXES = (
    "src/app/(dashboard)/operations/",
    "src/app/api/work-intake/",
    "src/app/api/site-visits/",
    "src/components/dispatch/",
    "src/components/operations/",
    "src/components/schedules/",
    "src/lib/finance-closure-state.ts",
    "src/lib/operations-",
    "src/lib/ops-task-",
    "src/lib/owner-queue-state.ts",
    "src/lib/tomorrow-prep.ts",
    "src/lib/visit-execution-state.ts",
    "src/lib/work-intake-",
)
SHARED_PROJECT_HOLD_PREFIXES = (
    "src/app/(dashboard)/projects/",
    "src/app/api/shared-projects/",
    "src/components/projects/",
    "src/components/reports/",
    "src/app/shared-reports/",
    "src/lib/shared-project",
    "src/lib/report-",
    "src/lib/shared-report-links.ts",
)
SECONDARY_REVIEW_PREFIXES = (
    "src/app/api/admin/test-email/",
    "src/app/api/comments/",
    "src/app/api/organization/members/",
    "src/app/api/search/",
    "src/app/(dashboard)/reports/",
    "src/app/(dashboard)/settings/",
    "src/components/comments/",
    "src/components/layout/",
    "src/components/settings/",
    "src/lib/google-report-jobs.ts",
    "src/lib/observability-proof.ts",
    "src/lib/office-handoff-acceptance.ts",
    "src/lib/validators.ts",
)
DOCS_META_PREFIXES = (
    ".gitattributes",
    "docs/",
    "package-lock.json",
)
TARGETED_VALIDATION_COMMANDS = [
    "npm run typecheck",
    "npm run test:run -- src/lib/__tests__/operations-assignment-guidance.test.ts src/lib/__tests__/operations-orchestration.test.ts src/components/dispatch/__tests__/operations-work-intake-board.test.tsx src/components/operations/today/__tests__/today-view.test.tsx src/components/operations/week/__tests__/week-view.test.tsx",
]


def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(FIELD_INSPECT_ROOT), *args],
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


def _status_dirty_paths() -> list[str]:
    status_lines = _run_git("status", "--porcelain").splitlines()
    paths: list[str] = []
    for line in status_lines:
        cleaned = re.sub(r"^[ MARCUD?!]{1,3}", "", line).strip()
        if cleaned:
            paths.append(cleaned)
    return paths


def _matches_prefixes(path: str, prefixes: tuple[str, ...]) -> bool:
    return path.startswith(prefixes)


def _classify_path(path: str, overlap_paths: set[str]) -> str:
    if path in overlap_paths:
        return "blocked_overlap"
    if _matches_prefixes(path, DOCS_META_PREFIXES):
        return "docs_meta_reference"
    if _matches_prefixes(path, SHARED_PROJECT_HOLD_PREFIXES):
        return "shared_project_follow_through_hold"
    if _matches_prefixes(path, SAFE_RUNTIME_PREFIXES):
        return "safe_operations_runtime_replay"
    if _matches_prefixes(path, SECONDARY_REVIEW_PREFIXES):
        return "secondary_cross_surface_review"
    return "secondary_cross_surface_review"


def _group_counts(paths: list[str]) -> dict[str, int]:
    grouped = Counter()
    for path in paths:
        parts = path.split("/")
        grouped["/".join(parts[:3])] += 1
    return dict(sorted(grouped.items(), key=lambda item: (-item[1], item[0])))


def _execution_posture(overlap_paths: list[str], safe_runtime_overlap_paths: list[str]) -> str:
    if not overlap_paths:
        return "ready_for_safe_replay"
    if not safe_runtime_overlap_paths:
        return "ready_for_safe_runtime_only"
    return "blocked_by_overlap"


def main() -> int:
    dirty_paths = _status_dirty_paths()
    replay_paths = [
        path for path in _run_git("diff", "--name-only", f"{PRIMARY_BRANCH}..{REPLAY_BRANCH}").splitlines() if path
    ]
    overlap_paths = sorted(set(dirty_paths) & set(replay_paths))
    safe_runtime_overlap_paths = [
        path for path in overlap_paths if _matches_prefixes(path, SAFE_RUNTIME_PREFIXES)
    ]

    buckets: dict[str, list[str]] = {
        "safe_operations_runtime_replay": [],
        "shared_project_follow_through_hold": [],
        "secondary_cross_surface_review": [],
        "docs_meta_reference": [],
        "blocked_overlap": [],
    }
    for path in replay_paths:
        buckets[_classify_path(path, set(overlap_paths))].append(path)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "field_inspect_root": str(FIELD_INSPECT_ROOT),
        "primary_branch": PRIMARY_BRANCH,
        "primary_head": _run_git("rev-parse", "--short", PRIMARY_BRANCH),
        "replay_branch": REPLAY_BRANCH,
        "replay_head": _run_git("rev-parse", "--short", REPLAY_BRANCH),
        "execution_posture": _execution_posture(overlap_paths, safe_runtime_overlap_paths),
        "dirty_primary_paths": dirty_paths,
        "dirty_primary_count": len(dirty_paths),
        "replay_path_count": len(replay_paths),
        "overlap_paths": overlap_paths,
        "overlap_count": len(overlap_paths),
        "safe_runtime_overlap_paths": safe_runtime_overlap_paths,
        "safe_runtime_overlap_count": len(safe_runtime_overlap_paths),
        "bucket_counts": {bucket: len(paths) for bucket, paths in buckets.items()},
        "bucket_group_counts": {bucket: _group_counts(paths) for bucket, paths in buckets.items()},
        "buckets": buckets,
        "targeted_validation_commands": TARGETED_VALIDATION_COMMANDS,
        "rules": [
            "Do not merge codex/reconcile-operations-runtime wholesale into the primary root.",
            "Replay the safe operations-runtime tranche first in a dedicated review branch or worktree whenever execution_posture is ready_for_safe_replay or ready_for_safe_runtime_only.",
            "Keep every shared-project and report-delivery path in a coordinated second tranche even when overlap_count is zero.",
            "Treat docs and meta files as reference or follow-up material, not part of the first replay tranche.",
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
