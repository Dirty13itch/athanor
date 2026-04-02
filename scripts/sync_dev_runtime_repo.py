from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "dev"
DEFAULT_REMOTE_REPO = "/home/shaun/repos/athanor"
DEFAULT_BACKUP_ROOT = "/home/shaun/.athanor/backups/runtime-ownership/runtime-repo-sync"
DEFAULT_RETENTION_COUNT = 3
DEFAULT_RESTART_UNITS = [
    "athanor-brain.service",
    "athanor-classifier.service",
    "athanor-quality-gate.service",
    "athanor-sentinel.service",
    "athanor-overnight.service",
]


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        capture_output=capture_output,
        check=True,
    )


def _git_status_lines() -> list[str]:
    result = _run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _ensure_clean_worktree() -> None:
    status_lines = _git_status_lines()
    if status_lines:
        preview = "\n".join(status_lines[:20])
        raise SystemExit(
            "Local implementation authority must be commit-clean before syncing DEV.\n"
            f"Working tree still has {len(status_lines)} changes.\n"
            f"{preview}"
        )


def _git_head() -> str:
    result = _run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True)
    return result.stdout.strip()


def _push_temp_ref(remote: str, remote_repo: str, head_sha: str, temp_branch: str) -> None:
    remote_url = f"ssh://{remote}{remote_repo}/.git"
    _run(["git", "push", remote_url, f"{head_sha}:refs/heads/{temp_branch}"], cwd=REPO_ROOT)


def _remote_sync_script() -> str:
    return r"""#!/usr/bin/env bash
set -euo pipefail

repo_path="$1"
temp_branch="$2"
backup_branch="$3"
backup_root="$4"
restart_units_csv="$5"
restart_flag="$6"
sync_timestamp="$7"
retention_count="$8"
cleanup_only="$9"

backup_parent="$(dirname "$backup_root")"
cd "$repo_path"

prune_sync_artifacts() {
  local keep_count="$1"
  local pruned_sync_branches=0
  local pruned_backup_branches=0
  local pruned_backup_dirs=0

  mapfile -t sync_branches < <(git for-each-ref --format='%(refname:short)' --sort=-creatordate refs/heads/runtime-sync)
  for branch in "${sync_branches[@]}"; do
    [[ -n "$branch" ]] || continue
    git branch -D "$branch" >/dev/null
    pruned_sync_branches=$((pruned_sync_branches + 1))
  done

  mapfile -t backup_branches < <(git for-each-ref --format='%(refname:short)' --sort=-creatordate refs/heads/backup/runtime-sync-)
  for idx in "${!backup_branches[@]}"; do
    if (( idx >= keep_count )); then
      git branch -D "${backup_branches[$idx]}" >/dev/null
      pruned_backup_branches=$((pruned_backup_branches + 1))
    fi
  done

  if [[ -d "$backup_parent" ]]; then
    mapfile -t backup_dirs < <(find "$backup_parent" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort -r)
    for idx in "${!backup_dirs[@]}"; do
      if (( idx >= keep_count )); then
        rm -rf -- "$backup_parent/${backup_dirs[$idx]}"
        pruned_backup_dirs=$((pruned_backup_dirs + 1))
      fi
    done
  fi

  printf 'pruned_sync_branches=%s\n' "$pruned_sync_branches"
  printf 'pruned_backup_branches=%s\n' "$pruned_backup_branches"
  printf 'pruned_backup_dirs=%s\n' "$pruned_backup_dirs"
}

if [[ "$cleanup_only" == "1" ]]; then
  prune_sync_artifacts "$retention_count"
  printf 'branch=%s\n' "$(git branch --show-current)"
  printf 'head=%s\n' "$(git rev-parse --short HEAD)"
  printf 'dirty=%s\n' "$(git status --porcelain | wc -l)"
  exit 0
fi

mkdir -p "$backup_root"

git status --short > "$backup_root/git-status.before.txt"
git rev-parse --short HEAD > "$backup_root/head.before.txt"
tar --warning=no-file-changed --exclude='.git' -czf "$backup_root/runtime-repo.before.tar.gz" .

current_branch="$(git branch --show-current || true)"
if [[ "$current_branch" != "main" ]]; then
  git switch main >/dev/null
fi

git switch -c "$backup_branch" >/dev/null 2>&1 || git switch "$backup_branch" >/dev/null

if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  GIT_AUTHOR_NAME="Athanor Runtime Backup" \
  GIT_AUTHOR_EMAIL="runtime-backup@athanor.local" \
  GIT_COMMITTER_NAME="Athanor Runtime Backup" \
  GIT_COMMITTER_EMAIL="runtime-backup@athanor.local" \
    git commit -m "Backup before runtime repo sync $sync_timestamp" >/dev/null
fi

git switch main >/dev/null
git reset --hard "$temp_branch" >/dev/null
git clean -fd >/dev/null

git status --short > "$backup_root/git-status.after.txt"
git rev-parse --short HEAD > "$backup_root/head.after.txt"

if [[ "$restart_flag" == "1" ]]; then
  IFS=',' read -r -a restart_units <<< "$restart_units_csv"
  for unit in "${restart_units[@]}"; do
    systemctl restart "$unit"
  done
  systemctl is-active "${restart_units[@]}" > "$backup_root/systemd.after.txt"
fi

prune_sync_artifacts "$retention_count"
printf 'branch=%s\n' "$(git branch --show-current)"
printf 'head=%s\n' "$(git rev-parse --short HEAD)"
printf 'dirty=%s\n' "$(git status --porcelain | wc -l)"
""".replace("\r\n", "\n")


