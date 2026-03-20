#!/usr/bin/env python3
"""Extract performer profile photos from Stash for PuLID/LoRA reference images.

Modes:
  --queens    Download only the 21 EoBQ queen performers (default)
  --top N     Download top N performers by scene count
  --all       Download all performers with photos

Photos are saved to OUTPUT_DIR/<performer_name>/profile.png
"""

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url

STASH_URL = get_url("stash")
GRAPHQL_URL = f"{STASH_URL}/graphql"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/mnt/vault/models/comfyui/reference_photos"))

EOQB_QUEENS = [
    "Emilie Ekstrom", "Jordan Night", "Alanah Rae", "Nikki Benz",
    "Chloe Lamour", "Nicolette Shea", "Peta Jensen", "Sandee Westgate",
    "Marisol Yotta", "Trina Michaels", "Nikki Sexx", "Madison Ivy",
    "Amy Anderssen", "Puma Swede", "Ava Addams", "Brooklyn Chase",
    "Esperanza Gomez", "Savannah Bond", "Shyla Stylez", "Brianna Banks",
    "Clanddi Jinkcebo",
]


def graphql(query: str, variables: dict | None = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def safe_dirname(name: str) -> str:
    return re.sub(r'[^\w\s\-.]', '', name).strip()


def fetch_performer_by_name(name: str) -> dict | None:
    query = """
    query($name: String!) {
      findPerformers(performer_filter: {name: {value: $name, modifier: EQUALS}}) {
        performers { id name image_path scene_count }
      }
    }
    """
    result = graphql(query, {"name": name})
    performers = result.get("data", {}).get("findPerformers", {}).get("performers", [])
    return performers[0] if performers else None


def fetch_top_performers(limit: int) -> list[dict]:
    query = """
    query($limit: Int!) {
      findPerformers(filter: {per_page: $limit, sort: "scene_count", direction: DESC}) {
        performers { id name image_path scene_count }
      }
    }
    """
    result = graphql(query, {"limit": limit})
    return result.get("data", {}).get("findPerformers", {}).get("performers", [])


def fetch_all_performers() -> list[dict]:
    page = 1
    per_page = 100
    all_performers = []
    while True:
        query = """
        query($page: Int!, $per_page: Int!) {
          findPerformers(filter: {per_page: $per_page, page: $page}) {
            count
            performers { id name image_path scene_count }
          }
        }
        """
        result = graphql(query, {"page": page, "per_page": per_page})
        data = result.get("data", {}).get("findPerformers", {})
        performers = data.get("performers", [])
        if not performers:
            break
        all_performers.extend(performers)
        total = data.get("count", 0)
        if len(all_performers) >= total:
            break
        page += 1
        if page % 10 == 0:
            print(f"  ... fetched {len(all_performers)}/{total} performers")
    return all_performers


MIN_REAL_PHOTO_SIZE = 20_000  # Silhouette placeholders are < 20KB


def fetch_scene_screenshots(performer_id: str, limit: int = 5) -> list[str]:
    """Fetch scene screenshot URLs for a performer (fallback for silhouette profiles)."""
    query = """
    query($id: [ID!]!) {
      findScenes(scene_filter: {performers: {value: $id, modifier: INCLUDES}}, filter: {per_page: %d, sort: "random"}) {
        scenes { paths { screenshot } }
      }
    }
    """ % limit
    try:
        result = graphql(query, {"id": [performer_id]})
        scenes = result.get("data", {}).get("findScenes", {}).get("scenes", [])
        return [s["paths"]["screenshot"] for s in scenes if s.get("paths", {}).get("screenshot")]
    except Exception:
        return []


def download_photo(performer: dict, output_dir: Path) -> bool:
    name = performer["name"]
    image_url = performer.get("image_path", "")
    performer_id = performer.get("id", "")

    dirname = safe_dirname(name)
    dest_dir = output_dir / dirname
    dest_file = dest_dir / "profile.png"

    if dest_file.exists() and dest_file.stat().st_size > MIN_REAL_PHOTO_SIZE:
        print(f"  SKIP {name} (already exists, {dest_file.stat().st_size:,} bytes)")
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Try profile photo first
    if image_url:
        try:
            urllib.request.urlretrieve(image_url, str(dest_file))
            size = dest_file.stat().st_size
            if size > MIN_REAL_PHOTO_SIZE:
                print(f"  OK   {name} profile ({size:,} bytes)")
                return True
            else:
                print(f"  WARN {name} profile is silhouette ({size:,} bytes), trying screenshots...")
                dest_file.unlink()
        except Exception as e:
            print(f"  WARN {name} profile download failed: {e}")

    # Fall back to scene screenshots
    if performer_id:
        screenshots = fetch_scene_screenshots(performer_id)
        for i, ss_url in enumerate(screenshots):
            ss_file = dest_dir / f"screenshot_{i:02d}.jpg"
            try:
                urllib.request.urlretrieve(ss_url, str(ss_file))
                size = ss_file.stat().st_size
                if size > MIN_REAL_PHOTO_SIZE:
                    # Use first good screenshot as the reference
                    if not dest_file.exists():
                        ss_file.rename(dest_file)
                        print(f"  OK   {name} screenshot ({size:,} bytes)")
                    else:
                        print(f"  OK   {name} extra screenshot_{i:02d} ({size:,} bytes)")
                    return True
                else:
                    ss_file.unlink()
            except Exception:
                continue

    print(f"  FAIL {name}: no usable photos found")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--queens", action="store_true", default=True, help="Download EoBQ queen performers only (default)")
    group.add_argument("--top", type=int, metavar="N", help="Download top N performers by scene count")
    group.add_argument("--all", action="store_true", help="Download all performers with photos")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")
    args = parser.parse_args()

    output = args.output
    print(f"Stash URL: {STASH_URL}")
    print(f"Output:    {output}")

    if args.all:
        print("Mode: all performers")
        performers = fetch_all_performers()
    elif args.top:
        print(f"Mode: top {args.top} by scene count")
        performers = fetch_top_performers(args.top)
    else:
        print(f"Mode: {len(EOQB_QUEENS)} EoBQ queens")
        performers = []
        for name in EOQB_QUEENS:
            p = fetch_performer_by_name(name)
            if p:
                performers.append(p)
            else:
                print(f"  WARN: '{name}' not found in Stash")

    print(f"\nFound {len(performers)} performers")

    if args.dry_run:
        for p in performers:
            scenes = p.get("scene_count", 0)
            has_img = "yes" if p.get("image_path") else "no"
            print(f"  {p['name']:30s}  scenes={scenes:4d}  image={has_img}")
        return

    ok = 0
    fail = 0
    for p in performers:
        if download_photo(p, output):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} downloaded, {fail} failed")


if __name__ == "__main__":
    main()
