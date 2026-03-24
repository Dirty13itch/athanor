# Athanor Agent Roster

**Last verified:** 2026-03-19 (from FOUNDRY agent server health endpoint)
**Server:** FOUNDRY:9000 (athanor-agents container, FastAPI v0.3.0)
**Status:** 9/9 agents online, scheduler running (APScheduler backend)

## Agent Summary

| Agent | Type | Schedule | Risk Class | Priority Class |
|-------|------|----------|------------|----------------|
| general-assistant | proactive | every 30 min | HIGH_IMPACT | latency-sensitive |
| media-agent | proactive | every 15 min | MEDIUM | latency-sensitive |
| home-agent | proactive | every 5 min | LOW | latency-sensitive |
| creative-agent | reactive | every 4 hours | MEDIUM | creative |
| research-agent | reactive | every 2 hours | MEDIUM | batch |
| knowledge-agent | reactive | every 1 hour | LOW | batch |
| coding-agent | reactive | every 3 hours | HIGH_IMPACT | batch |
| stash-agent | reactive | every 6 hours | LOW | creative |
| data-curator | reactive | every 6 hours | LOW | batch |

## Agent Details

### general-assistant
- **Description:** System monitoring, infrastructure management, task coordination, and codebase inspection.
- **Tools:** check_services, get_gpu_metrics, get_vllm_models, get_storage_info, delegate_to_agent, check_task_status, read_file, list_directory, search_files
- **Schedule:** Every 30 min — system health check, GPU status, service status. Reports issues only.
- **Trust class:** HIGH_IMPACT (requires trust to enable autonomous actions)

### media-agent
- **Description:** Media stack control — search/add TV (Sonarr), movies (Radarr), monitor Plex streams (Tautulli).
- **Tools:** search_tv_shows, get_tv_calendar, get_tv_queue, get_tv_library, add_tv_show, search_movies, get_movie_calendar, get_movie_queue, get_movie_library, add_movie, get_plex_activity, get_watch_history, get_plex_libraries
- **Schedule:** Every 15 min — check downloads, new additions, Plex activity.
- **Trust class:** MEDIUM (no penalty, no bonus — track record)

### home-agent
- **Description:** Smart home control via Home Assistant — lights, climate, automations, presence.
- **Tools:** get_ha_states, get_entity_state, find_entities, call_ha_service, set_light_brightness, set_climate_temperature, list_automations, trigger_automation
- **Schedule:** Every 5 min — entity state check, anomaly detection.
- **Trust class:** LOW (auto-execute at Level A/B, read-only monitoring)

### creative-agent
- **Description:** Image and video generation via ComfyUI — Flux text-to-image, Wan2.x text-to-video, queue management.
- **Tools:** generate_image, generate_video, check_queue, get_generation_history, get_comfyui_status
- **Schedule:** Every 4 hours — creative production cycle (check queue, generate missing stage videos, evaluate quality).
- **Trust class:** MEDIUM (starts here to prime trust flywheel)
- **Content policy:** creative_uncensored

### research-agent
- **Description:** Web research and information synthesis — citations, fact-checking, knowledge search, graph queries.
- **Tools:** web_search, fetch_page, search_knowledge, query_infrastructure, request_execution_lease
- **Schedule:** Every 2 hours — intelligence signals pipeline check (min_relevance=0.7).
- **Trust class:** MEDIUM
- **LLM model override:** Uses extended context for research tasks

### knowledge-agent
- **Description:** Project librarian — search docs, ADRs, research notes, infrastructure graph, intelligence signals, find related knowledge.
- **Tools:** search_knowledge, search_signals, deep_search, list_documents, query_knowledge_graph, find_related_docs, get_knowledge_stats, upload_document
- **Schedule:** Every 1 hour — knowledge base health, collection sizes, freshness check.
- **Trust class:** LOW (auto-execute, read-only)
- **Content policy:** private_internal

