from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from langgraph.checkpoint.base import empty_checkpoint

from .config import settings
from .persistence import build_checkpointer, get_checkpointer_status, reset_checkpointer_cache


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    preferred: Path | None = None
    for base in Path(__file__).resolve().parents:
        if base.joinpath("STATUS.md").exists() and base.joinpath("config", "automation-backbone").exists():
            return base
        if base.joinpath("config", "automation-backbone").exists():
            preferred = base
    if preferred is not None:
        return preferred
    for base in Path(__file__).resolve().parents:
        if base.joinpath("config", "automation-backbone").exists():
            return base
    return Path("/workspace")


@lru_cache(maxsize=1)
def _runtime_artifact_root() -> Path:
    env_root = str(os.getenv("ATHANOR_RUNTIME_ARTIFACT_ROOT") or "").strip()
    if env_root:
        return Path(env_root)

    repo_root = _repo_root()
    if os.access(repo_root, os.W_OK):
        return repo_root

    output_root = Path("/output")
    if output_root.exists() and os.access(output_root, os.W_OK):
        return output_root

    return repo_root


def durable_restart_proof_path() -> Path:
    return _runtime_artifact_root() / "reports" / "bootstrap" / "durable-restart-proof.json"


def read_durable_restart_proof() -> dict[str, Any]:
    path = durable_restart_proof_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_restart_proof_artifact(payload: dict[str, Any]) -> Path:
    path = durable_restart_proof_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _materialize_durable_checkpointer() -> tuple[Any, dict[str, Any]]:
    status = dict(get_checkpointer_status())
    if bool(status.get("configured")) and str(status.get("mode") or "") == "uninitialized":
        build_checkpointer()
        status = dict(get_checkpointer_status())
    saver = build_checkpointer()
    status = dict(get_checkpointer_status())
    return saver, status


def _pending_effect_markers(pending_writes: list[Any], effect_id: str) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for item in pending_writes or []:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        task_id = str(item[0] or "")
        channel = str(item[1] or "")
        value = item[2] if isinstance(item[2], dict) else {}
        if channel != "destructive_effect_marker":
            continue
        if str(value.get("effect_id") or "") != effect_id:
            continue
        markers.append(
            {
                "task_id": task_id,
                "channel": channel,
                "value": value,
            }
        )
    return markers


def _tuple_summary(checkpoint_tuple: Any, *, effect_id: str) -> dict[str, Any]:
    if checkpoint_tuple is None:
        return {
            "present": False,
            "checkpoint_id": "",
            "thread_id": "",
            "checkpoint_ns": "",
            "metadata": {},
            "pending_write_count": 0,
            "effect_marker_count": 0,
            "effect_markers": [],
        }

    config = dict(getattr(checkpoint_tuple, "config", {}) or {})
    configurable = dict(config.get("configurable") or {})
    metadata = dict(getattr(checkpoint_tuple, "metadata", {}) or {})
    pending_writes = list(getattr(checkpoint_tuple, "pending_writes", []) or [])
    effect_markers = _pending_effect_markers(pending_writes, effect_id)
    return {
        "present": True,
        "checkpoint_id": str(configurable.get("checkpoint_id") or ""),
        "thread_id": str(configurable.get("thread_id") or ""),
        "checkpoint_ns": str(configurable.get("checkpoint_ns") or ""),
        "metadata": metadata,
        "pending_write_count": len(pending_writes),
        "effect_marker_count": len(effect_markers),
        "effect_markers": effect_markers,
    }


def _fetch_local_health_snapshot() -> dict[str, Any]:
    url = "http://localhost:9000/health"
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def prepare_durable_restart_proof(*, actor: str = "operator", reason: str = "") -> dict[str, Any]:
    saver, status = _materialize_durable_checkpointer()
    now = _utc_now()
    proof_id = uuid.uuid4().hex[:12]
    effect_id = f"effect-{proof_id}"
    config = {
        "configurable": {
            "thread_id": f"bootstrap-restart-proof-{proof_id}",
            "checkpoint_ns": "bootstrap/durable-restart-proof",
        }
    }
    payload: dict[str, Any] = {
        "generated_at": now,
        "prepared_at": now,
        "verified_at": "",
        "proof_id": proof_id,
        "actor": actor,
        "reason": reason,
        "phase": "prepared",
        "passed": False,
        "detail": "",
        "artifact_path": str(durable_restart_proof_path()),
        "persistence_status": status,
        "checkpoint_config": config,
        "effect_id": effect_id,
        "restart_requirements": [
            "Restart the athanor-agents runtime after the checkpoint has been written.",
            "Rebuild the durable checkpointer in the restarted runtime.",
            "Verify the checkpoint tuple and destructive-effect marker persist exactly once.",
            "Verify /health still reports durable Postgres persistence.",
        ],
    }

    if not bool(status.get("configured")):
        payload["detail"] = "ATHANOR_POSTGRES_URL is not configured, so restart proof cannot run."
        _write_restart_proof_artifact(payload)
        return payload

    if not bool(status.get("durable")):
        payload["detail"] = (
            "Configured runtime is not using durable persistence yet: "
            f"mode={status.get('mode')}, reason={status.get('reason') or 'unknown'}."
        )
        _write_restart_proof_artifact(payload)
        return payload

    checkpoint = empty_checkpoint()
    metadata = {
        "source": "bootstrap_durable_restart_proof",
        "actor": actor,
        "reason": reason,
        "proof_id": proof_id,
        "effect_id": effect_id,
        "step": 1,
        "prepared_at": now,
    }
    checkpoint_config = saver.put(config, checkpoint, metadata, {})
    saver.put_writes(
        checkpoint_config,
        [
            (
                "destructive_effect_marker",
                {
                    "effect_id": effect_id,
                    "count": 1,
                    "kind": "simulated_non_replayable_effect",
                },
            )
        ],
        task_id=f"restart-proof-{proof_id}",
    )
    before_tuple = saver.get_tuple(checkpoint_config)
    payload["checkpoint_config"] = checkpoint_config
    payload["pre_restart"] = _tuple_summary(before_tuple, effect_id=effect_id)
    payload["detail"] = "Prepared durable restart proof checkpoint and effect marker."
    _write_restart_proof_artifact(payload)
    return payload


