"""Emergency protocol routes — CONSTITUTION.yaml kill switch, resume, status."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

logger = logging.getLogger("athanor.emergency")

router = APIRouter(prefix="/v1/emergency", tags=["emergency"])

_autonomous_operations_enabled = True

_BREAKER_NAMES = ["coordinator", "worker", "litellm", "qdrant", "redis", "embedding", "utility"]


def is_autonomous_enabled() -> bool:
    return _autonomous_operations_enabled


@router.post("/stop")
async def emergency_stop():
    """Kill switch — halt all autonomous operations immediately.

    CONSTITUTION emergency.kill_switch: halt_all_autonomous_operations
    """
    global _autonomous_operations_enabled
    _autonomous_operations_enabled = False

    from ..scheduler import stop_scheduler
    from ..circuit_breaker import get_circuit_breakers

    await stop_scheduler()

    cbs = get_circuit_breakers()
    for name in _BREAKER_NAMES:
        try:
            breaker = cbs.get_or_create(name)
            await breaker.force_open()
        except Exception:
            pass

    try:
        from ..escalation import _send_ntfy_notification
        await _send_ntfy_notification(
            title="EMERGENCY STOP",
            body="All autonomous operations halted. Scheduler stopped. Circuit breakers opened.",
            priority="urgent",
            tags=["rotating_light", "stop_sign"],
        )
    except Exception:
        pass

    from ..constitution import _log_audit
    _log_audit(
        operation_type="emergency_stop",
        target_resource="all",
        actor="operator",
        result="halted",
        constraint_checked="EMERGENCY",
    )

    logger.warning("EMERGENCY STOP activated — all autonomous operations halted")
    return {
        "status": "halted",
        "timestamp": datetime.now().isoformat(),
        "scheduler": "stopped",
        "circuit_breakers": "all_open",
    }


@router.post("/resume")
async def emergency_resume(request: Request):
    """Resume autonomous operations after emergency stop.

    Requires confirmation token in body: {"confirm": "RESUME"}
    """
    global _autonomous_operations_enabled

    try:
        body = await request.json()
    except Exception:
        body = {}
    if body.get("confirm") != "RESUME":
        return JSONResponse(
            status_code=400,
            content={"error": "Must provide {\"confirm\": \"RESUME\"} to resume operations"},
        )

    _autonomous_operations_enabled = True

    from ..scheduler import start_scheduler
    from ..circuit_breaker import get_circuit_breakers

    await start_scheduler()

    cbs = get_circuit_breakers()
    for name in _BREAKER_NAMES:
        try:
            breaker = cbs.get_or_create(name)
            await breaker.force_close()
        except Exception:
            pass

    try:
        from ..escalation import _send_ntfy_notification
        await _send_ntfy_notification(
            title="EMERGENCY RESUME",
            body="Autonomous operations resumed. Scheduler restarted. Circuit breakers reset.",
            priority="high",
            tags=["white_check_mark"],
        )
    except Exception:
        pass

    from ..constitution import _log_audit
    _log_audit(
        operation_type="emergency_resume",
        target_resource="all",
        actor="operator",
        result="resumed",
        constraint_checked="EMERGENCY",
    )

    logger.info("Emergency resume — autonomous operations restored")
    return {
        "status": "resumed",
        "timestamp": datetime.now().isoformat(),
        "scheduler": "running",
        "circuit_breakers": "all_closed",
    }


@router.get("/status")
async def emergency_status():
    """Check whether autonomous operations are enabled."""
    from ..scheduler import _scheduler_task
    return {
        "autonomous_operations_enabled": _autonomous_operations_enabled,
        "scheduler_running": _scheduler_task is not None and not _scheduler_task.done(),
        "timestamp": datetime.now().isoformat(),
    }
