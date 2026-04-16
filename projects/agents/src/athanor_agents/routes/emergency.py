"""Emergency protocol routes â€” CONSTITUTION.yaml kill switch, resume, status."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

logger = logging.getLogger("athanor.emergency")

router = APIRouter(prefix="/v1/emergency", tags=["emergency"])

_autonomous_operations_enabled = True

_BREAKER_NAMES = ["coordinator", "worker", "litellm", "qdrant", "redis", "embedding", "utility"]


def is_autonomous_enabled() -> bool:
    return _autonomous_operations_enabled


async def _load_operator_body(
    request: Request,
    *,
    route: str,
    action_class: str,
    default_reason: str,
):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        body = {}

    candidate = build_operator_action(body, default_reason=default_reason)
    try:
        action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        await emit_operator_audit_event(
            service="agent-server",
            route=route,
            action_class=action_class,
            decision="denied",
            status_code=status_code,
            action=candidate,
            detail=str(detail),
            target="all",
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


@router.post("/stop")
async def emergency_stop(request: Request):
    """Kill switch â€” halt all autonomous operations immediately."""
    global _autonomous_operations_enabled

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/emergency/stop",
        action_class="destructive-admin",
        default_reason="Activated emergency stop",
    )
    if denial:
        return denial

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
        actor=action.actor,
        result="halted",
        constraint_checked="EMERGENCY",
    )

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/emergency/stop",
        action_class="destructive-admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Activated emergency stop",
        target="all",
    )
    logger.warning("EMERGENCY STOP activated â€” all autonomous operations halted")
    return {
        "status": "halted",
        "timestamp": datetime.now().isoformat(),
        "scheduler": "stopped",
        "circuit_breakers": "all_open",
    }


@router.post("/resume")
async def emergency_resume(request: Request):
    """Resume autonomous operations after emergency stop."""
    global _autonomous_operations_enabled

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/emergency/resume",
        action_class="admin",
        default_reason="Resumed autonomous operations",
    )
    if denial:
        return denial

    if body.get("confirm") != "RESUME":
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/emergency/resume",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail='Must provide {"confirm": "RESUME"} to resume operations',
            target="all",
        )
        return JSONResponse(
            status_code=400,
            content={"error": 'Must provide {"confirm": "RESUME"} to resume operations'},
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
        actor=action.actor,
        result="resumed",
        constraint_checked="EMERGENCY",
    )

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/emergency/resume",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Resumed autonomous operations",
        target="all",
    )
    logger.info("Emergency resume â€” autonomous operations restored")
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
