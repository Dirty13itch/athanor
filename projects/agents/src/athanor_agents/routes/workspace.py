"""Workspace routes — GWT broadcast, subscriptions, endorsement."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

router = APIRouter(prefix="/v1", tags=["workspace"])


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

    body = await request.json()
    source = body.get("source_agent", "")
    content = body.get("content", "")
    priority = body.get("priority", "normal")
    ttl = body.get("ttl", 300)
    metadata = body.get("metadata", {})

    if not content:
        return JSONResponse(status_code=400, content={"error": "content is required"})

    item = await post_item(
        source_agent=source, content=content, priority=priority,
        ttl=ttl, metadata=metadata,
    )
    return {"status": "posted", "item": item.to_dict()}


@router.delete("/workspace/{item_id}")
async def delete_workspace_item(item_id: str):
    """Remove an item from the workspace."""
    from ..workspace import clear_item

    removed = await clear_item(item_id)
    if removed:
        return {"status": "removed", "id": item_id}
    return JSONResponse(status_code=404, content={"error": f"Item '{item_id}' not found"})


@router.delete("/workspace")
async def clear_workspace_all():
    """Clear all workspace items."""
    from ..workspace import clear_workspace

    count = await clear_workspace()
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

    body = await request.json()
    agent_name = body.get("agent_name", "")
    if not agent_name:
        return JSONResponse(status_code=400, content={"error": "agent_name is required"})

    sub = AgentSubscription(
        agent_name=agent_name,
        keywords=body.get("keywords", []),
        source_filters=body.get("source_filters", []),
        threshold=body.get("threshold", 0.3),
        react_prompt_template=body.get("react_prompt_template", ""),
    )
    await save_subscription(sub)
    return {"status": "saved", "subscription": sub.to_dict()}


@router.post("/workspace/{item_id}/endorse")
async def endorse_workspace_item(item_id: str, request: Request):
    """Endorse a workspace item (coalition building).

    Body: {"agent_name": "home-agent"}
    An agent endorses an item to boost its salience. Multiple agents
    endorsing the same item creates a coalition.
    """
    from ..workspace import endorse_item

    body = await request.json()
    agent_name = body.get("agent_name", "")
    if not agent_name:
        return JSONResponse(status_code=400, content={"error": "agent_name is required"})

    item = await endorse_item(item_id, agent_name)
    if item is None:
        return JSONResponse(status_code=404, content={"error": f"Item '{item_id}' not found"})

    return {
        "status": "endorsed",
        "item_id": item_id,
        "coalition": item.coalition,
        "salience": item.salience,
    }
