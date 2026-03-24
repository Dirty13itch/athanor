# Phase 0 — Discovery Ground Truth

*Generated: 2026-03-14 | HEAD: b1d1ded | Branch: main*

---

## 1. Repository Structure

- **Total files:** 1,137 (excluding .git, node_modules, __pycache__)
- **Commits:** 359 on main
- **Contributors:** Shaun (various names: 306 total), Claude (13)

### Top-level directories
| Dir | Files | Disk |
|-----|-------|------|
| projects/ | 593 | 28M |
| docs/ | 238 | 5.1M |
| ansible/ | 99 | 896K |
| scripts/ | 87 | 728K |
| services/ | 25 | 176K |
| tests/ | 5 | 160K |
| assets/ | 6 | 8.8M |
| evals/ | 12 | 3.9M |
| recipes/ | 2 | 12K |

### File types (top 15)
| Ext | Count |
|-----|-------|
| .md | 274 |
| .tsx | 212 |
| .ts | 211 |
| .py | 132 |
| .yml | 85 |
| .json | 57 |
| .sh | 34 |
| .png | 32 |
| .j2 | 22 |
| .ps1 | 13 |
| .yaml | 12 |
| .mjs | 6 |
| .svg | 5 |
| .toml | 3 |
| .service | 3 |

### LOC Summary
| Language | Files | LOC |
|----------|-------|-----|
| Python | 132 | 39,558 |
| TypeScript/TSX | 423 | 50,105 |
| YAML/YML | 97 | — |
| Markdown | 274 | — |
| Shell | 34 | — |
| **Total estimated** | **1,137** | **~90K+** |

---

## 2. Largest Files by LOC

### Python (top 15)
| File | LOC |
|------|-----|
| projects/agents/src/athanor_agents/server.py | 2,533 |
| projects/agents/src/athanor_agents/workspace.py | 864 |
| scripts/index-knowledge.py | 807 |
| projects/agents/src/athanor_agents/preference_learning.py | 804 |
| projects/agents/src/athanor_agents/tasks.py | 793 |
| projects/agents/src/athanor_agents/diagnosis.py | 792 |
| projects/agents/src/athanor_agents/self_improvement.py | 710 |
| projects/agents/src/athanor_agents/context.py | 693 |
| projects/agents/src/athanor_agents/scheduler.py | 681 |
| projects/agents/src/athanor_agents/tools/data_curator.py | 677 |
| scripts/completion_audit_common.py | 670 |
| projects/agents/src/athanor_agents/workplanner.py | 666 |
| projects/agents/tests/test_tasks.py | 657 |
| projects/agents/src/athanor_agents/tools/creative.py | 632 |
| scripts/extract-entities.py | 630 |

### TypeScript/TSX (top 15)
| File | LOC |
|------|-----|
| projects/dashboard/src/lib/server-agent.ts | 3,208 |
| projects/dashboard/src/lib/dashboard-fixtures.ts | 2,338 |
| projects/dashboard/src/lib/contracts.ts | 2,116 |
| projects/dashboard/src/lib/dashboard-data.ts | 1,755 |
| projects/dashboard/src/lib/subpage-data.ts | 1,302 |
| projects/eoq/src/data/narrative.ts | 946 |
| projects/dashboard/src/components/theme-sampler.tsx | 775 |
| projects/dashboard/src/lib/config.ts | 765 |
| projects/dashboard/src/features/overview/command-center.tsx | 710 |
| projects/eoq/src/hooks/use-game-engine.ts | 697 |
| projects/dashboard/src/features/agents/agent-console.tsx | 673 |
| projects/dashboard/src/features/intelligence/intelligence-console.tsx | 601 |
| projects/dashboard/src/features/history/history-console.tsx | 596 |
| projects/dashboard/src/components/subscription-control-card.tsx | 570 |
| projects/ulrich-energy/src/lib/fixtures.ts | 557 |

---

## 3. Git History Analysis

