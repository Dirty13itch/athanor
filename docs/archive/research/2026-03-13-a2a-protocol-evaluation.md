# A2A Protocol Evaluation for Athanor Multi-Agent System

**Date:** 2026-03-13
**Status:** Research Complete
**Author:** Research Agent
**Requested by:** Shaun
**Related:** ADR-008 (Agent Framework), ADR-017 (GWT Meta-Orchestrator), ADR-012 (LiteLLM Routing)

---

## Context

Athanor runs 9 LangGraph agents coordinated by a central agent server on FOUNDRY:9000, with LiteLLM on VAULT:4000 routing inference. The coordinator handles context injection, GWT workspace competition, trust scoring, task delegation, and scheduling. Agents communicate exclusively through the coordinator (hub-and-spoke). The question: should we adopt Google's Agent-to-Agent (A2A) protocol to enable direct agent-to-agent communication?

## 1. What Is A2A?

### Protocol Summary

A2A (Agent2Agent) is an open protocol for inter-agent communication, launched by Google at Cloud Next (April 2025), donated to the Linux Foundation (June 2025). Current version is **1.0.0** (not v0.9 as initially assumed -- v0.9 does not appear to exist publicly; the version progression was 0.1.0, 0.2.6, 0.3.0, 1.0.0). Backed by 150+ organizations including AWS, Microsoft, IBM, Salesforce.

### Transport & Wire Format

| Layer | Specification |
|-------|---------------|
| Transport | HTTP/HTTPS, gRPC (v0.3+) |
| Message format | JSON-RPC 2.0 |
| Streaming | Server-Sent Events (SSE) |
| Async | Webhook push notifications |

### Discovery: Agent Cards

Agents publish a JSON metadata document at `/.well-known/agent-card.json` containing:
- Agent identity (name, description, version)
- Service endpoint URL
- Supported capabilities (streaming, push, extended cards)
- Authentication requirements (API key, OAuth2, mTLS, OIDC)
- Skills list with structured metadata
- Optional cryptographic signature

A client agent fetches the card, identifies the best remote agent for its task, then sends JSON-RPC messages.

### Task Lifecycle

```
submitted → working → completed
                   → failed
                   → canceled
                   → rejected
         → input_required → (human/agent provides input) → working
         → auth_required → (auth provided) → working
```

### Security Model

Multi-layered:
- TLS/HTTPS for transport security
- Client auth: API keys, HTTP auth, OAuth2, mTLS, OIDC
- Authorization scoping per-resource
- In-task authorization for runtime permission decisions
- Agent card signing (v0.3+) for identity verification

### Key RPC Methods

- `message/send` -- send a message, get complete response
- `message/stream` -- send with SSE streaming
- `tasks/get` -- check task status/results

### A2A vs MCP

These are complementary, not competing:
- **MCP**: Agent-to-tool communication (how agents invoke tools, APIs, data sources)
- **A2A**: Agent-to-agent communication (how agents collaborate with each other)

Athanor already uses MCP extensively (13 MCP servers). A2A would add the inter-agent layer.

## 2. LiteLLM A2A Support

LiteLLM introduced A2A Agent Gateway in **v1.80.8-stable**. This is directly relevant because Athanor already runs LiteLLM on VAULT:4000.

### Integration Architecture

```
                    LiteLLM (VAULT:4000)
                    /a2a/{agent_name}/message/send
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
    Agent A (A2A)   Agent B (A2A)  Agent C (A2A)
```

### Two Integration Paths

**Path 1: Native A2A SDK**
```python
from a2a.client import A2AClient, A2ACardResolver

card = await A2ACardResolver().resolve("http://vault:4000")
client = A2AClient(card)
response = await client.send_message(
    SendMessageRequest(message=Message(role="user", parts=[TextPart(text="...")]))
)
```

**Path 2: LiteLLM built-in client**
```python
from litellm.a2a_protocol import A2AClient
client = A2AClient(base_url="http://vault:4000", api_key="...")
```

### What LiteLLM's A2A Gateway Provides

- Unified agent invocation across frameworks (LangGraph, Pydantic AI, Azure, Bedrock)
- Cost tracking per query and per-token pricing
- Request/response logging (integrates with LangFuse via existing setup)
- Team/key-based access control for agents
- Context header forwarding (`X-LiteLLM-Trace-Id`, `X-LiteLLM-Agent-Id`)

