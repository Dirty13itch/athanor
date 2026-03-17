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



# --- EoBQ Queen Reference Photo Tools ---

# 21 queen performer references (from projects/eoq/src/data/queens.ts)
EOQB_QUEEN_PERFORMERS = [
    "Emilie Ekstrom", "Jordan Night", "Alanah Rae", "Nikki Benz",
    "Chloe Lamour", "Nicolette Shea", "Peta Jensen", "Sandee Westgate",
    "Marisol Yotta", "Trina Michaels", "Nikki Sexx", "Madison Ivy",
    "Amy Anderssen", "Puma Swede", "Ava Addams", "Brooklyn Chase",
    "Esperanza Gomez", "Savannah Bond", "Shyla Stylez", "Brianna Banks",
    "Clanddi Jinkcebo",
]


@tool
def check_queen_references() -> str:
    """Check which EoBQ queens have real profile photos in Stash.

    Returns a table showing each queen's performer reference status:
    which have real images (suitable for PuLID face injection) and
    which are missing or have placeholder images.
    """
    results = []
    for name in EOQB_QUEEN_PERFORMERS:
        try:
            # Find performer
            data = _stash_query("""
                query ($name: String!) {
                    findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}}) {
                        count performers { id name scene_count image_count }
                    }
                }
            """, {"name": name})
            performers = data.get("findPerformers", {}).get("performers", [])

            if not performers:
                results.append(f"  {name}: NOT FOUND in Stash")
                continue

            p = performers[0]

            # Check if has real image (not placeholder)
            missing_data = _stash_query("""
                query ($name: String!) {
                    findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}, is_missing: "image"}) {
                        count
                    }
                }
            """, {"name": name})
            has_real_image = missing_data.get("findPerformers", {}).get("count", 1) == 0

            status = "HAS PHOTO" if has_real_image else "NO PHOTO"
            results.append(f"  {name}: {status} ({p.get('scene_count', 0)} scenes, {p.get('image_count', 0)} images)")

        except Exception as e:
            results.append(f"  {name}: ERROR ({e})")

    with_photos = sum(1 for r in results if "HAS PHOTO" in r)
    total = len(EOQB_QUEEN_PERFORMERS)
    header = f"EoBQ Queen Reference Photos: {with_photos}/{total} have real profile images\n"
    return header + "\n".join(results)


@tool
def get_performer_reference_photo(performer_name: str) -> str:
    """Get the best reference photo URL for a performer (for PuLID face injection).

    Returns the performer's profile image URL if they have a real photo,
    or the URL of their highest-rated scene screenshot as a fallback.

    Args:
        performer_name: Exact performer name as it appears in Stash
    """
    try:
        data = _stash_query("""
            query ($name: String!) {
                findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}}) {
                    performers { id name image_path }
                }
            }
        """, {"name": performer_name})
        performers = data.get("findPerformers", {}).get("performers", [])
        if not performers:
            return f"Performer '{performer_name}' not found in Stash"

        p = performers[0]

        # Check if has real image
        missing = _stash_query("""
            query ($name: String!) {
                findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}, is_missing: "image"}) { count }
            }
        """, {"name": performer_name})
        has_image = missing.get("findPerformers", {}).get("count", 1) == 0

        if has_image and p.get("image_path"):
            return f"Profile image: {p['image_path']}"

        # Fallback: get best scene screenshot
        scenes = _stash_query("""
            query ($id: [ID!]) {
                findScenes(scene_filter: {performers: {value: $id, modifier: INCLUDES}}, filter: {per_page: 5, sort: "rating100", direction: DESC}) {
                    scenes { id title paths { screenshot } rating100 }
                }
            }
        """, {"id": [p["id"]]})
        scene_list = scenes.get("findScenes", {}).get("scenes", [])
        if scene_list and scene_list[0].get("paths", {}).get("screenshot"):
            s = scene_list[0]
            return f"Scene screenshot (rating {s.get('rating100', '?')}): {s['paths']['screenshot']}"

        return f"No reference photo available for {performer_name}"
    except Exception as e:
        return f"Error: {e}"


# --- Image and Gallery Management ---


