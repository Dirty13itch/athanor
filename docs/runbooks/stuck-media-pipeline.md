# Stuck Media Pipeline

Source of truth: media packet, media stack health, and queue evidence

---

## Trigger

- stalled Sonarr or Radarr queue item
- unhealthy Prowlarr indexer chain
- SAB queue not progressing
- Plex or Tautulli not seeing completed imports

## Sequence

1. Check Prowlarr, then Sonarr or Radarr, then SABnzbd, then Plex and Tautulli.
2. Prefer bounded retry, pause, resume, or targeted refresh before any config mutation.
3. Keep destructive profile or downloader config changes behind explicit approval.
4. Confirm the downstream library sees the repaired item before closing the incident.

## Verify

- queue progresses again
- import completes
- library and watch surfaces recover
