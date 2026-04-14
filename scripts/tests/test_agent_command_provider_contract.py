from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = REPO_ROOT / "evals" / "pilot-agent-compare" / "providers" / "agent_command_provider.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _TemporaryDirectoryStub:
    def __init__(self, path: Path):
        self._path = path

    def __enter__(self) -> str:
        return str(self._path)

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_resolve_command_prefers_concrete_windows_shim(monkeypatch) -> None:
    module = _load_module(
        f"agent_command_provider_{uuid.uuid4().hex}",
        PROVIDER_PATH,
    )
    monkeypatch.setattr(module.shutil, "which", lambda command: "C:/Users/Shaun/AppData/Roaming/npm/codex.CMD")
    argv = module._resolve_command({"command": "codex"})
    assert argv == ["C:/Users/Shaun/AppData/Roaming/npm/codex.CMD"]


def test_call_api_uses_devnull_when_no_stdin_payload(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"agent_command_provider_call_{uuid.uuid4().hex}",
        PROVIDER_PATH,
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda prefix="": _TemporaryDirectoryStub(tmp_path),
    )
    monkeypatch.setattr(module, "_resolve_command", lambda config: ["C:/tool/codex.CMD"])
    monkeypatch.setattr(module, "_resolve_args", lambda config: ["exec", "{prompt}"])

    captured: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured.update(kwargs)
        return module.subprocess.CompletedProcess(
            kwargs["args"],
            0,
            stdout=b'{"type":"item.completed","item":{"text":"READY"}}',
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.call_api(
        "Reply with READY only.",
        {
            "config": {
                "providerId": "direct-cli",
                "stdinMode": "none",
                "cwd": "C:/",
                "stripAnsi": True,
            }
        },
        {"vars": {"task_id": "probe"}, "metadata": {}},
    )

    assert captured["stdin"] is module.subprocess.DEVNULL
    assert "input" not in captured
    assert result["output"] == '{"type":"item.completed","item":{"text":"READY"}}'


def test_call_api_writes_prompt_to_stdin_when_configured(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"agent_command_provider_stdin_{uuid.uuid4().hex}",
        PROVIDER_PATH,
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda prefix="": _TemporaryDirectoryStub(tmp_path),
    )
    monkeypatch.setattr(module, "_resolve_command", lambda config: ["C:/tool/codex.CMD"])
    monkeypatch.setattr(module, "_resolve_args", lambda config: ["exec", "--json", "-"])

    captured: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured.update(kwargs)
        return module.subprocess.CompletedProcess(
            kwargs["args"],
            0,
            stdout=b'{"type":"item.completed","item":{"text":"READY"}}',
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.call_api(
        "Reply with READY only.",
        {
            "config": {
                "providerId": "direct-cli",
                "stdinMode": "prompt",
                "cwd": "C:/",
                "stripAnsi": True,
                "extractJsonlField": "item.text",
                "matchJsonlType": "item.completed",
            }
        },
        {"vars": {"task_id": "probe"}, "metadata": {}},
    )

    assert captured["input"] == b"Reply with READY only."
    assert "stdin" not in captured
    assert result["output"] == "READY"


def test_call_api_strips_markdown_json_fence_when_enabled(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"agent_command_provider_markdown_json_{uuid.uuid4().hex}",
        PROVIDER_PATH,
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda prefix="": _TemporaryDirectoryStub(tmp_path),
    )
    monkeypatch.setattr(module, "_resolve_command", lambda config: ["C:/tool/goose.EXE"])
    monkeypatch.setattr(module, "_resolve_args", lambda config: ["run", "--text", "{prompt}"])

    def _fake_run(**kwargs):
        return module.subprocess.CompletedProcess(
            kwargs["args"],
            0,
            stdout=b'```json\n{"task_id":"probe","summary":"ok"}\n```',
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.call_api(
        "Return strict JSON only.",
        {
            "config": {
                "providerId": "goose",
                "stdinMode": "none",
                "cwd": "C:/",
                "stripAnsi": True,
                "stripMarkdownJsonFences": True,
            }
        },
        {"vars": {"task_id": "probe"}, "metadata": {}},
    )

    assert result["output"] == '{"task_id":"probe","summary":"ok"}'


def test_call_api_copies_env_from_parent(monkeypatch, tmp_path: Path) -> None:
    module = _load_module(
        f"agent_command_provider_env_from_{uuid.uuid4().hex}",
        PROVIDER_PATH,
    )
    monkeypatch.setattr(
        module.tempfile,
        "TemporaryDirectory",
        lambda prefix="": _TemporaryDirectoryStub(tmp_path),
    )
    monkeypatch.setattr(module, "_resolve_command", lambda config: ["C:/tool/goose.EXE"])
    monkeypatch.setattr(module, "_resolve_args", lambda config: ["run", "--text", "{prompt}"])
    monkeypatch.setenv("LITELLM_API_KEY", "test-litellm-key")

    captured: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured.update(kwargs)
        return module.subprocess.CompletedProcess(
            kwargs["args"],
            0,
            stdout=b'{"task_id":"probe","summary":"ok"}',
            stderr=b"",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.call_api(
        "Return strict JSON only.",
        {
            "config": {
                "providerId": "goose",
                "stdinMode": "none",
                "cwd": "C:/",
                "stripAnsi": True,
                "envFrom": {
                    "OPENAI_API_KEY": "LITELLM_API_KEY",
                },
            }
        },
        {"vars": {"task_id": "probe"}, "metadata": {}},
    )

    assert "env" in captured
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["OPENAI_API_KEY"] == "test-litellm-key"
