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
