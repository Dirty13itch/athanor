from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest


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


def test_choose_served_model_prefers_catalog_preferred_model() -> None:
    module = _load_module(
        f"provider_usage_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "provider_usage_evidence.py",
    )
    provider = {
        "id": "openai_api",
        "evidence": {
            "kind": "vault_litellm_proxy",
            "proxy": {
                "alias": "gpt",
                "preferred_models": ["gpt", "gpt-5-mini"],
                "served_model_match_tokens": ["gpt", "o4"],
            },
        },
    }

    model, matched_by = module.choose_served_model(provider, ["gpt-5-mini", "gpt-4", "o4-mini"])

    assert model == "gpt-5-mini"
    assert matched_by == "preferred_exact"


def test_choose_served_model_falls_back_to_token_match() -> None:
    module = _load_module(
        f"provider_usage_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "provider_usage_evidence.py",
    )
    provider = {
        "id": "dashscope_qwen_api",
        "evidence": {
            "kind": "vault_litellm_proxy",
            "proxy": {
                "alias": "qwen-max",
                "preferred_models": ["qwen-max", "qwen-plus"],
                "served_model_match_tokens": ["qwen"],
            },
        },
    }

    model, matched_by = module.choose_served_model(provider, ["qwen-turbo"])

    assert model == "qwen-turbo"
    assert matched_by == "token:qwen"


def test_classify_probe_failure_detects_auth_failures() -> None:
    module = _load_module(
        f"provider_usage_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "provider_usage_evidence.py",
    )

    assert module.classify_probe_failure(401, "No cookie auth credentials found") == "auth_failed"
    assert module.classify_probe_failure(500, "AuthenticationError: OPENAI_API_KEY missing") == "auth_failed"
    assert module.classify_probe_failure(500, "upstream timeout") == "request_failed"


def test_record_provider_usage_evidence_persists_richer_capture_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        f"record_provider_usage_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "record_provider_usage_evidence.py",
    )
    output = tmp_path / "provider-usage-evidence.json"
    provider_catalog = {
        "providers": [
            {
                "id": "deepseek_api",
                "evidence": {
                    "kind": "vault_litellm_proxy",
                    "proxy": {
                        "alias": "deepseek",
                    }
                },
            }
        ]
    }

    monkeypatch.setattr(module, "load_catalog_provider", lambda provider_id: provider_catalog["providers"][0])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_provider_usage_evidence.py",
            "--provider-id",
            "deepseek_api",
            "--status",
            "observed",
            "--source",
            "vault-litellm-live-probe",
            "--requested-model",
            "deepseek-chat",
            "--response-model",
            "deepseek-chat",
            "--matched-by",
            "preferred_exact",
            "--http-status",
            "200",
            "--request-surface",
            "POST http://vault/v1/chat/completions",
            "--write",
            str(output),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    capture = payload["captures"][0]
    assert capture["alias"] == "deepseek"
    assert capture["requested_model"] == "deepseek-chat"
    assert capture["response_model"] == "deepseek-chat"
    assert capture["matched_by"] == "preferred_exact"
    assert capture["http_status"] == 200
