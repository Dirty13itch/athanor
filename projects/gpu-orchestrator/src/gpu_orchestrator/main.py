"""Athanor GPU Orchestrator -- manages GPU state, vLLM sleep/wake, and local runtime sharing.

Phase 2 implementation per ADR-018: GPU monitoring, TTL auto-sleep, manual controls.
Updated 2026-04-11: tracked source re-aligned to the current six-zone runtime observed on
FOUNDRY, WORKSHOP, and DEV. The worker lane is now ComfyUI-only, coder points to the
llama.cpp Dolphin lane on Foundry:8100, and DEV embedding/reranker lanes are modeled
explicitly instead of being implicit sidecars.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field as PydanticField, model_validator
from fastapi.responses import JSONResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response

from .config import settings
from .gpu import (
    GpuMetrics,
    OllamaModelState,
    SleepState,
    VllmInstance,
    check_ollama_health,
    check_ollama_loaded,
    check_vllm_health,
    check_vllm_sleeping,
    fetch_all_gpu_metrics,
    sleep_vllm,
    unload_ollama_model,
    wake_vllm,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --- Zone Definitions ---


class ZoneState(str, Enum):
    ACTIVE = "active"       # GPU in use, workload running
    SLEEPING = "sleeping"   # Model unloaded / vLLM sleeping, VRAM freed
    AVAILABLE = "available" # GPU available for scheduling
    OFFLINE = "offline"     # Node or GPU unreachable


@dataclass
class Zone:
    """A logical GPU allocation zone."""

    name: str
    node: str
    gpus: list[int]
    vllm_url: str | None
    default_workload: str
    sleep_ttl: int  # seconds of idle before auto-sleep
    runtime: str = "vllm"  # "vllm" or "ollama"
    auto_sleep_enabled: bool = True
    ollama_url: str | None = None
    state: ZoneState = ZoneState.ACTIVE
    last_request_at: float = field(default_factory=time.time)
    vllm_instance: VllmInstance | None = None
    ollama_models: list[OllamaModelState] = field(default_factory=list)
    gpu_metrics: list[GpuMetrics] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "node": self.node,
            "gpus": self.gpus,
            "default_workload": self.default_workload,
            "state": self.state.value,
            "runtime": self.runtime,
            "sleep_ttl": self.sleep_ttl,
            "auto_sleep_enabled": self.auto_sleep_enabled,
            "idle_seconds": round(time.time() - self.last_request_at),
            "ttl_remaining": max(0, self.sleep_ttl - int(time.time() - self.last_request_at)),
            "vllm": self.vllm_instance.to_dict() if self.vllm_instance else None,
            "gpu_metrics": [g.to_dict() for g in self.gpu_metrics],
        }
        if self.runtime == "ollama":
            d["ollama_models"] = [m.to_dict() for m in self.ollama_models]
        return d


# Zone configuration -- re-aligned to the live runtime observed on 2026-04-11.
ZONES: dict[str, Zone] = {
    # --- FOUNDRY (node1) ---
    "coordinator": Zone(
        name="coordinator",
        node="node1",
        gpus=[0, 1, 3, 4],
        vllm_url=settings.vllm_node1_url,
        default_workload="vLLM Qwen3.5-27B-FP8 TP=4 (backbone)",
        sleep_ttl=1800,  # 30 min
        runtime="vllm",
    ),
    # F:2 4090 runs Dolphin 3.0 R1 24B via llama.cpp at :8100. We keep the
    # vLLM-oriented field and runtime names for compatibility with existing
    # orchestrator APIs, but the lane is no longer the older :8006 vLLM coder.
    "coder": Zone(
        name="coder",
        node="node1",
        gpus=[2],
        vllm_url=settings.vllm_coder_url,
        default_workload="llama.cpp Dolphin 3.0 R1 Mistral 24B abliterated (uncensored, F:2 4090)",
        sleep_ttl=86400,  # effectively never auto-sleep; llama.cpp has no sleep API
        runtime="vllm",
    ),
    # --- WORKSHOP (node2) ---
    "worker": Zone(
        name="worker",
        node="node2",
        gpus=[0],
        vllm_url=None,
        default_workload="ComfyUI (RTX 5090, creative workloads, :8188)",
        sleep_ttl=86400,
        runtime="ollama",  # kept as ollama so scheduler skips it; no ollama_url means no polling
        ollama_url=None,
    ),
    "vision": Zone(
        name="vision",
        node="node2",
        gpus=[1],
        vllm_url=settings.vllm_vision_url,
        default_workload="vLLM Qwen3-VL-8B-Instruct-FP8 (vision, sleep-enabled)",
        sleep_ttl=900,
        runtime="vllm",
    ),
    # --- DEV (node3) ---
    "embedding": Zone(
        name="embedding",
        node="node3",
        gpus=[0],
        vllm_url=settings.vllm_node1_embed_url,
        default_workload="vLLM Qwen3-Embedding-8B-FP8-DYNAMIC (4096-dim, always-on)",
        sleep_ttl=1800,
        runtime="vllm",
        auto_sleep_enabled=settings.embedding_auto_sleep_enabled,
    ),
    "reranker": Zone(
        name="reranker",
        node="node3",
        gpus=[0],
        vllm_url=settings.vllm_reranker_url,
        default_workload="vLLM Qwen3-Reranker-0.6B (NVIDIA 0.11.1, no sleep support)",
        sleep_ttl=86400,
        runtime="vllm",
    ),
}


SCHEDULER_ZONE_METADATA: dict[str, dict[str, Any]] = {
    "coordinator": {
        "gpu_id": "F:TP4",
        "owner": "vllm",
        "model": "qwen3.5-27b-tp4-bf16",
        "model_alias": "foundry-coordinator",
        "priority": 0,
    },
    "coder": {
        "gpu_id": "F:2",
        "owner": "llama.cpp",
        "model": "dolphin3-r1-24b",
        "model_alias": "foundry-coder",
        "priority": 2,
    },
    "worker": {
        "gpu_id": "W:0",
        "owner": "comfyui",
        "model": "comfyui-active-workflow",
        "model_alias": "workshop-worker",
        "priority": 1,
    },
    "vision": {
        "gpu_id": "W:1",
        "owner": "vllm",
        "model": "qwen3-vl-8b-instruct-fp8",
        "model_alias": "workshop-vision",
        "priority": 0,
    },
    "embedding": {
        "gpu_id": "D:0",
        "owner": "vllm",
        "model": "qwen3-embed-8b",
        "model_alias": "dev-embedding",
        "priority": 0,
    },
    "reranker": {
        "gpu_id": "D:0",
        "owner": "vllm",
        "model": "qwen3-reranker-0.6b",
        "model_alias": "dev-reranker",
        "priority": 0,
    },
}

SCHEDULER_WRITE_CAPABILITIES = ("request", "preload", "release")
SCHEDULER_ACTIVE_REQUEST_STATES = {"queued", "preloading", "active", "releasing"}


def _iso_from_epoch(timestamp: float | None) -> str | None:
    if not timestamp or timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _scheduler_state_name(zone: Zone) -> str:
    if zone.state == ZoneState.ACTIVE:
        return "ACTIVE"
    if zone.state == ZoneState.SLEEPING:
        return "SLEEPING_L1"
    if zone.state == ZoneState.AVAILABLE:
        return "IDLE"
    return "ERROR"


def _zone_vram_totals(zone: Zone) -> tuple[int, int]:
    used = round(sum(metric.vram_used_mb for metric in zone.gpu_metrics))
    total = round(sum(metric.vram_total_mb for metric in zone.gpu_metrics))
    return int(used), int(total)


def _scheduler_zone_projection(zone_name: str, zone: Zone) -> dict[str, Any]:
    metadata = SCHEDULER_ZONE_METADATA.get(zone_name, {})
    vram_used_mb, vram_total_mb = _zone_vram_totals(zone)
    idle_seconds = round(time.time() - zone.last_request_at)
    return {
        "observed_zone_state": zone.state.value,
        "scheduler_state": _scheduler_state_name(zone),
        "owner": metadata.get("owner", zone.runtime),
        "model": metadata.get("model", zone.default_workload),
        "model_alias": metadata.get("model_alias", zone_name),
        "priority": metadata.get("priority", 3),
        "vram_used_mb": vram_used_mb,
        "vram_total_mb": vram_total_mb,
        "last_transition": None,
        "last_request_at": zone.last_request_at,
        "last_request_at_iso": _iso_from_epoch(zone.last_request_at),
        "last_inference": _iso_from_epoch(zone.last_request_at),
        "node": zone.node,
        "device_indices": ",".join(str(index) for index in zone.gpus),
        "zone_name": zone_name,
        "projection_only": True,
        "runtime": zone.runtime,
        "workload": zone.default_workload,
        "idle_seconds": idle_seconds,
        "ttl_seconds": zone.sleep_ttl,
        "ttl_remaining": max(0, zone.sleep_ttl - int(idle_seconds)),
        "auto_sleep_enabled": zone.auto_sleep_enabled,
        "sleep_policy": "gpu_orchestrator_ttl" if zone.auto_sleep_enabled else "always_on",
    }


def _merge_scheduler_slot_state(existing: str | None, new_state: str) -> str:
    order = {"ERROR": 4, "ACTIVE": 3, "SLEEPING_L1": 2, "IDLE": 1}
    if existing is None:
        return new_state
    return existing if order.get(existing, 0) >= order.get(new_state, 0) else new_state


def build_scheduler_state_projection(
    active_requests: list[dict[str, Any]] | None = None,
    *,
    scheduler_enabled: bool | None = None,
) -> dict[str, Any]:
    enabled = settings.scheduler_mutation_enabled if scheduler_enabled is None else scheduler_enabled
    normalized_requests = sorted(
        [dict(item) for item in (active_requests or [])],
        key=lambda item: (
            str(item.get("updated_at") or ""),
            str(item.get("request_id") or ""),
        ),
    )
    zone_projections = {
        zone_name: _scheduler_zone_projection(zone_name, zone)
        for zone_name, zone in ZONES.items()
    }

    gpu_slots: dict[str, dict[str, Any]] = {}
    for zone_name, projection in zone_projections.items():
        slot_id = str(SCHEDULER_ZONE_METADATA.get(zone_name, {}).get("gpu_id") or zone_name)
        slot = gpu_slots.setdefault(
            slot_id,
            {
                "state": None,
                "owners": [],
                "models": [],
                "model_aliases": [],
                "zones": [],
                "node": projection["node"],
                "device_indices": projection["device_indices"],
                "priority_floor": projection["priority"],
                "vram_used_mb": 0,
                "vram_total_mb": 0,
                "projection_only": True,
            },
        )
        slot["state"] = _merge_scheduler_slot_state(slot["state"], projection["scheduler_state"])
        slot["owners"].append(projection["owner"])
        slot["models"].append(projection["model"])
        slot["model_aliases"].append(projection["model_alias"])
        slot["zones"].append(zone_name)
        slot["priority_floor"] = min(slot["priority_floor"], projection["priority"])
        slot["vram_used_mb"] += projection["vram_used_mb"]
        slot["vram_total_mb"] += projection["vram_total_mb"]

    for slot in gpu_slots.values():
        if len(slot["zones"]) > 1:
            slot["projection_conflict"] = "shared_gpu_multiple_zones"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "bounded_scheduler" if enabled else "observed_projection",
        "authority": "gpu-orchestrator",
        "surface_status": "mutation_enabled" if enabled else "baseline_projection",
        "scheduler_enabled": enabled,
        "queue_depth": sum(
            1
            for request in normalized_requests
            if str(request.get("scheduler_state") or "").strip().lower()
            in SCHEDULER_ACTIVE_REQUEST_STATES
        ),
        "active_transitions": sum(
            1
            for request in normalized_requests
            if str(request.get("scheduler_state") or "").strip().lower()
            in {"queued", "preloading", "releasing"}
        ),
        "write_capabilities": {
            capability: enabled for capability in SCHEDULER_WRITE_CAPABILITIES
        },
        "blockers": (
            []
            if enabled
            else [
                "scheduler mutation feature gate disabled",
                "bounded mutation routes require governed rollout before live use",
            ]
        ),
        "requests": normalized_requests,
        "gpus": gpu_slots,
        "zones": zone_projections,
    }


# --- Prometheus Metrics ---


gpu_utilization = Gauge(
    "athanor_gpu_utilization_percent",
    "GPU compute utilization percentage",
    ["node", "gpu_index", "gpu_name"],
)
gpu_vram_used = Gauge(
    "athanor_gpu_vram_used_mb",
    "GPU VRAM used in MB",
    ["node", "gpu_index", "gpu_name"],
)
gpu_vram_total = Gauge(
    "athanor_gpu_vram_total_mb",
    "GPU VRAM total in MB",
    ["node", "gpu_index", "gpu_name"],
)
gpu_temperature = Gauge(
    "athanor_gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["node", "gpu_index", "gpu_name"],
)
gpu_power = Gauge(
    "athanor_gpu_power_watts",
    "GPU power draw in watts",
    ["node", "gpu_index", "gpu_name"],
)
zone_state_gauge = Gauge(
    "athanor_zone_state",
    "Zone state (1=active, 2=sleeping, 3=available, 0=offline)",
    ["zone"],
)
zone_idle_seconds = Gauge(
    "athanor_zone_idle_seconds",
    "Seconds since last request to zone",
    ["zone"],
)
ollama_model_loaded = Gauge(
    "athanor_ollama_model_loaded",
    "Whether an Ollama model is loaded in VRAM (1=yes, 0=no)",
    ["zone", "model"],
)
ollama_model_vram_gb = Gauge(
    "athanor_ollama_model_vram_gb",
    "VRAM used by loaded Ollama model in GB",
    ["zone", "model"],
)
sleep_events = Counter(
    "athanor_gpu_sleep_events_total",
    "Total sleep events",
    ["zone", "trigger"],  # trigger: ttl, manual
)
wake_events = Counter(
    "athanor_gpu_wake_events_total",
    "Total wake events",
    ["zone", "trigger"],  # trigger: request, manual
)
sleep_wake_duration = Histogram(
    "athanor_gpu_sleep_wake_duration_seconds",
    "Duration of sleep/wake operations",
    ["zone", "operation"],
)

STATE_VALUES = {
    ZoneState.ACTIVE: 1,
    ZoneState.SLEEPING: 2,
    ZoneState.AVAILABLE: 3,
    ZoneState.OFFLINE: 0,
}


def update_prometheus_metrics():
    """Update Prometheus gauges from current zone state."""
    for zone in ZONES.values():
        zone_state_gauge.labels(zone=zone.name).set(STATE_VALUES.get(zone.state, 0))
        zone_idle_seconds.labels(zone=zone.name).set(time.time() - zone.last_request_at)

        for gm in zone.gpu_metrics:
            labels = {
                "node": gm.node,
                "gpu_index": str(gm.gpu_index),
                "gpu_name": gm.gpu_name,
            }
            gpu_utilization.labels(**labels).set(gm.utilization_pct)
            gpu_vram_used.labels(**labels).set(gm.vram_used_mb)
            gpu_vram_total.labels(**labels).set(gm.vram_total_mb)
            gpu_temperature.labels(**labels).set(gm.temperature_c)
            gpu_power.labels(**labels).set(gm.power_watts)

        # Ollama model metrics
        if zone.runtime == "ollama":
            for m in zone.ollama_models:
                ollama_model_loaded.labels(zone=zone.name, model=m.name).set(
                    1.0 if m.loaded else 0.0
                )
                ollama_model_vram_gb.labels(zone=zone.name, model=m.name).set(m.vram_gb)


# --- Redis State Persistence ---


REDIS_KEY_PREFIX = "athanor:gpu:"
SCHEDULER_REQUESTS_KEY = f"{REDIS_KEY_PREFIX}scheduler:requests"

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def save_zone_state(zone: Zone):
    """Persist zone state to Redis."""
    r = await get_redis()
    key = f"{REDIS_KEY_PREFIX}{zone.name}"
    data = {
        "state": zone.state.value,
        "last_request_at": str(zone.last_request_at),
    }
    await r.hset(key, mapping=data)


async def load_zone_state(zone: Zone):
    """Load zone state from Redis (if available)."""
    r = await get_redis()
    key = f"{REDIS_KEY_PREFIX}{zone.name}"
    data = await r.hgetall(key)
    if data:
        try:
            zone.state = ZoneState(data.get("state", "active"))
            zone.last_request_at = float(data.get("last_request_at", time.time()))
        except (ValueError, TypeError):
            pass


class SchedulerRequestPayload(BaseModel):
    model_config = {"extra": "forbid"}

    request_id: str = PydanticField(min_length=1)
    request_surface: str = PydanticField(min_length=1)
    zone: str | None = None
    model_alias: str | None = None
    priority: int
    request_kind: str = PydanticField(min_length=1)

    @model_validator(mode="after")
    def _validate_target(self) -> "SchedulerRequestPayload":
        self.request_id = self.request_id.strip()
        self.request_surface = self.request_surface.strip()
        self.request_kind = self.request_kind.strip()
        self.zone = self.zone.strip() if isinstance(self.zone, str) else None
        self.model_alias = self.model_alias.strip() if isinstance(self.model_alias, str) else None
        if not self.zone and not self.model_alias:
            raise ValueError("zone or model_alias is required")
        return self


class SchedulerPreloadPayload(BaseModel):
    model_config = {"extra": "forbid"}

    request_id: str = PydanticField(min_length=1)
    zone: str = PydanticField(min_length=1)
    model_alias: str = PydanticField(min_length=1)
    reason: str = PydanticField(min_length=1)

    @model_validator(mode="after")
    def _normalize(self) -> "SchedulerPreloadPayload":
        self.request_id = self.request_id.strip()
        self.zone = self.zone.strip()
        self.model_alias = self.model_alias.strip()
        self.reason = self.reason.strip()
        return self


class SchedulerReleasePayload(BaseModel):
    model_config = {"extra": "forbid"}

    request_id: str = PydanticField(min_length=1)
    zone: str = PydanticField(min_length=1)
    reason: str = PydanticField(min_length=1)

    @model_validator(mode="after")
    def _normalize(self) -> "SchedulerReleasePayload":
        self.request_id = self.request_id.strip()
        self.zone = self.zone.strip()
        self.reason = self.reason.strip()
        return self


def _scheduler_slot_id(zone_name: str) -> str:
    return str(SCHEDULER_ZONE_METADATA.get(zone_name, {}).get("gpu_id") or zone_name)


def _scheduler_zone_for_model_alias(model_alias: str | None) -> str | None:
    normalized_alias = str(model_alias or "").strip()
    if not normalized_alias:
        return None
    for zone_name, metadata in SCHEDULER_ZONE_METADATA.items():
        if str(metadata.get("model_alias") or "").strip() == normalized_alias:
            return zone_name
    return None


def _scheduler_conflict_for_zone(zone_name: str) -> str | None:
    slot_id = _scheduler_slot_id(zone_name)
    linked_zones = [
        candidate
        for candidate in ZONES
        if _scheduler_slot_id(candidate) == slot_id
    ]
    if len(linked_zones) > 1:
        return "shared_gpu_multiple_zones"
    return None


def _scheduler_zone_metadata(zone_name: str) -> dict[str, Any]:
    return dict(SCHEDULER_ZONE_METADATA.get(zone_name, {}))


def _resolve_scheduler_zone(zone_name: str | None, model_alias: str | None) -> tuple[str | None, str | None]:
    normalized_zone = str(zone_name or "").strip() or None
    resolved_from_alias = _scheduler_zone_for_model_alias(model_alias)
    normalized_alias = str(model_alias or "").strip() or None

    if normalized_zone and normalized_zone not in ZONES:
        return None, f"unknown_zone:{normalized_zone}"
    if normalized_alias and resolved_from_alias is None:
        return None, f"unknown_model_alias:{normalized_alias}"
    if normalized_zone and resolved_from_alias and normalized_zone != resolved_from_alias:
        return None, "zone_model_alias_mismatch"

    resolved_zone = normalized_zone or resolved_from_alias
    if resolved_zone is None:
        return None, "zone_or_model_alias_required"
    return resolved_zone, None


def _scheduler_active_request_records(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in records.values()
        if str(record.get("scheduler_state") or "").strip().lower()
        in SCHEDULER_ACTIVE_REQUEST_STATES
    ]


def _scheduler_queue_depth_for_zone(records: dict[str, dict[str, Any]], zone_name: str) -> int:
    return sum(
        1
        for record in records.values()
        if str(record.get("zone") or "").strip() == zone_name
        and str(record.get("scheduler_state") or "").strip().lower() in SCHEDULER_ACTIVE_REQUEST_STATES
    )


def _scheduler_record_matches(
    record: dict[str, Any],
    *,
    action: str,
    zone_name: str,
    model_alias: str | None = None,
    request_surface: str | None = None,
    request_kind: str | None = None,
) -> bool:
    if str(record.get("action") or "").strip() != action:
        return False
    if str(record.get("zone") or "").strip() != zone_name:
        return False
    if model_alias is not None and str(record.get("model_alias") or "").strip() != str(model_alias or "").strip():
        return False
    if request_surface is not None and str(record.get("request_surface") or "").strip() != str(request_surface or "").strip():
        return False
    if request_kind is not None and str(record.get("request_kind") or "").strip() != str(request_kind or "").strip():
        return False
    return True


def _scheduler_response_payload(
    *,
    request_id: str,
    zone_name: str,
    decision_reason: str,
    queue_depth: int,
    slot_id: str,
    accepted: bool | None = None,
    released: bool | None = None,
    scheduler_state: str,
    preload_state: str | None = None,
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "zone": zone_name,
        "slot_id": slot_id,
        "decision_reason": decision_reason,
        "queue_depth": queue_depth,
        "scheduler_state": scheduler_state,
    }
    if accepted is not None:
        payload["accepted"] = accepted
    if released is not None:
        payload["released"] = released
    if preload_state is not None:
        payload["preload_state"] = preload_state
    return payload


async def _load_scheduler_records() -> dict[str, dict[str, Any]]:
    redis = await get_redis()
    raw_records = await redis.hgetall(SCHEDULER_REQUESTS_KEY)
    records: dict[str, dict[str, Any]] = {}
    for request_id, value in raw_records.items():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records[str(request_id)] = parsed
    return records


async def _save_scheduler_record(record: dict[str, Any]) -> None:
    redis = await get_redis()
    await redis.hset(
        SCHEDULER_REQUESTS_KEY,
        mapping={str(record["request_id"]): json.dumps(record, sort_keys=True)},
    )


# --- Background Tasks ---


_monitor_task: asyncio.Task | None = None
_scheduler_task: asyncio.Task | None = None
_running = False


async def monitor_loop():
    """Poll GPU metrics from DCGM-exporter every 10 seconds."""
    while _running:
        try:
            all_metrics = await fetch_all_gpu_metrics()

            for zone in ZONES.values():
                node_metrics = all_metrics.get(zone.node, [])
                zone.gpu_metrics = [
                    m for m in node_metrics if m.gpu_index in zone.gpus
                ]

                if zone.runtime == "ollama" and zone.ollama_url:
                    # Ollama-managed zone: check model load state via /api/ps
                    models = await check_ollama_loaded(zone.ollama_url)
                    zone.ollama_models = models

                    if models:
                        # At least one model loaded -- zone is active
                        zone.state = ZoneState.ACTIVE
                    else:
                        # No models loaded -- VRAM is free (available for ComfyUI)
                        healthy = await check_ollama_health(zone.ollama_url)
                        if healthy:
                            zone.state = ZoneState.AVAILABLE
                        else:
                            zone.state = ZoneState.OFFLINE

                elif zone.vllm_url:
                    # vLLM-managed zone: check sleep state
                    if zone.vllm_instance is None:
                        zone.vllm_instance = VllmInstance(
                            name=zone.default_workload,
                            url=zone.vllm_url,
                            node=zone.node,
                            gpus=zone.gpus,
                        )
                    sleep_state = await check_vllm_sleeping(zone.vllm_url)
                    zone.vllm_instance.sleep_state = sleep_state
                    zone.vllm_instance.last_checked_at = time.time()

                    # Sync zone state from vLLM
                    if sleep_state == SleepState.SLEEPING:
                        zone.state = ZoneState.SLEEPING
                    elif sleep_state == SleepState.AWAKE:
                        zone.state = ZoneState.ACTIVE
                    elif sleep_state == SleepState.UNAVAILABLE:
                        healthy = await check_vllm_health(zone.vllm_url)
                        if healthy:
                            zone.state = ZoneState.ACTIVE
                        else:
                            zone.state = ZoneState.OFFLINE
                else:
                    # No runtime configured -- check if node is reachable via metrics
                    if zone.gpu_metrics:
                        zone.state = ZoneState.ACTIVE
                    else:
                        zone.state = ZoneState.OFFLINE

                await save_zone_state(zone)

            update_prometheus_metrics()

        except Exception as e:
            logger.error("Monitor loop error: %s", e)

        await asyncio.sleep(10)


async def scheduler_loop():
    """TTL-based auto-sleep: check idle zones every 30 seconds.

    For vLLM zones: sends /sleep API call.
    For Ollama zones: no action needed -- Ollama's native KEEP_ALIVE handles unloading.
    """
    while _running:
        try:
            now = time.time()

            for zone in ZONES.values():
                await apply_zone_sleep_policy(zone, now=now)

        except Exception as e:
            logger.error("Scheduler loop error: %s", e)

        await asyncio.sleep(30)


async def apply_zone_sleep_policy(zone: Zone, *, now: float | None = None) -> bool:
    """Apply the zone's sleep policy for the current scheduler tick.

    Returns True when the function changed live runtime state or persisted zone state.
    """
    current_time = time.time() if now is None else now

    # Ollama lanes own their unload policy; zones without a runtime URL are observation-only.
    if zone.runtime == "ollama" or zone.vllm_url is None:
        return False

    if not zone.auto_sleep_enabled:
        sleep_state = await check_vllm_sleeping(zone.vllm_url)
        if sleep_state == SleepState.SLEEPING or zone.state == ZoneState.SLEEPING:
            logger.info(
                "Zone %s is configured always-on but is sleeping -- waking runtime",
                zone.name,
            )
            start = time.time()
            success = await wake_vllm(zone.vllm_url)
            duration = time.time() - start
            if not success:
                return False
            zone.state = ZoneState.ACTIVE
            zone.last_request_at = current_time
            wake_events.labels(zone=zone.name, trigger="policy").inc()
            sleep_wake_duration.labels(zone=zone.name, operation="wake").observe(duration)
            await save_zone_state(zone)
            return True

        if zone.state != ZoneState.ACTIVE:
            zone.state = ZoneState.ACTIVE
            await save_zone_state(zone)
            return True
        return False

    # Only auto-sleep active vLLM zones.
    if zone.state != ZoneState.ACTIVE:
        return False

    idle_seconds = current_time - zone.last_request_at
    if idle_seconds < zone.sleep_ttl:
        return False

    logger.info(
        "Zone %s idle for %ds (TTL: %ds) -- triggering sleep",
        zone.name, int(idle_seconds), zone.sleep_ttl,
    )
    start = time.time()
    success = await sleep_vllm(zone.vllm_url, level=1)
    duration = time.time() - start

    if not success:
        return False

    zone.state = ZoneState.SLEEPING
    sleep_events.labels(zone=zone.name, trigger="ttl").inc()
    sleep_wake_duration.labels(zone=zone.name, operation="sleep").observe(duration)
    await save_zone_state(zone)
    return True


async def start_background_tasks():
    """Start monitoring and scheduling loops."""
    global _monitor_task, _scheduler_task, _running
    _running = True

    # Load persisted state
    for zone in ZONES.values():
        await load_zone_state(zone)
        await apply_zone_sleep_policy(zone)

    _monitor_task = asyncio.create_task(monitor_loop())
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info("Background tasks started (monitor=10s, scheduler=30s)")


async def stop_background_tasks():
    """Stop background loops."""
    global _running
    _running = False
    if _monitor_task:
        _monitor_task.cancel()
    if _scheduler_task:
        _scheduler_task.cancel()
    if _redis:
        await _redis.aclose()
    logger.info("Background tasks stopped")


# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_background_tasks()
    yield
    await stop_background_tasks()


app = FastAPI(
    title="Athanor GPU Orchestrator",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check."""
    zones_up = sum(1 for z in ZONES.values() if z.state != ZoneState.OFFLINE)
    return {
        "status": "ok",
        "zones_total": len(ZONES),
        "zones_up": zones_up,
    }


