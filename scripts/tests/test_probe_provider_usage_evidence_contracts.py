from __future__ import annotations

import importlib.util
import sys
import uuid
from pathlib import Path

import httpx


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


class _TimeoutClient:
    def post(self, *args, **kwargs):
        raise httpx.ReadTimeout('timed out')


def test_probe_provider_returns_request_failed_capture_on_http_timeout() -> None:
    module = _load_module(
        f"probe_provider_usage_evidence_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "probe_provider_usage_evidence.py",
    )
    provider = {
        "id": "venice_api",
        "evidence": {
            "kind": "vault_litellm_proxy",
            "proxy": {
                "alias": "venice-uncensored",
                "preferred_models": ["venice-uncensored"],
                "served_model_match_tokens": ["venice"],
            },
        },
    }
    module.load_catalog_provider = lambda provider_id: provider

    capture = module._probe_provider(
        'venice_api',
        client=_TimeoutClient(),
        api_key='test-key',
        base_url='http://192.168.1.203:4000',
        served_models=['venice-uncensored'],
        extra_notes=[],
    )

    assert capture['status'] == 'request_failed'
    assert capture['http_status'] is None
    assert 'timed out' in str(capture['error_snippet'])
    assert capture['request_surface'] == 'POST http://192.168.1.203:4000/v1/chat/completions'
