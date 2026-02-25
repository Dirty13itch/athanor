# Stash AI Integration Research

**Date:** 2026-02-24
**Status:** Complete -- recommendation ready
**Supports:** BUILD-MANIFEST 6.6 (Stash AI integration)
**Depends on:** ADR-011 (Media Stack), ADR-008 (Agent Framework)

---

## Context

Stash (stashapp/stash) is already deployed on VAULT:9999 (confirmed in SERVICES.md and vault-audit-2026-02-14). The container is `ghcr.io/hotio/stash:latest` with two companion containers (`stash-maint`, `stash-jobs`). BUILD-MANIFEST item 6.6 calls for AI integration. This research covers deployment details, API surface, AI plugin ecosystem, local vision models, and the design for a Stash Agent in the existing agent framework.

---

## 1. Stash Deployment

### Docker Configuration

**Official image:** `stashapp/stash:latest` (DockerHub) -- Go backend, TypeScript frontend, includes FFmpeg.

**Alternative images for hardware acceleration:**
- `feederbox826/stash-s6` -- hardware acceleration support + uv Python manager
- `nerethos/stash` -- hardware acceleration support + venv Python manager

**Current VAULT deployment** uses `ghcr.io/hotio/stash:latest` (hotio repackage). This works but the official image or feederbox826/stash-s6 would be better for plugin compatibility (Python manager included).

**Ports:**
- **9999** -- Web UI and GraphQL API (single port)

**Required volumes:**

| Mount | Container Path | Purpose |
|-------|---------------|---------|
| Config | `/root/.stash` | config.yml, scrapers, plugins, database |
| Data | `/data` | Media library (your content) |
| Generated | `/generated` | Screenshots, previews, sprites, transcodes |
| Cache | `/cache` | Temporary transcoding files |
| Metadata | `/metadata` | Export/import JSON metadata |
| Blobs | `/blobs` | Binary blob storage (scene covers, images) |

**Environment variables:**
```
STASH_STASH=/data/
STASH_GENERATED=/generated/
STASH_METADATA=/metadata/
STASH_CACHE=/cache/
STASH_PORT=9999
```

**Recommended docker-compose for VAULT:**
```yaml
services:
  stash:
    image: stashapp/stash:latest  # or feederbox826/stash-s6 for HW accel
    container_name: stash
    restart: unless-stopped
    ports:
      - "9999:9999"
    environment:
      - STASH_STASH=/data/
      - STASH_GENERATED=/generated/
      - STASH_METADATA=/metadata/
      - STASH_CACHE=/cache/
      - STASH_PORT=9999
    volumes:
      - /mnt/user/appdata/stash/config:/root/.stash
      - /mnt/user/data/media/adult:/data
      - /mnt/user/appdata/stash/generated:/generated
      - /mnt/user/appdata/stash/cache:/cache
      - /mnt/user/appdata/stash/metadata:/metadata
      - /mnt/user/appdata/stash/blobs:/blobs
      - /etc/localtime:/etc/localtime:ro
    logging:
      driver: json-file
      options:
        max-file: "10"
        max-size: "2m"
```

**Storage requirements:**
- Generated content (previews, sprites, screenshots) can be 10-30% of library size depending on settings
- Cache is temporary (used during transcoding), can be on fast storage
- Database (SQLite in config dir) is small (<100 MB for most libraries)
- Blobs grow with cover images -- typically a few GB

**Unraid:** Available in Community Apps as "Stash by CorneliousJD" or "stash-s6 by feederbox826". Both are community-maintained, not official stashapp team.

### Media Library Organization

Stash scans configured directories recursively. Best practices:

```
/mnt/user/data/media/adult/
  ├── scenes/           # Individual scenes/clips
  │   ├── studio-name/  # Organized by studio (optional)
  │   └── unsorted/     # New/uncategorized content
  ├── movies/           # Full-length movies
  └── images/           # Image galleries
```

Stash is flexible -- it doesn't require a specific folder structure. It discovers content by scanning and uses the database for organization. However, organizing by studio or source in the filesystem makes manual browsing easier and helps the auto-tagger (it reads path components).

