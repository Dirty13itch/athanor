from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from auth import BearerAuthContract


def _register_stub_modules() -> None:
    registry = types.ModuleType("registry")
    registry.CLUSTER = {"foundry": {"gpus": 5}}
    registry.MODELS = {"coder": {"vram_gb": 16}}
    registry.can_fit = lambda model, node, gpu=0: {"can_fit": True, "model": model, "node": node, "gpu": gpu}
    registry.get_cluster_state = lambda: {"gpu": {"foundry:0": {"utilization": 12}}}
    sys.modules["registry"] = registry

    capacity = types.ModuleType("capacity")
    capacity.predict_disk_full = lambda *args, **kwargs: {}
    capacity.detect_memory_leaks = lambda *args, **kwargs: {}
    capacity.get_capacity_report = lambda: {"disk": {"vault": {"used_pct": 51.2}}}
    sys.modules["capacity"] = capacity

    lifecycle = types.ModuleType("lifecycle")
    lifecycle.get_loaded_models = lambda: []

    async def async_load_model(model: str, keep_alive: str = "5m") -> dict[str, str]:
        return {"action": "loaded", "model": model, "keep_alive": keep_alive}

    async def async_unload_model(model: str) -> dict[str, str]:
        return {"action": "unloaded", "model": model}

    async def async_get_idle_models(minutes: int = 30) -> list[dict[str, int]]:
        return [{"minutes": minutes}]

    async def swap_models(source: str, target: str) -> dict[str, str]:
        return {"action": "swapped", "from": source, "to": target}

    lifecycle.async_load_model = async_load_model
    lifecycle.async_unload_model = async_unload_model
    lifecycle.async_get_idle_models = async_get_idle_models
    lifecycle.swap_models = swap_models
    sys.modules["lifecycle"] = lifecycle

    placer = types.ModuleType("placer")
    placer.recommend_placement = lambda model: {"model": model}
    placer.find_available_gpu = lambda min_vram_gb=8.0: []
    placer.suggest_migrations = lambda: []
    sys.modules["placer"] = placer

    quality = types.ModuleType("quality")
    quality.recommend_model = lambda *args, **kwargs: {"provider": "local"}
    quality.MODEL_PROFILES = {}
    sys.modules["quality"] = quality

    cost = types.ModuleType("cost")
    cost.get_cost_summary = lambda: {"providers": []}
    sys.modules["cost"] = cost

    advisor = types.ModuleType("advisor")
    advisor.generate_briefing = lambda *args, **kwargs: {"summary": "ok"}
    sys.modules["advisor"] = advisor

    if "apscheduler.schedulers.background" not in sys.modules:
        background = types.ModuleType("apscheduler.schedulers.background")

        class BackgroundScheduler:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.running = False

            def add_job(self, *args: object, **kwargs: object) -> None:
                return None

            def start(self) -> None:
                self.running = True

            def shutdown(self, *args: object, **kwargs: object) -> None:
                self.running = False

        background.BackgroundScheduler = BackgroundScheduler
        sys.modules["apscheduler"] = types.ModuleType("apscheduler")
        sys.modules["apscheduler.schedulers"] = types.ModuleType("apscheduler.schedulers")
        sys.modules["apscheduler.schedulers.background"] = background


def _load_main_module():
    _register_stub_modules()
    service_dir = Path(__file__).resolve().parents[1]
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))
    module_path = service_dir / "main.py"
    spec = importlib.util.spec_from_file_location("brain_main", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = _load_main_module()


class DummyScheduler:
    def __init__(self) -> None:
        self.running = False

    def add_job(self, *args: object, **kwargs: object) -> None:
        return None

    def start(self) -> None:
        self.running = True

    def shutdown(self) -> None:
        self.running = False


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, list[dict[str, object]]]]:
    monkeypatch.setattr(main, "scheduler", DummyScheduler())
    monkeypatch.setattr(main, "get_cluster_state", lambda: {"gpu": {"foundry:0": {"utilization": 12}}})
    monkeypatch.setattr(main, "get_capacity_report", lambda: {"disk": {"vault": {"used_pct": 51.2}}})
    monkeypatch.setattr(
        main,
        "AUTH_CONTRACT",
        BearerAuthContract(
            service_name="brain",
            runtime_environment="production",
            bearer_token="secret-token",
            token_env_names=("BRAIN_API_TOKEN", "ATHANOR_BRAIN_API_TOKEN"),
        ),
    )
    main._state["resources"] = {}
    main._state["predictions"] = {}
    main._state["updated_at"] = None
    main._health_state.update(
        {
            "resource_last_checked_at": None,
            "resource_error": None,
            "capacity_last_checked_at": None,
            "capacity_error": None,
        }
    )

    audit_events: list[dict[str, object]] = []

    async def record_audit(**kwargs: object) -> None:
        audit_events.append(dict(kwargs))

    monkeypatch.setattr(main, "emit_operator_audit_event", record_audit)

    with TestClient(main.app) as test_client:
        yield test_client, audit_events


