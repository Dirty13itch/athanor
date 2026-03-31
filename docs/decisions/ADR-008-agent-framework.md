# ADR-008: Agent Framework

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/archive/research/2026-02-15-agent-framework.md](../archive/research/2026-02-15-agent-framework.md)
**Depends on:** ADR-005 (Inference Engine)

---

## Context

VISION.md describes AI agents as what makes Athanor "more than a homelab." Agents do real work — research, media management, home automation, creative generation, knowledge organization. They need to call vLLM for inference, use external tools (APIs, file systems, web search), maintain persistent memory, and coordinate with each other. Some run proactively on schedules, others respond to requests.

Four frameworks were evaluated: LangGraph, CrewAI, AutoGen, and building custom. The evaluation focused on: vLLM integration, tool calling, memory/state management, multi-agent coordination, scheduling support, and one-person maintainability.

---

## Decision

### LangGraph as the agent orchestration framework.

LangGraph models agent behavior as directed graphs — nodes are actions (LLM calls, tool use, decisions), edges are transitions (conditional or unconditional). This gives explicit, debuggable control over agent workflows while leveraging LangChain's extensive tool ecosystem.

#### Why LangGraph

1. **Explicit control flow.** Agents aren't black boxes — the graph defines exactly what happens at each step. When an agent misbehaves, you can trace the graph execution.

2. **Native vLLM integration.** `ChatOpenAI(base_url="http://localhost:8000/v1")` connects to any vLLM instance. No adapters.

3. **Tool ecosystem.** LangChain provides integrations for web search, file operations, HTTP APIs, databases, and more. Athanor's agents need to call Plex, Home Assistant, ComfyUI, *arr APIs, and web search — LangChain has tools for most of these.

4. **Persistent memory.** In-thread memory (conversation context) and cross-thread memory (knowledge that persists across sessions). Custom stores for domain-specific data.

5. **Human-in-the-loop.** Some agent actions (downloads, purchases, automation changes) should require approval. LangGraph supports pausing execution for human input.

6. **Open WebUI compatibility.** LangGraph agents can be exposed as OpenAI-compatible endpoints, making them appear as "models" in Open WebUI. Chat with any agent through the same interface.

#### Deployment

```
Node 1 (Core):
  ├── vLLM (port 8000)          ← LLM inference
  ├── Agent Supervisor (port 9000) ← Routes requests to agents
  ├── Research Agent             ← Web search, document analysis
  ├── Media Agent                ← Plex, *arr, Stash integration
  ├── Home Agent                 ← Home Assistant automation
  ├── Creative Agent             ← ComfyUI job submission
  ├── Knowledge Agent            ← Local knowledge base queries
  └── General Assistant          ← Uncensored chat, general tasks

Node 2 (Interface):
  └── Agent API Gateway (port 9001) ← Proxies dashboard → Node 1 agents
```

All agents run as Docker containers on Node 1. They call vLLM on `localhost:8000` — zero network latency for the thousands of inference calls agents make per task.

The API gateway on Node 2 is a thin FastAPI proxy that routes dashboard requests to the appropriate agent on Node 1 over 5GbE.

#### Agent Definitions

Each agent is a LangGraph graph with:
- **System prompt** — defines the agent's role, capabilities, and constraints
- **Tools** — the APIs and functions the agent can call
- **State schema** — what the agent tracks across steps
- **Memory store** — persistent knowledge

Example structure:
```python
# agents/research/graph.py
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-3.1-70B-Instruct",
)

# Define the graph
graph = StateGraph(ResearchState)
graph.add_node("plan", plan_research)
graph.add_node("search", web_search)
graph.add_node("analyze", analyze_results)
graph.add_node("report", generate_report)
graph.add_edge("plan", "search")
graph.add_conditional_edges("search", should_search_more)
graph.add_edge("analyze", "report")
```

#### Scheduling

Proactive agents use APScheduler within their containers:

