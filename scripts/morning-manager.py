#!/usr/bin/env python3
"""Morning Manager — scheduled Claude Code CLI session for daily planning.

Runs at 07:00 via cron (DEV). Uses Claude Code CLI (`-p`, Opus) via 20x Max subscription.

Workflow:
1. Read STATUS.md and BUILD-MANIFEST.md
2. Fetch pipeline status and overnight results
3. Review pending approval plans
4. Decompose complex items into milestones and execution leases
5. Review overnight local worker outputs and score quality
6. Update STATUS.md, commit and push

Usage:
    python3 scripts/morning-manager.py [--dry-run]
"""

import argparse
import json
import logging
import subprocess
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_SERVER = get_url("agent_server")
BEARER_TOKEN = os.environ.get("ATHANOR_AGENT_API_TOKEN", "")


def fetch_json(path: str) -> dict:
    """Fetch JSON from the agent server."""
    try:
        headers = {"Accept": "application/json"}
        if BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
        req = Request(f"{AGENT_SERVER}{path}", headers=headers)
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError) as e:
        logger.warning("Failed to fetch %s: %s", path, e)
        return {}


def read_file(path: str) -> str:
    """Read a local file."""
    p = REPO_ROOT / path
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")[:8000]
    return f"[File not found: {path}]"


def build_morning_prompt() -> str:
    """Build the morning planning prompt from live system state."""
    status = read_file("STATUS.md")
    manifest = read_file("docs/BUILD-MANIFEST.md")

    pipeline = fetch_json("/v1/pipeline/status")
    pending_tasks = fetch_json("/v1/tasks?status=pending_approval&limit=20")
    pending_plans = fetch_json("/v1/plans?status=pending")
    stalled = fetch_json("/v1/projects/stalled")
    recent = fetch_json("/v1/activity?limit=30")
    governor = fetch_json("/v1/governor")

    prompt = f"""You are the Athanor morning manager. Review overnight work and plan today.

## Current STATUS.md
{status}

## BUILD-MANIFEST.md (first 4000 chars)
{manifest[:4000]}

## Governor State
{json.dumps(governor, indent=2)[:2000]}

## Pipeline Status
{json.dumps(pipeline, indent=2)[:1000]}

## Pending Approval Tasks ({len(pending_tasks.get('tasks', []))})
{json.dumps(pending_tasks, indent=2)[:2000]}

## Pending Plans ({len(pending_plans.get('plans', []))})
{json.dumps(pending_plans, indent=2)[:2000]}

## Stalled Projects
{json.dumps(stalled, indent=2)[:500]}

## Recent Activity (last 30)
{json.dumps(recent, indent=2)[:3000]}

## Your Tasks
1. Review overnight results — summarize what agents accomplished
2. Review pending approval tasks — approve safe ones, note risky ones for Shaun
3. Review pending plans — approve low-risk, flag high-risk for operator review
4. Check stalled projects — identify blockers, suggest remediation
5. Identify the top 3 priorities for today based on BUILD-MANIFEST and STATUS
6. Update STATUS.md with morning review notes and today's priorities

Output a structured morning briefing with:
- Overnight summary (1-2 paragraphs)
- Actions taken (approvals, rejections)
- Today's top 3 priorities
- Any items requiring Shaun's attention
- Updated STATUS.md content (if changes needed)
"""
    return prompt


def run_claude_session(prompt: str, dry_run: bool = False) -> dict:
    """Run Claude Code CLI in headless mode."""
    if dry_run:
        logger.info("DRY RUN — would send prompt (%d chars) to Claude Code CLI", len(prompt))
        return {"dry_run": True, "prompt_length": len(prompt)}

    try:
        result = subprocess.run(
            [
                "claude", "-p", prompt,
                "--output-format", "json",
                "--model", "opus",
                "--allowedTools", "Read,Bash",
            ],
            capture_output=True, text=True, timeout=600,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"text": result.stdout[:4000]}
        else:
            logger.error("Claude CLI failed: %s", result.stderr[:500])
            return {"error": result.stderr[:500]}
    except FileNotFoundError:
        logger.error("Claude Code CLI not found. Install: npm i -g @anthropic-ai/claude-code")
        return {"error": "CLI not installed"}
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out after 600s")
        return {"error": "timeout"}


def record_session(result: dict):
    """Record the session result to the agent server."""
    try:
        data = json.dumps({
            "session_type": "morning",
            "cli_tool": "claude_code",
            "model": "opus",
            "result_summary": str(result)[:2000],
            "timestamp": time.time(),
        }).encode()
        headers = {"Content-Type": "application/json"}
        if BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
        req = Request(
            f"{AGENT_SERVER}/v1/subscriptions/leases",
            data=data,
            headers=headers,
            method="POST",
        )
        urlopen(req, timeout=10)
    except Exception as e:
        logger.debug("Failed to record session: %s", e)


def main():
    parser = argparse.ArgumentParser(description="Morning manager — Claude Code CLI session")
    parser.add_argument("--dry-run", action="store_true", help="Build prompt but don't run CLI")
    args = parser.parse_args()

    logger.info("Morning manager starting")
    prompt = build_morning_prompt()
    logger.info("Prompt built: %d chars", len(prompt))

    result = run_claude_session(prompt, dry_run=args.dry_run)
    record_session(result)

    if "error" in result:
        logger.error("Session failed: %s", result["error"])
        sys.exit(1)

    logger.info("Morning manager complete")


if __name__ == "__main__":
    main()
