#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "current-tree-partition.json"

CATEGORY_ACTIONS = {
    "source_commit_candidates": "Keep. Split into source/test commits and verify with the owning test suite.",
    "registry_truth_changes": "Keep. Commit only with registry/report validator proof.",
    "generated_truth_artifacts": "Keep if produced by current generators; otherwise regenerate or drop from the slice.",
    "runtime_gated_changes": "Keep out of blind commits. Review as runtime/deploy packet work before landing.",
    "content_output_review": "Keep pending operator/product review; externalize bulky binary assets if the repo contract requires it.",
    "local_generated_noise": "Do not commit. Ignore, prune, or regenerate from source.",
    "archive_or_prune_review": "Review against archive criteria; keep only audit/recovery/live-runbook value.",
    "manual_review": "Review manually before staging.",
}

PROGRAM_OWNED_PATHS = {
    "scripts/run_ralph_loop_pass.py",
    "scripts/tests/test_ralph_loop_contracts.py",
    "scripts/write_steady_state_status.py",
    "scripts/tests/test_write_steady_state_status.py",
    "scripts/write_current_tree_partition.py",
    "scripts/tests/test_write_current_tree_partition.py",
    "scripts/write_value_throughput_scorecard.py",
    "scripts/tests/test_write_value_throughput_scorecard.py",
    "projects/dashboard/src/lib/operator-summary.ts",
    "projects/dashboard/src/lib/value-throughput.test.ts",
    "projects/dashboard/src/lib/value-throughput.ts",
    "projects/dashboard/src/app/api/operator/summary/route.test.ts",
    "projects/dashboard/src/features/operator/operator-console.tsx",
    "projects/dashboard/src/features/operator/operator-console.test.tsx",
    "projects/dashboard/src/features/overview/command-center.tsx",
    "projects/dashboard/src/features/overview/command-center.test.tsx",
}

LOCAL_GENERATED_PREFIXES = (
    ".data/",
    "audit/automation/",
    "tests/ui-audit/",
)

RUNTIME_GATED_PREFIXES = (
    "ansible/",
)

RUNTIME_GATED_PATH_PREFIXES = (
    "docs/operations/VAULT-",
    "docs/operations/WORKSHOP-",
    "docs/operations/OPENCLAW-",
    "docs/operations/RUNTIME-OWNERSHIP",
    "docs/operations/CONTROL-PLANE-DEPLOY",
    "scripts/deploy-",
)

SOURCE_PREFIXES = (
    "projects/agents/",
    "projects/dashboard/",
    "projects/eoq/scripts/",
    "evals/",
    "scripts/",
)

GENERATED_TRUTH_PREFIXES = (
    "docs/operations/",
    "docs/projects/",
)

GENERATED_TRUTH_PATHS = {
    "docs/DOCUMENTATION-INDEX.md",
    "docs/SERVICES.md",
    "docs/SYSTEM-SPEC.md",
    "docs/architecture/ATHANOR-ECOSYSTEM-SYSTEM-BIBLE.md",
    "docs/design/project-platform-architecture.md",
}

GENERATED_RUNTIME_SUFFIXES = (
    "-REPORT.md",
)

GENERATED_RUNTIME_PATHS = {
    "docs/operations/REPO-ROOTS-REPORT.md",
    "docs/operations/RUNTIME-OWNERSHIP-REPORT.md",
    "docs/operations/RUNTIME-OWNERSHIP-PACKETS.md",
    "audit/automation/contract-healer-latest.json",
}


def _run_git_status() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain=1", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_status_entries(porcelain: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw_line in porcelain.splitlines():
        if not raw_line.strip():
            continue
        index_status = raw_line[0]
        worktree_status = raw_line[1]
        path_text = raw_line[3:].strip()
        if " -> " in path_text:
            _, path_text = path_text.split(" -> ", 1)
        entries.append(
            {
                "path": path_text,
                "index_status": index_status,
                "worktree_status": worktree_status,
                "tracked": not (index_status == "?" and worktree_status == "?"),
            }
        )
    return entries


def classify_path(path: str) -> str:
    normalized = str(path or "").strip()
    if normalized.startswith(LOCAL_GENERATED_PREFIXES):
        return "local_generated_noise"
    if normalized.startswith(RUNTIME_GATED_PREFIXES) or normalized.startswith(RUNTIME_GATED_PATH_PREFIXES):
        return "runtime_gated_changes"
    if normalized.startswith("projects/eoq/NEW/"):
        return "content_output_review"
    if normalized.startswith("docs/archive/"):
        return "archive_or_prune_review"
    if normalized in PROGRAM_OWNED_PATHS or normalized.startswith(SOURCE_PREFIXES):
        return "source_commit_candidates"
    if normalized.startswith("config/automation-backbone/"):
        return "registry_truth_changes"
    if normalized in GENERATED_RUNTIME_PATHS or normalized in GENERATED_TRUTH_PATHS:
        return "generated_truth_artifacts"
    if normalized.startswith(GENERATED_TRUTH_PREFIXES):
        return "generated_truth_artifacts"
    if normalized.endswith(GENERATED_RUNTIME_SUFFIXES):
        return "generated_truth_artifacts"
    return "manual_review"


def build_payload(entries: list[dict[str, Any]]) -> dict[str, Any]:
    classification_counts = {category: 0 for category in CATEGORY_ACTIONS}
    paths: list[dict[str, Any]] = []
    commit_candidate_paths: list[str] = []
    runtime_gated_paths: list[str] = []
    local_noise_paths: list[str] = []
    content_output_paths: list[str] = []
    seen: dict[str, set[str]] = {
        "commit": set(),
        "runtime": set(),
        "noise": set(),
        "content": set(),
    }

    for entry in entries:
        path = str(entry.get("path") or "").strip()
        classification = classify_path(path)
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        if classification in {
            "source_commit_candidates",
            "registry_truth_changes",
            "generated_truth_artifacts",
        } and path not in seen["commit"]:
            seen["commit"].add(path)
            commit_candidate_paths.append(path)
        if classification == "runtime_gated_changes" and path not in seen["runtime"]:
            seen["runtime"].add(path)
            runtime_gated_paths.append(path)
        if classification == "local_generated_noise" and path not in seen["noise"]:
            seen["noise"].add(path)
            local_noise_paths.append(path)
        if classification == "content_output_review" and path not in seen["content"]:
            seen["content"].add(path)
            content_output_paths.append(path)
        paths.append(
            {
                "path": path,
                "index_status": str(entry.get("index_status") or " "),
                "worktree_status": str(entry.get("worktree_status") or " "),
                "tracked": bool(entry.get("tracked", False)),
                "classification": classification,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "dirty_path_count": len(paths),
        "classification_counts": classification_counts,
        "recommended_actions": CATEGORY_ACTIONS,
        "recommended_execution_lane": "partition_then_land_verified_slices",
        "commit_candidate_paths": commit_candidate_paths,
        "runtime_gated_paths": runtime_gated_paths,
        "local_generated_noise_paths": local_noise_paths,
        "content_output_review_paths": content_output_paths,
        "overlap_status": "explicit_partition_required_before_staging",
        "paths": sorted(paths, key=lambda item: item["path"]),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Partition the current Athanor dirty tree into explicit ownership classes.")
    parser.add_argument("--json", action="store_true", help="Print the partition payload to stdout instead of only writing the report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(parse_status_entries(_run_git_status()))
    _write_json(OUTPUT_PATH, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
