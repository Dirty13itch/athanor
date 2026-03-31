from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
import pytest

import main


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    async def fake_check_service(name: str, info: dict) -> dict:
        if name == "agent_server":
            return {
                "service": name,
                "node": "foundry",
                "status": "healthy",
                "http_status": 200,
                "response_ms": 12,
            }
        if name == "dashboard":
            return {
                "service": name,
                "node": "dev",
                "status": "degraded",
                "http_status": 503,
                "response_ms": 41,
            }
        return {
            "service": name,
            "node": "vault",
            "status": "unreachable",
            "http_status": None,
            "response_ms": None,
            "error": "connection refused",
        }

    monkeypatch.setattr(
        main,
        "SERVICES",
        {
            "agent_server": {"url": "http://agent-server.test/health", "node": "foundry"},
            "dashboard": {"url": "http://dashboard.test/api/overview", "node": "dev"},
            "litellm": {"url": "http://litellm.test/health", "node": "vault"},
        },
    )
    monkeypatch.setattr(main, "_check_service", fake_check_service)

    with TestClient(main.app) as test_client:
        yield test_client


def test_health_uses_shared_snapshot_shape(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "gateway"
    assert payload["auth_class"] == "internal_only"
    assert payload["network_scope"] == "internal_only"
    assert payload["status"] == "degraded"
    assert payload["healthy"] == 1
    assert payload["total"] == 3
    assert payload["last_error"] == "2 dependency checks degraded or unreachable"
    assert payload["started_at"]
    assert payload["timestamp"]
    assert isinstance(payload["dependencies"], list)
    assert {dependency["id"] for dependency in payload["dependencies"]} == {
        "agent_server",
        "dashboard",
        "litellm",
    }
    dependency_map = {dependency["id"]: dependency for dependency in payload["dependencies"]}
    assert dependency_map["agent_server"]["status"] == "healthy"
    assert dependency_map["dashboard"]["status"] == "degraded"
    assert dependency_map["litellm"]["status"] == "down"


def test_health_paginates_service_page_but_not_dependency_snapshot(client: TestClient) -> None:
    response = client.get("/health?limit=1&offset=1")

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "3"
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert len(payload["services"]) == 1
    assert payload["services"][0]["service"] == "dashboard"
    assert len(payload["dependencies"]) == 3
