"""Chat completions route — OpenAI-compatible endpoint with routing, caching, streaming."""

import asyncio
import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..agents import get_agent, list_agents
from ..config import settings
from ..input_guard import sanitize_input, check_output, REFUSAL_RESPONSE, OUTPUT_REDACTED_RESPONSE

logger = logging.getLogger("athanor.chat")

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions")
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
    from ..router import classify_request, apply_preference_override

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
        from ..context import enrich_context

        try:
            context_str = await enrich_context(model_name, user_input) or ""
        except Exception as e:
            logger.debug("Context injection failed: %s", e)

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
        from ..semantic_cache import get_semantic_cache
        from ..circuit_breaker import get_circuit_breakers, CircuitOpenError

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
            except Exception as e:
                logger.debug("Semantic cache lookup failed: %s", e)

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
                from ..routing import FALLBACK_CHAINS
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
            except Exception as e:
                logger.debug("Semantic cache store failed: %s", e)

        duration_ms = int(time.time() * 1000) - start_ms

        from ..activity import log_activity, log_conversation

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
        from ..preferences import record_outcome as record_pref_outcome
        from ..routing import get_cost_tracker
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
    from ..circuit_breaker import get_circuit_breakers, CircuitOpenError
    from ..diagnosis import get_diagnosis_engine

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
        except Exception as e:
            logger.debug("Diagnosis record_failure failed: %s", e)
        raise

    duration_ms = int(time.time() * 1000) - start_ms

    # Log activity + conversation (fire-and-forget)
    from ..activity import log_activity, log_conversation

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
    from ..preferences import record_outcome as record_pref_outcome
    from ..routing import get_cost_tracker
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

    # Capture operator intent from chat (fire-and-forget)
    from ..intent_capture import capture_intent_from_chat
    asyncio.create_task(capture_intent_from_chat(user_input, content, model_name))

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
    from ..activity import log_activity, log_conversation

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

    # Capture operator intent from chat (fire-and-forget)
    from ..intent_capture import capture_intent_from_chat
    asyncio.create_task(capture_intent_from_chat(user_input, full_response, model_name))

    # Record cost (fire-and-forget)
    if routing:
        from ..routing import get_cost_tracker
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