### Configuration

Agents are added via LiteLLM admin UI or config:
1. Navigate to Agents tab
2. Add agent name + invocation URL (e.g., `http://foundry:9000/agents/research`)

### Implication for Athanor

LiteLLM already runs on VAULT:4000. Adding A2A would mean LiteLLM becomes both the inference router AND the agent communication hub. This consolidates two routing planes into one service -- operationally simpler but increases VAULT's criticality.

## 3. LangGraph A2A Compatibility

### Official Support

LangGraph supports A2A natively since `langgraph-api>=0.4.21`.

**Requirements:**
- Agent state must include a `messages` key (Athanor agents already have this)
- A2A endpoint exposed at `/a2a/{assistant_id}`
- Agent cards auto-generated at `/.well-known/agent-card.json?assistant_id={id}`

**Supported RPC methods:**
- `message/send` -- synchronous
- `message/stream` -- SSE streaming
- `tasks/get` -- status polling

**LangSmith integration:** `contextId` auto-converts to `thread_id` for tracing.

**Disabling:** Set `"http": {"disable_a2a": true}` in `langgraph.json`.

### Athanor Compatibility Assessment

| Requirement | Athanor Status | Effort |
|-------------|---------------|--------|
| `messages` key in state | Already present | Zero |
| langgraph-api >= 0.4.21 | Needs version check | pip upgrade |
| Agent Card generation | Auto-generated by LangGraph | Zero |
| A2A endpoint exposure | New route per agent | Moderate |
| Multi-turn context | Already using thread_id | Low |

### Existing Templates

Multiple production-ready templates exist:
- `llmx-tech/a2a-template-langgraph` -- FastAPI + A2A + LangGraph
- `5enxia/langgraph-multiagent-with-a2a` -- Supervisor pattern over A2A
- `ruska-ai/a2a-langgraph` -- Minimal A2A wrapper

The supervisor pattern template is particularly relevant: it reimplements LangGraph's `langgraph-supervisor` using A2A, with the supervisor discovering sub-agents via `/.well-known/agent-card.json`.

## 4. Hub-and-Spoke vs Peer-to-Peer

### Academic Research

Google DeepMind's "Towards a Science of Scaling Agent Systems" (Kim et al., Dec 2025) is the definitive study. Key findings:

**5 architectures tested:** Single-Agent (SAS), Independent, Centralized (hub-and-spoke), Decentralized (peer-to-peer), Hybrid.

**Error amplification:**
| Topology | Error Amplification vs SAS |
|----------|--------------------------|
| Independent (no coordination) | 17.2x |
| Centralized (hub-and-spoke) | 4.4x |
| Decentralized (peer-to-peer) | Between, varies |

**Agent count thresholds:**
- **4 agents:** Structured topology becomes necessary. Below 4, any topology works.
- **16-32 agents:** Peer-to-peer mesh starts showing emergent performance gains (sigmoid scaling inflection point).
- **45% SAS baseline:** Multi-agent coordination only improves over single-agent if the single-agent baseline accuracy is below ~45%. Above that, adding agents provides diminishing returns.

**Task structure determines optimal topology:**
- **Parallelizable tasks:** Centralized achieved +81% improvement over single-agent (Finance-Agent benchmark)
- **Sequential tasks:** ALL multi-agent variants degraded by 39-70% (PlanCraft benchmark)

**Predictive model:** 87% accuracy predicting optimal architecture from task properties (tool count, decomposability).

### What This Means for Athanor's 9 Agents

Athanor has 9 agents. This is in the range (4-16) where:
- Hub-and-spoke is the established best default
- Peer-to-peer gains have not yet emerged
- The coordinator's error containment (4.4x vs 17.2x) is actively valuable
- Adding A2A peer-to-peer would increase communication complexity without crossing the threshold where mesh benefits materialize

**The research is clear: at 9 agents, hub-and-spoke wins.** The crossover to peer-to-peer advantages is at 16-32 agents, which Athanor is unlikely to reach (one-person system, bounded complexity).

### Athanor-Specific Topology Analysis