def test_health_is_public_and_uses_shared_snapshot_shape(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, _ = client
    response = test_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "brain"
    assert payload["status"] == "healthy"
    assert payload["auth_class"] == "admin"
    assert payload["started_at"]
    assert payload["actions_allowed"] == [
        "lifecycle.load",
        "lifecycle.unload",
        "lifecycle.swap-for-comfyui",
    ]
    assert {dependency["id"] for dependency in payload["dependencies"]} == {
        "resource-refresh",
        "capacity-refresh",
        "scheduler",
    }


def test_health_reports_refresh_failures_as_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "scheduler", DummyScheduler())
    monkeypatch.setattr(
        main,
        "AUTH_CONTRACT",
        BearerAuthContract(
            service_name="brain",
            runtime_environment="production",
            bearer_token="secret-token",
            token_env_names=("BRAIN_API_TOKEN", "ATHANOR_BRAIN_API_TOKEN"),
        ),
    )

    def _fail_cluster_state() -> dict:
        raise RuntimeError("cluster probe failed")

    monkeypatch.setattr(main, "get_cluster_state", _fail_cluster_state)
    monkeypatch.setattr(main, "get_capacity_report", lambda: {"disk": {}})
    main._state["resources"] = {}
    main._state["predictions"] = {}
    main._state["updated_at"] = None
    main._health_state.update(
        {
            "resource_last_checked_at": None,
            "resource_error": None,
            "capacity_last_checked_at": None,
            "capacity_error": None,
        }
    )

    with TestClient(main.app) as client:
        payload = client.get("/health").json()

    assert payload["status"] == "degraded"
    assert payload["last_error"] == "cluster probe failed"
    dependency = next(item for item in payload["dependencies"] if item["id"] == "resource-refresh")
    assert dependency["status"] == "down"
    assert "cluster probe failed" in dependency["detail"]


def test_lifecycle_load_requires_bearer_auth(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, _ = client

    response = test_client.post("/lifecycle/load?model=qwen3-coder")

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


def test_lifecycle_load_requires_operator_reason_and_audits_denial(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, audit_events = client
    headers = {"Authorization": "Bearer secret-token"}

    response = test_client.post(
        "/lifecycle/load?model=qwen3-coder",
        headers=headers,
        json={
            "actor": "test-suite",
            "session_id": "session-123",
            "correlation_id": "corr-123",
        },
    )

    assert response.status_code == 400
    assert "reason is required" in response.json()["error"]
    assert audit_events[-1]["route"] == "/lifecycle/load"
    assert audit_events[-1]["decision"] == "denied"


def test_lifecycle_swap_accepts_operator_envelope_and_audits(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, audit_events = client
    headers = {"Authorization": "Bearer secret-token"}

    response = test_client.post(
        "/lifecycle/swap-for-comfyui",
        headers=headers,
        json={
            "actor": "test-suite",
            "session_id": "session-123",
            "correlation_id": "corr-456",
            "reason": "Free VRAM for fixture ComfyUI run",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "action": "swapped",
        "from": "huihui_ai/qwen3.5-abliterated:35b",
        "to": "none",
    }
    assert audit_events[-1]["route"] == "/lifecycle/swap-for-comfyui"
    assert audit_events[-1]["decision"] == "accepted"
    assert audit_events[-1]["action_class"] == "admin"
