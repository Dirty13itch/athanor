from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path


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


def test_sync_provider_catalog_freshness_updates_latest_vault_probe_fields(tmp_path: Path, monkeypatch) -> None:
    module = _load_module(
        f"sync_provider_catalog_freshness_{uuid.uuid4().hex}",
        SCRIPTS_DIR / "sync_provider_catalog_freshness.py",
    )
    provider_catalog = {
        "version": "2026-04-13.0",
        "updated_at": "2026-04-13T21:09:06Z",
        "providers": [
            {
                "id": "anthropic_api",
                "evidence": {
                    "kind": "vault_litellm_proxy",
                    "provider_specific_usage": {
                        "status": "observed",
                        "last_verified_at": "2026-04-08T05:48:41Z",
                    },
                },
                "observed_runtime": {
                    "provider_specific_usage_observed": True,
                    "last_verified_at": "2026-04-08T05:48:41Z",
                },
                "notes": [
                    "The 2026-04-08 live VAULT provider probe now succeeds through the `claude` compatibility alias after the governed LiteLLM config reconcile restored the served-model contract."
                ],
            },
            {
                "id": "venice_api",
                "evidence": {
                    "kind": "vault_litellm_proxy",
                    "provider_specific_usage": {
                        "status": "observed",
                        "last_verified_at": "2026-04-08T00:08:35Z",
                    },
                },
                "observed_runtime": {
                    "provider_specific_usage_observed": True,
                    "last_verified_at": "2026-04-08T05:24:29Z",
                },
                "notes": [
                    "Venice remains configured as an API lane.",
                    "Provider-specific completion proof is current through 2026-04-08.",
                ],
            },
            {
                "id": "openai_api",
                "evidence": {
                    "kind": "vault_litellm_proxy",
                    "provider_specific_usage": {
                        "status": "auth_failed",
                        "last_verified_at": "2026-04-08T05:24:28Z",
                    },
                },
                "observed_runtime": {
                    "provider_specific_usage_observed": False,
                    "last_verified_at": "2026-04-08T05:24:28Z",
                },
                "notes": [
                    "Latest live VAULT provider probe classified this lane as auth_failed even though OPENAI_API_KEY is now present in the container env."
                ],
            },
        ],
    }
    evidence_path = tmp_path / "provider-usage-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "captures": [
                    {
                        "provider_id": "anthropic_api",
                        "observed_at": "2026-04-14T00:51:19Z",
                        "status": "observed",
                    },
                    {
                        "provider_id": "venice_api",
                        "observed_at": "2026-04-14T00:51:24Z",
                        "status": "observed",
                    },
                    {
                        "provider_id": "openai_api",
                        "observed_at": "2026-04-14T00:51:24Z",
                        "status": "auth_failed",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "load_registry", lambda name: provider_catalog)
    monkeypatch.setattr(module, "PROVIDER_USAGE_EVIDENCE_PATH", evidence_path)

    synced_catalog, touched = module.sync_provider_catalog_freshness()

    assert touched == ["anthropic_api", "venice_api", "openai_api"]
    synced = {provider["id"]: provider for provider in synced_catalog["providers"]}
    assert synced["anthropic_api"]["observed_runtime"]["last_verified_at"] == "2026-04-14T00:51:19Z"
    assert synced["anthropic_api"]["evidence"]["provider_specific_usage"]["last_verified_at"] == "2026-04-14T00:51:19Z"
    assert synced["anthropic_api"]["notes"][0].startswith("The 2026-04-14 live VAULT provider probe now succeeds")
    assert synced["venice_api"]["notes"][1] == "Provider-specific completion proof is current through 2026-04-14."
    assert synced["openai_api"]["observed_runtime"]["provider_specific_usage_observed"] is False
    assert synced_catalog["version"].startswith("2026-")
