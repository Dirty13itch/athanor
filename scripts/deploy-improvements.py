#!/usr/bin/env python3
"""Deploy validated improvements to the Athanor agent server.

Reads improvement proposals (from self-improvement engine or manual JSON),
applies changes to agent prompts/configs, and optionally restarts the container.

Dry-run by default. Use --apply to actually deploy.

Usage:
    python3 scripts/deploy-improvements.py --input /tmp/proposals.json --dry-run
    python3 scripts/deploy-improvements.py --input /tmp/proposals.json --apply
    python3 scripts/deploy-improvements.py --input /tmp/proposals.json --apply --restart

Proposal JSON format:
    [
        {
            "id": "abc123",
            "title": "Improve general assistant prompt",
            "category": "prompt",
            "target_files": ["projects/agents/src/athanor_agents/agents/general.py"],
            "proposed_changes": {
                "projects/agents/src/athanor_agents/agents/general.py": "...new content..."
            },
            "expected_improvement": "Better helpfulness scores"
        }
    ]

Categories:
    prompt          — Update agent system prompts (auto-deployable)
    config          — Update config values (auto-deployable)
    code            — Code changes (requires --force)
    infrastructure  — Ansible/systemd changes (blocked, manual only)
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES

# Agent server on FOUNDRY
AGENT_HOST = NODES["foundry"]
AGENT_PORT = 9000
AGENT_DEPLOY_PATH = "/opt/athanor/agents/src/"

# Repo root — scripts/ is one level down
REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_SRC = REPO_ROOT / "projects" / "agents" / "src"

# Categories safe for auto-deploy
AUTO_DEPLOY = {"prompt", "config"}

# Audit log
AUDIT_DIR = REPO_ROOT / "logs" / "improvements"


def file_hash(path: Path) -> str:
    """SHA256 of a file's contents."""
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return "missing"


def validate_proposal(proposal: dict) -> list[str]:
    """Validate a proposal before applying. Returns list of errors."""
    errors = []

    if not proposal.get("id"):
        errors.append("Missing 'id' field")
    if not proposal.get("category"):
        errors.append("Missing 'category' field")
    if not proposal.get("target_files"):
        errors.append("Missing 'target_files' field")
    if not proposal.get("proposed_changes"):
        errors.append("Missing 'proposed_changes' field")

    category = proposal.get("category", "")
    if category == "infrastructure":
        errors.append(f"Category 'infrastructure' cannot be auto-deployed. Manual apply only.")

    for target_file in proposal.get("target_files", []):
        full_path = REPO_ROOT / target_file
        if not str(full_path).startswith(str(REPO_ROOT)):
            errors.append(f"Path traversal detected: {target_file}")

    # Syntax check for Python changes
    for file_path, content in proposal.get("proposed_changes", {}).items():
        if file_path.endswith(".py"):
            try:
                compile(content, file_path, "exec")
            except SyntaxError as e:
                errors.append(f"Syntax error in {file_path}: {e}")

    return errors


def backup_file(file_path: Path) -> Path | None:
    """Create a timestamped backup of a file."""
    if not file_path.exists():
        return None

    backup_dir = REPO_ROOT / "backups" / "improvements"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rel_name = file_path.relative_to(REPO_ROOT)
    safe_name = str(rel_name).replace("/", "__")
    backup_path = backup_dir / f"{safe_name}.{timestamp}.bak"

    shutil.copy2(file_path, backup_path)
    return backup_path


def apply_change(file_path: str, content: str, dry_run: bool) -> dict:
    """Apply a single file change. Returns change record."""
    full_path = REPO_ROOT / file_path

    record = {
        "file": file_path,
        "existed": full_path.exists(),
        "old_hash": file_hash(full_path),
        "dry_run": dry_run,
    }

    if dry_run:
        new_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        record["new_hash"] = new_hash
        record["changed"] = record["old_hash"] != new_hash
        record["status"] = "would_apply"
        return record

    # Create backup
    backup = backup_file(full_path)
    if backup:
        record["backup"] = str(backup.relative_to(REPO_ROOT))

    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write new content
    full_path.write_text(content)
    record["new_hash"] = file_hash(full_path)
    record["changed"] = record["old_hash"] != record["new_hash"]
    record["status"] = "applied"

    return record


def rsync_to_foundry(dry_run: bool) -> dict:
    """Rsync agent source to FOUNDRY."""
    if dry_run:
        return {"status": "would_rsync", "target": f"{AGENT_HOST}:{AGENT_DEPLOY_PATH}"}

    try:
        result = subprocess.run(
            [
                "rsync", "-az", "--delete",
                str(AGENTS_SRC) + "/",
                f"node1:{AGENT_DEPLOY_PATH}",
            ],
            capture_output=True, text=True, timeout=30,
        )
        return {
            "status": "synced" if result.returncode == 0 else "rsync_failed",
            "returncode": result.returncode,
            "stderr": result.stderr[:200] if result.stderr else "",
        }
    except Exception as e:
        return {"status": "rsync_error", "error": str(e)}


def restart_agent_container(dry_run: bool) -> dict:
    """Restart the agent container on FOUNDRY via SSH."""
    if dry_run:
        return {"status": "would_restart", "container": "athanor-agents"}

    try:
        result = subprocess.run(
            [
                "ssh", "node1",
                "cd /opt/athanor/agents && docker compose up -d --build --no-deps agents",
            ],
            capture_output=True, text=True, timeout=120,
        )
        return {
            "status": "restarted" if result.returncode == 0 else "restart_failed",
            "returncode": result.returncode,
            "stdout": result.stdout[:200] if result.stdout else "",
            "stderr": result.stderr[:200] if result.stderr else "",
        }
    except Exception as e:
        return {"status": "restart_error", "error": str(e)}