@app.get("/status")
async def full_status():
    """Full GPU status across both nodes -- the primary debugging endpoint."""
    total_vram_used = 0.0
    total_vram_total = 0.0

    zones_data = {}
    for name, zone in ZONES.items():
        zones_data[name] = zone.to_dict()
        for gm in zone.gpu_metrics:
            total_vram_used += gm.vram_used_mb
            total_vram_total += gm.vram_total_mb

    return {
        "timestamp": time.time(),
        "summary": {
            "total_gpus": sum(len(z.gpus) for z in ZONES.values()),
            "zones_active": sum(1 for z in ZONES.values() if z.state == ZoneState.ACTIVE),
            "zones_sleeping": sum(1 for z in ZONES.values() if z.state == ZoneState.SLEEPING),
            "zones_available": sum(1 for z in ZONES.values() if z.state == ZoneState.AVAILABLE),
            "zones_offline": sum(1 for z in ZONES.values() if z.state == ZoneState.OFFLINE),
            "total_vram_used_mb": round(total_vram_used, 1),
            "total_vram_total_mb": round(total_vram_total, 1),
            "total_vram_utilization_pct": round(
                (total_vram_used / total_vram_total * 100) if total_vram_total > 0 else 0, 1
            ),
        },
        "zones": zones_data,
    }


