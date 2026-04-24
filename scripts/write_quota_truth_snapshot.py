#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _install_fastapi_stubs() -> None:
    if 'fastapi' in sys.modules and 'fastapi.responses' in sys.modules:
        return

    fastapi_mod = types.ModuleType('fastapi')
    responses_mod = types.ModuleType('fastapi.responses')

    class FastAPI:  # pragma: no cover - import shim for CLI-only paths
        def __init__(self, *args, **kwargs):
            self.version = kwargs.get('version', 'stub')

        def get(self, *args, **kwargs):
            return lambda fn: fn

        def post(self, *args, **kwargs):
            return lambda fn: fn

    class HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: object | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class Request:  # pragma: no cover - import shim for CLI-only paths
        pass

    class JSONResponse:  # pragma: no cover - import shim for CLI-only paths
        def __init__(self, content: object | None = None, status_code: int = 200, **kwargs):
            self.content = content
            self.status_code = status_code
            self.headers = kwargs

    fastapi_mod.FastAPI = FastAPI
    fastapi_mod.HTTPException = HTTPException
    fastapi_mod.Request = Request
    responses_mod.JSONResponse = JSONResponse
    sys.modules['fastapi'] = fastapi_mod
    sys.modules['fastapi.responses'] = responses_mod


def _load_subscription_burn_module(script_path: Path):
    spec = importlib.util.spec_from_file_location('athanor_subscription_burn', script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load {script_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if exc.name != 'fastapi':
            raise
        _install_fastapi_stubs()
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return module


def main() -> int:
    script_path = Path(__file__).resolve().with_name('subscription-burn.py')
    module = _load_subscription_burn_module(script_path)
    module.write_quota_truth_snapshot()
    print(module.QUOTA_TRUTH_PATH)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
