from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SUPPORTED_PROMPTFOO_NODE_20 = (20, 20, 0)
SUPPORTED_PROMPTFOO_NODE_22 = (22, 22, 0)
PROMPTFOO_RUNTIME_PROBE_TIMEOUT_SECONDS = 30


def parse_semver(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_supported_promptfoo_node_version(node_version: tuple[int, int, int] | None) -> bool:
    if not node_version:
        return False
    major, minor, patch = node_version
    if major == 20:
        return (major, minor, patch) >= SUPPORTED_PROMPTFOO_NODE_20
    if major == 22:
        return (major, minor, patch) >= SUPPORTED_PROMPTFOO_NODE_22
    return major > 22


def _probe_node_version(node_path: str | None) -> tuple[str | None, tuple[int, int, int] | None]:
    if not node_path:
        return None, None
    try:
        completed = subprocess.run(
            [node_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=PROMPTFOO_RUNTIME_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    version_text = (completed.stdout or completed.stderr or "").strip() or None
    return version_text, parse_semver(version_text or "")


def _dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        normalized = str(path).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _candidate_node_paths() -> list[str]:
    env_override = os.environ.get("PROMPTFOO_NODE_PATH")
    program_files = os.environ.get("ProgramFiles") or r"C:\Program Files"
    candidates = [
        env_override or "",
        shutil.which("node") or "",
        shutil.which("node.exe") or "",
        str(Path(program_files) / "Common Files" / "Adobe" / "Creative Cloud Libraries" / "libs" / "node.exe"),
        str(Path(program_files) / "Adobe" / "Adobe Creative Cloud Experience" / "libs" / "node.exe"),
    ]
    return [path for path in _dedupe_paths(candidates) if Path(path).exists()]


def _candidate_cli_paths() -> list[str]:
    runtime_home = Path(
        os.environ.get("PROMPTFOO_RUNTIME_HOME")
        or (Path(os.environ.get("LOCALAPPDATA") or "") / "promptfoo-adobe-runtime")
    )
    candidates = [
        os.environ.get("PROMPTFOO_CLI_JS") or "",
        str(runtime_home / "node_modules" / "promptfoo" / "dist" / "src" / "main.js"),
    ]
    return [path for path in _dedupe_paths(candidates) if Path(path).exists()]


def _probe_promptfoo_command(prefix: list[str]) -> dict[str, Any]:
    command = [*prefix, "--version"]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=PROMPTFOO_RUNTIME_PROBE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    return {
        "ok": completed.returncode == 0,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def resolve_promptfoo_runtime() -> dict[str, Any]:
    path_node = shutil.which("node") or shutil.which("node.exe")
    path_node_version_text, path_node_version = _probe_node_version(path_node)
    path_node_supported = is_supported_promptfoo_node_version(path_node_version)

    promptfoo_path = shutil.which("promptfoo") or shutil.which("promptfoo.cmd")
    npx_path = shutil.which("npx") or shutil.which("npx.cmd")
    cli_paths = _candidate_cli_paths()
    node_paths = _candidate_node_paths()

    candidates: list[dict[str, Any]] = []
    for cli_path in cli_paths:
        env_node = os.environ.get("PROMPTFOO_NODE_PATH")
        if env_node and Path(env_node).exists():
            candidates.append(
                {
                    "mode": "node_cli_override",
                    "prefix": [env_node, cli_path],
                    "cli_path": cli_path,
                    "node_path": env_node,
                    "source": "env_override",
                }
            )
        break

    if promptfoo_path:
        candidates.append(
            {
                "mode": "promptfoo_bin",
                "prefix": [promptfoo_path],
                "cli_path": promptfoo_path,
                "node_path": path_node,
                "source": "path_promptfoo",
            }
        )

    for cli_path in cli_paths:
        for node_path in node_paths:
            candidates.append(
                {
                    "mode": "node_cli",
                    "prefix": [node_path, cli_path],
                    "cli_path": cli_path,
                    "node_path": node_path,
                    "source": "local_runtime_home",
                }
            )

    if npx_path and path_node_supported:
        candidates.append(
            {
                "mode": "npx_exec",
                "prefix": [npx_path, "promptfoo@latest"],
                "cli_path": None,
                "node_path": path_node,
                "source": "path_npx",
            }
        )

    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        probe = _probe_promptfoo_command(candidate["prefix"])
        node_version_text, node_version = _probe_node_version(candidate.get("node_path"))
        attempt = {
            **candidate,
            "probe_command": probe["command"],
            "probe_returncode": probe["returncode"],
            "probe_stdout_tail": probe["stdout"][-1000:],
            "probe_stderr_tail": probe["stderr"][-1000:],
            "node_version": node_version_text,
            "node_version_supported": is_supported_promptfoo_node_version(node_version),
        }
        attempts.append(attempt)
        if probe["ok"]:
            version_text = (probe["stdout"] or probe["stderr"]).strip() or None
            return {
                "available": True,
                "command": list(candidate["prefix"]),
                "mode": candidate["mode"],
                "source": candidate["source"],
                "cli_path": candidate.get("cli_path"),
                "command_path": candidate["prefix"][0],
                "node_path": candidate.get("node_path"),
                "node_version": node_version_text,
                "node_version_supported": is_supported_promptfoo_node_version(node_version),
                "promptfoo_version": version_text,
                "blocking_reason": None,
                "probe_attempts": attempts,
            }

    blocking_reason = "missing_promptfoo_runtime"
    if path_node_version_text and not path_node_supported:
        blocking_reason = f"unsupported_promptfoo_node_runtime:{path_node_version_text}"
    elif attempts:
        blocking_reason = "promptfoo_runtime_unusable"

    return {
        "available": False,
        "command": None,
        "mode": None,
        "source": None,
        "cli_path": cli_paths[0] if cli_paths else None,
        "command_path": promptfoo_path or npx_path,
        "node_path": path_node,
        "node_version": path_node_version_text,
        "node_version_supported": path_node_supported,
        "promptfoo_version": None,
        "blocking_reason": blocking_reason,
        "probe_attempts": attempts,
    }
