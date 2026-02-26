import asyncio
import json
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .agents import get_agent, list_agents
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .agents import _init_agents
    from .activity import ensure_collections
    from .workspace import start_competition, stop_competition, register_agent
    from .tasks import start_task_worker, stop_task_worker
    from .scheduler import start_scheduler, stop_scheduler

    _init_agents()
    ensure_collections()
    await start_competition()
    await start_task_worker()
    await start_scheduler()

    # Register all agents in Redis for discovery (Phase 2)
    for name, meta in AGENT_METADATA.items():
        await register_agent(
            name=name,
            capabilities=meta["tools"],
            agent_type=meta["type"],
            subscriptions=meta.get("subscriptions", []),
        )

    yield
    await stop_scheduler()
    await stop_task_worker()
    await stop_competition()


app = FastAPI(title="Athanor Agent Server", version="0.3.0", lifespan=lifespan)


# --- Agent metadata (single source of truth) ---

AGENT_METADATA = {
    "general-assistant": {
        "description": "System monitoring, infrastructure management, task coordination, and codebase inspection.",
        "tools": ["check_services", "get_gpu_metrics", "get_vllm_models", "get_storage_info",
                  "delegate_to_agent", "check_task_status",
                  "read_file", "list_directory", "search_files"],
        "type": "proactive",
    },
    "media-agent": {
        "description": "Media stack control — search/add TV (Sonarr), movies (Radarr), monitor Plex streams (Tautulli).",
        "tools": [
            "search_tv_shows", "get_tv_calendar", "get_tv_queue", "get_tv_library", "add_tv_show",
            "search_movies", "get_movie_calendar", "get_movie_queue", "get_movie_library", "add_movie",
            "get_plex_activity", "get_watch_history", "get_plex_libraries",
        ],
        "type": "proactive",
        "schedule": "every 15 min",
    },
    "home-agent": {
        "description": "Smart home control via Home Assistant — lights, climate, automations, presence.",
        "tools": [
            "get_ha_states", "get_entity_state", "find_entities", "call_ha_service",
            "set_light_brightness", "set_climate_temperature", "list_automations", "trigger_automation",
        ],
        "type": "proactive",
        "schedule": "every 5 min",
        "status_note": None,
    },
    "creative-agent": {
        "description": "Image and video generation via ComfyUI — Flux text-to-image, Wan2.x text-to-video, queue management.",
        "tools": ["generate_image", "generate_video", "check_queue", "get_generation_history", "get_comfyui_status"],
        "type": "reactive",
    },
    "research-agent": {
        "description": "Web research and information synthesis — citations, fact-checking, knowledge search, graph queries.",
        "tools": ["web_search", "fetch_page", "search_knowledge", "query_infrastructure"],
        "type": "reactive",
    },
    "knowledge-agent": {
        "description": "Project librarian — search docs, ADRs, research notes, infrastructure graph, find related knowledge.",
        "tools": ["search_knowledge", "list_documents", "query_knowledge_graph", "find_related_docs", "get_knowledge_stats"],
        "type": "reactive",
    },
    "coding-agent": {
        "description": "Autonomous coding engine — generates, reviews, writes files, runs tests, iterates.",
        "tools": ["generate_code", "review_code", "explain_code", "transform_code",
                  "read_file", "write_file", "list_directory", "search_files", "run_command"],
        "type": "proactive",
    },
    "stash-agent": {
        "description": "Adult content library management — search, browse, organize, tag, and manage via Stash.",
        "tools": [
            "get_stash_stats", "search_scenes", "get_scene_details", "search_performers",
            "list_tags", "find_duplicates", "scan_library", "auto_tag", "generate_content",
            "update_scene_rating", "mark_scene_organized", "get_recent_scenes",
        ],
        "type": "reactive",
    },
}


# --- Health & Models ---


@app.get("/health")
async def health():
    return {"status": "ok", "agents": list_agents()}


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "athanor",
            }
            for name in list_agents()
        ],
    }


