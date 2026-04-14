import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .agent_registry import build_agent_metadata
from .auth import BearerAuthContract
from .agents import list_agents
from .command_hierarchy import build_system_map_snapshot
from .config import settings
from .control_plane_registry import build_control_plane_registry_snapshot
from .domain_registry import build_domain_metadata
from .durable_state import ensure_durable_state_schema, get_durable_state_status
from .launch_governance import build_launch_governance_posture
from .persistence import get_checkpointer_status
from .bootstrap_state import build_bootstrap_runtime_snapshot, ensure_bootstrap_state

# Configure root logger so all athanor_agents.* loggers are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)
SERVICE_STARTED_AT = datetime.now(timezone.utc).isoformat()

AUTH_CONTRACT = BearerAuthContract(
    service_name="agent-server",
    runtime_environment=settings.runtime_environment,
    bearer_token=settings.api_bearer_token,
    token_env_names=("ATHANOR_AGENT_API_TOKEN", "ATHANOR_API_BEARER_TOKEN"),
)


def get_agent_metadata() -> dict[str, dict]:
    return build_agent_metadata()


def _build_health_summary(
    deps: list[dict],
    active_agents: list[str],
    persistence: dict[str, object],
    durable_state: dict[str, object],
    governance: dict[str, object] | None = None,
) -> dict[str, object]:
    dep_map = {d["id"]: d for d in deps}
    down = [d["id"] for d in deps if d["status"] == "down"]
    core_down = [name for name in down if name in ("qdrant", "redis", "litellm")]
    persistence_mode = str(persistence.get("mode") or "unknown")
    persistence_reason = str(persistence.get("reason") or "").strip() or None
    durable_state_mode = str(durable_state.get("mode") or "unknown")
    durable_state_reason = str(durable_state.get("reason") or "").strip() or None
    launch_blockers = [f"dependency:{name}" for name in core_down]
    if not bool(persistence.get("durable")):
        launch_blockers.append(f"persistence:{persistence_mode}")
    if bool(durable_state.get("configured")) and not bool(durable_state.get("schema_ready")):
        launch_blockers.append(f"durable_state:{durable_state_mode}")
    governance_blockers = list((governance or {}).get("launch_blockers") or [])
    governance_issues = list((governance or {}).get("issues") or [])
    launch_blockers.extend(str(item) for item in governance_blockers if str(item).strip())

    if not active_agents or core_down:
        overall = "degraded"
    else:
        overall = "healthy"

    issues = list(down)
    if not bool(persistence.get("durable")):
        issues.append(f"persistence:{persistence_mode}")
    if bool(durable_state.get("configured")) and not bool(durable_state.get("schema_ready")):
        issues.append(f"durable_state:{durable_state_mode}")
    issues.extend(str(item) for item in governance_issues if str(item).strip())

    return {
        "status": overall,
        "last_error": "; ".join(sorted(core_down))
        if core_down
        else (persistence_reason or durable_state_reason or (issues[0] if issues else None)),
        "agents": active_agents,
        "agent_count": len(active_agents),
        "dependency_map": dep_map,
        "issues": issues or None,
        "persistence": persistence,
        "durable_state": durable_state,
        "governance": governance or None,
        "launch_ready": not bool(launch_blockers),
        "launch_blockers": launch_blockers or None,
    }


def _build_launch_governance_posture() -> dict[str, object]:
    return build_launch_governance_posture()


async def _load_governor_runtime() -> bool:
    from .governor import Governor

    try:
        await Governor.get().load()
        return True
    except Exception as exc:
        logger.warning(
            "Governor runtime unavailable during startup; continuing in degraded mode: %s",
            exc,
            exc_info=True,
        )
        return False


