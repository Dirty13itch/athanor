import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agents import get_agent, list_agents
from .config import settings

logger = logging.getLogger(__name__)


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

    # Seed skill library with initial skills if empty
    try:
        from .skill_learning import ensure_initial_skills
        seeded = await ensure_initial_skills()
        if seeded:
            print(f"[lifespan] Skill library seeded with {seeded} initial skills", flush=True)
    except Exception as e:
        print(f"[lifespan] Skill seeding failed: {e}", flush=True)

    # Reload pending escalation actions from Redis (survive container restarts)
    try:
        from .escalation import load_pending_from_redis
        await load_pending_from_redis()
    except Exception as e:
        print(f"[lifespan] Escalation queue reload failed: {e}", flush=True)

    yield
    await stop_scheduler()
    await stop_task_worker()
    await stop_competition()


app = FastAPI(title="Athanor Agent Server", version="0.3.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "tools": ["web_search", "fetch_page", "search_knowledge", "query_infrastructure", "request_execution_lease"],
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
                  "read_file", "write_file", "list_directory", "search_files", "run_command",
                  "request_execution_lease"],
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


# --- Subscription control layer ---


@app.get("/v1/subscriptions/providers")
async def subscription_providers():
    from .subscriptions import get_policy_snapshot

    policy = get_policy_snapshot()
    return {
        "providers": policy["providers"],
        "count": len(policy["providers"]),
        "policy_source": policy["policy_source"],
    }


@app.get("/v1/subscriptions/policy")
async def subscription_policy():
    from .subscriptions import get_policy_snapshot

    return get_policy_snapshot()


@app.get("/v1/subscriptions/leases")
async def subscription_leases(requester: str = "", limit: int = 50):
    from .subscriptions import list_execution_leases

    leases = await list_execution_leases(requester=requester, limit=limit)
    return {"leases": leases, "count": len(leases)}


@app.post("/v1/subscriptions/leases")
async def create_subscription_lease(request: Request):
    from .subscriptions import LeaseRequest, issue_execution_lease

    body = await request.json()
    requester = body.get("requester", "")
    task_class = body.get("task_class", "")
    if not requester or not task_class:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'requester' and 'task_class' are required"},
        )

    lease = await issue_execution_lease(
        LeaseRequest(
            requester=requester,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            priority=body.get("priority", "normal"),
            metadata=body.get("metadata", {}),
        )
    )
    return {"lease": lease.to_dict()}


@app.post("/v1/subscriptions/leases/{lease_id}/outcome")
async def update_subscription_outcome(lease_id: str, request: Request):
    from .subscriptions import record_execution_outcome

    body = await request.json()
    outcome = body.get("outcome", "")
    if not outcome:
        return JSONResponse(status_code=400, content={"error": "'outcome' is required"})

    lease = await record_execution_outcome(
        lease_id=lease_id,
        outcome=outcome,
        throttled=bool(body.get("throttled", False)),
        notes=body.get("notes", ""),
        quality_score=body.get("quality_score"),
        latency_ms=body.get("latency_ms"),
    )
    if lease is None:
        return JSONResponse(status_code=404, content={"error": f"Lease '{lease_id}' not found"})
    return {"lease": lease}


@app.get("/v1/subscriptions/quotas")
async def subscription_quota_summary():
    from .subscriptions import get_quota_summary

    return await get_quota_summary()


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
    from .services import registry

    async def check(svc) -> dict:
        try:
            target = svc.health_url or svc.url()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    target, timeout=5, follow_redirects=True, headers=dict(svc.headers)
                )
                return {
                    "name": svc.name,
                    "node": svc.node,
                    "status": "up" if resp.status_code < 400 else "error",
                    "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                }
        except Exception as e:
            logger.debug("Health check failed for %s: %s", svc.name, e)
            return {"name": svc.name, "node": svc.node, "status": "down", "latency_ms": None}

    results = await asyncio.gather(*[check(svc) for svc in registry.service_checks])
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
    """Get pending agent actions and notifications.

    Merges two sources:
    - escalation.py confidence-gated actions (tier=notify/ask)
    - tasks.py pending_approval tasks (require explicit human approval)
    """
    from .escalation import get_pending, get_unread_count
    from .tasks import list_tasks

    items = get_pending(include_resolved=include_resolved)

    # Merge pending_approval tasks as notifications
    pending_tasks = await list_tasks(status="pending_approval", limit=50)
    for t in pending_tasks:
        meta = t.get("metadata", {})
        category = meta.get("category", "routine")
        prompt = t.get("prompt", "")
        items.append({
            "id": f"task-{t['id']}",
            "tier": "ask",
            "agent": t["agent"],
            "action": prompt[:120],
            "category": category,
            "confidence": 0.0,
            "description": f"Auto-generated task (priority: {t.get('priority', 'normal')}). Approve to queue for execution.",
            "created_at": t.get("created_at", 0),
            "resolved": False,
            "resolution": "",
        })

    return {
        "notifications": items,
        "count": len(items),
        "unread": get_unread_count() + len(pending_tasks),
    }


@app.post("/v1/notifications/{action_id}/resolve")
async def resolve_notification(action_id: str, request: Request):
    """Approve or reject a pending agent action or task.

    Body: {"approved": true} or {"approved": false}

    IDs prefixed with "task-" route to the task approval system.
    All other IDs route to the escalation system.
    """
    body = await request.json()
    approved = body.get("approved", False)

    if action_id.startswith("task-"):
        from .tasks import approve_task, cancel_task
        task_id = action_id[len("task-"):]
        if approved:
            ok = await approve_task(task_id)
        else:
            ok = await cancel_task(task_id)
        if ok:
            return {"status": "resolved", "id": action_id, "approved": approved}
        return JSONResponse(
            status_code=404,
            content={"error": f"Task '{task_id}' not found or not awaiting approval"},
        )

    from .escalation import resolve_action
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
from .routes.workspace import router as workspace_router
app.include_router(workspace_router)

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
from .routes.tasks import router as tasks_router
app.include_router(tasks_router)

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
    """Get canonical project registry summaries for the project platform."""
    from .projects import get_project_summaries

    projects = get_project_summaries()
    return {"projects": projects, "count": len(projects)}


@app.get("/v1/projects/{project_id}")
async def get_project_detail(project_id: str):
    """Get a detailed canonical project definition including needs and operators."""
    from .projects import get_project

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
from .routes.goals import router as goals_router
app.include_router(goals_router)

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

# --- Skill Learning ---
from .routes.skills import router as skills_router
app.include_router(skills_router)

# --- Circuit Breakers ---

from .circuit_breaker import create_circuit_breaker_router

app.include_router(create_circuit_breaker_router())

# --- Preference Learning ---

from .preference_learning import create_preference_router

app.include_router(create_preference_router())


# --- Research Jobs ---
from .routes.research import router as research_router
app.include_router(research_router)

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
from .routes.chat import router as chat_router
app.include_router(chat_router)

# --- Morning Briefing ---


@app.get("/v1/briefing")
async def get_briefing():
    """Structured morning briefing aggregating cluster health, overnight
    activity, task stats, alerts, and RSS news. Returns JSON with
    prioritized sections and a markdown digest."""
    from .briefing import generate_briefing
    briefing = await generate_briefing()
    return briefing.to_dict()


# --- Metrics (learning, agent, inference, context) ---
from .routes.metrics import router as metrics_router
app.include_router(metrics_router)

# --- Emergency Protocols (CONSTITUTION.yaml) ---
from .routes.emergency import router as emergency_router
app.include_router(emergency_router)


def main():
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