# --- Agent metadata endpoint ---


@app.get("/v1/agents")
async def agents_metadata():
    active = list_agents()
    agents = []
    for name, meta in AGENT_METADATA.items():
        agents.append({
            "name": name,
            "description": meta["description"],
            "tools": meta["tools"],
            "type": meta["type"],
            "schedule": meta.get("schedule"),
            "status": "online" if name in active else "planned",
            "status_note": meta.get("status_note"),
        })
    return {"agents": agents}


# --- Media status endpoint ---


@app.get("/v1/status/media")
async def media_status():
    from .tools.media import _sonarr_get, _radarr_get, _tautulli_get

    async def plex():
        data = await asyncio.to_thread(_tautulli_get, "get_activity")
        return data.get("response", {}).get("data", {})

    async def sonarr_queue():
        data = await asyncio.to_thread(_sonarr_get, "/queue", {"pageSize": 20})
        return data.get("records", [])

    async def radarr_queue():
        data = await asyncio.to_thread(_radarr_get, "/queue", {"pageSize": 20})
        return data.get("records", [])

    async def tv_calendar():
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        return await asyncio.to_thread(_sonarr_get, "/calendar", {"start": start, "end": end})

    async def movie_calendar():
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return await asyncio.to_thread(_radarr_get, "/calendar", {"start": start, "end": end})

    async def tv_library():
        series = await asyncio.to_thread(_sonarr_get, "/series")
        return {
            "total": len(series),
            "monitored": sum(1 for s in series if s.get("monitored")),
            "episodes": sum(s.get("statistics", {}).get("episodeFileCount", 0) for s in series),
            "size_gb": round(sum(s.get("statistics", {}).get("sizeOnDisk", 0) for s in series) / (1024**3), 1),
        }

    async def movie_library():
        movies = await asyncio.to_thread(_radarr_get, "/movie")
        return {
            "total": len(movies),
            "monitored": sum(1 for m in movies if m.get("monitored")),
            "has_file": sum(1 for m in movies if m.get("hasFile")),
            "size_gb": round(sum(m.get("sizeOnDisk", 0) for m in movies) / (1024**3), 1),
        }

    async def watch_history():
        data = await asyncio.to_thread(_tautulli_get, "get_history", {"length": "10"})
        return data.get("response", {}).get("data", {}).get("data", [])

    results = await asyncio.gather(
        plex(), sonarr_queue(), radarr_queue(), tv_calendar(), movie_calendar(),
        tv_library(), movie_library(), watch_history(),
        return_exceptions=True,
    )

    def safe(r, default=None):
        return default if isinstance(r, BaseException) else r

    return {
        "plex_activity": safe(results[0], {}),
        "sonarr_queue": safe(results[1], []),
        "radarr_queue": safe(results[2], []),
        "tv_upcoming": safe(results[3], []),
        "movie_upcoming": safe(results[4], []),
        "tv_library": safe(results[5], {}),
        "movie_library": safe(results[6], {}),
        "watch_history": safe(results[7], []),
    }


# --- Service status endpoint ---


@app.get("/v1/status/services")
async def services_status():
    from .tools.system import SERVICES

    async def check(name: str, info: dict) -> dict:
        try:
            headers = info.get("headers", {})
            async with httpx.AsyncClient() as client:
                resp = await client.get(info["url"], timeout=5, follow_redirects=True, headers=headers)
                return {
                    "name": name,
                    "node": info["node"],
                    "status": "up" if resp.status_code < 400 else "error",
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                }
        except Exception:
            return {"name": name, "node": info["node"], "status": "down", "latency_ms": None}

    results = await asyncio.gather(*[check(n, i) for n, i in SERVICES.items()])
    return {"services": list(results)}


# --- Activity & Preferences ---