**Naming conventions that help auto-tagging:**
- Include performer names in filenames: `performer1.performer2.title.mp4`
- Include studio name in path or filename
- Use dots or spaces as separators (Stash's filename parser handles both)

**Hashing:** Stash supports `oshash` (fast, default) and `MD5` (slower, reads entire file). oshash is sufficient for deduplication via perceptual hash (phash) which is separate from file hash.

---

## 2. Stash GraphQL API

Stash has a comprehensive GraphQL API at `http://VAULT:9999/graphql`. This is the primary integration point.

### Authentication

- Optional username/password protection
- API keys generated via Settings
- Pass API key via `ApiKey` HTTP header
- For agent integration: generate an API key and store in agent config

### Key Queries

| Query | Purpose |
|-------|---------|
| `findScenes(scene_filter, filter)` | Search/filter scenes with pagination |
| `findScene(id)` | Get single scene with all metadata |
| `findPerformers(performer_filter, filter)` | Search/filter performers |
| `findPerformer(id)` | Get single performer details |
| `findTags(tag_filter, filter)` | List/search tags |
| `findStudios(studio_filter, filter)` | List/search studios |
| `findDuplicateScenes(distance, duration_diff)` | Find perceptual hash duplicates |
| `findScenesByPathRegex(filter)` | Regex path search |
| `stats` | Library statistics (scene count, size, etc.) |
| `sceneStreams(id)` | Get streamable URLs for a scene |
| `jobQueue` | Current running/pending jobs |
| `systemStatus` | System health |
| `plugins` | List loaded plugins |
| `pluginTasks` | Available plugin operations |

### Key Mutations

| Mutation | Purpose |
|----------|---------|
| `sceneUpdate(input)` | Update scene metadata (title, tags, performers, etc.) |
| `bulkSceneUpdate(input)` | Bulk update multiple scenes |
| `performerCreate/Update/Destroy` | CRUD performers |
| `tagCreate/Update/Destroy` | CRUD tags |
| `studioCreate/Update/Destroy` | CRUD studios |
| `metadataScan(input)` | Trigger library scan |
| `metadataAutoTag(input)` | Run auto-tagger |
| `metadataIdentify(input)` | Run identify task (match against StashDB) |
| `metadataGenerate(input)` | Generate previews/sprites/phash |
| `metadataClean(input)` | Clean missing files from DB |
| `runPluginTask(plugin_id, task_name)` | Execute a plugin task |
| `sceneMerge(input)` | Merge duplicate scenes |
| `performerMerge(input)` | Merge duplicate performers |
| `moveFiles(input)` | Move files within library |
| `deleteFiles(ids)` | Delete files from filesystem |

### Scene Object Fields

A Scene contains: `id`, `title`, `code`, `details` (description), `director`, `urls`, `date`, `rating100` (1-100 scale), `organized` (boolean), `o_counter`, `play_count`, `play_duration`, `resume_time`, `files` (video metadata: codec, resolution, duration, bitrate), `paths` (screenshot/preview/stream URLs), `scene_markers` (timestamped bookmarks), `galleries`, `studio`, `groups`, `tags`, `performers`, `stash_ids` (links to StashDB), `custom_fields`.

### Performer Object Fields

A Performer contains: `id`, `name`, `disambiguation`, `urls`, `gender`, `birthdate`, `ethnicity`, `country`, `eye_color`, `height_cm`, `measurements`, `career_start`/`career_end`, `tattoos`, `piercings`, `alias_list`, `favorite`, `tags`, `scene_count`, `image_count`, `stash_ids`, `rating100`, `details`, `custom_fields`.

### Filter System

The filter system supports complex queries with AND/OR/NOT logic. Scene filters include: `tags`, `performers`, `studios`, `resolution`, `duration`, `rating100`, `organized`, `path`, `is_missing`, `has_markers`, `play_count`, `o_counter`, `file_count`, `duplicated`, `stash_id_endpoint`, `created_at`, `updated_at`, and `custom_fields`.

### Scraping Operations

| Query | Purpose |
|-------|---------|
| `scrapeSingleScene(source, input)` | Scrape metadata for one scene |
| `scrapeMultiScenes(source, input)` | Batch scrape multiple scenes |
| `scrapeSinglePerformer(source, input)` | Scrape performer metadata |
| `scrapeURL(url, type)` | Scrape from a URL directly |
| `listScrapers(types)` | List available scrapers |

### Job Management

All long-running operations (scan, generate, auto-tag, identify) return a job ID. Jobs can be monitored via `jobQueue` query and stopped via `stopJob(job_id)` mutation.

### Example Queries

**Find untagged scenes:**
```graphql
query {
  findScenes(
    scene_filter: {
      tag_count: { value: 0, modifier: EQUALS }
      organized: false
    }
    filter: { per_page: 25, sort: "created_at", direction: DESC }
  ) {
    count
    scenes {
      id
      title
      files { path duration }
      paths { screenshot }
    }
  }
}
```

**Get library stats:**
```graphql
query {
  stats {
    scene_count
    scenes_size
    scenes_duration
    image_count
    images_size
    gallery_count
    performer_count
    studio_count
    tag_count
  }
}
```

**Find duplicate scenes:**
```graphql
query {
  findDuplicateScenes(distance: 4, duration_diff: 10.0) {
    id
    title
    files { path size duration }
    paths { screenshot }
  }
}
```

**Source:** [Stash GraphQL schema](https://github.com/stashapp/stash/tree/develop/graphql/schema)

---

## 3. Built-in ML/AI Features

Stash has **no built-in machine learning**. Its "AI" features are pattern-matching, not neural networks:

- **Auto-Tagger:** Matches performer names, studio names, and tags against filenames and directory paths using string matching. Not ML-based.
- **Identify Task:** Matches scenes against StashDB/stash-box instances using perceptual hash fingerprints (phash). This is a lookup, not ML inference.
- **Perceptual Hash (phash):** Generated per-scene for deduplication. Uses image similarity hashing, not deep learning.
- **Scene Filename Parser:** Regex-based extraction of metadata from filenames.

All actual AI capabilities come from the plugin ecosystem.

---

## 4. Plugin Ecosystem and AI Plugins

### Plugin Architecture

- Plugins are YAML configs + JavaScript (embedded) or Python/Go/any binary (external)
- Hooks fire on object Create/Update/Destroy (post-operation only)
- Tasks are user-triggered or can be triggered via `runPluginTask` GraphQL mutation
- Plugins receive JSON input with server connection details
- Plugin sources are YAML index files (default: CommunityScripts repo)

### AI-Relevant Community Plugins

#### AITagger (skier233/nsfw_ai_model_server)
- **What:** Automatic content tagging using custom NSFW classification models
- **Models:** Custom models (architecture not disclosed), NVIDIA GPU required (GTX 1080+)
- **Tags:** 10 free, 151 total (Patreon-gated for full model)
- **Features:** Image and video tagging with timestamps, frame-by-frame analysis
- **Architecture:** Separate server process that Stash plugin communicates with
- **Local:** Yes, fully local inference
- **Caveat:** Patreon paywall for full model set. Free tier is limited.
- **Source:** https://github.com/skier233/nsfw_ai_model_server

#### AHavenVLMConnector
- **What:** Uses Vision-Language Models for context-aware content tagging
- **Models:** Any OpenAI-compatible VLM -- tested with glm-4.6v-flash, Mistral Small 3.2 24B, **Qwen3-VL-8B**, lfm2.5-vl
- **Architecture:** Connects to any OpenAI-compatible endpoint (LM Studio, vLLM, etc.)
- **Features:** Tag scenes based on VLM understanding of video frames. Configurable frame interval, concurrent task limit, weighted endpoint load balancing.
- **Workflow:** Tag scene with `VLM_TagMe` -> run "Tag Videos" task -> VLM processes frames -> tags applied
- **Local:** Yes, designed for local-first operation
- **THIS IS THE BEST FIT for Athanor.** It can use Node 1's vLLM with a VL model, or a dedicated VLM on one of the GPUs.
- **Source:** https://github.com/stashapp/CommunityScripts/tree/main/plugins/AHavenVLMConnector

#### LocalVisage
- **What:** Face recognition for performer identification
- **Models:** DeepFace (open-source facial recognition framework)
- **Architecture:** Builds local face embedding database from existing performer images, then matches unknown faces
- **Features:** Model building from library images, incremental updates, click-to-identify on images
- **Local:** Fully local, Python-based, runs DeepFace server on port 7860
- **Hardware:** CPU inference works, GPU accelerates. DeepFace uses ~2-4 GB RAM.
- **Source:** https://github.com/stashapp/CommunityScripts/tree/main/plugins/LocalVisage

#### AIOverhaul + Stash-AIServer (skier233)
- **What:** Combined AI server for tagging + recommendations
- **Features:** AI tagging (via nsfw_ai_model_server), TF-IDF personalized recommendations, tag-based similar scene suggestions
- **Architecture:** Separate backend server (Python), modular plugin architecture, supports remote inference
- **Source:** https://github.com/skier233/Stash-AIServer

#### stashAI
- **What:** AI-related UI enhancements for Stash (JavaScript-based)
- **Source:** https://github.com/stashapp/CommunityScripts/tree/main/plugins/stashAI

### Plugin Comparison for Athanor

| Plugin | Best For | Fits Athanor? | Notes |
|--------|----------|---------------|-------|
| AHavenVLMConnector | VLM-based scene understanding | **Excellent** | Uses OpenAI-compatible API, works with vLLM |
| LocalVisage | Face recognition | **Good** | DeepFace, fully local, lightweight |
| AITagger | Content classification | Fair | Patreon paywall, closed models |
| AIOverhaul | Recommendations | Fair | Heavy, separate server, some closed components |

**Recommendation:** Install AHavenVLMConnector + LocalVisage. Skip AITagger (paywall) and AIOverhaul (overengineered for our needs -- we'll build recommendations natively via Qdrant embeddings).

---

## 5. AI Integration Opportunities

### 5.1 Auto-Tagging via VLM (AHavenVLMConnector + vLLM)

**How it works:**
1. Deploy a Vision-Language Model on one of Node 1's GPUs via vLLM
2. Configure AHavenVLMConnector to point at Node 1's vLLM endpoint
3. VLM analyzes video frames at configurable intervals
4. Plugin applies detected tags to scenes in Stash

**Model options for local VLM inference on 16 GB VRAM (single 5070 Ti):**

| Model | Size | VRAM | Capabilities |
|-------|------|------|-------------|
| Qwen2.5-VL-7B-Instruct-AWQ | ~4.5 GB | ~8 GB | Scene understanding, OCR, object detection |
| Qwen3-VL-8B | ~8 GB | ~12 GB | Latest Qwen VL, strong reasoning |
| InternVL2.5-8B-AWQ | ~5 GB | ~8 GB | Strong vision-language understanding |
| LLaVA-v1.6-Mistral-7B-AWQ | ~4.5 GB | ~8 GB | Solid general VLM |

**Recommended:** Qwen2.5-VL-7B-Instruct-AWQ or Qwen3-VL-8B. Both supported by vLLM, quantized versions fit on a single 5070 Ti. AHavenVLMConnector explicitly lists Qwen3-VL-8B as tested.

**GPU allocation:** Use GPU 4 on Node 1 (currently running embeddings). Either share with embedding model (embedding is tiny at 0.6B params) or dedicate a GPU when processing Stash content.

### 5.2 Performer Recognition (LocalVisage)

**How it works:**
1. Build face database from existing performer images in Stash
2. When new content is added, extract faces from thumbnails/screenshots
3. Match against known performer faces
4. Assign performers to scenes automatically

**DeepFace backends:** ArcFace (most accurate), Facenet512, VGG-Face, OpenFace. All run locally. ArcFace recommended.

**Integration:** LocalVisage runs a DeepFace server (port 7860) alongside Stash. Can run on VAULT's CPU (no GPU needed for inference, though GPU speeds it up).

### 5.3 Scene Description Generation via LLM

**Not a Stash plugin feature -- build in agent layer:**
1. Agent extracts scene screenshots via Stash API (`paths.screenshot`)
2. Send screenshot to VLM for description
3. Agent updates scene `details` field via `sceneUpdate` mutation

This is better handled by the Stash Agent than a Stash plugin, because the agent can use the existing Qwen3-32B for text and a VLM for image understanding, with full control over prompting and output quality.

### 5.4 Smart Playlists / Recommendations via Qdrant

**Architecture:**
1. For each scene, generate an embedding from: title + tags + performers + studio + description
2. Store embeddings in a `stash_scenes` Qdrant collection
3. Query similar scenes by cosine similarity
4. Build "more like this" recommendations
5. Combine with play history (o_counter, play_count) for personalized recommendations

**This replaces AIOverhaul's TF-IDF recommender** with a proper vector-based approach that lives in Athanor's existing Qdrant infrastructure.

**Collection schema:**
```python
{
    "collection": "stash_scenes",
    "vectors": {"size": 1024, "distance": "Cosine"},
    "payload": {
        "stash_id": int,
        "title": str,
        "tags": list[str],
        "performers": list[str],
        "studio": str,
        "rating": int,
        "play_count": int,
        "duration": float,
    }
}
```

### 5.5 Content Deduplication

Stash has built-in phash-based deduplication via `findDuplicateScenes`. The agent can:
1. Periodically query for duplicates
2. Present them to the user with side-by-side comparison data
3. Recommend which to keep (higher resolution, better codec, larger file)
4. Delete the inferior copy on user approval (escalation: ask tier)

### 5.6 CLIP-Based Semantic Search (custom build)

Not in Stash plugins but buildable:
1. Run CLIP (e.g., `openai/clip-vit-large-patch14`) on scene thumbnails/previews
2. Store CLIP embeddings in Qdrant
3. Enable natural language scene search ("outdoor scene with pool")
4. CLIP runs on a single GPU, ~2 GB VRAM

This is a Tier 2 enhancement -- build after basic integration works.

---

## 6. Stash Agent Design

### Agent Registration

Add to `AGENT_METADATA` in server.py:

```python
"stash-agent": {
    "description": "Adult content library management via Stash -- search, tag, organize, find duplicates, AI analysis.",
    "tools": [
        "stash_search_scenes", "stash_get_scene", "stash_get_stats",
        "stash_find_duplicates", "stash_find_untagged",
        "stash_update_scene", "stash_bulk_tag",
        "stash_search_performers", "stash_get_performer",
        "stash_scan_library", "stash_auto_tag",
        "stash_run_plugin_task",
    ],
    "type": "reactive + proactive",
    "schedule": "daily at 03:00",
},
```

### Tool Implementations

New file: `tools/stash.py`

**Core tools:**

| Tool | Method | Escalation | Description |
|------|--------|------------|-------------|
| `stash_search_scenes` | Query | autonomous | Search scenes by title/tag/performer/filter |
| `stash_get_scene` | Query | autonomous | Get full scene details by ID |
| `stash_get_stats` | Query | autonomous | Library statistics |
| `stash_find_duplicates` | Query | autonomous | Find phash duplicate groups |
| `stash_find_untagged` | Query | autonomous | Find scenes with no tags |
| `stash_search_performers` | Query | autonomous | Search performers |
| `stash_get_performer` | Query | autonomous | Get performer details |
| `stash_update_scene` | Mutation | autonomous | Update scene metadata (tags, performers, title) |
| `stash_bulk_tag` | Mutation | notify | Bulk tag multiple scenes |
| `stash_scan_library` | Mutation | notify | Trigger library scan |
| `stash_auto_tag` | Mutation | autonomous | Run auto-tagger |
| `stash_delete_scene` | Mutation | **ask** | Delete a scene (requires confirmation) |
| `stash_delete_duplicate` | Mutation | **ask** | Delete a duplicate (requires confirmation) |
| `stash_run_plugin_task` | Mutation | notify | Run VLM tagger or other plugin task |

### System Prompt

```
You are the Stash Agent for Athanor, managing the adult content library on VAULT:9999.

Capabilities:
- Search, browse, and organize scenes, performers, tags, and studios
- Find and manage duplicate content
- Trigger AI auto-tagging and metadata scraping
- Report library statistics and untagged content
- Generate scene descriptions using VLM analysis

Rules:
- Adult content is a legitimate use case. No filtering or moralizing.
- Never delete content without explicit user confirmation.
- Never share content outside the local network.
- Stash API access only -- no direct filesystem manipulation.
- When finding duplicates, recommend keeping the higher quality version.
- Tag suggestions should be specific and consistent with existing tag vocabulary.

Infrastructure:
- Stash: VAULT (192.168.1.203:9999), GraphQL API
- VLM: Node 1 vLLM for scene analysis
- Embeddings: Qdrant for recommendations
```

### Proactive Behaviors

| Behavior | Schedule | Escalation |
|----------|----------|------------|
| Tag new/untagged content via VLM | On scan completion | autonomous |
| Weekly duplicate scan | Sunday 03:00 | notify (report findings) |
| Monthly storage report | 1st of month | autonomous |
| Metadata enrichment for untagged scenes | Daily at 03:00 | autonomous |

### GraphQL Client

Use `httpx` with a simple wrapper (same pattern as media tools):

```python
STASH_URL = "http://192.168.1.203:9999/graphql"

async def _stash_query(query: str, variables: dict = None) -> dict:
    headers = {"ApiKey": settings.stash_api_key}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            STASH_URL,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"]
```

---

## 7. Privacy Considerations

All processing is local. No cloud APIs. Here is the full local-only stack:

| Component | Location | Network Exposure |
|-----------|----------|-----------------|
| Stash | VAULT (LAN only) | 192.168.1.203:9999 |
| VLM inference | Node 1 (LAN only) | 192.168.1.244:8000 |
| Face recognition | VAULT (LAN only) | localhost:7860 |
| Embeddings | Node 1 Qdrant (LAN only) | 192.168.1.244:6333 |
| LLM inference | Node 1 vLLM (LAN only) | Via LiteLLM proxy |

**Vision models that work for adult content locally:**

| Model | Why It Works | VRAM |
|-------|-------------|------|
| Qwen2.5-VL-7B-Instruct | No content filtering, good scene understanding | ~12 GB |
| Qwen3-VL-8B | Latest Qwen VL, no built-in content filter | ~14 GB |
| InternVL2.5-8B | Strong visual reasoning, minimal filtering | ~12 GB |
| DeepFace (ArcFace) | Face detection/recognition, no content awareness | ~2 GB |
| CLIP ViT-L/14 | Semantic image search, content-agnostic | ~2 GB |

**Models to avoid:**
- LLaVA with Llama-guard -- content filtering built in
- Any model hosted by OpenAI/Anthropic/Google (content policies)
- Stability AI models with safety checkers

**Qwen VL models are ideal** because: (a) no built-in content filtering, (b) strong visual reasoning, (c) vLLM native support, (d) AWQ quantization available, (e) already in the Qwen ecosystem that Athanor uses.

---

## 8. Implementation Plan

### Phase 1: Core Agent (1-2 sessions)
1. Add `stash_api_key` to agent config
2. Create `tools/stash.py` with GraphQL client + core tools
3. Create `agents/stash.py` with agent definition
4. Register in server.py
5. Test: search scenes, get stats, find untagged, find duplicates

### Phase 2: VLM Auto-Tagging (1 session)
1. Download Qwen2.5-VL-7B-Instruct-AWQ to NFS models share
2. Deploy as separate vLLM instance on GPU 4 (or share with embedding)
3. Install AHavenVLMConnector in Stash, configure endpoint
4. Test: tag a batch of scenes, verify results

### Phase 3: Face Recognition (1 session)
1. Install LocalVisage in Stash
2. Build initial face database from existing performer images
3. Test on known performers
4. Add incremental update to proactive behaviors

### Phase 4: Recommendations via Qdrant (1 session)
1. Create `stash_scenes` collection in Qdrant
2. Build embedding pipeline: scene metadata -> text embedding -> Qdrant
3. Add `stash_recommend` tool to agent
4. Backfill embeddings for existing library

### Phase 5: CLIP Semantic Search (future)
1. Deploy CLIP model on Node 1
2. Process scene screenshots through CLIP
3. Store visual embeddings in Qdrant
4. Enable natural language visual search

---

## 9. Open Questions

1. **Current Stash library size?** Need to check VAULT to understand scale (number of scenes, storage used). This affects processing time estimates.
2. **hotio vs official image?** The current hotio image may not support Python plugins (needed for LocalVisage, AITagger). May need to switch to feederbox826/stash-s6 or official image.
3. **GPU 4 capacity for dual workload?** Running embedding model (0.6B, ~1 GB VRAM) and VLM (7-8B, ~12 GB VRAM) on same 16 GB GPU should work but needs testing.
4. **StashDB integration?** Whether to enable fingerprint matching against StashDB community database. Sends phash fingerprints to internet -- may be acceptable since they're not content, just hashes.
5. **Stash API key?** Need to generate one from Stash settings before agent integration.

---

## Sources

- [Stash GitHub](https://github.com/stashapp/stash) -- Go/TypeScript, GraphQL API
- [Stash Documentation](https://docs.stashapp.cc) -- installation, configuration, tasks
- [Stash GraphQL Schema](https://github.com/stashapp/stash/tree/develop/graphql/schema) -- full type definitions
- [Stash Docker Compose](https://github.com/stashapp/stash/blob/develop/docker/production/docker-compose.yml) -- official compose
- [Stash Plugin System](https://docs.stashapp.cc/in-app-manual/plugins/) -- hooks, tasks, plugin API
- [AHavenVLMConnector](https://github.com/stashapp/CommunityScripts/tree/main/plugins/AHavenVLMConnector) -- VLM-based tagging
- [LocalVisage](https://github.com/stashapp/CommunityScripts/tree/main/plugins/LocalVisage) -- DeepFace face recognition
- [AITagger / nsfw_ai_model_server](https://github.com/skier233/nsfw_ai_model_server) -- custom NSFW classification
- [Stash-AIServer / AIOverhaul](https://github.com/skier233/Stash-AIServer) -- AI backend + recommendations
- [CommunityScripts](https://github.com/stashapp/CommunityScripts) -- full plugin repository
- [Stash Unraid Install](https://docs.stashapp.cc/installation/unraid/) -- Community Apps setup
- [DeepFace](https://github.com/serengil/deepface) -- face recognition framework used by LocalVisage
