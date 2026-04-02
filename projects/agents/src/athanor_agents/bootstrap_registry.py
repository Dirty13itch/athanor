from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import settings


def _default_registry_path(filename: str) -> Path:
    target_parts = ("config", "automation-backbone", filename)
    preferred: Path | None = None
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if base.joinpath("STATUS.md").exists() and candidate.exists():
            return candidate
        if candidate.exists():
            preferred = candidate
    if preferred is not None:
        return preferred
    for base in Path(__file__).resolve().parents:
        candidate = base.joinpath(*target_parts)
        if candidate.exists():
            return candidate
    return Path("/workspace").joinpath(*target_parts)


def _resolve_builder_registry_path() -> Path:
    configured = str(getattr(settings, "bootstrap_builder_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("bootstrap-builder-registry.json")


def _resolve_program_registry_path() -> Path:
    configured = str(getattr(settings, "bootstrap_program_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("bootstrap-program-registry.json")


def _resolve_takeover_registry_path() -> Path:
    configured = str(getattr(settings, "bootstrap_takeover_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("bootstrap-takeover-registry.json")


def _resolve_slice_catalog_path() -> Path:
    configured = str(getattr(settings, "bootstrap_slice_catalog_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("bootstrap-slice-catalog.json")


def _resolve_execution_policy_path() -> Path:
    configured = str(getattr(settings, "bootstrap_execution_policy_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("bootstrap-execution-policy.json")


def _resolve_foundry_proving_registry_path() -> Path:
    configured = str(getattr(settings, "foundry_proving_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("foundry-proving-registry.json")


def _resolve_governance_drill_registry_path() -> Path:
    configured = str(getattr(settings, "governance_drill_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("governance-drill-registry.json")


def _resolve_approval_packet_registry_path() -> Path:
    configured = str(getattr(settings, "approval_packet_registry_path", "") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_registry_path("approval-packet-registry.json")


@lru_cache(maxsize=1)
def load_bootstrap_builder_registry() -> dict[str, Any]:
    path = _resolve_builder_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    hosts = data.get("hosts")
    if not isinstance(hosts, list):
        raise ValueError(f"Bootstrap builder registry at {path} must contain a 'hosts' list")
    return data


@lru_cache(maxsize=1)
def load_bootstrap_program_registry() -> dict[str, Any]:
    path = _resolve_program_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    families = data.get("families")
    programs = data.get("programs")
    if not isinstance(families, list):
        raise ValueError(f"Bootstrap program registry at {path} must contain a 'families' list")
    if not isinstance(programs, list):
        raise ValueError(f"Bootstrap program registry at {path} must contain a 'programs' list")
    return data


@lru_cache(maxsize=1)
def load_bootstrap_takeover_registry() -> dict[str, Any]:
    path = _resolve_takeover_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    criteria = data.get("criteria")
    if not isinstance(criteria, list):
        raise ValueError(f"Bootstrap takeover registry at {path} must contain a 'criteria' list")
    return data


@lru_cache(maxsize=1)
def load_bootstrap_slice_catalog() -> dict[str, Any]:
    path = _resolve_slice_catalog_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    families = data.get("families")
    slices = data.get("slices")
    if not isinstance(families, list):
        raise ValueError(f"Bootstrap slice catalog at {path} must contain a 'families' list")
    if not isinstance(slices, list):
        raise ValueError(f"Bootstrap slice catalog at {path} must contain a 'slices' list")
    return data


@lru_cache(maxsize=1)
def load_bootstrap_execution_policy() -> dict[str, Any]:
    path = _resolve_execution_policy_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Bootstrap execution policy at {path} must be a JSON object")
    return data


@lru_cache(maxsize=1)
def load_foundry_proving_registry() -> dict[str, Any]:
    path = _resolve_foundry_proving_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Foundry proving registry at {path} must be a JSON object")
    return data


@lru_cache(maxsize=1)
def load_governance_drill_registry() -> dict[str, Any]:
    path = _resolve_governance_drill_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    drills = data.get("drills")
    if not isinstance(drills, list):
        raise ValueError(f"Governance drill registry at {path} must contain a 'drills' list")
    return data


@lru_cache(maxsize=1)
def load_approval_packet_registry() -> dict[str, Any]:
    path = _resolve_approval_packet_registry_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    packet_types = data.get("packet_types")
    if not isinstance(packet_types, list):
        raise ValueError(f"Approval packet registry at {path} must contain a 'packet_types' list")
    return data


def reset_bootstrap_registry_cache() -> None:
    load_bootstrap_builder_registry.cache_clear()
    load_bootstrap_program_registry.cache_clear()
    load_bootstrap_takeover_registry.cache_clear()
    load_bootstrap_slice_catalog.cache_clear()
    load_bootstrap_execution_policy.cache_clear()
    load_foundry_proving_registry.cache_clear()
    load_governance_drill_registry.cache_clear()
    load_approval_packet_registry.cache_clear()


def get_bootstrap_hosts() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_bootstrap_builder_registry().get("hosts", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def get_bootstrap_host(host_id: str) -> dict[str, Any] | None:
    for item in get_bootstrap_hosts():
        if str(item.get("id") or "") == host_id:
            return item
    return None


def get_bootstrap_families() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_bootstrap_program_registry().get("families", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def get_bootstrap_family(family_id: str) -> dict[str, Any] | None:
    for item in get_bootstrap_families():
        if str(item.get("id") or "") == family_id:
            return item
    return None


def get_bootstrap_programs() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_bootstrap_program_registry().get("programs", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def get_bootstrap_program(program_id: str) -> dict[str, Any] | None:
    for item in get_bootstrap_programs():
        if str(item.get("id") or "") == program_id:
            return item
    return None


def get_default_bootstrap_program() -> dict[str, Any] | None:
    default_id = str(load_bootstrap_program_registry().get("default_program_id") or "").strip()
    if default_id:
        return get_bootstrap_program(default_id)
    programs = get_bootstrap_programs()
    return programs[0] if programs else None


def get_bootstrap_takeover_registry() -> dict[str, Any]:
    return dict(load_bootstrap_takeover_registry())


def get_bootstrap_takeover_criteria() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_bootstrap_takeover_registry().get("criteria", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def get_bootstrap_slice_catalog() -> dict[str, Any]:
    return dict(load_bootstrap_slice_catalog())


def get_bootstrap_slice_definitions(*, family: str = "") -> list[dict[str, Any]]:
    family_id = str(family or "").strip()
    items = []
    for item in load_bootstrap_slice_catalog().get("slices", []):
        if not isinstance(item, dict):
            continue
        slice_id = str(item.get("id") or "").strip()
        if not slice_id:
            continue
        if family_id and str(item.get("family") or "").strip() != family_id:
            continue
        items.append(dict(item))
    return items


def get_bootstrap_execution_policy() -> dict[str, Any]:
    return dict(load_bootstrap_execution_policy())


def get_foundry_proving_registry() -> dict[str, Any]:
    return dict(load_foundry_proving_registry())


def get_governance_drill_registry() -> dict[str, Any]:
    return dict(load_governance_drill_registry())


def get_governance_drills() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_governance_drill_registry().get("drills", [])
        if isinstance(item, dict) and str(item.get("drill_id") or "").strip()
    ]


def get_approval_packet_registry() -> dict[str, Any]:
    return dict(load_approval_packet_registry())


def get_approval_packet_types() -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in load_approval_packet_registry().get("packet_types", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def build_bootstrap_registry_snapshot() -> dict[str, Any]:
    builder_registry = load_bootstrap_builder_registry()
    program_registry = load_bootstrap_program_registry()
    takeover_registry = load_bootstrap_takeover_registry()
    slice_catalog = load_bootstrap_slice_catalog()
    execution_policy = load_bootstrap_execution_policy()
    foundry_proving = load_foundry_proving_registry()
    governance_drills = load_governance_drill_registry()
    approval_packets = load_approval_packet_registry()
    hosts = get_bootstrap_hosts()
    families = get_bootstrap_families()
    programs = get_bootstrap_programs()
    criteria = get_bootstrap_takeover_criteria()
    slice_families = [
        dict(item)
        for item in slice_catalog.get("families", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    slices = get_bootstrap_slice_definitions()
    drills = get_governance_drills()
    packet_types = get_approval_packet_types()
    return {
        "builder_hosts": {
            "version": builder_registry.get("version", "unknown"),
            "default_failover_strategy": builder_registry.get("default_failover_strategy", "automatic_relay"),
            "integration_policy": builder_registry.get("integration_policy", "serial_after_validation"),
            "count": len(hosts),
            "hosts": hosts,
        },
        "programs": {
            "version": program_registry.get("version", "unknown"),
            "default_program_id": program_registry.get("default_program_id", ""),
            "family_count": len(families),
            "program_count": len(programs),
            "families": families,
            "programs": programs,
        },
        "takeover": {
            "version": takeover_registry.get("version", "unknown"),
            "promotion_rule": takeover_registry.get("promotion_rule", "explicit_promotion_only"),
            "criteria_count": len(criteria),
            "criteria": criteria,
            "external_posture": takeover_registry.get("external_posture", {}),
        },
        "slice_catalog": {
            "version": slice_catalog.get("version", "unknown"),
            "family_count": len(slice_families),
            "slice_count": len(slices),
            "families": slice_families,
            "slices": slices,
        },
        "execution_policy": {
            "version": execution_policy.get("version", "unknown"),
            "handoff_schema_version": execution_policy.get("handoff_schema_version", "unknown"),
            "worktree": dict(execution_policy.get("worktree") or {}),
            "integration": dict(execution_policy.get("integration") or {}),
            "concurrency": dict(execution_policy.get("concurrency") or {}),
            "scheduling": dict(execution_policy.get("scheduling") or {}),
        },
        "foundry_proving": {
            "version": foundry_proving.get("version", "unknown"),
            "project_id": str(foundry_proving.get("project_id") or ""),
            "first_proving_slice_id": str(foundry_proving.get("first_proving_slice_id") or ""),
            "validator_bundle": list(foundry_proving.get("validator_bundle") or []),
            "promotion_gate": dict(foundry_proving.get("promotion_gate") or {}),
            "acceptance_evidence_requirements": list(foundry_proving.get("acceptance_evidence_requirements") or []),
        },
        "governance_drills": {
            "version": governance_drills.get("version", "unknown"),
            "evidence_root": str(governance_drills.get("evidence_root") or ""),
            "drill_count": len(drills),
            "drills": drills,
        },
        "approval_packets": {
            "version": approval_packets.get("version", "unknown"),
            "packet_type_count": len(packet_types),
            "packet_types": packet_types,
        },
    }