@app.get("/v1/activity")
async def get_activity(
    agent: str = "",
    action_type: str = "",
    limit: int = 20,
    since: int = 0,
):
    """Query recent agent activity. Filterable by agent, action type, and time."""
    from .activity import query_activity

    results = await query_activity(
        agent=agent, action_type=action_type, limit=limit, since_unix=since
    )
    return {"activity": results, "count": len(results)}


@app.get("/v1/conversations")
async def get_conversations(
    agent: str = "",
    limit: int = 20,
    since: int = 0,
):
    """Query recent conversations. Filterable by agent and time."""
    from .activity import query_conversations

    results = await query_conversations(agent=agent, limit=limit, since_unix=since)
    return {"conversations": results, "count": len(results)}


@app.get("/v1/preferences")
async def get_preferences(query: str = "", agent: str = "", limit: int = 10):
    """Search stored user preferences by semantic similarity."""
    from .activity import query_preferences

    if not query:
        return {"preferences": [], "count": 0, "note": "Provide ?query= to search"}

    results = await query_preferences(query=query, agent=agent, limit=limit)
    return {"preferences": results, "count": len(results)}


@app.post("/v1/preferences")
async def add_preference(request: Request):
    """Store a new user preference signal.

    Body: {"agent": "media-agent", "signal_type": "remember_this",
           "content": "I prefer 4K quality", "category": "media"}
    """
    from .activity import store_preference

    body = await request.json()
    agent_name = body.get("agent", "global")
    signal_type = body.get("signal_type", "remember_this")
    content = body.get("content", "")
    category = body.get("category", "")
    metadata = body.get("metadata")

    if not content:
        return JSONResponse(
            status_code=400,
            content={"error": "content is required"},
        )

    await store_preference(
        agent=agent_name,
        signal_type=signal_type,
        content=content,
        category=category,
        metadata=metadata,
    )
    return {"status": "stored", "agent": agent_name, "signal_type": signal_type}


# --- Escalation & Notifications ---


@app.get("/v1/notifications")
async def get_notifications(include_resolved: bool = False):
    """Get pending agent actions and notifications."""
    from .escalation import get_pending, get_unread_count

    items = get_pending(include_resolved=include_resolved)
    return {
        "notifications": items,
        "count": len(items),
        "unread": get_unread_count(),
    }


@app.post("/v1/notifications/{action_id}/resolve")
async def resolve_notification(action_id: str, request: Request):
    """Approve or reject a pending agent action.

    Body: {"approved": true} or {"approved": false}
    """
    from .escalation import resolve_action

    body = await request.json()
    approved = body.get("approved", False)

    if resolve_action(action_id, approved):
        return {"status": "resolved", "id": action_id, "approved": approved}
    return JSONResponse(
        status_code=404,
        content={"error": f"Action '{action_id}' not found or already resolved"},
    )


@app.get("/v1/escalation/config")
async def get_escalation_config():
    """Get escalation threshold configuration."""
    from .escalation import get_thresholds_config

    return {"thresholds": get_thresholds_config()}


@app.post("/v1/escalation/evaluate")
async def evaluate_escalation(request: Request):
    """Evaluate an action against escalation thresholds.

    Body: {"agent": "home-agent", "action": "dim lights", "category": "routine", "confidence": 0.7}
    """
    from .escalation import ActionCategory, evaluate

    body = await request.json()
    agent = body.get("agent", "")
    action = body.get("action", "")
    category_str = body.get("category", "read")
    confidence = body.get("confidence", 0.5)

    try:
        category = ActionCategory(category_str)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid category '{category_str}'. Valid: {[c.value for c in ActionCategory]}"},
        )

    tier = evaluate(agent, action, category, confidence)

    # Log escalation events for pattern detection (NOTIFY and ASK only — ACT is normal)
    if tier.value in ("notify", "ask"):
        from .activity import log_event
        import asyncio
        asyncio.create_task(log_event(
            event_type="escalation_triggered",
            agent=agent,
            description=f"{tier.value}: {action[:200]}",
            data={"category": category_str, "confidence": confidence, "tier": tier.value},
        ))

    return {
        "agent": agent,
        "action": action,
        "category": category_str,
        "confidence": confidence,
        "tier": tier.value,
    }


