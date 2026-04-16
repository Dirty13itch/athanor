from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from truth_inventory import load_optional_json, load_registry


PROVIDER_CATALOG_PATH = REPO_ROOT / "config" / "automation-backbone" / "provider-catalog.json"
PROVIDER_USAGE_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"

CURRENT_THROUGH_PATTERN = re.compile(r"Provider-specific completion proof is current through \d{4}-\d{2}-\d{2}\.")
LIVE_PROBE_DATE_PATTERN = re.compile(r"The \d{4}-\d{2}-\d{2} live VAULT provider probe")
PROVIDER_CATALOG_HEADER_PATTERN = re.compile(r"provider-catalog\.json@\d{4}-\d{2}-\d{2}\.\d+")
HEADER_SYNC_PATHS = [
    REPO_ROOT / "docs" / "TROUBLESHOOTING.md",
    REPO_ROOT / "docs" / "runbooks" / "vault-litellm-provider-auth-repair.md",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _version_for_today(current_version: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prefix, _, suffix = str(current_version or "").partition(".")
    if prefix == today:
        try:
            return f"{today}.{int(suffix or '0') + 1}"
        except ValueError:
            return f"{today}.1"
    return f"{today}.0"


def _latest_capture_by_provider(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for capture in captures:
        provider_id = str(capture.get("provider_id") or "").strip()
        observed_at = str(capture.get("observed_at") or "").strip()
        if not provider_id or not observed_at:
            continue
        existing = latest.get(provider_id)
        if existing is None or observed_at > str(existing.get("observed_at") or ""):
            latest[provider_id] = capture
    return latest


def _sync_header_versions(provider_catalog_version: str) -> None:
    replacement = f"provider-catalog.json@{provider_catalog_version}"
    for path in HEADER_SYNC_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        updated = PROVIDER_CATALOG_HEADER_PATTERN.sub(replacement, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def _refresh_notes(notes: list[Any], latest_observed_at: str, latest_status: str, alias: str) -> list[Any]:
    latest_date = latest_observed_at[:10]
    refreshed: list[Any] = []
    for note in notes:
        if not isinstance(note, str):
            refreshed.append(note)
            continue
        updated = note
        if "live VAULT provider probe now succeeds through" in updated:
            if latest_status in {"observed", "verified"}:
                updated = LIVE_PROBE_DATE_PATTERN.sub(
                    f"The {latest_date} live VAULT provider probe",
                    updated,
                )
            else:
                updated = (
                    f"The {latest_date} live VAULT provider probe no longer completed through the `{alias}` alias; "
                    f"the latest provider-specific request ended in `{latest_status}`, so keep the lane demoted until completion succeeds again."
                )
        elif CURRENT_THROUGH_PATTERN.search(updated):
            if latest_status in {"observed", "verified"}:
                updated = CURRENT_THROUGH_PATTERN.sub(
                    f"Provider-specific completion proof is current through {latest_date}.",
                    updated,
                )
            else:
                updated = (
                    f"Latest live VAULT provider probe ended in `{latest_status}` on {latest_date}; "
                    "keep the lane demoted until provider-specific completion succeeds again."
                )
        refreshed.append(updated)
    return refreshed


def sync_provider_catalog_freshness() -> tuple[dict[str, Any], list[str]]:
    catalog = deepcopy(load_registry("provider-catalog.json"))
    evidence_document = load_optional_json(PROVIDER_USAGE_EVIDENCE_PATH)
    captures = [
        capture
        for capture in evidence_document.get("captures", [])
        if isinstance(capture, dict)
    ]
    latest_by_provider = _latest_capture_by_provider(captures)
    touched: list[str] = []

    for provider in catalog.get("providers", []):
        if not isinstance(provider, dict):
            continue
        provider_id = str(provider.get("id") or "").strip()
        latest_capture = latest_by_provider.get(provider_id)
        evidence = dict(provider.get("evidence") or {})
        alias = str((dict(evidence.get("proxy") or {}).get("alias") or provider_id)).strip() or provider_id
        if not provider_id or str(evidence.get("kind") or "") != "vault_litellm_proxy" or latest_capture is None:
            continue

        latest_observed_at = str(latest_capture.get("observed_at") or "").strip()
        if not latest_observed_at:
            continue

        provider_changed = False

        observed_runtime = dict(provider.get("observed_runtime") or {})
        if observed_runtime.get("last_verified_at") != latest_observed_at:
            observed_runtime["last_verified_at"] = latest_observed_at
            provider_changed = True
        expected_observed = str(latest_capture.get("status") or "") == "observed"
        if observed_runtime.get("provider_specific_usage_observed") != expected_observed:
            observed_runtime["provider_specific_usage_observed"] = expected_observed
            provider_changed = True
        provider["observed_runtime"] = observed_runtime

        provider_specific_usage = dict(evidence.get("provider_specific_usage") or {})
        if provider_specific_usage.get("last_verified_at") != latest_observed_at:
            provider_specific_usage["last_verified_at"] = latest_observed_at
            provider_changed = True
        latest_status = str(latest_capture.get("status") or "").strip()
        if latest_status and provider_specific_usage.get("status") != latest_status:
            provider_specific_usage["status"] = latest_status
            provider_changed = True
        evidence["provider_specific_usage"] = provider_specific_usage
        provider["evidence"] = evidence

        refreshed_notes = _refresh_notes(list(provider.get("notes") or []), latest_observed_at, latest_status, alias)
        if refreshed_notes != provider.get("notes"):
            provider["notes"] = refreshed_notes
            provider_changed = True

        if provider_changed:
            touched.append(provider_id)

    if touched:
        catalog["updated_at"] = _utc_now()
        catalog["version"] = _version_for_today(str(catalog.get("version") or ""))
        _sync_header_versions(str(catalog["version"]))
    return catalog, touched


def main() -> int:
    catalog, touched = sync_provider_catalog_freshness()
    _sync_header_versions(str(catalog.get("version") or ""))
    if not touched:
        print("provider-catalog freshness already current")
        return 0
    PROVIDER_CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print("updated provider-catalog freshness for:", ", ".join(touched))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