@app.get("/scheduler/state")
async def scheduler_state():
    """Scheduler state projection with bounded queued intent when enabled."""
    if not settings.scheduler_mutation_enabled:
        return build_scheduler_state_projection(
            scheduler_enabled=False,
        )
    try:
        records = await _load_scheduler_records()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load scheduler records: %s", exc)
        records = {}
    return build_scheduler_state_projection(
        _scheduler_active_request_records(records),
        scheduler_enabled=settings.scheduler_mutation_enabled,
    )


@app.post("/scheduler/request")
async def scheduler_request(payload: SchedulerRequestPayload):
    """Queue a bounded scheduler intent for one zone or model alias."""
    zone_name, resolution_error = _resolve_scheduler_zone(payload.zone, payload.model_alias)
    if resolution_error == "zone_model_alias_mismatch":
        return JSONResponse(
            status_code=409,
            content={"error": resolution_error},
        )
    if resolution_error and resolution_error.startswith("unknown_"):
        return JSONResponse(
            status_code=404,
            content={"error": resolution_error},
        )
    if resolution_error:
        return JSONResponse(
            status_code=400,
            content={"error": resolution_error},
        )
    assert zone_name is not None

    slot_id = _scheduler_slot_id(zone_name)
    if not settings.scheduler_mutation_enabled:
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=zone_name,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                decision_reason="scheduler_mutation_disabled",
                queue_depth=0,
            ),
        )

    conflict = _scheduler_conflict_for_zone(zone_name)
    if conflict:
        records = await _load_scheduler_records()
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=zone_name,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                decision_reason=conflict,
                queue_depth=_scheduler_queue_depth_for_zone(records, zone_name),
            ),
        )

    records = await _load_scheduler_records()
    existing = records.get(payload.request_id)
    resolved_alias = str(payload.model_alias or _scheduler_zone_metadata(zone_name).get("model_alias") or "")
    if existing:
        if _scheduler_record_matches(
            existing,
            action="request",
            zone_name=zone_name,
            model_alias=resolved_alias,
            request_surface=payload.request_surface,
            request_kind=payload.request_kind,
        ):
            return _scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=zone_name,
                slot_id=slot_id,
                accepted=bool(existing.get("accepted", True)),
                scheduler_state=str(existing.get("scheduler_state") or "queued"),
                decision_reason="request_idempotent_replay",
                queue_depth=_scheduler_queue_depth_for_zone(records, zone_name),
            )
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=zone_name,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                decision_reason="request_id_payload_mismatch",
                queue_depth=_scheduler_queue_depth_for_zone(records, zone_name),
            ),
        )

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "request_id": payload.request_id,
        "action": "request",
        "zone": zone_name,
        "slot_id": slot_id,
        "model_alias": resolved_alias,
        "request_surface": payload.request_surface,
        "request_kind": payload.request_kind,
        "priority": payload.priority,
        "scheduler_state": "queued",
        "decision_reason": "queued_transition_intent_recorded",
        "accepted": True,
        "requested_at": now,
        "updated_at": now,
    }
    await _save_scheduler_record(record)
    records[payload.request_id] = record
    return _scheduler_response_payload(
        request_id=payload.request_id,
        zone_name=zone_name,
        slot_id=slot_id,
        accepted=True,
        scheduler_state="queued",
        decision_reason="queued_transition_intent_recorded",
        queue_depth=_scheduler_queue_depth_for_zone(records, zone_name),
    )