# --- GWT Workspace ---


@app.get("/v1/workspace")
async def get_workspace_items():
    """Get current workspace broadcast — top items by salience."""
    from .workspace import get_broadcast

    items = await get_broadcast()
    return {
        "broadcast": [i.to_dict() for i in items],
        "count": len(items),
    }


@app.post("/v1/workspace")
async def post_workspace_item(request: Request):
    """Post an item to the workspace for competition.

    Body: {"source_agent": "media-agent", "content": "New episode available",
           "priority": "normal", "ttl": 300, "metadata": {}}
    """
    from .workspace import post_item

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


@app.delete("/v1/workspace/{item_id}")
async def delete_workspace_item(item_id: str):
    """Remove an item from the workspace."""
    from .workspace import clear_item

    removed = await clear_item(item_id)
    if removed:
        return {"status": "removed", "id": item_id}
    return JSONResponse(status_code=404, content={"error": f"Item '{item_id}' not found"})


@app.delete("/v1/workspace")
async def clear_workspace_all():
    """Clear all workspace items."""
    from .workspace import clear_workspace

    count = await clear_workspace()
    return {"status": "cleared", "items_removed": count}


@app.get("/v1/workspace/stats")
async def workspace_stats():
    """Get workspace statistics — item counts, utilization, active agents."""
    from .workspace import get_stats

    return await get_stats()


@app.get("/v1/agents/registry")
async def agents_registry():
    """Get all registered agents from Redis (Phase 2 discovery)."""
    from .workspace import get_registered_agents

    agents = await get_registered_agents()
    return {"agents": agents, "count": len(agents)}


# --- Event Ingestion (Phase 2) ---

EVENT_PRIORITY_MAP = {
    "alert": "critical",
    "state_change": "normal",
    "schedule": "low",
    "webhook": "normal",
}


@app.post("/v1/events")
async def ingest_event(request: Request):
    """Ingest an external event and convert it to a workspace item.

    Accepts events from HA automations, cron jobs, webhooks, etc.
    Body: {"source": "home-assistant", "event_type": "state_change",
           "content": "Motion detected in garage", "metadata": {...}}
    """
    from .workspace import post_item

    body = await request.json()
    source = body.get("source", "external")
    event_type = body.get("event_type", "webhook")
    content = body.get("content", "")
    metadata = body.get("metadata", {})
    priority = EVENT_PRIORITY_MAP.get(event_type, "normal")

    if not content:
        return JSONResponse(status_code=400, content={"error": "content is required"})

    metadata["event_type"] = event_type
    metadata["source"] = source

    item = await post_item(
        source_agent=f"event:{source}",
        content=content,
        priority=priority,
        ttl=600,  # Events live longer than agent items
        metadata=metadata,
    )

    return {
        "status": "ingested",
        "item_id": item.id,
        "priority": priority,
        "salience": item.salience,
    }


@app.get("/v1/events/query")
async def query_events_endpoint(
    event_type: str = "",
    agent: str = "",
    limit: int = 50,
    since_unix: int = 0,
):
    """Query structured system events for pattern detection.

    Supports filtering by event_type, agent, and time range.
    Event types: task_completed, task_failed, escalation_triggered,
    feedback_received, trust_change, goal_created, schedule_run.
    """
    from .activity import query_events

    events = await query_events(
        event_type=event_type,
        agent=agent,
        limit=limit,
        since_unix=since_unix,
    )
    return {"events": events, "count": len(events)}


@app.get("/v1/patterns")
async def get_patterns(agent: str = ""):
    """Get the latest pattern detection report.

    Optionally filter patterns relevant to a specific agent.
    """
    from .patterns import get_latest_report, get_agent_patterns

    if agent:
        patterns = await get_agent_patterns(agent)
        return {"agent": agent, "patterns": patterns, "count": len(patterns)}

    report = await get_latest_report()
    if not report:
        return {"patterns": [], "recommendations": [], "message": "No pattern report yet. Runs daily at 5:00 AM."}
    return report


