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
ECOSYSTEM_REGISTRY_PATH = REPO_ROOT / "docs" / "operations" / "ATHANOR-ECOSYSTEM-REGISTRY.md"
OUTPUT_PATH = REPO_ROOT / "reports" / "reconciliation" / "github-portfolio-latest.json"
GITHUB_OWNER = "Dirty13itch"


def _clean_cell(value: str) -> str:
    return re.sub(r"`([^`]+)`", r"\1", value).strip()


def _parse_batch_tables(markdown_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_batch: str | None = None
    table_headers: list[str] | None = None

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## Batch "):
            current_batch = line.removeprefix("## ").strip()
            table_headers = None
            continue
        if not line.startswith("|"):
            table_headers = None
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "Repo":
            table_headers = cells
            continue
        if all(set(cell) <= {"-", " "} for cell in cells):
            continue
        if not current_batch or not table_headers or len(cells) != len(table_headers):
            continue

        row = {header: _clean_cell(value) for header, value in zip(table_headers, cells)}
        repo_value = row.get("Repo", "")
        if not repo_value.startswith(f"{GITHUB_OWNER}/"):
            continue
        row["Batch"] = current_batch
        rows.append(row)

    return rows


def _github_repo_id(full_name: str) -> str:
    return full_name.split("/", 1)[1].lower().replace("_", "-")


def _fetch_live_repos() -> list[dict[str, Any]]:
    completed = subprocess.run(
        [
            "gh",
            "repo",
            "list",
            GITHUB_OWNER,
            "--limit",
            "200",
            "--json",
            "name,description,isPrivate,isFork,updatedAt,url",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"gh repo list failed: {completed.stderr.strip()}")
    payload = json.loads(completed.stdout)
    return [dict(item) for item in payload if isinstance(item, dict)]




def _is_github_auth_block(detail: str) -> bool:
    normalized = str(detail or "").lower()
    return any(
        marker in normalized
        for marker in (
            "http 401",
            "http 403",
            "bad credentials",
            "gh auth login",
            "requires authentication",
        )
    )


def _build_blocked_portfolio_snapshot(registry: dict[str, Any], reason: str) -> dict[str, Any]:
    existing_registry = registry.get("github_portfolio") if isinstance(registry.get("github_portfolio"), dict) else {}
    snapshot = dict(existing_registry or {})
    snapshot.setdefault("owner", GITHUB_OWNER)
    return snapshot

def _mirror_registry_rows(table_rows: list[dict[str, str]], live_repos: list[dict[str, Any]]) -> dict[str, Any]:
    live_by_name = {str(item["name"]): item for item in live_repos}
    doc_by_name = {row["Repo"].split("/", 1)[1]: row for row in table_rows}

    doc_names = set(doc_by_name)
    live_names = set(live_by_name)

    doc_only = sorted(doc_names - live_names)
    github_only = sorted(live_names - doc_names)

    mirrored_repos: list[dict[str, Any]] = []
    for name in sorted(doc_names | live_names, key=str.lower):
        row = doc_by_name.get(name)
        live = live_by_name.get(name)
        full_name = f"{GITHUB_OWNER}/{name}"
        mirrored_repos.append(
            {
                "id": f"github-{_github_repo_id(full_name)}",
                "github_repo": full_name,
                "name": name,
                "url": live["url"] if live else f"https://github.com/{full_name}",
                "description": (live or {}).get("description") or "",
                "is_private": bool((live or {}).get("isPrivate", False)),
                "is_fork": bool((live or {}).get("isFork", False)),
                "updated_at": (live or {}).get("updatedAt") or "",
                "ecosystem_role": row.get("Proposed role", "reference") if row else "reference",
                "working_clone": row.get("Working clone", "no registry row yet") if row else "no registry row yet",
                "current_maturity": row.get("Current maturity", "live GitHub repo without ecosystem row") if row else "live GitHub repo without ecosystem row",
                "likely_tenant_status": row.get("Likely tenant status", "n/a") if row else "n/a",
                "shared_extraction_potential": row.get("Shared extraction potential", "unknown") if row else "unknown",
                "depends_on_athanor": row.get("Depends on Athanor", "unknown") if row else "unknown",
                "athanor_depends_on_it": row.get("Athanor depends on it", "unknown") if row else "unknown",
                "batch": row.get("Batch", "Unclassified") if row else "Unclassified",
                "shaun_decision": row.get("Shaun decision", "needs ecosystem review") if row else "needs ecosystem review",
                "has_confirmed_local_clone": "no confirmed local clone" not in (row.get("Working clone", "").lower() if row else ""),
                "doc_classified": row is not None,
                "live_on_github": live is not None,
            }
        )

    role_counts = Counter(
        str(repo["ecosystem_role"])
        for repo in mirrored_repos
        if repo["doc_classified"]
    )
    batch_counts = Counter(
        str(repo["batch"])
        for repo in mirrored_repos
        if repo["doc_classified"]
    )
    repos_without_confirmed_local_clone = [
        repo["github_repo"]
        for repo in mirrored_repos
        if repo["doc_classified"] and not repo["has_confirmed_local_clone"]
    ]

    return {
        "owner": GITHUB_OWNER,
        "last_verified_at": datetime.now(timezone.utc).isoformat(),
        "repo_count": len(mirrored_repos),
        "doc_repo_count": len(doc_names),
        "live_repo_count": len(live_names),
        "doc_only_repos": [f"{GITHUB_OWNER}/{name}" for name in doc_only],
        "github_only_repos": [f"{GITHUB_OWNER}/{name}" for name in github_only],
        "repos_without_confirmed_local_clone": repos_without_confirmed_local_clone,
        "role_counts": dict(sorted(role_counts.items())),
        "batch_counts": dict(sorted(batch_counts.items())),
        "repos": mirrored_repos,
    }


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    table_rows = _parse_batch_tables(ECOSYSTEM_REGISTRY_PATH.read_text(encoding="utf-8"))
    try:
        live_repos = _fetch_live_repos()
    except RuntimeError as exc:
        detail = str(exc)
        if not _is_github_auth_block(detail):
            raise
        blocked_snapshot = _build_blocked_portfolio_snapshot(registry, detail.removeprefix("gh repo list failed:").strip())
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(blocked_snapshot, indent=2) + "\n", encoding="utf-8")
        print(f"GitHub portfolio sync external block: {detail.removeprefix('gh repo list failed:').strip()}")
        return 0

    github_portfolio = _mirror_registry_rows(table_rows, live_repos)
    github_portfolio["sync_status"] = "ok"

    registry["updated_at"] = github_portfolio["last_verified_at"]
    registry["github_portfolio"] = github_portfolio
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(github_portfolio, indent=2) + "\n", encoding="utf-8")

    print(
        "Synced GitHub portfolio mirror with "
        f"{github_portfolio['repo_count']} repos and "
        f"{len(github_portfolio['repos_without_confirmed_local_clone'])} repo(s) without confirmed local clone."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