def _execute_remote_sync(
    *,
    remote: str,
    remote_repo: str,
    temp_branch: str,
    backup_branch: str,
    backup_root: str,
    restart_units: list[str],
    restart_services: bool,
    timestamp: str,
    retention_count: int,
    cleanup_only: bool,
) -> str:
    remote_script = _remote_sync_script()
    command = [
        "ssh",
        remote,
        "bash",
        "-s",
        "--",
        remote_repo,
        temp_branch,
        backup_branch,
        backup_root,
        ",".join(restart_units),
        "1" if restart_services else "0",
        timestamp,
        str(retention_count),
        "1" if cleanup_only else "0",
    ]
    try:
        result = subprocess.run(
            command,
            input=remote_script.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip() if exc.stderr else ""
        stdout = exc.stdout.decode("utf-8", errors="replace").strip() if exc.stdout else ""
        raise SystemExit(
            "Remote DEV repo sync failed.\n"
            f"stdout:\n{stdout or '<empty>'}\n"
            f"stderr:\n{stderr or '<empty>'}"
        ) from exc
    return result.stdout.decode("utf-8", errors="replace").strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mirror a clean implementation-authority commit into the DEV runtime repo."
    )
    parser.add_argument("--execute", action="store_true", help="Perform the sync. Without this flag the script prints the plan only.")
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Prune old DEV runtime-sync refs and backup artifacts without performing a mirror reset.",
    )
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--remote-repo", default=DEFAULT_REMOTE_REPO)
    parser.add_argument("--backup-root", default=DEFAULT_BACKUP_ROOT)
    parser.add_argument(
        "--retention-count",
        type=int,
        default=DEFAULT_RETENTION_COUNT,
        help="Number of backup branches and backup directories to retain on DEV.",
    )
    parser.add_argument("--restart-services", action="store_true", help="Restart repo-root services after the sync.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.retention_count < 0:
        raise SystemExit("--retention-count must be >= 0")
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    head_sha = _git_head()
    short_sha = head_sha[:12]
    temp_branch = f"runtime-sync/{timestamp}-{short_sha}"
    backup_branch = f"backup/runtime-sync-{timestamp}"
    backup_root = f"{args.backup_root}/{timestamp}"

    print(f"local_head={short_sha}")
    print(f"remote={args.remote}")
    print(f"remote_repo={args.remote_repo}")
    print(f"temp_branch={temp_branch}")
    print(f"backup_branch={backup_branch}")
    print(f"backup_root={backup_root}")
    print(f"cleanup_only={args.cleanup_only}")
    print(f"retention_count={args.retention_count}")
    print(f"restart_services={args.restart_services}")
    print(f"restart_units={','.join(DEFAULT_RESTART_UNITS)}")

    if not args.execute:
        print("dry_run=true")
        return 0

    if not args.cleanup_only:
        _ensure_clean_worktree()
        _push_temp_ref(args.remote, args.remote_repo, head_sha, temp_branch)
    summary = _execute_remote_sync(
        remote=args.remote,
        remote_repo=args.remote_repo,
        temp_branch=temp_branch,
        backup_branch=backup_branch,
        backup_root=backup_root,
        restart_units=DEFAULT_RESTART_UNITS,
        restart_services=args.restart_services,
        timestamp=timestamp,
        retention_count=args.retention_count,
        cleanup_only=args.cleanup_only,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
