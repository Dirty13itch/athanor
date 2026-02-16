# Media Stack

**Date:** 2026-02-15
**Status:** Complete — recommendation ready
**Supports:** ADR-011 (Media Stack)
**Depends on:** ADR-001 (Base Platform), ADR-003 (Storage Architecture)

---

## The Question

How does Athanor's media stack — Plex, *arr, Stash, and download clients — fit into the architecture? Where does each component run, and how does it integrate with agents and the dashboard?

---

## This Is Largely Pre-Decided

The media stack already runs on VAULT (Unraid). Plex, Sonarr, Radarr, and download clients are established Unraid Docker apps. This ADR formalizes the architecture and documents the integration points with Athanor's agent and dashboard layers.

---

## Components

### Plex Media Server

- **Runs on:** VAULT (Docker, Unraid CA)
- **Transcoding:** Arc A380 (Intel Quick Sync) — hardware transcoding for remote streaming
- **Library:** `/mnt/user/media/` on VAULT's HDD array (164 TB)
- **Port:** 32400

Plex is the streaming interface. It handles media playback, library organization, and user management. No alternative is considered — Plex works, the library is established.

### *arr Stack

| App | Purpose | Port |
|-----|---------|------|
| Sonarr | TV show management | 8989 |
| Radarr | Movie management | 7878 |
| Prowlarr | Indexer management | 9696 |
| Lidarr (optional) | Music management | 8686 |
| Readarr (optional) | Book management | 8787 |

All run as Docker containers on VAULT. Prowlarr syncs indexers to all *arr apps — configure once, used everywhere.

**Path configuration (critical):** Follow [TRaSH Guides](https://trash-guides.info/) hardlink setup for Unraid. Use a single `/data` root with separate subdirectories for downloads and media. This enables hardlinks and instant (atomic) moves between download and library directories — no copy/move overhead.

```
/mnt/user/data/
  ├── media/
  │   ├── movies/
  │   ├── tv/
  │   └── music/
  └── downloads/
      ├── usenet/
      └── torrents/
```

Sonarr/Radarr see both directories under the same mount, enabling hardlinks.

**Quality profiles:** Use TRaSH Guides' recommended custom formats and quality profiles for optimal quality/size balance. [Profilarr](https://github.com/Recyclarr/recyclarr) can automate profile syncing.

### Download Clients

| Client | Purpose | Port |
|--------|---------|------|
| SABnzbd | Usenet downloads | 8080 |
| qBittorrent | Torrent downloads | 8112 |

Both run on VAULT. Downloads go directly to VAULT's storage — no network transfer needed.

**VPN:** qBittorrent should run through a VPN container (Gluetun or similar) for torrent traffic. SABnzbd over SSL to provider is sufficient.

### Stash

- **Runs on:** VAULT (Docker)
- **Port:** 9999
- **Library:** `/mnt/user/media/adult/` on VAULT's HDD array
- **Purpose:** Adult content organization, tagging, and management

Stash (v0.30.1, Dec 2025) provides:
- Web-based library browser and player
- Auto-tagging via scene fingerprinting (StashDB)
- Metadata scraping from community databases
- Performer, studio, and tag management
- Duplicate detection
- DLNA streaming

Stash requires FFmpeg for media processing (included in the Docker image).

**Integration with agents:** The Media Agent (ADR-008) can query Stash's GraphQL API for library management — finding untagged scenes, organizing performers, generating reports.

**Sources:**
- [Stash GitHub](https://github.com/stashapp/stash)
- [Stash documentation](https://docs.stashapp.cc)
- [Stash Docker compose](https://github.com/stashapp/stash/blob/develop/docker/production/docker-compose.yml)

### Tautulli (Optional but Recommended)

- **Runs on:** VAULT (Docker)
- **Port:** 8181
- **Purpose:** Plex monitoring and statistics

Tautulli provides viewing history, user statistics, and notification triggers that Plex itself doesn't expose well. The dashboard (ADR-007) queries Tautulli's API for the media panel (now playing, recent additions, library stats).

---

## Overseerr / Jellyseerr (Optional)

Request management interface — users (or agents) can request movies/TV shows, which automatically flow to Sonarr/Radarr.

- **Runs on:** VAULT (Docker)
- **Port:** 5055
- **Value for Athanor:** The Media Agent can submit requests via Overseerr's API instead of calling Sonarr/Radarr directly. Provides a cleaner workflow with approval tracking.

---

## Agent Integration (ADR-008)

The Media Agent on Node 1 manages the entire media stack via APIs over 10GbE:

| Action | Target API | Example |
|--------|-----------|---------|
| Add a TV show | Sonarr REST API | "Download the latest season of X" |
| Add a movie | Radarr REST API | "Get the new Y movie" |
| Check download status | SABnzbd/qBit API | "What's downloading?" |
| Library stats | Tautulli API | "What's been watched this week?" |
| Adult content management | Stash GraphQL API | "Tag unorganized scenes" |
| Now playing | Plex/Tautulli API | "What's streaming right now?" |

The Media Agent can:
- Accept natural language requests ("download X") and translate to API calls
- Monitor download queues and notify on completion
- Run quality checks on library (missing metadata, low-quality files)
- Manage Stash library (auto-tag, organize, detect duplicates)
- Report library statistics to the dashboard

---

## Dashboard Integration (ADR-007)

The Media panel shows:
- Now playing (Tautulli API)
- Recent additions (Tautulli API)
- Download queue status (SABnzbd/qBit API)
- Library statistics (Tautulli API)
- Quick actions (request media, trigger library scan)

---

## Recommendation

All components run on VAULT as Docker containers. This is established infrastructure — the ADR formalizes it and documents the agent/dashboard integration points.

| Component | Priority | Notes |
|-----------|----------|-------|
| Plex | Already running | Verify Arc A380 transcoding works |
| Sonarr + Radarr | Already running (or first to deploy) | Set up TRaSH Guides path structure |
| Prowlarr | Deploy with *arr stack | Centralizes indexer management |
| SABnzbd + qBittorrent | Already running (or with *arr) | VPN for qBit |
| Stash | Deploy when ready | Adult content organization |
| Tautulli | Deploy with Plex | Monitoring and statistics |
| Overseerr | Optional, deploy later | Request management for agent integration |

---

## Sources

- [TRaSH Guides](https://trash-guides.info/) — the authoritative guide for *arr configuration
- [TRaSH Unraid hardlink setup](https://trash-guides.info/File-and-Folder-Structure/How-to-set-up/Unraid/)
- [Servarr Docker Guide](https://wiki.servarr.com/docker-guide)
- [Ultimate Plex Stack (GitHub)](https://github.com/DonMcD/ultimate-plex-stack)
- [Arr Stack Docker Compose Guide 2026](https://corelab.tech/arr-stack-docker-compose-guide/)
- [Stash GitHub](https://github.com/stashapp/stash)
- [Stash documentation](https://docs.stashapp.cc)