@app.post("/scheduler/preload")
async def scheduler_preload(payload: SchedulerPreloadPayload):
    """Record bounded preload intent for a specific zone."""
    if payload.zone not in ZONES:
        return JSONResponse(
            status_code=404,
            content={"error": f"unknown_zone:{payload.zone}"},
        )

    slot_id = _scheduler_slot_id(payload.zone)
    expected_alias = str(_scheduler_zone_metadata(payload.zone).get("model_alias") or "")
    if payload.model_alias != expected_alias:
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                preload_state="rejected",
                decision_reason="model_alias_zone_mismatch",
                queue_depth=0,
            ),
        )

    if not settings.scheduler_mutation_enabled:
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                preload_state="rejected",
                decision_reason="scheduler_mutation_disabled",
                queue_depth=0,
            ),
        )

    conflict = _scheduler_conflict_for_zone(payload.zone)
    records = await _load_scheduler_records()
    if conflict:
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                preload_state="rejected",
                decision_reason=conflict,
                queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
            ),
        )

    existing = records.get(payload.request_id)
    if existing:
        if _scheduler_record_matches(
            existing,
            action="preload",
            zone_name=payload.zone,
            model_alias=payload.model_alias,
        ):
            return _scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                accepted=bool(existing.get("accepted", True)),
                scheduler_state=str(existing.get("scheduler_state") or "preloading"),
                preload_state=str(existing.get("preload_state") or "queued"),
                decision_reason="request_idempotent_replay",
                queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
            )
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                accepted=False,
                scheduler_state="rejected",
                preload_state="rejected",
                decision_reason="request_id_payload_mismatch",
                queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
            ),
        )

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "request_id": payload.request_id,
        "action": "preload",
        "zone": payload.zone,
        "slot_id": slot_id,
        "model_alias": payload.model_alias,
        "reason": payload.reason,
        "scheduler_state": "preloading",
        "preload_state": "queued",
        "decision_reason": "preload_intent_recorded",
        "accepted": True,
        "requested_at": now,
        "updated_at": now,
    }
    await _save_scheduler_record(record)
    records[payload.request_id] = record
    return _scheduler_response_payload(
        request_id=payload.request_id,
        zone_name=payload.zone,
        slot_id=slot_id,
        accepted=True,
        scheduler_state="preloading",
        preload_state="queued",
        decision_reason="preload_intent_recorded",
        queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
    )


