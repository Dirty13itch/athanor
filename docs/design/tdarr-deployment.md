# Tdarr — Library-Wide Transcoding Deployment Plan

*Background optimization service that converts legacy codecs to save storage space and improve streaming compatibility.*

---

## What It Does

- Scans the entire media library for legacy codecs (MPEG-2, H.264, FLAC, uncompressed audio)
- Converts video to H.265 (HEVC) or AV1 where the quality/size tradeoff is favorable
- Remuxes containers when needed (e.g., AVI → MKV without re-encoding)
- Strips unnecessary audio tracks and subtitles based on language preferences
- Normalizes audio levels across the library

---

## Hardware Acceleration

- **Primary:** Intel QuickSync on the Arc A380 for H.265/AV1 hardware encode
- **Fallback:** CPU encoding on the 9950X for codecs the A380 can't handle
- The A380's QuickSync engine handles most transcoding workloads at 75W TDP
- No contention with GPU inference — the A380 is in VAULT, not a compute node

---

## Deployment

Docker container on VAULT:

```yaml
services:
  tdarr:
    image: ghcr.io/haveagitgat/tdarr:latest
    ports:
      - 8265:8265    # Web UI
    environment:
      - PUID=99
      - PGID=100
      - serverIP=0.0.0.0
      - serverPort=8266
    volumes:
      - /mnt/user/appdata/tdarr/server:/app/server
      - /mnt/user/appdata/tdarr/configs:/app/configs
      - /mnt/user/appdata/tdarr/logs:/app/logs
      - /mnt/user/data/media:/media
      - /mnt/user/appdata/tdarr/transcode_cache:/temp
    devices:
      - /dev/dri:/dev/dri    # Intel QuickSync passthrough
    restart: unless-stopped
```

---

## Scheduling and Priority

- Scheduled during low-usage hours (overnight, midnight–6 AM) to avoid Plex stream contention
- Throttled during active Plex streams — Tdarr pauses or reduces workers when Tautulli reports active sessions
- I/O scheduling matters: transcoding saturates disk throughput, should not overlap with parity checks
- Worker count: start with 1 GPU worker + 2 CPU workers, tune based on observed load

---

## Non-Destructive Workflow

1. Originals kept until conversion verified (Tdarr's built-in verification)
2. Separate output directory, then atomic move replaces original
3. Tdarr maintains a database of processed files — won't re-process unless source changes
4. Health check plugins verify output plays correctly before replacing source

---

## Storage Impact

- H.265 achieves 40-60% size reduction from H.264 at equivalent quality
- AV1 achieves 50-70% reduction but encodes much slower (better for archive, not bulk)
- VAULT HDD array at 89% capacity (146T/165T). Converting H.264 content could reclaim 30-60TB
- This directly addresses the capacity concern flagged in ADR-011

---

## Integration with *arr Stack

- New downloads from Sonarr/Radarr arrive as whatever codec the source provides
- Tdarr picks them up automatically after import completes
- Plex detects the new optimized file seamlessly (same path, updated container)

---

## Blocker

Deploy after media stack is stable and indexers are configured. Not blocked on credentials.
