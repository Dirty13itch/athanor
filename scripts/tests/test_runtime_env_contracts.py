from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_load_runtime_env_contract_derives_canonical_gateway_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module(
        f"runtime_env_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "runtime_env.py",
    )

    for name in [
        "ATHANOR_LITELLM_API_KEY",
        "ATHANOR_LITELLM_URL",
        "OPENAI_API_KEY",
        "OPENAI_API_BASE",
        "OPENAI_HOST",
        "OPENAI_BASE_PATH",
        "LITELLM_API_KEY",
        "LITELLM_URL",
    ]:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("LITELLM_API_KEY", "desk-test-key")
    monkeypatch.setattr(module, "_default_litellm_api_base", lambda: "http://192.168.1.203:4000/v1")

    resolved = module.load_runtime_env_contract(
        env_names=[
            "ATHANOR_LITELLM_API_KEY",
            "ATHANOR_LITELLM_URL",
            "OPENAI_API_KEY",
            "OPENAI_API_BASE",
            "OPENAI_HOST",
            "OPENAI_BASE_PATH",
        ]
    )

    assert resolved == {
        "ATHANOR_LITELLM_API_KEY": "desk-test-key",
        "ATHANOR_LITELLM_URL": "http://192.168.1.203:4000/v1",
        "OPENAI_API_BASE": "http://192.168.1.203:4000/v1",
        "OPENAI_API_KEY": "desk-test-key",
        "OPENAI_BASE_PATH": "v1/chat/completions",
        "OPENAI_HOST": "http://192.168.1.203:4000",
    }


def test_load_runtime_env_contract_normalizes_openai_host_and_base_path(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module(
        f"runtime_env_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "runtime_env.py",
    )

    for name in [
        "ATHANOR_LITELLM_URL",
        "LITELLM_URL",
        "OPENAI_API_BASE",
        "OPENAI_HOST",
        "OPENAI_BASE_PATH",
    ]:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("OPENAI_HOST", "http://192.168.1.203:4000")
    monkeypatch.setenv("OPENAI_BASE_PATH", "v1/chat/completions")

    resolved = module.load_runtime_env_contract(env_names=["ATHANOR_LITELLM_URL", "OPENAI_API_BASE"])

    assert resolved["ATHANOR_LITELLM_URL"] == "http://192.168.1.203:4000/v1"
    assert resolved["OPENAI_API_BASE"] == "http://192.168.1.203:4000/v1"


def test_runtime_env_status_reports_derived_names(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module(
        f"runtime_env_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "runtime_env.py",
    )

    for name in ["ATHANOR_LITELLM_API_KEY", "OPENAI_API_KEY", "LITELLM_API_KEY"]:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("LITELLM_API_KEY", "desk-test-key")
    monkeypatch.setattr(module, "_default_litellm_api_base", lambda: "http://192.168.1.203:4000/v1")

    status = module.runtime_env_status(
        env_names=["ATHANOR_LITELLM_API_KEY", "OPENAI_API_KEY", "LITELLM_API_KEY"]
    )

    assert status["missing"] == []
    assert status["resolved"] == ["ATHANOR_LITELLM_API_KEY", "LITELLM_API_KEY", "OPENAI_API_KEY"]
    assert status["derived"] == ["ATHANOR_LITELLM_API_KEY", "OPENAI_API_KEY"]
