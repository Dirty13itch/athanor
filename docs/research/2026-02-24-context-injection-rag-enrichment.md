# Context Injection & RAG Enrichment for LangGraph ReAct Agents

*Research: 2026-02-24*
*Status: Complete*
*Unblocks: Intelligence Layer 2 (per-agent memory and context-aware responses)*

---

## Context

Athanor's 7 LangGraph agents currently use static string system prompts with no dynamic context injection. Every request is processed without knowledge of user preferences, recent activity, past conversations, or agent-specific situational data. This research evaluates patterns for enriching agent context before and during the ReAct loop, with specific focus on the installed stack: LangGraph 1.0.9, Qwen3-32B-AWQ (32K context), Qdrant (1024-dim Cosine), and FastAPI.

### Current Architecture

```
User Request
  -> FastAPI POST /v1/chat/completions
  -> _convert_messages() (role mapping only)
  -> agent.ainvoke({"messages": lc_messages}, config)
  -> create_react_agent(prompt=STATIC_STRING, tools=..., checkpointer=InMemorySaver)
  -> LLM call via LiteLLM -> Qwen3-32B-AWQ (vLLM, TP=4)
```

No enrichment happens between "user sends message" and "agent processes it."

---

## Options Analyzed

### 1. Callable `prompt` Parameter

LangGraph's `create_react_agent()` accepts `prompt` as a `Callable[[StateSchema], list[BaseMessage]]`. This runs **once at the start** of each agent invocation, before the first LLM call. It receives the full agent state (including messages) and returns the complete message list to send to the model.

**Mechanics:**
```python
def media_prompt(state: AgentState) -> list[BaseMessage]:
    # Static system instruction
    system = SystemMessage(content="You are the Media Agent...")

    # Dynamic context (fetched async in a wrapper)
    context = SystemMessage(content=f"""
## Your Memory
{format_preferences(state.get("preferences", []))}

## Recent Activity
{format_activity(state.get("recent_activity", []))}
""")

    return [system, context] + state["messages"]
```

**Pros:**
- Cleanest API — purpose-built for this use case
- Runs once per invocation, not per ReAct iteration (no token waste)
- Full access to state, including custom fields via `state_schema`
- The callable signature in LangGraph 1.0.9 also supports `store` injection via `BaseStore`

**Cons:**
- The callable is synchronous in some LangGraph versions (need to verify async support)
- Fetching context inside the prompt callable creates coupling between prompt logic and data access
- Cannot modify messages mid-ReAct-loop (by design, which is usually correct)

**Verdict:** Best fit for initial context enrichment. Use this.

### 2. `pre_model_hook` Parameter

Runs **before every LLM call** in the ReAct loop (including after tool results come back). Returns a dict with `messages` or `llm_input_messages`.

**Mechanics:**
```python
def manage_context(state: AgentState) -> dict:
    messages = state["messages"]

    # Trim to prevent context overflow
    if len(messages) > 15:
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        recent = messages[-(15 - len(system_msgs)):]
        messages = system_msgs + recent

    return {"llm_input_messages": messages}
```

**Pros:**
- Runs every iteration — ideal for context window management
- Can trim, summarize, or rewrite messages before each LLM call
- Can implement sliding window or token-counting truncation

**Cons:**
- Re-injecting RAG context here would waste tokens on every ReAct iteration
- Adds latency to every LLM call if doing expensive operations
- Should NOT be used for initial enrichment — that belongs in `prompt`

**Verdict:** Best fit for context window management (trimming, truncation). Not for RAG injection.

### 3. Endpoint Middleware (FastAPI-level enrichment)

Enrich messages in the `chat_completions()` endpoint before passing to `agent.ainvoke()`.

**Mechanics:**
```python
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model_name = body.get("model", "general-assistant")
    messages = body.get("messages", [])

    # Enrich before agent sees the request
    enrichment = await get_context_for_agent(model_name, messages)
    enriched_messages = inject_context(messages, enrichment)

    lc_messages = _convert_messages(enriched_messages)
    # ... pass to agent
```

**Pros:**
- Full async control — can use `asyncio.gather()` for parallel queries
- Clean separation: enrichment logic is in the request pipeline, not in agent config
- Easy to test independently
- Can share enrichment code across agents via a dispatcher

