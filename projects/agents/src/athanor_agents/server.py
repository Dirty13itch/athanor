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

    _init_agents()
    yield


app = FastAPI(title="Athanor Agent Server", version="0.2.0", lifespan=lifespan)


# --- Agent metadata (single source of truth) ---

AGENT_METADATA = {
    "general-assistant": {
        "description": "System monitoring and infrastructure management across all 3 nodes.",
        "tools": ["check_services", "get_gpu_metrics", "get_vllm_models", "get_storage_info"],
        "type": "reactive",
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
        "status_note": "Blocked on HA onboarding",
    },
    "creative-agent": {
        "description": "Image generation via ComfyUI Flux — text-to-image, queue management, generation history.",
        "tools": ["generate_image", "check_queue", "get_generation_history", "get_comfyui_status"],
        "type": "reactive",
    },
    "research-agent": {
        "description": "Web research and information synthesis — citations, fact-checking, knowledge search, graph queries.",
        "tools": ["web_search", "fetch_page", "search_knowledge", "query_infrastructure"],
        "type": "reactive",
    },
    "knowledge-agent": {
        "description": "Knowledge base maintenance — documentation sync, stale doc detection, cross-reference updates.",
        "tools": ["scan_docs", "check_freshness", "update_index", "find_conflicts"],
        "type": "proactive",
        "schedule": "daily 3 AM",
        "status_note": "Planned",
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

    if stream:
        return StreamingResponse(
            _stream_response(agent, lc_messages, config, model_name),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    result = await agent.ainvoke({"messages": lc_messages}, config=config)
    content = _strip_think_tags(result["messages"][-1].content)

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


async def _stream_response(agent, messages, config, model_name):
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    # Send initial role chunk
    yield _sse_chunk(chat_id, created, model_name, {"role": "assistant"})

    in_think = False
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
            yield _sse_chunk(chat_id, created, model_name, {"content": text})

    # Finish
    yield _sse_chunk(chat_id, created, model_name, {}, finish_reason="stop")
    yield "data: [DONE]\n\n"


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