@app.post("/scheduler/release")
async def scheduler_release(payload: SchedulerReleasePayload):
    """Release a bounded request or preload reservation back to observed projection."""
    if payload.zone not in ZONES:
        return JSONResponse(
            status_code=404,
            content={"error": f"unknown_zone:{payload.zone}"},
        )

    records = await _load_scheduler_records()
    existing = records.get(payload.request_id)
    slot_id = _scheduler_slot_id(payload.zone)
    if existing is None:
        return JSONResponse(
            status_code=404,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                released=False,
                scheduler_state="rejected",
                decision_reason="request_not_found",
                queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
            ),
        )
    if str(existing.get("zone") or "").strip() != payload.zone:
        return JSONResponse(
            status_code=409,
            content=_scheduler_response_payload(
                request_id=payload.request_id,
                zone_name=payload.zone,
                slot_id=slot_id,
                released=False,
                scheduler_state="rejected",
                decision_reason="release_zone_mismatch",
                queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
            ),
        )
    if str(existing.get("scheduler_state") or "").strip() == "released":
        return _scheduler_response_payload(
            request_id=payload.request_id,
            zone_name=payload.zone,
            slot_id=slot_id,
            released=True,
            scheduler_state="released",
            decision_reason="already_released",
            queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
        )

    updated_record = dict(existing)
    updated_record["scheduler_state"] = "released"
    updated_record["decision_reason"] = "release_recorded"
    updated_record["released"] = True
    updated_record["release_reason"] = payload.reason
    updated_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_scheduler_record(updated_record)
    records[payload.request_id] = updated_record
    return _scheduler_response_payload(
        request_id=payload.request_id,
        zone_name=payload.zone,
        slot_id=slot_id,
        released=True,
        scheduler_state="released",
        decision_reason="release_recorded",
        queue_depth=_scheduler_queue_depth_for_zone(records, payload.zone),
    )


