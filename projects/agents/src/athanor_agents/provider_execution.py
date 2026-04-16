from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .command_hierarchy import build_command_decision_record, build_plan_packet
from .config import settings
from .subscriptions import (
    LeaseRequest,
    get_quota_summary,
    get_policy_snapshot,
    get_provider_catalog_snapshot,
    issue_execution_lease,
    list_execution_leases,
    preview_execution_lease,
    record_execution_outcome,
)
from .tool_permissions import evaluate_tool_permission

HANDOFFS_KEY = "athanor:provider-execution:handoffs"
HANDOFF_EVENTS_KEY = "athanor:provider-execution:events"
HANDOFF_EVENT_LIMIT = 100
COMMAND_PROBE_TTL_SECONDS = 300
BRIDGE_PROVIDER_TTL_SECONDS = 60
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 90
MAX_DIRECT_OUTPUT_CHARS = 6000
MAX_EXECUTION_ATTEMPTS = 6

_COMMAND_PROBE_CACHE: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
_BRIDGE_PROVIDER_CACHE: dict[str, Any] = {
    "checked_at": 0.0,
    "providers": {},
    "bridge_status": "disabled",
    "detail": "Provider bridge is not configured.",
    "bridge_url": "",
}

_PROVIDER_ADAPTER_HINTS: dict[str, dict[str, Any]] = {
    "athanor_local": {
        "meta_lane": "sovereign_local",
        "probe_args": [],
        "notes": [
            "Bulk private work should stay here unless policy escalates outward.",
        ],
    },
    "anthropic_claude_code": {
        "probe_args": ["--help"],
        "notes": [
            "Use direct CLI when installed locally or through the DESK bridge; otherwise generate a structured bundle.",
        ],
    },
    "openai_codex": {
        "probe_args": ["--help"],
        "notes": [
            "Falls back to operator handoff when direct execution is unavailable.",
        ],
    },
    "google_gemini": {
        "probe_args": ["--help"],
        "notes": [
            "Use abstracted context for hybrid-abstractable work.",
        ],
    },
    "moonshot_kimi": {
        "probe_args": ["--help"],
        "notes": [
            "Can execute directly where the Kimi CLI exists; otherwise stays handoff-first.",
        ],
    },
    "zai_glm_coding": {
        "probe_args": ["--help"],
        "notes": [
            "Defaults to structured handoff unless a CLI or bridge adapter is available.",
        ],
    },
}

LOCAL_ONLY_POLICY_CLASSES = {"sovereign_only", "refusal_sensitive"}


@dataclass
class HandoffBundle:
    id: str
    requester: str
    provider: str
    lease_id: str | None
    task_class: str
    policy_class: str
    meta_lane: str
    execution_mode: str
    created_at: float
    updated_at: float
    completed_at: float | None
    status: str
    outcome: str | None
    summary: str
    prompt: str
    prompt_mode: str
    abstract_prompt: str | None
    fallback: list[str] = field(default_factory=list)
    command_decision: dict[str, Any] = field(default_factory=dict)
    plan_packet: dict[str, Any] = field(default_factory=dict)
    instructions: list[str] = field(default_factory=list)
    result_summary: str = ""
    failure_reason: str = ""
    artifact_refs: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    last_execution: dict[str, Any] = field(default_factory=dict)
    execution_attempts: list[dict[str, Any]] = field(default_factory=list)
    fallback_from_execution_mode: str | None = None
    fallback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _iso_from_unix(value: Any) -> str | None:
    if value in (None, "", 0, 0.0):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def serialize_handoff_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(bundle)
    for field in ("created_at", "updated_at", "completed_at"):
        serialized[field] = _iso_from_unix(serialized.get(field))
    return serialized


async def _get_redis():
    from .workspace import get_redis

    return await get_redis()


def _provider_env_key(provider_id: str) -> str:
    return f"ATHANOR_{provider_id.upper()}_COMMAND".replace("-", "_")


def _provider_catalog_entry(provider_id: str) -> dict[str, Any]:
    for entry in get_provider_catalog_snapshot(policy_only=False).get("providers", []):
        if str(entry.get("id") or "").strip() == provider_id:
            return dict(entry)
    return {}


