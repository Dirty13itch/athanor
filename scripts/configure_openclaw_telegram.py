from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


OPENCLAW_PATH_EXPORT = 'export PATH="$HOME/.local/npm-global/bin:$PATH"; '
TELEGRAM_TOKEN_PATTERN = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{20,}$")
TELEGRAM_ID_PATTERN = re.compile(r"^-?\d+$")


def _run(args: list[str], *, input_text: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _require(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    detail = stderr or stdout or f"returncode={result.returncode}"
    raise RuntimeError(f"{action} failed: {detail}")


def _ssh(host: str, remote_command: str, *, input_text: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return _run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, "sh", "-lc", remote_command],
        input_text=input_text,
        timeout=timeout,
    )


def _parse_telegram_ids(values: list[str], label: str) -> list[int]:
    ids: list[int] = []
    for value in values:
        for item in value.split(","):
            stripped = item.strip()
            if not stripped:
                continue
            if not TELEGRAM_ID_PATTERN.fullmatch(stripped):
                raise ValueError(f"{label} must be numeric Telegram IDs, got {stripped!r}")
            ids.append(int(stripped))
    return ids


def _read_token(token_file: Path | None) -> str:
    if token_file:
        return token_file.read_text(encoding="utf-8").strip()
    return (os.environ.get("OPENCLAW_TELEGRAM_BOT_TOKEN") or "").strip()


def _patch_config_script(allow_from: list[int], approvers: list[int]) -> str:
    return f"""
import json
from pathlib import Path

config_path = Path.home() / ".openclaw" / "openclaw.json"
config = json.loads(config_path.read_text(encoding="utf-8"))

channels = config.setdefault("channels", {{}})
telegram = channels.setdefault("telegram", {{}})
telegram["enabled"] = True
telegram["dmPolicy"] = "allowlist"
telegram["groupPolicy"] = "allowlist"
telegram["allowFrom"] = {json.dumps(allow_from)}

groups = telegram.setdefault("groups", {{}})
wildcard = groups.setdefault("*", {{}})
wildcard["requireMention"] = True
wildcard["groupPolicy"] = "allowlist"

capabilities = telegram.setdefault("capabilities", {{}})
capabilities["inlineButtons"] = "allowlist"

exec_approvals = telegram.setdefault("execApprovals", {{}})
exec_approvals["enabled"] = True
exec_approvals["approvers"] = {json.dumps(approvers)}
exec_approvals["agentFilter"] = ["operator", "coder", "cluster"]
exec_approvals["target"] = "dm"

config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({{"config": str(config_path), "allowFrom": {json.dumps(allow_from)}, "approvers": {json.dumps(approvers)}}}, sort_keys=True))
"""


def configure(args: argparse.Namespace) -> dict[str, Any]:
    token = _read_token(args.token_file)
    allow_from = _parse_telegram_ids(args.allow_from, "--allow-from")
    approvers = _parse_telegram_ids(args.approver or args.allow_from, "--approver")

    if not allow_from:
        raise ValueError("at least one --allow-from numeric Telegram ID is required")
    if not approvers:
        raise ValueError("at least one --approver numeric Telegram ID is required")
    if not token:
        raise ValueError("provide --token-file or OPENCLAW_TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Telegram bot token does not match the expected BotFather token shape")

    if args.dry_run:
        remote = _ssh(args.host, OPENCLAW_PATH_EXPORT + "openclaw config validate && openclaw channels status --json", timeout=45)
        _require(remote, "OpenClaw remote dry-run probe")
        return {"host": args.host, "dry_run": True, "allowFrom": allow_from, "approvers": approvers}

    token_install = _ssh(
        args.host,
        "umask 077; mkdir -p \"$HOME/.openclaw/secrets\"; cat > \"$HOME/.openclaw/secrets/telegram-bot-token\"",
        input_text=token,
        timeout=45,
    )
    _require(token_install, "Telegram token install")

    channel_add = _ssh(
        args.host,
        OPENCLAW_PATH_EXPORT
        + "openclaw channels add --channel telegram --account default --name Telegram --token-file \"$HOME/.openclaw/secrets/telegram-bot-token\"",
        timeout=60,
    )
    _require(channel_add, "OpenClaw Telegram channel add")

    patch = _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", args.host, "python3", "-"], input_text=_patch_config_script(allow_from, approvers), timeout=45)
    _require(patch, "OpenClaw Telegram config patch")

    validate = _ssh(args.host, OPENCLAW_PATH_EXPORT + "openclaw config validate", timeout=45)
    _require(validate, "OpenClaw config validate")

    restart = _ssh(args.host, "systemctl --user restart openclaw-gateway.service", timeout=45)
    _require(restart, "OpenClaw gateway restart")

    status = _ssh(args.host, OPENCLAW_PATH_EXPORT + "openclaw channels status --probe --json", timeout=60)
    _require(status, "OpenClaw Telegram status probe")
    status_json = json.loads(status.stdout)

    return {
        "host": args.host,
        "dry_run": False,
        "allowFrom": allow_from,
        "approvers": approvers,
        "telegram": status_json.get("channelAccounts", {}).get("telegram", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure OpenClaw Telegram token and approval allowlist on DEV.")
    parser.add_argument("--host", default="dev", help="SSH host alias for the OpenClaw gateway host.")
    parser.add_argument("--token-file", type=Path, help="Local file containing the BotFather token.")
    parser.add_argument("--allow-from", action="append", default=[], help="Numeric Telegram user/chat ID. Repeat or comma-separate.")
    parser.add_argument("--approver", action="append", default=[], help="Numeric Telegram approver ID. Defaults to --allow-from.")
    parser.add_argument("--dry-run", action="store_true", help="Validate arguments and remote reachability without writing credentials.")
    args = parser.parse_args()

    try:
        result = configure(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