```
Current (Hub-and-Spoke):
                     Coordinator
                    /  |  |  |  \
                  GA  R  M  H  Cr  K  Co  St  DC

Communication paths: 9 (coordinator ↔ each agent)
Error containment: Coordinator validates all delegation

Hypothetical A2A Mesh:
        GA ←→ R ←→ M ←→ H
        ↕     ↕    ↕    ↕
        Cr ←→ K ←→ Co ←→ St ←→ DC

Communication paths: Up to 36 (9 choose 2)
Error containment: None — each agent makes independent routing decisions
```

The 36 potential communication paths vs 9 is a 4x increase in coordination surface area. For a system with 9 agents, this is all cost and no benefit.

## 5. Practical Test Design

If we were to test A2A despite the topology analysis suggesting against it, here is how to do it rigorously.

### A/B Test Architecture

```
Mode A (current):  User → Coordinator → Agent → Coordinator → User
Mode B (A2A):      User → Coordinator → Agent ←A2A→ Agent → Coordinator → User
```

Note: Mode B still uses the coordinator as entry/exit point, but allows agents to discover and invoke each other directly for sub-tasks.

### Metrics

| Metric | How to Measure | Expected Signal |
|--------|----------------|-----------------|
| End-to-end latency | LangFuse trace duration | A2A adds 1 HTTP hop per inter-agent call |
| Task completion rate | Success/failure ratio per task type | Should be equivalent if routing is correct |
| Agent coordination overhead | Total inference tokens per task | A2A may increase (discovery + negotiation) |
| Error propagation | Failed sub-task cascade depth | Hub-and-spoke should contain better |
| Context consistency | Manual audit of 20 task traces | Coordinator ensures shared context |
| LangFuse trace completeness | Missing spans per task | A2A may break trace chains |
| Cost per task | LiteLLM cost tracking | Token overhead from A2A negotiation |

### Test Protocol

1. Select 50 representative tasks across all 9 agents (historical from LangFuse)
2. Run each task in both modes (randomized order)
3. Measure all metrics above
4. Statistical comparison (paired t-test on latency, chi-squared on completion rate)
5. Qualitative review of 10 failure cases per mode

### Minimum Viable Test

Before the full A/B test, a simpler proof-of-concept:
1. Add A2A endpoint to Research Agent only
2. Give Coding Agent an A2A client for Research
3. Test: "Write a Python function that implements the algorithm from paper X"
4. Compare: Coding → coordinator → Research vs Coding →A2A→ Research
5. Measure latency delta and trace completeness

## 6. Implementation Effort

### Scope: A2A Discovery Layer (Coordinator Fallback)

| Work Item | Effort | Risk |
|-----------|--------|------|
| Upgrade langgraph-api to >= 0.4.21 | 1 hour | Low -- pip upgrade, test |
| Add A2A endpoint to each agent | 1 day | Low -- LangGraph auto-generates |
| Configure Agent Cards for 9 agents | 2 hours | Low -- JSON metadata |
| Register agents in LiteLLM A2A gateway | 2 hours | Low -- UI or config |
| Modify `delegate_to_agent()` to try A2A first | 1 day | Medium -- fallback logic |
| Add A2A client to delegation tools | 1 day | Medium -- new dependency |
| Preserve LangFuse trace continuity | 2 days | High -- header forwarding, span linking |
| Context injection for A2A-invoked agents | 2 days | High -- bypass coordinator context pipeline |
| Update GWT workspace for A2A broadcasts | 1 day | Medium -- broadcast path changes |
| Integration testing (9 agents x A2A) | 2 days | Medium -- combinatorial surface |
| Monitoring/alerting for A2A communication | 1 day | Low -- Prometheus metrics |
| Documentation update | 0.5 day | Low |

**Total estimated effort: 11-12 days**

### Critical Path Items

1. **LangFuse trace continuity** -- The `X-LiteLLM-Trace-Id` and `X-LiteLLM-Agent-Id` headers must propagate through A2A calls, or traces break. This is the hardest part.
2. **Context injection** -- Currently, the coordinator runs context injection (knowledge retrieval, workspace state, preferences) before invoking any agent. If Agent A calls Agent B directly via A2A, Agent B doesn't get this context. This fundamentally changes the information flow.

## 7. Risks: What Breaks If Agents Bypass the Coordinator

This is the critical section. The coordinator is not just a router -- it provides essential services that break if bypassed.

### 7.1 Context Injection Pipeline

