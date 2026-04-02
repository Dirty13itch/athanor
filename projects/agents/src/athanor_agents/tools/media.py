import httpx
from langchain_core.tools import tool

from ..config import settings
from ..services import registry

SONARR = registry.sonarr_api_url
RADARR = registry.radarr_api_url
PROWLARR = registry.prowlarr_api_url
SABNZBD = registry.sabnzbd_api_url
TAUTULLI = registry.tautulli_api_url


def _sonarr_get(path: str, params: dict | None = None) -> dict:
    p = {"apikey": settings.sonarr_api_key, **(params or {})}
    resp = httpx.get(f"{SONARR}{path}", params=p, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _radarr_get(path: str, params: dict | None = None) -> dict:
    p = {"apikey": settings.radarr_api_key, **(params or {})}
    resp = httpx.get(f"{RADARR}{path}", params=p, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _sonarr_post(path: str, json_data: dict) -> dict:
    resp = httpx.post(
        f"{SONARR}{path}",
        params={"apikey": settings.sonarr_api_key},
        json=json_data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _radarr_post(path: str, json_data: dict) -> dict:
    resp = httpx.post(
        f"{RADARR}{path}",
        params={"apikey": settings.radarr_api_key},
        json=json_data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _tautulli_get(cmd: str, params: dict | None = None) -> dict:
    p = {"apikey": settings.tautulli_api_key, "cmd": cmd, **(params or {})}
    resp = httpx.get(TAUTULLI, params=p, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _prowlarr_get(path: str, params: dict | None = None) -> dict | list:
    if not settings.prowlarr_api_key:
        raise RuntimeError("ATHANOR_PROWLARR_API_KEY is not configured")
    resp = httpx.get(
        f"{PROWLARR}{path}",
        params=params or {},
        headers={"X-Api-Key": settings.prowlarr_api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _sabnzbd_request(params: dict | None = None) -> dict:
    if not settings.sabnzbd_api_key:
        raise RuntimeError("ATHANOR_SABNZBD_API_KEY is not configured")
    request_params = {
        "apikey": settings.sabnzbd_api_key,
        "output": "json",
        **(params or {}),
    }
    resp = httpx.get(SABNZBD, params=request_params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# --- Sonarr Tools ---


@tool
def search_tv_shows(query: str) -> str:
    """Search for a TV show by name in Sonarr's lookup. Returns matching shows with year, status, and whether they're already in the library."""
    try:
        results = _sonarr_get("/series/lookup", {"term": query})
        if not results:
            return f"No TV shows found matching '{query}'."
        lines = [f"TV Show Search: '{query}' ({len(results)} results)"]
        for s in results[:10]:
            in_lib = "IN LIBRARY" if s.get("id") else "not added"
            lines.append(
                f"  - {s['title']} ({s.get('year', '?')}) — {s.get('status', '?')} — {in_lib} — TVDB: {s.get('tvdbId', '?')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching Sonarr: {e}"


@tool
def get_tv_calendar(days: int = 7) -> str:
    """Get upcoming TV episodes from Sonarr for the next N days (default 7). Shows air dates and episode info."""
    try:
        from datetime import datetime, timedelta

        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        episodes = _sonarr_get("/calendar", {"start": start, "end": end})
        if not episodes:
            return f"No episodes scheduled in the next {days} days."
        lines = [f"TV Calendar (next {days} days, {len(episodes)} episodes):"]
        for ep in episodes[:20]:
            series = ep.get("series", {}).get("title", "?")
            s_num = ep.get("seasonNumber", "?")
            e_num = ep.get("episodeNumber", "?")
            title = ep.get("title", "TBA")
            air = ep.get("airDateUtc", "?")[:10]
            lines.append(f"  {air} — {series} S{s_num:02d}E{e_num:02d} '{title}'")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching TV calendar: {e}"


@tool
def get_tv_queue() -> str:
    """Get the current Sonarr download queue — shows what's downloading, progress, and ETA."""
    try:
        data = _sonarr_get("/queue", {"pageSize": 20})
        records = data.get("records", [])
        if not records:
            return "Sonarr download queue is empty."
        lines = [f"Sonarr Queue ({len(records)} items):"]
        for r in records:
            title = r.get("title", "?")
            pct = r.get("sizeleft", 0)
            size = r.get("size", 1)
            progress = ((size - pct) / size * 100) if size else 0
            status = r.get("status", "?")
            lines.append(f"  - {title}: {progress:.0f}% — {status}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching Sonarr queue: {e}"


@tool
def get_tv_library() -> str:
    """Get an overview of the Sonarr TV library — total shows, episodes, storage used."""
    try:
        series = _sonarr_get("/series")
        total = len(series)
        monitored = sum(1 for s in series if s.get("monitored"))
        episodes = sum(s.get("statistics", {}).get("episodeFileCount", 0) for s in series)
        size_gb = sum(s.get("statistics", {}).get("sizeOnDisk", 0) for s in series) / (1024**3)
        continuing = sum(1 for s in series if s.get("status") == "continuing")
        lines = [
            f"TV Library: {total} shows ({monitored} monitored, {continuing} continuing)",
            f"  Episodes on disk: {episodes}",
            f"  Total size: {size_gb:.1f} GB",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching TV library: {e}"


@tool
def add_tv_show(tvdb_id: int) -> str:
    """Add a TV show to Sonarr by its TVDB ID. Use search_tv_shows first to find the TVDB ID. Adds monitored with automatic quality profile."""
    try:
        lookup = _sonarr_get("/series/lookup", {"term": f"tvdb:{tvdb_id}"})
        if not lookup:
            return f"No show found with TVDB ID {tvdb_id}."
        show = lookup[0]
        if show.get("id"):
            return f"'{show['title']}' is already in the library."

        profiles = _sonarr_get("/qualityprofile")
        profile_id = profiles[0]["id"] if profiles else 1
        root_folders = _sonarr_get("/rootfolder")
        root_path = root_folders[0]["path"] if root_folders else "/data/media/tv"

        payload = {
            "title": show["title"],
            "tvdbId": tvdb_id,
            "qualityProfileId": profile_id,
            "rootFolderPath": root_path,
            "monitored": True,
            "addOptions": {"searchForMissingEpisodes": True},
            "images": show.get("images", []),
            "seasons": show.get("seasons", []),
        }
        result = _sonarr_post("/series", payload)
        return f"Added '{result['title']}' to Sonarr (ID: {result['id']}). Searching for episodes."
    except httpx.HTTPStatusError as e:
        return f"Failed to add show: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Error adding show: {e}"


# --- Radarr Tools ---


@tool
def search_movies(query: str) -> str:
    """Search for a movie by name in Radarr's lookup. Returns matching movies with year, status, and whether they're already in the library."""
    try:
        results = _radarr_get("/movie/lookup", {"term": query})
        if not results:
            return f"No movies found matching '{query}'."
        lines = [f"Movie Search: '{query}' ({len(results)} results)"]
        for m in results[:10]:
            in_lib = "IN LIBRARY" if m.get("id") else "not added"
            lines.append(
                f"  - {m['title']} ({m.get('year', '?')}) — {in_lib} — TMDB: {m.get('tmdbId', '?')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching Radarr: {e}"


@tool
def get_movie_calendar(days: int = 30) -> str:
    """Get upcoming movie releases from Radarr for the next N days (default 30)."""
    try:
        from datetime import datetime, timedelta

        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        movies = _radarr_get("/calendar", {"start": start, "end": end})
        if not movies:
            return f"No movie releases in the next {days} days."
        lines = [f"Movie Calendar (next {days} days, {len(movies)} releases):"]
        for m in movies[:20]:
            title = m.get("title", "?")
            year = m.get("year", "?")
            date = m.get("digitalRelease") or m.get("physicalRelease") or "TBA"
            if date != "TBA":
                date = date[:10]
            lines.append(f"  {date} — {title} ({year})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching movie calendar: {e}"


@tool
def get_movie_queue() -> str:
    """Get the current Radarr download queue — shows what's downloading, progress, and status."""
    try:
        data = _radarr_get("/queue", {"pageSize": 20})
        records = data.get("records", [])
        if not records:
            return "Radarr download queue is empty."
        lines = [f"Radarr Queue ({len(records)} items):"]
        for r in records:
            title = r.get("title", "?")
            pct = r.get("sizeleft", 0)
            size = r.get("size", 1)
            progress = ((size - pct) / size * 100) if size else 0
            status = r.get("status", "?")
            lines.append(f"  - {title}: {progress:.0f}% — {status}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching Radarr queue: {e}"


@tool
def get_movie_library() -> str:
    """Get an overview of the Radarr movie library — total movies, monitored, storage used."""
    try:
        movies = _radarr_get("/movie")
        total = len(movies)
        monitored = sum(1 for m in movies if m.get("monitored"))
        has_file = sum(1 for m in movies if m.get("hasFile"))
        size_gb = sum(m.get("sizeOnDisk", 0) for m in movies) / (1024**3)
        lines = [
            f"Movie Library: {total} movies ({monitored} monitored, {has_file} downloaded)",
            f"  Total size: {size_gb:.1f} GB",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching movie library: {e}"


@tool
def add_movie(tmdb_id: int) -> str:
    """Add a movie to Radarr by its TMDB ID. Use search_movies first to find the TMDB ID. Adds monitored and triggers automatic search."""
    try:
        lookup = _radarr_get("/movie/lookup", {"term": f"tmdb:{tmdb_id}"})
        if not lookup:
            return f"No movie found with TMDB ID {tmdb_id}."
        movie = lookup[0] if isinstance(lookup, list) else lookup
        if movie.get("id"):
            return f"'{movie['title']}' is already in the library."

        profiles = _radarr_get("/qualityprofile")
        profile_id = profiles[0]["id"] if profiles else 1
        root_folders = _radarr_get("/rootfolder")
        root_path = root_folders[0]["path"] if root_folders else "/data/media/movies"

        payload = {
            "title": movie["title"],
            "tmdbId": tmdb_id,
            "year": movie.get("year"),
            "qualityProfileId": profile_id,
            "rootFolderPath": root_path,
            "monitored": True,
            "addOptions": {"searchForMovie": True},
            "images": movie.get("images", []),
        }
        result = _radarr_post("/movie", payload)
        return f"Added '{result['title']}' to Radarr (ID: {result['id']}). Searching for download."
    except httpx.HTTPStatusError as e:
        return f"Failed to add movie: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Error adding movie: {e}"


# --- Tautulli Tools ---


@tool
def get_plex_activity() -> str:
    """Check what's currently playing on Plex via Tautulli. Shows active streams, users, and what they're watching."""
    try:
        data = _tautulli_get("get_activity")
        result = data.get("response", {}).get("data", {})
        sessions = result.get("sessions", [])
        count = result.get("stream_count", 0)
        if not sessions:
            return "No active Plex streams."
        lines = [f"Plex Activity ({count} active streams):"]
        for s in sessions:
            user = s.get("friendly_name", "?")
            title = s.get("full_title", s.get("title", "?"))
            state = s.get("state", "?")
            quality = s.get("quality_profile", "?")
            progress = s.get("progress_percent", "?")
            lines.append(f"  - {user}: {title} ({state}, {progress}%, {quality})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching Plex activity: {e}"


@tool
def get_watch_history(count: int = 10) -> str:
    """Get recent Plex watch history via Tautulli. Shows the last N items watched (default 10)."""
    try:
        data = _tautulli_get("get_history", {"length": str(count)})
        records = data.get("response", {}).get("data", {}).get("data", [])
        if not records:
            return "No watch history available."
        lines = [f"Recent Watch History ({len(records)} items):"]
        for r in records:
            user = r.get("friendly_name", "?")
            title = r.get("full_title", r.get("title", "?"))
            date = r.get("date", "?")
            duration = int(r.get("duration", 0)) // 60
            watched = int(r.get("watched_status", 0))
            status = "watched" if watched else "partial"
            lines.append(f"  {date} — {user}: {title} ({duration} min, {status})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching watch history: {e}"


@tool
def get_plex_libraries() -> str:
    """Get Plex library statistics via Tautulli — shows library sections, item counts, and total size."""
    try:
        data = _tautulli_get("get_libraries")
        libs = data.get("response", {}).get("data", [])
        if not libs:
            return "No Plex libraries found."
        lines = ["Plex Libraries:"]
        for lib in libs:
            name = lib.get("section_name", "?")
            stype = lib.get("section_type", "?")
            count = lib.get("count", "?")
            lines.append(f"  - {name} ({stype}): {count} items")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching Plex libraries: {e}"


@tool
def get_prowlarr_health() -> str:
    """Get Prowlarr health status and active warnings/errors from the authenticated /api/v1/health endpoint."""
    try:
        payload = _prowlarr_get("/health")
        if not isinstance(payload, list):
            return f"Prowlarr health returned unexpected payload: {payload!r}"
        if not payload:
            return "Prowlarr health is clean. No active warnings or errors."
        lines = [f"Prowlarr Health ({len(payload)} issues):"]
        for item in payload[:20]:
            source = item.get("source") or item.get("type") or "unknown"
            level = item.get("type") or item.get("severity") or "notice"
            message = item.get("message") or item.get("messageTemplate") or "No message"
            lines.append(f"  - {level} [{source}]: {message}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching Prowlarr health: {e}"


@tool
def get_sabnzbd_queue(limit: int = 10) -> str:
    """Get the active SABnzbd queue with progress, status, category, and remaining time."""
    try:
        payload = _sabnzbd_request({"mode": "queue", "limit": limit})
        queue = payload.get("queue", {})
        slots = queue.get("slots", [])
        if not slots:
            status = queue.get("status", "Idle")
            return f"SABnzbd queue is empty. Status: {status}."
        lines = [
            f"SABnzbd Queue ({len(slots)} items, status={queue.get('status', '?')}, speed={queue.get('speed', '?')})"
        ]
        for slot in slots[:limit]:
            filename = slot.get("filename", "?")
            status = slot.get("status", "?")
            percentage = slot.get("percentage", "?")
            time_left = slot.get("timeleft", "?")
            category = slot.get("cat", "?")
            nzo_id = slot.get("nzo_id", "?")
            lines.append(
                f"  - {filename}: {status}, {percentage}% complete, {time_left} left, cat={category}, nzo_id={nzo_id}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching SABnzbd queue: {e}"


@tool
def pause_sabnzbd_queue() -> str:
    """Pause the entire SABnzbd download queue."""
    try:
        payload = _sabnzbd_request({"mode": "pause"})
        status = payload.get("status")
        return "Paused the SABnzbd queue." if status else f"SABnzbd did not confirm pause: {payload}"
    except Exception as e:
        return f"Error pausing SABnzbd queue: {e}"


@tool
def resume_sabnzbd_queue() -> str:
    """Resume the entire SABnzbd download queue."""
    try:
        payload = _sabnzbd_request({"mode": "resume"})
        status = payload.get("status")
        return "Resumed the SABnzbd queue." if status else f"SABnzbd did not confirm resume: {payload}"
    except Exception as e:
        return f"Error resuming SABnzbd queue: {e}"


MEDIA_TOOLS = [
    search_tv_shows,
    get_tv_calendar,
    get_tv_queue,
    get_tv_library,
    add_tv_show,
    search_movies,
    get_movie_calendar,
    get_movie_queue,
    get_movie_library,
    add_movie,
    get_prowlarr_health,
    get_sabnzbd_queue,
    pause_sabnzbd_queue,
    resume_sabnzbd_queue,
    get_plex_activity,
    get_watch_history,
    get_plex_libraries,
]
