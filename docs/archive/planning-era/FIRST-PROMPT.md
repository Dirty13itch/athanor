Read these files in order. They represent months of iterative design across 5 repos, a 10+ hour deep planning session, and live cluster verification. Read them completely before responding.

1. ~/repos/ATHANOR-MAP.md — Single source of truth. 16 original sections + Sections 17-21 appended tonight: verified cluster state, mobile ops stack (Open WebUI + Grafana + LangFuse + Termux/Mosh), bleeding-edge tools evaluated, three-agent cognitive architecture (Prometheus/Worker Pool/Sentinel), and corrected 4-week sprint plan.

2. ~/repos/DEEP-RESEARCH-LIST.md — 73 research items across 14 categories with priority tiers. Items marked with checkmarks were resolved during the planning session.

3. ~/repos/athanor/ — THE LIVING SYSTEM. Read in order: docs/VISION.md, docs/SYSTEM-SPEC.md, CLAUDE.md, AGENTS.md, MEMORY.md. Then scan the full directory tree to understand what's actually deployed vs planned.

4. ~/repos/reference/hydra/ — Parts warehouse (READ ONLY, never modify). 66 MCP tools, 41 n8n workflows, Python modules to port one at a time: routellm, preference_learning, self_diagnosis, resource_optimization, knowledge_optimization, capability_expansion.

5. ~/repos/reference/kaizen/ — Research artifact (READ ONLY). 558-line GWT workspace manager, salience scoring.

6. ~/repos/reference/local-system/ — Newest design docs (READ ONLY). CLAUDE.md has the confidence-based escalation protocol.

7. ~/repos/reference/system-bible/ — Locked hardware decisions (READ ONLY).

VERIFIED CLUSTER STATE (live, March 7 2026 ~3:00 PM CT, verified via SSH from this machine):

FOUNDRY (.244, user: athanor) — SSH OK. 4x RTX 5070Ti + RTX 4090. vLLM serving on :8000 (Qwen3-32B-AWQ TP=4). Port :8001 closed (utility slot empty, future Qwen3.5-9B).

WORKSHOP (.225, user: athanor) — SSH OK. RTX 5090 + RTX 5060Ti. Dashboard on :3001. Ports :8100 and :8101 CLOSED — zero vLLM processes, 5090 is 99% idle. THIS IS THE WEEK 1 TARGET for Qwen3.5-35B-A3B-AWQ.

VAULT (.203, user: root) — SSH OK. LiteLLM on :4000, Qdrant on :6333, Redis on :6379. LangFuse :3030 NOT YET deployed. Open WebUI :3080 NOT YET deployed. Both are Week 1 deploys.

DEV (.189, user: shaun, this machine) — RTX 5060Ti, 5GbE NIC, Ubuntu 24.04. SSH to all nodes confirmed. Claude Code, Aider, Goose, claude-squad installed. Mosh installed. SSH config corrected with proper usernames and both keys (id_ed25519 + athanor_mgmt).

WHAT'S ALREADY DONE TONIGHT (Week 0 — complete):
- DEV bootstrapped with all 4 dev tools + configs
- All repos cloned (athanor + hydra + kaizen + local-system + system-bible)
- SSH connectivity verified to all nodes with correct users
- SSH config fixed with correct usernames (athanor for FOUNDRY/WORKSHOP, root for VAULT)
- athanor_mgmt key copied from DESK
- Mosh installed for mobile access
- ATHANOR-MAP.md updated with Sections 17-21 (addendum)

After reading everything, produce three things:

FIRST — A conflict report: where does ATHANOR-MAP.md disagree with the actual codebase in ~/repos/athanor/? The map was designed in a planning conversation without seeing source code. Where reality differs from the map, reality wins. Be specific — file paths, config values, service names.

SECOND — A gap assessment: what does the actual codebase have that the map doesn't mention? What does the map plan that has no corresponding code yet? This tells us what exists to build on vs what needs to be created from scratch.

THIRD — The Week 1 action list, in execution order. Week 0 items are DONE. Week 1 starts now:
  1. Deploy Open WebUI on VAULT — single Docker container connecting to LiteLLM :4000 + Qdrant :6333 (exact docker run command in Section 18 of the map)
  2. Deploy LangFuse v3 on VAULT — 6-service Docker Compose (web, worker, PostgreSQL, ClickHouse, Redis, MinIO). Config exists in the observability/ directory.
  3. Install vLLM v0.17.0 on WORKSHOP — new Python venv, do NOT touch existing v0.16.0 install
  4. Download cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit to WORKSHOP (~22GB)
  5. Serve on RTX 5090 :8100 with flags: --tool-call-parser qwen3_coder --kv-cache-dtype auto --enable-auto-tool-choice --enable-prefix-caching --max-model-len 131072
  6. Update LiteLLM config on VAULT to add worker model slot pointing to workshop:8100
  7. Configure LiteLLM success_callback for LangFuse integration
  8. Run test harness (~/repos/athanor/tests/harness.py or equivalent) — 100 requests across categories
  9. Verify Open WebUI can reach the new model via LiteLLM
  10. Install claude-tmux on DEV for visual session management

CRITICAL RULES — these are non-negotiable engineering constraints from deep research:
- FOUNDRY is production. Do NOT SSH in, modify, or restart anything without my explicit approval.
- Qwen3.5 models require vLLM v0.17.0 — v0.16.0 throws "Qwen3_5MoeForConditionalGeneration not supported". v0.18.0 does NOT exist yet.
- --kv-cache-dtype MUST be "auto" not "fp8" — FP8 KV cache causes silent corruption of GDN (Gated DeltaNet) layers in Qwen3.5's hybrid architecture.
- --tool-call-parser MUST be "qwen3_coder" not "hermes" — Qwen3.5 uses XML tool format.
- Speculative decoding: use MTP-1 (--speculative-config '{"method": "mtp", "num_speculative_tokens": 1}'), NOT draft models. Draft-model spec decoding is broken in vLLM V1.
- Don't rebuild what works. Upgrade it. Let it compound. This system has been through 4 rebuilds — no more.
- The 8 existing agents have real domain integrations (Sonarr/Radarr, Home Assistant, Stash GraphQL). Don't consolidate them. Enhance them.
- Hydra is a parts warehouse. Port modules one at a time into the athanor repo. Don't restructure athanor to match hydra.
- Right over fast. Each layer verified solid before building the next.

Do NOT make any changes to any node yet. Assess first. Present your three reports, then wait for my approval before executing anything.
