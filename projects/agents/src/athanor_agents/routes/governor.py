"""Governor API routes — matches dashboard proxy expectations."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["governor"])


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
        )
        return None, None, JSONResponse(status_code=status_code, content={"error": detail})

    return body, action, None


@router.get("/governor")
async def governor_snapshot():
    """Full governor snapshot matching governorSnapshotSchema."""
    from ..governor import build_governor_snapshot

    return await build_governor_snapshot()


@router.post("/governor/pause")
async def governor_pause(request: Request):
    """Pause governor globally or a specific lane."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/pause",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    scope = body.get("scope", "global")
    actor = action.actor
    reason = action.reason

    gov = Governor.get()
    await gov.pause(scope=scope, actor=actor, reason=reason)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/pause",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Paused governor scope={scope}",
        target=scope,
    )
    return {"status": "paused", "scope": scope}


@router.post("/governor/resume")
async def governor_resume(request: Request):
    """Resume governor globally or a specific lane."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/resume",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    scope = body.get("scope", "global")
    actor = action.actor
    reason = action.reason

    gov = Governor.get()
    await gov.resume(scope=scope, actor=actor, reason=reason)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/resume",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Resumed governor scope={scope}",
        target=scope,
    )
    return {"status": "resumed", "scope": scope}


@router.post("/governor/heartbeat")
async def governor_heartbeat(request: Request):
    """Record a heartbeat from the dashboard."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/heartbeat",
        action_class="operator",
        default_reason="Dashboard heartbeat acknowledgement",
    )
    if denial:
        return denial
    source = body.get("source", "dashboard")

    gov = Governor.get()
    await gov.record_heartbeat(source=source)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/heartbeat",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Recorded heartbeat source={source}",
        target=source,
    )
    return {"status": "ok", "source": source}


@router.post("/governor/presence")
async def governor_presence(request: Request):
    """Set presence mode and state."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/presence",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    mode = body.get("mode", "auto")
    state = body.get("state", "at_desk")
    reason = action.reason
    actor = action.actor

    gov = Governor.get()
    await gov.set_presence(mode=mode, state=state, reason=reason, actor=actor)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/presence",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Set operator presence mode={mode} state={state}",
        target=state,
        metadata={"mode": mode},
    )
    return {"status": "ok", "mode": mode, "state": state}


@router.post("/governor/release-tier")
async def governor_release_tier(request: Request):
    """Set the release tier for cloud provider access."""
    from ..governor import Governor

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/release-tier",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial
    tier = body.get("tier", "standard")
    reason = action.reason
    actor = action.actor

    gov = Governor.get()
    await gov.set_release_tier(tier=tier, reason=reason, actor=actor)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/release-tier",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Set release tier={tier}",
        target=tier,
    )
    return {"status": "ok", "tier": tier}


@router.get("/governor/operations")
async def governor_operations():
    """Operations readiness check."""
    from ..governor import build_operations_readiness_snapshot

    return await build_operations_readiness_snapshot()


@router.get("/governor/operator-tests")
async def governor_operator_tests():
    """List available operator tests."""
    from ..operator_tests import build_operator_tests_snapshot

    return await build_operator_tests_snapshot()


@router.post("/governor/operator-tests/run")
async def governor_run_operator_tests(request: Request):
    """Run operator tests."""
    from ..operator_tests import run_operator_tests

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/governor/operator-tests/run",
        action_class="admin",
        default_reason="",
    )
    if denial:
        return denial

    flow_ids = body.get("flow_ids")
    if isinstance(flow_ids, list):
        selected_flow_ids = [str(flow_id) for flow_id in flow_ids if str(flow_id).strip()]
    else:
        selected_flow_ids = None

    snapshot = await run_operator_tests(flow_ids=selected_flow_ids, actor=action.actor)
    passed = sum(
        1 for flow in snapshot.get("flows", []) if str(flow.get("last_outcome") or "").strip().lower() == "passed"
    )
    total = int(snapshot.get("flow_count", len(snapshot.get("flows", []))) or 0)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/governor/operator-tests/run",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Executed operator tests passed={passed}/{total}",
        metadata={
            "source": body.get("source", "dashboard"),
            "flow_ids": selected_flow_ids or [],
        },
    )
    return snapshot


@router.get("/governor/tool-permissions")
async def governor_tool_permissions():
    """Get the canonical tool-permission governance snapshot."""
    from ..governor import build_tool_permissions_snapshot

    return await build_tool_permissions_snapshot()

