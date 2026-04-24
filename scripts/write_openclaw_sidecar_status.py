from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "openclaw-sidecar-status.json"
OPENCLAW_PATH_EXPORT = 'export PATH="$HOME/.local/npm-global/bin:$PATH"; '

SECRET_KEYS = {"token", "api_key", "apikey", "password", "secret", "bot_token", "app_token"}
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in SECRET_KEYS or normalized.endswith("_token") or normalized.endswith("_key"):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = _sanitize(child)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        if EMAIL_PATTERN.search(value):
            return EMAIL_PATTERN.sub("<redacted-email>", value)
        if value.startswith(("sk-", "xox", "ghp_", "gho_", "glpat-")):
            return "<redacted>"
    return value


def _run(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"timed out after {timeout}s",
        }
    except OSError as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _ssh_openclaw(host: str, command: str, timeout: int = 30) -> dict[str, Any]:
    return _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, OPENCLAW_PATH_EXPORT + command], timeout)


def _ssh_shell(host: str, command: str, timeout: int = 30) -> dict[str, Any]:
    return _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", host, command], timeout)


def _json_from_stdout(result: dict[str, Any]) -> Any | None:
    if not result.get("ok"):
        return None
    text = str(result.get("stdout") or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _summarize_gateway(result: dict[str, Any]) -> dict[str, Any]:
    stdout = str(result.get("stdout") or "")
    capability = "unknown"
    if "Capability: admin-capable" in stdout:
        capability = "admin-capable"
    elif "Capability: read-only" in stdout:
        capability = "read-only"
    return {
        "ok": bool(result.get("ok")) and "Runtime: running" in stdout and "bind=loopback" in stdout,
        "service_running": "Runtime: running" in stdout,
        "loopback_only": "bind=loopback" in stdout and "127.0.0.1:18789" in stdout,
        "capability": capability,
        "returncode": result.get("returncode"),
    }


def _summarize_agents(value: Any) -> dict[str, Any]:
    agents = value if isinstance(value, list) else []
    ids = [str(agent.get("id")) for agent in agents if isinstance(agent, dict) and agent.get("id")]
    models_by_id = {
        str(agent.get("id")): str(agent.get("model"))
        for agent in agents
        if isinstance(agent, dict) and agent.get("id") and agent.get("model")
    }
    workspaces_by_id = {
        str(agent.get("id")): str(agent.get("workspace"))
        for agent in agents
        if isinstance(agent, dict) and agent.get("id") and agent.get("workspace")
    }
    expected = {"operator", "coder", "cluster"}
    return {
        "ok": expected.issubset(set(ids)),
        "ids": ids,
        "expected_minimum_present": sorted(expected.intersection(ids)),
        "models_by_id": models_by_id,
        "workspaces_by_id": workspaces_by_id,
        "count": len(ids),
    }


def _summarize_models(value: Any) -> dict[str, Any]:
    model = value if isinstance(value, dict) else {}
    auth = model.get("auth") if isinstance(model.get("auth"), dict) else {}
    missing = auth.get("missingProvidersInUse") if isinstance(auth.get("missingProvidersInUse"), list) else []
    providers = auth.get("providers") if isinstance(auth.get("providers"), list) else []
    return {
        "ok": not missing and bool(model.get("resolvedDefault")),
        "default_model": model.get("resolvedDefault") or model.get("defaultModel"),
        "missing_providers": missing,
        "configured_provider_count": len(providers),
    }


def _summarize_security(value: Any) -> dict[str, Any]:
    audit = value if isinstance(value, dict) else {}
    summary = audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    findings = audit.get("findings") if isinstance(audit.get("findings"), list) else []
    return {
        "ok": int(summary.get("critical") or 0) == 0,
        "critical": int(summary.get("critical") or 0),
        "warn": int(summary.get("warn") or 0),
        "info": int(summary.get("info") or 0),
        "finding_ids": [str(item.get("checkId")) for item in findings if isinstance(item, dict) and item.get("checkId")],
    }


def _summarize_nodes(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {}
    nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
    connected = [node for node in nodes if isinstance(node, dict) and bool(node.get("connected"))]
    desk = next(
        (
            node
            for node in connected
            if str(node.get("displayName") or "").lower() == "desk"
            or str(node.get("platform") or "").lower() == "win32"
        ),
        None,
    )
    commands = set(str(command) for command in (desk or {}).get("commands", []) if str(command).strip())
    return {
        "ok": bool(desk) and {"system.which", "system.run", "system.run.prepare"}.issubset(commands),
        "count": len(nodes),
        "connected_count": len(connected),
        "desk_connected": bool(desk),
        "desk_commands": sorted(commands),
    }


def _first_telegram_account(value: Any) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {}
    accounts_by_channel = payload.get("channelAccounts") if isinstance(payload.get("channelAccounts"), dict) else {}
    accounts = accounts_by_channel.get("telegram") if isinstance(accounts_by_channel.get("telegram"), list) else []
    defaults = payload.get("channelDefaultAccountId") if isinstance(payload.get("channelDefaultAccountId"), dict) else {}
    default_account_id = defaults.get("telegram")
    for account in accounts:
        if isinstance(account, dict) and account.get("accountId") == default_account_id:
            return account
    for account in accounts:
        if isinstance(account, dict):
            return account
    return {}


def _summarize_channels(list_value: Any, status_value: Any) -> dict[str, Any]:
    listed = list_value if isinstance(list_value, dict) else {}
    chat = listed.get("chat") if isinstance(listed.get("chat"), dict) else {}
    listed_accounts = chat.get("telegram") if isinstance(chat.get("telegram"), list) else []
    status = status_value if isinstance(status_value, dict) else {}
    channels = status.get("channels") if isinstance(status.get("channels"), dict) else {}
    telegram = channels.get("telegram") if isinstance(channels.get("telegram"), dict) else {}
    account = _first_telegram_account(status)

    configured = bool(account.get("configured")) or bool(telegram.get("configured"))
    running = bool(account.get("running")) or bool(telegram.get("running"))
    token_status = str(account.get("tokenStatus") or ("configured" if configured else "missing")).lower()
    token_ok = token_status not in {"", "missing", "none", "invalid", "unknown"}
    allow_unmentioned_groups = bool(account.get("allowUnmentionedGroups"))

    return {
        "ok": bool(listed_accounts) and configured and running and token_ok and not allow_unmentioned_groups,
        "listed": bool(listed_accounts),
        "listed_accounts": [str(item) for item in listed_accounts],
        "configured": configured,
        "running": running,
        "token_status": token_status,
        "token_ok": token_ok,
        "allow_unmentioned_groups": allow_unmentioned_groups,
        "last_error": account.get("lastError") or telegram.get("lastError"),
        "mode": account.get("mode") or telegram.get("mode"),
        "account_id": account.get("accountId"),
        "list_raw_type": type(list_value).__name__ if list_value is not None else "none",
        "status_raw_type": type(status_value).__name__ if status_value is not None else "none",
    }


def build_status(host: str = "dev") -> dict[str, Any]:
    gateway = _ssh_openclaw(host, "openclaw gateway status", timeout=45)
    healthz = _ssh_shell(host, "curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/healthz", timeout=20)
    security_raw = _ssh_openclaw(host, "openclaw security audit --json", timeout=45)
    models_raw = _ssh_openclaw(host, "openclaw models status --json", timeout=45)
    agents_raw = _ssh_openclaw(host, "openclaw agents list --bindings --json", timeout=45)
    channels_raw = _ssh_openclaw(host, "openclaw channels list --json", timeout=45)
    channel_status_raw = _ssh_openclaw(host, "openclaw channels status --probe --json", timeout=45)
    nodes_raw = _ssh_openclaw(host, "openclaw nodes status --json", timeout=45)
    tasks_raw = _ssh_openclaw(host, "openclaw tasks audit --json", timeout=45)

    security = _json_from_stdout(security_raw)
    models = _json_from_stdout(models_raw)
    agents = _json_from_stdout(agents_raw)
    channels = _json_from_stdout(channels_raw)
    channel_status = _json_from_stdout(channel_status_raw)
    nodes = _json_from_stdout(nodes_raw)
    tasks = _json_from_stdout(tasks_raw)

    checks = {
        "gateway": _summarize_gateway(gateway),
        "healthz": {
            "ok": bool(healthz.get("ok")) and str(healthz.get("stdout") or "").strip() == "200",
            "http_code": str(healthz.get("stdout") or "").strip(),
            "returncode": healthz.get("returncode"),
        },
        "security": _summarize_security(security),
        "models": _summarize_models(models),
        "agents": _summarize_agents(agents),
        "channels_configured": _summarize_channels(channels, channel_status),
        "nodes_visible": _summarize_nodes(nodes),
        "tasks_audit": {
            "ok": bool(tasks_raw.get("ok")),
            "raw_type": type(tasks).__name__ if tasks is not None else "none",
        },
    }
    ready = (
        checks["gateway"]["ok"]
        and checks["healthz"]["ok"]
        and checks["security"]["ok"]
        and checks["agents"]["ok"]
        and checks["models"]["ok"]
        and checks["channels_configured"]["ok"]
    )

    blockers = [
        label
        for label, blocked in [
            ("model_auth_missing_or_unverified", not checks["models"]["ok"]),
            ("telegram_channel_missing_or_unverified", not checks["channels_configured"]["ok"]),
            ("node_pairing_not_verified", not checks["nodes_visible"]["ok"]),
        ]
        if blocked
    ]

    return _sanitize(
        {
            "generated_at": _now_iso(),
            "host": host,
            "service_id": "openclaw_gateway",
            "posture": "sidecar_approval_gated",
            "bind_contract": "loopback_only_tunnel_required",
            "ready_for_everything_locally": ready,
            "checks": checks,
            "blockers": blockers,
            "raw": {
                "security": security,
                "models": models,
                "agents": agents,
                "channels": channels,
                "channel_status": channel_status,
                "nodes": nodes,
                "tasks": tasks,
            },
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Write OpenClaw sidecar status evidence.")
    parser.add_argument("--host", default="dev")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    status = build_status(host=args.host)
    payload = json.dumps(status, indent=2, sort_keys=True)
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
