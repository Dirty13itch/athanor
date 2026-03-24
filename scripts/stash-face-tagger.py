#!/usr/bin/env python3
"""Stash Face Tagger -- auto-tag scenes with performers using InsightFace.

Uses ArcFace embeddings to match faces in scene screenshots against
reference images in gen-subjects/. Tags scenes via Stash GraphQL API.

Usage:
    python3 stash-face-tagger.py                   # Process batch of untagged scenes
    python3 stash-face-tagger.py --build-refs       # Rebuild reference embeddings
    python3 stash-face-tagger.py --batch-size 50    # Process 50 scenes
    python3 stash-face-tagger.py --dry-run           # Report matches without tagging
    python3 stash-face-tagger.py --scene-id 12345   # Process specific scene
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("stash-face-tagger")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STASH_URL = "http://192.168.1.203:9999"
REFS_DIR = Path("/mnt/vault/data/gen-subjects")
EMBEDDINGS_CACHE = Path("/mnt/vault/data/gen-output/face_embeddings_cache.npz")
RESULTS_LOG = Path("/mnt/vault/data/gen-output/face_tagger_results.json")

# Stash Docker volume mapping -> DEV local (via NFS)
STASH_PATH_MAP = {
    "/data/whisparr": "/mnt/vault/data/vault/whisparr",
    "/data/stash": "/mnt/vault/data/vault/stash",
    "/data/archive": "/mnt/vault/data/archive/whisparr-complete",
    "/data/media": "/mnt/vault/data/media",
    "/data/gen-output": "/mnt/vault/data/gen-output",
    "/data/Browser Downloads": "/mnt/vault/data/vault/Browser Downloads",
}

# Thresholds for cosine similarity (ArcFace normed embeddings)
AUTO_TAG_THRESHOLD = 0.55
REVIEW_THRESHOLD = 0.40
MAX_FRAMES_PER_SCENE = 5
FRAME_EXTRACT_TIMEOUT = 30


def _update_threshold(value: float) -> None:
    global AUTO_TAG_THRESHOLD
    AUTO_TAG_THRESHOLD = value

# ---------------------------------------------------------------------------
# InsightFace setup
# ---------------------------------------------------------------------------

_face_app = None


def get_face_app():
    """Lazy-init InsightFace FaceAnalysis."""
    global _face_app
    if _face_app is None:
        from insightface.app import FaceAnalysis
        _face_app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace initialized")
    return _face_app


# ---------------------------------------------------------------------------
# Stash GraphQL helpers
# ---------------------------------------------------------------------------

def _gql(query: str, variables: dict | None = None) -> dict:
    """Execute a Stash GraphQL query."""
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        f"{STASH_URL}/graphql",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"]


def get_untagged_scenes(batch_size: int = 20) -> list[dict]:
    """Fetch scenes with zero performers."""
    data = _gql(
        """
        query($perPage: Int!) {
            findScenes(
                scene_filter: { performer_count: { modifier: EQUALS, value: 0 } }
                filter: { per_page: $perPage, sort: "random" }
            ) {
                count
                scenes { id title files { path duration } }
            }
        }
        """,
        {"perPage": batch_size},
    )
    scenes = data["findScenes"]["scenes"]
    total = data["findScenes"]["count"]
    logger.info("Found %d untagged scenes (fetched %d)", total, len(scenes))
    return scenes


def get_scene_by_id(scene_id: str) -> dict | None:
    """Fetch a specific scene."""
    data = _gql(
        """
        query($id: ID!) {
            findScene(id: $id) {
                id title files { path duration }
                performers { id name }
            }
        }
        """,
        {"id": scene_id},
    )
    return data.get("findScene")


def find_performer_by_name(name: str) -> str | None:
    """Look up performer ID by exact name match."""
    data = _gql(
        """
        query($name: String!) {
            findPerformers(
                performer_filter: { name: { modifier: EQUALS, value: $name } }
                filter: { per_page: 1 }
            ) { performers { id name } }
        }
        """,
        {"name": name},
    )
    performers = data["findPerformers"]["performers"]
    return performers[0]["id"] if performers else None


def tag_scene_performer(scene_id: str, performer_ids: list[str]) -> bool:
    """Add performer(s) to a scene, preserving any existing tags."""
    data = _gql(
        'query($id: ID!) { findScene(id: $id) { performers { id } } }',
        {"id": scene_id},
    )
    existing = [p["id"] for p in data["findScene"]["performers"]]
    all_ids = list(set(existing + performer_ids))
    _gql(
        """
        mutation($id: ID!, $pids: [ID!]!) {
            sceneUpdate(input: { id: $id, performer_ids: $pids }) {
                id performers { id name }
            }
        }
        """,
        {"id": scene_id, "pids": all_ids},
    )
    return True


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------

def _stash_to_local_path(stash_path: str) -> Path | None:
    """Convert Stash container path to DEV local path via NFS."""
    for prefix, local_prefix in STASH_PATH_MAP.items():
        if stash_path.startswith(prefix):
            return Path(stash_path.replace(prefix, local_prefix, 1))
    logger.warning("Cannot map Stash path: %s", stash_path)
    return None


def extract_frames(video_path: Path, duration: float, count: int = 5) -> list[Path]:
    """Extract evenly-spaced frames from a video using ffmpeg."""
    if not video_path.exists():
        logger.warning("Video not found: %s", video_path)
        return []

    frames = []
    start = duration * 0.10
    end = duration * 0.90
    interval = (end - start) / (count + 1)

    tmp_dir = Path("/tmp/stash-face-tagger")
    tmp_dir.mkdir(exist_ok=True)

    for i in range(count):
        ts = start + interval * (i + 1)
        out = tmp_dir / f"frame_{video_path.stem[:40]}_{i:02d}.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", f"{ts:.1f}",
                    "-i", str(video_path),
                    "-vframes", "1", "-q:v", "2",
                    str(out),
                ],
                capture_output=True,
                timeout=FRAME_EXTRACT_TIMEOUT,
                check=True,
            )
            if out.exists() and out.stat().st_size > 1000:
                frames.append(out)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.debug("Frame extraction failed at %.1fs: %s", ts, e)
    return frames


# ---------------------------------------------------------------------------
# Embedding computation & matching
# ---------------------------------------------------------------------------

def compute_embedding(image_path: Path) -> list[np.ndarray]:
    """Detect faces in an image and return their normed ArcFace embeddings."""
    import cv2
    app = get_face_app()
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    faces = app.get(img)
    return [f.normed_embedding for f in faces if f.normed_embedding is not None]


@dataclass
class PerformerRef:
    slug: str
    display_name: str
    stash_id: str | None = None
    embeddings: list[np.ndarray] = field(default_factory=list)


def build_reference_embeddings(force: bool = False) -> list[PerformerRef]:
    """Build or load cached embeddings for all reference performers."""
    refs: list[PerformerRef] = []

    if not force and EMBEDDINGS_CACHE.exists():
        try:
            cache = np.load(str(EMBEDDINGS_CACHE), allow_pickle=True)
            ref_data = cache["ref_data"].item()
            for slug, info in ref_data.items():
                refs.append(PerformerRef(
                    slug=slug,
                    display_name=info["display_name"],
                    stash_id=info.get("stash_id"),
                    embeddings=[np.array(e) for e in info["embeddings"]],
                ))
            logger.info("Loaded %d performer references from cache", len(refs))
            return refs
        except Exception as e:
            logger.warning("Cache load failed (%s), rebuilding", e)

    logger.info("Building reference embeddings from %s", REFS_DIR)
    for subj_dir in sorted(d for d in REFS_DIR.iterdir() if d.is_dir()):
        slug = subj_dir.name
        display_name = slug.replace("-", " ").title()

        stash_id = find_performer_by_name(display_name)

        ref_images = sorted(
            f for f in subj_dir.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )

        embeddings = []
        for ref_img in ref_images[:10]:
            embs = compute_embedding(ref_img)
            if embs:
                embeddings.extend(embs)
                logger.debug("  %s/%s: %d face(s)", slug, ref_img.name, len(embs))

        if embeddings:
            refs.append(PerformerRef(
                slug=slug, display_name=display_name,
                stash_id=stash_id, embeddings=embeddings,
            ))
            logger.info("  %s: %d embeddings, stash_id=%s", slug, len(embeddings), stash_id)
        else:
            logger.warning("  %s: no faces detected in reference images", slug)

    # Save cache
    ref_data = {}
    for pr in refs:
        ref_data[pr.slug] = {
            "display_name": pr.display_name,
            "stash_id": pr.stash_id,
            "embeddings": [e.tolist() for e in pr.embeddings],
        }
    EMBEDDINGS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(str(EMBEDDINGS_CACHE), ref_data=ref_data)
    logger.info("Cached %d performer references to %s", len(refs), EMBEDDINGS_CACHE)
    return refs


def match_face(
    embedding: np.ndarray,
    refs: list[PerformerRef],
) -> list[tuple[PerformerRef, float]]:
    """Match a face embedding against all references via cosine similarity."""
    matches = []
    for ref in refs:
        if not ref.embeddings:
            continue
        best_sim = max(float(np.dot(embedding, re)) for re in ref.embeddings)
        matches.append((ref, best_sim))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# Scene processing
# ---------------------------------------------------------------------------

def process_scene(
    scene: dict,
    refs: list[PerformerRef],
    dry_run: bool = False,
) -> dict:
    """Process a single scene: extract frames, detect faces, match, tag."""
    scene_id = scene["id"]
    title = scene.get("title", "")
    files = scene.get("files", [])

    result = {
        "scene_id": scene_id,
        "title": title,
        "tagged": [],
        "review": [],
        "faces_detected": 0,
        "frames_extracted": 0,
        "errors": [],
    }

    if not files:
        result["errors"].append("No files for scene")
        return result

    stash_path = files[0]["path"]
    duration = files[0].get("duration") or 300
    local_path = _stash_to_local_path(stash_path)

    if local_path is None:
        result["errors"].append(f"Cannot map path: {stash_path}")
        return result

    frames = extract_frames(local_path, duration, count=MAX_FRAMES_PER_SCENE)
    result["frames_extracted"] = len(frames)

    if not frames:
        result["errors"].append("No frames extracted")
        return result

    # Aggregate best similarity per performer across all frames
    all_matches: dict[str, float] = {}
    for frame in frames:
        embeddings = compute_embedding(frame)
        result["faces_detected"] += len(embeddings)
        for emb in embeddings:
            top = match_face(emb, refs)
            for ref, sim in top[:3]:
                if sim > REVIEW_THRESHOLD:
                    all_matches[ref.slug] = max(all_matches.get(ref.slug, 0), sim)

    to_tag = []
    to_review = []
    for slug, sim in sorted(all_matches.items(), key=lambda x: x[1], reverse=True):
        ref = next(r for r in refs if r.slug == slug)
        entry = {"performer": ref.display_name, "slug": slug, "similarity": round(sim, 4)}

        if sim >= AUTO_TAG_THRESHOLD:
            to_tag.append(entry)
            if ref.stash_id and not dry_run:
                try:
                    tag_scene_performer(scene_id, [ref.stash_id])
                    entry["tagged"] = True
                    logger.info("  TAGGED scene %s <- %s (sim=%.3f)", scene_id, ref.display_name, sim)
                except Exception as e:
                    entry["error"] = str(e)
                    logger.error("  Tag failed: %s", e)
            elif not ref.stash_id:
                entry["error"] = "No stash_id"
                logger.warning("  MATCH %s but no stash_id", ref.display_name)
        elif sim >= REVIEW_THRESHOLD:
            to_review.append(entry)
            logger.info("  REVIEW scene %s ~ %s (sim=%.3f)", scene_id, ref.display_name, sim)

    result["tagged"] = to_tag
    result["review"] = to_review

    for f in frames:
        try:
            f.unlink()
        except OSError:
            pass

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stash Face Tagger")
    parser.add_argument("--build-refs", action="store_true", help="Rebuild reference embeddings")
    parser.add_argument("--batch-size", type=int, default=20, help="Scenes per batch")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without tagging")
    parser.add_argument("--scene-id", type=str, help="Process a specific scene ID")
    parser.add_argument("--threshold", type=float, default=AUTO_TAG_THRESHOLD,
                        help="Auto-tag similarity threshold")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Update module-level threshold from CLI arg
    _update_threshold(args.threshold)

    refs = build_reference_embeddings(force=args.build_refs)
    if not refs:
        logger.error("No reference embeddings. Run with --build-refs first.")
        sys.exit(1)

    logger.info(
        "Ready: %d performers, %d total embeddings",
        len(refs), sum(len(r.embeddings) for r in refs),
    )

    if args.build_refs:
        logger.info("Reference embeddings built successfully.")
        return

    if args.scene_id:
        scene = get_scene_by_id(args.scene_id)
        if not scene:
            logger.error("Scene %s not found", args.scene_id)
            sys.exit(1)
        scenes = [scene]
    else:
        scenes = get_untagged_scenes(batch_size=args.batch_size)

    if not scenes:
        logger.info("No scenes to process.")
        return

    results = []
    tagged_count = 0
    review_count = 0
    t0 = time.time()

    for i, scene in enumerate(scenes):
        logger.info(
            "[%d/%d] Scene %s: %s",
            i + 1, len(scenes), scene["id"], scene.get("title", "")[:60],
        )
        result = process_scene(scene, refs, dry_run=args.dry_run)
        results.append(result)
        tagged_count += len(result["tagged"])
        review_count += len(result["review"])

    elapsed = time.time() - t0

    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "scenes_processed": len(scenes),
        "tagged": tagged_count,
        "review_queue": review_count,
        "elapsed_seconds": round(elapsed, 1),
        "dry_run": args.dry_run,
        "results": results,
    }

    history = []
    if RESULTS_LOG.exists():
        try:
            history = json.loads(RESULTS_LOG.read_text())
        except Exception:
            pass
    history.append(log_entry)
    if len(history) > 100:
        history = history[-100:]
    RESULTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_LOG.write_text(json.dumps(history, indent=2))

    logger.info("=" * 60)
    logger.info("RESULTS: %d scenes in %.1fs", len(scenes), elapsed)
    logger.info("  Auto-tagged:  %d", tagged_count)
    logger.info("  Review queue: %d", review_count)
    if args.dry_run:
        logger.info("  (DRY RUN -- no tags applied)")
    logger.info("Saved to %s", RESULTS_LOG)


if __name__ == "__main__":
    main()
