# Athanor Operations Center

## What This Is

5 repos, one sovereign AI system. Athanor is deployed and running. Everything else is reference.

```
~/repos/
├── athanor/              ← THE LIVING SYSTEM. All changes go here.
├── reference/
│   ├── hydra/            ← Parts warehouse: 66 MCP tools, 41 n8n workflows, routellm, preference_learning
│   ├── kaizen/           ← Research artifact: GWT workspace manager (558 lines), salience scoring
│   ├── local-system/     ← Design docs: CLAUDE.md, VISION.md, STRUCTURE.md
│   └── system-bible/     ← Locked hardware decisions
```

## Cluster Topology

| Node | Hostname | IP | Hardware | GPU | Role |
|------|----------|----|----------|-----|------|
| FOUNDRY | foundry | .244 | EPYC 7663, 224GB DDR4 | 4×5070Ti (TP=4) + 4090 | Coordinator :8000, Utility :8001 |
| WORKSHOP | workshop | .225 | TR 7960X, 128GB DDR5 | 5090 + 5060Ti | Worker :8100, Fallback :8101 |
| VAULT | vault | .203 | 9950X, 128GB DDR5, Unraid | A380 (Plex) | LiteLLM :4000, LangFuse :3030, services |
| DESK | desk | .215 | i7-13700K, 64GB DDR5, Win11 | RTX 3060 | Workstation |
| DEV | dev | TBD | Ryzen 9 9900X, 64GB DDR5 | RTX 5060Ti | Ops center (you are here) |

All nodes 5GbE SFP+. SSH from DEV to all nodes configured.

## Development Tools

Four tools, specific roles. All managed via claude-squad for parallel sessions.

| Tool | Backend | Role |
|------|---------|------|
| Claude Code | Anthropic API (Sonnet 4.6) | Complex architecture, multi-file porting, hard reasoning |
| Aider | LiteLLM → local Qwen3.5 | Pair programming, test-fix loops, single-file, routine work |
| Goose | LiteLLM → local Qwen3.5 | Reproducible Recipes, scheduled overnight ops, infrastructure automation |
| claude-squad | Session manager | Parallel git worktrees, auto-accept overnight, manages all above |

## Stack

- Inference: vLLM (nightly for Qwen3.5, v0.16.0 stable on FOUNDRY)
- Routing: LiteLLM on VAULT:4000 (contract-driven slots: Reasoning, Fast Agent, Utility, Embed, TTS, STT)
- Orchestration: LangGraph + FastAPI on FOUNDRY:9000
- Agents: 8 live (General Assistant, Research, Media, Home, Creative, Knowledge, Coding, Stash)
- Storage: Qdrant (5 collections), Neo4j (43 relationships), Redis (state/cache/pubsub)
- Monitoring: Prometheus + Grafana + Loki + Grafana Alloy
- Deployment: Ansible roles at ansible/roles/

## Critical Rules

- NEVER modify FOUNDRY configs without explicit approval — it's production.
- Test on DEV → deploy to WORKSHOP → only then consider FOUNDRY.
- Qwen3.5 models require `--tool-call-parser qwen3_coder` (NOT hermes).
- BF16 KV cache only (`--kv-cache-dtype auto`). FP8 KV corrupts Qwen3.5 GDN layers.
- `--max-num-batched-tokens 2096` required for Qwen3.5 hybrid attention.
- Deploy via Ansible, not manual SSH. Playbooks are the source of truth.
- Prompts live in /agents/. Never inline prompts in code.
- Don't rebuild what works. Upgrade it. Let it compound.