**Cons:**
- Enrichment is "invisible" to the agent (it just sees modified messages)
- Cannot access LangGraph state (checkpointer history, etc.)
- Tighter coupling to the FastAPI server
- Doesn't benefit from LangGraph's built-in `store` integration

**Verdict:** Viable but less clean than callable `prompt`. Better for cross-cutting concerns.

### 4. Custom State Schema with Pre-populated Fields

Define a custom `state_schema` with fields for context, then populate those fields in the `ainvoke()` call. The callable `prompt` then reads from state.

**Mechanics:**
```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class EnrichedState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    preferences: list[dict]
    recent_activity: list[dict]
    user_context: dict

# At invocation time:
enrichment = await fetch_enrichment(agent_name, user_query)
result = await agent.ainvoke({
    "messages": lc_messages,
    "preferences": enrichment["preferences"],
    "recent_activity": enrichment["activity"],
    "user_context": enrichment["context"],
}, config=config)
```

**Pros:**
- Clean separation: data fetching in endpoint, data formatting in prompt callable
- State fields are typed and documented
- Tools can also access enrichment via `InjectedState`
- Most flexible pattern

**Cons:**
- Requires defining custom state per agent (or a shared enriched state)
- Adds complexity to the agent factory

**Verdict:** Best overall pattern when combined with callable `prompt`. Recommended.

### 5. InjectedState for Tool-Level Context

LangGraph supports `Annotated[dict, InjectedState]` in tool parameters. Tools can read state fields without the LLM knowing about them.

**Mechanics:**
```python
from langgraph.prebuilt import InjectedState

@tool
def search_with_context(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Search with user preferences applied."""
    prefs = state.get("preferences", {})
    # Use preferences to filter/rank results
    ...
```

**Pros:** Tools can be preference-aware without bloating the system prompt.
**Cons:** Only applies to tool execution, not to the LLM's reasoning about what tools to call.
**Verdict:** Complementary to prompt-level injection. Use for tool-level personalization.

---

## Recommended Architecture

### Pattern: State Schema + Callable Prompt + Endpoint Enrichment

```
User Request
  -> FastAPI endpoint
  -> async fetch_enrichment(agent_name, user_query)
       -> asyncio.gather(
            query_preferences(query, agent),
            query_recent_activity(agent, limit=5),
            get_workspace_broadcast(),
          )
  -> agent.ainvoke({
       "messages": lc_messages,
       "preferences": preferences,
       "recent_activity": activity,
       "workspace": broadcast,
     }, config=config)
  -> callable prompt(state) builds:
       [SystemMessage(static), SystemMessage(dynamic_context), *user_messages]
  -> pre_model_hook trims if needed
  -> LLM processes enriched context
```

### Implementation Skeleton

