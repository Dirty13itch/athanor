from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from truth_inventory import PROVIDER_USAGE_EVIDENCE_PATH, REPO_ROOT, load_optional_json, load_registry


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


AUTH_FAILURE_MARKERS = (
    "authenticationerror",
    "api key",
    "missing anthropic api key",
    "openaiexception",
    "geminiexception",
    "moonshotexception",
    "dashscopeexception",
    "zaiexception",
    "openrouterexception",
    "no cookie auth credentials",
    "invalid api key",
    "the api_key client option must be set",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def provider_catalog_index() -> dict[str, dict[str, Any]]:
    catalog = load_registry("provider-catalog.json")
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in catalog.get("providers", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }


def load_catalog_provider(provider_id: str) -> dict[str, Any]:
    provider = provider_catalog_index().get(provider_id)
    if provider is None:
        raise SystemExit(f"Unknown provider id: {provider_id}")
    return provider


def iter_vault_proxy_provider_ids() -> list[str]:
    provider_ids: list[str] = []
    for provider_id, provider in provider_catalog_index().items():
        evidence = dict(provider.get("evidence") or {})
        if str(evidence.get("kind") or "") == "vault_litellm_proxy":
            provider_ids.append(provider_id)
    return sorted(provider_ids)


def load_document(path: Path = PROVIDER_USAGE_EVIDENCE_PATH) -> dict[str, Any]:
    document = load_optional_json(path)
    if not document:
        return {
            "version": "2026-03-29.1",
            "updated_at": utc_now(),
            "captures": [],
        }
    document.setdefault("version", "2026-03-29.1")
    document.setdefault("captures", [])
    return document


def append_capture(capture: dict[str, Any], path: Path = PROVIDER_USAGE_EVIDENCE_PATH) -> None:
    document = load_document(path)
    captures = [entry for entry in document.get("captures", []) if isinstance(entry, dict)]
    captures.append(dict(capture))
    captures.sort(key=lambda entry: (str(entry.get("provider_id") or ""), str(entry.get("observed_at") or "")))
    document["updated_at"] = utc_now()
    document["captures"] = captures
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_litellm_api_key() -> str:
    return (
        os.environ.get("ATHANOR_LITELLM_API_KEY", "").strip()
        or os.environ.get("LITELLM_API_KEY", "").strip()
        or os.environ.get("LITELLM_MASTER_KEY", "").strip()
    )


def litellm_base_url() -> str:
    from services.cluster_config import get_url

    return get_url("litellm").rstrip("/")


def litellm_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def list_served_models(*, client: httpx.Client, base_url: str, api_key: str) -> list[str]:
    response = client.get(f"{base_url}/v1/models", headers=litellm_headers(api_key))
    response.raise_for_status()
    payload = response.json()
    return [
        str(entry.get("id") or "").strip()
        for entry in payload.get("data", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]


def proxy_probe_metadata(provider: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    evidence = dict(provider.get("evidence") or {})
    if str(evidence.get("kind") or "") != "vault_litellm_proxy":
        raise SystemExit(f"Provider {provider.get('id')} does not use the vault_litellm_proxy evidence contract")
    proxy = dict(evidence.get("proxy") or {})
    alias = str(proxy.get("alias") or "").strip()
    preferred_models = [
        str(model).strip()
        for model in proxy.get("preferred_models", [])
        if str(model).strip()
    ]
    match_tokens = [
        str(token).strip().lower()
        for token in proxy.get("served_model_match_tokens", [])
        if str(token).strip()
    ]
    return alias, preferred_models, match_tokens


def choose_served_model(provider: dict[str, Any], available_models: list[str]) -> tuple[str | None, str]:
    alias, preferred_models, match_tokens = proxy_probe_metadata(provider)
    available = [str(model).strip() for model in available_models if str(model).strip()]
    available_lower = {model.lower(): model for model in available}

    for model in preferred_models:
        exact = available_lower.get(model.lower())
        if exact:
            return exact, "preferred_exact"

    if alias:
        exact_alias = available_lower.get(alias.lower())
        if exact_alias:
            return exact_alias, "alias_exact"

    for token in match_tokens:
        for model in available:
            if token in model.lower():
                return model, f"token:{token}"

    return None, "no_match"


def classify_probe_failure(status_code: int, error_text: str) -> str:
    lowered = error_text.lower()
    if status_code in {401, 403}:
        return "auth_failed"
    if any(marker in lowered for marker in AUTH_FAILURE_MARKERS):
        return "auth_failed"
    return "request_failed"