### Most Modified Files (all time, top 20)
| Changes | File |
|---------|------|
| 66 | docs/BUILD-MANIFEST.md |
| 58 | CLAUDE.md |
| 55 | projects/agents/src/athanor_agents/server.py |
| 51 | STATUS.md |
| 26 | docs/BUILD-ROADMAP.md |
| 24 | docs/SYSTEM-SPEC.md |
| 23 | .mcp.json |
| 21 | projects/dashboard/src/components/sidebar-nav.tsx |
| 20 | projects/dashboard/src/lib/config.ts |
| 20 | MEMORY.md |
| 19 | docs/SERVICES.md |
| 18 | .claude/settings.json |
| 17 | projects/agents/src/athanor_agents/scheduler.py |
| 15 | ansible/host_vars/core.yml |
| 14 | projects/agents/src/athanor_agents/tasks.py |
| 14 | .gitignore |
| 13 | projects/agents/src/athanor_agents/context.py |
| 13 | projects/agents/src/athanor_agents/config.py |
| 13 | projects/agents/docker-compose.yml |
| 13 | .claude/settings.local.json |

### Co-change Pairs (last 200 commits, top 10 non-snapshot)
| Count | File A | File B |
|-------|--------|--------|
| 8 | STATUS.md | docs/BUILD-MANIFEST.md |
| 6 | server.py | tasks.py |
| 6 | e2e/helpers.ts | e2e/visual.spec.ts |
| 5 | vault-litellm defaults | litellm_config template |
| 5 | SERVICES.md | SYSTEM-SPEC.md |
| 4 | diagnosis.py | self_improvement.py |
| 4 | scheduler.py | self_improvement.py |
| 4 | STATUS.md | SYSTEM-SPEC.md |
| 4 | dashboard-data.ts | dashboard-fixtures.ts |
| 4 | tasks-console.tsx | work-planner-console.tsx |

### Stale Branches
| Branch | Age | Status |
|--------|-----|--------|
| claude/audit-athanor-repo-Go24h | 19h | Post-Codex cleanup |
| codex/backbone-wip-sync-20260313 | 2d | WIP backbone progress |
| codex/dashboard-overhaul-reconciled | 4d | Merged main |
| codex/dashboard-overhaul-ui-sync | 5d | Dashboard overhaul |
| claude/companycam-alternative-E2fgM | 2w | CompanyCam alternative |
| claude/review-ai-plan-8jW3e | 2w | Wan2GP review |

---

## 4. Live Container State

### DEV (.189) — 3 containers
| Container | Image | Port |
|-----------|-------|------|
| dcgm-exporter | nvidia dcgm 3.3.9 | :9400 |
| vllm-reranker | nvidia vllm 25.12 | :8003 |
| vllm-embedding | nvidia vllm 25.12 | :8001 |

### FOUNDRY (.244) — 14 containers
| Container | Image | Port | Notes |
|-----------|-------|------|-------|
| athanor-agents | athanor/agents:latest | (9000 via compose) | Up 6 min (recent restart) |
| vllm-coordinator | athanor/vllm:qwen35 | (8000) | TP=4, GPUs 0,1,3,4 |
| vllm-coder | athanor/vllm:qwen35 | :8006 | GPU 2 (4090) |
| crucible-api | crucible-crucible-api | :8742 | AI search |
| crucible-ollama | ollama/ollama | :11434 | Crucible LLM |
| crucible-chromadb | chromadb/chroma | :8001 | Crucible vectors |
| crucible-searxng | searxng/searxng | :8080 | Crucible search |
| athanor-gpu-orchestrator | athanor/gpu-orchestrator | (9200) | GPU management |
| alloy | grafana/alloy v1.9.0 | — | Log/metric forwarding |
| wyoming-whisper | rhasspy/wyoming-whisper | :10300 | STT |
| qdrant | qdrant v1.13.2 | :6333-6334 | Vector DB |
| speaches | speaches-ai/speaches | :8200 | TTS+STT |
| dcgm-exporter | nvidia dcgm | :9400 | GPU metrics |
| node-exporter | prom/node-exporter | (9100) | System metrics |

