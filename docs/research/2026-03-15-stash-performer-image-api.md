# Stash GraphQL API: Performer Image Extraction

**Date:** 2026-03-15
**Status:** Complete -- ready for implementation
**Supports:** PuLID/LoRA reference image pipeline
**Depends on:** ADR-011 (Media Stack), existing Stash deployment on VAULT:9999

---

## Context

We need to extract performer profile photos (headshots) from Stash for use as PuLID/LoRA reference images. The library contains 14,547 performers. This research documents the exact API surface, URL patterns, authentication, and implementation approach.

---

## 1. GraphQL Endpoint

**URL:** `http://192.168.1.203:9999/graphql`

**Playground (interactive):** `http://192.168.1.203:9999/playground`

The playground provides schema introspection and a Documentation Explorer for the live instance.

---

## 2. Authentication

### Header-Based API Key (Recommended)

```
ApiKey: <your-api-key>
```

- Header name is `ApiKey` (capital A, capital K, no hyphen)
- The API key is configured in Stash Settings > Security
- Can also be passed as query parameter: `?apikey=<key>`

### Session-Based (Cookie)

- POST to `/login` with `username` and `password` form values
- Returns session cookie `session`

### No Auth Required If

- No username/password is configured in Stash settings
- Request originates from local network (Stash validates `X-FORWARDED-FOR` for proxy chains)

### Auth on Image Endpoints

The REST image endpoints (`/performer/{id}/image`) go through the same `authenticateHandler()` middleware as GraphQL. If auth is enabled, the `ApiKey` header or `?apikey=` query param must be included in image download requests too.

