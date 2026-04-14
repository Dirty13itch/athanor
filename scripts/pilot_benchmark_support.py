from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TRACE_STRING_FIELDS = (
    "trace_id",
    "scenario_id",
    "request_surface",
    "policy_class",
    "decision_summary",
    "decision_reason",
    "command_decision_record_ref",
    "operator_stream_event_ref",
)
REQUIRED_TRACE_LIST_FIELDS = (
    "allowed_actions",
    "blocked_actions",
)


def load_json_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def validate_decision_trace_payload(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    for field in REQUIRED_TRACE_STRING_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"missing_or_invalid_field:{field}")

    for field in REQUIRED_TRACE_LIST_FIELDS:
        value = payload.get(field)
        if not isinstance(value, list):
            errors.append(f"missing_or_invalid_field:{field}")
            continue
        invalid_items = [item for item in value if not isinstance(item, str) or not item.strip()]
        if invalid_items:
            errors.append(f"invalid_list_items:{field}")

    return errors


def validate_decision_trace_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    result: dict[str, Any] = {
        "path": str(file_path),
        "exists": file_path.exists(),
        "valid": False,
        "errors": [],
        "trace_id": None,
        "scenario_id": None,
        "policy_class": None,
    }
    if not file_path.exists():
        result["errors"] = ["file_missing"]
        return result

    try:
        payload = load_json_file(file_path)
    except json.JSONDecodeError as exc:
        result["errors"] = [f"invalid_json:{exc.msg}"]
        return result

    errors = validate_decision_trace_payload(payload)
    result["errors"] = errors
    result["valid"] = not errors
    if isinstance(payload, dict):
        result["trace_id"] = payload.get("trace_id")
        result["scenario_id"] = payload.get("scenario_id")
        result["policy_class"] = payload.get("policy_class")
        result["payload"] = payload
    return result


def dump_json_file(path: str | Path, payload: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sorted_unique_strings(values: list[Any]) -> list[str]:
    return sorted({str(item).strip() for item in values if isinstance(item, str) and str(item).strip()})


def build_policy_diff_summary(native_payload: dict[str, Any], bridge_payload: dict[str, Any]) -> str:
    native_allowed = _sorted_unique_strings(list(native_payload.get("allowed_actions") or []))
    bridge_allowed = _sorted_unique_strings(list(bridge_payload.get("allowed_actions") or []))
    native_blocked = _sorted_unique_strings(list(native_payload.get("blocked_actions") or []))
    bridge_blocked = _sorted_unique_strings(list(bridge_payload.get("blocked_actions") or []))

    native_only_allowed = [item for item in native_allowed if item not in bridge_allowed]
    bridge_only_allowed = [item for item in bridge_allowed if item not in native_allowed]
    native_only_blocked = [item for item in native_blocked if item not in bridge_blocked]
    bridge_only_blocked = [item for item in bridge_blocked if item not in native_blocked]

    lines = [
        "# AGT Policy Bridge Diff Summary",
        "",
        f"- Scenario: `{native_payload.get('scenario_id')}`",
        f"- Request surface: `{native_payload.get('request_surface')}`",
        f"- Native policy class: `{native_payload.get('policy_class')}`",
        f"- Bridge policy class: `{bridge_payload.get('policy_class')}`",
        f"- Native decision: {native_payload.get('decision_summary')}",
        f"- Bridge decision: {bridge_payload.get('decision_summary')}",
        f"- Native decision reason: {native_payload.get('decision_reason')}",
        f"- Bridge decision reason: {bridge_payload.get('decision_reason')}",
        "",
        "## Allowed Action Diffs",
        "",
        f"- Native-only allowed: {', '.join(f'`{item}`' for item in native_only_allowed) if native_only_allowed else 'none'}",
        f"- Bridge-only allowed: {', '.join(f'`{item}`' for item in bridge_only_allowed) if bridge_only_allowed else 'none'}",
        "",
        "## Blocked Action Diffs",
        "",
        f"- Native-only blocked: {', '.join(f'`{item}`' for item in native_only_blocked) if native_only_blocked else 'none'}",
        f"- Bridge-only blocked: {', '.join(f'`{item}`' for item in bridge_only_blocked) if bridge_only_blocked else 'none'}",
        "",
        "## Audit Lineage",
        "",
        f"- Native command decision record: `{native_payload.get('command_decision_record_ref')}`",
        f"- Native operator stream event: `{native_payload.get('operator_stream_event_ref')}`",
        f"- Bridge command decision record: `{bridge_payload.get('command_decision_record_ref')}`",
        f"- Bridge operator stream event: `{bridge_payload.get('operator_stream_event_ref')}`",
    ]
    return "\n".join(lines) + "\n"


def build_rollback_note(native_payload: dict[str, Any], bridge_payload: dict[str, Any]) -> str:
    lines = [
        "# AGT Policy Bridge Rollback Note",
        "",
        f"- Scenario: `{native_payload.get('scenario_id')}`",
        f"- Native enforcement trace: `{native_payload.get('trace_id')}`",
        f"- AGT bridge trace: `{bridge_payload.get('trace_id')}`",
        "- Rollback target: return control to native Athanor approval, routing, and audit governance surfaces.",
        "- Rollback trigger: any AGT-backed bridge path that widens permissions, weakens audit lineage, or obscures the fallback reason.",
        f"- Native command-decision lineage remains authoritative at `{native_payload.get('command_decision_record_ref')}`.",
        f"- Native operator-stream lineage remains authoritative at `{native_payload.get('operator_stream_event_ref')}`.",
    ]
    return "\n".join(lines) + "\n"
