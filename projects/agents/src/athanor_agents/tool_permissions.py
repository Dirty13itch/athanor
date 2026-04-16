from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .model_governance import get_tool_permission_registry


SUBJECT_CLASS_ALIASES: dict[str, str] = {
    "meta lane": "meta_lanes",
    "meta lanes": "meta_lanes",
    "meta strategy": "meta_lanes",
    "frontier cloud": "meta_lanes",
    "sovereign local": "meta_lanes",
    "specialist agent": "specialist_agents",
    "specialist agents": "specialist_agents",
    "workers": "workers",
    "worker": "workers",
    "judges": "judges",
    "judge": "judges",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def _humanize_subject(subject_id: str) -> str:
    return subject_id.replace("_", " ").replace("-", " ").strip().title()


def _normalize_subject_profile(item: dict[str, Any], default_mode: str) -> dict[str, Any]:
    subject_id = str(item.get("id") or item.get("subject") or "subject").strip()
    mode = str(
        item.get("mode")
        or ("scoped_execution" if bool(item.get("direct_execution")) else default_mode)
    ).strip() or default_mode
    allow = [str(entry) for entry in list(item.get("allow") or item.get("allowed_tools") or []) if str(entry).strip()]
    deny = [str(entry) for entry in list(item.get("deny") or item.get("restricted_tools") or []) if str(entry).strip()]
    return {
        "subject": subject_id,
        "label": str(item.get("label") or _humanize_subject(subject_id)),
        "mode": mode,
        "allow": allow,
        "deny": deny,
        "direct_execution": bool(item.get("direct_execution", mode == "scoped_execution")),
    }


def _resolve_subject_class(subject: str) -> str:
    normalized = _normalize_text(subject)
    if normalized in SUBJECT_CLASS_ALIASES:
        return SUBJECT_CLASS_ALIASES[normalized]
    if normalized.endswith("agent") or normalized.endswith("agents"):
        return "specialist_agents"
    if "judge" in normalized or "verifier" in normalized:
        return "judges"
    if "worker" in normalized:
        return "workers"
    return normalized.replace(" ", "_") or "unknown"


def _matches_rule(terms: list[str], rules: list[str]) -> tuple[bool, str | None]:
    normalized_terms = [_normalize_text(term) for term in terms if _normalize_text(term)]
    normalized_rules = [rule for rule in rules if rule]
    for rule in normalized_rules:
        for term in normalized_terms:
            if term == rule or rule in term or term in rule:
                return True, rule
    return False, None


def build_tool_permission_snapshot() -> dict[str, Any]:
    registry = get_tool_permission_registry()
    default_mode = str(registry.get("default_mode") or "governor_mediated")
    subjects = [
        _normalize_subject_profile(dict(item), default_mode)
        for item in registry.get("subjects", [])
        if isinstance(item, dict)
    ]
    mode_counts: dict[str, int] = {}
    for item in subjects:
        mode = str(item.get("mode") or default_mode)
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    return {
        "generated_at": _now_iso(),
        "version": str(registry.get("version") or "unknown"),
        "status": str(registry.get("status") or "configured"),
        "default_mode": default_mode,
        "subject_count": len(subjects),
        "mode_counts": mode_counts,
        "subjects": subjects,
    }


def evaluate_tool_permission(
    subject: str,
    action: str,
    *,
    tool_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = build_tool_permission_snapshot()
    subject_class = _resolve_subject_class(subject)
    profiles = {str(item.get("subject")): dict(item) for item in snapshot.get("subjects", [])}
    profile = dict(
        profiles.get(
            subject_class,
            {
                "subject": subject_class,
                "label": _humanize_subject(subject_class),
                "mode": snapshot["default_mode"],
                "allow": [],
                "deny": [],
                "direct_execution": False,
            },
        )
    )
    metadata = dict(metadata or {})

    terms = [action]
    if tool_name:
        terms.append(tool_name)
    if metadata.get("action"):
        terms.append(str(metadata["action"]))
    if metadata.get("tool"):
        terms.append(str(metadata["tool"]))
    if metadata.get("task_class"):
        terms.append(str(metadata["task_class"]))

    normalized_allow = [_normalize_text(item) for item in profile.get("allow", [])]
    normalized_deny = [_normalize_text(item) for item in profile.get("deny", [])]
    deny_hit, deny_rule = _matches_rule(terms, normalized_deny)
    allow_hit, allow_rule = _matches_rule(terms, normalized_allow)

    if deny_hit:
        allowed = False
        reason = (
            f"{profile['label']} may not perform '{action}' because it matches the denied capability "
            f"'{deny_rule}'."
        )
    elif allow_hit:
        allowed = True
        reason = (
            f"{profile['label']} may perform '{action}' because it matches the allow-listed capability "
            f"'{allow_rule}'."
        )
    else:
        allowed = False
        reason = (
            f"{profile['label']} may not perform '{action}' because it is outside the governed allow-list for "
            f"{profile['mode']} execution."
        )

    return {
        "generated_at": snapshot["generated_at"],
        "subject": subject,
        "subject_class": subject_class,
        "label": profile["label"],
        "action": action,
        "tool_name": tool_name,
        "mode": profile["mode"],
        "allowed": allowed,
        "reason": reason,
        "matched_allow": allow_rule,
        "matched_deny": deny_rule,
        "allow": list(profile.get("allow", [])),
        "deny": list(profile.get("deny", [])),
        "direct_execution": bool(profile.get("direct_execution")),
        "status": snapshot["status"],
        "version": snapshot["version"],
    }
