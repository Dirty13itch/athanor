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

    # Seed skill library with initial skills if empty
    try:
        from .skill_learning import ensure_initial_skills
        seeded = await ensure_initial_skills()
        if seeded:
            print(f"[lifespan] Skill library seeded with {seeded} initial skills", flush=True)
    except Exception as e:
        print(f"[lifespan] Skill seeding failed: {e}", flush=True)

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


@app.get("/v1/models/governance")
async def model_governance():
    from .model_governance import build_live_model_governance_snapshot

    return await build_live_model_governance_snapshot()


@app.get("/v1/models/governance/promotions")
async def model_governance_promotions(limit: int = 12):
    from .promotion_control import build_promotion_controls_snapshot

    return await build_promotion_controls_snapshot(limit=limit)


@app.post("/v1/models/governance/promotions")
async def stage_model_governance_promotion(request: Request):
    from .promotion_control import stage_promotion_candidate

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


@app.post("/v1/models/governance/promotions/{promotion_id}/{action}")
async def transition_model_governance_promotion(promotion_id: str, action: str, request: Request):
    from .promotion_control import transition_promotion_candidate

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


@app.get("/v1/models/governance/retirements")
async def model_governance_retirements(limit: int = 12):
    from .retirement_control import build_retirement_controls_snapshot

    return await build_retirement_controls_snapshot(limit=limit)


@app.post("/v1/models/governance/retirements")
async def stage_model_governance_retirement(request: Request):
    from .retirement_control import stage_retirement_candidate

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


@app.post("/v1/models/governance/retirements/{retirement_id}/{action}")
async def transition_model_governance_retirement(retirement_id: str, action: str, request: Request):
    from .retirement_control import transition_retirement_candidate

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


@app.get("/v1/models/proving-ground")
async def model_proving_ground(limit: int = 12):
    from .proving_ground import build_proving_ground_snapshot

    return await build_proving_ground_snapshot(limit=limit)


@app.post("/v1/models/proving-ground/run")
async def run_model_proving_ground(request: Request):
    from .proving_ground import run_proving_ground

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    limit = int(body.get("limit", 12)) if isinstance(body, dict) else 12
    return await run_proving_ground(limit=limit)


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
    from .tool_permissions import evaluate_tool_permission

    body = await request.json()
    requester = body.get("requester", "")
    task_class = body.get("task_class", "")
    if not requester or not task_class:
        return JSONResponse(
            status_code=400,
            content={"error": "Both 'requester' and 'task_class' are required"},
        )

    permission = evaluate_tool_permission(
        requester,
        "lease requests",
        tool_name="subscription lease",
        metadata={"task_class": task_class},
    )
    if not permission["allowed"]:
        return JSONResponse(status_code=403, content={"error": permission["reason"]})

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


@app.get("/v1/subscriptions/summary")
async def subscription_backbone_summary(limit: int = 10):
    from .backbone import build_quota_lease_summary

    return await build_quota_lease_summary(limit=limit)


@app.get("/v1/subscriptions/execution")
async def subscription_execution_snapshot(limit: int = 10):
    from .provider_execution import build_provider_execution_snapshot

    return await build_provider_execution_snapshot(limit=limit)


@app.post("/v1/subscriptions/execution")
async def subscription_execute_provider(request: Request):
    from .provider_execution import execute_provider_request

    body = await request.json()
    requester = body.get("requester", "")
    task_class = body.get("task_class", "")
    prompt = body.get("prompt", "")
    if not requester or not task_class or not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'requester', 'task_class', and 'prompt' are required"},
        )

    try:
        result = await execute_provider_request(
            requester=requester,
            prompt=prompt,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            metadata=body.get("metadata", {}),
            issue_lease=bool(body.get("issue_lease", True)),
            timeout_seconds=int(body.get("timeout_seconds", 90)),
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    return result


@app.get("/v1/subscriptions/handoffs")
async def subscription_handoffs(requester: str = "", limit: int = 25):
    from .provider_execution import list_handoff_bundles

    bundles = await list_handoff_bundles(requester=requester, limit=limit)
    return {"handoffs": bundles, "count": len(bundles)}


@app.get("/v1/subscriptions/handoffs/events")
async def subscription_handoff_events(limit: int = 25):
    from .provider_execution import list_handoff_events

    events = await list_handoff_events(limit=limit)
    return {"events": events, "count": len(events)}


@app.post("/v1/subscriptions/handoffs")
async def create_subscription_handoff(request: Request):
    from .provider_execution import create_handoff_bundle

    body = await request.json()
    requester = body.get("requester", "")
    task_class = body.get("task_class", "")
    prompt = body.get("prompt", "")
    if not requester or not task_class or not prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "Fields 'requester', 'task_class', and 'prompt' are required"},
        )

    try:
        bundle = await create_handoff_bundle(
            requester=requester,
            prompt=prompt,
            task_class=task_class,
            sensitivity=body.get("sensitivity", "repo_internal"),
            interactive=bool(body.get("interactive", False)),
            expected_context=body.get("expected_context", "medium"),
            parallelism=body.get("parallelism", "low"),
            metadata=body.get("metadata", {}),
            issue_lease=bool(body.get("issue_lease", True)),
        )
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    return {"handoff": bundle}


