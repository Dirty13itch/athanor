from __future__ import annotations

import asyncio
import importlib.util
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


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


def test_canonical_cli_candidates_derive_from_policy_lease(monkeypatch) -> None:
    module = _load_module(
        f"cli_router_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "cli-router.py",
    )
    module._POLICY_CACHE = None
    module._PROVIDER_SNAPSHOT_CACHE = None

    monkeypatch.setattr(
        module,
        "_load_policy",
        lambda: {
            "task_classes": {
                "multi_file_implementation": {
                    "primary": ["anthropic_claude_code"],
                    "fallback": ["openai_codex", "athanor_local", "zai_glm_coding"],
                }
            },
            "providers": {
                "anthropic_claude_code": {"routing_posture": "ordinary_auto"},
                "openai_codex": {"routing_posture": "ordinary_auto"},
                "athanor_local": {"routing_posture": "ordinary_auto"},
                "zai_glm_coding": {"routing_posture": "governed_handoff_only"},
            }
        },
    )
    monkeypatch.setattr(
        module,
        "_provider_catalog_snapshot",
        lambda: {
            "providers": [
                {"id": "anthropic_claude_code", "access_mode": "cli", "cli_commands": ["claude"]},
                {"id": "openai_codex", "access_mode": "cli", "cli_commands": ["codex"]},
                {"id": "athanor_local", "access_mode": "local", "cli_commands": []},
                {"id": "zai_glm_coding", "access_mode": "cli", "cli_commands": ["glm"]},
            ]
        },
    )

    candidates = module._canonical_cli_candidates("feature_dev", "Implement the next feature slice")

    assert candidates == [
        ("anthropic_claude_code", "claude"),
        ("openai_codex", "codex"),
    ]


def test_route_uses_canonical_policy_preference(monkeypatch) -> None:
    module = _load_module(
        f"cli_router_contract_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "cli-router.py",
    )
    router = module.CLIRouter()

    monkeypatch.setattr(router, "classify_task", AsyncMock(return_value=("feature_dev", 0.91, "embedding")))
    monkeypatch.setattr(
        module,
        "_canonical_cli_candidates",
        lambda task_type, task_description: [
            ("anthropic_claude_code", "claude"),
            ("openai_codex", "codex"),
        ],
    )

    async def fake_available() -> dict[str, bool]:
        router._cli_to_subscription = {"claude": "claude_max", "codex": "chatgpt_pro"}
        router._cli_to_provider = {
            "claude": "anthropic_claude_code",
            "codex": "openai_codex",
        }
        return {"claude": True, "codex": True}

    monkeypatch.setattr(router, "get_available_clis", fake_available)

    decision = asyncio.run(router.route({"description": "Implement the next feature slice"}))

    assert decision["cli"] == "claude"
    assert decision["subscription"] == "claude_max"
    assert decision["provider"] == "anthropic_claude_code"
    assert decision["alternatives"] == ["codex"]
    assert "policy_preference" in decision["reason"]
    assert "policy_task_class=multi_file_implementation" in decision["reason"]
