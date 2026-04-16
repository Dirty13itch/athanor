# Agent Framework

> Historical note: archived research retained for ADR-008 decision history. It is not current agent-server, routing, or deployment truth.

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-008 (Agent Framework)
**Depends on:** ADR-005 (Inference Engine)

---

## The Question

How does Athanor orchestrate AI agents — the research agent, media agent, home agent, creative agent, knowledge agent, and future agents described in VISION.md? What framework manages their lifecycle, tool access, memory, and coordination?

---

## Requirements

From VISION.md and the system architecture:

1. **OpenAI-compatible API** — agents must work with vLLM's API (ADR-005)
2. **Tool use** — agents call external APIs (Plex, Home Assistant, web search, file operations, ComfyUI)
3. **Memory** — agents need persistent state across conversations (who asked what, what was found)
4. **Multi-agent coordination** — some tasks require multiple agents collaborating
5. **Proactive + reactive** — some agents run on schedules (media agent checking for new releases), others respond to requests (research agent answering a question)
6. **One-person maintainable** — the framework must be debuggable, understandable, and not require a PhD in distributed systems
7. **Open scope** — new agent types must be addable without rearchitecting
8. **Local-first** — runs entirely on local hardware, no cloud dependency

---

## Candidates

### 1. LangGraph (LangChain ecosystem)

**GitHub:** LangGraph 10k+ stars, LangChain 100k+ | **Maintained by:** LangChain Inc.

LangGraph models agent workflows as directed graphs — nodes are actions, edges are transitions.

**Strengths:**
- Graph-based workflow gives explicit control over agent behavior
- Conditional branching, loops, parallel execution
- Built-in state management (in-thread memory via MemorySaver, cross-thread via stores)
- Native vLLM integration — `ChatOpenAI(base_url="http://localhost:8000/v1")` works out of the box
- Human-in-the-loop support (agent pauses for approval)
- LangChain ecosystem provides hundreds of tool integrations (web search, file ops, API calls)
- LangGraph Platform for deployment (or self-host with LangServe)
- Extensive documentation and examples

**Concerns:**
- LangChain dependency — LangChain is large, opinionated, and changes frequently
- Abstraction overhead — simple tasks require navigating multiple layers of abstraction
- Lock-in to LangChain ecosystem patterns
- Documentation can be overwhelming (too many options, not enough guidance on which to use)

