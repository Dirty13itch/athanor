#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> int:
    script_path = Path(__file__).resolve().with_name("subscription-burn.py")
    spec = importlib.util.spec_from_file_location("athanor_subscription_burn", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_quota_truth_snapshot()
    print(module.QUOTA_TRUTH_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
