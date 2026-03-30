from __future__ import annotations

import asyncio
import importlib.util
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient


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


@pytest.fixture()
def subscription_burn_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[object, TestClient, list[dict[str, object]]]]:
    module = _load_module(
        f"subscription_burn_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "subscription-burn.py",
    )

    task_dir = tmp_path / "subscription-tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    default_repo = tmp_path / "repo"
    default_repo.mkdir(parents=True, exist_ok=True)

    module.TASKS_DIR = task_dir
    module.STATE_FILE = tmp_path / "subscription-burn-state.json"
    module.DEFAULT_WORKING_DIR = default_repo
    registry = {
        "version": "test-burn-registry",
        "source_of_truth": "config/automation-backbone/subscription-burn-registry.json",
        "subscriptions": [
            {
                "id": "claude_max",
                "provider_id": "anthropic_claude_code",
                "stats_key": "claude_code",
                "type": "rolling_window",
                "window_hours": 5,
                "cli_env": "ATHANOR_CLAUDE_CLI",
                "cli_command": "claude",
                "legacy_path": "/tmp/claude",
                "cli_args": ["-p", "--dangerously-skip-permissions"],
                "task_file": "claude-tasks.yaml",
            },
            {
                "id": "chatgpt_pro",
                "provider_id": "openai_codex",
                "stats_key": "codex_cli",
                "type": "daily_reset",
                "daily_limit": 200,
                "reset_time": "00:00",
                "cli_env": "ATHANOR_CODEX_CLI",
                "cli_command": "codex",
                "cli_args": [],
                "task_file": "codex-tasks.yaml",
            },
            {
                "id": "gemini_advanced",
                "provider_id": "google_gemini",
                "stats_key": "gemini_cli",
                "type": "daily_reset",
                "daily_limit": 100,
                "reset_time": "00:00",
                "cli_env": "ATHANOR_GEMINI_CLI",
                "cli_command": "gemini",
                "cli_args": [],
                "task_file": "gemini-tasks.yaml",
            },
            {
                "id": "kimi_allegretto",
                "provider_id": "moonshot_kimi",
                "stats_key": "kimi_code",
                "type": "rolling_window",
                "window_hours": 5,
                "max_concurrent": 30,
                "cli_env": "ATHANOR_KIMI_CLI",
                "cli_command": "kimi",
                "cli_args": [],
                "task_file": "kimi-tasks.yaml",
            },
        ],
        "windows": [
            {"id": "morning", "hour": 7, "minute": 0, "label": "Window 1 - Morning", "subscriptions": ["claude_max", "gemini_advanced", "kimi_allegretto"]},
            {"id": "midday", "hour": 12, "minute": 0, "label": "Window 2 - Midday", "subscriptions": ["claude_max", "chatgpt_pro"]},
            {"id": "evening", "hour": 17, "minute": 0, "label": "Window 3 - Evening", "subscriptions": ["claude_max", "kimi_allegretto"]},
            {"id": "overnight", "hour": 22, "minute": 0, "label": "Window 4 - Overnight", "subscriptions": ["claude_max", "chatgpt_pro"]},
        ],
    }
    module.PROVIDER_CATALOG = {
        "anthropic_claude_code": {
            "id": "anthropic_claude_code",
            "label": "Claude Code",
            "subscription_product": "Claude Max",
            "monthly_cost_usd": 200,
            "official_pricing_status": "official_verified",
        },
        "openai_codex": {
            "id": "openai_codex",
            "label": "Codex",
            "subscription_product": "ChatGPT Pro",
            "monthly_cost_usd": 200,
            "official_pricing_status": "official_verified",
        },
        "google_gemini": {
            "id": "google_gemini",
            "label": "Gemini CLI",
            "subscription_product": "Google AI Pro / Gemini CLI",
            "monthly_cost_usd": 20,
            "official_pricing_status": "official_verified",
        },
        "moonshot_kimi": {
            "id": "moonshot_kimi",
            "label": "Kimi Code",
            "subscription_product": "Kimi Membership / Kimi Code",
            "monthly_cost_usd": None,
            "official_pricing_status": "official-source-present-cost-unverified",
        },
    }
    module.apply_burn_registry(registry)
    module.NTFY_URL = "http://ntfy.test/topic"
    module._scheduler_running = True

    async def fake_ntfy(*args: object, **kwargs: object) -> None:
        return None

    async def fake_build_index() -> None:
        module._cli_router.index.ready = True
        module._cli_router.index.centroids = {"feature_dev": object()}
        module._cli_router.index.dim = 1

    async def fake_close() -> None:
        return None

    async def idle_loop() -> None:
        await asyncio.sleep(3600)

    audit_events: list[dict[str, object]] = []

    async def record_audit(**kwargs: object) -> None:
        audit_events.append(dict(kwargs))

    monkeypatch.setattr(module, "ntfy", fake_ntfy)
    monkeypatch.setattr(module, "scheduler_loop", idle_loop)
    monkeypatch.setattr(module, "reaper_loop", idle_loop)
    monkeypatch.setattr(module._cli_router, "build_index", fake_build_index)
    monkeypatch.setattr(module._cli_router, "close", fake_close)
    monkeypatch.setattr(module, "emit_operator_audit_event", record_audit)
    monkeypatch.setattr(module._cli_router_mod, "emit_operator_audit_event", record_audit)

    with TestClient(module.app) as client:
        yield module, client, audit_events


