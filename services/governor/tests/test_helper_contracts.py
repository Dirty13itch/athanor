from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import types

SERVICE_DIR = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, filename: str):
    module_path = SERVICE_DIR / filename
    imports_module = types.ModuleType("_imports")
    imports_module.AGENT_SERVER_URL = "http://agent-server.test"
    imports_module.DASHBOARD_URL = "http://dashboard.test"
    imports_module.NTFY_URL = "http://ntfy.test"
    sys.modules["_imports"] = imports_module
    if "requests" not in sys.modules:
        requests_module = types.ModuleType("requests")
        requests_module.RequestException = Exception
        requests_module.get = lambda *args, **kwargs: None
        requests_module.post = lambda *args, **kwargs: None
        requests_module.patch = lambda *args, **kwargs: None
        sys.modules["requests"] = requests_module

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load governor helper module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_real_imports_module():
    module_path = SERVICE_DIR / "_imports.py"
    spec = importlib.util.spec_from_file_location("athanor_governor_real_imports", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load governor import shim from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


overnight = _load_module("athanor_governor_overnight", "overnight.py")
self_improve = _load_module("athanor_governor_self_improve", "self_improve.py")
act_first = _load_module("athanor_governor_act_first", "act_first.py")
status_report = _load_module("athanor_governor_status_report", "status_report.py")
ACTIVE_HELPER_PATHS = {
    "overnight.py": SERVICE_DIR / "overnight.py",
    "self_improve.py": SERVICE_DIR / "self_improve.py",
    "act_first.py": SERVICE_DIR / "act_first.py",
    "status_report.py": SERVICE_DIR / "status_report.py",
    "_imports.py": SERVICE_DIR / "_imports.py",
}
LOCAL_STATE_TOKENS = (
    "sqlite",
    "sqlite3",
    "GOVERNOR_DB",
    "task_queue",
    "active_agents",
    "tmux",
    "/tmp/agent-worktrees",
)
LOCAL_STATE_TOKEN_EXEMPTIONS = {}
LEGACY_QUEUE_ROUTE_TOKENS = (
    "/queue",
    "/dispatch-and-run",
)


def _read_helper_source(filename: str) -> str:
    return ACTIVE_HELPER_PATHS[filename].read_text(encoding="utf-8")


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload: dict | list | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def test_overnight_get_pending_tasks_reads_canonical_pending_tasks(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, capture_output=True, text=True):
        captured["cmd"] = cmd
        return types.SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"tasks": [{"id": "task-1", "status": "pending"}]}),
        )

    monkeypatch.setattr(overnight.subprocess, "run", _fake_run)

    tasks = overnight.get_pending_tasks()

    assert tasks == [{"id": "task-1", "status": "pending"}]
    assert captured["cmd"] == [
        "curl",
        "-sf",
        "http://agent-server.test/v1/tasks?status=pending&limit=50",
    ]


def test_overnight_dispatch_task_posts_operator_envelope_to_canonical_dispatch(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, capture_output=True, text=True):
        captured["cmd"] = cmd
        return types.SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"task_id": "task-1", "agent": "coding-agent"}),
        )

    monkeypatch.setattr(overnight.subprocess, "run", _fake_run)

    result = overnight.dispatch_task()

    assert result == {"task_id": "task-1", "agent": "coding-agent"}
    cmd = captured["cmd"]
    assert cmd[:5] == ["curl", "-sf", "-X", "POST", "http://agent-server.test/v1/tasks/dispatch"]
    payload = json.loads(cmd[cmd.index("-d") + 1])
    assert payload["actor"] == "overnight-governor"
    assert payload["session_id"] == "overnight-governor"
    assert payload["reason"] == "Overnight dispatch cycle"
    assert payload["correlation_id"]


def test_overnight_uses_pending_task_language_in_notifications(monkeypatch) -> None:
    captured: list[tuple[str, str, str]] = []

    monkeypatch.setattr(overnight, "get_pending_tasks", lambda: [])
    monkeypatch.setattr(
        overnight,
        "notify",
        lambda title, message, priority="default": captured.append((title, message, priority)),
    )

    overnight.run_overnight()

    assert len(captured) == 1
    title, message, priority = captured[0]
    assert title == "Overnight: No Pending Tasks"
    assert "No pending tasks" in message
    assert priority == "low"


def test_self_improve_create_task_posts_canonical_task_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return types.SimpleNamespace(
            status_code=200,
            json=lambda: {"task": {"id": "task-9"}},
        )

    marked: list[str] = []
    monkeypatch.setattr(self_improve.requests, "post", _fake_post)
    monkeypatch.setattr(self_improve, "_agent_headers", lambda: {"Authorization": "Bearer token"})
    monkeypatch.setattr(self_improve, "mark_proposal_processed", lambda proposal_id: marked.append(proposal_id))

    result = self_improve.create_task_from_proposal(
        {
            "id": "proposal-1",
            "title": "Close safety drift",
            "description": "Tighten the canonical task seam",
            "category": "safety",
        }
    )

    assert result == {"task": {"id": "task-9"}}
    assert captured["url"] == "http://agent-server.test/v1/tasks"
    assert captured["headers"] == {"Authorization": "Bearer token"}
    assert captured["timeout"] == 30
    payload = captured["json"]
    assert payload["agent"] == "coding-agent"
    assert payload["actor"] == "self-improve-loop"
    assert payload["session_id"] == "self-improve-loop"
    assert payload["reason"] == "Submitted improvement proposal proposal-1"
    assert payload["metadata"] == {
        "source": "self_improve_loop",
        "proposal_id": "proposal-1",
        "proposal_category": "safety",
        "requires_approval": True,
    }
    assert marked == ["proposal-1"]


