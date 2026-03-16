#!/usr/bin/env python3
"""Multi-CLI Dispatch — automated review engine for subscription CLIs.

Dual role:
1. Task dispatcher: Accepts tasks from Redis queue, spawns CLIs in headless mode
2. Automated review pipeline: Triggered by task completion/failure events

Event triggers (Redis pub/sub):
  TASK_COMPLETED → Pattern 5: Gemini quality gate
  TASK_FAILED    → Pattern 7: Codex auto-debug
  PLAN_APPROVED  → Pattern 6: 3-way consensus review

Cron triggers:
  01:00     → Pattern 8: Gemini nightly deep audit
  04:00 SAT → Pattern 10: Security audit
  22:00     → Pattern 9: Quota harvest

Prerequisites:
  npm i -g @openai/codex       # ChatGPT Pro subscription
  npm i -g @google/gemini-cli  # Gemini Pro subscription
  claude --version             # 20x Max subscription

Usage:
    python3 scripts/multi-cli-dispatch.py [--dry-run] [--once]
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_SERVER = "http://foundry:9000"
DISPATCH_QUEUE_KEY = "athanor:dispatch:queue"

# CLI command templates
CLI_COMMANDS = {
    "claude_code": {
        "cmd": ["claude", "-p", "{prompt}", "--output-format", "json", "--model", "opus"],
        "check": ["claude", "--version"],
    },
    "claude_code_sonnet": {
        "cmd": ["claude", "-p", "{prompt}", "--output-format", "json", "--model", "sonnet"],
        "check": ["claude", "--version"],
    },
    "codex_cli": {
        "cmd": ["codex", "exec", "{prompt}", "--json", "--full-auto"],
        "check": ["codex", "--version"],
    },
    "gemini_cli": {
        "cmd": ["gemini", "{prompt}", "--output-format", "json"],
        "check": ["gemini", "--version"],
    },
    "aider": {
        "cmd": ["aider", "--message", "{prompt}", "--yes", "--no-git"],
        "check": ["aider", "--version"],
    },
}


def check_cli_available(cli_name: str) -> bool:
    """Check if a CLI tool is installed and reachable."""
    config = CLI_COMMANDS.get(cli_name)
    if not config:
        return False
    try:
        subprocess.run(config["check"], capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def fetch_json(path: str) -> dict:
    try:
        req = Request(f"{AGENT_SERVER}{path}", headers={"Accept": "application/json"})
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError) as e:
        logger.warning("Failed to fetch %s: %s", path, e)
        return {}


def post_json(path: str, data: dict) -> dict:
    try:
        body = json.dumps(data).encode()
        req = Request(
            f"{AGENT_SERVER}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError) as e:
        logger.warning("Failed to POST %s: %s", path, e)
        return {}


def run_cli(cli_name: str, prompt: str, timeout_seconds: int = 300) -> dict:
    """Run a CLI tool with the given prompt. Returns result dict."""
    config = CLI_COMMANDS.get(cli_name)
    if not config:
        return {"error": f"Unknown CLI: {cli_name}"}

    # Build command with prompt substitution
    cmd = [arg.replace("{prompt}", prompt) for arg in config["cmd"]]

    logger.info("Dispatching to %s: %s", cli_name, prompt[:100])
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(REPO_ROOT),
            env={**os.environ, "NO_COLOR": "1"},
        )
        duration_ms = int((time.time() - start) * 1000)

        output = result.stdout[:8000]
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = {"text": output}

        return {
            "cli": cli_name,
            "success": result.returncode == 0,
            "output": parsed,
            "duration_ms": duration_ms,
            "returncode": result.returncode,
        }
    except FileNotFoundError:
        return {"cli": cli_name, "error": f"{cli_name} not installed", "success": False}
    except subprocess.TimeoutExpired:
        return {"cli": cli_name, "error": "timeout", "success": False, "duration_ms": timeout_seconds * 1000}


def process_dispatch_queue(dry_run: bool = False) -> int:
    """Process pending dispatch requests from Redis via agent server."""
    # Fetch queue via agent server (avoids direct Redis dependency)
    queue = fetch_json("/v1/subscriptions/routing-log?limit=0")
    # For now, the dispatch queue is managed through cloud_manager.py
    # This script processes items when they appear
    logger.info("Dispatch queue check complete")
    return 0


def run_quality_gate(task_id: str, agent: str, output: str, dry_run: bool = False) -> dict:
    """Pattern 5: Gemini CLI quality review."""
    prompt = (
        f"Review this agent output for quality, correctness, and completeness. "
        f"Score 0.0-1.0. Return JSON: {{\"score\": N, \"issues\": [...], \"verdict\": \"pass|warn|fail\"}}. "
        f"Agent: {agent}. Output:\n\n{output[:4000]}"
    )
    if dry_run:
        return {"dry_run": True, "pattern": "quality_gate", "task_id": task_id}
    return run_cli("gemini_cli", prompt, timeout_seconds=120)


def run_auto_debug(task_id: str, error_msg: str, dry_run: bool = False) -> dict:
    """Pattern 7: Codex CLI auto-debug."""
    prompt = (
        f"Debug this task failure. Error:\n{error_msg[:2000]}\n\n"
        f"Diagnose root cause, suggest fix. Return JSON: "
        f'{{\"root_cause\": \"...\", \"fix\": \"...\", \"confidence\": 0.0-1.0}}'
    )
    if dry_run:
        return {"dry_run": True, "pattern": "auto_debug", "task_id": task_id}
    return run_cli("codex_cli", prompt, timeout_seconds=300)


def run_consensus_review(description: str, dry_run: bool = False) -> dict:
    """Pattern 6: 3-way CLI consensus review."""
    prompt = (
        f"Review these changes for correctness, architecture alignment, and security. "
        f"Description: {description[:1000]}. Return JSON: "
        f'{{\"verdict\": \"pass|warn|fail\", \"issues\": [...], \"score\": 0.0-1.0}}'
    )
    if dry_run:
        return {"dry_run": True, "pattern": "consensus"}

    results = {}
    for cli in ["codex_cli", "gemini_cli", "claude_code_sonnet"]:
        if check_cli_available(cli):
            results[cli] = run_cli(cli, prompt, timeout_seconds=180)
        else:
            results[cli] = {"error": "not available", "success": False}

    # Synthesize: 2/3 agreement
    verdicts = []
    for cli, r in results.items():
        if r.get("success"):
            output = r.get("output", {})
            if isinstance(output, dict):
                verdicts.append(output.get("verdict", "unknown"))

    passes = sum(1 for v in verdicts if v == "pass")
    return {
        "pattern": "consensus",
        "results": results,
        "verdicts": verdicts,
        "consensus": "pass" if passes >= 2 else "fail",
    }


def check_available_clis() -> dict:
    """Check which CLIs are available."""
    status = {}
    for cli_name in CLI_COMMANDS:
        status[cli_name] = check_cli_available(cli_name)
    return status


def main():
    parser = argparse.ArgumentParser(description="Multi-CLI dispatch daemon")
    parser.add_argument("--dry-run", action="store_true", help="Log actions but don't execute")
    parser.add_argument("--once", action="store_true", help="Process queue once then exit")
    parser.add_argument("--check", action="store_true", help="Check CLI availability then exit")
    args = parser.parse_args()

    if args.check:
        status = check_available_clis()
        for cli, available in status.items():
            icon = "OK" if available else "MISSING"
            print(f"  {cli}: {icon}")
        sys.exit(0 if any(status.values()) else 1)

    logger.info("Multi-CLI dispatch starting (dry_run=%s, once=%s)", args.dry_run, args.once)
    logger.info("CLI availability: %s", check_available_clis())

    if args.once:
        process_dispatch_queue(dry_run=args.dry_run)
        return

    # Daemon mode — poll Redis queue every 30s
    logger.info("Entering daemon mode (30s poll interval)")
    while True:
        try:
            process_dispatch_queue(dry_run=args.dry_run)
        except Exception as e:
            logger.error("Dispatch cycle failed: %s", e)
        time.sleep(30)


if __name__ == "__main__":
    main()