def test_health_uses_shared_snapshot_shape(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    module, client, _ = subscription_burn_client

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "subscription-burn"
    assert payload["status"] == "healthy"
    assert payload["auth_class"] == "internal_only"
    assert payload["network_scope"] == "internal_only"
    assert payload["subscriptions_tracked"] == len(module.SUBSCRIPTIONS)
    assert payload["scheduler_running"] is True
    assert payload["started_at"]
    dependency_ids = {dependency["id"] for dependency in payload["dependencies"]}
    assert dependency_ids == {
        "task_directory",
        "scheduler_loop",
        "reaper_loop",
        "provider_catalog",
        "burn_registry",
        "cli_router_index",
        "ntfy_topic",
    }
    assert "burn.execute" in payload["actions_allowed"]
    assert payload["timestamp"]
    assert payload["burn_registry_version"] == "test-burn-registry"


def test_live_scheduler_surface_only_tracks_catalog_backed_burn_lanes(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    module, _, _ = subscription_burn_client

    assert set(module.SUBSCRIPTIONS) == {
        "claude_max",
        "chatgpt_pro",
        "gemini_advanced",
        "kimi_allegretto",
    }
    assert "zai_glm_pro" not in module.SUBSCRIPTIONS
    assert "venice_pro" not in module.SUBSCRIPTIONS


def test_schedule_comes_from_burn_registry(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    module, client, _ = subscription_burn_client

    response = client.get("/schedule")

    assert response.status_code == 200
    payload = response.json()
    assert payload["burn_registry_version"] == "test-burn-registry"
    assert {window["id"] for window in payload["windows"]} == {"morning", "midday", "evening", "overnight"}
    assert any(window["subscriptions"] == ["claude_max", "chatgpt_pro"] for window in payload["windows"])
    assert len(payload["windows"]) == len(module.BURN_SCHEDULE)


def test_subscription_truth_comes_from_provider_catalog(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    module, _, _ = subscription_burn_client

    claude_truth = module.get_subscription_truth("claude_max")
    kimi_truth = module.get_subscription_truth("kimi_allegretto")

    assert claude_truth == {
        "provider_id": "anthropic_claude_code",
        "label": "Claude Code",
        "subscription_product": "Claude Max",
        "known_monthly_cost": 200,
        "pricing_status": "official_verified",
    }
    assert kimi_truth == {
        "provider_id": "moonshot_kimi",
        "label": "Kimi Code",
        "subscription_product": "Kimi Membership / Kimi Code",
        "known_monthly_cost": None,
        "pricing_status": "official-source-present-cost-unverified",
    }


def test_manual_burn_requires_operator_envelope_and_audits_denial(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    _, client, audit_events = subscription_burn_client

    response = client.post("/burn/claude_max", json={})

    assert response.status_code == 400
    assert "missing required fields" in response.json()["error"]
    assert audit_events[-1]["route"] == "/burn/{subscription}"
    assert audit_events[-1]["decision"] == "denied"


def test_manual_burn_emits_accepted_audit(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, client, audit_events = subscription_burn_client
    execute_burn = AsyncMock(
        return_value={
            "subscription": "claude_max",
            "pid": 1234,
            "started_at": "2026-03-27T12:00:00+00:00",
        }
    )
    monkeypatch.setattr(module, "execute_burn", execute_burn)

    response = client.post(
        "/burn/claude_max",
        json={
            "actor": "operator",
            "session_id": "sess-1",
            "correlation_id": "corr-1",
            "reason": "Run manual subscription burn",
        },
    )

    assert response.status_code == 200
    execute_burn.assert_awaited_once_with("claude_max", manual=True)
    assert audit_events[-1]["route"] == "/burn/{subscription}"
    assert audit_events[-1]["decision"] == "accepted"
    assert audit_events[-1]["target"] == "claude_max"


def test_dispatch_route_requires_operator_envelope_and_audits_denial(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    _, client, audit_events = subscription_burn_client

    response = client.post("/dispatch", json={"description": "Route the next task"})

    assert response.status_code == 400
    assert "missing required fields" in response.json()["error"]
    assert audit_events[-1]["route"] == "/dispatch"
    assert audit_events[-1]["decision"] == "denied"


def test_dispatch_route_passes_canonical_operator_action_to_router(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, client, audit_events = subscription_burn_client
    dispatch = AsyncMock(
        return_value={
            "routing": {
                "cli": "claude",
                "subscription": "claude_max",
                "task_type": "feature_dev",
            },
            "dispatch": {"status": "queued"},
        }
    )
    monkeypatch.setattr(module._cli_router, "dispatch", dispatch)

    response = client.post(
        "/dispatch",
        json={
            "actor": "operator",
            "session_id": "sess-2",
            "correlation_id": "corr-2",
            "reason": "Dispatch routed task",
            "description": "Implement the next feature slice",
        },
    )

    assert response.status_code == 200
    dispatch.assert_awaited_once_with(
        {"description": "Implement the next feature slice"},
        dry_run=False,
        operator_action={
            "actor": "operator",
            "session_id": "sess-2",
            "correlation_id": "corr-2",
            "reason": "Dispatch routed task",
            "dry_run": False,
            "protected_mode": False,
        },
    )
    assert audit_events[-1]["route"] == "/dispatch"
    assert audit_events[-1]["decision"] == "accepted"


def test_record_result_requires_operator_envelope_and_audits_denial(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    _, client, audit_events = subscription_burn_client

    response = client.post(
        "/record-result",
        json={"cli": "claude", "task_type": "feature_dev", "success": True, "duration": 12.5},
    )

    assert response.status_code == 400
    assert "missing required fields" in response.json()["error"]
    assert audit_events[-1]["route"] == "/record-result"
    assert audit_events[-1]["decision"] == "denied"


def test_invalidate_cache_requires_operator_envelope_and_audits_denial(
    subscription_burn_client: tuple[object, TestClient, list[dict[str, object]]],
) -> None:
    _, client, audit_events = subscription_burn_client

    response = client.post("/router/invalidate-cache", json={})

    assert response.status_code == 400
    assert "missing required fields" in response.json()["error"]
    assert audit_events[-1]["route"] == "/router/invalidate-cache"
    assert audit_events[-1]["decision"] == "denied"


def test_cli_router_uses_topology_urls_and_forwards_operator_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"cli_router_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "cli-router.py",
    )
    router = module.CLIRouter()
    monkeypatch.setattr(
        router,
        "route",
        AsyncMock(
            return_value={
                "cli": "claude",
                "subscription": "claude_max",
                "task_type": "feature_dev",
                "confidence": 0.8,
                "method": "embedding",
                "reason": "test",
                "alternatives": [],
            }
        ),
    )

    captured: dict[str, object] = {}

    class DummyClient:
        async def post(self, url: str, json: dict[str, object] | None = None) -> httpx.Response:
            captured["url"] = url
            captured["json"] = json
            return httpx.Response(200, json={"status": "queued"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(router, "_client", AsyncMock(return_value=DummyClient()))

    result = asyncio.run(
        router.dispatch(
            {"description": "Implement the next feature slice"},
            operator_action={
                "actor": "operator",
                "session_id": "sess-3",
                "correlation_id": "corr-3",
                "reason": "Dispatch routed task",
            },
        )
    )

    assert "127.0.0.1" not in module.EMBEDDING_URL
    assert "127.0.0.1" not in module.SUBSCRIPTION_BURN_URL
    assert captured["url"] == f"{module.SUBSCRIPTION_BURN_URL}/burn/claude_max"
    assert captured["json"] == {
        "operator_action": {
            "actor": "operator",
            "session_id": "sess-3",
            "correlation_id": "corr-3",
            "reason": "Dispatch routed task",
        }
    }
    assert result["dispatch"]["status"] == "queued"