@app.post("/v1/subscriptions/handoffs/{handoff_id}/outcome")
async def update_subscription_handoff_outcome(handoff_id: str, request: Request):
    from .provider_execution import record_handoff_outcome

    body = await request.json()
    outcome = body.get("outcome", "")
    if not outcome:
        return JSONResponse(status_code=400, content={"error": "'outcome' is required"})

    bundle = await record_handoff_outcome(
        handoff_id=handoff_id,
        outcome=outcome,
        notes=body.get("notes", ""),
        result_summary=body.get("result_summary", ""),
        artifact_refs=body.get("artifact_refs"),
        quality_score=body.get("quality_score"),
        latency_ms=body.get("latency_ms"),
    )
    if bundle is None:
        return JSONResponse(status_code=404, content={"error": f"Handoff '{handoff_id}' not found"})
    return {"handoff": bundle}


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


@app.get("/v1/system-map")
async def system_map():
    from .command_hierarchy import build_system_map_snapshot

    return await build_system_map_snapshot(AGENT_METADATA)


@app.get("/v1/governor")
async def governor_snapshot():
    from .governor import build_governor_snapshot

    return await build_governor_snapshot()


@app.get("/v1/governor/operations")
async def governor_operations_snapshot():
    from .governor import build_operations_readiness_snapshot

    return await build_operations_readiness_snapshot()


@app.get("/v1/governor/tool-permissions")
async def governor_tool_permissions_snapshot():
    from .governor import build_tool_permissions_snapshot

    return await build_tool_permissions_snapshot()


@app.get("/v1/governor/operator-tests")
async def governor_operator_tests():
    from .operator_tests import build_operator_tests_snapshot

    return await build_operator_tests_snapshot()


@app.post("/v1/governor/operator-tests/run")
async def governor_operator_tests_run(request: Request):
    from .operator_tests import run_operator_tests

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    flow_ids = None
    if isinstance(body, dict):
        raw_flow_ids = body.get("flow_ids")
        if isinstance(raw_flow_ids, list):
            flow_ids = [str(item) for item in raw_flow_ids if str(item).strip()]
    actor = body.get("actor", "operator") if isinstance(body, dict) else "operator"
    return await run_operator_tests(flow_ids=flow_ids, actor=actor)


@app.post("/v1/governor/pause")
async def governor_pause(request: Request):
    from .governor import pause_automation

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    scope = body.get("scope", "global") if isinstance(body, dict) else "global"
    reason = body.get("reason", "") if isinstance(body, dict) else ""
    actor = body.get("actor", "operator") if isinstance(body, dict) else "operator"
    return await pause_automation(scope=scope, reason=reason, actor=actor)


@app.post("/v1/governor/resume")
async def governor_resume(request: Request):
    from .governor import resume_automation

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    scope = body.get("scope", "global") if isinstance(body, dict) else "global"
    actor = body.get("actor", "operator") if isinstance(body, dict) else "operator"
    return await resume_automation(scope=scope, actor=actor)


@app.post("/v1/governor/presence")
async def governor_presence(request: Request):
    from .governor import set_operator_presence

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    state_id = body.get("state", "at_desk") if isinstance(body, dict) else "at_desk"
    reason = body.get("reason", "") if isinstance(body, dict) else ""
    actor = body.get("actor", "operator") if isinstance(body, dict) else "operator"
    mode = body.get("mode", "manual") if isinstance(body, dict) else "manual"
    return await set_operator_presence(state_id=state_id, reason=reason, actor=actor, mode=mode)


@app.post("/v1/governor/heartbeat")
async def governor_heartbeat(request: Request):
    from .governor import record_presence_heartbeat

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    state_id = body.get("state", "at_desk") if isinstance(body, dict) else "at_desk"
    source = body.get("source", "dashboard_heartbeat") if isinstance(body, dict) else "dashboard_heartbeat"
    reason = body.get("reason", "") if isinstance(body, dict) else ""
    actor = body.get("actor", "dashboard-heartbeat") if isinstance(body, dict) else "dashboard-heartbeat"
    return await record_presence_heartbeat(
        state_id=state_id,
        source=source,
        reason=reason,
        actor=actor,
    )


@app.post("/v1/governor/release-tier")
async def governor_release_tier(request: Request):
    from .governor import set_release_tier

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    tier = body.get("tier", "production") if isinstance(body, dict) else "production"
    reason = body.get("reason", "") if isinstance(body, dict) else ""
    actor = body.get("actor", "operator") if isinstance(body, dict) else "operator"
    return await set_release_tier(tier=tier, reason=reason, actor=actor)


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


