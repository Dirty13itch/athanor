# ADR-011: Media Stack

**Date:** 2026-02-15
**Status:** Accepted
**Research:** [docs/research/2026-02-15-media-stack.md](../research/2026-02-15-media-stack.md)
**Depends on:** ADR-001 (Base Platform), ADR-003 (Storage Architecture)

---

## Context

Athanor's media stack — Plex, *arr apps, Stash, and download clients — is established infrastructure on VAULT (Unraid). This ADR formalizes the architecture, documents the path structure, and defines integration points with Athanor's agent and dashboard layers. There's no technology decision to make — the components are well-established and already partially running.

---

## Decision

### Full media stack on VAULT with TRaSH Guides path structure and agent/dashboard API integration.

#### Components

| Service | Image | Port | GPU | Purpose |
|---------|-------|------|-----|---------|
| Plex | plexinc/pms-docker | 32400 | Arc A380 (Quick Sync) | Media streaming + transcoding |
| Sonarr | linuxserver/sonarr | 8989 | — | TV show management |
| Radarr | linuxserver/radarr | 7878 | — | Movie management |
| Prowlarr | linuxserver/prowlarr | 9696 | — | Indexer management |
| SABnzbd | linuxserver/sabnzbd | 8080 | — | Usenet downloads |
| qBittorrent | linuxserver/qbittorrent | 8112 | — | Torrent downloads (via VPN) |
| Stash | stashapp/stash | 9999 | — | Adult content management |
| Tautulli | linuxserver/tautulli | 8181 | — | Plex monitoring/statistics |
| Overseerr | linuxserver/overseerr | 5055 | — | Request management (optional) |

All run as Docker containers on VAULT. All are available in Unraid Community Apps.

#### Path Structure

Following [TRaSH Guides for Unraid](https://trash-guides.info/File-and-Folder-Structure/How-to-set-up/Unraid/) — enables hardlinks and atomic moves:

```
/mnt/user/data/
  ├── media/
  │   ├── movies/
  │   ├── tv/
  │   ├── music/
  │   └── adult/        ← Stash library
  └── downloads/
      ├── usenet/
      │   ├── complete/
      │   └── incomplete/
      └── torrents/
          ├── complete/
          └── incomplete/
```

All *arr apps and download clients mount `/mnt/user/data` as a single volume. This keeps downloads and media on the same filesystem, enabling hardlinks (no copy, no extra disk space) when Sonarr/Radarr import completed downloads.

#### VPN for Torrents

qBittorrent routes through a VPN container (Gluetun):

```yaml
services:
  gluetun:
    image: qmcgaw/gluetun
    cap_add:
      - NET_ADMIN
    environment:
      - VPN_SERVICE_PROVIDER=...
      - VPN_TYPE=wireguard
    ports:
      - 8112:8112  # qBit WebUI exposed through Gluetun

  qbittorrent:
    image: linuxserver/qbittorrent
    network_mode: "service:gluetun"  # All traffic through VPN
```

SABnzbd connects directly to Usenet providers over SSL — no VPN needed.

---

## Agent Integration

The Media Agent (ADR-008) manages the entire stack via REST/GraphQL APIs:

| Capability | API | Example Request |
|-----------|-----|-----------------|
| Request TV show | Sonarr v3 API | "Download Severance season 3" |
| Request movie | Radarr v3 API | "Get Oppenheimer in 4K" |
| Check downloads | SABnzbd/qBit API | "What's downloading right now?" |
| Library stats | Tautulli API | "How many movies do we have?" |
| Now playing | Tautulli API | "What's streaming?" |
| Organize adult content | Stash GraphQL API | "Tag unmatched scenes" |
| Submit request | Overseerr API | "Request this title" |

All APIs are authenticated via API keys stored in environment variables. The Media Agent on Node 1 reaches VAULT over 5GbE.

---

## Dashboard Integration

The Media panel in Athanor's dashboard (ADR-007) shows:

| Widget | Data Source | Update |
|--------|------------|--------|
| Now Playing | Tautulli WebSocket API | Real-time |
| Recent Additions | Tautulli API | Polling (5 min) |
| Download Queue | SABnzbd + qBit API | Polling (30s) |
| Library Stats | Tautulli API | Polling (1 hour) |
| Quick Request | Overseerr API | On-demand |

---

## What This Enables

- **Natural language media management** — "download the new X" flows through agent → Sonarr/Radarr → download client → library
- **Automated quality management** — TRaSH custom formats ensure optimal quality/size
- **Always-on media** — VAULT runs 24/7, Plex streams while compute nodes may be off
- **Hardware transcoding** — Arc A380 Quick Sync handles remote streaming without CPU load
- **Adult content organization** — Stash provides proper management with auto-tagging, not a file dump
- **Dashboard visibility** — see what's streaming, downloading, and recently added at a glance
- **Hardlinks** — no wasted disk space for imported media, instant moves

---

## Alternatives Considered

| Alternative | Why Not |
|-------------|---------|
| Jellyfin instead of Plex | Valid alternative, but Plex library is established. Migration cost for no clear benefit. Revisit if Plex pricing/licensing becomes problematic. |
| No Stash | Adult content is a significant use case (VISION.md). File dumps without organization become unmanageable. Stash provides proper tagging and discovery. |
| Media on compute nodes | Media is storage-bound, not GPU-bound. VAULT is the storage server. Moving media services to compute nodes wastes their GPU resources and requires 24/7 uptime. |

---

## Risks

- **VAULT HDD capacity.** 164 TB with 18 TB free (90% full). Media growth will consume this within a year. Plan for 1-2 additional 24 TB HDDs (see ADR-003).
- **Plex Pass requirement.** Hardware transcoding requires Plex Pass (lifetime purchase or subscription). Already purchased or needs to be.
- **Arc A380 transcoding compatibility.** Intel Quick Sync on Arc should work for Plex but verify driver compatibility on Unraid.

---

## Sources

- [TRaSH Guides](https://trash-guides.info/)
- [TRaSH Unraid hardlink setup](https://trash-guides.info/File-and-Folder-Structure/How-to-set-up/Unraid/)
- [Servarr Docker Guide](https://wiki.servarr.com/docker-guide)
- [Arr Stack Docker Compose Guide 2026](https://corelab.tech/arr-stack-docker-compose-guide/)
- [Stash GitHub](https://github.com/stashapp/stash)
- [Stash documentation](https://docs.stashapp.cc)
