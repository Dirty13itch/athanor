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
from .input_guard import sanitize_input, check_output, REFUSAL_RESPONSE, OUTPUT_REDACTED_RESPONSE


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .agents import _init_agents
    from .activity import ensure_collections
    from .workspace import start_competition, stop_competition, register_agent
    from .tasks import start_task_worker, stop_task_worker
    from .scheduler import start_scheduler, stop_scheduler

    _init_agents()
    ensure_collections()

    # Initialize cognitive architecture (Phase 2)
    from .cst import get_cst
    from .specialist import get_specialists

    await get_cst()  # Load CST from Redis (or create fresh)
    get_specialists()  # Initialize specialist registry

    try:
        await start_competition()
        print("[lifespan] GWT competition started", flush=True)
    except Exception as e:
        print(f"[lifespan] GWT competition FAILED: {e}", flush=True)
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
    "data-curator": {
        "description": "Personal data librarian — discovers, parses, analyzes, and indexes files from all sources into searchable Qdrant collection.",
        "tools": [
            "scan_directory", "parse_document", "analyze_content", "index_document",
            "search_personal", "get_scan_status", "sync_gdrive",
        ],
        "type": "proactive",
        "schedule": "every 6 hours",
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


# --- Phase 3: Subscriptions & Endorsement ---


@app.get("/v1/workspace/subscriptions")
async def get_workspace_subscriptions():
    """Get all agent subscriptions for workspace broadcasts."""
    from .workspace import get_subscriptions

    subs = await get_subscriptions()
    return {
        "subscriptions": {k: v.to_dict() for k, v in subs.items()},
        "count": len(subs),
    }


@app.post("/v1/workspace/subscriptions")
async def update_workspace_subscription(request: Request):
    """Create or update an agent's workspace subscription.

    Body: {"agent_name": "media-agent", "keywords": ["movie", "show"],
           "source_filters": ["event:plex"], "threshold": 0.3,
           "react_prompt_template": "Handle: '{content}' from {source_agent}"}
    """
    from .workspace import AgentSubscription, save_subscription

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


@app.post("/v1/workspace/{item_id}/endorse")
async def endorse_workspace_item(item_id: str, request: Request):
    """Endorse a workspace item (coalition building).

    Body: {"agent_name": "home-agent"}
    An agent endorses an item to boost its salience. Multiple agents
    endorsing the same item creates a coalition.
    """
    from .workspace import endorse_item

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


# --- Prometheus Alerts ---


@app.get("/v1/alerts")
async def get_alerts():
    """Get currently firing Prometheus alerts and recent history."""
    from .alerts import get_active_alerts, get_alert_history

    active = await get_active_alerts()
    history = await get_alert_history(limit=20)
    return {**active, "history": history}


@app.post("/v1/alerts/check")
async def trigger_alert_check():
    """Manually trigger a Prometheus alert check (normally every 5 min)."""
    from .alerts import check_prometheus_alerts

    return await check_prometheus_alerts()


# --- Pattern Detection ---


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


# --- Convention Library ---


@app.get("/v1/conventions")
async def get_conventions(status: str = "confirmed", agent: str = ""):
    """Get conventions filtered by status (confirmed/proposed/rejected) and optionally by agent."""
    from .conventions import get_conventions as _get_conventions

    conventions = await _get_conventions(status=status, agent=agent or None)
    return {
        "conventions": [c.to_dict() for c in conventions],
        "count": len(conventions),
        "status": status,
    }


@app.post("/v1/conventions")
async def propose_convention_endpoint(request: Request):
    """Propose a new convention manually.

    Body: {"type": "behavior", "agent": "coding-agent", "description": "...", "rule": "..."}
    """
    from .conventions import propose_convention

    body = await request.json()
    conv_type = body.get("type", "behavior")
    agent = body.get("agent", "global")
    description = body.get("description", "")
    rule = body.get("rule", "")
    source = body.get("source", "manual")

    if not description or not rule:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'description' and 'rule' are required"},
        )

    conv = await propose_convention(
        convention_type=conv_type,
        agent=agent,
        description=description,
        rule=rule,
        source=source,
    )
    return {"status": conv.status, "convention": conv.to_dict()}


