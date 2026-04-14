from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from truth_inventory import PLANNED_SUBSCRIPTION_EVIDENCE_PATH, REPO_ROOT, load_optional_json, load_registry


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


ALLOWED_STATUSES = {
    "tooling_present",
    "tooling_ready",
    "supported_tool_usage_observed",
    "missing_tooling",
    "activation_blocked",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def burn_registry_index() -> dict[str, dict[str, Any]]:
    registry = load_registry("subscription-burn-registry.json")
    entries = registry.get("planned_subscriptions", [])
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }


def provider_catalog_index() -> dict[str, dict[str, Any]]:
    catalog = load_registry("provider-catalog.json")
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in catalog.get("providers", [])
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    }


def load_planned_subscription(family_id: str) -> dict[str, Any]:
    family = burn_registry_index().get(family_id)
    if family is None:
        raise SystemExit(f"Unknown planned subscription family id: {family_id}")
    return family


def load_catalog_provider(provider_id: str) -> dict[str, Any]:
    provider = provider_catalog_index().get(provider_id)
    if provider is None:
        raise SystemExit(f"Unknown provider id: {provider_id}")
    return provider


def load_document(path: Path = PLANNED_SUBSCRIPTION_EVIDENCE_PATH) -> dict[str, Any]:
    document = load_optional_json(path)
    if not document:
        return {
            "version": "2026-04-11.1",
            "updated_at": utc_now(),
            "captures": [],
        }
    document.setdefault("version", "2026-04-11.1")
    document.setdefault("captures", [])
    return document


def append_capture(capture: dict[str, Any], path: Path = PLANNED_SUBSCRIPTION_EVIDENCE_PATH) -> None:
    document = load_document(path)
    captures = [entry for entry in document.get("captures", []) if isinstance(entry, dict)]
    captures.append(dict(capture))
    captures.sort(key=lambda entry: (str(entry.get("family_id") or ""), str(entry.get("observed_at") or "")))
    document["updated_at"] = utc_now()
    document["captures"] = captures
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

