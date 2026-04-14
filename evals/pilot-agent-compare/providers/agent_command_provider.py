from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*(?P<body>\{[\s\S]*\}|\[[\s\S]*\])\s*```\s*$",
    re.IGNORECASE,
)


def _as_argv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return shlex.split(value, posix=os.name != "nt")
    raise TypeError(f"Unsupported argv value: {type(value)!r}")


def _load_optional_json_env(env_name: str | None) -> Any:
    if not env_name:
        return None
    raw = os.getenv(env_name)
    if not raw:
        return None
    return json.loads(raw)


def _resolve_command(config: dict[str, Any]) -> list[str]:
    command = config.get("command")
    if command is None and config.get("commandEnv"):
        command = os.getenv(str(config["commandEnv"]))
    argv = _as_argv(command)
    if not argv:
        env_name = config.get("commandEnv")
        source = f" env var {env_name}" if env_name else ""
        raise ValueError(f"Provider command is not configured.{source}")
    resolved_command = shutil.which(argv[0])
    if resolved_command:
        argv[0] = resolved_command
    return argv


def _resolve_args(config: dict[str, Any]) -> list[str]:
    args = config.get("args")
    if args is None:
        args = _load_optional_json_env(config.get("argsEnv"))
    return _as_argv(args)


def _format_template(value: str, tokens: dict[str, str]) -> str:
    rendered = value
    for key, token_value in tokens.items():
        rendered = rendered.replace(f"{{{key}}}", token_value)
    return rendered


def _extract_json_field(payload: str, field_path: str) -> str:
    data = json.loads(payload)
    current: Any = data
    for key in field_path.split("."):
        if isinstance(current, dict):
            current = current[key]
        else:
            raise KeyError(f"Cannot descend into {field_path!r} at {key!r}")
    if isinstance(current, str):
        return current
    return json.dumps(current, ensure_ascii=False)


def _extract_jsonl_field(payload: str, field_path: str, match_type: str | None = None) -> str:
    last_value: str | None = None
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if match_type and str(data.get("type") or "").strip() != match_type:
            continue
        current: Any = data
        for key in field_path.split("."):
            if isinstance(current, dict):
                current = current[key]
            else:
                raise KeyError(f"Cannot descend into {field_path!r} at {key!r}")
        if isinstance(current, str):
            last_value = current
        else:
            last_value = json.dumps(current, ensure_ascii=False)
    if last_value is None:
        raise KeyError(f"No JSONL value found for {field_path!r}")
    return last_value


def _maybe_strip_ansi(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    return ANSI_ESCAPE_RE.sub("", text)


def _decode_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _maybe_strip_markdown_json_fence(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    match = MARKDOWN_JSON_FENCE_RE.match(text.strip())
    if not match:
        return text
    return match.group("body").strip()


def _apply_env_from(child_env: dict[str, str], config: dict[str, Any]) -> None:
    env_from = config.get("envFrom", {})
    if not isinstance(env_from, dict):
        return
    for target_name, source_name in env_from.items():
        resolved = os.getenv(str(source_name))
        if resolved is None:
            raise ValueError(
                f"Provider env source {source_name!r} is not set for target {target_name!r}"
            )
        child_env[str(target_name)] = resolved


def call_api(prompt: str, options: dict, context: dict) -> dict:
    config = options.get("config", {})
    provider_id = str(config.get("providerId", context.get("provider", "external-agent")))
    timeout_ms = int(config.get("timeoutMs", 120000))
    stdin_mode = str(config.get("stdinMode", "prompt"))
    cwd = config.get("cwd") or os.getcwd()
    strip_ansi = bool(config.get("stripAnsi", True))
    strip_markdown_json_fences = bool(config.get("stripMarkdownJsonFences", False))

    command = _resolve_command(config)
    args = _resolve_args(config)
    task_id = str(context.get("vars", {}).get("task_id", "unknown-task"))

    payload = {
        "provider_id": provider_id,
        "task_id": task_id,
        "prompt": prompt,
        "vars": context.get("vars", {}),
        "metadata": context.get("metadata", {}),
    }

    with tempfile.TemporaryDirectory(prefix="promptfoo-agent-") as temp_dir:
        prompt_path = Path(temp_dir) / "prompt.txt"
        payload_path = Path(temp_dir) / "payload.json"
        prompt_path.write_text(prompt, encoding="utf-8")
        payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        tokens = {
            "prompt": prompt,
            "prompt_file": str(prompt_path),
            "payload_file": str(payload_path),
            "task_id": task_id,
            "provider_id": provider_id,
        }

        argv = [_format_template(part, tokens) for part in command + args]
        child_env = os.environ.copy()
        child_env.update(
            {
                "PROMPTFOO_EVAL_PROMPT": prompt,
                "PROMPTFOO_EVAL_PROMPT_FILE": str(prompt_path),
                "PROMPTFOO_EVAL_PAYLOAD_FILE": str(payload_path),
                "PROMPTFOO_EVAL_TASK_ID": task_id,
                "PROMPTFOO_EVAL_PROVIDER_ID": provider_id,
            }
        )

        _apply_env_from(child_env, config)

        extra_env = config.get("env", {})
        if isinstance(extra_env, dict):
            for key, value in extra_env.items():
                child_env[str(key)] = _format_template(str(value), tokens)

        stdin_payload = None
        if stdin_mode == "prompt":
            stdin_payload = prompt
        elif stdin_mode == "json":
            stdin_payload = json.dumps(payload)
        elif stdin_mode != "none":
            raise ValueError(f"Unsupported stdinMode: {stdin_mode}")

        started = time.monotonic()
        stdin_bytes = stdin_payload.encode("utf-8") if isinstance(stdin_payload, str) else None
        run_kwargs: dict[str, Any] = {
            "args": argv,
            "capture_output": True,
            "text": False,
            "cwd": cwd,
            "env": child_env,
            "timeout": timeout_ms / 1000,
            "check": False,
        }
        if stdin_bytes is None:
            run_kwargs["stdin"] = subprocess.DEVNULL
        else:
            run_kwargs["input"] = stdin_bytes
        result = subprocess.run(**run_kwargs)
        duration_ms = int((time.monotonic() - started) * 1000)

        stdout = _maybe_strip_ansi(_decode_output(result.stdout), strip_ansi).strip()
        stderr = _maybe_strip_ansi(_decode_output(result.stderr), strip_ansi).strip()

        extract_field = config.get("extractJsonField")
        if stdout and extract_field:
            stdout = _extract_json_field(stdout, str(extract_field)).strip()

        extract_jsonl_field = config.get("extractJsonlField")
        if stdout and extract_jsonl_field:
            stdout = _extract_jsonl_field(
                stdout,
                str(extract_jsonl_field),
                str(config.get("matchJsonlType") or "").strip() or None,
            ).strip()

        if stdout:
            stdout = _maybe_strip_markdown_json_fence(stdout, strip_markdown_json_fences).strip()

        if result.returncode != 0:
            detail = stderr or stdout or "no output"
            raise RuntimeError(
                f"{provider_id} exited with code {result.returncode}: {detail}"
            )

        return {
            "output": stdout,
            "metadata": {
                "providerId": provider_id,
                "taskId": task_id,
                "argv": argv,
                "cwd": cwd,
                "durationMs": duration_ms,
                "stderr": stderr,
            },
        }