**Current flow:**
```
User message → Coordinator
  → Embedding (30ms)
  → 4 parallel Qdrant queries (preferences, activity, knowledge, personal_data)
  → Redis goals fetch
  → Graph expansion (Neo4j)
  → Enriched context → Agent
```

**With A2A bypass:**
Agent A calls Agent B directly. Agent B gets raw text with zero context enrichment. No knowledge retrieval, no preference awareness, no activity history.

**Fix difficulty:** HIGH. Would need to duplicate or extract the context pipeline into a shared service callable by any agent. ~3 days additional work.

### 7.2 GWT Workspace & Competition

The GWT workspace (ADR-017) relies on the coordinator running competition cycles:
- Specialists evaluate salience
- Softmax selection picks winner
- Winner is broadcast to all agents
- CST (Continuous State Tensor) is updated

If agents delegate directly via A2A, the workspace doesn't see these interactions. The competition cycle loses visibility into what agents are doing, breaking the salience model.

**Fix difficulty:** MEDIUM. Agents could post to workspace after A2A interactions, but this is a retroactive notification, not a pre-delegation competition.

### 7.3 Ordering & Deduplication

The coordinator serializes task execution. If Research Agent and Knowledge Agent both receive the same query (one via coordinator, one via A2A from General Assistant), there is no dedup mechanism. Two identical inference calls burn tokens.

**Fix difficulty:** MEDIUM. Redis-based dedup key (hash of prompt + agent) with TTL.

### 7.4 LangFuse Tracing

Current tracing chain:
```
Trace: user-request-123
  └── Span: coordinator
       └── Span: research-agent
            └── Span: llm-call (via LiteLLM)
```

With A2A bypass:
```
Trace: user-request-123
  └── Span: coordinator
       └── Span: coding-agent
            └── (A2A call to research-agent -- different trace?)
                 └── Span: research-agent (new trace? orphaned?)
                      └── Span: llm-call
```

LiteLLM's `X-LiteLLM-Trace-Id` header forwarding helps, but requires every A2A call to explicitly propagate headers. One missed propagation = orphaned traces.

**Fix difficulty:** HIGH. Requires discipline in every A2A call site + monitoring for orphaned traces.

### 7.5 Trust Scoring & Rate Limiting

The coordinator enforces trust levels (CONSTITUTION.yaml) and rate limits. A2A bypass means:
- No trust check before agent invocation
- No rate limiting on inter-agent calls
- Potential for runaway delegation loops (Agent A calls B, B calls A)

**Fix difficulty:** MEDIUM. Circuit breaker pattern (already in `circuit_breaker.py`) needs extension to A2A calls.

### 7.6 Scheduling & Priority

The coordinator manages task queues with priority. A2A calls bypass the queue entirely -- an A2A request from one agent pre-empts scheduled work.

**Fix difficulty:** LOW. A2A calls can be treated as normal priority.

### 7.7 Audit Trail

All coordinator-mediated tasks are logged to Redis activity streams and Qdrant activity collection. A2A direct calls bypass this logging.

**Fix difficulty:** LOW. Middleware on A2A endpoints logs to same stores.

## 8. Recommendation

### Verdict: Do Not Implement A2A for Athanor

The honest assessment, based on the evidence:

**A2A solves the wrong problem for Athanor.** A2A is designed for cross-organizational, cross-framework, multi-vendor agent interoperability. Athanor has 9 agents, all written in the same framework (LangGraph), all running on the same server (FOUNDRY:9000), all using the same inference backend (LiteLLM), all owned by one person.

**The topology research is unambiguous.** At 9 agents, hub-and-spoke outperforms peer-to-peer. The crossover is at 16-32 agents. Athanor will not reach 16 agents -- one-person systems have bounded complexity.

**The coordinator provides irreplaceable services.** Context injection, GWT workspace, trust scoring, tracing, scheduling, and dedup all depend on the coordinator mediating every interaction. Bypassing it breaks 6 of 7 operational guarantees.

**The cost-benefit is negative:**
- Cost: 11-12 days implementation + ongoing maintenance of two communication patterns
- Benefit: Agents can call each other directly for... what? The coordinator already delegates efficiently. The only scenario where direct A2A helps is when Agent A discovers mid-task that it needs Agent B -- but `delegate_to_agent()` already handles this through the coordinator with <100ms overhead.

