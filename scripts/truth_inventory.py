from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"

REPORT_PATHS = {
    "hardware": REPO_ROOT / "docs" / "operations" / "HARDWARE-REPORT.md",
    "models": REPO_ROOT / "docs" / "operations" / "MODEL-DEPLOYMENT-REPORT.md",
    "providers": REPO_ROOT / "docs" / "operations" / "PROVIDER-CATALOG-REPORT.md",
    "operator_surfaces": REPO_ROOT / "docs" / "operations" / "OPERATOR-SURFACE-REPORT.md",
    "tooling": REPO_ROOT / "docs" / "operations" / "TOOLING-INVENTORY-REPORT.md",
    "repo_roots": REPO_ROOT / "docs" / "operations" / "REPO-ROOTS-REPORT.md",
    "runtime_migrations": REPO_ROOT / "docs" / "operations" / "RUNTIME-MIGRATION-REPORT.md",
    "runtime_cutover": REPO_ROOT / "docs" / "operations" / "GOVERNOR-FACADE-CUTOVER-PACKET.md",
    "vault_litellm_repair_packet": REPO_ROOT / "docs" / "operations" / "VAULT-LITELLM-AUTH-REPAIR-PACKET.md",
    "autonomy_activation": REPO_ROOT / "docs" / "operations" / "AUTONOMY-ACTIVATION-REPORT.md",
    "drift": REPO_ROOT / "docs" / "operations" / "TRUTH-DRIFT-REPORT.md",
    "secret_surfaces": REPO_ROOT / "docs" / "operations" / "SECRET-SURFACE-REPORT.md",
}
TRUTH_SNAPSHOT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "latest.json"
PROVIDER_USAGE_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"
VAULT_LITELLM_ENV_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-litellm-env-audit.json"
DASHBOARD_OPERATOR_SURFACES_PATH = (
    REPO_ROOT / "projects" / "dashboard" / "src" / "generated" / "operator-surfaces.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def load_registry(name: str) -> dict[str, Any]:
    return load_json(CONFIG_DIR / name)


def provider_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("id") or ""): dict(entry)
        for entry in catalog.get("providers", [])
        if str(entry.get("id") or "").strip()
    }


def list_or_none(values: list[str]) -> str:
    cleaned = [str(value) for value in values if str(value).strip()]
    return ", ".join(f"`{value}`" for value in cleaned) if cleaned else "none"


def render_link_list(sources: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for source in sources:
        label = str(source.get("label") or source.get("url") or "").strip()
        url = str(source.get("url") or "").strip()
        if not label and not url:
            continue
        rendered.append(f"[{label}]({url})" if url else label)
    return ", ".join(rendered) if rendered else "none"


def collect_known_drifts(*registries: dict[str, Any]) -> list[dict[str, Any]]:
    drifts: list[dict[str, Any]] = []
    for registry in registries:
        for entry in registry.get("known_drifts", []) or []:
            if isinstance(entry, dict) and str(entry.get("status") or "active") == "active":
                drifts.append(dict(entry))
    return drifts