### WORKSHOP (.225) — 10 containers
| Container | Image | Port |
|-----------|-------|------|
| athanor-dashboard | athanor/dashboard | :3001 |
| athanor-ws-pty-bridge | athanor/ws-pty-bridge | :3100 |
| athanor-eoq | athanor/eoq | :3002 |
| comfyui | athanor/comfyui:blackwell | :8188 |
| vllm-node2 | athanor/vllm:qwen35 | (8000) |
| athanor-ulrich-energy | athanor/ulrich-energy | :3003 |
| alloy | grafana/alloy v1.9.0 | — |
| open-webui | open-webui:main | :3000 |
| dcgm-exporter | nvidia dcgm | :9400 |
| node-exporter | prom/node-exporter | (9100) |

### VAULT (.203) — 44 containers
Core: litellm(:4000), neo4j(:7474/:7687), redis(:6379), qdrant(:6333), postgres(:5432), meilisearch(:7700)
Observability: langfuse-web(:3030), langfuse-worker, langfuse-postgres, langfuse-clickhouse, langfuse-redis, langfuse-minio, prometheus(:9090), grafana(:3000), ls-alloy, ls-loki, cadvisor(:9880), node-exporter(:9100)
Media: plex(:32400), sonarr(:8989), radarr(:7878), prowlarr(:9696), sabnzbd(:8080), tautulli(:8181), stash(:9999), tdarr_server(:8265-8266), tdarr_node
Home: homeassistant(:8123), wyoming-piper(:10200), wyoming-openwakeword(:10400)
Apps: gitea(:3033), miniflux(:8070), n8n(:5678), vault-open-webui(:3090), spiderfoot(:5001), ntfy(:8880), field-inspect-candidate(:3081), field-inspect-s3(:9000-9001), field-inspect-db(:5433), ulrich-energy-website(:8088), backup-exporter(:9199), blackbox-exporter(:9115)
**ISSUE:** field_inspect_app is in restart loop (exit 127)

**Total: 71 containers across 4 nodes**

---

## 5. GPU State

| Node | GPU | Model | VRAM Used | VRAM Total | Util |
|------|-----|-------|-----------|------------|------|
| DEV | 0 | RTX 5060 Ti | 4,799 MB | 16,311 MB | 0% |
| FOUNDRY | 0 | RTX 5070 Ti | 15,596 MB | 16,303 MB | 100% |
| FOUNDRY | 1 | RTX 5070 Ti | 15,596 MB | 16,303 MB | 100% |
| FOUNDRY | 2 | RTX 4090 | 22,984 MB | 24,564 MB | 0% |
| FOUNDRY | 3 | RTX 5070 Ti | 15,604 MB | 16,303 MB | 93% |
| FOUNDRY | 4 | RTX 5070 Ti | 15,596 MB | 16,303 MB | 92% |
| WORKSHOP | 0 | RTX 5090 | 31,340 MB | 32,607 MB | 0% |
| WORKSHOP | 1 | RTX 5060 Ti | 420 MB | 16,311 MB | 0% |

**Total VRAM:** 152,298 MB (~149 GB) across 8 GPUs

---

## 6. Agent System

### 9 Agents (projects/agents/src/athanor_agents/agents/)
| Agent | File | Tools File |
|-------|------|-----------|
| General | general.py | (uses system tools) |
| Research | research.py | tools/research.py |
| Media | media.py | tools/media.py |
| Home | home.py | tools/home.py |
| Creative | creative.py | tools/creative.py |
| Knowledge | knowledge.py | tools/knowledge.py |
| Coding | coding.py | tools/coding.py |
| Stash | stash.py | tools/stash.py |
| Data Curator | data_curator.py | tools/data_curator.py |

### Agent Server Modules (37 .py files in athanor_agents/)
server.py (2533), workspace.py (864), preference_learning.py (804), tasks.py (793), diagnosis.py (792), self_improvement.py (710), context.py (693), scheduler.py (681), workplanner.py (666), escalation.py (485), subscriptions.py (591), router.py (492), goals.py (486), activity.py (530), skill_learning.py (530), semantic_cache.py (12273 bytes), routing.py (449), config.py (9234 bytes), ...

### 10 Test Files
test_tasks.py (657), test_context.py (620), test_preference_learning.py (572), test_skill_learning.py (549), test_repo_contracts.py, test_contract_drift.py, test_prompting.py, test_settings_contract.py, test_project_registry.py, test_subscription_policy.py

