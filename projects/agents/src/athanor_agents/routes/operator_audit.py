from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import build_operator_action, emit_operator_audit_event, validate_operator_action

router = APIRouter(prefix="/v1/operator", tags=["operator-audit"])


@router.post("/audit")
async def operator_audit_ingest(request: Request):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "JSON object body is required"})

    action_class = str(body.get("action_class") or "operator")
    action = build_operator_action(body.get("action"), default_actor="dashboard-operator")
    try:
        validate_operator_action(action, action_class=action_class)
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        return JSONResponse(status_code=400, content={"error": detail})

    await emit_operator_audit_event(
        service=str(body.get("service") or "dashboard"),
        route=str(body.get("route") or "/unknown"),
        action_class=action_class,
        decision=str(body.get("decision") or "accepted"),
        status_code=int(body.get("status_code") or 200),
        action=action,
        detail=str(body.get("detail") or "") or None,
        target=str(body.get("target") or "") or None,
        metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
    )
    return {"ok": True}