def test_active_helper_sources_do_not_reintroduce_local_state_ownership() -> None:
    for filename in ACTIVE_HELPER_PATHS:
        source = _read_helper_source(filename)
        for token in LOCAL_STATE_TOKENS:
            if token in LOCAL_STATE_TOKEN_EXEMPTIONS.get(filename, set()):
                continue
            assert token not in source, f"{filename} reintroduced retired local-state token {token!r}"


def test_import_shim_does_not_export_legacy_governor_url() -> None:
    source = _read_helper_source("_imports.py")
    assert "GOVERNOR_URL" not in source


def test_import_shim_loads_against_real_cluster_config() -> None:
    module = _load_real_imports_module()

    assert module.AGENT_SERVER_URL
    assert module.DASHBOARD_URL
    assert module.NTFY_URL
    assert not hasattr(module, "GOVERNOR_URL")


def test_active_helpers_do_not_keep_legacy_queue_route_tokens() -> None:
    for filename in ACTIVE_HELPER_PATHS:
        source = _read_helper_source(filename)
        for token in LEGACY_QUEUE_ROUTE_TOKENS:
            assert token not in source, f"{filename} reintroduced retired compatibility route token {token!r}"


def test_act_first_reads_canonical_tasks_and_reports_results(monkeypatch) -> None:
    captured: dict[str, object] = {"urls": [], "notifications": []}

    def _fake_get(url, timeout=None):
        captured["urls"].append((url, timeout))
        return _FakeResponse(
            payload={
                "tasks": [
                    {"id": "task-1", "status": "completed", "assigned_runtime": "foundry", "prompt": "Completed thing"},
                    {"id": "task-2", "status": "failed", "assigned_runtime": "workshop", "prompt": "Failed thing"},
                ]
            }
        )

    def _fake_notify(title, message, priority="default", tags="robot"):
        captured["notifications"].append((title, message, priority, tags))

    monkeypatch.setattr(act_first.requests, "get", _fake_get)
    monkeypatch.setattr(act_first, "notify", _fake_notify)

    act_first.report_completed_tasks()

    assert captured["urls"] == [("http://agent-server.test/v1/tasks?limit=50", 5)]
    notifications = captured["notifications"]
    assert len(notifications) == 2
    assert notifications[0][0] == "Task Done: Completed thing"
    assert "canonical task results" in notifications[0][1]
    assert notifications[1][0] == "Task Failed: Failed thing"
    assert "canonical task state before retrying" in notifications[1][1]


def test_status_report_reads_canonical_surfaces(monkeypatch) -> None:
    captured: list[tuple[str, int | None]] = []

    def _fake_get(url, timeout=None):
        captured.append((url, timeout))
        if url.endswith("/v1/goals"):
            return _FakeResponse(payload={"goals": [{"active": True, "priority": "high", "agent": "coding-agent", "text": "Finish truth"}]})
        if url.endswith("/v1/tasks/stats"):
            return _FakeResponse(
                payload={
                    "pending": 1,
                    "pending_approval": 2,
                    "running": 3,
                    "completed": 4,
                    "failed": 5,
                    "cancelled": 6,
                }
            )
        if url.endswith("/v1/improvement/proposals"):
            return _FakeResponse(payload={"proposals": [{"status": "proposed", "category": "safety", "title": "Close drift"}]})
        if url.endswith("/health"):
            return _FakeResponse(payload={"agents": ["coding-agent", "research-agent"]})
        if url.endswith("/api/subscriptions/summary"):
            return _FakeResponse(payload={"provider_summaries": [{"direct_execution_ready": True, "governed_handoff_ready": True}]})
        if url.endswith("/v1/skills"):
            return _FakeResponse(payload={"skills": ["routing", "audit"]})
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(status_report.requests, "get", _fake_get)

    report = status_report.generate_report()

    assert ("http://agent-server.test/v1/goals", 10) in captured
    assert ("http://agent-server.test/v1/tasks/stats", 10) in captured
    assert ("http://agent-server.test/v1/improvement/proposals", 10) in captured
    assert ("http://agent-server.test/health", 10) in captured
    assert ("http://dashboard.test/api/subscriptions/summary", 10) in captured
    assert ("http://agent-server.test/v1/skills", 10) in captured
    assert "TASK ENGINE:" in report
    assert "SUBSCRIPTIONS: 1 providers | 1 direct-ready | 1 handoff-ready" in report
