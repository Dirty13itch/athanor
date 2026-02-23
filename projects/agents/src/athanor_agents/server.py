import json
import re
import time
import uuid
from contextlib import asynccontextmanager

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


app = FastAPI(title="Athanor Agent Server", version="0.1.0", lifespan=lifespan)


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


@app.get("/v1/agents")
async def agents_endpoint():
    from .agents import get_agent_info
    return {"agents": get_agent_info()}


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
    tool_timers: dict[str, float] = {}  # run_id -> start_time

    async for event in agent.astream_events(
        {"messages": messages},
        config=config,
        version="v2",
    ):
        kind = event["event"]

        # --- Tool start ---
        if kind == "on_tool_start":
            run_id = event.get("run_id", "")
            tool_timers[run_id] = time.time()
            tool_event = {
                "type": "tool_start",
                "name": event.get("name", "unknown"),
                "args": event.get("data", {}).get("input", {}),
            }
            yield f"data: {json.dumps(tool_event)}\n\n"
            continue

        # --- Tool end ---
        if kind == "on_tool_end":
            run_id = event.get("run_id", "")
            start = tool_timers.pop(run_id, None)
            duration_ms = int((time.time() - start) * 1000) if start else 0
            output_data = event.get("data", {})
            # LangGraph tool output is in data.output (ToolMessage content)
            output = output_data.get("output", "")
            if hasattr(output, "content"):
                output = output.content
            output_str = str(output) if output else ""
            # Truncate very long outputs to avoid blowing up SSE
            if len(output_str) > 4000:
                output_str = output_str[:4000] + "\n... (truncated)"
            tool_event = {
                "type": "tool_end",
                "name": event.get("name", "unknown"),
                "output": output_str,
                "duration_ms": duration_ms,
            }
            yield f"data: {json.dumps(tool_event)}\n\n"
            continue

        # --- LLM text stream ---
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            text = chunk.content if hasattr(chunk, "content") else ""
            if not text:
                continue
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
