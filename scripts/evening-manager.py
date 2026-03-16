#!/usr/bin/env python3
"""Evening Manager — scheduled Claude Code CLI session for daily review.

Runs at 20:00 via cron (DEV). Uses Claude Code CLI (`-p`, Sonnet) via 20x Max subscription.

Workflow:
1. Review day's activity and outputs
2. Score task quality on high-priority completed tasks
3. Record preferences for learning loop
4. Check stalled projects, adjust milestones
5. Update STATUS.md, commit and push

Usage:
    python3 scripts/evening-manager.py [--dry-run]
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_SERVER = os.environ.get("ATHANOR_AGENT_URL", "http://192.168.1.244:9000")
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
    p = REPO_ROOT / path
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")[:8000]
    return f"[File not found: {path}]"


def build_evening_prompt() -> str:
    """Build the evening review prompt from live system state."""
    status = read_file("STATUS.md")

    recent = fetch_json("/v1/activity?limit=50")
    completed = fetch_json("/v1/tasks?status=completed&limit=30")
    failed = fetch_json("/v1/tasks?status=failed&limit=10")
    stalled = fetch_json("/v1/projects/stalled")
    pipeline = fetch_json("/v1/pipeline/status")
    improvement = fetch_json("/v1/improvement/summary")

    prompt = f"""You are the Athanor evening reviewer. Review the day's work, score quality, and prepare for tomorrow.

## Current STATUS.md
{status}

## Pipeline Status
{json.dumps(pipeline, indent=2)[:1000]}

## Completed Tasks Today ({len(completed.get('tasks', []))})
{json.dumps(completed, indent=2)[:3000]}

## Failed Tasks ({len(failed.get('tasks', []))})
{json.dumps(failed, indent=2)[:1500]}

## Stalled Projects
{json.dumps(stalled, indent=2)[:500]}

## Improvement Summary
{json.dumps(improvement, indent=2)[:1000]}

## Recent Activity (last 50)
{json.dumps(recent, indent=2)[:3000]}

## Your Tasks
1. Summarize the day's accomplishments (what did agents produce?)
2. Identify the 3 best and 3 worst task outcomes — explain why
3. Check failed tasks — is there a pattern? Should any be retried?
4. Check stalled projects — suggest unblocking actions
5. Score overall system productivity (1-10) with reasoning
6. Prepare tomorrow's priorities
7. Update STATUS.md with evening review notes

Output a structured evening review with:
- Day summary (1-2 paragraphs)
- Top 3 accomplishments
- Top 3 issues/failures
- System productivity score (1-10)
- Tomorrow's recommended priorities
- Updated STATUS.md content
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
                "--model", "sonnet",
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
        logger.error("Claude Code CLI not found")
        return {"error": "CLI not installed"}
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out after 600s")
        return {"error": "timeout"}


def record_session(result: dict):
    """Record the session result to the agent server."""
    try:
        data = json.dumps({
            "session_type": "evening",
            "cli_tool": "claude_code",
            "model": "sonnet",
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
    parser = argparse.ArgumentParser(description="Evening manager — Claude Code CLI session")
    parser.add_argument("--dry-run", action="store_true", help="Build prompt but don't run CLI")
    args = parser.parse_args()

    logger.info("Evening manager starting")
    prompt = build_evening_prompt()
    logger.info("Prompt built: %d chars", len(prompt))

    result = run_claude_session(prompt, dry_run=args.dry_run)
    record_session(result)

    if "error" in result:
        logger.error("Session failed: %s", result["error"])
        sys.exit(1)

    logger.info("Evening manager complete")


if __name__ == "__main__":
    main()
