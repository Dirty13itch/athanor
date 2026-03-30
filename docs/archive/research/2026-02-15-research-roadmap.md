# Athanor Research Roadmap

> Historical note: archived planning-era research roadmap. Dependency ordering, node naming, and implementation assumptions here are historical only.

The hardware audit is complete. This document maps every architectural decision
needed to go from "pile of parts" to "running system," ordered by dependency.

---

## Decision Map

Decisions are numbered by dependency order. Earlier decisions constrain later ones.
Each decision becomes an ADR in docs/decisions/ once research supports it.

```
ADR-001  Base Platform (OS + Workload Management)
  │
  ├── ADR-002  Network Architecture (5GbE fabric, VLANs, DNS, discovery)
  │
  ├── ADR-003  Storage Architecture (shared storage, model storage, NFS/local/distributed)
  │
  └── ADR-004  Node Roles + Hardware Allocation (what goes where, given 001-003)
         │
         ├── ADR-005  AI Inference Engine (vLLM, llama.cpp, Ollama, SGLang, etc.)
         │
         ├── ADR-006  Creative Pipeline (image gen, video gen, ComfyUI, etc.)
         │
         ├── ADR-007  Dashboard + Unified Interface (tech stack, design system)
         │
         ├── ADR-008  Agent Framework (orchestration, autonomy model, tool access)
         │
         └── ADR-009  Monitoring + Observability (metrics, logs, alerting)
                │
                ├── ADR-010  Home Automation Integration (HA, Lutron, UniFi)
                │
                ├── ADR-011  Media Stack (Plex, *arr, adult content management)
                │
                └── ADR-012+ Per-project architecture (EoBQ, Kindred, future)
```

## Research Order

| # | Topic | Research Doc | Depends On | Status |
|---|-------|-------------|------------|--------|
| 1 | Base Platform: OS + Workload Management | 2026-02-15-base-platform.md | Hardware inventory | **Complete** — recommends Ubuntu 24.04 + Docker Compose + Ansible |
| 2 | Network Architecture | 2026-02-15-network-architecture.md | ADR-001 | **Complete** — ADR-002 written. 5GbE switched + 56G InfiniBand direct link. |
| 3 | Storage Architecture | 2026-02-15-storage-architecture.md | ADR-001, ADR-002 | **Complete** — ADR-003 written. Three-tier NVMe/NFS, Hyper M.2 expansion for Node 1. |
| 4 | Node Roles + Hardware Allocation | 2026-02-15-node-roles.md | ADR-001, 002, 003 | **Complete** — ADR-004 written. Node 1=inference+agents, Node 2=creative+interactive, VAULT=storage+media+always-on. |
| 5 | AI Inference Engine | 2026-02-15-inference-engine.md | ADR-004 | **Complete** — ADR-005 written. vLLM primary, NVFP4 on Blackwell, SGLang on watch list. |
| 6 | Creative Pipeline | 2026-02-15-creative-pipeline.md | ADR-004 | **Complete** — ADR-006 written. ComfyUI on Node 2 (RTX 5090), Flux dev + Wan 2.2 14B, GPU isolation via Docker. |
| 7 | Dashboard + Unified Interface | 2026-02-15-dashboard.md | ADR-004 | **Complete** — ADR-007 written. Open WebUI for chat, custom Next.js + shadcn/ui dashboard for command center. |
| 8 | Agent Framework | 2026-02-15-agent-framework.md | ADR-005 | **Complete** — ADR-008 written. LangGraph orchestration, agents as Docker containers on Node 1. |
| 9 | Monitoring + Observability | 2026-02-15-monitoring.md | ADR-004 | **Complete** — ADR-009 written. Prometheus + Grafana on VAULT, DCGM-exporter for GPUs. |
| 10 | Home Automation | 2026-02-15-home-automation.md | ADR-001, ADR-007 | **Complete** — ADR-010 written. Home Assistant Docker on VAULT, Lutron + UniFi integrations. |
| 11 | Media Stack | 2026-02-15-media-stack.md | ADR-001, ADR-003 | **Complete** — ADR-011 written. Full media stack on VAULT, TRaSH Guides path structure, Stash for adult content. |

## Research Methodology

Each research topic follows this process:

1. **Define the question** — what exactly are we deciding?
2. **List candidates** — what are the real options? (not every option, just viable ones)
3. **Define criteria** — derived from Athanor's principles (one-person scale, open scope, practical over pure)
4. **Research each candidate** — current sources, not memory. Web search for anything AI-related or fast-moving.
5. **Document findings** — comparison matrix, trade-offs, sources cited
6. **Recommend** — or identify what needs a hands-on spike to resolve
7. **ADR** — when the recommendation is clear, write the decision record

### What counts as a source
- Official documentation
- Benchmarks (with methodology noted)
- GitHub repos (stars, commit activity, release cadence)
- Community experience (Reddit, HN, forums — noted as anecdotal)
- Datasheets and specs

### What doesn't count
- My own training data for fast-moving topics (AI tools, GPU compatibility)
- Blog posts without benchmarks or evidence
- Marketing materials
- "Everyone uses X" without understanding why

## Pace

One research topic per session or per few sessions, depending on depth.
No pressure to rush. A bad decision costs more than a slow one.
Some topics (inference engine, agent framework) may need hands-on spikes
after initial research — that's fine, note it in the research doc.

## Topics That May Not Need Full Research

Some decisions are nearly forced by constraints:

- **VAULT stays on Unraid** — non-negotiable per VISION.md
- **DEV stays as-is** — Windows 11 workstation, not a server
- **NVIDIA drivers required** — no alternative for CUDA inference
- **5GbE hardware exists** — the question is topology, not whether to use it

These get noted in the relevant ADRs without full research docs.
