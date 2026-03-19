"""Model governance endpoints - extracted from backbone server.py.

These endpoints handle model promotions, retirements, and the proving ground.
Extracted from the backbone branch and reconciled into main as a router module.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["model-governance"])


@router.get("/v1/models/governance")
async def model_governance():
    from ..model_governance import build_live_model_governance_snapshot

    return await build_live_model_governance_snapshot()


@router.get("/v1/models/governance/promotions")
async def model_governance_promotions(limit: int = 12):
    from ..promotion_control import build_promotion_controls_snapshot

    return await build_promotion_controls_snapshot(limit=limit)


@router.post("/v1/models/governance/promotions")
async def stage_model_governance_promotion(request: Request):
    from ..promotion_control import stage_promotion_candidate

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    role_id = body.get("role_id", "") if isinstance(body, dict) else ""
    candidate = body.get("candidate", "") if isinstance(body, dict) else ""
    if not role_id or not candidate:
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'role_id' and 'candidate' are required"},
        )

    record = await stage_promotion_candidate(
        role_id=role_id,
        candidate=candidate,
        target_tier=body.get("target_tier", "canary") if isinstance(body, dict) else "canary",
        actor=body.get("actor", "operator") if isinstance(body, dict) else "operator",
        reason=body.get("reason", "") if isinstance(body, dict) else "",
        source=body.get("source", "manual") if isinstance(body, dict) else "manual",
        asset_class=body.get("asset_class", "models") if isinstance(body, dict) else "models",
    )
    return {"promotion": record}


@router.post("/v1/models/governance/promotions/{promotion_id}/{action}")
async def transition_model_governance_promotion(promotion_id: str, action: str, request: Request):
    from ..promotion_control import transition_promotion_candidate

    if action not in {"advance", "hold", "rollback"}:
        return JSONResponse(status_code=400, content={"error": f"Unsupported action '{action}'"})

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    record = await transition_promotion_candidate(
        promotion_id,
        action=action,
        actor=body.get("actor", "operator") if isinstance(body, dict) else "operator",
        reason=body.get("reason", "") if isinstance(body, dict) else "",
    )
    if record is None:
        return JSONResponse(status_code=404, content={"error": f"Promotion '{promotion_id}' not found"})
    return {"promotion": record}


@router.get("/v1/models/governance/retirements")
async def model_governance_retirements(limit: int = 12):
    from ..retirement_control import build_retirement_controls_snapshot

    return await build_retirement_controls_snapshot(limit=limit)


@router.post("/v1/models/governance/retirements")
async def stage_model_governance_retirement(request: Request):
    from ..retirement_control import stage_retirement_candidate

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    asset_class = body.get("asset_class", "") if isinstance(body, dict) else ""
    asset_id = body.get("asset_id", "") if isinstance(body, dict) else ""
    label = body.get("label", asset_id) if isinstance(body, dict) else asset_id
    if not asset_class or not asset_id:
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'asset_class' and 'asset_id' are required"},
        )

    record = await stage_retirement_candidate(
        asset_class=asset_class,
        asset_id=asset_id,
        label=label,
        target_stage=body.get("target_stage", "retired_reference_only")
        if isinstance(body, dict)
        else "retired_reference_only",
        actor=body.get("actor", "operator") if isinstance(body, dict) else "operator",
        reason=body.get("reason", "") if isinstance(body, dict) else "",
        source=body.get("source", "manual") if isinstance(body, dict) else "manual",
    )
    return {"retirement": record}


@router.post("/v1/models/governance/retirements/{retirement_id}/{action}")
async def transition_model_governance_retirement(retirement_id: str, action: str, request: Request):
    from ..retirement_control import transition_retirement_candidate

    if action not in {"advance", "hold", "rollback"}:
        return JSONResponse(status_code=400, content={"error": f"Unsupported action '{action}'"})

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    record = await transition_retirement_candidate(
        retirement_id,
        action=action,
        actor=body.get("actor", "operator") if isinstance(body, dict) else "operator",
        reason=body.get("reason", "") if isinstance(body, dict) else "",
    )
    if record is None:
        return JSONResponse(status_code=404, content={"error": f"Retirement '{retirement_id}' not found"})
    return {"retirement": record}


@router.get("/v1/models/proving-ground")
async def model_proving_ground(limit: int = 12):
    from ..proving_ground import build_proving_ground_snapshot

    return await build_proving_ground_snapshot(limit=limit)


@router.post("/v1/models/proving-ground/run")
async def run_model_proving_ground(request: Request):
    from ..proving_ground import run_proving_ground

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    limit = int(body.get("limit", 12)) if isinstance(body, dict) else 12
    return await run_proving_ground(limit=limit)
