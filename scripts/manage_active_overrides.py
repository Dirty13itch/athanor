#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from routing_contract_support import append_history, dump_json, load_json

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_OVERRIDES_PATH = REPO_ROOT / "reports" / "truth-inventory" / "active-overrides.json"
LOCAL_TZ = ZoneInfo("America/Chicago")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().isoformat()


def _load_payload() -> dict[str, Any]:
    if ACTIVE_OVERRIDES_PATH.exists():
        payload = load_json(ACTIVE_OVERRIDES_PATH)
        if isinstance(payload, dict):
            payload.setdefault("active_overrides", [])
            payload.setdefault("history_streams", ["reports/history/overrides"])
            return payload
    return {
        "version": "2026-04-11.1",
        "updated_at": _iso_now(),
        "source_of_truth": "reports/truth-inventory/active-overrides.json",
        "policy": {
            "owner": "Shaun",
            "allowed_types": [
                "single_run_force",
                "temporary_disable",
                "temporary_promote",
                "budget_raise",
                "collector_bypass",
            ],
            "default_ttls": {
                "single_run_force": "single_execution",
                "routing_or_quota_override": "4h",
                "budget_raise": "until_local_midnight_america_chicago",
                "temporary_disable": "24h",
                "temporary_promote": "24h",
                "collector_bypass": "4h",
            },
            "required_audit_streams": [
                "command_decision_record",
                "operator_stream_event",
            ],
        },
        "history_streams": ["reports/history/overrides"],
        "active_overrides": [],
    }


def _save_payload(payload: dict[str, Any]) -> None:
    payload["updated_at"] = _iso_now()
    dump_json(ACTIVE_OVERRIDES_PATH, payload)


def _default_ttl(policy: dict[str, Any], override_type: str) -> str:
    ttl_map = dict(policy.get("default_ttls") or {})
    if override_type in ttl_map:
        return str(ttl_map[override_type])
    if override_type in {"temporary_disable", "temporary_promote", "collector_bypass"}:
        return str(ttl_map.get("routing_or_quota_override") or "4h")
    return "4h"


