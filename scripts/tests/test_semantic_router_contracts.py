from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = SCRIPTS_DIR / "semantic-router-service.py"


class _DummyRoute:
    def __init__(self, name: str, utterances: list[str]) -> None:
        self.name = name
        self.utterances = utterances


class _DummyEncoder:
    def __init__(self, name: str) -> None:
        self.name = name


class _DummyIndex:
    def __init__(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready


class _DummySemanticRouter:
    def __init__(self, *, encoder: _DummyEncoder, routes: list[_DummyRoute], index: _DummyIndex) -> None:
        self.encoder = encoder
        self.routes = routes
        self.index = index

    def sync(self, mode: str) -> None:
        self.mode = mode

    def __call__(self, text: str):
        if "research" in text.lower():
            return types.SimpleNamespace(name="research")
        return types.SimpleNamespace(name="cloud_safe")


def _install_semantic_router_stubs() -> None:
    semantic_router_pkg = types.ModuleType("semantic_router")
    semantic_router_pkg.Route = _DummyRoute
    semantic_router_pkg.SemanticRouter = _DummySemanticRouter
    sys.modules["semantic_router"] = semantic_router_pkg

    encoders_pkg = types.ModuleType("semantic_router.encoders")
    encoders_pkg.HuggingFaceEncoder = _DummyEncoder
    sys.modules["semantic_router.encoders"] = encoders_pkg

    index_pkg = types.ModuleType("semantic_router.index")
    sys.modules["semantic_router.index"] = index_pkg

    local_index_pkg = types.ModuleType("semantic_router.index.local")
    local_index_pkg.LocalIndex = _DummyIndex
    sys.modules["semantic_router.index.local"] = local_index_pkg


def _load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    _install_semantic_router_stubs()
    module_name = "athanor_semantic_router_contracts"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load semantic router module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def client() -> Iterator[tuple[TestClient, object]]:
    module = _load_module()
    with TestClient(module.app) as test_client:
        yield test_client, module


def test_health_uses_shared_snapshot_shape(client: tuple[TestClient, object]) -> None:
    test_client, _ = client

    response = test_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "semantic-router"
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["auth_class"] == "internal_only"
    assert {entry["id"] for entry in payload["dependencies"]} == {"semantic_index", "encoder_model"}
    assert payload["route_count"] >= 1
    assert payload["routes"] == payload["route_count"]


def test_classify_uses_loaded_router(client: tuple[TestClient, object]) -> None:
    test_client, _ = client

    response = test_client.post("/classify", json={"text": "Research the next routing approach"})

    assert response.status_code == 200
    assert response.json()["route"] == "research"


def test_classify_fails_closed_when_router_not_ready(
    client: tuple[TestClient, object],
) -> None:
    test_client, module = client
    assert module.router is not None
    module.router.index._ready = False

    response = test_client.post("/classify", json={"text": "Classify this"})

    assert response.status_code == 503
    assert "not ready" in response.json()["detail"]