| Agent | Schedule | Action |
|-------|----------|--------|
| Media Agent | Every 15 min | Check *arr for new downloads, update library |
| Home Agent | Every 5 min | Check HA status, optimize automations |
| Knowledge Agent | Daily at 3 AM | Index new documents, update embeddings |

Reactive agents (Research, General Assistant, Creative) wait for requests.

---

## What This Enables

- **Research agent** — ask a question, get a researched answer with sources from web search and local knowledge
- **Media agent** — "download the latest season of X" → agent calls Sonarr/Radarr, monitors progress, notifies when done
- **Home agent** — "optimize the lighting schedule" → agent queries HA, analyzes patterns, suggests (or applies) changes
- **Creative agent** — "generate character portraits for EoBQ" → agent submits ComfyUI workflows, collects results
- **Knowledge agent** — "what did I bookmark about X?" → agent searches local knowledge base, bookmarks, notes
- **General assistant** — uncensored local chat for any question, not limited by cloud AI guardrails
- **New agents** — add a new graph file, register it with the supervisor. No rearchitecting.

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| CrewAI | Simpler mental model (roles + tasks), but less control over conditional workflows. Athanor's agents need branching, looping, and runtime decisions that CrewAI's sequential/hierarchical processes don't handle as naturally. |
| AutoGen | Architecture rewrite (0.4 → AG2) fragmented the community. Conversation-heavy paradigm generates excessive inference calls — costly with local LLMs. |
| Custom (FastAPI + OpenAI client) | Maximum control but must build tool calling, memory, checkpointing, and human-in-the-loop from scratch. LangGraph provides these out of the box. The abstraction overhead is worth the development time savings. |
| No framework (vLLM function calling only) | vLLM supports tool calling natively, but there's no state management, no memory, no orchestration. Agents need more than raw function calling. |

---

## Risks

- **LangChain ecosystem churn.** LangChain moves fast and sometimes introduces breaking changes. Mitigated by pinning versions in Docker and testing upgrades before deploying.
- **Abstraction overhead.** LangGraph's graph model adds complexity that simple scripts don't need. Mitigated by keeping agent graphs simple — most agents are 3-5 nodes, not 50. Start simple, add complexity only when needed.
- **Local LLM agent quality.** Agents are only as good as the underlying LLM. A 70B model may not match GPT-4 for complex reasoning tasks. Mitigated by: using the best available local models, designing agents with explicit tool use (reduce reasoning burden), and falling back to cloud APIs for tasks that require it (pragmatism over dogma).
- **Memory management.** Persistent memory across sessions requires a storage backend. Start simple (SQLite), migrate to PostgreSQL if complexity grows.

---

## Implementation Order

1. **Deploy LangGraph with a single agent** — General Assistant with vLLM on Node 1
2. **Add tool calling** — web search, file operations
3. **Expose as OpenAI endpoint** — integrate with Open WebUI
4. **Add Research Agent** — web search + local knowledge
5. **Add Media Agent** — *arr API integration + scheduling
6. **Add Home Agent** — Home Assistant API integration
7. **Add Creative Agent** — ComfyUI API integration
8. **Add Knowledge Agent** — document indexing, bookmark search
9. **Refine and iterate** — new agents as needs emerge

---

## Sources

- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangGraph + vLLM integration guide](https://medium.com/@dewasheesh.rana/building-high-performance-agentic-ai-with-vllm-and-langgraph-3f785380ef7c)
- [LangGraph agents in Open WebUI](https://medium.com/@davit_martirosyan/integrating-langgraph-agents-into-open-webui-3533cc3a47e1)
- [Agent framework comparison 2026 (Turing)](https://www.turing.com/resources/ai-agent-frameworks)
- [CrewAI vs LangGraph vs AutoGen (DataCamp)](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [CrewAI vLLM support](https://community.crewai.com/t/crewai-and-openai-compatible-vllm-hosted-model/6674)
