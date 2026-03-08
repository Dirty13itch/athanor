#!/usr/bin/env python3
"""Sync Athanor agent system prompts to LangFuse prompt management.

Reads SYSTEM_PROMPT constants from each agent source file, computes a
content hash, and creates a new LangFuse prompt version only when the
content has changed.  Fully idempotent — safe to run on every deploy.

Usage:
    python3 scripts/sync-prompts-to-langfuse.py
    python3 scripts/sync-prompts-to-langfuse.py --dry-run
    python3 scripts/sync-prompts-to-langfuse.py --host http://192.168.1.203:3030

Env overrides:
    LANGFUSE_PUBLIC_KEY  (default: pk-lf-athanor)
    LANGFUSE_SECRET_KEY  (default: sk-lf-athanor)
    LANGFUSE_HOST        (default: http://192.168.1.203:3030)
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# --- Defaults (match ansible/roles/vault-langfuse) ---
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://192.168.1.203:3030")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-athanor")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-athanor")

# --- Agent definitions ---
# Maps agent_id -> (source file relative to AGENTS_DIR, tools list name(s))
AGENTS_DIR = Path(__file__).resolve().parent.parent / "projects" / "agents" / "src" / "athanor_agents" / "agents"

AGENT_DEFS: dict[str, dict] = {
    "general-assistant": {
        "file": "general.py",
        "tools": [
            "check_services", "get_gpu_metrics", "get_vllm_models",
            "get_storage_info", "delegate_to_agent", "check_task_status",
            "read_file", "list_directory", "search_files",
        ],
    },
    "research-agent": {
        "file": "research.py",
        "tools": ["web_search", "fetch_page", "search_knowledge", "query_infrastructure"],
    },
    "knowledge-agent": {
        "file": "knowledge.py",
        "tools": [
            "search_knowledge", "search_signals", "deep_search",
            "list_documents", "query_knowledge_graph", "find_related_docs",
            "get_knowledge_stats",
        ],
    },
    "creative-agent": {
        "file": "creative.py",
        "tools": [
            "generate_image", "generate_video", "generate_character_portrait",
            "check_queue", "get_generation_history", "get_comfyui_status",
        ],
    },
    "home-agent": {
        "file": "home.py",
        "tools": [
            "get_ha_states", "get_entity_state", "find_entities",
            "call_ha_service", "set_light_brightness", "set_climate_temperature",
            "list_automations", "trigger_automation", "activate_scene",
            "get_entity_history", "get_network_devices",
        ],
    },
    "media-agent": {
        "file": "media.py",
        "tools": [
            "search_tv_shows", "get_tv_calendar", "get_tv_queue",
            "get_tv_library", "add_tv_show", "search_movies",
            "get_movie_calendar", "get_movie_queue", "get_movie_library",
            "add_movie", "get_plex_activity", "get_watch_history",
            "get_plex_libraries",
        ],
    },
    "coding-agent": {
        "file": "coding.py",
        "tools": [
            "generate_code", "review_code", "explain_code", "transform_code",
            "read_file", "write_file", "list_directory", "search_files",
            "run_command",
        ],
    },
    "stash-agent": {
        "file": "stash.py",
        "tools": [
            "get_stash_stats", "search_scenes", "get_scene_details",
            "search_performers", "list_tags", "find_duplicates",
            "scan_library", "auto_tag", "generate_content",
            "update_scene_rating", "mark_scene_organized", "get_recent_scenes",
        ],
    },
    "data-curator": {
        "file": "data_curator.py",
        "tools": [
            "scan_directory", "parse_document", "analyze_content",
            "index_document", "search_personal", "get_scan_status",
            "sync_gdrive",
        ],
    },
}


def extract_system_prompt(filepath: Path) -> str | None:
    """Extract SYSTEM_PROMPT string constant from a Python source file using AST."""
    try:
        source = filepath.read_text()
    except FileNotFoundError:
        print(f"  ERROR: file not found: {filepath}", file=sys.stderr)
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as exc:
        print(f"  ERROR: syntax error in {filepath}: {exc}", file=sys.stderr)
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
                    # Handle JoinedStr (f-string) — unlikely but defensive
                    print(f"  WARNING: SYSTEM_PROMPT in {filepath} is not a plain string constant", file=sys.stderr)
                    return None

    print(f"  WARNING: no SYSTEM_PROMPT found in {filepath}", file=sys.stderr)
    return None


def content_hash(text: str) -> str:
    """SHA-256 of prompt content for change detection."""
    return hashlib.sha256(text.encode()).hexdigest()


def get_existing_prompt(client: httpx.Client, host: str, name: str) -> dict | None:
    """Fetch the latest version of a prompt from LangFuse. Returns None if not found."""
    url = f"{host}/api/public/v2/prompts/{name}"
    try:
        resp = client.get(url)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        print(f"  WARNING: GET {name} returned {resp.status_code}: {resp.text}", file=sys.stderr)
        return None
    except httpx.RequestError as exc:
        print(f"  ERROR: request failed for {name}: {exc}", file=sys.stderr)
        return None


def create_prompt_version(
    client: httpx.Client,
    host: str,
    name: str,
    prompt_text: str,
    labels: list[str],
    metadata: dict,
) -> bool:
    """Create a new prompt version in LangFuse. Returns True on success."""
    url = f"{host}/api/public/v2/prompts"
    payload = {
        "name": name,
        "prompt": prompt_text,
        "type": "text",
        "labels": labels,
        "config": metadata,
    }
    try:
        resp = client.post(url, json=payload)
        if resp.status_code in (200, 201):
            version = resp.json().get("version", "?")
            print(f"  SYNCED: {name} -> version {version}")
            return True
        print(f"  ERROR: POST {name} returned {resp.status_code}: {resp.text}", file=sys.stderr)
        return False
    except httpx.RequestError as exc:
        print(f"  ERROR: request failed for {name}: {exc}", file=sys.stderr)
        return False


def prompt_changed(existing: dict | None, new_hash: str) -> bool:
    """Check if the prompt content has changed by comparing hashes stored in config."""
    if existing is None:
        return True
    config = existing.get("config", {}) or {}
    return config.get("content_hash") != new_hash


def sync_all(host: str, dry_run: bool = False) -> tuple[int, int, int]:
    """Sync all agent prompts. Returns (synced, unchanged, errors)."""
    synced = 0
    unchanged = 0
    errors = 0

    auth = (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
    client = httpx.Client(auth=auth, timeout=30.0)

    # Verify connectivity
    try:
        health = client.get(f"{host}/api/public/health")
        if health.status_code != 200:
            print(f"ERROR: LangFuse health check failed ({health.status_code})", file=sys.stderr)
            sys.exit(1)
    except httpx.RequestError as exc:
        print(f"ERROR: Cannot reach LangFuse at {host}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"LangFuse: {host} (healthy)")
    print(f"Syncing {len(AGENT_DEFS)} agent prompts...\n")

    now = datetime.now(timezone.utc).isoformat()

    for agent_id, agent_def in sorted(AGENT_DEFS.items()):
        filepath = AGENTS_DIR / agent_def["file"]
        prompt_name = f"agent-{agent_id}"

        print(f"[{agent_id}]")

        # Extract prompt from source
        prompt_text = extract_system_prompt(filepath)
        if prompt_text is None:
            errors += 1
            continue

        new_hash = content_hash(prompt_text)

        # Check existing version
        existing = get_existing_prompt(client, host, prompt_name)

        if not prompt_changed(existing, new_hash):
            print(f"  UNCHANGED (hash matches)")
            unchanged += 1
            continue

        if dry_run:
            action = "CREATE" if existing is None else "UPDATE"
            print(f"  DRY RUN: would {action} {prompt_name}")
            synced += 1
            continue

        # Build metadata
        metadata = {
            "agent_name": agent_id,
            "content_hash": new_hash,
            "last_synced": now,
            "tools": agent_def["tools"],
            "source_file": str(filepath.relative_to(Path(__file__).resolve().parent.parent)),
        }

        labels = ["production", "latest"]

        if create_prompt_version(client, host, prompt_name, prompt_text, labels, metadata):
            synced += 1
        else:
            errors += 1

    client.close()
    return synced, unchanged, errors


def main():
    parser = argparse.ArgumentParser(
        description="Sync Athanor agent system prompts to LangFuse prompt management."
    )
    parser.add_argument(
        "--host",
        default=LANGFUSE_HOST,
        help=f"LangFuse base URL (default: {LANGFUSE_HOST})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes",
    )
    args = parser.parse_args()

    synced, unchanged, errors = sync_all(args.host, dry_run=args.dry_run)

    print(f"\nResults: {synced} synced, {unchanged} unchanged, {errors} errors")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
