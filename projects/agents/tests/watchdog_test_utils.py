from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from pathlib import Path


WATCHDOG_DIR = Path(__file__).resolve().parents[1] / "watchdog"
WATCHDOG_MAIN = WATCHDOG_DIR / "main.py"
WATCHDOG_DEPENDENCIES = ("catalog", "circuit", "remediation")


def load_watchdog_module(env: dict[str, str]):
    original_env = {key: os.environ.get(key) for key in env}
    for key, value in env.items():
        os.environ[key] = value

    for dependency in WATCHDOG_DEPENDENCIES:
        sys.modules.pop(dependency, None)

    module_name = f"athanor_watchdog_main_{uuid.uuid4().hex}"
    sys.path.insert(0, str(WATCHDOG_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, WATCHDOG_MAIN)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load watchdog main module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path and sys.path[0] == str(WATCHDOG_DIR):
            sys.path.pop(0)
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
