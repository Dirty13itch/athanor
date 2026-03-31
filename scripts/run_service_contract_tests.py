from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / ".venv-services-ci"
STATE_FILE = VENV_DIR / ".service-contract-fingerprint"
REQUIREMENT_FILES = (
    REPO_ROOT / "services" / "gateway" / "requirements-test.txt",
    REPO_ROOT / "services" / "governor" / "requirements-test.txt",
    REPO_ROOT / "services" / "quality-gate" / "requirements.txt",
    REPO_ROOT / "services" / "brain" / "requirements.txt",
    REPO_ROOT / "services" / "sentinel" / "requirements.txt",
    REPO_ROOT / "scripts" / "requirements-test.txt",
)
TEST_COMMANDS = (
    (
        "quality-gate",
        ("-m", "pytest", "services/quality-gate/tests", "-q"),
    ),
    (
        "gateway",
        ("-m", "pytest", "services/gateway/tests", "-q"),
    ),
    (
        "governor-helper-contracts",
        ("-m", "pytest", "services/governor/tests", "-q"),
    ),
    (
        "brain-classifier-sentinel",
        (
            "-m",
            "pytest",
            "--import-mode=importlib",
            "services/brain/tests/test_brain_contracts.py",
            "services/classifier/tests/test_classifier_contracts.py",
            "services/sentinel/tests/test_checks_contracts.py",
            "services/sentinel/tests/test_sentinel_contracts.py",
            "-q",
        ),
    ),
    (
        "script-services",
        (
            "-m",
            "pytest",
            "--import-mode=importlib",
            "scripts/tests/test_cli_router_contracts.py",
            "scripts/tests/test_mcp_athanor_agents_contracts.py",
            "scripts/tests/test_provider_usage_evidence_contracts.py",
            "scripts/tests/test_subscription_burn_contracts.py",
            "scripts/tests/test_truth_inventory_report_contracts.py",
            "scripts/tests/test_vault_litellm_env_audit_contracts.py",
            "scripts/tests/test_semantic_router_contracts.py",
            "-q",
        ),
    ),
)


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _run(command: list[str], *, cwd: Path | None = None) -> None:
    print(f"RUN {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd or REPO_ROOT), check=True)


def _fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(sys.executable.encode("utf-8"))
    digest.update(sys.version.encode("utf-8"))
    for path in REQUIREMENT_FILES:
        digest.update(str(path.relative_to(REPO_ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _ensure_venv(*, reinstall: bool) -> Path:
    venv_python = _venv_python()
    desired = _fingerprint()
    current = STATE_FILE.read_text(encoding="utf-8").strip() if STATE_FILE.exists() else ""

    if not venv_python.exists():
        _run([sys.executable, "-m", "venv", str(VENV_DIR)])

    if reinstall or current != desired:
        install_command = [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"]
        _run(install_command)
        install_requirements = [str(venv_python), "-m", "pip", "install"]
        for requirement in REQUIREMENT_FILES:
            install_requirements.extend(["-r", str(requirement)])
        install_requirements.append("pytest")
        _run(install_requirements)
        STATE_FILE.write_text(f"{desired}\n", encoding="utf-8")

    return venv_python


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Athanor service and script contract tests in a disposable repo-local venv."
    )
    parser.add_argument(
        "--reinstall",
        action="store_true",
        help="Force a dependency reinstall even if the fingerprint matches.",
    )
    args = parser.parse_args()

    venv_python = _ensure_venv(reinstall=args.reinstall)
    for label, command in TEST_COMMANDS:
        print(f"== {label} ==")
        _run([str(venv_python), *command])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
