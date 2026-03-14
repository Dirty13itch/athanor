"""Tools for adult content management via Stash GraphQL API."""

import httpx
from langchain_core.tools import tool

from ..services import registry

STASH_URL = registry.stash_graphql_url


def _stash_query(query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query against Stash."""
    resp = httpx.post(
        STASH_URL,
        json={"query": query, "variables": variables or {}},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data and data["errors"]:
        raise RuntimeError(data["errors"][0].get("message", "GraphQL error"))
    return data.get("data", {})


# --- Library Stats ---


@tool
def get_stash_stats() -> str:
    """Get Stash library statistics — scene count, image count, performer count, tag count, storage info."""
    try:
        data = _stash_query("""
            { stats {
                scene_count image_count gallery_count
                performer_count studio_count tag_count
                scenes_size images_size
                scenes_duration
            } }
        """)
        s = data["stats"]
        size_gb = (s.get("scenes_size", 0) + s.get("images_size", 0)) / (1024**3)
        hours = s.get("scenes_duration", 0) / 3600
        return (
            f"Stash Library Stats:\n"
            f"  Scenes: {s['scene_count']}\n"
            f"  Images: {s['image_count']}\n"
            f"  Galleries: {s['gallery_count']}\n"
            f"  Performers: {s['performer_count']}\n"
            f"  Studios: {s['studio_count']}\n"
            f"  Tags: {s['tag_count']}\n"
            f"  Total size: {size_gb:.1f} GB\n"
            f"  Total duration: {hours:.1f} hours"
        )
    except Exception as e:
        return f"Error fetching stats: {e}"


# --- Scene Search & Browse ---


@tool
def search_scenes(query: str, limit: int = 20) -> str:
    """Search Stash scenes by title, path, or details. Returns matching scenes with performers, tags, and resolution."""
    try:
        data = _stash_query("""
            query($filter: FindFilterType!) {
                findScenes(filter: $filter) {
                    count
                    scenes {
                        id title rating100
                        files { path duration width height }
                        performers { name }
                        tags { name }
                        studio { name }
                        play_count o_counter
                        organized
                    }
                }
            }
        """, {"filter": {"q": query, "per_page": limit, "sort": "title", "direction": "ASC"}})
        result = data["findScenes"]
        if not result["scenes"]:
            return f"No scenes matching '{query}'."
        lines = [f"Scene Search: '{query}' ({result['count']} total, showing {len(result['scenes'])})"]
        for sc in result["scenes"]:
            perfs = ", ".join(p["name"] for p in sc.get("performers", []))
            tags = ", ".join(t["name"] for t in (sc.get("tags", []) or [])[:5])
            f = sc.get("files", [{}])[0] if sc.get("files") else {}
            res = f"{f.get('width', '?')}x{f.get('height', '?')}" if f else "?"
            dur = f"{int(f.get('duration', 0)) // 60}min" if f.get("duration") else "?"
            rating = f"{sc.get('rating100', 0) // 20}★" if sc.get("rating100") else "—"
            org = "✓" if sc.get("organized") else "✗"
            lines.append(
                f"  [{sc['id']}] {sc.get('title') or '(untitled)'} — {res} {dur} — {rating} org:{org}"
            )
            if perfs:
                lines.append(f"       Performers: {perfs}")
            if tags:
                lines.append(f"       Tags: {tags}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching scenes: {e}"


@tool
def get_scene_details(scene_id: str) -> str:
    """Get full details for a specific scene by ID. Returns all metadata, file info, and streaming URL."""
    try:
        data = _stash_query("""
            query($id: ID!) {
                findScene(id: $id) {
                    id title details rating100 url
                    files { path duration width height size video_codec audio_codec bit_rate frame_rate }
                    performers { id name }
                    tags { id name }
                    studio { id name }
                    groups { group { id name } }
                    play_count o_counter play_duration
                    organized created_at updated_at
                    paths { screenshot stream preview }
                }
            }
        """, {"id": scene_id})
        sc = data.get("findScene")
        if not sc:
            return f"Scene {scene_id} not found."
        f = sc.get("files", [{}])[0] if sc.get("files") else {}
        perfs = ", ".join(p["name"] for p in sc.get("performers", []))
        tags = ", ".join(t["name"] for t in sc.get("tags", []))
        studio = sc.get("studio", {}).get("name", "—") if sc.get("studio") else "—"
        size_mb = f.get("size", 0) / (1024**2) if f.get("size") else 0
        lines = [
            f"Scene: {sc.get('title') or '(untitled)'} [ID: {sc['id']}]",
            f"  Studio: {studio}",
            f"  Performers: {perfs or '—'}",
            f"  Tags: {tags or '—'}",
            f"  Rating: {sc.get('rating100', 0) // 20}/5" if sc.get("rating100") else "  Rating: —",
            f"  File: {f.get('width', '?')}x{f.get('height', '?')} {f.get('video_codec', '?')} {size_mb:.0f} MB",
            f"  Duration: {int(f.get('duration', 0)) // 60}:{int(f.get('duration', 0)) % 60:02d}" if f.get("duration") else "  Duration: —",
            f"  Play count: {sc.get('play_count', 0)} | O-counter: {sc.get('o_counter', 0)}",
            f"  Organized: {'Yes' if sc.get('organized') else 'No'}",
        ]
        if sc.get("details"):
            lines.append(f"  Details: {sc['details'][:300]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching scene details: {e}"


# --- Performer Management ---


@tool
def search_performers(query: str, limit: int = 20) -> str:
    """Search Stash performers by name. Returns performers with scene count and basic info."""
    try:
        data = _stash_query("""
            query($filter: FindFilterType!) {
                findPerformers(filter: $filter) {
                    count
                    performers {
                        id name disambiguation gender
                        scene_count image_count
                        favorite
                        tags { name }
                    }
                }
            }
        """, {"filter": {"q": query, "per_page": limit, "sort": "name", "direction": "ASC"}})
        result = data["findPerformers"]
        if not result["performers"]:
            return f"No performers matching '{query}'."
        lines = [f"Performer Search: '{query}' ({result['count']} total)"]
        for p in result["performers"]:
            fav = "★" if p.get("favorite") else ""
            tags = ", ".join(t["name"] for t in (p.get("tags", []) or [])[:3])
            lines.append(
                f"  [{p['id']}] {p['name']} {fav} — {p.get('scene_count', 0)} scenes"
                + (f" — {tags}" if tags else "")
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching performers: {e}"


# --- Tag Management ---


@tool
def list_tags(limit: int = 50) -> str:
    """List all tags in Stash sorted by scene count. Shows tag names, scene counts, and descriptions."""
    try:
        data = _stash_query("""
            query($filter: FindFilterType!) {
                findTags(filter: $filter) {
                    count
                    tags { id name description scene_count image_count }
                }
            }
        """, {"filter": {"per_page": limit, "sort": "scenes_count", "direction": "DESC"}})
        result = data["findTags"]
        if not result["tags"]:
            return "No tags found."
        lines = [f"Tags ({result['count']} total, showing top {len(result['tags'])} by scene count):"]
        for t in result["tags"]:
            lines.append(f"  [{t['id']}] {t['name']}: {t.get('scene_count', 0)} scenes")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tags: {e}"


# --- Duplicate Detection ---


@tool
def find_duplicates() -> str:
    """Find duplicate scenes in Stash using perceptual hash matching. Returns groups of potential duplicates."""
    try:
        data = _stash_query("""
            { findDuplicateScenes(distance: MEDIUM) {
                __typename
                ... on Scene {
                    id title
                    files { path duration width height size }
                    performers { name }
                }
            } }
        """)
        # findDuplicateScenes returns groups of duplicates
        groups = data.get("findDuplicateScenes", [])
        if not groups:
            return "No duplicate scenes found."
        lines = [f"Duplicate Groups Found: {len(groups)}"]
        for i, group in enumerate(groups[:10]):
            if isinstance(group, list):
                lines.append(f"\n  Group {i + 1}:")
                for sc in group:
                    f = sc.get("files", [{}])[0] if sc.get("files") else {}
                    size_mb = f.get("size", 0) / (1024**2) if f.get("size") else 0
                    lines.append(
                        f"    [{sc['id']}] {sc.get('title') or '(untitled)'} — "
                        f"{f.get('width', '?')}x{f.get('height', '?')} {size_mb:.0f} MB"
                    )
        return "\n".join(lines)
    except Exception as e:
        return f"Error finding duplicates: {e}"


# --- Task Management ---


@tool
def scan_library() -> str:
    """Trigger a full library scan in Stash. Discovers new files and updates metadata."""
    try:
        data = _stash_query("""
            mutation { metadataScan(input: {}) }
        """)
        job_id = data.get("metadataScan", "unknown")
        return f"Library scan started (job ID: {job_id}). Check Stash UI for progress."
    except Exception as e:
        return f"Error starting scan: {e}"


@tool
def auto_tag() -> str:
    """Run Stash auto-tagger — matches performers, studios, and tags based on filenames and paths."""
    try:
        data = _stash_query("""
            mutation { metadataAutoTag(input: {}) }
        """)
        job_id = data.get("metadataAutoTag", "unknown")
        return f"Auto-tag started (job ID: {job_id}). Check Stash UI for progress."
    except Exception as e:
        return f"Error starting auto-tag: {e}"


@tool
def generate_content() -> str:
    """Generate thumbnails, previews, sprites, and phash for all scenes. Required for duplicate detection and browsing."""
    try:
        data = _stash_query("""
            mutation { metadataGenerate(input: {
                sprites: true, previews: true, markers: true,
                phashes: true, interactiveHeatmapsSpeeds: false
            }) }
        """)
        job_id = data.get("metadataGenerate", "unknown")
        return f"Content generation started (job ID: {job_id}). This may take a while for large libraries."
    except Exception as e:
        return f"Error starting generation: {e}"


# --- Scene Updates ---


@tool
def update_scene_rating(scene_id: str, rating: int) -> str:
    """Set a scene's rating (1-5 stars). Internally stored as rating100 (20-100)."""
    try:
        if not 1 <= rating <= 5:
            return "Rating must be between 1 and 5."
        rating100 = rating * 20
        data = _stash_query("""
            mutation($id: ID!, $rating: Int) {
                sceneUpdate(input: { id: $id, rating100: $rating }) { id title rating100 }
            }
        """, {"id": scene_id, "rating": rating100})
        sc = data.get("sceneUpdate", {})
        return f"Updated scene {sc.get('title', scene_id)} rating to {rating}/5."
    except Exception as e:
        return f"Error updating rating: {e}"


@tool
def mark_scene_organized(scene_id: str) -> str:
    """Mark a scene as organized (metadata reviewed and confirmed)."""
    try:
        data = _stash_query("""
            mutation($id: ID!) {
                sceneUpdate(input: { id: $id, organized: true }) { id title organized }
            }
        """, {"id": scene_id})
        sc = data.get("sceneUpdate", {})
        return f"Scene '{sc.get('title', scene_id)}' marked as organized."
    except Exception as e:
        return f"Error marking organized: {e}"


@tool
def get_recent_scenes(limit: int = 20) -> str:
    """Get recently added scenes, sorted by creation date. Good for checking new content."""
    try:
        data = _stash_query("""
            query($filter: FindFilterType!) {
                findScenes(filter: $filter) {
                    count
                    scenes {
                        id title created_at
                        files { path duration width height }
                        performers { name }
                        studio { name }
                        organized play_count
                    }
                }
            }
        """, {"filter": {"per_page": limit, "sort": "created_at", "direction": "DESC"}})
        result = data["findScenes"]
        if not result["scenes"]:
            return "No scenes in library."
        lines = [f"Recent Scenes ({result['count']} total, showing {len(result['scenes'])}):"]
        for sc in result["scenes"]:
            perfs = ", ".join(p["name"] for p in sc.get("performers", []))
            studio = sc.get("studio", {}).get("name", "") if sc.get("studio") else ""
            f = sc.get("files", [{}])[0] if sc.get("files") else {}
            res = f"{f.get('width', '?')}x{f.get('height', '?')}" if f else "?"
            org = "✓" if sc.get("organized") else "✗"
            date = sc.get("created_at", "?")[:10]
            lines.append(
                f"  [{sc['id']}] {date} — {sc.get('title') or '(untitled)'} — {res} org:{org}"
            )
            if perfs or studio:
                lines.append(f"       {studio}{' — ' if studio and perfs else ''}{perfs}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching recent scenes: {e}"


@tool
def create_tag(name: str, description: str = "") -> str:
    """Create a new tag in Stash.

    Args:
        name: Tag name (e.g. "blonde", "outdoor", "POV")
        description: Optional description of what this tag represents
    """
    try:
        inp: dict = {"name": name}
        if description:
            inp["description"] = description
        data = _stash_query("""
            mutation($input: TagCreateInput!) {
                tagCreate(input: $input) { id name description }
            }
        """, {"input": inp})
        tag = data.get("tagCreate", {})
        return f"Tag created: [{tag['id']}] {tag['name']}"
    except Exception as e:
        return f"Error creating tag: {e}"


@tool
def tag_scenes(scene_ids: list[str], tag_names: list[str], mode: str = "add") -> str:
    """Add or remove tags from one or more scenes.

    Args:
        scene_ids: List of scene IDs to modify
        tag_names: List of tag names to add/remove
        mode: "add" to add tags, "remove" to remove tags
    """
    if mode not in ("add", "remove"):
        return "Mode must be 'add' or 'remove'."
    try:
        # Resolve tag names to IDs
        tag_ids = []
        for name in tag_names:
            data = _stash_query("""
                query($filter: FindFilterType!) {
                    findTags(filter: $filter) { tags { id name } }
                }
            """, {"filter": {"q": name, "per_page": 5}})
            tags = data.get("findTags", {}).get("tags", [])
            match = next((t for t in tags if t["name"].lower() == name.lower()), None)
            if not match:
                return f"Tag not found: '{name}'. Create it first with create_tag."
            tag_ids.append(match["id"])

        results = []
        for sid in scene_ids:
            # Get current tags
            scene_data = _stash_query("""
                query($id: ID!) { findScene(id: $id) { id title tags { id } } }
            """, {"id": sid})
            scene = scene_data.get("findScene")
            if not scene:
                results.append(f"Scene {sid}: not found")
                continue
            current_ids = [t["id"] for t in scene.get("tags", [])]
            if mode == "add":
                new_ids = list(set(current_ids + tag_ids))
            else:
                new_ids = [tid for tid in current_ids if tid not in tag_ids]

            _stash_query("""
                mutation($id: ID!, $tag_ids: [ID!]) {
                    sceneUpdate(input: { id: $id, tag_ids: $tag_ids }) { id title }
                }
            """, {"id": sid, "tag_ids": new_ids})
            results.append(f"Scene {sid} ({scene.get('title', '?')}): {mode}ed {len(tag_ids)} tags")

        return "\n".join(results)
    except Exception as e:
        return f"Error tagging scenes: {e}"


@tool
def delete_tag(tag_name: str) -> str:
    """Delete a tag from Stash. Removes the tag from all scenes.

    Args:
        tag_name: Exact name of the tag to delete
    """
    try:
        data = _stash_query("""
            query($filter: FindFilterType!) {
                findTags(filter: $filter) { tags { id name scene_count } }
            }
        """, {"filter": {"q": tag_name, "per_page": 5}})
        tags = data.get("findTags", {}).get("tags", [])
        match = next((t for t in tags if t["name"].lower() == tag_name.lower()), None)
        if not match:
            return f"Tag not found: '{tag_name}'"

        _stash_query("""
            mutation($input: TagDestroyInput!) { tagDestroy(input: $input) }
        """, {"input": {"id": match["id"]}})
        return f"Tag deleted: [{match['id']}] {match['name']} (was on {match.get('scene_count', 0)} scenes)"
    except Exception as e:
        return f"Error deleting tag: {e}"


STASH_TOOLS = [
    get_stash_stats,
    search_scenes,
    get_scene_details,
    search_performers,
    list_tags,
    create_tag,
    tag_scenes,
    delete_tag,
    find_duplicates,
    scan_library,
    auto_tag,
    generate_content,
    update_scene_rating,
    mark_scene_organized,
    get_recent_scenes,
]
