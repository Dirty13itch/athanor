import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .agents import list_agents
from .config import settings

logger = logging.getLogger(__name__)


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
        "description": "Project librarian — search docs, ADRs, research notes, infrastructure graph, intelligence signals, find related knowledge.",
        "tools": ["search_knowledge", "search_signals", "deep_search", "list_documents", "query_knowledge_graph", "find_related_docs", "get_knowledge_stats", "upload_document"],
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .agents import _init_agents
    from .activity import ensure_collections
    from .workspace import start_competition, stop_competition, register_agent
    from .tasks import start_task_worker, stop_task_worker
    from .scheduler import start_scheduler, stop_scheduler

    _init_agents()
    ensure_collections()

    from .cst import get_cst
    from .specialist import get_specialists

    await get_cst()
    get_specialists()

    try:
        await start_competition()
        print("[lifespan] GWT competition started", flush=True)
    except Exception as e:
        print(f"[lifespan] GWT competition FAILED: {e}", flush=True)
    await start_task_worker()
    await start_scheduler()

    for name, meta in AGENT_METADATA.items():
        await register_agent(
            name=name,
            capabilities=meta["tools"],
            agent_type=meta["type"],
            subscriptions=meta.get("subscriptions", []),
        )

    try:
        from .skill_learning import ensure_initial_skills
        seeded = await ensure_initial_skills()
        if seeded:
            print(f"[lifespan] Skill library seeded with {seeded} initial skills", flush=True)
    except Exception as e:
        print(f"[lifespan] Skill seeding failed: {e}", flush=True)

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


# --- Auth middleware ---
# Unauthenticated paths: health (monitoring), metrics (prometheus)
AUTH_EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = settings.api_bearer_token
        if not token:
            # No token configured — auth disabled (backwards compatible)
            return await call_next(request)
        if request.url.path in AUTH_EXEMPT_PATHS:
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        if auth == f"Bearer {token}":
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={"error": {"message": "Invalid or missing bearer token", "type": "authentication_error"}},
        )


app.add_middleware(BearerAuthMiddleware)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Core endpoints (tightly coupled to AGENT_METADATA / app) ---


@app.get("/health")
async def health():
    """Structured health check with dependency probes."""
    import asyncio
    import httpx

    async def _probe(name: str, url: str, timeout: float = 2.0) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                resp = await c.get(url)
                return {"name": name, "status": "up", "latency_ms": int(resp.elapsed.total_seconds() * 1000)}
        except Exception as e:
            return {"name": name, "status": "down", "error": str(e)[:120]}

    deps = await asyncio.gather(
        _probe("redis", f"http://{settings.vault_host}:6379", timeout=1.0),  # TCP only, will fail on HTTP but that's fine
        _probe("qdrant", f"{settings.qdrant_url}/collections"),
        _probe("litellm", f"{settings.litellm_url}/health"),
        _probe("coordinator", f"{settings.coordinator_url}/health"),
        _probe("worker", f"{settings.worker_url}/health"),
        _probe("embedding", f"{settings.embedding_url}/health"),
    )

    # Redis probe: use actual Redis PING instead of HTTP
    try:
        import redis as _redis
        r = _redis.from_url(settings.redis_url, password=settings.redis_password or None, socket_timeout=1.0)
        r.ping()
        deps = list(deps)
        deps[0] = {"name": "redis", "status": "up", "latency_ms": 0}
    except Exception as e:
        deps = list(deps)
        deps[0] = {"name": "redis", "status": "down", "error": str(e)[:120]}

    dep_map = {d["name"]: d for d in deps}
    down = [d["name"] for d in deps if d["status"] == "down"]
    active_agents = list_agents()

    # Core deps: qdrant, redis, litellm. If any core dep is down, status is degraded.
    # If agents can't load, status is unhealthy.
    core_down = [n for n in down if n in ("qdrant", "redis", "litellm")]
    if not active_agents:
        overall = "unhealthy"
    elif core_down:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "agents": active_agents,
        "agent_count": len(active_agents),
        "dependencies": dep_map,
        "issues": down if down else None,
    }


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


# --- Route modules ---

from .routes.subscriptions import router as subscriptions_router
from .routes.notifications import router as notifications_router
from .routes.status import router as status_router
from .routes.activity import router as activity_router
from .routes.events import router as events_router
from .routes.conventions import router as conventions_router
from .routes.planning import router as planning_router
from .routes.diagnostics import router as diagnostics_router
from .routes.workspace import router as workspace_router
from .routes.tasks import router as tasks_router
from .routes.goals import router as goals_router
from .routes.skills import router as skills_router
from .routes.research import router as research_router
from .routes.metrics import router as metrics_router
from .routes.chat import router as chat_router
from .routes.emergency import router as emergency_router
from .routes.workflows import router as workflows_router

app.include_router(subscriptions_router)
app.include_router(notifications_router)
app.include_router(status_router)
app.include_router(activity_router)
app.include_router(events_router)
app.include_router(conventions_router)
app.include_router(planning_router)
app.include_router(diagnostics_router)
app.include_router(workspace_router)
app.include_router(tasks_router)
app.include_router(goals_router)
app.include_router(skills_router)
app.include_router(research_router)
app.include_router(metrics_router)
app.include_router(chat_router)
app.include_router(emergency_router)
app.include_router(workflows_router)

# --- Factory routers (modules that define create_*_router()) ---

from .routing import create_routing_router
from .diagnosis import create_diagnosis_router
from .semantic_cache import create_cache_router
from .self_improvement import create_improvement_router
from .circuit_breaker import create_circuit_breaker_router
from .preference_learning import create_preference_router

app.include_router(create_routing_router())
app.include_router(create_diagnosis_router())
app.include_router(create_cache_router())
app.include_router(create_improvement_router())
app.include_router(create_circuit_breaker_router())
app.include_router(create_preference_router())


def main():
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
