from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _load_main_module():
    module_path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("classifier_main", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = _load_main_module()


@pytest.fixture()
def reset_classifier_state() -> Iterator[None]:
    main.classifier_pipe = None
    main.model_last_error = None
    main.model_checked_at = None
    yield
    main.classifier_pipe = None
    main.model_last_error = None
    main.model_checked_at = None


def test_health_uses_shared_snapshot_shape_when_model_loads(
    monkeypatch: pytest.MonkeyPatch,
    reset_classifier_state: None,
) -> None:
    monkeypatch.setattr(main, "build_classifier_pipeline", lambda _path: object())

    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "classifier"
    assert payload["status"] == "healthy"
    assert payload["auth_class"] == "read-only"
    assert payload["actions_allowed"] == []
    assert payload["started_at"]
    assert payload["dependencies"][0]["id"] == "guard-model"
    assert payload["dependencies"][0]["status"] == "healthy"
    assert payload["model_loaded"] is True


def test_health_reports_model_load_failures(
    monkeypatch: pytest.MonkeyPatch,
    reset_classifier_state: None,
) -> None:
    def _raise(_path: str):
        raise RuntimeError("missing qwen3guard weights")

    monkeypatch.setattr(main, "build_classifier_pipeline", _raise)

    with TestClient(main.app) as client:
        payload = client.get("/health").json()

    assert payload["status"] == "degraded"
    assert payload["last_error"] == "missing qwen3guard weights"
    assert payload["dependencies"][0]["status"] == "down"
    assert "missing qwen3guard weights" in payload["dependencies"][0]["detail"]
    assert payload["model_loaded"] is False