@app.post("/v1/patterns/run")
async def trigger_pattern_detection():
    """Manually trigger pattern detection (normally runs at 5:00 AM)."""
    from .patterns import run_pattern_detection

    report = await run_pattern_detection()
    return report


# --- Task Execution Engine ---


@app.post("/v1/tasks")
async def create_task(request: Request):
    """Submit a task for background autonomous execution.

    Body: {"agent": "research-agent", "prompt": "Research vLLM updates",
           "priority": "normal", "metadata": {}}
    """
    from .tasks import submit_task

    body = await request.json()
    agent = body.get("agent", "")
    prompt = body.get("prompt", "")
    priority = body.get("priority", "normal")
    metadata = body.get("metadata", {})

    if not agent or not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'agent' and 'prompt' are required"},
        )

    try:
        task = await submit_task(
            agent=agent,
            prompt=prompt,
            priority=priority,
            metadata=metadata,
        )
        return {"status": "submitted", "task": task.to_dict()}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/v1/tasks")
async def get_tasks(
    status: str = "",
    agent: str = "",
    limit: int = 50,
):
    """List tasks with optional filters."""
    from .tasks import list_tasks

    tasks = await list_tasks(status=status, agent=agent, limit=limit)
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/v1/tasks/stats")
async def task_stats():
    """Get task execution statistics."""
    from .tasks import get_task_stats

    return await get_task_stats()


@app.get("/v1/tasks/schedules")
async def task_schedules():
    """Get proactive agent schedule status."""
    from .scheduler import get_schedule_status

    return await get_schedule_status()