@app.post("/v1/conventions/{convention_id}/confirm")
async def confirm_convention_endpoint(convention_id: str):
    """Confirm a proposed convention — activates it for context injection."""
    from .conventions import confirm_convention

    conv = await confirm_convention(convention_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    return {"status": "confirmed", "convention": conv.to_dict()}


@app.post("/v1/conventions/{convention_id}/reject")
async def reject_convention_endpoint(convention_id: str):
    """Reject a proposed convention — archived, never re-proposed."""
    from .conventions import reject_convention

    conv = await reject_convention(convention_id)
    if not conv:
        return JSONResponse(status_code=404, content={"error": "Convention not found in proposed"})
    return {"status": "rejected", "convention": conv.to_dict()}


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


@app.post("/v1/tasks/{task_id}/approve")
async def approve_task_endpoint(task_id: str):
    """Approve a pending_approval task (high-impact agents require morning approval)."""
    from .tasks import approve_task

    if await approve_task(task_id):
        return {"approved": True, "task_id": task_id}
    return JSONResponse(
        status_code=404,
        content={"error": f"Task '{task_id}' not found or not pending approval"},
    )


# --- Work Planner ---


@app.get("/v1/workplan")
async def get_workplan():
    """Get the current work plan and queue status."""
    from .workplanner import get_current_plan, get_plan_history, should_refill

    plan = await get_current_plan()
    history = await get_plan_history(limit=5)
    needs_refill = await should_refill()

    return {
        "current_plan": plan,
        "history": history,
        "needs_refill": needs_refill,
    }


@app.post("/v1/workplan/generate")
async def trigger_workplan(request: Request):
    """Manually trigger work plan generation.

    Body: {"focus": "eoq"} or {} for general planning.
    """
    from .workplanner import generate_work_plan

    body = await request.json()
    focus = body.get("focus", "")

    plan = await generate_work_plan(focus=focus)
    return plan


@app.get("/v1/projects")
async def get_projects():
    """Get all project definitions used by the work planner."""
    from .workplanner import get_project_definitions

    projects = get_project_definitions()
    return {
        "projects": {
            pid: {
                "name": p["name"],
                "description": p["description"],
                "status": p["status"],
                "agents": p["agents"],
                "needs_count": len(p["needs"]),
                "constraints": p["constraints"],
            }
            for pid, p in projects.items()
        },
        "count": len(projects),
    }


@app.get("/v1/projects/{project_id}")
async def get_project_detail(project_id: str):
    """Get detailed project definition including all needs."""
    from .workplanner import get_project

    project = get_project(project_id)
    if not project:
        return JSONResponse(
            status_code=404,
            content={"error": f"Project '{project_id}' not found"},
        )
    return {"project": project}


@app.post("/v1/workplan/redirect")
async def redirect_workplan(request: Request):
    """Steer the work planner with a preference or focus direction.

    Stores the preference in Qdrant and triggers a new plan generation
    with the given focus. This is how the human stays in the loop.

    Body: {"direction": "focus more on EoBQ character art, less infrastructure"}
    """
    from .activity import store_preference
    from .workplanner import generate_work_plan

    body = await request.json()
    direction = body.get("direction", "")

    if not direction:
        return JSONResponse(status_code=400, content={"error": "direction is required"})

    # Store as a durable preference so future plans also see it
    await store_preference(
        agent="global",
        signal_type="work_direction",
        content=direction,
        category="work_planning",
    )

    # Fire-and-forget plan generation — returns immediately so the UI doesn't hang
    import asyncio
    asyncio.create_task(generate_work_plan(focus=direction))
    return {"status": "redirected", "direction": direction, "message": "Preference saved, plan generating in background"}


@app.get("/v1/outputs")
async def list_outputs():
    """List files produced by agent tasks in the output directory."""
    import os

    output_dir = "/output"
    files = []

    for root, dirs, filenames in os.walk(output_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in filenames:
            if fname.startswith("."):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, output_dir)
            try:
                stat = os.stat(full_path)
                files.append({
                    "path": rel_path,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except OSError:
                continue

    files.sort(key=lambda f: f["modified"], reverse=True)
    return {"outputs": files, "count": len(files)}


@app.get("/v1/outputs/{path:path}")
async def read_output(path: str):
    """Read the contents of a specific output file."""
    import os

    full_path = os.path.join("/output", path)

    # Security: prevent path traversal
    real_path = os.path.realpath(full_path)
    if not real_path.startswith("/output/"):
        return JSONResponse(status_code=403, content={"error": "Path traversal blocked"})

    if not os.path.isfile(real_path):
        return JSONResponse(status_code=404, content={"error": f"File not found: {path}"})

    try:
        stat = os.stat(real_path)
        # For binary files (images, etc.), return metadata only
        _, ext = os.path.splitext(path)
        if ext.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"):
            return {
                "path": path,
                "type": "binary",
                "size_bytes": stat.st_size,
                "extension": ext,
                "modified": stat.st_mtime,
            }
        # For text files, return content
        with open(real_path, encoding="utf-8", errors="replace") as f:
            content = f.read(50000)  # Cap at 50KB
        return {
            "path": path,
            "type": "text",
            "content": content,
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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

    # Record preference learning outcome
    from .preferences import record_outcome as record_pref_outcome
    from .router import classify_request
    pref_feedback = "positive" if feedback_type == "thumbs_up" else "negative"
    task_type = classify_request(message_content, agent).task_type.value
    model = body.get("model", "reasoning")  # Default to reasoning if not specified
    asyncio.create_task(record_pref_outcome(
        model=model, task_type=task_type, feedback=pref_feedback,
    ))

    # Log feedback event for pattern detection
    from .activity import log_event
    asyncio.create_task(log_event(
        event_type="feedback_received",
        agent=agent,
        description=f"{feedback_type}: {message_content[:200]}",
        data={"feedback_type": feedback_type},
    ))

    # Immediate trust regression on negative feedback
    if feedback_type == "thumbs_down":
        from .escalation import get_all_adjustments, set_autonomy_adjustment
        current = await get_all_adjustments()
        key = f"{agent}:routine"
        current_adj = current.get(key, 0.0)
        asyncio.create_task(set_autonomy_adjustment(agent, "routine", current_adj + 0.03))

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


@app.get("/v1/autonomy")
async def get_autonomy_adjustments():
    """Get current autonomy threshold adjustments per agent.

    Positive = less autonomy (higher thresholds).
    Negative = more autonomy (lower thresholds).
    """
    from .escalation import get_all_adjustments

    adjustments = await get_all_adjustments()
    return {"adjustments": adjustments, "max_adjustment": 0.15}


@app.post("/v1/autonomy/reset")
async def reset_autonomy(request: Request):
    """Reset autonomy adjustments for an agent (or all agents).

    Body: {"agent": "media-agent"} or {} for all.
    """
    from .workspace import get_redis
    from .escalation import AUTONOMY_ADJUSTMENTS_KEY, refresh_adjustment_cache

    body = await request.json()
    agent = body.get("agent", "")

    r = await get_redis()
    if agent:
        # Remove all adjustments for this agent
        all_keys = await r.hkeys(AUTONOMY_ADJUSTMENTS_KEY)
        removed = 0
        for k in all_keys:
            key = k.decode() if isinstance(k, bytes) else k
            if key.startswith(f"{agent}:"):
                await r.hdel(AUTONOMY_ADJUSTMENTS_KEY, key)
                removed += 1
        await refresh_adjustment_cache()
        return {"status": "reset", "agent": agent, "removed": removed}
    else:
        await r.delete(AUTONOMY_ADJUSTMENTS_KEY)
        await refresh_adjustment_cache()
        return {"status": "reset", "agent": "all"}


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


# --- Routing ---


@app.post("/v1/routing/classify")
async def classify_route(request: Request):
    """Classify a prompt without invoking an agent. Diagnostic endpoint.

    Body: {"prompt": "Hello!", "agent": "general-assistant"}
    """
    from .router import classify_request

    body = await request.json()
    prompt = body.get("prompt", "")
    agent_name = body.get("agent", "")
    conversation_length = body.get("conversation_length", 0)

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "prompt is required"})

    routing = classify_request(prompt, agent_name, conversation_length)
    return routing.to_dict()


# --- Cognitive State ---


@app.get("/v1/cognitive/cst")
async def get_cst_state():
    """Get current Continuous State Tensor state."""
    from .cst import get_cst

    cst = await get_cst()
    return cst.to_dict()


@app.get("/v1/cognitive/specialists")
async def get_specialist_state():
    """Get specialist registry with inhibition and competition stats."""
    from .specialist import get_specialists

    specialists = get_specialists()
    return {
        name: s.to_dict()
        for name, s in specialists.items()
    }


# --- Inference-Aware Scheduling ---


@app.get("/v1/scheduling/status")
async def scheduling_status():
    """Get current inference load and agent scheduling state."""
    from .scheduling import get_scheduling_status

    return await get_scheduling_status()


# --- Preference Learning ---


@app.get("/v1/preferences/models")
async def get_model_preferences():
    """Get all learned model preferences, grouped by task type."""
    from .preferences import get_all_preferences

    return await get_all_preferences()


# --- Quality Cascade / Model Routing ---

from .routing import create_routing_router

app.include_router(create_routing_router())

# --- Self-Diagnosis Engine ---

from .diagnosis import create_diagnosis_router

app.include_router(create_diagnosis_router())

# --- Semantic Cache ---

from .semantic_cache import create_cache_router

app.include_router(create_cache_router())

# --- Self-Improvement Engine ---

from .self_improvement import create_improvement_router

app.include_router(create_improvement_router())

# --- Circuit Breakers ---

from .circuit_breaker import create_circuit_breaker_router

app.include_router(create_circuit_breaker_router())

# --- Preference Learning ---

from .preference_learning import create_preference_router

app.include_router(create_preference_router())


# --- Research Jobs ---


@app.post("/v1/research/jobs")
async def create_research_job(request: Request):
    """Create a new autonomous research job.

    Body: {"topic": "latest vLLM optimizations", "description": "...",
           "sources": ["web_search", "knowledge_base"],
           "schedule_hours": 0, "max_duration_minutes": 60}
    """
    from .research_jobs import create_job

    body = await request.json()
    topic = body.get("topic", "")
    if not topic:
        return JSONResponse(status_code=400, content={"error": "topic is required"})

    job = await create_job(
        topic=topic,
        description=body.get("description", ""),
        sources=body.get("sources"),
        schedule_hours=body.get("schedule_hours", 0),
        max_duration_minutes=body.get("max_duration_minutes", 60),
    )
    return job.to_dict()


@app.get("/v1/research/jobs")
async def list_research_jobs(status: str = ""):
    """List all research jobs, optionally filtered by status."""
    from .research_jobs import list_jobs

    return await list_jobs(status=status)


@app.post("/v1/research/jobs/{job_id}/execute")
async def execute_research_job(job_id: str):
    """Execute a research job immediately."""
    from .research_jobs import execute_job

    result = await execute_job(job_id)
    if "error" in result:
        return JSONResponse(status_code=404, content=result)
    return result


@app.delete("/v1/research/jobs/{job_id}")
async def delete_research_job(job_id: str):
    """Delete a research job."""
    from .research_jobs import delete_job

    if await delete_job(job_id):
        return {"status": "deleted", "job_id": job_id}
    return JSONResponse(status_code=404, content={"error": f"Job {job_id} not found"})


# --- Memory Consolidation ---


@app.post("/v1/consolidate")
async def run_consolidation_endpoint():
    """Run memory consolidation pipeline on demand.

    Purges old entries from activity, conversations, implicit_feedback,
    and events collections based on retention policies.
    """
    from .consolidation import run_consolidation

    results = await run_consolidation()
    return results


@app.get("/v1/consolidate/stats")
async def consolidation_stats():
    """Get current point counts for all consolidation-tracked collections."""
    from .consolidation import get_collection_stats

    return await get_collection_stats()


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
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    # Extract user input summary for activity logging
    user_input = messages[-1].get("content", "")[:500] if messages else ""

    # --- Input guard: scan for prompt injection / exfiltration ---
    cleaned_input, input_risk_score, input_warnings = sanitize_input(user_input)
    if input_risk_score > 0.7:
        return JSONResponse(
            status_code=400,
            content={
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": REFUSAL_RESPONSE},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "blocked": True,
            },
            headers={"X-Input-Guard-Score": f"{input_risk_score:.2f}"},
        )
    # Use cleaned input (invisible chars stripped) for downstream processing
    if cleaned_input != user_input:
        user_input = cleaned_input
        if messages:
            messages[-1]["content"] = cleaned_input
            # Rebuild langchain messages with cleaned content
            lc_messages = _convert_messages(messages)

    # --- Tiered routing classification ---
    from .router import classify_request, apply_preference_override

    routing = classify_request(
        prompt=user_input,
        agent_name=model_name,
        conversation_length=len(messages),
    )

    # Apply learned preference override (may change model)
    routing = await apply_preference_override(routing)

    # Context injection — enrich with preferences, activity, knowledge
    context_str = ""
    if not body.get("skip_context", False):
        from .context import enrich_context

        try:
            context_str = await enrich_context(model_name, user_input) or ""
        except Exception:
            pass  # Never let context injection block a request

    if context_str:
        if routing.tier_config.use_agent:
            # Agent graph has its own system prompt — inject context into the
            # last HumanMessage to avoid multiple system messages (vLLM rejects them)
            for i in range(len(lc_messages) - 1, -1, -1):
                if isinstance(lc_messages[i], HumanMessage):
                    lc_messages[i] = HumanMessage(
                        content=f"[Context]\n{context_str}\n[/Context]\n\n{lc_messages[i].content}"
                    )
                    break
        else:
            # Reactive path — direct LLM call, system message is safe
            lc_messages.insert(0, SystemMessage(content=context_str))

    # --- REACTIVE fast path: bypass agent graph for simple queries ---
    if not routing.tier_config.use_agent and not stream:
        from .semantic_cache import get_semantic_cache
        from .circuit_breaker import get_circuit_breakers, CircuitOpenError

        # Semantic cache check (reactive queries only — agent graph is too stateful)
        cache_hit = False
        cached_response = None
        if not body.get("skip_cache", False):
            try:
                cache = get_semantic_cache()
                cached = await cache.lookup(user_input, routing.tier_config.model)
                if cached:
                    cached_response, _score = cached
                    cache_hit = True
            except Exception:
                pass  # Cache failures never block requests

        start_ms = int(time.time() * 1000)

        if cache_hit:
            content = cached_response
        else:
            # Circuit-breaker-protected LLM call
            from langchain_openai import ChatOpenAI

            breakers = get_circuit_breakers()

            async def _invoke_llm():
                fast_llm = ChatOpenAI(
                    base_url=settings.llm_base_url,
                    api_key=settings.llm_api_key,
                    model=routing.tier_config.model,
                    temperature=routing.tier_config.temperature,
                    max_tokens=routing.tier_config.max_tokens,
                    streaming=False,
                    extra_body={
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                )
                return await fast_llm.ainvoke(lc_messages)

            try:
                result = await breakers.execute_with_breaker(
                    routing.tier_config.model,
                    _invoke_llm,
                )
                content = _strip_think_tags(result.content)
            except CircuitOpenError:
                # All models in this tier are down — try fallback chain
                from .routing import FALLBACK_CHAINS
                fallback_content = None
                for fallback_model in FALLBACK_CHAINS.get(routing.tier_config.model, []):
                    try:
                        async def _invoke_fallback(m=fallback_model):
                            fb_llm = ChatOpenAI(
                                base_url=settings.llm_base_url,
                                api_key=settings.llm_api_key,
                                model=m,
                                temperature=routing.tier_config.temperature,
                                max_tokens=routing.tier_config.max_tokens,
                                streaming=False,
                                extra_body={
                                    "chat_template_kwargs": {"enable_thinking": False},
                                },
                            )
                            return await fb_llm.ainvoke(lc_messages)
                        fb_result = await breakers.execute_with_breaker(
                            fallback_model, _invoke_fallback,
                        )
                        fallback_content = _strip_think_tags(fb_result.content)
                        break
                    except (CircuitOpenError, Exception):
                        continue

                if fallback_content is None:
                    return JSONResponse(
                        status_code=503,
                        content={"error": {"message": "All inference services unavailable", "type": "service_unavailable"}},
                    )
                content = fallback_content

            # Store in semantic cache (fire-and-forget)
            try:
                cache = get_semantic_cache()
                tokens_est = len(user_input) // 4 + len(content) // 4
                asyncio.create_task(cache.store(
                    user_input, content, routing.tier_config.model, tokens_est,
                ))
            except Exception:
                pass

        duration_ms = int(time.time() * 1000) - start_ms

        from .activity import log_activity, log_conversation

        asyncio.create_task(log_activity(
            agent=model_name,
            action_type="chat_reactive" + ("_cached" if cache_hit else ""),
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

        # Record preference outcome + cost (fire-and-forget)
        from .preferences import record_outcome as record_pref_outcome
        from .routing import get_cost_tracker
        input_tokens_est = len(user_input) // 4
        output_tokens_est = len(content) // 4
        asyncio.create_task(record_pref_outcome(
            model=routing.tier_config.model,
            task_type=routing.task_type.value,
            latency_ms=float(duration_ms),
        ))
        get_cost_tracker().record(
            routing.tier_config.model, input_tokens_est, output_tokens_est, float(duration_ms),
        )

        # Output guard: scan for data leakage
        _, output_risk_score, output_warnings = check_output(content)
        if output_risk_score > 0.7:
            content = OUTPUT_REDACTED_RESPONSE

        guard_score = max(input_risk_score, output_risk_score)

        return JSONResponse(
            content={
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
                "usage": {"prompt_tokens": input_tokens_est, "completion_tokens": output_tokens_est, "total_tokens": input_tokens_est + output_tokens_est},
                "routing": routing.to_dict(),
                "cache_hit": cache_hit,
            },
            headers={"X-Input-Guard-Score": f"{guard_score:.2f}"},
        )

    if stream:
        return StreamingResponse(
            _stream_response(agent, lc_messages, config, model_name, user_input, routing, thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Input-Guard-Score": f"{input_risk_score:.2f}",
            },
        )

    start_ms = int(time.time() * 1000)

    # Circuit-breaker-protected agent invocation
    from .circuit_breaker import get_circuit_breakers, CircuitOpenError
    from .diagnosis import get_diagnosis_engine

    breakers = get_circuit_breakers()
    try:
        result = await breakers.execute_with_breaker(
            routing.tier_config.model,
            lambda: agent.ainvoke({"messages": lc_messages}, config=config),
        )
        content = _strip_think_tags(result["messages"][-1].content)
    except CircuitOpenError:
        return JSONResponse(
            status_code=503,
            content={"error": {"message": f"Inference service '{routing.tier_config.model}' unavailable", "type": "service_unavailable"}},
        )
    except Exception as exc:
        # Record failure in diagnosis engine (fire-and-forget)
        try:
            diag = get_diagnosis_engine()
            asyncio.create_task(diag.record_failure(
                service=routing.tier_config.model,
                error_message=f"{type(exc).__name__}: {str(exc)[:500]}",
                context={"agent": model_name, "user_input": user_input[:200]},
            ))
        except Exception:
            pass
        raise

    duration_ms = int(time.time() * 1000) - start_ms

    # Log activity + conversation (fire-and-forget)
    from .activity import log_activity, log_conversation

    asyncio.create_task(log_activity(
        agent=model_name,
        action_type=f"chat_{routing.tier.value}",
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

    # Record preference outcome + cost (fire-and-forget)
    from .preferences import record_outcome as record_pref_outcome
    from .routing import get_cost_tracker
    input_tokens_est = len(user_input) // 4
    output_tokens_est = len(content) // 4
    asyncio.create_task(record_pref_outcome(
        model=routing.tier_config.model,
        task_type=routing.task_type.value,
        latency_ms=float(duration_ms),
    ))
    get_cost_tracker().record(
        routing.tier_config.model, input_tokens_est, output_tokens_est, float(duration_ms),
    )

    # Output guard: scan for data leakage
    _, output_risk_score, output_warnings = check_output(content)
    if output_risk_score > 0.7:
        content = OUTPUT_REDACTED_RESPONSE

    guard_score = max(input_risk_score, output_risk_score)

    return JSONResponse(
        content={
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
            "usage": {"prompt_tokens": input_tokens_est, "completion_tokens": output_tokens_est, "total_tokens": input_tokens_est + output_tokens_est},
            "routing": routing.to_dict(),
        },
        headers={"X-Input-Guard-Score": f"{guard_score:.2f}"},
    )


def _convert_messages(messages: list[dict]) -> list:
    # Ensure system messages come first (vLLM rejects mid-conversation system msgs)
    system_msgs = []
    other_msgs = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_msgs.append(SystemMessage(content=content))
        elif role == "user":
            other_msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            other_msgs.append(AIMessage(content=content))
    return system_msgs + other_msgs


async def _stream_response(agent, messages, config, model_name, user_input="", routing=None, thread_id=""):
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
            yield f'event: tool_start\ndata: {json.dumps({"name": name, "run_id": run_id, "toolCallId": run_id or f"tool-{uuid.uuid4().hex[:8]}", "args": args})}\n\n'
            continue

        # Tool call end — emit named SSE event
        if kind == "on_tool_end":
            name = event.get("name", "unknown")
            run_id = event.get("run_id", "")
            output = str(event.get("data", {}).get("output", ""))[:2000]
            yield f'event: tool_end\ndata: {json.dumps({"name": name, "run_id": run_id, "toolCallId": run_id or f"tool-{uuid.uuid4().hex[:8]}", "result": output, "output": output})}\n\n'
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

    tier_label = routing.tier.value if routing else "unknown"
    asyncio.create_task(log_activity(
        agent=model_name,
        action_type=f"chat_{tier_label}",
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
        thread_id=thread_id,
    ))

    # Record cost (fire-and-forget)
    if routing:
        from .routing import get_cost_tracker
        get_cost_tracker().record(
            routing.tier_config.model,
            len(user_input) // 4,
            len(full_response) // 4,
            float(duration_ms),
        )


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


# --- Morning Briefing ---


@app.get("/v1/briefing")
async def get_briefing():
    """Structured morning briefing aggregating cluster health, overnight
    activity, task stats, alerts, and RSS news. Returns JSON with
    prioritized sections and a markdown digest."""
    from .briefing import generate_briefing
    briefing = await generate_briefing()
    return briefing.to_dict()


# --- Learning Metrics (compound learning loop) ---


@app.get("/v1/learning/metrics")
async def learning_metrics():
    """Aggregated metrics showing whether the system is actually learning.

    Collects from: semantic cache, circuit breakers, preference learning,
    trust scores, routing stats, diagnosis patterns, consolidation stats.
    """
    metrics = {}

    # 1. Semantic cache performance
    try:
        from .semantic_cache import get_semantic_cache
        cache = get_semantic_cache()
        stats = await cache.get_stats()
        metrics["cache"] = {
            "total_entries": stats.get("entries", 0),
            "collection": stats.get("collection", "llm_cache"),
            "similarity_threshold": stats.get("similarity_threshold", 0.93),
        }
    except Exception:
        metrics["cache"] = None

    # 2. Circuit breaker health
    try:
        from .circuit_breaker import get_circuit_breakers
        breakers = get_circuit_breakers()
        states = breakers.get_all_stats()
        metrics["circuits"] = {
            "services": len(states),
            "open": sum(1 for s in states.values() if s.get("state") == "open"),
            "half_open": sum(1 for s in states.values() if s.get("state") == "half_open"),
            "closed": sum(1 for s in states.values() if s.get("state") == "closed"),
            "total_failures": sum(s.get("failures", 0) for s in states.values()),
        }
    except Exception:
        metrics["circuits"] = None

    # 3. Preference learning convergence
    try:
        from .preferences import get_all_preferences
        prefs = await get_all_preferences()
        if prefs:
            total_entries = prefs.get("total_entries", 0)
            task_types = prefs.get("task_types", {})
            all_models = [m for models in task_types.values() for m in models]
            total_samples = sum(m.get("interactions", 0) for m in all_models)
            avg_score = sum(m.get("score", 0) for m in all_models) / max(len(all_models), 1) if all_models else 0
            metrics["preferences"] = {
                "model_task_pairs": total_entries,
                "task_types": len(task_types),
                "total_samples": total_samples,
                "avg_score": round(avg_score, 3),
                "converged": sum(1 for m in all_models if m.get("interactions", 0) >= prefs.get("min_samples", 3)),
            }
        else:
            metrics["preferences"] = {"model_task_pairs": 0, "total_samples": 0}
    except Exception:
        metrics["preferences"] = None

    # 4. Trust scores
    try:
        from .goals import compute_trust_scores
        trust = await compute_trust_scores()
        if trust:
            avg_trust = sum(t.get("trust_score", 0) for t in trust.values()) / max(len(trust), 1)
            metrics["trust"] = {
                "agents_tracked": len(trust),
                "avg_trust_score": round(avg_trust, 3),
                "high_trust": sum(1 for t in trust.values() if t.get("trust_score", 0) > 0.7),
                "low_trust": sum(1 for t in trust.values() if t.get("trust_score", 0) < 0.3),
            }
        else:
            metrics["trust"] = {"agents_tracked": 0}
    except Exception:
        metrics["trust"] = None

    # 5. Diagnosis patterns
    try:
        from .diagnosis import get_diagnosis_engine
        diag = get_diagnosis_engine()
        report = diag.analyze(hours=24)
        metrics["diagnosis"] = {
            "recent_failures": report.total_failures,
            "patterns_detected": len(report.top_patterns),
            "recommendations": len(report.recommendations),
            "health_score": report.health_score,
            "trend": report.trend,
        }
    except Exception:
        metrics["diagnosis"] = None

    # 6. Consolidation (memory hygiene)
    try:
        from .consolidation import get_collection_stats
        cstats = await get_collection_stats()
        total_points = sum(c.get("count", 0) for c in cstats.values()) if isinstance(cstats, dict) else 0
        metrics["memory"] = {
            "collections": len(cstats) if isinstance(cstats, dict) else 0,
            "total_points": total_points,
        }
    except Exception:
        metrics["memory"] = None

    # 7. Task execution stats
    try:
        from .tasks import get_task_stats
        tstats = await get_task_stats()
        metrics["tasks"] = {
            "total": tstats.get("total", 0),
            "completed": tstats.get("by_status", {}).get("completed", 0),
            "failed": tstats.get("by_status", {}).get("failed", 0),
            "success_rate": round(
                tstats.get("by_status", {}).get("completed", 0) /
                max(tstats.get("total", 1), 1), 3
            ),
        }
    except Exception:
        metrics["tasks"] = None

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "summary": _compute_learning_summary(metrics),
    }


def _compute_learning_summary(metrics: dict) -> dict:
    """Compute a high-level learning health score from aggregated metrics."""
    scores = []
    signals = []

    # Cache: higher hit rate = more learning
    if metrics.get("cache") and metrics["cache"].get("total_entries", 0) > 0:
        hit_rate = metrics["cache"].get("hit_rate", 0)
        scores.append(min(hit_rate * 2, 1.0))  # 50% hit rate = perfect score
        if hit_rate > 0.1:
            signals.append(f"Cache hit rate {hit_rate:.0%}")

    # Preferences: more converged pairs = more learning
    if metrics.get("preferences") and metrics["preferences"].get("model_task_pairs", 0) > 0:
        convergence = metrics["preferences"]["converged"] / max(metrics["preferences"]["model_task_pairs"], 1)
        scores.append(convergence)
        if convergence > 0.5:
            signals.append(f"{metrics['preferences']['converged']} preference pairs converged")

    # Trust: high average = system is reliable
    if metrics.get("trust") and metrics["trust"].get("agents_tracked", 0) > 0:
        avg_trust = metrics["trust"].get("avg_trust_score", 0)
        scores.append(avg_trust)
        if avg_trust > 0.6:
            signals.append(f"Avg trust score {avg_trust:.2f}")

    # Tasks: success rate
    if metrics.get("tasks") and metrics["tasks"].get("total", 0) > 0:
        sr = metrics["tasks"].get("success_rate", 0)
        scores.append(sr)
        if sr > 0.8:
            signals.append(f"Task success rate {sr:.0%}")

    # Diagnosis: fewer failures = healthier
    if metrics.get("diagnosis"):
        failures = metrics["diagnosis"].get("recent_failures", 0)
        failure_score = max(1.0 - (failures / 50), 0)  # 50+ failures = 0
        scores.append(failure_score)

    overall = round(sum(scores) / max(len(scores), 1), 3) if scores else 0.0
    return {
        "overall_health": overall,
        "data_points": len(scores),
        "positive_signals": signals,
        "assessment": (
            "thriving" if overall > 0.8 else
            "healthy" if overall > 0.6 else
            "developing" if overall > 0.3 else
            "cold_start"
        ),
    }


@app.get("/v1/metrics/agents")
async def agent_metrics():
    """Per-agent performance metrics for dashboard display."""
    from .agents import get_agent_info
    from .routing import get_cost_tracker

    agents_info = get_agent_info()
    cost = get_cost_tracker().summary()
    agent_ids = [a["id"] for a in agents_info]

    # Get activity counts per agent (uses agent ID, e.g., "general-assistant")
    activity_by_agent = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for aid in agent_ids:
                resp = await client.post(
                    f"{settings.qdrant_url}/collections/activity/points/count",
                    json={"filter": {"must": [{"key": "agent", "match": {"value": aid}}]}},
                )
                if resp.status_code == 200:
                    activity_by_agent[aid] = resp.json().get("result", {}).get("count", 0)
    except Exception:
        pass

    # Get trust scores
    trust_by_agent = {}
    try:
        from .goals import compute_trust_scores
        trust = await compute_trust_scores()
        if trust:
            trust_by_agent = {k: v.get("trust_score", 0) for k, v in trust.items()}
    except Exception:
        pass

    # Get task stats per agent
    task_by_agent = {}
    try:
        from .tasks import get_stats
        tstats = await get_stats()
        task_by_agent = tstats.get("by_agent", {})
    except Exception:
        pass

    result = []
    for info in agents_info:
        aid = info["id"]
        result.append({
            "id": aid,
            "name": info["name"],
            "type": info.get("type", "reactive"),
            "status": info.get("status", "unknown"),
            "tools_count": len(info.get("tools", [])),
            "interactions": activity_by_agent.get(aid, 0),
            "trust_score": trust_by_agent.get(aid, None),
            "tasks": task_by_agent.get(aid, {}),
        })

    return {
        "agents": result,
        "cost": cost,
    }


@app.get("/v1/metrics/inference")
async def inference_metrics():
    """Inference layer metrics — prefix cache, KV cache, throughput."""
    metrics = {}

    # Query vLLM Prometheus metrics via Prometheus
    queries = {
        "prefix_cache_hit_rate": 'rate(vllm:prefix_cache_hits_total[5m]) / rate(vllm:prefix_cache_queries_total[5m])',
        "kv_cache_usage": 'vllm:kv_cache_usage_perc',
        "requests_running": 'vllm:num_requests_running',
        "requests_waiting": 'vllm:num_requests_waiting',
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for key, query in queries.items():
                resp = await client.get(
                    f"{settings.prometheus_url}/api/v1/query",
                    params={"query": query},
                )
                if resp.status_code == 200:
                    results = resp.json().get("data", {}).get("result", [])
                    metrics[key] = [
                        {
                            "model": r["metric"].get("model_name", "?"),
                            "instance": r["metric"].get("instance", "?"),
                            "value": float(r["value"][1]) if r["value"][1] != "NaN" else None,
                        }
                        for r in results
                    ]
    except Exception as e:
        metrics["error"] = str(e)

    return metrics


def main():
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