```python
# --- State schema (shared across agents) ---

class EnrichedAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    preferences: list[dict]       # From Qdrant preferences collection
    recent_activity: list[dict]   # From Qdrant activity collection
    workspace: list[dict]         # From GWT workspace broadcast
    remaining_steps: RemainingSteps


# --- Context fetcher (in server.py or new context.py) ---

async def fetch_enrichment(
    agent_name: str,
    user_query: str,
    timeout: float = 3.0,
) -> dict:
    """Fetch all context for an agent in parallel. Graceful degradation on timeout."""

    async def safe(coro, default):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except (asyncio.TimeoutError, Exception):
            return default

    # Single embedding for the user query (reuse across searches)
    try:
        query_vector = await asyncio.to_thread(_get_embedding, user_query[:500])
    except Exception:
        return {"preferences": [], "recent_activity": [], "workspace": []}

    prefs_task = safe(
        _search_preferences_by_vector(query_vector, agent_name, limit=5),
        [],
    )
    activity_task = safe(
        _search_activity_by_agent(agent_name, limit=5),
        [],
    )
    workspace_task = safe(
        _get_workspace_broadcast(),
        [],
    )

    prefs, activity, workspace = await asyncio.gather(
        prefs_task, activity_task, workspace_task
    )

    return {
        "preferences": prefs,
        "recent_activity": activity,
        "workspace": workspace,
    }


# --- Callable prompt factory (per-agent) ---

def make_media_prompt(static_prompt: str):
    def media_prompt(state: EnrichedAgentState) -> list:
        parts = [static_prompt]

        # Inject preferences
        prefs = state.get("preferences", [])
        if prefs:
            pref_text = "\n".join(f"- {p['content']}" for p in prefs[:5])
            parts.append(f"\n## Your Memory (User Preferences)\n{pref_text}")

        # Inject recent activity
        activity = state.get("recent_activity", [])
        if activity:
            act_text = "\n".join(
                f"- [{a['timestamp'][:16]}] {a['input_summary'][:100]}"
                for a in activity[:5]
            )
            parts.append(f"\n## Recent Interactions\n{act_text}")

        system = SystemMessage(content="\n".join(parts))
        return [system] + state["messages"]

    return media_prompt


# --- Pre-model hook for context window management ---

def trim_context(state: EnrichedAgentState) -> dict:
    """Keep context under budget. Runs before every LLM call."""
    messages = list(state["messages"])

    # Rough token estimate: 4 chars per token
    total_chars = sum(len(str(m.content)) for m in messages)
    MAX_CHARS = 80000  # ~20K tokens, leaving room for response

    if total_chars > MAX_CHARS:
        # Keep system messages + last N messages
        system = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        # Trim from the front of non-system messages
        while sum(len(str(m.content)) for m in non_system) > (MAX_CHARS - sum(len(str(m.content)) for m in system)):
            if len(non_system) <= 2:
                break
            non_system.pop(0)

        messages = system + non_system

    return {"llm_input_messages": messages}


# --- Agent factory update ---

def create_media_agent():
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.7,
        streaming=True,
    )

    return create_react_agent(
        model=llm,
        tools=MEDIA_TOOLS,
        prompt=make_media_prompt(MEDIA_SYSTEM_PROMPT),
        pre_model_hook=trim_context,
        state_schema=EnrichedAgentState,
        checkpointer=InMemorySaver(),
    )
```

---

## Per-Agent Context Specialization

| Agent | Preferences Query | Activity Filter | Extra Context |
|-------|------------------|-----------------|---------------|
| **media-agent** | "media quality viewing preferences" | `agent=media-agent` | Last 5 watch history items (Tautulli) |
| **home-agent** | "home comfort lighting temperature" | `agent=home-agent` | Current time, day of week, season |
| **creative-agent** | "image style resolution preferences" | `agent=creative-agent` | Recent generation history |
| **general-assistant** | (user query as-is) | all agents, last 5 | System health summary |
| **research-agent** | "research topics methodology" | `agent=research-agent` | Recent research topics (dedup) |
| **knowledge-agent** | "documentation search patterns" | `agent=knowledge-agent` | Knowledge base stats |
| **coding-agent** | "coding style conventions" | `agent=coding-agent` | Recent code patterns |

### Context Templates Per Agent

**Media Agent dynamic context:**
```
## Your Memory (User Preferences)
- I prefer 4K quality when available
- Don't recommend horror movies
- Favorite genres: sci-fi, thriller, documentary

## Recent Activity
- [2026-02-24 18:30] Searched for "The Last of Us Season 3"
- [2026-02-24 17:15] Added "Severance" to monitoring

## Currently Playing on Plex
- Nothing playing
```

**Home Agent dynamic context:**
```
## Your Memory (User Preferences)
- Preferred temperature: 71F during day, 68F at night
- Living room lights dim after 9 PM
- Morning routine starts at 6:30 AM

## Current State
- Time: 8:45 PM (evening routine)
- Day: Monday
- Season: Winter

## Recent Interactions
- [2026-02-24 20:30] Set bedroom temperature to 68F
- [2026-02-24 19:00] Dimmed living room to 40%
```

---

## Performance Analysis

### Latency Budget

Target: enrichment adds <300ms to request processing (before first token).

| Operation | Expected Latency | Strategy |
|-----------|-----------------|----------|
| Embedding (user query) | 20-50ms | Single call, reuse vector |
| Qdrant preferences search | 5-15ms | Async, 3s timeout |
| Qdrant activity scroll | 5-15ms | Async, 3s timeout |
| GWT workspace read | 2-5ms | Redis GET, async |
| **Total (parallel)** | **50-80ms** | `asyncio.gather()` |