@tool
def search_images(query: str = "", performer: str = "", limit: int = 20) -> str:
    """Search images in Stash by query text or performer name.

    Args:
        query: Text search query
        performer: Filter by performer name
        limit: Max results (default 20)
    """
    try:
        image_filter: dict = {}
        if performer:
            perf_data = _stash_query(
                'query ($q: String!) { findPerformers(performer_filter: { name: { value: $q, modifier: EQUALS } }) { performers { id } } }',
                {"q": performer},
            )
            found = perf_data.get("findPerformers", {}).get("performers", [])
            if found:
                image_filter["performers"] = {"value": [found[0]["id"]], "modifier": "INCLUDES", "depth": 0}

        data = _stash_query(
            """query ($filter: ImageFilterType, $find: FindFilterType) {
                findImages(image_filter: $filter, filter: $find) {
                    count
                    images { id title rating100 o_counter file { width height size } paths { thumbnail } performers { name } }
                }
            }""",
            {"filter": image_filter if image_filter else None, "find": {"q": query, "per_page": limit, "sort": "created_at", "direction": "DESC"}},
        )
        result = data.get("findImages", {})
        images = result.get("images", [])
        if not images:
            return f"No images found{' for ' + performer if performer else ''}."
        lines = [f"Images ({result.get('count', len(images))} total, showing {len(images)}):"]
        for img in images:
            perfs = ", ".join(p["name"] for p in img.get("performers", []))
            f = img.get("file", {})
            lines.append(
                f"  [{img['id']}] {img.get('title', 'untitled')}"
                + (f" | {perfs}" if perfs else "")
                + (f" | {f.get('width', '?')}x{f.get('height', '?')}" if f else "")
                + (f" | rating {img['rating100']}" if img.get("rating100") else "")
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching images: {e}"


@tool
def list_galleries(limit: int = 20) -> str:
    """List galleries in Stash.

    Args:
        limit: Max results (default 20)
    """
    try:
        data = _stash_query(
            """query ($find: FindFilterType) {
                findGalleries(filter: $find) {
                    count
                    galleries { id title image_count date performers { name } }
                }
            }""",
            {"find": {"per_page": limit, "sort": "created_at", "direction": "DESC"}},
        )
        result = data.get("findGalleries", {})
        galleries = result.get("galleries", [])
        if not galleries:
            return "No galleries found."
        lines = [f"Galleries ({result.get('count', len(galleries))} total):"]
        for g in galleries:
            perfs = ", ".join(p["name"] for p in g.get("performers", []))
            lines.append(
                f"  [{g['id']}] {g.get('title', 'untitled')}"
                + f" | {g.get('image_count', 0)} images"
                + (f" | {perfs}" if perfs else "")
                + (f" | {g['date']}" if g.get("date") else "")
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing galleries: {e}"


@tool
def create_gallery(title: str, performer_names: list[str] | None = None) -> str:
    """Create a new gallery in Stash.

    Args:
        title: Gallery title
        performer_names: Optional list of performer names to associate
    """
    try:
        input_data: dict = {"title": title}
        if performer_names:
            perf_ids = []
            for name in performer_names:
                try:
                    perf_data = _stash_query(
                        'query ($q: String!) { findPerformers(performer_filter: { name: { value: $q, modifier: EQUALS } }) { performers { id } } }',
                        {"q": name},
                    )
                    found = perf_data.get("findPerformers", {}).get("performers", [])
                    if found:
                        perf_ids.append(found[0]["id"])
                except Exception:
                    pass
            if perf_ids:
                input_data["performer_ids"] = perf_ids

        data = _stash_query(
            """mutation ($input: GalleryCreateInput!) {
                galleryCreate(input: $input) { id title }
            }""",
            {"input": input_data},
        )
        result = data.get("galleryCreate", {})
        return f"Gallery '{result.get('title', title)}' created (ID: {result.get('id', '?')})."
    except Exception as e:
        return f"Error creating gallery: {e}"


# --- Smart Playlists (Saved Filters) ---


@tool
def list_smart_playlists() -> str:
    """List all saved filters (smart playlists) in Stash.

    Returns filter names, IDs, and modes (SCENES, PERFORMERS, etc).
    """
    try:
        data = _stash_query("""
            { findSavedFilters {
                id name mode
                find_filter { q sort direction per_page }
                object_filter
            } }
        """)
        filters = data.get("findSavedFilters", [])
        if not filters:
            return "No saved filters/smart playlists found."
        lines = [f"Smart Playlists ({len(filters)} total):"]
        for f in filters:
            mode = f.get("mode", "SCENES")
            ff = f.get("find_filter") or {}
            query = ff.get("q", "")
            sort = ff.get("sort", "")
            lines.append(
                f"  [{f['id']}] {f['name']} ({mode})"
                + (f" — query: {query}" if query else "")
                + (f", sort: {sort}" if sort else "")
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing smart playlists: {e}"


@tool
def create_smart_playlist(
    name: str,
    mode: str = "SCENES",
    query: str = "",
    sort: str = "date",
    direction: str = "DESC",
    tags: list[str] | None = None,
    rating_min: int | None = None,
    performer: str | None = None,
) -> str:
    """Create a smart playlist (saved filter) in Stash.

    Args:
        name: Playlist name (e.g., "Top Rated This Month", "Unorganized Scenes")
        mode: Filter mode — SCENES, PERFORMERS, IMAGES, GALLERIES, STUDIOS, TAGS
        query: Text search query
        sort: Sort field (date, rating, random, title, duration, file_count)
        direction: Sort direction (ASC or DESC)
        tags: Optional list of tag names to filter by
        rating_min: Optional minimum rating (1-5 scale, stored as 1-100)
        performer: Optional performer name to filter by
    """
    find_filter = {
        "q": query,
        "sort": sort,
        "direction": direction.upper(),
        "per_page": 40,
    }

    # Build object filter for advanced criteria
    scene_filter = {}
    if tags:
        # Resolve tag names to IDs
        tag_ids = []
        for tag_name in tags:
            try:
                tag_data = _stash_query(
                    'query ($q: String!) { findTags(tag_filter: { name: { value: $q, modifier: EQUALS } }) { tags { id name } } }',
                    {"q": tag_name},
                )
                found = tag_data.get("findTags", {}).get("tags", [])
                if found:
                    tag_ids.append(found[0]["id"])
            except Exception:
                pass
        if tag_ids:
            scene_filter["tags"] = {
                "value": tag_ids,
                "modifier": "INCLUDES",
                "depth": 0,
            }

    if rating_min is not None:
        scene_filter["rating100"] = {
            "value": rating_min * 20,
            "modifier": "GREATER_THAN",
        }

    if performer:
        try:
            perf_data = _stash_query(
                'query ($q: String!) { findPerformers(performer_filter: { name: { value: $q, modifier: EQUALS } }) { performers { id name } } }',
                {"q": performer},
            )
            found = perf_data.get("findPerformers", {}).get("performers", [])
            if found:
                scene_filter["performers"] = {
                    "value": [found[0]["id"]],
                    "modifier": "INCLUDES",
                    "depth": 0,
                }
        except Exception:
            pass

    try:
        data = _stash_query(
            """mutation ($input: SaveFilterInput!) {
                saveFilter(input: $input) { id name mode }
            }""",
            {
                "input": {
                    "name": name,
                    "mode": mode.upper(),
                    "find_filter": find_filter,
                    "object_filter": scene_filter if scene_filter else None,
                }
            },
        )
        result = data.get("saveFilter", {})
        return f"Smart playlist '{result.get('name', name)}' created (ID: {result.get('id', '?')}, mode: {result.get('mode', mode)})."
    except Exception as e:
        return f"Error creating smart playlist: {e}"


@tool
def create_performer(
    name: str,
    disambiguation: str = "",
    gender: str = "FEMALE",
    country: str = "",
    ethnicity: str = "",
    details: str = "",
    tattoos: str = "",
    piercings: str = "",
    favorite: bool = False,
) -> str:
    """Create a new performer profile in Stash.

    Args:
        name: Performer's name (required)
        disambiguation: Disambiguation text (e.g., "actress" or "model") if name is common
        gender: MALE, FEMALE, TRANSGENDER_MALE, TRANSGENDER_FEMALE, INTERSEX, NON_BINARY
        country: Two-letter country code (e.g., "US", "SE", "DE")
        ethnicity: Ethnicity string
        details: Biography or notes
        tattoos: Tattoo descriptions
        piercings: Piercing descriptions
        favorite: Mark as favorite
    """
    try:
        mutation = """
        mutation ($input: PerformerCreateInput!) {
            performerCreate(input: $input) {
                id name disambiguation gender country
            }
        }
        """
        input_data: dict = {"name": name}
        if disambiguation:
            input_data["disambiguation"] = disambiguation
        if gender:
            input_data["gender"] = gender.upper()
        if country:
            input_data["country"] = country.upper()
        if ethnicity:
            input_data["ethnicity"] = ethnicity
        if details:
            input_data["details"] = details
        if tattoos:
            input_data["tattoos"] = tattoos
        if piercings:
            input_data["piercings"] = piercings
        if favorite:
            input_data["favorite"] = True

        data = _stash_query(mutation, {"input": input_data})
        result = data.get("performerCreate", {})
        return (
            f"Performer created: {result.get('name', name)} "
            f"(ID: {result.get('id', '?')}, "
            f"gender: {result.get('gender', gender)}, "
            f"country: {result.get('country', country or 'unset')})"
        )
    except Exception as e:
        return f"Error creating performer: {e}"


@tool
def delete_smart_playlist(playlist_id: str) -> str:
    """Delete a saved filter (smart playlist) by ID.

    Args:
        playlist_id: The ID of the saved filter to delete. Use list_smart_playlists to find IDs.
    """
    try:
        _stash_query(
            "mutation ($id: ID!) { destroySavedFilter(id: $id) }",
            {"id": playlist_id},
        )
        return f"Smart playlist {playlist_id} deleted."
    except Exception as e:
        return f"Error deleting smart playlist: {e}"


# --- Tool registry (must be after all @tool definitions) ---

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
    check_queen_references,
    get_performer_reference_photo,
    search_images,
    list_galleries,
    create_gallery,
    list_smart_playlists,
    create_smart_playlist,
    delete_smart_playlist,
    create_performer,
]
