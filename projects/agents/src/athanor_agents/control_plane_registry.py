from __future__ import annotations

from typing import Any

from .model_governance import (
    get_attention_budget_registry,
    get_coding_lane_registry,
    get_core_change_window_registry,
    get_memory_namespace_registry,
    get_project_packet_registry,
    get_source_policy_registry,
    get_system_mode_registry,
)
from .bootstrap_registry import build_bootstrap_registry_snapshot


def _items(registry: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in registry.get(key, [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]


def get_coding_lanes() -> list[dict[str, Any]]:
    return _items(get_coding_lane_registry(), "lanes")


def get_memory_namespaces() -> list[dict[str, Any]]:
    return _items(get_memory_namespace_registry(), "namespaces")


def get_source_policies(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    items = _items(get_source_policy_registry(), "sources")
    if enabled_only:
        return [item for item in items if bool(item.get("enabled"))]
    return items


def get_project_packets() -> list[dict[str, Any]]:
    return _items(get_project_packet_registry(), "projects")


def get_project_packet(project_id: str) -> dict[str, Any] | None:
    for packet in get_project_packets():
        if str(packet.get("id") or "") == project_id:
            return packet
    return None


def get_system_modes() -> list[dict[str, Any]]:
    return _items(get_system_mode_registry(), "modes")


def get_attention_budgets_registry_entries() -> list[dict[str, Any]]:
    return _items(get_attention_budget_registry(), "budgets")


def get_core_change_windows() -> list[dict[str, Any]]:
    return _items(get_core_change_window_registry(), "windows")


def build_control_plane_registry_snapshot() -> dict[str, Any]:
    lanes = get_coding_lanes()
    namespaces = get_memory_namespaces()
    policies = get_source_policies()
    packets = get_project_packets()
    modes = get_system_modes()
    budgets = get_attention_budgets_registry_entries()
    windows = get_core_change_windows()
    return {
        "coding_lanes": {
            "count": len(lanes),
            "live": sum(1 for item in lanes if str(item.get("status") or "") == "live"),
            "lanes": lanes,
        },
        "memory_namespaces": {
            "count": len(namespaces),
            "local_only": sum(1 for item in namespaces if not bool(item.get("cloud_allowed"))),
            "namespaces": namespaces,
        },
        "source_policies": {
            "count": len(policies),
            "enabled": sum(1 for item in policies if bool(item.get("enabled"))),
            "sources": policies,
        },
        "project_packets": {
            "count": len(packets),
            "live": sum(1 for item in packets if str(item.get("status") or "") == "live"),
            "projects": packets,
        },
        "system_modes": {
            "count": len(modes),
            "default_mode": str(get_system_mode_registry().get("default_mode") or "normal"),
            "modes": modes,
        },
        "attention_budgets": {
            "count": len(budgets),
            "total_daily_limit": sum(int(item.get("daily_limit") or 0) for item in budgets),
            "budgets": budgets,
        },
        "core_change_windows": {
            "count": len(windows),
            "windows": windows,
        },
        "bootstrap": build_bootstrap_registry_snapshot(),
    }