def _provider_adapter_metadata(
    provider_id: str,
    provider_meta: dict[str, Any],
    *,
    catalog_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = dict(catalog_meta or _provider_catalog_entry(provider_id))
    hints = dict(_PROVIDER_ADAPTER_HINTS.get(provider_id) or {})
    access_mode = str(catalog.get("access_mode") or "").strip()
    privacy = str(provider_meta.get("privacy") or catalog.get("privacy_posture") or "cloud").strip()
    routing_posture = str(provider_meta.get("routing_posture") or "ordinary_auto").strip()
    routing_reason = str(provider_meta.get("routing_reason") or "").strip()
    execution_modes = [
        str(item).strip()
        for item in list(catalog.get("execution_modes") or [])
        if str(item).strip()
    ]
    if not execution_modes:
        if access_mode == "local" or privacy in {"lan_only", "sovereign_only"}:
            execution_modes = ["local_runtime"]
        else:
            execution_modes = ["handoff_bundle"]
    command_names = [
        str(item).strip()
        for item in list(catalog.get("cli_commands") or [])
        if str(item).strip()
    ]
    if "local_runtime" in execution_modes:
        default_mode = "local_runtime"
    elif "handoff_bundle" in execution_modes:
        default_mode = "handoff_bundle"
    elif "bridge_cli" in execution_modes:
        default_mode = "bridge_cli"
    elif "direct_cli" in execution_modes:
        default_mode = "direct_cli"
    else:
        default_mode = execution_modes[0]
    notes = list(
        dict.fromkeys(
            [
                *[str(item) for item in list(catalog.get("notes") or []) if str(item).strip()],
                *[str(item) for item in list(hints.get("notes") or []) if str(item).strip()],
            ]
        )
    )
    return {
        "catalog_access_mode": access_mode,
        "catalog_execution_modes": execution_modes,
        "catalog_state_classes": [
            str(item).strip()
            for item in list(catalog.get("state_classes") or [])
            if str(item).strip()
        ],
        "routing_posture": routing_posture,
        "routing_reason": routing_reason,
        "command_names": command_names,
        "probe_args": list(hints.get("probe_args", ["--help"])) if command_names else [],
        "supports_handoff": "handoff_bundle" in execution_modes,
        "allow_direct_cli": "direct_cli" in execution_modes,
        "allow_bridge_cli": "bridge_cli" in execution_modes,
        "default_mode": default_mode,
        "meta_lane": str(
            hints.get("meta_lane")
            or (
                "sovereign_local"
                if default_mode == "local_runtime" or privacy in {"lan_only", "sovereign_only"} or access_mode == "local"
                else "frontier_cloud"
            )
        ),
        "notes": notes,
    }


def _bridge_enabled() -> bool:
    return bool(settings.provider_bridge_url.strip())


def _bridge_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.provider_bridge_token:
        headers["Authorization"] = f"Bearer {settings.provider_bridge_token}"
    return headers


def _resolve_command(provider_id: str, command_names: list[str]) -> str | None:
    configured = os.getenv(_provider_env_key(provider_id))
    if configured:
        return configured

    for name in command_names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None


def _probe_command(command_hint: str | None, provider_id: str, probe_args: list[str]) -> dict[str, Any]:
    now = time.time()
    cache_key = (provider_id, command_hint or "", tuple(probe_args))
    cached = _COMMAND_PROBE_CACHE.get(cache_key)
    if cached and now - float(cached.get("checked_at", 0.0)) < COMMAND_PROBE_TTL_SECONDS:
        return cached

    if not command_hint:
        result = {
            "ok": False,
            "status": "missing",
            "detail": "No local command is available for this provider.",
            "checked_at": now,
        }
        _COMMAND_PROBE_CACHE[cache_key] = result
        return result

    try:
        completed = subprocess.run(
            [command_hint, *probe_args],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        output = (completed.stdout or completed.stderr or "").strip().splitlines()
        first_line = output[0][:180] if output else ""
        ok = completed.returncode == 0
        result = {
            "ok": ok,
            "status": "available" if ok else "degraded",
            "detail": first_line or f"Probe exited with code {completed.returncode}.",
            "checked_at": now,
        }
    except PermissionError as exc:
        result = {
            "ok": False,
            "status": "degraded",
            "detail": f"Probe failed with permission error: {exc}",
            "checked_at": now,
        }
    except subprocess.TimeoutExpired:
        result = {
            "ok": False,
            "status": "degraded",
            "detail": "Probe timed out while checking the local command.",
            "checked_at": now,
        }
    except OSError as exc:
        result = {
            "ok": False,
            "status": "degraded",
            "detail": f"Probe failed: {exc}",
            "checked_at": now,
        }

    _COMMAND_PROBE_CACHE[cache_key] = result
    return result


async def _fetch_bridge_provider_snapshot(force: bool = False) -> dict[str, Any]:
    if not _bridge_enabled():
        return {
            "providers": {},
            "bridge_status": "disabled",
            "detail": "Provider bridge is not configured.",
            "bridge_url": "",
        }

    now = time.time()
    bridge_url = settings.provider_bridge_url.rstrip("/")
    cached = _BRIDGE_PROVIDER_CACHE
    if (
        not force
        and cached.get("bridge_url") == bridge_url
        and now - float(cached.get("checked_at", 0.0)) < BRIDGE_PROVIDER_TTL_SECONDS
    ):
        return dict(cached)

    try:
        async with httpx.AsyncClient(timeout=min(settings.provider_bridge_timeout_seconds, 10)) as client:
            response = await client.get(f"{bridge_url}/v1/provider-bridge/providers", headers=_bridge_headers())
        response.raise_for_status()
        payload = response.json()
        providers = {
            str(item.get("provider")): dict(item)
            for item in list(payload.get("providers") or [])
            if str(item.get("provider") or "").strip()
        }
        result = {
            "providers": providers,
            "bridge_status": "available",
            "detail": str(payload.get("detail") or "DESK provider bridge is reachable."),
            "checked_at": now,
            "bridge_url": bridge_url,
        }
    except Exception as exc:  # pragma: no cover - exercised in live runtime
        result = {
            "providers": {},
            "bridge_status": "degraded",
            "detail": f"Provider bridge probe failed: {exc}",
            "checked_at": now,
            "bridge_url": bridge_url,
        }

    _BRIDGE_PROVIDER_CACHE.update(result)
    return dict(_BRIDGE_PROVIDER_CACHE)


def _build_local_adapter_record(
    provider_id: str,
    provider_meta: dict[str, Any],
    *,
    catalog_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adapter_meta = _provider_adapter_metadata(provider_id, provider_meta, catalog_meta=catalog_meta)
    command_names = list(adapter_meta.get("command_names", []))
    command_hint = _resolve_command(provider_id, command_names)
    default_mode = str(adapter_meta.get("default_mode", "handoff_bundle"))
    probe_args = list(adapter_meta.get("probe_args", []))
    probe = _probe_command(command_hint, provider_id, probe_args)
    allow_direct_cli = bool(adapter_meta.get("allow_direct_cli"))
    routing_posture = str(adapter_meta.get("routing_posture") or "ordinary_auto")

    if routing_posture == "governed_handoff_only":
        execution_mode = "handoff_bundle"
        adapter_available = False
        availability_state = "handoff-only"
    elif default_mode == "local_runtime":
        execution_mode = "local_runtime"
        adapter_available = True
        availability_state = "available"
    elif allow_direct_cli and command_hint and probe["ok"]:
        execution_mode = "direct_cli"
        adapter_available = True
        availability_state = "available"
    else:
        execution_mode = "handoff_bundle" if bool(adapter_meta.get("supports_handoff", True)) else default_mode
        adapter_available = False
        availability_state = "handoff-only" if adapter_meta.get("supports_handoff", True) else "disabled"
        if allow_direct_cli and command_hint and not probe["ok"]:
            availability_state = "degraded"

    record = {
        "provider": provider_id,
        "execution_mode": execution_mode,
        "adapter_available": adapter_available,
        "supports_handoff": bool(adapter_meta.get("supports_handoff", True)),
        "allow_direct_cli": bool(adapter_meta.get("allow_direct_cli", False)),
        "allow_bridge_cli": bool(adapter_meta.get("allow_bridge_cli", False)),
        "command_hint": command_hint,
        "meta_lane": adapter_meta.get(
            "meta_lane",
            "sovereign_local" if provider_meta.get("privacy") == "lan_only" else "frontier_cloud",
        ),
        "notes": list(adapter_meta.get("notes", [])),
        "availability_state": availability_state,
        "probe_status": str(probe.get("status", "missing")),
        "probe_detail": str(probe.get("detail", "")),
        "probe_checked_at": float(probe.get("checked_at", 0.0)),
        "bridge_status": "disabled",
        "bridge_detail": "Provider bridge is not configured.",
        "catalog_access_mode": str(adapter_meta.get("catalog_access_mode") or ""),
        "catalog_execution_modes": list(adapter_meta.get("catalog_execution_modes", [])),
        "catalog_state_classes": list(adapter_meta.get("catalog_state_classes", [])),
        "routing_posture": routing_posture,
        "routing_reason": str(adapter_meta.get("routing_reason") or ""),
    }
    if routing_posture == "governed_handoff_only":
        record["notes"].append("Policy keeps this lane governed-handoff-only until stronger evidence exists.")
    return record


async def _build_adapter_record(provider_id: str, provider_meta: dict[str, Any]) -> dict[str, Any]:
    catalog_meta = _provider_catalog_entry(provider_id)
    adapter = _build_local_adapter_record(provider_id, provider_meta, catalog_meta=catalog_meta)
    runtime_state = await _recent_provider_execution_state(provider_id)
    if adapter["execution_mode"] in {"local_runtime", "direct_cli"}:
        if runtime_state and runtime_state["status"] == "degraded" and adapter["supports_handoff"]:
            adapter["adapter_available"] = False
            adapter["execution_mode"] = "handoff_bundle"
            adapter["availability_state"] = "degraded"
            adapter["notes"].append(f"Recent direct execution degraded: {runtime_state['detail']}")
            adapter["probe_detail"] = runtime_state["detail"] or adapter["probe_detail"]
        return adapter

    bridge_snapshot = await _fetch_bridge_provider_snapshot()
    bridge_provider = dict(bridge_snapshot.get("providers", {}).get(provider_id) or {})
    adapter["bridge_status"] = str(bridge_snapshot.get("bridge_status", "disabled"))
    adapter["bridge_detail"] = str(bridge_snapshot.get("detail", ""))
    if bridge_provider.get("adapter_available") and bool(adapter.get("allow_bridge_cli")) and str(
        adapter.get("routing_posture") or "ordinary_auto"
    ) != "governed_handoff_only":
        adapter["execution_mode"] = "bridge_cli"
        adapter["adapter_available"] = True
        adapter["availability_state"] = "available"
        adapter["command_hint"] = f"bridge://{provider_id}"
        adapter["notes"].append("DESK provider bridge can execute this lane directly.")
        adapter["bridge_detail"] = str(bridge_provider.get("probe_detail") or adapter["bridge_detail"])
    elif bridge_provider.get("adapter_available") and not bool(adapter.get("allow_bridge_cli")):
        adapter["notes"].append(
            "DESK provider bridge advertised direct execution, but the provider catalog keeps this lane handoff-only."
        )
    elif bridge_provider.get("adapter_available") and str(adapter.get("routing_posture") or "") == "governed_handoff_only":
        adapter["notes"].append(
            "DESK provider bridge advertised direct execution, but policy keeps this lane governed-handoff-only."
        )
    elif adapter["availability_state"] == "handoff-only" and bridge_snapshot.get("bridge_status") == "degraded":
        adapter["availability_state"] = "degraded"
        adapter["notes"].append("DESK provider bridge is configured but currently degraded.")

    if runtime_state and runtime_state["status"] == "degraded" and adapter["supports_handoff"]:
        adapter["adapter_available"] = False
        adapter["execution_mode"] = "handoff_bundle"
        adapter["availability_state"] = "degraded"
        adapter["notes"].append(f"Recent execution degraded: {runtime_state['detail']}")
        if adapter["bridge_status"] == "available":
            adapter["bridge_detail"] = runtime_state["detail"] or adapter["bridge_detail"]

    return adapter


def _abstract_prompt(prompt: str, task_class: str) -> str:
    trimmed = prompt.strip()
    if not trimmed:
        return f"Provide planning guidance for {task_class.replace('_', ' ')}."
    redacted = trimmed[:220]
    return (
        f"Plan or review a {task_class.replace('_', ' ')} task using only abstract structure. "
        f"Do not request raw private content. Summary: {redacted}"
    )


def _handoff_instructions(provider: str, execution_mode: str, prompt_mode: str) -> list[str]:
    provider_label = provider.replace("_", " ")
    instructions = [
        f"Open the {provider_label} lane using {execution_mode.replace('_', ' ')} mode.",
        "Use the supplied plan packet and command decision as the governing context.",
    ]
    if prompt_mode == "abstracted":
        instructions.append("Use only the abstracted prompt; do not reconstruct raw sensitive content.")
    else:
        instructions.append("Use the raw prompt within the approved cloud/privacy boundary.")
    instructions.extend(
        [
            "Return a structured result: summary, key steps, artifacts, risks, and next actions.",
            "Record the result or outcome back into Athanor with the associated lease or bundle id.",
        ]
    )
    return instructions


def _truncate_output(text: str, limit: int = MAX_DIRECT_OUTPUT_CHARS) -> str:
    trimmed = text.strip()
    if len(trimmed) <= limit:
        return trimmed
    return f"{trimmed[:limit]}\n\n... [truncated, {len(trimmed)} chars total]"


_TRACE_PREFIXES = (
    "TurnBegin(",
    "StepBegin(",
    "ThinkPart(",
    "StatusUpdate(",
    "TokenUsage(",
    "TurnEnd(",
    "type=",
    "think=",
    "encrypted=",
    "context_",
    "max_context_tokens=",
    "token_usage=",
    "input_",
    "output=",
    "message_id=",
)


def _extract_text_part(text: str) -> str:
    preferred_match = re.search(
        r"TextPart\(.*?text=(?P<quote>['\"])(?P<text>.*?)(?P=quote)",
        text,
        flags=re.DOTALL,
    )
    match = preferred_match or re.search(r"text=(?P<quote>['\"])(?P<text>.*?)(?P=quote)", text, flags=re.DOTALL)
    if not match:
        return ""
    return str(match.group("text")).strip()


def _truncate_summary(text: str, limit: int = 220) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[:limit].rstrip()}..."


def _summarize_output_text(text: str, prompt_preview: str | None = None, limit: int = 220) -> str:
    prompt_line = str(prompt_preview or "").strip()
    extracted = _extract_text_part(text)
    if extracted:
        return _truncate_summary(extracted, limit)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if prompt_line and stripped == prompt_line:
            continue
        if stripped.startswith(_TRACE_PREFIXES):
            continue
        return _truncate_summary(stripped, limit)
    return ""


def _execution_summary(stdout: str, stderr: str, provider: str, prompt_preview: str | None = None) -> str:
    preferred = stdout.strip() or stderr.strip()
    if not preferred:
        return f"{provider.replace('_', ' ')} produced no output."
    summarized = _summarize_output_text(preferred, prompt_preview=prompt_preview)
    if summarized:
        return summarized
    return _truncate_output(preferred, limit=240)


def _execution_fingerprint(execution: dict[str, Any]) -> str:
    return json.dumps(execution, sort_keys=True, separators=(",", ":"), default=str)


def _append_unique_artifact_ref(
    artifact_refs: list[dict[str, str]],
    label: str,
    href: str,
) -> list[dict[str, str]]:
    if not any(str(item.get("label")) == label and str(item.get("href")) == href for item in artifact_refs):
        artifact_refs.append({"label": label, "href": href})
    return artifact_refs


def _default_provider_workspace() -> str:
    if os.name == "nt":
        return os.getenv("ATHANOR_PROVIDER_WORKSPACE_DIR", str(Path("C:/Athanor")))
    return os.getenv("ATHANOR_PROVIDER_WORKSPACE_DIR", "/opt/athanor")


def _bundle_prompt(bundle: dict[str, Any]) -> str:
    if bundle.get("prompt_mode") == "abstracted":
        return str(bundle.get("abstract_prompt") or bundle.get("prompt") or "")
    return str(bundle.get("prompt") or "")


def _coerce_bundle_timestamp(value: Any) -> float:
    if value in (None, "", 0, 0.0):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    try:
        return float(text)
    except ValueError:
        normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
        try:
            return datetime.fromisoformat(normalized).timestamp()
        except ValueError:
            return 0.0


async def list_handoff_bundles(
    requester: str = "",
    limit: int = 25,
    *,
    serialize: bool = True,
) -> list[dict[str, Any]]:
    redis = await _get_redis()
    raw = await redis.hgetall(HANDOFFS_KEY)
    bundles = [json.loads(value) for value in raw.values()]
    if requester:
        bundles = [bundle for bundle in bundles if bundle.get("requester") == requester]
    bundles.sort(key=lambda bundle: _coerce_bundle_timestamp(bundle.get("created_at")), reverse=True)
    bundles = bundles[:limit]
    if serialize:
        return [serialize_handoff_bundle(bundle) for bundle in bundles]
    return bundles


async def _recent_provider_execution_state(
    provider_id: str,
    *,
    limit: int = 25,
    ttl_seconds: int = 900,
) -> dict[str, Any] | None:
    if provider_id == "athanor_local":
        return None

    now = time.time()
    for bundle in await list_handoff_bundles(limit=limit, serialize=False):
        if str(bundle.get("provider")) != provider_id:
            continue
        updated_at = _coerce_bundle_timestamp(bundle.get("updated_at") or bundle.get("created_at"))
        if updated_at and now - updated_at > ttl_seconds:
            continue
        execution = dict(bundle.get("last_execution") or {})
        if not execution:
            continue
        detail = str(
            execution.get("stderr")
            or execution.get("summary")
            or bundle.get("failure_reason")
            or bundle.get("result_summary")
            or ""
        ).strip()
        return {
            "status": "available" if execution.get("ok") else "degraded",
            "detail": detail,
            "checked_at": updated_at,
        }
    return None


def _provider_handoff_counts(handoffs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "pending_handoffs": 0,
        "completed_handoffs": 0,
        "failed_handoffs": 0,
        "fallback_handoffs": 0,
        "direct_execution_count": 0,
        "handoff_bundle_count": 0,
    }
    for handoff in handoffs:
        status = str(handoff.get("status") or "pending")
        if status == "pending":
            counts["pending_handoffs"] += 1
        elif status == "completed":
            counts["completed_handoffs"] += 1
        elif status == "failed":
            counts["failed_handoffs"] += 1

        execution_mode = str(handoff.get("execution_mode") or "")
        if execution_mode in {"bridge_cli", "direct_cli"}:
            counts["direct_execution_count"] += 1
        if execution_mode == "handoff_bundle":
            counts["handoff_bundle_count"] += 1
        if handoff.get("fallback_from_execution_mode"):
            counts["fallback_handoffs"] += 1
    return counts


def _recent_provider_outcomes(stats: dict[str, Any], handoffs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outcomes = dict(stats.get("outcomes") or {})
    for handoff in handoffs:
        status = str(handoff.get("status") or "").strip()
        if status:
            outcomes[status] = int(outcomes.get(status, 0)) + 1
        if handoff.get("fallback_from_execution_mode"):
            outcomes["fallback_to_handoff"] = int(outcomes.get("fallback_to_handoff", 0)) + 1

    return [
        {"outcome": outcome, "count": int(count)}
        for outcome, count in sorted(outcomes.items(), key=lambda item: item[0])
    ]


def _next_action_for_provider_state(
    provider_state: str,
    *,
    direct_execution_ready: bool,
    governed_handoff_ready: bool,
    reserve_state: str,
) -> str:
    if provider_state == "disabled":
        return "leave_disabled"
    if provider_state == "throttled":
        return "preserve_reserve"
    if provider_state == "degraded":
        return "investigate_adapter"
    if provider_state == "handoff_only":
        return "use_structured_handoff"
    if direct_execution_ready and reserve_state in {"premium_interactive", "premium_async"}:
        return "keep_direct_path_ready"
    if governed_handoff_ready:
        return "direct_or_handoff"
    return "monitor"


def _recent_provider_latency_ms(provider_handoffs: list[dict[str, Any]]) -> int | None:
    durations: list[int] = []
    for handoff in provider_handoffs:
        last_execution = dict(handoff.get("last_execution") or {})
        raw_duration = last_execution.get("duration_ms") or last_execution.get("latency_ms")
        try:
            duration = int(raw_duration)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            durations.append(duration)
    if not durations:
        return None
    return int(round(sum(durations) / len(durations)))


async def build_provider_posture_records(limit: int = 25) -> list[dict[str, Any]]:
    policy = get_policy_snapshot()
    provider_catalog = {
        str(entry.get("id") or ""): dict(entry)
        for entry in get_provider_catalog_snapshot(policy_only=False).get("providers", [])
        if str(entry.get("id") or "").strip()
    }
    quotas = await get_quota_summary()
    raw_provider_stats = dict(quotas.get("providers") or {})
    raw_handoffs = await list_handoff_bundles(limit=max(limit * 2, 25), serialize=False)
    handoffs_by_provider: dict[str, list[dict[str, Any]]] = {}
    for handoff in raw_handoffs:
        provider_id = str(handoff.get("provider") or "").strip()
        if provider_id:
            handoffs_by_provider.setdefault(provider_id, []).append(dict(handoff))

    records: list[dict[str, Any]] = []
    for provider_id, provider_meta in dict(policy.get("providers") or {}).items():
        catalog_meta = dict(provider_catalog.get(provider_id) or {})
        adapter = await _build_adapter_record(provider_id, dict(provider_meta))
        stats = dict(raw_provider_stats.get(provider_id) or {})
        provider_handoffs = handoffs_by_provider.get(provider_id, [])
        counts = _provider_handoff_counts(provider_handoffs)
        recent_execution = await _recent_provider_execution_state(provider_id)
        recent_outcomes = _recent_provider_outcomes(stats, provider_handoffs)
        direct_execution_ready = bool(
            adapter.get("adapter_available")
            and str(adapter.get("execution_mode") or "") in {"bridge_cli", "direct_cli", "local_runtime"}
        )
        governed_handoff_ready = bool(adapter.get("supports_handoff", True))
        reserve_state = str(provider_meta.get("reserve") or "standard")

        state_reasons: list[str] = []
        if not provider_meta.get("enabled", True):
            provider_state = "disabled"
            state_reasons.append("provider_disabled")
        elif int(stats.get("throttle_events", 0) or 0) > 0 or any(
            str(item.get("outcome") or "") == "throttled" for item in recent_outcomes
        ):
            provider_state = "throttled"
            state_reasons.append("recent_throttle_events")
        elif str(adapter.get("availability_state") or "") == "degraded" or (
            recent_execution and recent_execution.get("status") == "degraded"
        ):
            provider_state = "degraded"
            state_reasons.append("adapter_or_recent_execution_degraded")
        elif str(adapter.get("availability_state") or "") == "handoff-only" or (
            not direct_execution_ready and governed_handoff_ready
        ):
            provider_state = "handoff_only"
            state_reasons.append("handoff_only_execution_path")
            if str(adapter.get("routing_posture") or "") == "governed_handoff_only":
                state_reasons.append("policy_governed_handoff_only")
        else:
            provider_state = "available"
            state_reasons.append("direct_or_local_path_ready")

        if counts["fallback_handoffs"] > 0:
            state_reasons.append("recent_direct_failure_fell_back_to_handoff")

        records.append(
            {
                "provider": provider_id,
                "label": str(catalog_meta.get("label") or provider_id.replace("_", " ").title()),
                "vendor": str(catalog_meta.get("vendor") or ""),
                "subscription_product": str(catalog_meta.get("subscription_product") or ""),
                "catalog_category": str(catalog_meta.get("category") or ""),
                "catalog_access_mode": str(catalog_meta.get("access_mode") or ""),
                "catalog_state_classes": list(catalog_meta.get("state_classes", [])),
                "catalog_monthly_cost_usd": catalog_meta.get("monthly_cost_usd"),
                "catalog_pricing_status": str(catalog_meta.get("official_pricing_status") or ""),
                "pricing_truth_label": str(catalog_meta.get("pricing_truth_label") or ""),
                "evidence_posture": str(catalog_meta.get("evidence_posture") or ""),
                "routing_posture": str(adapter.get("routing_posture") or provider_meta.get("routing_posture") or ""),
                "routing_reason": str(adapter.get("routing_reason") or provider_meta.get("routing_reason") or ""),
                "official_sources": list(catalog_meta.get("official_sources", [])),
                "lane": str(provider_meta.get("role") or "unclassified"),
                "availability": provider_state,
                "provider_state": provider_state,
                "state_reasons": state_reasons,
                "reserve_state": reserve_state,
                "privacy": str(provider_meta.get("privacy") or "cloud"),
                "limit": int(stats.get("limit", 0) or 0),
                "remaining": int(stats.get("remaining", 0) or 0),
                "throttle_events": int(stats.get("throttle_events", 0) or 0),
                "recent_outcomes": recent_outcomes,
                "avg_latency_ms": _recent_provider_latency_ms(provider_handoffs),
                "last_issued_at": _iso_from_unix(stats.get("last_issued_at")),
                "last_outcome_at": _iso_from_unix(stats.get("last_outcome_at")),
                "direct_execution_ready": direct_execution_ready,
                "governed_handoff_ready": governed_handoff_ready,
                "execution_mode": str(adapter.get("execution_mode") or "handoff_bundle"),
                "bridge_status": str(adapter.get("bridge_status") or "disabled"),
                "recent_execution_state": str(
                    recent_execution.get("status") if recent_execution else adapter.get("probe_status") or "missing"
                ),
                "recent_execution_detail": str(
                    recent_execution.get("detail")
                    if recent_execution
                    else adapter.get("bridge_detail") or adapter.get("probe_detail") or ""
                ),
                "next_action": _next_action_for_provider_state(
                    provider_state,
                    direct_execution_ready=direct_execution_ready,
                    governed_handoff_ready=governed_handoff_ready,
                    reserve_state=reserve_state,
                ),
                **counts,
            }
        )

    records.sort(key=lambda item: item["provider"])
    return records


async def list_handoff_events(limit: int = 25) -> list[dict[str, Any]]:
    redis = await _get_redis()
    raw = await redis.lrange(HANDOFF_EVENTS_KEY, 0, max(limit - 1, 0))
    events = [json.loads(item) for item in raw]
    events.sort(key=lambda item: _coerce_bundle_timestamp(item.get("timestamp", 0.0)), reverse=True)
    return events[:limit]


async def _record_handoff_event(event: dict[str, Any]) -> None:
    redis = await _get_redis()
    await redis.lpush(HANDOFF_EVENTS_KEY, json.dumps(event))
    await redis.ltrim(HANDOFF_EVENTS_KEY, 0, HANDOFF_EVENT_LIMIT - 1)


def _normalize_handoff_status(outcome: str) -> str:
    normalized = outcome.strip().lower()
    if normalized in {"completed", "success", "succeeded", "accepted"}:
        return "completed"
    if normalized in {"failed", "error", "rejected", "throttled"}:
        return "failed"
    if normalized in {"cancelled", "canceled", "abandoned", "skipped"}:
        return "cancelled"
    return "completed"


async def _persist_handoff_bundle(bundle: dict[str, Any]) -> None:
    redis = await _get_redis()
    await redis.hset(HANDOFFS_KEY, str(bundle["id"]), json.dumps(bundle))


async def _append_execution_attempt(handoff_id: str, execution: dict[str, Any]) -> dict[str, Any] | None:
    redis = await _get_redis()
    raw = await redis.hget(HANDOFFS_KEY, handoff_id)
    if not raw:
        return None

    bundle = json.loads(raw)
    attempts = list(bundle.get("execution_attempts") or [])
    attempts.append(execution)
    bundle["execution_attempts"] = attempts[-MAX_EXECUTION_ATTEMPTS:]
    bundle["last_execution"] = execution
    bundle["updated_at"] = time.time()
    await redis.hset(HANDOFFS_KEY, handoff_id, json.dumps(bundle))
    return bundle


async def create_handoff_bundle(
    requester: str,
    prompt: str,
    task_class: str,
    sensitivity: str = "repo_internal",
    interactive: bool = False,
    expected_context: str = "medium",
    parallelism: str = "low",
    metadata: dict[str, Any] | None = None,
    issue_lease: bool = True,
    *,
    serialize: bool = True,
) -> dict[str, Any]:
    meta = dict(metadata or {})
    lease_permission = evaluate_tool_permission(
        requester,
        "lease requests",
        tool_name="provider execution",
        metadata={"task_class": task_class, **meta},
    )
    execution_permission = evaluate_tool_permission(
        requester,
        "bounded execution",
        tool_name="provider execution",
        metadata={"task_class": task_class, **meta},
    )
    if not lease_permission["allowed"]:
        raise PermissionError(lease_permission["reason"])
    if not execution_permission["allowed"]:
        raise PermissionError(execution_permission["reason"])

    lease_request = LeaseRequest(
        requester=requester,
        task_class=task_class,
        sensitivity=sensitivity,
        interactive=interactive,
        expected_context=expected_context,
        parallelism=parallelism,
        metadata=meta,
    )
    existing_lease = dict(meta.get("execution_lease") or {})
    if existing_lease:
        lease_payload = existing_lease
        lease_id = str(existing_lease.get("id") or "") or None
    else:
        lease = (
            await issue_execution_lease(lease_request)
            if issue_lease
            else preview_execution_lease(lease_request)
        )
        lease_payload = lease.to_dict()
        lease_id = str(lease_payload.get("id") or "") if issue_lease else None
        meta["execution_lease"] = lease_payload

    command_decision = build_command_decision_record(
        prompt=prompt,
        task_class=task_class,
        requester=requester,
        metadata=meta,
    )
    plan_packet = build_plan_packet(
        prompt=prompt,
        task_class=task_class,
        requester=requester,
        metadata=meta,
    )

    policy_class = str(command_decision["policy_class"])
    prompt_mode = "abstracted" if policy_class == "hybrid_abstractable" else "raw"
    abstract_prompt = _abstract_prompt(prompt, task_class) if prompt_mode == "abstracted" else None

    selected_provider = str(lease_payload.get("provider") or "athanor_local")
    if policy_class in LOCAL_ONLY_POLICY_CLASSES and selected_provider != "athanor_local":
        raise PermissionError(
            f"{policy_class} work must remain on athanor_local, not {selected_provider}."
        )

    adapter = await _build_adapter_record(
        selected_provider,
        dict(get_policy_snapshot().get("providers", {}).get(lease_payload.get("provider"), {})),
    )
    created_at = time.time()
    bundle = HandoffBundle(
        id=f"handoff-{uuid.uuid4().hex[:12]}",
        requester=requester,
        provider=selected_provider,
        lease_id=lease_id,
        task_class=task_class,
        policy_class=policy_class,
        meta_lane=str(command_decision["meta_lane"]),
        execution_mode=str(adapter["execution_mode"]),
        created_at=created_at,
        updated_at=created_at,
        completed_at=None,
        status="pending",
        outcome=None,
        summary=f"{requester} -> {task_class} via {selected_provider}",
        prompt=prompt,
        prompt_mode=prompt_mode,
        abstract_prompt=abstract_prompt,
        fallback=list(lease_payload.get("fallback", [])),
        command_decision=command_decision,
        plan_packet=plan_packet,
        instructions=_handoff_instructions(
            selected_provider,
            str(adapter["execution_mode"]),
            prompt_mode,
        ),
        artifact_refs=[
            {"label": "agents", "href": "/agents"},
            {"label": "tasks", "href": "/tasks"},
        ],
        notes=list(adapter.get("notes", []))
        + [
            f"routing posture {lease_payload.get('metadata', {}).get('provider_routing_posture', 'unknown')}",
            f"routing reason {lease_payload.get('metadata', {}).get('provider_routing_reason', 'unspecified')}",
            f"tool-permission subject {lease_permission['subject_class']} approved lease requests",
            f"tool-permission subject {execution_permission['subject_class']} approved bounded execution",
        ],
        last_execution={},
        execution_attempts=[],
        fallback_from_execution_mode=None,
        fallback_reason="",
    )

    await _persist_handoff_bundle(bundle.to_dict())
    await _record_handoff_event(
        {
            "event": "handoff_bundle_created",
            "handoff_id": bundle.id,
            "provider": bundle.provider,
            "requester": bundle.requester,
            "task_class": bundle.task_class,
            "timestamp": bundle.created_at,
            "status": bundle.status,
            "lease_id": bundle.lease_id,
            "execution_mode": bundle.execution_mode,
        }
    )
    payload = bundle.to_dict()
    return serialize_handoff_bundle(payload) if serialize else payload


async def record_handoff_outcome(
    handoff_id: str,
    outcome: str,
    notes: str = "",
    result_summary: str = "",
    artifact_refs: list[dict[str, str]] | None = None,
    quality_score: float | None = None,
    latency_ms: int | None = None,
    execution_details: dict[str, Any] | None = None,
    *,
    serialize: bool = True,
) -> dict[str, Any] | None:
    redis = await _get_redis()
    raw = await redis.hget(HANDOFFS_KEY, handoff_id)
    if not raw:
        return None

    bundle = json.loads(raw)
    normalized_status = _normalize_handoff_status(outcome)
    completed_at = time.time()
    bundle["status"] = normalized_status
    bundle["outcome"] = outcome
    bundle["updated_at"] = completed_at
    bundle["completed_at"] = completed_at
    bundle["result_summary"] = result_summary
    bundle["failure_reason"] = notes if normalized_status == "failed" else ""
    if artifact_refs is not None:
        bundle["artifact_refs"] = artifact_refs
    if execution_details is not None:
        attempts = list(bundle.get("execution_attempts") or [])
        fingerprint = _execution_fingerprint(execution_details)
        last_attempt = attempts[-1] if attempts else None
        if not last_attempt or _execution_fingerprint(last_attempt) != fingerprint:
            attempts.append(execution_details)
        bundle["execution_attempts"] = attempts[-MAX_EXECUTION_ATTEMPTS:]
        bundle["last_execution"] = execution_details
    await redis.hset(HANDOFFS_KEY, handoff_id, json.dumps(bundle))

    lease_id = bundle.get("lease_id")
    if lease_id:
        await record_execution_outcome(
            lease_id=str(lease_id),
            outcome=outcome,
            throttled=outcome.strip().lower() == "throttled",
            notes=notes or result_summary,
            quality_score=quality_score,
            latency_ms=latency_ms,
        )

    await _record_handoff_event(
        {
            "event": "handoff_bundle_updated",
            "handoff_id": handoff_id,
            "provider": bundle.get("provider"),
            "requester": bundle.get("requester"),
            "task_class": bundle.get("task_class"),
            "timestamp": completed_at,
            "status": normalized_status,
            "outcome": outcome,
        }
    )
    return serialize_handoff_bundle(bundle) if serialize else bundle


def _build_direct_cli_command(
    provider_id: str,
    command_hint: str,
    bundle: dict[str, Any],
) -> tuple[list[str], str | None, str | None]:
    prompt = _bundle_prompt(bundle)
    workspace_dir = str(
        bundle.get("plan_packet", {}).get("workspace_dir")
        or bundle.get("command_decision", {}).get("workspace_dir")
        or _default_provider_workspace()
    )

    if provider_id == "anthropic_claude_code":
        command = [
            command_hint,
            "--print",
            "--output-format",
            "text",
            "--permission-mode",
            "default",
            "--add-dir",
            workspace_dir,
        ]
        return command, workspace_dir, prompt

    if provider_id == "moonshot_kimi":
        command = [
            command_hint,
            "--print",
            "--output-format",
            "text",
            "--work-dir",
            workspace_dir,
            "--prompt",
            prompt,
        ]
        return command, workspace_dir, None

    if provider_id == "openai_codex":
        command = [command_hint, "exec", prompt]
        return command, workspace_dir, None

    if provider_id in {"google_gemini", "zai_glm_coding"}:
        command = [command_hint, prompt]
        return command, workspace_dir, None

    raise ValueError(f"No direct CLI command builder is configured for provider '{provider_id}'.")


async def _run_direct_cli(
    command: list[str],
    cwd: str | None,
    timeout_seconds: int,
    stdin_text: str | None = None,
) -> dict[str, Any]:
    started_at = time.time()
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdin_bytes = stdin_text.encode("utf-8") if stdin_text is not None else None
        stdout, stderr = await asyncio.wait_for(process.communicate(stdin_bytes), timeout=timeout_seconds)
        duration_ms = max(int((time.time() - started_at) * 1000), 1)
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        ok = process.returncode == 0
        return {
            "ok": ok,
            "duration_ms": duration_ms,
            "exit_code": process.returncode,
            "stdout": _truncate_output(stdout_text),
            "stderr": _truncate_output(stderr_text, limit=2400),
            "summary": _execution_summary(stdout_text, stderr_text, "provider"),
        }
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return {
            "ok": False,
            "duration_ms": max(int((time.time() - started_at) * 1000), 1),
            "exit_code": None,
            "stdout": "",
            "stderr": f"Direct execution timed out after {timeout_seconds}s.",
            "summary": "Provider direct execution timed out.",
        }


async def _execute_via_bridge(
    bundle: dict[str, Any],
    adapter: dict[str, Any],
    timeout_seconds: int,
    operator_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not _bridge_enabled():
        return {
            "ok": False,
            "duration_ms": 0,
            "summary": "Provider bridge is not configured.",
            "stderr": "Provider bridge is not configured.",
        }

    started_at = time.time()
    bridge_url = settings.provider_bridge_url.rstrip("/")
    payload = {
        "provider": bundle["provider"],
        "requester": bundle["requester"],
        "task_class": bundle["task_class"],
        "policy_class": bundle["policy_class"],
        "meta_lane": bundle["meta_lane"],
        "prompt_mode": bundle["prompt_mode"],
        "prompt": bundle["prompt"],
        "abstract_prompt": bundle.get("abstract_prompt"),
        "handoff_id": bundle["id"],
        "lease_id": bundle.get("lease_id"),
        "timeout_seconds": timeout_seconds,
        "workspace_dir": bundle.get("plan_packet", {}).get("workspace_dir") or _default_provider_workspace(),
        "operator_action": dict(operator_action or {}),
    }

    try:
        async with httpx.AsyncClient(timeout=max(timeout_seconds + 15, settings.provider_bridge_timeout_seconds)) as client:
            response = await client.post(
                f"{bridge_url}/v1/provider-bridge/execute",
                headers=_bridge_headers(),
                json=payload,
            )
        response.raise_for_status()
        result = dict(response.json())
        result.setdefault("ok", True)
        result.setdefault("duration_ms", max(int((time.time() - started_at) * 1000), 1))
        return result
    except Exception as exc:  # pragma: no cover - exercised in live runtime
        return {
            "ok": False,
            "duration_ms": max(int((time.time() - started_at) * 1000), 1),
            "summary": "DESK provider bridge execution failed.",
            "stderr": str(exc),
        }


async def execute_provider_request(
    requester: str,
    prompt: str,
    task_class: str,
    sensitivity: str = "repo_internal",
    interactive: bool = False,
    expected_context: str = "medium",
    parallelism: str = "low",
    metadata: dict[str, Any] | None = None,
    issue_lease: bool = True,
    timeout_seconds: int = DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    operator_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = await create_handoff_bundle(
        requester=requester,
        prompt=prompt,
        task_class=task_class,
        sensitivity=sensitivity,
        interactive=interactive,
        expected_context=expected_context,
        parallelism=parallelism,
        metadata=metadata,
        issue_lease=issue_lease,
        serialize=False,
    )

    provider_meta = dict(get_policy_snapshot().get("providers", {}).get(bundle["provider"], {}))
    adapter = await _build_adapter_record(bundle["provider"], provider_meta)
    bundle["execution_mode"] = adapter["execution_mode"]
    bundle["notes"] = list(dict.fromkeys(list(bundle.get("notes") or []) + list(adapter.get("notes") or [])))
    await _persist_handoff_bundle(bundle)

    if adapter["execution_mode"] == "local_runtime":
        return {
            "status": "local_runtime",
            "provider": bundle["provider"],
            "handoff": serialize_handoff_bundle(bundle),
            "adapter": adapter,
            "message": "The selected lane is sovereign local runtime; use the task engine or workforce to execute locally.",
        }

    if adapter["execution_mode"] == "handoff_bundle" or not adapter["adapter_available"]:
        message = "Direct execution is unavailable; structured handoff bundle created."
        if bundle.get("lease_id"):
            await record_execution_outcome(
                lease_id=str(bundle["lease_id"]),
                outcome="handoff_created",
                notes=message,
            )
        return {
            "status": "handoff_created",
            "provider": bundle["provider"],
            "handoff": serialize_handoff_bundle(bundle),
            "adapter": adapter,
            "message": message,
        }

    await _record_handoff_event(
        {
            "event": "provider_execution_started",
            "handoff_id": bundle["id"],
            "provider": bundle["provider"],
            "requester": bundle["requester"],
            "task_class": bundle["task_class"],
            "timestamp": time.time(),
            "execution_mode": adapter["execution_mode"],
        }
    )

    if adapter["execution_mode"] == "bridge_cli":
        execution = await _execute_via_bridge(
            bundle,
            adapter,
            timeout_seconds,
            operator_action=operator_action,
        )
    else:
        command, cwd, stdin_text = _build_direct_cli_command(
            bundle["provider"],
            str(adapter.get("command_hint") or ""),
            bundle,
        )
        execution = await _run_direct_cli(
            command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            stdin_text=stdin_text,
        )
        execution.update(
            {
                "command": command,
                "cwd": cwd,
                "execution_mode": adapter["execution_mode"],
                "stdin_mode": "pipe" if stdin_text is not None else "argument",
            }
        )

    execution["provider"] = bundle["provider"]
    execution["requester"] = bundle["requester"]
    execution["policy_class"] = bundle["policy_class"]
    execution["meta_lane"] = bundle["meta_lane"]
    execution["summary"] = _execution_summary(
        str(execution.get("stdout") or ""),
        str(execution.get("stderr") or ""),
        str(bundle["provider"]),
        prompt_preview=str(bundle.get("prompt") or ""),
    )
    updated_bundle = await _append_execution_attempt(str(bundle["id"]), execution)
    if updated_bundle:
        bundle = updated_bundle

    if execution.get("ok"):
        artifact_refs = list(bundle.get("artifact_refs") or [])
        artifact_refs = _append_unique_artifact_ref(artifact_refs, "activity", "/activity")
        artifact_refs = _append_unique_artifact_ref(artifact_refs, "history", "/conversations")
        if adapter["execution_mode"] == "bridge_cli":
            artifact_refs = _append_unique_artifact_ref(artifact_refs, "bridge", "/agents")
        else:
            artifact_refs = _append_unique_artifact_ref(artifact_refs, "direct-output", "/agents")

        completed = await record_handoff_outcome(
            handoff_id=str(bundle["id"]),
            outcome="completed",
            notes="",
            result_summary=str(execution.get("summary") or f"{bundle['provider']} execution completed."),
            artifact_refs=artifact_refs,
            latency_ms=int(execution.get("duration_ms", 0) or 0),
            execution_details=execution,
            serialize=False,
        )
        return {
            "status": "completed",
            "provider": bundle["provider"],
            "handoff": serialize_handoff_bundle(completed),
            "adapter": adapter,
            "execution": execution,
            "message": "Provider execution completed successfully.",
        }

    failure_note = str(execution.get("stderr") or execution.get("summary") or "Direct provider execution failed.")
    if adapter["supports_handoff"]:
        bundle["execution_mode"] = "handoff_bundle"
        bundle["fallback_from_execution_mode"] = str(adapter["execution_mode"])
        bundle["fallback_reason"] = failure_note
        notes = list(bundle.get("notes") or [])
        notes.append(f"Direct execution failed; downgraded to handoff mode: {failure_note}")
        bundle["notes"] = notes[-12:]
        bundle["updated_at"] = time.time()
        await _persist_handoff_bundle(bundle)
        await _record_handoff_event(
            {
                "event": "provider_execution_fallback",
                "handoff_id": bundle["id"],
                "provider": bundle["provider"],
                "requester": bundle["requester"],
                "task_class": bundle["task_class"],
                "timestamp": time.time(),
                "execution_mode": adapter["execution_mode"],
                "fallback_mode": "handoff_bundle",
                "detail": failure_note,
            }
        )
        if bundle.get("lease_id"):
            await record_execution_outcome(
                lease_id=str(bundle["lease_id"]),
                outcome="fallback_to_handoff",
                notes=failure_note,
                latency_ms=int(execution.get("duration_ms", 0) or 0),
            )
        return {
            "status": "fallback_to_handoff",
            "provider": bundle["provider"],
            "handoff": serialize_handoff_bundle(bundle),
            "adapter": adapter,
            "execution": execution,
            "message": "Direct provider execution failed; structured handoff remains available.",
        }

    failed = await record_handoff_outcome(
        handoff_id=str(bundle["id"]),
        outcome="failed",
        notes=failure_note,
        result_summary=str(execution.get("summary") or ""),
        latency_ms=int(execution.get("duration_ms", 0) or 0),
        execution_details=execution,
        serialize=False,
    )
    return {
        "status": "failed",
        "provider": bundle["provider"],
        "handoff": serialize_handoff_bundle(failed),
        "adapter": adapter,
        "execution": execution,
        "message": "Provider execution failed and no governed handoff fallback is available.",
    }


async def build_provider_execution_snapshot(limit: int = 10) -> dict[str, Any]:
    policy = get_policy_snapshot()
    catalog = get_provider_catalog_snapshot(policy_only=True)
    adapters = []
    for provider_id, provider_meta in dict(policy.get("providers") or {}).items():
        adapters.append(await _build_adapter_record(provider_id, dict(provider_meta)))

    adapters.sort(key=lambda item: item["provider"])
    provider_posture = await build_provider_posture_records(limit=limit)
    handoffs = await list_handoff_bundles(limit=limit)
    handoff_events = await list_handoff_events(limit=limit)
    recent_leases = await list_execution_leases(limit=limit)
    status_counts: dict[str, int] = {}
    provider_state_counts: dict[str, int] = {}
    for handoff in handoffs:
        status = str(handoff.get("status") or "pending")
        status_counts[status] = status_counts.get(status, 0) + 1
    for provider in provider_posture:
        state = str(provider.get("provider_state") or "unknown")
        provider_state_counts[state] = provider_state_counts.get(state, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_source": policy.get("policy_source", "unknown"),
        "catalog_version": catalog.get("version", ""),
        "catalog_source": catalog.get("source_of_truth", ""),
        "adapters": adapters,
        "provider_posture": provider_posture,
        "provider_state_counts": provider_state_counts,
        "recent_handoffs": handoffs,
        "recent_events": handoff_events,
        "recent_leases": recent_leases,
        "handoff_status_counts": status_counts,
        "total_handoffs": len(handoffs),
        "direct_execution_count": sum(
            1 for handoff in handoffs if str(handoff.get("execution_mode") or "") in {"bridge_cli", "direct_cli"}
        ),
        "handoff_only_count": sum(
            1 for handoff in handoffs if str(handoff.get("execution_mode") or "") == "handoff_bundle"
        ),
        "count": len(adapters),
    }