**Known bug (Issue #5538):** When Stash fetches its own image URLs internally (e.g., setting a performer image from a local URL), the internal HTTP request lacks auth headers, causing malformed images. This does not affect external clients fetching images.

**Source:** [`pkg/session/session.go`](https://github.com/stashapp/stash/blob/develop/pkg/session/session.go)

---

## 3. Performer GraphQL Queries

### findPerformers (Paginated List)

```graphql
query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
  findPerformers(filter: $filter, performer_filter: $performer_filter) {
    count
    performers {
      id
      name
      disambiguation
      gender
      image_path
      favorite
      scene_count
      tags { id name }
      stash_ids { endpoint stash_id }
    }
  }
}
```

**Variables for pagination:**
```json
{
  "filter": {
    "page": 1,
    "per_page": 100,
    "sort": "name",
    "direction": "ASC"
  }
}
```

**Pagination notes:**
- `per_page` defaults to 25
- `per_page: -1` returns ALL results (use with caution on 14K+ performers)
- `page` is 1-indexed
- Response includes `count` for total results

### findPerformer (Single by ID)

```graphql
query FindPerformer($id: ID!) {
  findPerformer(id: $id) {
    id
    name
    image_path
    gender
    ethnicity
    birthdate
    height_cm
    tags { id name }
  }
}
```

### Filtering Performers

```graphql
# Only performers with images (has image_path != default)
# Only performers who appear in scenes
query PerformersWithScenes($filter: FindFilterType) {
  findPerformers(
    filter: $filter,
    performer_filter: {
      scene_count: { value: 1, modifier: GREATER_THAN }
    }
  ) {
    count
    performers {
      id
      name
      image_path
      scene_count
    }
  }
}
```

**Source:** [`graphql/schema/types/performer.graphql`](https://github.com/stashapp/stash/blob/develop/graphql/schema/types/performer.graphql), [`graphql/schema/schema.graphql`](https://github.com/stashapp/stash/blob/develop/graphql/schema/schema.graphql)

---

## 4. Performer Image URL Pattern

### GraphQL `image_path` Field

The `image_path` field on the `Performer` type is a **resolver field** (not stored directly). It returns a full URL:

```
http://<host>:<port>/performer/<id>/image?t=<updated_at_unix>
```

Example:
```
http://192.168.1.203:9999/performer/42/image?t=1710460800
```

- `?t=` is a cache-busting timestamp (performer's `updated_at` as Unix epoch)
- If the performer has **no custom image**, the URL includes `&default=true` and serves a generated default placeholder

### REST Endpoint

```
GET /performer/{performerId}/image
```

**Query parameters:**
- `?t=<timestamp>` -- cache busting (optional for downloads)
- `?default=true` -- forces return of default placeholder image
- `?apikey=<key>` -- alternative auth if header not used

**Response:**
- Content-Type: varies (JPEG, PNG, WebP -- whatever was uploaded)
- Body: raw image bytes
- No Content-Disposition header (served inline)

### How Performers Get Images

1. **StashDB scraping** -- downloaded from StashDB during Identify task
2. **Manual upload** -- URL or base64 via `performerUpdate` mutation's `image` field
3. **Clipboard paste** -- via UI
4. **Default** -- auto-generated silhouette placeholder (gender-specific)

### Image Storage

Images are stored as blobs, either:
- In SQLite database (default: "Database" storage mode)
- On filesystem at configured blob path (if "Filesystem" storage mode)

The `GetImage(ctx, performerID)` function retrieves raw bytes from whichever backend is configured.

### Image Format/Resolution

- **No standardized format** -- images are stored as-uploaded
- Typical sources (StashDB): JPEG, 300-800px wide, portrait orientation headshots
- Some may be WebP (note: WebP breaks Safari < 13)
- No server-side resizing -- images are served at original resolution
- For PuLID/LoRA, downstream resizing to 512x512 or 1024x1024 will be needed

**Source:** [`internal/api/routes_performer.go`](https://github.com/stashapp/stash/blob/develop/internal/api/routes_performer.go), [`internal/api/urlbuilders/performer.go`](https://github.com/stashapp/stash/blob/develop/internal/api/urlbuilders/performer.go)

---

## 5. Detecting Performers With vs Without Images

The `image_path` URL is always returned (never null) -- it falls back to a default placeholder. To distinguish real images from defaults:

**Option A: Check `&default=true` in URL**
```python
has_real_image = "&default=true" not in performer["image_path"]
```

**Option B: Use `is_missing` filter**
```graphql
findPerformers(
  performer_filter: {
    is_missing: "image"
  }
) { count }
```
This returns performers WITHOUT images. Invert to get those WITH images.

**Option C: Check response size**
Default placeholder images are small (~2-5KB). Real performer photos are typically >10KB.

---

## 6. Bulk Export Capability

Stash has **no built-in bulk image export**. The approach is:

1. Query `findPerformers` with pagination (100 per page)
2. For each performer, check if they have a real image (not default)
3. GET the image from the REST endpoint
4. Save to organized directory structure

### Recommended Pipeline

```python
import httpx
import asyncio
from pathlib import Path

STASH_URL = "http://192.168.1.203:9999"
GRAPHQL_URL = f"{STASH_URL}/graphql"
API_KEY = ""  # Set if auth is enabled
OUTPUT_DIR = Path("/path/to/reference_images/performers")

headers = {"Content-Type": "application/json"}
if API_KEY:
    headers["ApiKey"] = API_KEY

QUERY = """
query FindPerformers($filter: FindFilterType) {
  findPerformers(filter: $filter) {
    count
    performers {
      id
      name
      image_path
      gender
      scene_count
    }
  }
}
"""

async def download_performer_images():
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        # First get total count
        resp = await client.post(GRAPHQL_URL, json={
            "query": QUERY,
            "variables": {"filter": {"page": 1, "per_page": 1}}
        })
        total = resp.json()["data"]["findPerformers"]["count"]

        page = 1
        per_page = 100
        downloaded = 0
        skipped = 0

        while (page - 1) * per_page < total:
            resp = await client.post(GRAPHQL_URL, json={
                "query": QUERY,
                "variables": {"filter": {
                    "page": page, "per_page": per_page,
                    "sort": "name", "direction": "ASC"
                }}
            })
            performers = resp.json()["data"]["findPerformers"]["performers"]

            for p in performers:
                # Skip performers without real images
                if "&default=true" in (p["image_path"] or ""):
                    skipped += 1
                    continue

                # Skip performers with no scenes (likely unused entries)
                if p["scene_count"] == 0:
                    skipped += 1
                    continue

                # Sanitize filename
                safe_name = "".join(
                    c if c.isalnum() or c in " -_" else "_"
                    for c in p["name"]
                ).strip()
                filename = f"{safe_name}_{p['id']}.jpg"
                filepath = OUTPUT_DIR / filename

                if filepath.exists():
                    continue

                # Download image
                img_resp = await client.get(
                    f"{STASH_URL}/performer/{p['id']}/image",
                    headers={"ApiKey": API_KEY} if API_KEY else {}
                )
                if img_resp.status_code == 200 and len(img_resp.content) > 5000:
                    filepath.write_bytes(img_resp.content)
                    downloaded += 1

            page += 1

        print(f"Downloaded: {downloaded}, Skipped: {skipped}, Total: {total}")

asyncio.run(download_performer_images())
```

---

## 7. Rate Limiting

**Stash has no rate limiting.** It is a local-only application with no throttling on API requests. However:

- The SQLite database is single-writer, so extremely parallel writes can bottleneck
- Image serving is I/O bound (reading from DB or filesystem)
- Recommended: limit concurrent image downloads to 10-20 to avoid overwhelming the Stash container

For 14,547 performers at ~50KB average image size:
- **Estimated data:** ~700 MB total (not all will have images)
- **Estimated time:** ~5-10 minutes at 20 concurrent downloads over 5GbE

---

## 8. Organization for PuLID/LoRA Reference

Recommended directory structure:

```
/mnt/vault/models/reference_images/
  performers/
    by_id/
      42.jpg          # Fast lookup by Stash ID
      43.jpg
    by_name/
      performer_name_42.jpg   # Human-readable browsing
    metadata.json      # ID -> name/gender/tags mapping
```

The `metadata.json` enables downstream tools to:
- Filter by gender for gender-specific LoRA training
- Group by tags for category-specific reference sets
- Map back to Stash IDs for provenance tracking

---

## 9. Alternative: Stash Metadata Export

Stash has a built-in metadata export (`metadataExport` mutation) that writes JSON files to the metadata directory. This includes performer data but **not** image binary data -- only metadata fields. Images must be fetched separately via the REST endpoint.

---

## 10. stashapp-tools Python Package

The `stashapp-tools` package on PyPI provides a `StashInterface` class that wraps the GraphQL API:

```python
from stashapi.stashapp import StashInterface

stash = StashInterface({
    "scheme": "http",
    "host": "192.168.1.203",
    "port": 9999,
    "ApiKey": "<key>"  # if auth enabled
})

# Find performers with pagination
result = stash.find_performers(f={"per_page": 100, "page": 1})
```

This is a convenience wrapper but raw `httpx` is simpler for a bulk download script and avoids the dependency.

**Source:** [stashapp-tools on PyPI](https://pypi.org/project/stashapp-tools/)

---

## Summary

| Item | Answer |
|------|--------|
| GraphQL endpoint | `http://192.168.1.203:9999/graphql` |
| Playground | `http://192.168.1.203:9999/playground` |
| Auth header | `ApiKey: <key>` (or `?apikey=<key>` query param) |
| Performer list query | `findPerformers(filter, performer_filter)` |
| Image URL pattern | `/performer/{id}/image?t={unix_timestamp}` |
| Image format | As-uploaded (JPEG/PNG/WebP), no standardization |
| Bulk export | No built-in -- paginated query + REST download |
| Rate limiting | None (self-hosted) |
| Default image detection | `&default=true` in URL or `is_missing: "image"` filter |
| Estimated download | ~700 MB, 5-10 min at 20 concurrent |

---

## Sources

- [Stash GraphQL Schema - performer.graphql](https://github.com/stashapp/stash/blob/develop/graphql/schema/types/performer.graphql) -- complete Performer type definition
- [Stash GraphQL Schema - schema.graphql](https://github.com/stashapp/stash/blob/develop/graphql/schema/schema.graphql) -- query definitions
- [Stash performer routes](https://github.com/stashapp/stash/blob/develop/internal/api/routes_performer.go) -- REST image serving implementation
- [Stash performer URL builder](https://github.com/stashapp/stash/blob/develop/internal/api/urlbuilders/performer.go) -- image URL construction
- [Stash performer resolver](https://github.com/stashapp/stash/blob/develop/internal/api/resolver_model_performer.go) -- image_path GraphQL resolver
- [Stash session auth](https://github.com/stashapp/stash/blob/develop/pkg/session/session.go) -- ApiKey header/query param
- [Stash API Wiki](https://github.com/stashapp/stash/wiki/API) -- general API documentation
- [Stash Issue #5538](https://github.com/stashapp/stash/issues/5538) -- performer image auth bug
- [stashapp-tools PyPI](https://pypi.org/project/stashapp-tools/) -- Python wrapper library
- [DeepWiki - Stash GraphQL API](https://deepwiki.com/stashapp/stash/4.1-graphql-api) -- API overview

Last updated: 2026-03-15
