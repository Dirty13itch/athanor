# Stash Agent — Scope & Workflow

## Overview

The Stash Agent manages Shaun's adult content library via the Stash GraphQL API running on VAULT:9999. It's one of 9 agents in the Athanor agent fleet, running on FOUNDRY:9000.

## Architecture

```
User (Dashboard/Chat)
  → Agent Server (FOUNDRY:9000)
    → Stash Agent (LangGraph ReAct)
      → Stash GraphQL API (VAULT:9999)
        → Filesystem (/mnt/user/data/stash/)
```

**Model:** Uses the `reasoning` LiteLLM route (Qwen3.5-27B-FP8 TP=4).
**Temperature:** 0.7 (slightly creative for natural conversation).
**Thinking:** Disabled (`enable_thinking: false`).

## Tool Inventory (15 tools)

| Tool | Category | Description |
|------|----------|-------------|
| `get_stash_stats` | Browse | Library statistics (counts, storage, duration) |
| `search_scenes` | Browse | Full-text scene search with metadata |
| `get_scene_details` | Browse | Detailed scene info by ID |
| `search_performers` | Browse | Performer search with scene counts |
| `list_tags` | Browse | Tags sorted by scene count |
| `get_recent_scenes` | Browse | Recently added content |
| `create_tag` | Tag CRUD | Create new tags |
| `tag_scenes` | Tag CRUD | Add/remove tags from scenes |
| `delete_tag` | Tag CRUD | Delete tags by name |
| `find_duplicates` | Maintenance | Perceptual hash duplicate detection |
| `scan_library` | Maintenance | Full filesystem scan for new content |
| `auto_tag` | Maintenance | Filename-based auto-tagging |
| `generate_content` | Maintenance | Thumbnails, previews, sprites, phash |
| `update_scene_rating` | Organize | Set 1-5 star ratings |
| `mark_scene_organized` | Organize | Flag scenes as metadata-reviewed |

## Content Policy

Adult content is explicitly allowed and expected. The system prompt instructs:
- No filtering, moralizing, or softening
- Direct, matter-of-fact language
- Clinical terminology acceptable
- Confirm before destructive actions (deletes, bulk ops)

## Limitations

- **No video playback** — agent can link to scenes but can't stream
- **No performer creation** — performers come from Stash scraping, not agent CRUD
- **No image management** — galleries/images not yet exposed via tools
- **No smart playlists** — planned but not implemented
- **No scene deletion** — intentionally omitted to prevent data loss

## Scheduled Tasks

The stash-agent runs a daily maintenance schedule (via `scheduler.py`):
- Library scan for new content
- Auto-tag pass on unorganized scenes

Last updated: 2026-03-14