def write_audit_log(deployment: dict):
    """Write deployment record to audit log."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = AUDIT_DIR / f"deploy_{timestamp}.json"
    audit_file.write_text(json.dumps(deployment, indent=2, default=str))
    print(f"Audit log: {audit_file.relative_to(REPO_ROOT)}", file=sys.stderr)


def process_proposals(
    proposals: list[dict],
    dry_run: bool,
    force: bool,
    restart: bool,
) -> dict[str, Any]:
    """Process all improvement proposals."""
    deployment = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "force": force,
        "proposals_received": len(proposals),
        "results": [],
    }

    applied_any = False

    for proposal in proposals:
        proposal_id = proposal.get("id", "unknown")
        category = proposal.get("category", "unknown")

        print(f"\n--- Proposal {proposal_id}: {proposal.get('title', 'untitled')} ---", file=sys.stderr)
        print(f"  Category: {category}", file=sys.stderr)

        result = {
            "proposal_id": proposal_id,
            "title": proposal.get("title", ""),
            "category": category,
            "changes": [],
        }

        # Validate
        errors = validate_proposal(proposal)

        # Block non-auto-deploy categories unless forced
        if category not in AUTO_DEPLOY and not force:
            errors.append(
                f"Category '{category}' requires --force flag. "
                f"Only {AUTO_DEPLOY} are auto-deployable."
            )

        if errors:
            result["status"] = "rejected"
            result["errors"] = errors
            for e in errors:
                print(f"  REJECT: {e}", file=sys.stderr)
            deployment["results"].append(result)
            continue

        # Apply changes
        for file_path, content in proposal.get("proposed_changes", {}).items():
            print(f"  {'Would apply' if dry_run else 'Applying'}: {file_path}", file=sys.stderr)
            change = apply_change(file_path, content, dry_run)
            result["changes"].append(change)

            if change.get("changed"):
                applied_any = True
                status = change["status"]
                print(f"    {status} ({change['old_hash']} → {change['new_hash']})", file=sys.stderr)
            else:
                print(f"    No change (content identical)", file=sys.stderr)

        result["status"] = "applied" if not dry_run else "dry_run"
        deployment["results"].append(result)

    # Rsync + restart if changes were applied
    if applied_any and not dry_run:
        print("\nSyncing to FOUNDRY...", file=sys.stderr)
        deployment["rsync"] = rsync_to_foundry(dry_run)
        print(f"  {deployment['rsync']['status']}", file=sys.stderr)

        if restart:
            print("Restarting agent container...", file=sys.stderr)
            deployment["restart"] = restart_agent_container(dry_run)
            print(f"  {deployment['restart']['status']}", file=sys.stderr)
    elif dry_run and applied_any:
        deployment["rsync"] = rsync_to_foundry(dry_run=True)
        if restart:
            deployment["restart"] = restart_agent_container(dry_run=True)

    # Summary
    applied = sum(1 for r in deployment["results"] if r["status"] in ("applied", "dry_run"))
    rejected = sum(1 for r in deployment["results"] if r["status"] == "rejected")
    deployment["summary"] = {
        "applied": applied,
        "rejected": rejected,
        "total": len(proposals),
        "changes_made": applied_any,
    }

    print(f"\nSummary: {applied} applied, {rejected} rejected out of {len(proposals)}", file=sys.stderr)

    return deployment


def main():
    parser = argparse.ArgumentParser(
        description="Deploy validated improvements to the agent server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 scripts/deploy-improvements.py --input /tmp/proposals.json --dry-run
  python3 scripts/deploy-improvements.py --input /tmp/proposals.json --apply
  python3 scripts/deploy-improvements.py --input /tmp/proposals.json --apply --restart
  python3 scripts/deploy-improvements.py --input /tmp/proposals.json --apply --force  # code changes""",
    )
    parser.add_argument("--input", required=True, help="Proposals JSON file")
    parser.add_argument("--output", default="-", help="Output deployment report (- for stdout)")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying (default)")
    parser.add_argument("--restart", action="store_true", help="Restart agent container after deploying")
    parser.add_argument("--force", action="store_true", help="Allow non-auto-deployable categories (code)")
    args = parser.parse_args()

    dry_run = not args.apply

    # Read proposals
    with open(args.input) as f:
        raw = f.read()

    try:
        proposals = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Accept both a list of proposals and the self_improvement engine format
    if isinstance(proposals, dict):
        if "proposals" in proposals:
            proposals = proposals["proposals"]
        elif "improvement_suggestions" in proposals:
            proposals = proposals["improvement_suggestions"]
        else:
            proposals = [proposals]

    if not isinstance(proposals, list):
        print("ERROR: Input must be a JSON array of proposals", file=sys.stderr)
        sys.exit(1)

    mode = "DRY RUN" if dry_run else "LIVE DEPLOY"
    print(f"=== {mode} — {len(proposals)} proposals ===", file=sys.stderr)

    if not dry_run:
        print("WARNING: Changes will be applied to the codebase and synced to FOUNDRY.", file=sys.stderr)

    result = process_proposals(proposals, dry_run, args.force, args.restart)

    # Write audit log for actual deployments
    if not dry_run:
        write_audit_log(result)

    output = json.dumps(result, indent=2, default=str)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