All three Qdrant/Redis operations run in parallel after the embedding completes. The embedding call is the bottleneck at 20-50ms (Qwen3-Embedding-0.6B on Node 1 GPU 4).

### Optimization Strategies

1. **Single embedding, multiple searches.** Embed the user query once. Use the same vector for both preference search and activity search (via vector similarity). Saves one 20-50ms embedding call.

2. **Aggressive timeouts.** Each enrichment source gets a 3-second timeout. If any source fails, the agent proceeds with whatever context is available. No enrichment failure should block the request.

3. **Async HTTP client.** Replace synchronous `httpx.post()` with `httpx.AsyncClient()` for Qdrant and embedding calls in the enrichment pipeline. The current `activity.py` uses sync httpx wrapped in `asyncio.to_thread()` — direct async is cleaner.

4. **Relevance threshold.** Only inject preferences with similarity score > 0.5. Low-relevance preferences add noise without value.

5. **Cache layer (future).** For repeated queries (e.g., "what's playing on Plex"), cache the enrichment result for 60 seconds in Redis. Not needed for v1 but worth designing for.

6. **Batch embedding (future).** If enriching multiple agents simultaneously (e.g., meta-orchestrator routing), batch the embedding calls. Qwen3-Embedding-0.6B supports batch input.

### Latency Measurements to Validate

Before deploying, measure on the actual cluster:
- Qwen3-Embedding-0.6B latency for single query (expect 20-50ms)
- Qdrant search latency for 922-point `knowledge` collection (expect 5-15ms)
- Qdrant scroll latency for `activity` collection (expect 5-15ms)
- Redis GET latency from Node 1 to VAULT (expect 1-3ms)
- End-to-end enrichment pipeline (expect 50-100ms total)

---

## Context Window Management

### Token Budget for Qwen3-32B-AWQ (32K context)

```
Total context window:               32,768 tokens
  - System prompt (static):           ~500 tokens
  - Injected context (dynamic):      ~1,500 tokens  (HARD CAP: 2,000)
  - Conversation history:            ~8,000 tokens  (managed via pre_model_hook)
  - Tool calls + results:            ~6,000 tokens  (per-iteration, varies)
  - Think block (Qwen3):             ~2,000 tokens  (internal reasoning)
  - Model response:                  ~4,000 tokens  (max_tokens setting)
  - Safety margin:                   ~8,768 tokens
```

### Rules

1. **Injected context hard cap: 2,000 tokens (~1,500 words, ~6,000 chars).** This includes preferences, activity, and any agent-specific context. Enforce by character counting before injection.

2. **Preference items: max 5, max 100 chars each.** Total: ~500 tokens. Sorted by relevance score, threshold at 0.5.

3. **Activity items: max 5, max 150 chars each.** Total: ~750 tokens. Most recent first.

4. **Agent-specific context: max 250 tokens.** Watch history, entity states, etc.

5. **Conversation history: trim at 15 messages.** Keep system messages + most recent 13-14 non-system messages. Implemented via `pre_model_hook`.

6. **Tool results: truncate at 2,000 chars per result.** Already implemented in streaming code (`output[:2000]`).

### Token Counting

For a production system, use `tiktoken` or the model's tokenizer. For Qwen3, a rough 3.5 chars/token ratio works for English text. For the v1 implementation, character-based estimation is sufficient:

```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate for Qwen3. 3.5 chars per token for English."""
    return len(text) // 3 + 1
```

---

## Where to Inject: Message Placement

### Option A: Extra SystemMessage (Recommended)

Add a second `SystemMessage` after the static system prompt:

```python
[
    SystemMessage(content="You are the Media Agent..."),           # Static
    SystemMessage(content="## Your Memory\n- Prefers 4K..."),     # Dynamic
    HumanMessage(content="What's new on Plex?"),                  # User
]
```

**Why:** Multiple system messages are well-supported by Qwen3. The model treats them as additive instructions. Clean separation between static persona and dynamic context.

### Option B: Append to System Prompt

Concatenate dynamic context into the static system prompt string:

```python
[
    SystemMessage(content="You are the Media Agent...\n\n## Your Memory\n- Prefers 4K..."),
    HumanMessage(content="What's new on Plex?"),
]
```

**Why not:** Harder to measure/cap the dynamic portion. Mixes concerns.

### Option C: Prepend as HumanMessage