def finalize_durable_restart_proof(
    proof_id: str,
    *,
    actor: str = "operator",
    reason: str = "",
) -> dict[str, Any]:
    artifact = read_durable_restart_proof()
    now = _utc_now()
    if not artifact:
        payload = {
            "generated_at": now,
            "prepared_at": "",
            "verified_at": now,
            "proof_id": proof_id,
            "actor": actor,
            "reason": reason,
            "phase": "verified",
            "passed": False,
            "detail": "No prepared durable restart proof artifact exists.",
            "artifact_path": str(durable_restart_proof_path()),
            "persistence_status": dict(get_checkpointer_status()),
        }
        _write_restart_proof_artifact(payload)
        return payload

    payload = dict(artifact)
    payload["verified_at"] = now
    payload["actor"] = actor or str(payload.get("actor") or "operator")
    if reason:
        payload["reason"] = reason
    if str(payload.get("proof_id") or "") != proof_id:
        payload["phase"] = "verified"
        payload["passed"] = False
        payload["detail"] = (
            f"Prepared proof id {payload.get('proof_id')!r} does not match requested proof id {proof_id!r}."
        )
        _write_restart_proof_artifact(payload)
        return payload

    reset_checkpointer_cache()
    saver, status = _materialize_durable_checkpointer()
    payload["persistence_status"] = status
    if not bool(status.get("durable")):
        payload["phase"] = "verified"
        payload["passed"] = False
        payload["detail"] = (
            "Runtime did not rebuild a durable Postgres checkpointer after restart: "
            f"mode={status.get('mode')}, reason={status.get('reason') or 'unknown'}."
        )
        _write_restart_proof_artifact(payload)
        return payload

    checkpoint_config = dict(payload.get("checkpoint_config") or {})
    effect_id = str(payload.get("effect_id") or "")
    after_tuple = saver.get_tuple(checkpoint_config)
    payload["post_restart"] = _tuple_summary(after_tuple, effect_id=effect_id)
    health = _fetch_local_health_snapshot()
    if health:
        payload["health_snapshot"] = {
            "status": str(health.get("status") or ""),
            "persistence": dict(health.get("persistence") or {}),
            "bootstrap": dict(health.get("bootstrap") or {}),
        }

    post_restart = dict(payload.get("post_restart") or {})
    effect_markers = list(post_restart.get("effect_markers") or [])
    health_persistence = dict((payload.get("health_snapshot") or {}).get("persistence") or {})
    passed = (
        bool(post_restart.get("present"))
        and str(post_restart.get("checkpoint_id") or "")
        == str(dict(checkpoint_config.get("configurable") or {}).get("checkpoint_id") or "")
        and int(post_restart.get("effect_marker_count") or 0) == 1
        and len(effect_markers) == 1
        and int(dict(effect_markers[0].get("value") or {}).get("count") or 0) == 1
        and str(dict(post_restart.get("metadata") or {}).get("proof_id") or "") == proof_id
        and str(dict(post_restart.get("metadata") or {}).get("effect_id") or "") == effect_id
        and bool(health_persistence.get("durable"))
        and str(health_persistence.get("mode") or "") == "postgres"
    )
    payload["phase"] = "verified"
    payload["passed"] = passed
    payload["detail"] = (
        "Durable restart proof passed: checkpoint tuple, effect marker, and health persistence all survived restart."
        if passed
        else (
            "Durable restart proof failed after restart: "
            f"present={bool(post_restart.get('present'))}, "
            f"effect_marker_count={int(post_restart.get('effect_marker_count') or 0)}, "
            f"health_durable={bool(health_persistence.get('durable'))}, "
            f"health_mode={str(health_persistence.get('mode') or 'unknown')}."
        )
    )
    _write_restart_proof_artifact(payload)
    return payload