### coding-agent
- **Description:** Autonomous coding engine — generates, reviews, writes files, runs tests, iterates.
- **Tools:** generate_code, review_code, explain_code, transform_code, read_file, write_file, list_directory, search_files, run_command, run_tests, create_pr, check_ci_status
- **Schedule:** Every 3 hours — code health check, agent server endpoint verification, error detection.
- **Trust class:** HIGH_IMPACT (requires trust buildup for autonomous code changes)
- **Weekly task:** DPO training orchestration (Saturday 02:00)

### stash-agent
- **Description:** Adult content library management — search, browse, organize, tag, and manage via Stash.
- **Tools:** get_stash_stats, search_scenes, get_scene_details, search_performers, get_performer_details, update_performer, get_galleries, get_tags, organize_scenes, batch_tag
- **Schedule:** Every 6 hours — library stats, untagged/uncategorized scene detection.
- **Trust class:** LOW (auto-execute)
- **Content policy:** creative_uncensored

### data-curator
- **Description:** Personal data librarian — discovers, parses, analyzes, and indexes files from all sources into searchable Qdrant collection.
- **Tools:** scan_directory, parse_document, analyze_content, index_document, get_scan_status, search_indexed, get_collection_stats
- **Schedule:** Every 6 hours — autonomous curation cycle (scan roots, parse new files, index, report).
- **Trust class:** LOW (auto-execute)
- **Content policy:** private_internal

## Scheduling Architecture

### Inference-Aware Scheduling
The scheduler queries Prometheus for vLLM GPU utilization and queue depth before dispatching agent tasks:

| Priority Class | GPU Util < 80% | GPU Util 80-95% | GPU Util > 95% |
|---------------|----------------|-----------------|----------------|
| latency-sensitive | Run | Run | Run |
| batch | Run | Throttled | Blocked |
| creative | Run | Run | Throttled |

- **VLLM queue depth > 5:** batch agents throttled
- **VLLM queue depth > 15:** only latency-sensitive agents run

### Governor Autonomy Levels
Tasks are gated through the Governor which assigns autonomy levels (A-D) based on agent trust score and presence state:

| Level | Trust Required | Approval |
|-------|---------------|----------|
| A | High trust + low risk | Auto-execute |
| B | Medium trust | Auto-execute with logging |
| C | Low trust or medium risk | Pending approval |
| D | New agent or high risk | Manual approval required |

### Scheduled Background Jobs (APScheduler)
Beyond per-agent schedules, these global jobs run:

| Job | Schedule | Description |
|-----|----------|-------------|
| Memory consolidation | 03:00 daily | Merge short-term → long-term memory |
| Owner model rebuild | 04:00 daily | Full preference model recalculation |
| Pattern detection | 05:00 daily | Cross-agent behavioral analysis |
| Improvement cycle | 05:30 daily | Self-improvement proposals |
| Daily digest | 06:55 daily | Morning briefing generation |
| Morning workplan | 07:00 daily | Day's task queue generation |
| Knowledge refresh | 00:00 daily | Nightly knowledge base refresh |
| Nightly optimization | 22:00 daily | Prompt and routing optimization |
| Alert checks | Every 5 min | System alert monitoring |
| Cache cleanup | Every 1 hour | Semantic cache maintenance |
| Work pipeline | Every 2 hours | Task queue processing |
| Workplan refill | Every 2 hours | Auto-refill task queue |
| Benchmark | Every 6 hours | Agent performance benchmarking |
| DPO training | Saturday 02:00 | Weekly preference learning (4090) |

## Dependencies
- **Redis:** State, scheduling keys, trust scores (VAULT:6379)
- **Qdrant:** Activity logging, knowledge search (VAULT:6333)
- **LiteLLM:** LLM routing for all agent inference (VAULT:4000)
- **vLLM coordinator:** Primary inference (FOUNDRY:8000)
- **vLLM coder:** Code generation (FOUNDRY:8006)
- **Embedding service:** Vector embeddings (DEV:8001)
