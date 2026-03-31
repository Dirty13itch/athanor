"""Workspace routes - GWT broadcast, subscriptions, endorsement."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from ..operator_contract import (
    build_operator_action,
    emit_operator_audit_event,
    require_operator_action,
)

router = APIRouter(prefix="/v1", tags=["workspace"])


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


@router.get("/workspace")
async def get_workspace_items():
    """Get current workspace broadcast — top items by salience."""
    from ..workspace import get_broadcast

    items = await get_broadcast()
    return {
        "broadcast": [i.to_dict() for i in items],
        "count": len(items),
    }


@router.post("/workspace")
async def post_workspace_item(request: Request):
    """Post an item to the workspace for competition.

    Body: {"source_agent": "media-agent", "content": "New episode available",
           "priority": "normal", "ttl": 300, "metadata": {}}
    """
    from ..workspace import post_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workspace",
        action_class="operator",
        default_reason="Posted workspace item",
    )
    if denial:
        return denial
    source = body.get("source_agent", "")
    content = body.get("content", "")
    priority = body.get("priority", "normal")
    ttl = body.get("ttl", 300)
    metadata = body.get("metadata", {})

    if not content:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workspace",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="content is required",
        )
        return JSONResponse(status_code=400, content={"error": "content is required"})

    item = await post_item(
        source_agent=source, content=content, priority=priority,
        ttl=ttl, metadata=metadata,
    )
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workspace",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Posted workspace item {item.id}",
        target=item.id,
        metadata={"source_agent": source, "priority": priority},
    )
    return {"status": "posted", "item": item.to_dict()}


@router.delete("/workspace/{item_id}")
async def delete_workspace_item(item_id: str, request: Request):
    """Remove an item from the workspace."""
    from ..workspace import clear_item

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/workspace/{item_id}",
        action_class="admin",
        default_reason=f"Removed workspace item {item_id}",
    )
    if denial:
        return denial

    removed = await clear_item(item_id)
    if removed:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workspace/{item_id}",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Removed workspace item {item_id}",
            target=item_id,
        )
        return {"status": "removed", "id": item_id}
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workspace/{item_id}",
        action_class="admin",
        decision="denied",
        status_code=404,
        action=action,
        detail=f"Item {item_id} not found",
        target=item_id,
    )
    return JSONResponse(status_code=404, content={"error": f"Item '{item_id}' not found"})


@router.delete("/workspace")
async def clear_workspace_all(request: Request):
    """Clear all workspace items."""
    from ..workspace import clear_workspace

    _, action, denial = await _load_operator_body(
        request,
        route="/v1/workspace",
        action_class="destructive-admin",
        default_reason="Cleared workspace broadcast",
    )
    if denial:
        return denial

    count = await clear_workspace()
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workspace",
        action_class="destructive-admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail="Cleared workspace broadcast",
        metadata={"items_removed": count},
    )
    return {"status": "cleared", "items_removed": count}


@router.get("/workspace/stats")
async def workspace_stats():
    """Get workspace statistics — item counts, utilization, active agents."""
    from ..workspace import get_stats

    return await get_stats()


@router.get("/agents/registry")
async def agents_registry():
    """Get all registered agents from Redis (Phase 2 discovery)."""
    from ..workspace import get_registered_agents

    agents = await get_registered_agents()
    return {"agents": agents, "count": len(agents)}


# --- Phase 3: Subscriptions & Endorsement ---


@router.get("/workspace/subscriptions")
async def get_workspace_subscriptions():
    """Get all agent subscriptions for workspace broadcasts."""
    from ..workspace import get_subscriptions

    subs = await get_subscriptions()
    return {
        "subscriptions": {k: v.to_dict() for k, v in subs.items()},
        "count": len(subs),
    }


@router.post("/workspace/subscriptions")
async def update_workspace_subscription(request: Request):
    """Create or update an agent's workspace subscription.

    Body: {"agent_name": "media-agent", "keywords": ["movie", "show"],
           "source_filters": ["event:plex"], "threshold": 0.3,
           "react_prompt_template": "Handle: '{content}' from {source_agent}"}
    """
    from ..workspace import AgentSubscription, save_subscription

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workspace/subscriptions",
        action_class="admin",
        default_reason="Updated workspace subscription",
    )
    if denial:
        return denial
    agent_name = body.get("agent_name", "")
    if not agent_name:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workspace/subscriptions",
            action_class="admin",
            decision="denied",
            status_code=400,
            action=action,
            detail="agent_name is required",
        )
        return JSONResponse(status_code=400, content={"error": "agent_name is required"})

    sub = AgentSubscription(
        agent_name=agent_name,
        keywords=body.get("keywords", []),
        source_filters=body.get("source_filters", []),
        threshold=body.get("threshold", 0.3),
        react_prompt_template=body.get("react_prompt_template", ""),
    )
    await save_subscription(sub)
    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workspace/subscriptions",
        action_class="admin",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Updated workspace subscription for {agent_name}",
        target=agent_name,
    )
    return {"status": "saved", "subscription": sub.to_dict()}


@router.post("/workspace/{item_id}/endorse")
async def endorse_workspace_item(item_id: str, request: Request):
    """Endorse a workspace item (coalition building).

    Body: {"agent_name": "home-agent"}
    An agent endorses an item to boost its salience. Multiple agents
    endorsing the same item creates a coalition.
    """
    from ..workspace import endorse_item

    body, action, denial = await _load_operator_body(
        request,
        route="/v1/workspace/{item_id}/endorse",
        action_class="operator",
        default_reason=f"Endorsed workspace item {item_id}",
    )
    if denial:
        return denial
    agent_name = body.get("agent_name", "")
    if not agent_name:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workspace/{item_id}/endorse",
            action_class="operator",
            decision="denied",
            status_code=400,
            action=action,
            detail="agent_name is required",
            target=item_id,
        )
        return JSONResponse(status_code=400, content={"error": "agent_name is required"})

    item = await endorse_item(item_id, agent_name)
    if item is None:
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/workspace/{item_id}/endorse",
            action_class="operator",
            decision="denied",
            status_code=404,
            action=action,
            detail=f"Item {item_id} not found",
            target=item_id,
        )
        return JSONResponse(status_code=404, content={"error": f"Item '{item_id}' not found"})

    await emit_operator_audit_event(
        service="agent-server",
        route="/v1/workspace/{item_id}/endorse",
        action_class="operator",
        decision="accepted",
        status_code=200,
        action=action,
        detail=f"Endorsed workspace item {item_id}",
        target=item_id,
        metadata={"agent_name": agent_name, "coalition_size": len(item.coalition)},
    )
    return {
        "status": "endorsed",
        "item_id": item_id,
        "coalition": item.coalition,
        "salience": item.salience,
    }