Add a synthetic `HumanMessage` with context:

```python
[
    SystemMessage(content="You are the Media Agent..."),
    HumanMessage(content="[Context] User prefers 4K, recently watched..."),
    HumanMessage(content="What's new on Plex?"),
]
```

**Why not:** The model may treat it as conversation history and respond to it. Creates confusion about what the user actually said.

### Option D: Separate "context" Role

Some frameworks support a `context` message role. LangChain does not natively support this, and vLLM/Qwen3 would ignore or error on unknown roles.

**Why not:** Not supported by the stack.

### Verdict

**Option A (extra SystemMessage)** is the cleanest pattern. Use it.

---

## Implementation Plan

### Phase 1: Foundation (1 session)

1. Create `context.py` module with:
   - `EnrichedAgentState` TypedDict
   - `fetch_enrichment()` async function
   - `format_preferences()` and `format_activity()` helpers
   - `trim_context()` pre-model hook

2. Create `prompts.py` module with:
   - `make_enriched_prompt(static_prompt, agent_name)` factory
   - Per-agent static prompts (moved from agent files)

3. Update one agent (media-agent) as proof of concept:
   - Switch to `EnrichedAgentState`
   - Switch to callable prompt
   - Add pre_model_hook

4. Update `server.py` chat_completions:
   - Call `fetch_enrichment()` before `agent.ainvoke()`
   - Pass enrichment data in state

### Phase 2: Rollout (1 session)

5. Update remaining 6 agents to use enriched state
6. Implement per-agent context specialization
7. Add latency metrics (log enrichment time to activity)

### Phase 3: Optimization (1 session)

8. Switch from sync httpx to async httpx.AsyncClient for Qdrant
9. Add relevance threshold filtering (score > 0.5)
10. Add enrichment latency to Prometheus metrics
11. Measure and validate latency budget

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Enrichment latency exceeds 300ms | Slower first-token time | Aggressive timeouts, graceful degradation |
| Injected context confuses model | Lower response quality | Cap at 2K tokens, relevance threshold |
| Qdrant unavailable | No enrichment | Try/except with empty defaults |
| Context window overflow | Truncated responses | pre_model_hook trimming, character counting |
| Stale preferences | Irrelevant context | Recency weighting, TTL on preference points |

---

## Sources

- [LangGraph Agents API Reference](https://langchain-ai.github.io/langgraph/reference/agents/?h=create_react) -- `create_react_agent` parameter documentation
- [LangGraph ReAct Agent (DeepWiki)](https://deepwiki.com/langchain-ai/langgraph/8.1-react-agent-(create_react_agent)) -- Detailed analysis of prompt, pre_model_hook, post_model_hook, state_schema, InjectedState patterns
- [LangGraph pre/post hooks discussion](https://forum.langchain.com/t/add-pre-post-hooks-for-structured-response-generation-in-create-react-agent/1795) -- Community discussion on hook patterns
- [Qdrant Async Client](https://python-client.qdrant.tech/qdrant_client.async_qdrant_client) -- AsyncQdrantClient for non-blocking vector searches
- [Async RAG with FastAPI + Qdrant](https://blog.futuresmart.ai/rag-system-with-async-fastapi-qdrant-langchain-and-openai) -- Pattern for async RAG pipeline
- [Qwen3-32B Model Card (HuggingFace)](https://huggingface.co/Qwen/Qwen3-32B) -- 32K native context, 131K via YaRN
- [Context Window Management Strategies](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/) -- Sliding window, summarization, selective injection
- [Context Engineering for Production Agents](https://medium.com/@kuldeep.paul08/context-engineering-optimizing-llm-memory-for-production-ai-agents-6a7c9165a431) -- Token budget allocation patterns
- [Top Techniques for Context Length Management](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms) -- Write/Select/Compress/Isolate framework
- [LangGraph InjectedState Documentation](https://context7.com/langchain-ai/langgraph/llms.txt) -- Tool-level state injection for personalized tool execution
- Verified LangGraph 1.0.9 / langgraph-prebuilt 1.0.8 installed on Node 1 (runtime inspection of `create_react_agent` signature confirms `prompt`, `pre_model_hook`, `post_model_hook`, `state_schema`, `context_schema`, `store` parameters)
