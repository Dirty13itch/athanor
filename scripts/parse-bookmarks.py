#!/usr/bin/env python3
"""Parse Chrome/Netscape bookmark export HTML into structured JSON and index to Qdrant.

Extracts all bookmarks with folder hierarchy, indexes each as a searchable
vector in the personal_data Qdrant collection, and outputs a JSON summary.

Usage:
    python3 scripts/parse-bookmarks.py [--index] [--input FILE]

Options:
    --index     Also index bookmarks into Qdrant personal_data collection
    --input     Path to bookmarks HTML file (default: auto-detect)
    -h, --help  Show this help
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

# Default bookmark file locations
DEFAULT_PATHS = [
    Path("/mnt/c/Users/Shaun/Documents/bookmarks_2_16_26.html"),
    Path("/mnt/c/Users/Shaun/Documents/ChromeBackup/Bookmarks"),  # JSON format
]

QDRANT_URL = "http://192.168.1.244:6333"
EMBEDDING_URL = (os.environ.get("ATHANOR_LITELLM_URL") or "http://192.168.1.203:4000").rstrip("/") + "/v1"
EMBEDDING_KEY = (
    os.environ.get("ATHANOR_LITELLM_API_KEY")
    or os.environ.get("LITELLM_API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
COLLECTION = "personal_data"


class BookmarkParser(HTMLParser):
    """Parse Netscape bookmark HTML format."""

    def __init__(self):
        super().__init__()
        self.bookmarks = []
        self.folder_stack = []
        self.current_folder = ""
        self.current_attrs = {}
        self.in_h3 = False
        self.in_a = False
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag == "h3":
            self.in_h3 = True
            self.current_text = ""
            self.current_attrs = attr_dict
        elif tag == "a":
            self.in_a = True
            self.current_text = ""
            self.current_attrs = attr_dict
        elif tag == "dl":
            pass  # folder contents start
        elif tag == "dt":
            pass

    def handle_endtag(self, tag):
        if tag == "h3" and self.in_h3:
            self.in_h3 = False
            folder_name = self.current_text.strip()
            self.folder_stack.append(folder_name)
            self.current_folder = " > ".join(self.folder_stack)
        elif tag == "a" and self.in_a:
            self.in_a = False
            title = self.current_text.strip()
            url = self.current_attrs.get("href", "")
            add_date = self.current_attrs.get("add_date", "")

            if url and not url.startswith("javascript:"):
                self.bookmarks.append({
                    "title": title,
                    "url": url,
                    "folder": self.current_folder,
                    "folder_depth": len(self.folder_stack),
                    "add_date": add_date,
                    "add_date_human": (
                        time.strftime("%Y-%m-%d", time.localtime(int(add_date)))
                        if add_date and add_date.isdigit()
                        else ""
                    ),
                })
        elif tag == "dl":
            if self.folder_stack:
                self.folder_stack.pop()
                self.current_folder = " > ".join(self.folder_stack)

    def handle_data(self, data):
        if self.in_h3 or self.in_a:
            self.current_text += data


def classify_bookmark(bookmark):
    """Classify a bookmark based on its folder path and URL."""
    folder = bookmark["folder"].lower()
    url = bookmark["url"].lower()

    if "adult" in folder or "nsfw" in folder or "performer" in folder:
        return "adult"
    if "work" in folder or "energy" in folder or "rater" in folder:
        return "work"
    if "finance" in folder or "loan" in folder or "insurance" in folder or "investment" in folder:
        return "finance"
    if "homelab" in folder or "ai" in folder or "model" in folder or "research" in folder:
        return "ai_homelab"
    if "hack" in folder or "osint" in folder or "pen test" in folder or "dark" in folder:
        return "security"
    if "media" in folder or "download" in folder or "torrent" in folder or "usenet" in folder:
        return "media"
    if "streaming" in folder or "sport" in folder:
        return "streaming"
    if "gaming" in folder or "game" in folder:
        return "gaming"
    if "personal" in folder or "home project" in folder:
        return "personal"
    if "queue" in folder:
        return "queue"

    # URL-based fallback
    if "github.com" in url:
        return "ai_homelab"
    if "reddit.com" in url:
        return "social"

    return "general"


def get_embedding(text):
    """Get embedding vector from LiteLLM."""
    import urllib.request

    payload = json.dumps({
        "model": "embedding",
        "input": text[:2000],
    }).encode()
    req = urllib.request.Request(
        f"{EMBEDDING_URL}/embeddings",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {EMBEDDING_KEY}",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["data"][0]["embedding"]


def ensure_collection():
    """Ensure the personal_data Qdrant collection exists."""
    import urllib.request

    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass

    payload = json.dumps({
        "vectors": {"size": 1024, "distance": "Cosine"},
    }).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    urllib.request.urlopen(req, timeout=10)


def index_bookmarks(bookmarks):
    """Index bookmarks into Qdrant personal_data collection."""
    import urllib.request

    ensure_collection()

    success = 0
    fail = 0
    batch = []
    batch_size = 20

    for i, bm in enumerate(bookmarks):
        # Create searchable text from bookmark
        text = f"{bm['title']} — {bm['folder']} ({bm['url']})"

        try:
            vector = get_embedding(text)
            point_id = hashlib.md5(bm["url"].encode()).hexdigest()

            batch.append({
                "id": point_id,
                "vector": vector,
                "payload": {
                    "source": f"bookmarks:{bm['folder']}",
                    "filename": "bookmarks_2_16_26.html",
                    "category": "bookmark",
                    "subcategory": bm["category"],
                    "text": text,
                    "title": bm["title"],
                    "url": bm["url"],
                    "folder": bm["folder"],
                    "folder_depth": bm["folder_depth"],
                    "add_date": bm["add_date_human"],
                    "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            })

            if len(batch) >= batch_size:
                _upsert_batch(batch)
                success += len(batch)
                print(f"  Indexed {success}/{len(bookmarks)} bookmarks...", file=sys.stderr)
                batch = []

        except Exception as e:
            fail += 1
            print(f"  ERR: {bm['title'][:50]}: {e}", file=sys.stderr)

    # Final batch
    if batch:
        _upsert_batch(batch)
        success += len(batch)

    return success, fail


def _upsert_batch(points):
    """Upsert a batch of points to Qdrant."""
    import urllib.request

    payload = json.dumps({"points": points}).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Qdrant upsert failed: HTTP {resp.status}")


def main():
    parser = argparse.ArgumentParser(description="Parse bookmarks and optionally index to Qdrant")
    parser.add_argument("--index", action="store_true", help="Index bookmarks into Qdrant")
    parser.add_argument("--input", type=str, help="Path to bookmarks HTML file")
    args = parser.parse_args()

    # Find bookmark file
    if args.input:
        bookmark_path = Path(args.input)
    else:
        bookmark_path = None
        for path in DEFAULT_PATHS:
            if path.exists():
                bookmark_path = path
                break

    if not bookmark_path or not bookmark_path.exists():
        print("Error: No bookmark file found. Use --input to specify.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {bookmark_path}", file=sys.stderr)

    # Parse bookmarks
    content = bookmark_path.read_text(encoding="utf-8", errors="replace")
    bp = BookmarkParser()
    bp.feed(content)

    # Classify each bookmark
    for bm in bp.bookmarks:
        bm["category"] = classify_bookmark(bm)

    # Statistics
    categories = {}
    folders = set()
    for bm in bp.bookmarks:
        cat = bm["category"]
        categories[cat] = categories.get(cat, 0) + 1
        folders.add(bm["folder"])

    print(f"\nParsed {len(bp.bookmarks)} bookmarks in {len(folders)} folders", file=sys.stderr)
    print("\nCategories:", file=sys.stderr)
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}", file=sys.stderr)

    # Output JSON summary
    summary = {
        "total_bookmarks": len(bp.bookmarks),
        "total_folders": len(folders),
        "categories": categories,
        "folders": sorted(folders),
        "bookmarks": bp.bookmarks,
    }

    # Save JSON
    output_path = Path("docs/data/bookmarks.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2))
    print(f"\nJSON saved to {output_path}", file=sys.stderr)

    # Index if requested
    if args.index:
        print(f"\nIndexing {len(bp.bookmarks)} bookmarks to Qdrant...", file=sys.stderr)
        success, fail = index_bookmarks(bp.bookmarks)
        print(f"\nDone: {success} indexed, {fail} failed", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
