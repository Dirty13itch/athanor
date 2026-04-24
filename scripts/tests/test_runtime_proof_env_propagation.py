from __future__ import annotations

import importlib.util
import subprocess
import sys
import uuid
from pathlib import Path


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


def test_run_contract_healer_sets_runtime_proof_context_for_validator(monkeypatch) -> None:
    module = _load_module(
        f"run_contract_healer_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_contract_healer.py",
    )

    captured_env: dict[str, str] | None = None

    def fake_run(command, **kwargs):
        nonlocal captured_env
        captured_env = kwargs.get("env")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_command([module.sys.executable, "scripts/validate_platform_contract.py"])

    assert captured_env is not None
    assert captured_env["ATHANOR_RUNTIME_PROOF_CONTEXT"] == "1"


def test_ralph_run_command_sets_runtime_proof_context_for_validator(monkeypatch) -> None:
    module = _load_module(
        f"run_ralph_loop_pass_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "run_ralph_loop_pass.py",
    )

    captured_env: dict[str, str] | None = None

    def fake_run(command, **kwargs):
        nonlocal captured_env
        captured_env = kwargs.get("env")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module._run_command([module.sys.executable, "scripts/validate_platform_contract.py"])

    assert captured_env is not None
    assert captured_env["ATHANOR_RUNTIME_PROOF_CONTEXT"] == "1"