@app.get("/v1/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """Get detailed task status including execution steps."""
    from .tasks import get_task

    task = await get_task(task_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task '{task_id}' not found"},
        )
    return {"task": task.to_dict()}


@app.post("/v1/tasks/{task_id}/cancel")
async def cancel_task_endpoint(task_id: str):
    """Cancel a pending or running task."""
    from .tasks import cancel_task

    if await cancel_task(task_id):
        return {"status": "cancelled", "task_id": task_id}
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or already completed"},
    )


# --- Feedback & Goals ---


@app.post("/v1/feedback")
async def post_feedback(request: Request):
    """Store feedback (thumbs up/down) on an agent response.

    Body: {"agent": "general-assistant", "feedback_type": "thumbs_up",
           "message_content": "the user message", "response_content": "the agent response"}
    """
    from .goals import store_feedback

    body = await request.json()
    agent = body.get("agent", "general-assistant")
    feedback_type = body.get("feedback_type", "thumbs_up")
    message_content = body.get("message_content", "")
    response_content = body.get("response_content", "")

    if feedback_type not in ("thumbs_up", "thumbs_down"):
        return JSONResponse(
            status_code=400,
            content={"error": "feedback_type must be 'thumbs_up' or 'thumbs_down'"},
        )

    result = await store_feedback(
        agent=agent,
        message_content=message_content,
        feedback_type=feedback_type,
        response_content=response_content,
    )

    # Log feedback event for pattern detection
    from .activity import log_event
    asyncio.create_task(log_event(
        event_type="feedback_received",
        agent=agent,
        description=f"{feedback_type}: {message_content[:200]}",
        data={"feedback_type": feedback_type},
    ))

    return result


@app.post("/v1/feedback/implicit")
async def post_implicit_feedback(request: Request):
    """Store batched implicit feedback events from the dashboard client.

    Body: {"session_id": "abc123", "events": [
        {"type": "page_view", "page": "/", "timestamp": 1740000000000},
        {"type": "dwell", "page": "/agents", "duration_ms": 15000, "timestamp": 1740000015000},
        {"type": "tap", "page": "/chat", "agent": "media-agent", "metadata": {"target": "send"}, "timestamp": 1740000020000}
    ]}
    """
    from .activity import store_implicit_events

    body = await request.json()
    session_id = body.get("session_id", "")
    events = body.get("events", [])

    if not events:
        return {"stored": 0}

    if not session_id:
        return JSONResponse(status_code=400, content={"error": "session_id is required"})

    stored = await store_implicit_events(session_id=session_id, events=events)
    return {"stored": stored, "received": len(events)}


@app.get("/v1/notification-budget")
async def get_notification_budget(agent: str = ""):
    """Get notification budget status for agents.

    Optionally filter by agent name. Returns daily limits, used counts, and remaining budget.
    """
    from .goals import check_notification_budget, get_notification_budgets

    if agent:
        budget = await check_notification_budget(agent)
        return {"agent": agent, **budget}
    return {"budgets": await get_notification_budgets()}


@app.get("/v1/goals")
async def get_goals(agent: str = "", active_only: bool = True):
    """List active steering goals."""
    from .goals import list_goals

    goals = await list_goals(agent=agent, active_only=active_only)
    return {"goals": goals, "count": len(goals)}


@app.post("/v1/goals")
async def create_goal_endpoint(request: Request):
    """Create a new steering goal.

    Body: {"text": "Keep GPU utilization above 50%", "agent": "global", "priority": "normal"}
    """
    from .goals import create_goal

    body = await request.json()
    text = body.get("text", "")
    agent = body.get("agent", "global")
    priority = body.get("priority", "normal")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text is required"})

    goal = await create_goal(text=text, agent=agent, priority=priority)
    return {"status": "created", "goal": goal}


@app.delete("/v1/goals/{goal_id}")
async def delete_goal_endpoint(goal_id: str):
    """Delete a steering goal."""
    from .goals import delete_goal

    if await delete_goal(goal_id):
        return {"status": "deleted", "id": goal_id}
    return JSONResponse(status_code=404, content={"error": f"Goal '{goal_id}' not found"})


@app.get("/v1/trust")
async def get_trust_scores():
    """Get trust scores per agent (derived from feedback + escalation history)."""
    from .goals import compute_trust_scores

    return await compute_trust_scores()


# --- Context injection (diagnostic) ---


@app.post("/v1/context/preview")
async def preview_context(request: Request):
    """Preview what context would be injected for a given agent + message.

    Body: {"agent": "media-agent", "message": "Add Breaking Bad"}
    Returns the formatted context string without invoking the agent.
    """
    from .context import enrich_context

    body = await request.json()
    agent_name = body.get("agent", "general-assistant")
    message = body.get("message", "")

    start_ms = int(time.time() * 1000)
    context_str = await enrich_context(agent_name, message)
    duration_ms = int(time.time() * 1000) - start_ms

    return {
        "agent": agent_name,
        "message": message,
        "context": context_str,
        "context_chars": len(context_str),
        "context_tokens_est": len(context_str) // 4,
        "duration_ms": duration_ms,
    }


# --- Chat completions ---


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model", "general-assistant")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    agent = get_agent(model_name)
    if agent is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"Agent '{model_name}' not found. Available: {list_agents()}",
                    "type": "invalid_request_error",
                }
            },
        )

    lc_messages = _convert_messages(messages)
    thread_id = body.get("thread_id", str(uuid.uuid4()))
    config = {"configurable": {"thread_id": thread_id}}

    # Extract user input summary for activity logging
    user_input = messages[-1].get("content", "")[:500] if messages else ""

    # Context injection — enrich with preferences, activity, knowledge
    if not body.get("skip_context", False):
        from .context import enrich_context

        try:
            context_str = await enrich_context(model_name, user_input)
            if context_str:
                lc_messages.insert(0, SystemMessage(content=context_str))
        except Exception:
            pass  # Never let context injection block a request

    if stream:
        return StreamingResponse(
            _stream_response(agent, lc_messages, config, model_name, user_input),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    start_ms = int(time.time() * 1000)
    result = await agent.ainvoke({"messages": lc_messages}, config=config)
    content = _strip_think_tags(result["messages"][-1].content)
    duration_ms = int(time.time() * 1000) - start_ms

    # Log activity + conversation (fire-and-forget)
    from .activity import log_activity, log_conversation

    asyncio.create_task(log_activity(
        agent=model_name,
        action_type="chat",
        input_summary=user_input,
        output_summary=content[:500],
        duration_ms=duration_ms,
    ))
    asyncio.create_task(log_conversation(
        agent=model_name,
        user_message=user_input,
        assistant_response=content,
        duration_ms=duration_ms,
        thread_id=thread_id,
    ))

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _convert_messages(messages: list[dict]) -> list:
    lc_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))
    return lc_messages


async def _stream_response(agent, messages, config, model_name, user_input=""):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    start_ms = int(time.time() * 1000)

    # Send initial role chunk
    yield _sse_chunk(chat_id, created, model_name, {"role": "assistant"})

    in_think = False
    collected_text = []
    tools_used = []
    async for event in agent.astream_events(
        {"messages": messages},
        config=config,
        version="v2",
    ):
        kind = event["event"]

        # Tool call start — emit named SSE event
        if kind == "on_tool_start":
            name = event.get("name", "unknown")
            run_id = event.get("run_id", "")
            args = event.get("data", {}).get("input", {})
            tools_used.append(name)
            yield f'event: tool_start\ndata: {json.dumps({"name": name, "run_id": run_id, "args": args})}\n\n'
            continue

        # Tool call end — emit named SSE event
        if kind == "on_tool_end":
            name = event.get("name", "unknown")
            run_id = event.get("run_id", "")
            output = str(event.get("data", {}).get("output", ""))[:2000]
            yield f'event: tool_end\ndata: {json.dumps({"name": name, "run_id": run_id, "result": output})}\n\n'
            continue

        if kind != "on_chat_model_stream":
            continue

        chunk = event["data"]["chunk"]
        text = chunk.content if hasattr(chunk, "content") else ""
        if not text:
            continue

        # Filter out <think> blocks from Qwen3
        text, in_think = _filter_think_streaming(text, in_think)
        if text:
            collected_text.append(text)
            yield _sse_chunk(chat_id, created, model_name, {"content": text})

    # Finish
    yield _sse_chunk(chat_id, created, model_name, {}, finish_reason="stop")
    yield "data: [DONE]\n\n"

    # Log activity + conversation (fire-and-forget)
    duration_ms = int(time.time() * 1000) - start_ms
    full_response = "".join(collected_text)
    from .activity import log_activity, log_conversation

    asyncio.create_task(log_activity(
        agent=model_name,
        action_type="chat",
        input_summary=user_input,
        output_summary=full_response[:500],
        tools_used=tools_used,
        duration_ms=duration_ms,
    ))
    asyncio.create_task(log_conversation(
        agent=model_name,
        user_message=user_input,
        assistant_response=full_response,
        tools_used=tools_used,
        duration_ms=duration_ms,
    ))


def _sse_chunk(chat_id, created, model, delta, finish_reason=None):
    data = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }
    return f"data: {json.dumps(data)}\n\n"


def _strip_think_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


def _filter_think_streaming(text: str, in_think: bool) -> tuple[str, bool]:
    result = []
    i = 0
    while i < len(text):
        if in_think:
            end = text.find("</think>", i)
            if end == -1:
                break
            in_think = False
            i = end + len("</think>")
            # Skip trailing whitespace
            while i < len(text) and text[i] in (" ", "\n"):
                i += 1
        else:
            start = text.find("<think>", i)
            if start == -1:
                result.append(text[i:])
                break
            result.append(text[i:start])
            in_think = True
            i = start + len("<think>")
    return "".join(result), in_think


def main():
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
