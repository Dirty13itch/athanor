from __future__ import annotations

import importlib.util
import threading
from dataclasses import dataclass, field
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient


def _load_module(name: str, relative: str):
    if relative == "main.py" and "apscheduler.schedulers.background" not in sys.modules:
        background = types.ModuleType("apscheduler.schedulers.background")

        class BackgroundScheduler:
            def __init__(self, *args: object, **kwargs: object) -> None:
                return None

            def add_job(self, *args: object, **kwargs: object) -> None:
                return None

            def start(self) -> None:
                return None

            def shutdown(self, *args: object, **kwargs: object) -> None:
                return None

        background.BackgroundScheduler = BackgroundScheduler
        sys.modules["apscheduler"] = types.ModuleType("apscheduler")
        sys.modules["apscheduler.schedulers"] = types.ModuleType("apscheduler.schedulers")
        sys.modules["apscheduler.schedulers.background"] = background

    module_path = Path(__file__).resolve().parents[1] / relative
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class CheckResult:
    service: str
    tier: str
    passed: bool
    latency_ms: float
    detail: str = ""
    timestamp: float = field(default=0.0)


checks = types.ModuleType("checks")
checks.HEARTBEAT_CHECKS = []
checks.READINESS_SERVICES = ()
checks.CheckResult = CheckResult
checks.run_heartbeat = lambda *args, **kwargs: CheckResult("stub", "heartbeat", True, 0.0, "stub")
checks.run_readiness = lambda *args, **kwargs: CheckResult("stub", "readiness", True, 0.0, "stub")
checks.run_integration = lambda *args, **kwargs: []
checks.send_ntfy_alert = lambda *args, **kwargs: None
sys.modules["checks"] = checks
main = _load_module("sentinel_main", "main.py")


class DummyScheduler:
    def add_job(self, *args: object, **kwargs: object) -> None:
        return None

    def start(self) -> None:
        return None

    def shutdown(self, wait: bool = False) -> None:
        return None


class DummyThread:
    def __init__(self, *args: object, **kwargs: object) -> None:
        return None

    def start(self) -> None:
        return None


def test_health_uses_shared_snapshot_shape(monkeypatch) -> None:
    monkeypatch.setattr(main, "BackgroundScheduler", lambda daemon=True: DummyScheduler())
    monkeypatch.setattr(main.threading, "Thread", DummyThread)
    main.results = {
        ("heartbeat", "gateway"): CheckResult("gateway", "heartbeat", True, 12.0, "HTTP 200"),
        ("readiness", "vllm_coder"): CheckResult("vllm_coder", "readiness", True, 18.0, "HTTP 200"),
        ("integration", "task_engine_stats"): CheckResult("task_engine_stats", "integration", True, 20.0, "HTTP 200"),
    }
    main.results_lock = threading.Lock()

    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "sentinel"
    assert payload["status"] == "healthy"
    assert payload["auth_class"] == "read-only"
    assert payload["actions_allowed"] == []
    assert {dependency["id"] for dependency in payload["dependencies"]} == {
        "tier:heartbeat",
        "tier:readiness",
        "tier:integration",
    }


def test_health_reports_missing_results_as_degraded(monkeypatch) -> None:
    monkeypatch.setattr(main, "BackgroundScheduler", lambda daemon=True: DummyScheduler())
    monkeypatch.setattr(main.threading, "Thread", DummyThread)
    main.results = {}
    main.results_lock = threading.Lock()

    with TestClient(main.app) as client:
        payload = client.get("/health").json()

    assert payload["status"] == "degraded"
    assert payload["last_error"] == "tier:heartbeat no checks recorded yet"
    heartbeat = next(item for item in payload["dependencies"] if item["id"] == "tier:heartbeat")
    assert heartbeat["status"] == "unknown"