@app.get("/v1/activity/operator-stream")
async def operator_stream(limit: int = 30):
    from .backbone import build_operator_stream

    events = await build_operator_stream(limit=limit)
    return {"events": events, "count": len(events)}


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


@app.get("/v1/tasks/runs")
async def task_execution_runs(agent: str = "", limit: int = 50):
    from .backbone import build_execution_run_records

    runs = await build_execution_run_records(agent=agent, limit=limit)
    return {"runs": runs, "count": len(runs)}


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


@app.get("/v1/tasks/scheduled")
async def scheduled_jobs(limit: int = 50):
    from .backbone import build_scheduled_job_records

    jobs = await build_scheduled_job_records(limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@app.post("/v1/tasks/scheduled/{job_id}/run")
async def run_scheduled_job_endpoint(job_id: str, request: Request):
    from .scheduler import run_scheduled_job

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    actor = str(dict(body or {}).get("actor") or "operator")
    force = bool(dict(body or {}).get("force"))
    try:
        result = await run_scheduled_job(job_id, actor=actor, force=force)
        return result
    except KeyError:
        return JSONResponse(
            status_code=404,
            content={"error": f"Scheduled job '{job_id}' not found"},
        )


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
    from .command_hierarchy import classify_policy_class
    from .router import classify_request

    body = await request.json()
    prompt = body.get("prompt", "")
    agent_name = body.get("agent", "")
    conversation_length = body.get("conversation_length", 0)

    if not prompt:
        return JSONResponse(status_code=400, content={"error": "prompt is required"})

    routing = classify_request(prompt, agent_name, conversation_length)
    policy = classify_policy_class(prompt, body.get("metadata"))
    payload = routing.to_dict()
    payload.update(policy)
    return payload


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

from .skill_learning import (
    add_skill, get_skill, get_all_skills, delete_skill,
    record_execution, search_skills, get_top_skills, get_stats as get_skill_stats,
)


@app.get("/v1/skills")
async def list_skills(
    query: str = "",
    category: str | None = None,
    min_success_rate: float = 0.0,
    limit: int = 20,
):
    """Search the skill library."""
    skills = await search_skills(query=query, category=category, min_success_rate=min_success_rate, limit=limit)
    return {"skills": [s.to_dict() for s in skills], "count": len(skills)}


@app.get("/v1/skills/top")
async def top_skills(limit: int = 10):
    """Get top-performing skills by proven effectiveness."""
    skills = await get_top_skills(limit)
    return {"skills": [s.to_dict() for s in skills]}


@app.get("/v1/skills/stats")
async def skill_stats():
    """Get skill library statistics."""
    return await get_skill_stats()


@app.get("/v1/skills/{skill_id}")
async def get_skill_by_id(skill_id: str):
    """Get a specific skill by ID."""
    from fastapi import HTTPException
    skill = await get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@app.post("/v1/skills")
async def create_skill(body: dict):
    """Add a new skill to the library."""
    from fastapi import HTTPException
    required = {"name", "description", "trigger_conditions", "steps"}
    if not required.issubset(body):
        raise HTTPException(status_code=422, detail=f"Required fields: {required}")
    skill_id = await add_skill(
        name=body["name"],
        description=body["description"],
        trigger_conditions=body["trigger_conditions"],
        steps=body["steps"],
        category=body.get("category", "general"),
        tags=body.get("tags"),
        created_by=body.get("created_by", "api"),
    )
    return {"skill_id": skill_id, "status": "created"}


@app.post("/v1/skills/{skill_id}/execution")
async def record_skill_execution(skill_id: str, body: dict):
    """Record a skill execution outcome (updates success rate)."""
    from fastapi import HTTPException
    success = body.get("success", True)
    duration_ms = body.get("duration_ms", 0.0)
    context = body.get("context")
    ok = await record_execution(skill_id, success, float(duration_ms), context)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "recorded"}


@app.delete("/v1/skills/{skill_id}")
async def remove_skill(skill_id: str):
    """Delete a skill from the library."""
    from fastapi import HTTPException
    ok = await delete_skill(skill_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted"}


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
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
        "metadata": {"agent": model_name, "session_id": thread_id},
        "tags": [model_name],
    }

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
            _safe_stream_response(agent, lc_messages, config, model_name, user_input, routing, thread_id),
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


async def _safe_stream_response(agent, messages, config, model_name, user_input="", routing=None, thread_id=""):
    try:
        async for chunk in _stream_response(
            agent, messages, config, model_name, user_input, routing, thread_id
        ):
            yield chunk
    except Exception as exc:
        yield f'event: error\ndata: {json.dumps({"type": "error", "message": str(exc)[:500]})}\n\n'


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


@app.get("/v1/review/judges")
async def judge_plane(limit: int = 12):
    from .judge import build_judge_plane_snapshot

    return await build_judge_plane_snapshot(limit=limit)


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
