# ADR-017: GWT-Inspired Meta-Orchestrator

**Date:** 2026-02-25
**Status:** Accepted
**Deciders:** Shaun, Claude

## Context

Athanor has 6 deployed agents that are entirely reactive -- they sit idle until a user explicitly calls them via API. No proactive behavior, no inter-agent coordination, no event-driven responses. Hardware utilization is ~10-27% despite full VRAM allocation. The system needs a meta-orchestration layer that enables proactive agent behavior, event-driven responses, and emergent multi-agent coordination.

## Options Evaluated

1. **Simple Cron/Queue** -- Scheduled jobs trigger specific agents on fixed intervals
2. **LangGraph Supervisor** -- Central supervisor node routes all requests to agents
3. **Event Bus (Kafka/RabbitMQ)** -- Pub/sub message broker for inter-agent communication
4. **GWT-Inspired Workspace** -- Shared workspace with competitive selection, modeled on Global Workspace Theory

## Decision

**Option 4: GWT-Inspired Workspace with competitive selection.**

A shared workspace (backed by Redis) where agents compete to broadcast information system-wide. Agents post candidates to the workspace, a selection cycle picks the most salient, and the winner is broadcast to all agents. This mirrors the cognitive architecture of Global Workspace Theory: many specialized processors competing for a limited-capacity global broadcast.

## Rationale

1. **Simple cron is too rigid.** Fixed schedules can't respond to emergent events or changing priorities. Adding a new trigger means editing crontabs, not extending the system.
2. **LangGraph supervisor is hub-spoke.** Every new interaction pattern requires explicit routing logic in the supervisor. The supervisor becomes a bottleneck and a single point of failure for coordination logic.
3. **Kafka/RabbitMQ is enterprise-scale infrastructure for a 7-agent system.** Zookeeper, brokers, partitions, consumer groups -- none of this complexity is justified at this scale.
4. **GWT provides emergent routing.** Agents self-select based on workspace content. New agents register and compete without rewriting orchestration logic. The capacity limit (7 items in the workspace) prevents overload naturally, mirroring the cognitive bottleneck that makes GWT effective.

### Why GWT specifically?

The key insight from Global Workspace Theory is that intelligence emerges not from central control but from competition for a shared broadcast medium. This maps directly to Athanor's architecture: specialized agents (like specialized brain modules) compete to have their information broadcast, and the broadcast itself triggers further processing by other agents. This creates emergent coordination without explicit orchestration.

## Implementation

### Phase 1: Foundation
- Deploy Redis on VAULT (single container, port 6379)
- Define workspace data model: `WorkspaceItem(id, source_agent, content, salience_score, timestamp, ttl)`
- Implement simple salience scoring (urgency x relevance x recency)
- Basic workspace API: post item, query workspace, clear expired items

### Phase 2: Competition Cycle
- 1Hz competition cycle: collect candidates from all agents, score, select top-7, broadcast winners
- Agent registration protocol: each agent declares capabilities, activation thresholds, subscription topics
- Redis pub/sub for broadcast notifications (agents subscribe to workspace changes)
- Event ingestion: Home Assistant events, cron triggers, API webhooks feed workspace items

### Phase 3: Coalition Formation
- Agents can endorse other agents' candidates (boosting salience)
- Multi-agent task decomposition: winning item triggers coordinated response from multiple agents
- Conflict resolution: when agents propose contradictory actions, workspace arbitrates via salience

### Phase 4: Experience Memory
- Learned salience priors: track which candidates led to successful outcomes
- Workspace history in Neo4j (graph of broadcast chains, agent interactions)
- Adaptive activation thresholds: agents that repeatedly lose competition reduce submission rate

## Consequences

### Positive
- System becomes proactive -- workspace drives continuous work without user prompting
- New agents plug in by registering capabilities; zero changes to existing orchestration
- Emergent coordination: agents that have never been explicitly connected can collaborate through workspace
- GPU utilization increases as agents proactively schedule work during idle periods

### Negative
- Adds Redis dependency (single container, ~50MB RAM, well-understood operationally)
- Agents need refactoring to support registration protocol and workspace subscription
- Proactive behavior needs guardrails to prevent runaway cycles or resource waste
- New debugging surface: workspace state, competition history, broadcast chains

### Observability
- `redis-cli monitor` for real-time workspace traffic
- Workspace API endpoints for dashboard visualization (current items, competition history)
- Prometheus metrics: competition cycle latency, broadcast rate, agent participation
- Dashboard integration: live workspace view showing active items and agent states
