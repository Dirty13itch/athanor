from __future__ import annotations

import importlib.util
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


def test_resolve_external_path_prefers_devstack_override(monkeypatch) -> None:
    module = _load_module(
        f"truth_inventory_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "truth_inventory.py",
    )
    monkeypatch.setenv("ATHANOR_DEVSTACK_ROOT", "/workspace/_external/devstack")

    resolved = module.resolve_external_path("C:/athanor-devstack/reports/master-atlas/latest.json")

    assert resolved == Path("/workspace/_external/devstack/reports/master-atlas/latest.json")


def test_resolve_external_path_prefers_implementation_authority_override(monkeypatch) -> None:
    module = _load_module(
        f"truth_inventory_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "truth_inventory.py",
    )
    monkeypatch.setenv("ATHANOR_IMPLEMENTATION_AUTHORITY", "/workspace")

    resolved = module.resolve_external_path("C:/Athanor/config/automation-backbone/lane-selection-matrix.json")

    assert resolved == Path("/workspace/config/automation-backbone/lane-selection-matrix.json")


def test_resolve_external_path_prefers_codex_override(monkeypatch) -> None:
    module = _load_module(
        f"truth_inventory_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "truth_inventory.py",
    )
    monkeypatch.setenv("ATHANOR_CODEX_ROOT", "/workspace/_external/codex")

    resolved = module.resolve_external_path("C:/Codex System Config/STATUS.md")

    assert resolved == Path("/workspace/_external/codex/STATUS.md")


def test_resolve_external_path_keeps_default_wsl_mapping_without_override(monkeypatch) -> None:
    module = _load_module(
        f"truth_inventory_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "truth_inventory.py",
    )
    monkeypatch.delenv("ATHANOR_DEVSTACK_ROOT", raising=False)
    monkeypatch.delenv("ATHANOR_CODEX_ROOT", raising=False)

    resolved = module.resolve_external_path("C:/athanor-devstack/configs/devstack-capability-lane-registry.json")

    assert resolved == Path("/mnt/c/athanor-devstack/configs/devstack-capability-lane-registry.json")
