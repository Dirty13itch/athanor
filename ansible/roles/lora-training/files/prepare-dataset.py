#!/usr/bin/env python3
"""Prepare a LoRA training dataset from Stash performer photos.

Usage:
    python prepare-dataset.py <performer_name> [--output /data/training/datasets/<name>]
    python prepare-dataset.py "Ava Addams" --trigger ohwx_ava --repeats 20

Fetches performer images from Stash GraphQL API, crops to training resolution,
and creates a kohya-compatible dataset directory structure:
    <output>/
        <repeats>_<trigger>/
            image_001.jpg
            image_001.txt  (caption file)
            image_002.jpg
            image_002.txt
            ...
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

STASH_URL = os.environ.get("STASH_URL", "http://192.168.1.203:9999")


def fetch_performer_images(performer_name: str) -> list[dict]:
    """Fetch performer images from Stash GraphQL API."""
    query = """
    query ($name: String!) {
      findPerformers(performer_filter: { name: { value: $name, modifier: EQUALS } }) {
        performers {
          id
          name
          image_path
          scenes {
            id
            paths { screenshot }
          }
        }
      }
    }
    """
    data = json.dumps({
        "query": query,
        "variables": {"name": performer_name},
    }).encode()

    req = urllib.request.Request(
        f"{STASH_URL}/graphql",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            performers = result.get("data", {}).get("findPerformers", {}).get("performers", [])
            if not performers:
                print(f"Performer '{performer_name}' not found in Stash", file=sys.stderr)
                return []
            return performers
    except Exception as e:
        print(f"Stash API error: {e}", file=sys.stderr)
        return []


def download_image(url: str, output_path: Path) -> bool:
    """Download an image from URL to local path."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  Failed to download {url}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Prepare LoRA training dataset from Stash")
    parser.add_argument("performer", help="Performer name to search in Stash")
    parser.add_argument("--output", "-o", default=None, help="Output directory")
    parser.add_argument("--trigger", "-t", default="ohwx", help="Trigger word for captions")
    parser.add_argument("--repeats", "-r", type=int, default=20, help="Training repeats")
    parser.add_argument("--max-images", "-m", type=int, default=30, help="Max images to download")
    args = parser.parse_args()

    # Default output directory
    safe_name = args.performer.lower().replace(" ", "_")
    output_dir = Path(args.output or f"/data/training/datasets/{safe_name}")
    dataset_dir = output_dir / f"{args.repeats}_{args.trigger}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print(f"Preparing dataset for: {args.performer}")
    print(f"Output: {dataset_dir}")
    print(f"Trigger: {args.trigger}, Repeats: {args.repeats}")

    performers = fetch_performer_images(args.performer)
    if not performers:
        sys.exit(1)

    performer = performers[0]
    print(f"Found performer: {performer['name']} (ID: {performer['id']})")

    # Collect image URLs
    image_urls = []

    # Profile image
    if performer.get("image_path"):
        image_urls.append(performer["image_path"])

    # Scene screenshots
    for scene in performer.get("scenes", []):
        paths = scene.get("paths", {})
        if paths and paths.get("screenshot"):
            image_urls.append(paths["screenshot"])

    print(f"Found {len(image_urls)} images")

    # Download images
    downloaded = 0
    for i, url in enumerate(image_urls[:args.max_images]):
        img_path = dataset_dir / f"image_{i+1:03d}.jpg"
        caption_path = dataset_dir / f"image_{i+1:03d}.txt"

        if img_path.exists():
            print(f"  Skipping {img_path.name} (already exists)")
            downloaded += 1
            continue

        print(f"  Downloading image {i+1}/{min(len(image_urls), args.max_images)}...")
        if download_image(url, img_path):
            # Write caption file
            caption_path.write_text(f"a photo of {args.trigger}, {performer['name']}")
            downloaded += 1

    print(f"\nDataset ready: {downloaded} images in {dataset_dir}")
    print(f"To train: docker compose --profile training up lora-training")


if __name__ == "__main__":
    main()