---

## 7. Infrastructure Configuration

### Ansible (30 roles, 6 playbooks)
**Roles:** agents, backup, comfyui, common, dashboard, docker, eoq, gpu-orchestrator, monitoring, networking, nvidia, open-webui, qdrant, ulrich-energy, vault-gitea, vault-grafana-alerts, vault-homeassistant, vault-langfuse, vault-litellm, vault-media, vault-miniflux, vault-monitoring, vault-n8n, vault-neo4j, vault-open-webui, vault-redis, vault-voice, vllm, vllm-embedding, voice
**Playbooks:** common.yml, deploy-services.yml, dev.yml, node1.yml, node2.yml, site.yml, vault.yml
**Host vars:** core.yml (FOUNDRY), interface.yml (WORKSHOP), vault.yml (VAULT)

### Docker Compose Files (10)
projects/agents/, projects/dashboard/, projects/gpu-orchestrator/, services/node1/agents/, services/node1/monitoring/, services/node1/vllm/, services/node2/comfyui/, services/node2/dashboard/, services/node2/monitoring/, services/node2/open-webui/

### MCP Servers (16 configured)
**Active (8):** docker, athanor-agents, redis, qdrant, smart-reader, sequential-thinking, neo4j, postgres
**Disabled (8):** grafana, langfuse, miniflux, n8n, gitea, context7, github, playwright

---

## 8. Claude Code Configuration

### Hooks (12)
stop-autocommit.sh, session-start.sh, statusline.sh, pre-tool-use-bash-firewall.sh, post-tool-use-failure.sh, post-tool-use-typecheck.sh, task-completed-notify.sh, user-prompt-context.sh, pre-compact-save.sh, session-start-health.sh, session-end.sh, pre-tool-use-protect-paths.sh

### Skills (14)
network-diagnostics.md, architecture-decision/, troubleshoot.md, verify-inventory/, deploy-docker-service.md, comfyui-deploy.md, vllm-deploy.md, state-update.md, gpu-placement.md, athanor-conventions.md, local-coding.md, node-ssh.md, deploy-agent.md

### Commands (11)
decide.md, orient.md, build.md, project.md, morning.md, research.md, trace.md, deploy.md, audit.md, health.md, status.md

### Agents (6)
node-inspector.md, doc-writer.md, researcher.md, debugger.md, coder.md, infra-auditor.md

### Rules (11)
dashboard.md, agents.md, session-continuity.md, docker.md, scripts.md, eoq.md, knowledge.md, vllm.md, docs.md, ansible.md

---

## 9. Projects

| Project | Purpose | Stack |
|---------|---------|-------|
| agents | 9-agent AI system | Python, FastAPI, LangGraph |
| dashboard | Command Center UI | Next.js 16, TypeScript, Tailwind |
| eoq | Empire of Broken Queens game | Next.js, TypeScript |
| gpu-orchestrator | GPU zone management | Python, FastAPI |
| kindred | (In development) | — |
| ulrich-energy | Business app | Next.js, TypeScript |
| ws-pty-bridge | WebSocket terminal | Node.js |

---

## 10. Documentation

- 20 ADRs (ADR-001 through ADR-020)
- 23 design docs
- 20+ research docs
- Key docs: VISION.md, SYSTEM-SPEC.md, BUILD-MANIFEST.md, SERVICES.md, REFERENCE-INDEX.md
- CONSTITUTION.yaml: 310 lines, version 2.1.0, 16 immutable constraints

---

## 11. Known Issues (from discovery)

1. **field_inspect_app** on VAULT in restart loop (exit 127) [VERIFIED]
2. **6 stale branches** on origin, oldest 2 weeks [VERIFIED]
3. **FOUNDRY athanor-agents** restarted 6 minutes ago (recent instability?) [VERIFIED]
4. **FOUNDRY GPUs 0,1 at 100% util** — expected for coordinator inference [VERIFIED]
5. **Qdrant version mismatch**: FOUNDRY v1.13.2 vs VAULT v1.17.0 [VERIFIED]
