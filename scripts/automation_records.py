from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

import redis.asyncio as aioredis

from runtime_env import load_optional_runtime_env


AUTOMATION_RUN_STREAM = "athanor:automation:runs"
DEFAULT_REDIS_URL = "redis://192.168.1.203:6379/0"

_redis: aioredis.Redis | None = None

load_optional_runtime_env(env_names=["ATHANOR_REDIS_URL", "ATHANOR_REDIS_PASSWORD"])


@dataclass(frozen=True, slots=True)
class AutomationRunRecord:
    automation_id: str
    lane: str
    action_class: str
    inputs: dict[str, Any]
    result: dict[str, Any]
    rollback: dict[str, Any]
    duration: float
    operator_visible_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_stream_mapping(self) -> dict[str, str]:
        return {
            "timestamp": f"{time.time():.6f}",
            "automation_id": self.automation_id,
            "lane": self.lane,
            "action_class": self.action_class,
            "inputs": json.dumps(self.inputs, sort_keys=True),
            "result": json.dumps(self.result, sort_keys=True),
            "rollback": json.dumps(self.rollback, sort_keys=True),
            "duration": f"{self.duration:.6f}",
            "operator_visible_summary": self.operator_visible_summary,
        }


@dataclass(frozen=True, slots=True)
class AutomationRunEmitResult:
    persisted: bool
    error: str | None = None


def _parse_json_mapping(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        redis_url = os.getenv("ATHANOR_REDIS_URL", "").strip() or DEFAULT_REDIS_URL
        redis_password = os.getenv("ATHANOR_REDIS_PASSWORD", "").strip() or None
        _redis = aioredis.from_url(redis_url, password=redis_password, decode_responses=True)
    return _redis


async def emit_automation_run_record(record: AutomationRunRecord) -> AutomationRunEmitResult:
    try:
        redis_client = await _get_redis()
        await redis_client.xadd(
            AUTOMATION_RUN_STREAM,
            record.to_stream_mapping(),
            maxlen=5000,
            approximate=True,
        )
        return AutomationRunEmitResult(persisted=True)
    except Exception as exc:
        return AutomationRunEmitResult(persisted=False, error=str(exc))


def _coerce_json_mapping(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str):
        return {}
    text = raw.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _coerce_float(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


async def read_recent_automation_run_records(*, limit: int = 8) -> list[dict[str, Any]]:
    redis_url = os.getenv("ATHANOR_REDIS_URL", "").strip() or DEFAULT_REDIS_URL
    redis_password = os.getenv("ATHANOR_REDIS_PASSWORD", "").strip() or None
    redis_client = aioredis.from_url(redis_url, password=redis_password, decode_responses=True)
    try:
        entries = await redis_client.xrevrange(
            AUTOMATION_RUN_STREAM,
            max="+",
            min="-",
            count=max(1, int(limit)),
        )
    except Exception:
        return []
    finally:
        try:
            await redis_client.aclose()
        except Exception:
            pass

    records: list[dict[str, Any]] = []
    for stream_id, mapping in entries:
        payload = dict(mapping or {})
        records.append(
            {
                "stream_id": str(stream_id),
                "timestamp": str(payload.get("timestamp") or "").strip() or None,
                "automation_id": str(payload.get("automation_id") or "").strip() or None,
                "lane": str(payload.get("lane") or "").strip() or None,
                "action_class": str(payload.get("action_class") or "").strip() or None,
                "inputs": _coerce_json_mapping(payload.get("inputs")),
                "result": _coerce_json_mapping(payload.get("result")),
                "rollback": _coerce_json_mapping(payload.get("rollback")),
                "duration": _coerce_float(payload.get("duration")),
                "operator_visible_summary": str(payload.get("operator_visible_summary") or "").strip() or None,
            }
        )
    return records


async def read_recent_automation_run_records(
    *,
    limit: int = 10,
    lanes: list[str] | None = None,
    automation_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    try:
        redis_client = await _get_redis()
        raw_entries = await redis_client.xrevrange(
            AUTOMATION_RUN_STREAM,
            count=max(1, min(limit * 5, 250)),
        )
    except Exception:
        return []

    lane_filter = {str(item).strip() for item in (lanes or []) if str(item).strip()}
    automation_filter = {str(item).strip() for item in (automation_ids or []) if str(item).strip()}
    records: list[dict[str, Any]] = []

    for stream_id, mapping in raw_entries:
        record = {
            "stream_id": stream_id,
            "timestamp": str(mapping.get("timestamp") or "").strip() or None,
            "automation_id": str(mapping.get("automation_id") or "").strip() or None,
            "lane": str(mapping.get("lane") or "").strip() or None,
            "action_class": str(mapping.get("action_class") or "").strip() or None,
            "inputs": _parse_json_mapping(str(mapping.get("inputs") or "{}")),
            "result": _parse_json_mapping(str(mapping.get("result") or "{}")),
            "rollback": _parse_json_mapping(str(mapping.get("rollback") or "{}")),
            "duration": float(mapping.get("duration") or 0.0),
            "operator_visible_summary": str(mapping.get("operator_visible_summary") or "").strip() or None,
        }
        lane = str(record.get("lane") or "").strip()
        automation_id = str(record.get("automation_id") or "").strip()
        if lane_filter and lane not in lane_filter:
            continue
        if automation_filter and automation_id not in automation_filter:
            continue
        records.append(record)
        if len(records) >= limit:
            break

    return records