def _expires_from_ttl(ttl: str | None) -> tuple[str | None, int | None]:
    if not ttl:
        return None, None
    normalized = ttl.strip().lower()
    if not normalized:
        return None, None
    if normalized == "single_execution":
        return None, 1
    if normalized.startswith("until_local_midnight"):
        now_local = datetime.now(LOCAL_TZ)
        next_midnight = (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_midnight.astimezone(timezone.utc).isoformat(), None
    if normalized.endswith("h") and normalized[:-1].isdigit():
        return (_now() + timedelta(hours=int(normalized[:-1]))).isoformat(), None
    if normalized.endswith("m") and normalized[:-1].isdigit():
        return (_now() + timedelta(minutes=int(normalized[:-1]))).isoformat(), None
    raise ValueError(f"Unsupported TTL value: {ttl}")


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("metadata JSON must be an object")
    return loaded


def _build_audit_bundle(
    *,
    action: str,
    actor: str,
    session_id: str,
    correlation_id: str,
    reason: str,
    override_record: dict[str, Any],
) -> dict[str, Any]:
    created_at = _iso_now()
    decision_id = f"decision-{uuid.uuid4().hex[:12]}"
    event_id = f"override-event-{uuid.uuid4().hex[:12]}"
    return {
        "action": action,
        "recorded_at": created_at,
        "command_decision_record": {
            "id": decision_id,
            "decided_by": actor,
            "authority_layer": "operator",
            "policy_class": "manual_override",
            "reason": reason,
            "approved": True,
            "target": override_record.get("target"),
            "override_type": override_record.get("type"),
            "correlation_id": correlation_id,
            "session_id": session_id,
            "created_at": created_at,
        },
        "operator_stream_event": {
            "id": event_id,
            "event_type": f"override_{action}",
            "severity": "info",
            "actor": actor,
            "target": override_record.get("target"),
            "message": f"{action} override {override_record.get('type')} on {override_record.get('target')}",
            "correlation_id": correlation_id,
            "session_id": session_id,
            "created_at": created_at,
        },
        "override": override_record,
    }


def _expire_stale(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    now = _now()
    still_active: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    for item in payload.get("active_overrides", []):
        if not isinstance(item, dict):
            continue
        expires_at = item.get("expires_at")
        remaining_executions = item.get("remaining_executions")
        if expires_at:
            expires_dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expires_dt <= now:
                expired.append(dict(item))
                continue
        if remaining_executions == 0:
            expired.append(dict(item))
            continue
        still_active.append(dict(item))
    return still_active, expired


def cmd_list(_: argparse.Namespace) -> int:
    payload = _load_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    payload = _load_payload()
    policy = dict(payload.get("policy") or {})
    allowed_types = {str(item) for item in policy.get("allowed_types", [])}
    if args.override_type not in allowed_types:
        raise SystemExit(f"Unsupported override type: {args.override_type}")

    ttl = args.ttl or _default_ttl(policy, args.override_type)
    expires_at, remaining_executions = _expires_from_ttl(ttl)
    metadata = _parse_metadata(args.metadata_json)
    override_id = f"override-{uuid.uuid4().hex[:12]}"
    record = {
        "id": override_id,
        "type": args.override_type,
        "target": args.target,
        "reason": args.reason,
        "actor": args.actor,
        "session_id": args.session_id,
        "correlation_id": args.correlation_id or uuid.uuid4().hex,
        "ttl_policy": ttl,
        "remaining_executions": remaining_executions,
        "expires_at": expires_at,
        "created_at": _iso_now(),
        "metadata": metadata,
    }
    payload.setdefault("active_overrides", []).append(record)
    _save_payload(payload)
    append_history("overrides", _build_audit_bundle(
        action="added",
        actor=args.actor,
        session_id=args.session_id,
        correlation_id=record["correlation_id"],
        reason=args.reason,
        override_record=record,
    ))
    print(json.dumps({"path": str(ACTIVE_OVERRIDES_PATH), "override_id": override_id}, indent=2))
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    payload = _load_payload()
    removed: dict[str, Any] | None = None
    kept: list[dict[str, Any]] = []
    for item in payload.get("active_overrides", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("id")) == args.override_id and removed is None:
            removed = dict(item)
            continue
        kept.append(dict(item))
    if removed is None:
        raise SystemExit(f"Override not found: {args.override_id}")
    payload["active_overrides"] = kept
    _save_payload(payload)
    append_history("overrides", _build_audit_bundle(
        action="removed",
        actor=args.actor,
        session_id=args.session_id,
        correlation_id=args.correlation_id or uuid.uuid4().hex,
        reason=args.reason,
        override_record=removed,
    ))
    print(json.dumps({"path": str(ACTIVE_OVERRIDES_PATH), "removed": removed["id"]}, indent=2))
    return 0


def cmd_expire(args: argparse.Namespace) -> int:
    payload = _load_payload()
    active, expired = _expire_stale(payload)
    payload["active_overrides"] = active
    _save_payload(payload)
    correlation_id = args.correlation_id or uuid.uuid4().hex
    for item in expired:
        append_history("overrides", _build_audit_bundle(
            action="expired",
            actor=args.actor,
            session_id=args.session_id,
            correlation_id=correlation_id,
            reason=args.reason,
            override_record=item,
        ))
    print(json.dumps({"path": str(ACTIVE_OVERRIDES_PATH), "expired_count": len(expired)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Athanor active overrides.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Print current active override state.")
    list_parser.set_defaults(func=cmd_list)

    add_parser = subparsers.add_parser("add", help="Add a new active override.")
    add_parser.add_argument("--type", dest="override_type", required=True)
    add_parser.add_argument("--target", required=True)
    add_parser.add_argument("--reason", required=True)
    add_parser.add_argument("--ttl", default=None)
    add_parser.add_argument("--metadata-json", default=None)
    add_parser.add_argument("--actor", default="Shaun")
    add_parser.add_argument("--session-id", default="manual-cli")
    add_parser.add_argument("--correlation-id", default=None)
    add_parser.set_defaults(func=cmd_add)

    remove_parser = subparsers.add_parser("remove", help="Remove an active override by id.")
    remove_parser.add_argument("--id", dest="override_id", required=True)
    remove_parser.add_argument("--reason", required=True)
    remove_parser.add_argument("--actor", default="Shaun")
    remove_parser.add_argument("--session-id", default="manual-cli")
    remove_parser.add_argument("--correlation-id", default=None)
    remove_parser.set_defaults(func=cmd_remove)

    expire_parser = subparsers.add_parser("expire", help="Expire overrides whose TTL has elapsed.")
    expire_parser.add_argument("--reason", default="scheduled expiry sweep")
    expire_parser.add_argument("--actor", default="Shaun")
    expire_parser.add_argument("--session-id", default="manual-cli")
    expire_parser.add_argument("--correlation-id", default=None)
    expire_parser.set_defaults(func=cmd_expire)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