@app.get("/gpu/{zone_name}")
async def zone_status(zone_name: str):
    """Get status for a specific GPU zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found. Available: {list(ZONES.keys())}"},
        )
    return zone.to_dict()


@app.post("/gpu/{zone_name}/sleep")
async def zone_sleep(zone_name: str, level: int = 1):
    """Manually put a zone to sleep (unload models)."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )

    if zone.runtime == "ollama" and zone.ollama_url:
        # Ollama zone: unload all loaded models
        if not zone.ollama_models:
            return {"status": "already_sleeping", "zone": zone_name, "runtime": "ollama"}

        unloaded = []
        for m in zone.ollama_models:
            if m.loaded:
                success = await unload_ollama_model(zone.ollama_url, m.name)
                if success:
                    unloaded.append(m.name)

        if unloaded:
            zone.state = ZoneState.AVAILABLE
            zone.ollama_models = []
            sleep_events.labels(zone=zone_name, trigger="manual").inc()
            await save_zone_state(zone)
            return {
                "status": "sleeping",
                "zone": zone_name,
                "runtime": "ollama",
                "unloaded": unloaded,
            }
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to unload Ollama models in zone '{zone_name}'"},
        )

    # vLLM zone
    if not zone.vllm_url:
        return JSONResponse(
            status_code=400,
            content={"error": f"Zone '{zone_name}' has no vLLM instance"},
        )
    if zone.state == ZoneState.SLEEPING:
        return {"status": "already_sleeping", "zone": zone_name}

    start = time.time()
    success = await sleep_vllm(zone.vllm_url, level=level)
    duration = time.time() - start

    if success:
        zone.state = ZoneState.SLEEPING
        sleep_events.labels(zone=zone_name, trigger="manual").inc()
        sleep_wake_duration.labels(zone=zone_name, operation="sleep").observe(duration)
        await save_zone_state(zone)
        return {
            "status": "sleeping",
            "zone": zone_name,
            "level": level,
            "duration_seconds": round(duration, 3),
        }
    return JSONResponse(
        status_code=500,
        content={"error": f"Failed to sleep zone '{zone_name}'. Check vLLM logs."},
    )


