from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_post_mutation_adds_operator_envelope(monkeypatch):
    module = _load_module(
        f"mcp_athanor_agents_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "mcp-athanor-agents.py",
    )

    captured: dict[str, object] = {}

    class DummyClient:
        def post(self, url: str, json: dict[str, object] | None = None, timeout: int = 30) -> httpx.Response:
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(module, "_client", DummyClient())

    response = module._post_mutation(
        "/v1/tasks",
        {"agent": "research-agent", "prompt": "Audit autonomy"},
        reason="Submit background task to research-agent",
        timeout=15,
    )

    assert response.status_code == 200
    assert captured["url"] == f"{module.AGENT_URL}/v1/tasks"
    payload = captured["json"]
    assert payload["agent"] == "research-agent"
    assert payload["prompt"] == "Audit autonomy"
    assert payload["actor"] == "mcp-athanor-agents"
    assert payload["session_id"].startswith("mcp-athanor-agents-")
    assert payload["correlation_id"]
    assert payload["reason"] == "Submit background task to research-agent"
    assert payload["protected_mode"] is False
    assert captured["timeout"] == 15


def test_submit_task_uses_mutation_helper(monkeypatch):
    module = _load_module(
        f"mcp_athanor_agents_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "mcp-athanor-agents.py",
    )

    captured: dict[str, object] = {}

    def fake_post_mutation(path: str, payload: dict[str, object] | None, *, reason: str, timeout: int = 30, protected_mode: bool = False):
        captured["path"] = path
        captured["payload"] = payload
        captured["reason"] = reason
        captured["timeout"] = timeout
        captured["protected_mode"] = protected_mode
        return httpx.Response(
            200,
            json={"task": {"id": "task-1", "agent": "research-agent", "status": "pending"}},
            request=httpx.Request("POST", f"{module.AGENT_URL}{path}"),
        )

    monkeypatch.setattr(module, "_post_mutation", fake_post_mutation)

    result = module.submit_task("research-agent", "Research the next autonomy blocker", priority="high")

    assert captured["path"] == "/v1/tasks"
    assert captured["payload"] == {
        "agent": "research-agent",
        "prompt": "Research the next autonomy blocker",
        "priority": "high",
    }
    assert captured["reason"] == "Submit background task to research-agent"
    assert captured["timeout"] == 15
    assert "task-1" in result


def test_mutating_tools_route_through_post_mutation(monkeypatch):
    module = _load_module(
        f"mcp_athanor_agents_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "mcp-athanor-agents.py",
    )

    calls: list[dict[str, object]] = []

    def fake_post_mutation(path: str, payload: dict[str, object] | None, *, reason: str, timeout: int = 30, protected_mode: bool = False):
        calls.append(
            {
                "path": path,
                "payload": dict(payload or {}),
                "reason": reason,
                "timeout": timeout,
                "protected_mode": protected_mode,
            }
        )
        response_json: dict[str, object] = {"status": "ok"}
        if path == "/v1/preferences":
            response_json = {"status": "stored"}
        elif path == "/v1/pipeline/cycle":
            response_json = {"intents_mined": 1, "intents_new": 1, "plans_created": 2, "tasks_spawned": 3}
        elif path == "/v1/improvement/trigger":
            response_json = {"status": "started", "proposals_generated": 4}
        elif path.endswith("/review"):
            response_json = {"quality_score": 0.8, "agent": "coding-agent", "status": "completed"}
        elif path.endswith("/supervise"):
            response_json = {"milestones_created": 2, "total_milestones": 3}
        return httpx.Response(200, json=response_json, request=httpx.Request("POST", f"{module.AGENT_URL}{path}"))

    monkeypatch.setattr(module, "_post_mutation", fake_post_mutation)

    module.store_preference("Prefer terse reports", agent="global", category="ui")
    module.trigger_pipeline_cycle()
    module.trigger_improvement_cycle()
    module.review_task_output("task-9")
    module.supervise_project("athanor", "Close the next autonomy seam")

    assert calls == [
        {
            "path": "/v1/preferences",
            "payload": {
                "agent": "global",
                "signal_type": "remember_this",
                "content": "Prefer terse reports",
                "category": "ui",
            },
            "reason": "Store preference for global",
            "timeout": 15,
            "protected_mode": False,
        },
        {
            "path": "/v1/pipeline/cycle",
            "payload": {},
            "reason": "Trigger pipeline cycle from MCP bridge",
            "timeout": 60,
            "protected_mode": False,
        },
        {
            "path": "/v1/improvement/trigger",
            "payload": {},
            "reason": "Trigger improvement cycle from MCP bridge",
            "timeout": 60,
            "protected_mode": False,
        },
        {
            "path": "/v1/tasks/task-9/review",
            "payload": {},
            "reason": "Review completed task task-9",
            "timeout": 30,
            "protected_mode": False,
        },
        {
            "path": "/v1/projects/athanor/supervise",
            "payload": {"instruction": "Close the next autonomy seam"},
            "reason": "Supervise project athanor",
            "timeout": 30,
            "protected_mode": False,
        },
    ]