**Sources:**
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangGraph + vLLM integration](https://medium.com/@dewasheesh.rana/building-high-performance-agentic-ai-with-vllm-and-langgraph-3f785380ef7c)
- [LangGraph agent framework page](https://www.langchain.com/langgraph)

### 2. CrewAI

**GitHub:** 25k+ stars | **Maintained by:** CrewAI Inc.

CrewAI models agents as a "crew" with roles, goals, and tasks. Role-based multi-agent collaboration.

**Strengths:**
- Intuitive mental model — define agents with roles ("researcher"), give them tasks, let them collaborate
- Built-in memory (short-term ChromaDB, long-term SQLite, entity memory)
- Process types: sequential (agents take turns) and hierarchical (manager delegates)
- vLLM support via LiteLLM under the hood — any OpenAI-compatible endpoint works
- Good documentation for getting started
- Lower learning curve than LangGraph

**Concerns:**
- Less control over execution flow than LangGraph's graph model
- Opinionated about agent structure — may not fit all use cases
- CrewAI Inc. pushes their hosted platform; open-source version may lag
- Tool integration is less rich than LangChain's ecosystem
- Memory implementation is less flexible than LangGraph's

**Sources:**
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [CrewAI local LLM setup](https://docs.crewai.com/en/learn/llm-connections)
- [CrewAI + vLLM community thread](https://community.crewai.com/t/crewai-and-openai-compatible-vllm-hosted-model/6674)

### 3. AutoGen (Microsoft)

**GitHub:** 40k+ stars | **Maintained by:** Microsoft Research

AutoGen treats agent interactions as conversations. Agents talk to each other.

**Strengths:**
- Conversational paradigm — agents naturally discuss and negotiate
- Flexible agent definitions
- Code execution built in (agents can write and run code)
- Microsoft backing, active research

**Concerns:**
- Conversation-heavy paradigm generates many inference calls — costly with local LLMs
- Recent architecture rewrite (AutoGen 0.4 → AG2) caused community fragmentation
- Less focused on production deployment than LangGraph/CrewAI
- Complex setup for multi-agent scenarios

**Sources:**
- [AutoGen GitHub](https://github.com/microsoft/autogen)
- [CrewAI vs LangGraph vs AutoGen (DataCamp)](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)

### 4. Custom (FastAPI + OpenAI client + state management)

Build a minimal agent framework from scratch using:
- FastAPI for the agent API
- `openai` Python client for vLLM calls
- PostgreSQL or SQLite for state/memory
- APScheduler or Celery for scheduled tasks

**Strengths:**
- Zero framework dependency — understand every line
- No abstraction overhead
- Exactly what's needed, nothing more
- Maximum control over tool calling, memory, scheduling

**Concerns:**
- Must build tool calling, memory, error handling, retry logic, conversation management from scratch
- No community examples to follow
- Higher initial development cost
- Risk of reinventing what frameworks already solve well

---

## Comparison

| Criterion | LangGraph | CrewAI | AutoGen | Custom |
|-----------|-----------|--------|---------|--------|
| vLLM integration | Native | Via LiteLLM | Yes | Direct |
| Tool ecosystem | Excellent (LangChain) | Good | Good | Build your own |
| Memory/state | Good (multiple stores) | Good (ChromaDB/SQLite) | Basic | Build your own |
| Multi-agent | Graph-based (explicit) | Role-based (intuitive) | Conversation-based | Build your own |
| Scheduling/proactive | Manual (+ APScheduler) | Manual (+ scheduler) | Manual | APScheduler/Celery |
| Learning curve | Medium-high | Medium | Medium-high | Low (but high build cost) |
| Flexibility | Very high | Medium | High | Maximum |
| One-person maintainable | Yes (with learning investment) | Yes | Questionable (rewrite churn) | Yes |
| Community size | Large | Large | Large (but fragmented) | N/A |

---

## The Real Question

All three major frameworks support vLLM, tool use, and multi-agent coordination. The differentiator is **how much control vs. convenience** Athanor needs:

- **LangGraph** gives the most control — explicit state machines, conditional branching, fine-grained tool execution. Best when agent behavior needs to be predictable and debuggable.
- **CrewAI** gives the most convenience — define roles and tasks, let the framework handle coordination. Best when agents have clear roles and straightforward collaboration patterns.
- **Custom** gives maximum simplicity — no framework learning curve, but higher build cost for features that frameworks provide.

Athanor's agents (from VISION.md) have clearly defined roles: research agent, media agent, home agent, creative agent, knowledge agent. This maps naturally to CrewAI's mental model. But agents also need conditional workflows (research agent decides whether to search the web, query local knowledge, or ask for clarification) — this maps to LangGraph's graph model.

---

## Recommendation

### LangGraph as the primary agent framework.

**Why LangGraph over CrewAI:**

1. **Graph-based control flow matches agent complexity.** Athanor's agents aren't just "do task and return result" — they branch, loop, call tools conditionally, and manage state across sessions. LangGraph's explicit state machines make this debuggable.

2. **vLLM integration is first-class.** `ChatOpenAI(base_url="http://localhost:8000/v1", model="meta-llama/...")` — done. No adapter layer, no translation.

3. **LangChain tool ecosystem.** Hundreds of pre-built tool integrations. Home Assistant, web search, file operations, API calls — LangGraph agents inherit all of these.

4. **Memory flexibility.** In-thread memory for conversations, cross-thread memory for persistent state. Custom stores for domain knowledge. This is critical for agents that need to remember what they've learned.

5. **Human-in-the-loop.** Some agent actions (media downloads, home automation changes, large inference jobs) should require approval. LangGraph has built-in support for pausing execution and waiting for human input.

6. **Open WebUI integration.** LangGraph agents can be exposed as OpenAI-compatible endpoints via LangServe, which means Open WebUI can chat with agents directly — the agent is just another "model" in the chat interface.

**Why not CrewAI:** CrewAI is simpler for straightforward multi-agent tasks, but its role-based paradigm is less flexible for the conditional, branching workflows Athanor's agents need. If an agent needs to decide at runtime which of 5 different paths to take based on intermediate results, LangGraph's graph model is more natural than CrewAI's sequential/hierarchical processes.

**Why not custom:** The features LangGraph provides (state management, tool calling, checkpointing, human-in-the-loop) would take weeks to build from scratch. The abstraction overhead is a worthwhile tradeoff for these capabilities.

**Why not AutoGen:** Architecture rewrite caused fragmentation. Conversation-heavy paradigm generates excessive inference calls with local LLMs where every token costs GPU cycles.

---

## Agent Architecture

```
Dashboard (Node 2)  ──→  Agent API Gateway (Node 2)  ──→  Agent Workers (Node 1)
                                                              │
                                                              ├── Research Agent
                                                              ├── Media Agent
                                                              ├── Home Agent
                                                              ├── Creative Agent
                                                              ├── Knowledge Agent
                                                              └── General Assistant
                                                              │
                                                              ▼
                                                         vLLM (Node 1:8000)
                                                         localhost — zero latency
```

Each agent is a LangGraph graph deployed as a Docker container on Node 1. Agents call vLLM on localhost:8000.

The API gateway on Node 2 routes dashboard requests to the appropriate agent on Node 1 over 5GbE. The payload is small JSON — latency is negligible.

**Proactive agents** (media agent, home agent) run on schedules via APScheduler within their containers. They check for new media, optimize automations, and report via the dashboard.

**Reactive agents** (research, general assistant) wait for requests from the dashboard or Open WebUI.

---

## Sources

- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangGraph + vLLM](https://medium.com/@dewasheesh.rana/building-high-performance-agentic-ai-with-vllm-and-langgraph-3f785380ef7c)
- [LangGraph agents in Open WebUI](https://medium.com/@davit_martirosyan/integrating-langgraph-agents-into-open-webui-3533cc3a47e1)
- [Top AI agent frameworks 2026 (Turing)](https://www.turing.com/resources/ai-agent-frameworks)
- [CrewAI vs LangGraph vs AutoGen (DataCamp)](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Agent framework comparison (Langwatch)](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more)
- [CrewAI local LLM setup](https://thinkpeak.ai/setting-up-crewai-with-local-llms/)