@app.post("/gpu/{zone_name}/wake")
async def zone_wake(zone_name: str):
    """Manually wake a sleeping zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )

    if zone.runtime == "ollama":
        # Ollama zones wake on-demand when a request comes in.
        # Nothing to do here -- the next inference request will load the model.
        return {
            "status": "ok",
            "zone": zone_name,
            "runtime": "ollama",
            "message": "Ollama models load on-demand. Next inference request will load the model.",
        }

    if not zone.vllm_url:
        return JSONResponse(
            status_code=400,
            content={"error": f"Zone '{zone_name}' has no vLLM instance"},
        )
    if zone.state == ZoneState.ACTIVE:
        return {"status": "already_awake", "zone": zone_name}

    start = time.time()
    success = await wake_vllm(zone.vllm_url)
    duration = time.time() - start

    if success:
        zone.state = ZoneState.ACTIVE
        zone.last_request_at = time.time()
        wake_events.labels(zone=zone_name, trigger="manual").inc()
        sleep_wake_duration.labels(zone=zone_name, operation="wake").observe(duration)
        await save_zone_state(zone)
        return {
            "status": "awake",
            "zone": zone_name,
            "duration_seconds": round(duration, 3),
        }
    return JSONResponse(
        status_code=500,
        content={"error": f"Failed to wake zone '{zone_name}'. Check vLLM logs."},
    )


@app.post("/gpu/{zone_name}/touch")
async def zone_touch(zone_name: str):
    """Reset the idle timer for a zone (mark it as recently used).

    Call this when routing a request through a zone to prevent auto-sleep.
    """
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    zone.last_request_at = time.time()
    await save_zone_state(zone)
    return {"status": "touched", "zone": zone_name, "last_request_at": zone.last_request_at}


@app.get("/gpu/{zone_name}/ttl")
async def zone_ttl(zone_name: str):
    """Get TTL configuration and remaining time for a zone."""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    idle = time.time() - zone.last_request_at
    return {
        "zone": zone_name,
        "runtime": zone.runtime,
        "sleep_ttl": zone.sleep_ttl,
        "idle_seconds": round(idle),
        "ttl_remaining": max(0, zone.sleep_ttl - int(idle)),
        "auto_sleep_mechanism": (
            "Ollama native KEEP_ALIVE=10m" if zone.runtime == "ollama"
            else "GPU orchestrator TTL polling"
        ),
    }


@app.put("/gpu/{zone_name}/ttl")
async def set_zone_ttl(zone_name: str, request: Request):
    """Update TTL for a zone. Body: {"sleep_ttl": 1800}"""
    zone = ZONES.get(zone_name)
    if not zone:
        return JSONResponse(
            status_code=404,
            content={"error": f"Zone '{zone_name}' not found"},
        )
    body = await request.json()
    new_ttl = body.get("sleep_ttl")
    if new_ttl is None or not isinstance(new_ttl, (int, float)) or new_ttl < 60:
        return JSONResponse(
            status_code=400,
            content={"error": "sleep_ttl must be a number >= 60 seconds"},
        )
    zone.sleep_ttl = int(new_ttl)
    return {"zone": zone_name, "sleep_ttl": zone.sleep_ttl}


@app.get("/zones")
async def list_zones():
    """List all GPU zones with summary info."""
    return {
        "zones": [
            {
                "name": z.name,
                "node": z.node,
                "gpus": z.gpus,
                "state": z.state.value,
                "runtime": z.runtime,
                "workload": z.default_workload,
                "idle_seconds": round(time.time() - z.last_request_at),
            }
            for z in ZONES.values()
        ]
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    update_prometheus_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


def main():
    import uvicorn

    logger.info("Starting GPU Orchestrator on %s:%d", settings.host, settings.port)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
