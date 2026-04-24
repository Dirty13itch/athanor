from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "automation-backbone"
WINDOWS_ABS_PATH_RE = re.compile(r"^(?P<drive>[A-Za-z]):[\\/](?P<rest>.*)$")
EXTERNAL_ROOT_ENV_OVERRIDES = {
    "c:/athanor": "ATHANOR_IMPLEMENTATION_AUTHORITY",
    "c:/athanor-devstack": "ATHANOR_DEVSTACK_ROOT",
    "c:/codex system config": "ATHANOR_CODEX_ROOT",
}


def _resolve_external_override(text: str) -> Path | None:
    normalized = text.replace("\\", "/")
    lowered = normalized.lower().rstrip("/")
    for external_root, env_var in EXTERNAL_ROOT_ENV_OVERRIDES.items():
        override_root = os.environ.get(env_var, "").strip()
        if not override_root:
            continue
        if lowered == external_root or lowered.startswith(external_root + "/"):
            suffix = normalized[len(external_root) :].lstrip("/\\")
            resolved_root = Path(override_root)
            return resolved_root / suffix if suffix else resolved_root
    return None


def resolve_external_path(raw: str | Path | None, *, base: Path | None = None) -> Path:
    text = str(raw or "").strip()
    if not text:
        return base or REPO_ROOT
    normalized = text.replace("\\", "/")
    lowered = normalized.lower().rstrip("/")
    overridden = _resolve_external_override(text)
    if overridden is not None:
        return overridden
    match = WINDOWS_ABS_PATH_RE.match(text)
    if match:
        rest = match.group("rest").replace("\\", "/").lstrip("/")
        canonical_external_root = any(
            lowered == external_root or lowered.startswith(external_root + "/")
            for external_root in EXTERNAL_ROOT_ENV_OVERRIDES
        )
        if os.name == "nt" and not canonical_external_root:
            return Path(f"{match.group('drive').upper()}:/{rest}")
        return Path("/mnt") / match.group("drive").lower() / rest
    path = Path(text)
    if path.is_absolute():
        return path
    return (base or REPO_ROOT) / text


_implementation_authority_override = os.environ.get("ATHANOR_IMPLEMENTATION_AUTHORITY", "").strip()
IMPLEMENTATION_AUTHORITY_ROOT = resolve_external_path(_implementation_authority_override or REPO_ROOT)

_repo_roots_registry_path = CONFIG_DIR / "repo-roots-registry.json"
if not _implementation_authority_override and _repo_roots_registry_path.exists():
    try:
        _repo_roots_registry = json.loads(_repo_roots_registry_path.read_text(encoding="utf-8"))
        _implementation_root = next(
            (
                str(root.get("path") or "").strip()
                for root in _repo_roots_registry.get("roots", [])
                if str(root.get("authority_level") or "") == "implementation-authority"
                and str(root.get("status") or "active") == "active"
                and str(root.get("path") or "").strip()
            ),
            "",
        )
        if _implementation_root:
            IMPLEMENTATION_AUTHORITY_ROOT = resolve_external_path(_implementation_root)
    except json.JSONDecodeError:
        pass

REPORT_PATHS = {
    "hardware": REPO_ROOT / "docs" / "operations" / "HARDWARE-REPORT.md",
    "models": REPO_ROOT / "docs" / "operations" / "MODEL-DEPLOYMENT-REPORT.md",
    "providers": REPO_ROOT / "docs" / "operations" / "PROVIDER-CATALOG-REPORT.md",
    "operator_surfaces": REPO_ROOT / "docs" / "operations" / "OPERATOR-SURFACE-REPORT.md",
    "tooling": REPO_ROOT / "docs" / "operations" / "TOOLING-INVENTORY-REPORT.md",
    "repo_roots": REPO_ROOT / "docs" / "operations" / "REPO-ROOTS-REPORT.md",
    "runtime_ownership": REPO_ROOT / "docs" / "operations" / "RUNTIME-OWNERSHIP-REPORT.md",
    "runtime_ownership_packets": REPO_ROOT / "docs" / "operations" / "RUNTIME-OWNERSHIP-PACKETS.md",
    "runtime_migrations": REPO_ROOT / "docs" / "operations" / "RUNTIME-MIGRATION-REPORT.md",
    "runtime_cutover": REPO_ROOT / "docs" / "operations" / "GOVERNOR-FACADE-CUTOVER-PACKET.md",
    "vault_litellm_repair_packet": REPO_ROOT / "docs" / "operations" / "VAULT-LITELLM-AUTH-REPAIR-PACKET.md",
    "vault_redis_repair_packet": REPO_ROOT / "docs" / "operations" / "VAULT-REDIS-REPAIR-PACKET.md",
    "autonomy_activation": REPO_ROOT / "docs" / "operations" / "AUTONOMY-ACTIVATION-REPORT.md",
    "drift": REPO_ROOT / "docs" / "operations" / "TRUTH-DRIFT-REPORT.md",
    "secret_surfaces": REPO_ROOT / "docs" / "operations" / "SECRET-SURFACE-REPORT.md",
    "surface_owner_matrix": REPO_ROOT / "docs" / "operations" / "SURFACE-OWNER-MATRIX.md",
    "publication_provenance": REPO_ROOT / "docs" / "operations" / "PUBLICATION-PROVENANCE-REPORT.md",
}
TRUTH_SNAPSHOT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "latest.json"
BOOTSTRAP_REPORTS_DIR = REPO_ROOT / "reports" / "bootstrap"
PROVIDER_USAGE_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "provider-usage-evidence.json"
PLANNED_SUBSCRIPTION_EVIDENCE_PATH = REPO_ROOT / "reports" / "truth-inventory" / "planned-subscription-evidence.json"
VAULT_LITELLM_ENV_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-litellm-env-audit.json"
VAULT_REDIS_AUDIT_PATH = REPO_ROOT / "reports" / "truth-inventory" / "vault-redis-audit.json"
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
