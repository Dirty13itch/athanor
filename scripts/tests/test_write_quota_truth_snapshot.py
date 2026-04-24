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


def test_load_subscription_burn_module_registers_module_for_dataclass_evaluation(tmp_path: Path) -> None:
    module = _load_module(
        f"write_quota_truth_snapshot_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "write_quota_truth_snapshot.py",
    )

    script_path = tmp_path / "temp-subscription-burn.py"
    script_path.write_text(
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class Payload:\n"
        "    value: int = 1\n",
        encoding="utf-8",
    )

    loaded = module._load_subscription_burn_module(script_path)

    assert loaded.Payload().value == 1