**LiteLLM A2A Gateway is interesting but premature.** When/if Athanor needs to integrate external agents (e.g., a friend's agent, a commercial service), A2A through LiteLLM becomes relevant. That is not the current need.

### When to Revisit

Re-evaluate A2A if any of these become true:
1. **Agent count exceeds 15** -- approaching the mesh benefit threshold
2. **External agents need integration** -- agents from different owners/frameworks
3. **Cross-node agent distribution** -- agents spread across FOUNDRY + WORKSHOP + DEV with independent lifecycles
4. **Coordinator becomes a measured bottleneck** -- latency > 500ms for delegation (currently <100ms)
5. **LiteLLM A2A Gateway matures** -- cost tracking + tracing are production-stable (currently v1.80.8 introduced it; give it 6+ months)

### What to Do Instead

1. **Keep improving the coordinator.** The GWT workspace, specialist competition, and context injection pipeline are the right architecture for 9 agents.
2. **Monitor delegation latency.** Add a Grafana panel for coordinator delegation latency. If it crosses 200ms consistently, revisit.
3. **Watch A2A maturity.** The protocol is at 1.0.0, the LiteLLM integration is brand new, and the ICLR 2026 security paper found 100% attack success rates on current A2A deployments. Let the ecosystem harden.
4. **Upgrade langgraph-api anyway.** Getting to >= 0.4.21 is free and prepares for A2A if needed later. The A2A endpoint can be disabled via config (`disable_a2a: true`).

## 9. Sources

### A2A Protocol
- [A2A Protocol Specification v1.0.0](https://a2a-protocol.org/latest/specification/)
- [Google Developers Blog: A2A Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [Google Cloud Blog: A2A Protocol Upgrade (v0.3)](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade)

### LiteLLM Integration
- [LiteLLM A2A Agent Gateway Docs](https://docs.litellm.ai/docs/a2a)
- [LiteLLM v1.80.8 Release Notes (A2A Introduction)](https://docs.litellm.ai/release_notes/v1-80-8)

### LangGraph Compatibility
- [LangChain A2A Endpoint in Agent Server](https://docs.langchain.com/langsmith/server-a2a)
- [LangGraph + A2A Tutorial (IBM/watsonx)](https://heidloff.net/article/a2a-langgraph-watsonx-ai/)
- [A2A Template for LangGraph (GitHub)](https://github.com/llmx-tech/a2a-template-langgraph)
- [LangGraph Supervisor + A2A (GitHub)](https://github.com/5enxia/langgraph-multiagent-with-a2a)

### Topology Research
- [Google DeepMind: Towards a Science of Scaling Agent Systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)
- [MIT Media Lab: Agent Scaling Project](https://www.media.mit.edu/projects/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/overview/)
- [Towards Data Science: 17x Error Trap](https://towardsdatascience.com/why-your-multi-agent-system-is-failing-escaping-the-17x-error-trap-of-the-bag-of-agents/)
- [Multi-Agent Orchestration: Enterprise Strategy 2025-2026](https://www.onabout.ai/p/mastering-multi-agent-orchestration-architectures-patterns-roi-benchmarks-for-2025-2026)

### Protocol Comparison
- [Survey: MCP, ACP, A2A, ANP Protocols (arXiv)](https://arxiv.org/html/2505.02279v1)
- [ProtocolBench: Which LLM Multi-Agent Protocol to Choose? (OpenReview)](https://openreview.net/pdf/69a333bc7563ad96f0c2c1cdd6fd07ba8d4c11ac.pdf)
- [A2ASECBENCH: Security Benchmark (ICLR 2026)](https://openreview.net/pdf/cbf9372232d6c3383d426389d44c490277480d16.pdf)
- [Auth0: MCP vs A2A Guide](https://auth0.com/blog/mcp-vs-a2a/)
- [IBM: A2A Protocol Overview](https://www.ibm.com/think/topics/agent2agent-protocol)

### Self-Hosted Experiences
- [IBM Tutorial: A2A with BeeAI + Ollama](https://www.ibm.com/think/tutorials/use-a2a-protocol-for-ai-agent-communication)
- [Oracle: Multi-Agent RAG with A2A](https://blogs.oracle.com/developers/build-a-scalable-multi-agent-rag-system-with-a2a-protocol-and-langchain)
- [HuggingFace: A2A Protocol Explained](https://huggingface.co/blog/1bo/a2a-protocol-explained)

---

*Last updated: 2026-03-13*
