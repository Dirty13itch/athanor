from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from auth import BearerAuthContract


def _json_response(method: str, url: str, payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload, request=httpx.Request(method, url))


class DummyAsyncClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.calls: list[tuple[str, str]] = []

    async def get(self, url: str, *args: object, **kwargs: object) -> httpx.Response:
        self.calls.append(("GET", url))
        if url.endswith("/collections"):
            return _json_response("GET", url, {"result": {"collections": []}})
        return _json_response("GET", url, {"ok": True})

    async def post(self, url: str, *args: object, **kwargs: object) -> httpx.Response:
        self.calls.append(("POST", url))
        if url.endswith("/points/scroll"):
            return _json_response("POST", url, {"result": {"points": [], "next_page_offset": None}})
        if url.endswith("/points/search"):
            return _json_response("POST", url, {"result": []})
        return _json_response("POST", url, {"result": {}})

    async def put(self, url: str, *args: object, **kwargs: object) -> httpx.Response:
        self.calls.append(("PUT", url))
        return _json_response("PUT", url, {"result": {"status": "ok"}})

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, list[dict[str, object]]]]:
    monkeypatch.setattr(
        main,
        "AUTH_CONTRACT",
        BearerAuthContract(
            service_name="quality-gate",
            runtime_environment="production",
            bearer_token="secret-token",
            token_env_names=("QUALITY_GATE_API_TOKEN", "ATHANOR_QUALITY_GATE_API_TOKEN"),
        ),
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", DummyAsyncClient)

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
    assert payload["service"] == "quality-gate"
    assert payload["status"] in {"healthy", "degraded"}
    assert payload["auth_class"] == "admin"
    assert isinstance(payload["dependencies"], list)
    assert {dependency["id"] for dependency in payload["dependencies"]} == {"qdrant", "embedding"}
    assert "store" in payload["actions_allowed"]
    assert payload["started_at"]


def test_validate_requires_bearer_auth(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/validate",
        json={"content": "x" * 40, "collection": "memory", "metadata": {"source": "manual"}},
    )

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "authentication_error"


def test_batch_dedup_denial_returns_contract_error_and_audits(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, audit_events = client
    headers = {"Authorization": "Bearer secret-token"}

    response = test_client.post(
        "/batch-dedup?collection=memory",
        headers=headers,
        json={
            "actor": "test-suite",
            "session_id": "session-123",
            "correlation_id": "corr-123",
        },
    )

    assert response.status_code == 400
    assert "reason is required" in response.json()["error"]
    assert audit_events[-1]["route"] == "/batch-dedup"
    assert audit_events[-1]["decision"] == "denied"


def test_batch_dedup_dry_run_accepts_operator_envelope_and_audits(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, audit_events = client
    headers = {"Authorization": "Bearer secret-token"}

    response = test_client.post(
        "/batch-dedup?collection=memory",
        headers=headers,
        json={
            "actor": "test-suite",
            "session_id": "session-123",
            "correlation_id": "corr-456",
            "reason": "Verify dry-run dedup contract",
        },
    )

    assert response.status_code == 200
    assert response.json()["collection"] == "memory"
    assert response.json()["dry_run"] is True
    assert audit_events[-1]["route"] == "/batch-dedup"
    assert audit_events[-1]["decision"] == "accepted"
    assert audit_events[-1]["action_class"] == "admin"


def test_cleanup_junk_requires_protected_mode_for_destructive_runs(
    client: tuple[TestClient, list[dict[str, object]]],
) -> None:
    test_client, audit_events = client
    headers = {"Authorization": "Bearer secret-token"}

    response = test_client.post(
        "/cleanup-junk?collection=memory&dry_run=false",
        headers=headers,
        json={
            "actor": "test-suite",
            "session_id": "session-123",
            "correlation_id": "corr-789",
            "reason": "Verify destructive cleanup gate",
        },
    )

    assert response.status_code == 400
    assert "protected_mode=true is required" in response.json()["error"]
    assert audit_events[-1]["route"] == "/cleanup-junk"
    assert audit_events[-1]["decision"] == "denied"
