from __future__ import annotations

import asyncio
import atexit
import importlib
import logging
from datetime import datetime, timezone
from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from .config import settings

logger = logging.getLogger(__name__)
_CHECKPOINTER_CONTEXT = None
_CHECKPOINTER_CLEANUP_REGISTERED = False
_LAST_CHECKPOINTER_STATUS: dict[str, object] = {}

CHECKPOINTER_ENV_VAR = "ATHANOR_POSTGRES_URL"
CHECKPOINTER_PRIMARY_DRIVER = "langgraph.checkpoint.postgres.PostgresSaver"
CHECKPOINTER_SETUP_AUTHORITY = "langgraph.checkpoint.postgres.PostgresSaver.setup()"
CHECKPOINTER_FALLBACK_DRIVER = "langgraph.checkpoint.memory.InMemorySaver"
CHECKPOINTER_REQUIRED_PACKAGES = [
    "langgraph-checkpoint-postgres>=3.0.5",
    "psycopg[binary]>=3.2",
]
CHECKPOINTER_LAUNCH_BLOCKER_RULES = {
    "configured_postgres_requires_durable": "launch_blocker",
    "schema_bootstrap_incomplete": "launch_blocker",
    "restart_proof_missing_after_cutover": "launch_blocker",
    "unconfigured_runtime": "explicit_memory_fallback_allowed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _postgres_configured() -> bool:
    return bool(str(settings.postgres_url or "").strip())


def _set_checkpointer_status(
    mode: str,
    *,
    durable: bool,
    configured: bool | None = None,
    driver: str | None = None,
    reason: str | None = None,
) -> None:
    global _LAST_CHECKPOINTER_STATUS

    if configured is None:
        configured = _postgres_configured()

    _LAST_CHECKPOINTER_STATUS = {
        "mode": mode,
        "durable": durable,
        "configured": configured,
        "driver": driver,
        "reason": reason,
        "env_var": CHECKPOINTER_ENV_VAR,
        "primary_driver": CHECKPOINTER_PRIMARY_DRIVER,
        "setup_authority": CHECKPOINTER_SETUP_AUTHORITY,
        "fallback_driver": CHECKPOINTER_FALLBACK_DRIVER,
        "required_packages": list(CHECKPOINTER_REQUIRED_PACKAGES),
        "launch_blocker_rules": dict(CHECKPOINTER_LAUNCH_BLOCKER_RULES),
        "last_updated_at": _utc_now(),
    }


def get_checkpointer_status() -> dict[str, object]:
    if not _LAST_CHECKPOINTER_STATUS:
        _set_checkpointer_status(
            "uninitialized",
            durable=False,
            driver=None,
            reason="Checkpointer has not been built yet",
        )
    return dict(_LAST_CHECKPOINTER_STATUS)


def build_checkpointer_contract() -> dict[str, object]:
    status = get_checkpointer_status()
    if bool(status.get("configured")) and str(status.get("mode") or "") == "uninitialized":
        build_checkpointer()
        status = get_checkpointer_status()
    postgres_module_available = importlib.util.find_spec("langgraph.checkpoint.postgres") is not None
    return {
        "env_contract": {
            "name": CHECKPOINTER_ENV_VAR,
            "configured": bool(status.get("configured")),
            "blank_means": "memory_fallback_explicit",
            "set_means": "durable_postgres_required",
        },
        "driver_contract": {
            "desired": CHECKPOINTER_PRIMARY_DRIVER,
            "active": str(status.get("driver") or ""),
            "fallback": CHECKPOINTER_FALLBACK_DRIVER,
            "setup_authority": CHECKPOINTER_SETUP_AUTHORITY,
        },
        "dependency_contract": {
            "required_packages": list(CHECKPOINTER_REQUIRED_PACKAGES),
            "postgres_module_available": postgres_module_available,
        },
        "runtime_contract": {
            "mode": str(status.get("mode") or "unknown"),
            "durable": bool(status.get("durable")),
            "configured": bool(status.get("configured")),
            "driver": str(status.get("driver") or ""),
            "reason": str(status.get("reason") or ""),
        },
        "launch_blocker_contract": dict(CHECKPOINTER_LAUNCH_BLOCKER_RULES),
    }


def _register_checkpointer_cleanup() -> None:
    global _CHECKPOINTER_CLEANUP_REGISTERED
    if not _CHECKPOINTER_CLEANUP_REGISTERED:
        atexit.register(_close_checkpointer_context)
        _CHECKPOINTER_CLEANUP_REGISTERED = True


def _close_checkpointer_context() -> None:
    global _CHECKPOINTER_CONTEXT
    context = _CHECKPOINTER_CONTEXT
    _CHECKPOINTER_CONTEXT = None
    if context is None:
        return
    exit_method = getattr(context, "__exit__", None)
    if callable(exit_method):
        exit_method(None, None, None)


def reset_checkpointer_cache() -> None:
    build_checkpointer.cache_clear()
    _close_checkpointer_context()
    _set_checkpointer_status(
        "uninitialized",
        durable=False,
        driver=None,
        reason="Checkpointer cache reset",
    )


def _load_postgres_saver():
    module = importlib.import_module("langgraph.checkpoint.postgres")
    return module.PostgresSaver


def _needs_async_checkpointer_shim(saver: object) -> bool:
    saver_type = type(saver)
    return any(
        getattr(saver_type, name, None) is None
        or getattr(saver_type, name, None) is getattr(BaseCheckpointSaver, name, None)
        for name in ("aget_tuple", "aput", "aput_writes", "alist")
    )


def _install_async_checkpointer_shim(saver):
    if not _needs_async_checkpointer_shim(saver):
        return saver

    async def _aget_tuple(config):
        return await asyncio.to_thread(saver.get_tuple, config)

    async def _aput(config, checkpoint, metadata, new_versions):
        return await asyncio.to_thread(saver.put, config, checkpoint, metadata, new_versions)

    async def _aput_writes(config, writes, task_id, task_path=""):
        return await asyncio.to_thread(saver.put_writes, config, writes, task_id, task_path)

    async def _alist(config, *, filter=None, before=None, limit=None):
        items = await asyncio.to_thread(
            lambda: list(saver.list(config, filter=filter, before=before, limit=limit))
        )
        for item in items:
            yield item

    saver.aget_tuple = _aget_tuple
    saver.aput = _aput
    saver.aput_writes = _aput_writes
    saver.alist = _alist
    return saver


@lru_cache(maxsize=1)
def build_checkpointer():
    postgres_url = str(settings.postgres_url or "").strip()
    if not postgres_url:
        reason = "ATHANOR_POSTGRES_URL not configured"
        logger.info("%s; using InMemorySaver fallback", reason)
        _set_checkpointer_status(
            "memory_fallback",
            durable=False,
            configured=False,
            driver="langgraph.checkpoint.memory.InMemorySaver",
            reason=reason,
        )
        return InMemorySaver()

    try:
        PostgresSaver = _load_postgres_saver()
    except ModuleNotFoundError:
        reason = "langgraph.checkpoint.postgres is not installed"
        logger.warning(
            "%s; using InMemorySaver fallback until durable checkpointer deps land",
            reason,
        )
        _set_checkpointer_status(
            "memory_fallback",
            durable=False,
            configured=True,
            driver="langgraph.checkpoint.memory.InMemorySaver",
            reason=reason,
        )
        return InMemorySaver()

    saver_candidate = None
    saver = None
    try:
        saver_candidate = PostgresSaver.from_conn_string(postgres_url)
        enter = getattr(saver_candidate, "__enter__", None)
        exit_method = getattr(saver_candidate, "__exit__", None)
        if callable(enter) and callable(exit_method):
            saver = enter()
        else:
            saver = saver_candidate

        saver = _install_async_checkpointer_shim(saver)

        setup = getattr(saver, "setup", None)
        if callable(setup):
            setup()
    except Exception as exc:
        logger.exception(
            "Failed to initialize Postgres-backed LangGraph checkpointer; using InMemorySaver fallback"
        )
        if saver_candidate is not None:
            exit_method = getattr(saver_candidate, "__exit__", None)
            if callable(exit_method):
                exit_method(None, None, None)
        _set_checkpointer_status(
            "memory_fallback",
            durable=False,
            configured=True,
            driver="langgraph.checkpoint.memory.InMemorySaver",
            reason=f"Postgres checkpointer init failed: {exc}",
        )
        return InMemorySaver()

    if saver_candidate is not None:
        enter = getattr(saver_candidate, "__enter__", None)
        exit_method = getattr(saver_candidate, "__exit__", None)
        if callable(enter) and callable(exit_method):
            global _CHECKPOINTER_CONTEXT
            _CHECKPOINTER_CONTEXT = saver_candidate
            _register_checkpointer_cleanup()

    _set_checkpointer_status(
        "postgres",
        durable=True,
        configured=True,
        driver="langgraph.checkpoint.postgres.PostgresSaver",
        reason=None,
    )
    logger.info("Using Postgres-backed LangGraph checkpointer")
    return saver