async def _probe_redis_dependency(checked_at: str) -> dict[str, object]:
    def _ping() -> dict[str, object]:
        import redis as _redis

        started = time.monotonic()
        client = _redis.from_url(
            settings.redis_url,
            password=settings.redis_password or None,
            socket_timeout=1.0,
        )
        client.ping()
        latency_ms = int((time.monotonic() - started) * 1000)
        return {
            "id": "redis",
            "status": "healthy",
            "required": True,
            "last_checked_at": checked_at,
            "detail": f"latency_ms={latency_ms}",
            "latency_ms": latency_ms,
        }

    try:
        return await asyncio.to_thread(_ping)
    except Exception as e:
        return {
            "id": "redis",
            "status": "down",
            "required": True,
            "last_checked_at": checked_at,
            "detail": str(e)[:120],
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .agents import _init_agents
    from .activity import ensure_collections
    from .workspace import start_competition, stop_competition, register_agent
    from .tasks import start_task_worker, stop_task_worker
    from .scheduler import start_scheduler, stop_scheduler

    AUTH_CONTRACT.validate_startup()
    await ensure_durable_state_schema()
    await ensure_bootstrap_state()
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

    await _load_governor_runtime()

    agent_metadata = get_agent_metadata()
    for name, meta in agent_metadata.items():
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

    try:
        from .core_memory import seed_core_memories
        seeded = await seed_core_memories()
        if seeded:
            print(f"[lifespan] Core memory seeded for {seeded} agents", flush=True)
    except Exception as e:
        print(f"[lifespan] Core memory seeding failed: {e}", flush=True)

    yield
    from .governor import Governor

    await Governor.get().shutdown()
    await stop_scheduler()
    await stop_task_worker()
    await stop_competition()


app = FastAPI(title="Athanor Agent Server", version="0.3.0", lifespan=lifespan)


# --- Auth middleware ---
# Unauthenticated paths: health/liveness (monitoring), metrics (prometheus)
AUTH_EXEMPT_PATHS = {"/health", "/health/livez", "/metrics", "/docs", "/openapi.json"}


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        denial = AUTH_CONTRACT.authorize(request)
        if denial is None:
            return await call_next(request)
        return denial


app.add_middleware(BearerAuthMiddleware)

from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    origin
    for origin in {
        settings.dashboard_url.rstrip("/"),
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    }
    if origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Core endpoints (registry-backed metadata plus app state) ---


@app.get("/health")
async def health():
    """Structured health check with dependency probes."""
    import asyncio
    import httpx
    from .governance_state import build_governance_snapshot

    checked_at = datetime.now(timezone.utc).isoformat()

    async def _probe(name: str, url: str, timeout: float = 2.0, headers: dict | None = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                resp = await c.get(url, headers=headers or {})
                latency_ms = int(resp.elapsed.total_seconds() * 1000)
                return {
                    "id": name,
                    "status": "healthy",
                    "required": name in {"redis", "qdrant", "litellm"},
                    "last_checked_at": checked_at,
                    "detail": f"latency_ms={latency_ms}",
                    "latency_ms": latency_ms,
                }
        except Exception as e:
            return {
                "id": name,
                "status": "down",
                "required": name in {"redis", "qdrant", "litellm"},
                "last_checked_at": checked_at,
                "detail": str(e)[:120],
            }

    deps = await asyncio.gather(
        _probe_redis_dependency(checked_at),
        _probe("qdrant", f"{settings.qdrant_url}/collections"),
        _probe("litellm", f"{settings.litellm_url}/health",
               headers={"Authorization": f"Bearer {settings.litellm_api_key}"} if settings.litellm_api_key else None),
        _probe("coordinator", f"{settings.coordinator_url}/health"),
        _probe("embedding", f"{settings.embedding_url}/health"),
    )

    active_agents = list_agents()
    persistence = get_checkpointer_status()
    durable_state = get_durable_state_status()
    governance = await build_governance_snapshot()
    bootstrap = await build_bootstrap_runtime_snapshot(
        include_snapshot_write=False,
        allow_stale=True,
    )
    summary = _build_health_summary(deps, active_agents, persistence, durable_state, governance)

    return {
        "service": "agent-server",
        "version": app.version,
        "auth_class": "admin",
        "dependencies": deps,
        "started_at": SERVICE_STARTED_AT,
        "actions_allowed": [
            "governor.pause",
            "governor.resume",
            "governor.presence",
            "governor.release_tier",
            "tasks.approve",
            "tasks.reject",
        ],
        "bootstrap": bootstrap,
        **summary,
    }


@app.get("/health/livez")
async def health_livez():
    """Cheap liveness check that avoids dependency fan-out."""
    active_agents = list_agents()
    return {
        "service": "agent-server",
        "status": "healthy" if active_agents else "degraded",
        "started_at": SERVICE_STARTED_AT,
        "agent_count": len(active_agents),
        "agents": active_agents,
        "launch_ready": True,
        "mode": "liveness_only",
    }


@app.get("/v1/system-map")
async def system_map():
    """Return the live system map plus registry-backed topology and portfolio state."""
    return await build_system_map_snapshot(get_agent_metadata())


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
    agent_metadata = get_agent_metadata()
    agents = []
    for name, meta in agent_metadata.items():
        agents.append({
            "name": name,
            "description": meta["description"],
            "tools": meta["tools"],
            "type": meta["type"],
            "schedule": meta.get("schedule"),
            "owner_domains": meta.get("owner_domains", []),
            "support_domains": meta.get("support_domains", []),
            "status": "online" if name in active else "planned",
            "status_note": meta.get("status_note"),
        })
    return {"agents": agents}


@app.get("/v1/domains")
async def domains_metadata():
    return {"domains": build_domain_metadata()}


@app.get("/v1/control-plane/registries")
async def control_plane_registries():
    return build_control_plane_registry_snapshot()


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
from .routes.governor import router as governor_router
from .routes.plans import router as plans_router
from .routes.projects import router as projects_router
from .routes.models import router as models_router
from .routes.home import router as home_router
from .routes.digests import router as digests_router
from .routes.model_governance import router as model_governance_router
from .routes.operator_audit import router as operator_audit_router
from .routes.operator_governance import router as operator_governance_router
from .routes.operator_work import router as operator_work_router
from .routes.review import router as review_router
from .routes.core_memory import router as core_memory_router
from .routes.bootstrap import router as bootstrap_router

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
app.include_router(governor_router)
app.include_router(plans_router)
app.include_router(projects_router)
app.include_router(models_router)
app.include_router(home_router)
app.include_router(digests_router)
app.include_router(model_governance_router)
app.include_router(operator_audit_router)
app.include_router(operator_governance_router)
app.include_router(operator_work_router)
app.include_router(review_router)
app.include_router(core_memory_router)
app.include_router(bootstrap_router)

from .routes.feedback import router as feedback_router
app.include_router(feedback_router)

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
