#!/usr/bin/env python3
"""
build-profile.py - Gather user profile data and upsert to Qdrant preferences.
Run from DEV (WSL2). Requires: gh CLI, git, and network access to Athanor services.
Usage: python3 scripts/build-profile.py
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import get_url

COLLECTION = "preferences"
DEFAULT_QDRANT_URL = get_url("qdrant")
DEFAULT_EMBEDDING_URL = get_url("embedding")
EMBEDDING_MODEL = os.environ.get("ATHANOR_EMBEDDING_MODEL", "qwen3-embed-8b")


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _ensure_openai_base_url(url: str) -> str:
    normalized = _normalize_url(url)
    return normalized if normalized.endswith("/v1") else f"{normalized}/v1"


QDRANT_URL = _normalize_url(os.environ.get("ATHANOR_QDRANT_URL", DEFAULT_QDRANT_URL))
EMBEDDING_BASE_URL = _ensure_openai_base_url(
    os.environ.get("ATHANOR_VLLM_EMBEDDING_URL", DEFAULT_EMBEDDING_URL)
)


def run(cmd: str, timeout: int = 30) -> str:
    """Run shell command, return stdout."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def get_embedding(text: str) -> list[float] | None:
    """Get an embedding from the canonical Athanor embedding service."""
    payload = json.dumps({"model": EMBEDDING_MODEL, "input": text}).encode("utf-8")
    request = Request(
        f"{EMBEDDING_BASE_URL}/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["data"][0]["embedding"]
    except (OSError, URLError, json.JSONDecodeError, KeyError, IndexError):
        return None


def upsert_point(point_id: str, category: str, key: str, value: str) -> bool:
    """Upsert a single preference point to Qdrant."""
    text = f"{category}: {key} = {value}"
    vector = get_embedding(text)
    if vector is None:
        print(f"  SKIP {category}/{key} - no embedding")
        return False

    uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))
    now = datetime.now(timezone.utc)
    payload = {
        "agent": "global",
        "signal_type": "profile",
        "content": value,
        "category": category,
        "key": key,
        "timestamp": now.isoformat(),
        "timestamp_unix": int(now.timestamp()),
    }
    body = json.dumps({"points": [{"id": uid, "vector": vector, "payload": payload}]}).encode("utf-8")

    try:
        request = Request(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            data=body,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("status") == "ok":
            print(f"  OK {category}/{key} ({uid[:8]}...)")
            return True
        print(f"  FAIL {category}/{key}: {json.dumps(result)[:200]}")
        return False
    except Exception as exc:
        print(f"  FAIL {category}/{key}: {exc}")
        return False


def main() -> int:
    print("=== Athanor Profile Builder ===")
    print(f"Qdrant: {QDRANT_URL}/collections/{COLLECTION}")
    print(f"Embedding: {EMBEDDING_MODEL} via {EMBEDDING_BASE_URL}")
    print()

    git_name = run("git config --global user.name") or "unknown"
    git_email = run("git config --global user.email") or "unknown"
    print(f"Identity: {git_name} <{git_email}>")

    gh_login = run("gh api user --jq '.login'") or "unknown"
    gh_repos_count = run("gh api user --jq '.public_repos'") or "0"
    print(f"GitHub: {gh_login} ({gh_repos_count} public repos)")

    repos_raw = run("gh api user/repos --paginate --jq '.[].name'")
    repos = repos_raw.split("\n") if repos_raw else []
    print(f"Repos: {len(repos)} total")

    starred_raw = run("gh api user/starred --paginate --jq '.[].full_name'", timeout=60)
    starred = starred_raw.split("\n") if starred_raw else []
    print(f"Starred: {len(starred)} repos")

    local_repos = run("ls ~/repos/")
    print(f"Local repos: {local_repos}")
    print()

    print("=== Upserting to Qdrant preferences ===")
    ok = 0
    total = 0

    items = [
        ("profile-identity", "identity", "name", git_name),
        ("profile-email", "identity", "email", git_email),
        ("profile-github", "identity", "github", f"{gh_login} - {gh_repos_count} public repos, {len(repos)} total"),
        ("profile-reddit", "identity", "reddit", "SudoMakeMeAHotdish (NSFW access)"),
        (
            "profile-schedule",
            "work_pattern",
            "schedule",
            "Evenings weekdays, weekends primary. Amanda is home. Keep noise, heat, and power reasonable.",
        ),
        (
            "profile-role",
            "work_pattern",
            "role",
            "Orchestrator, not coder. Specifies requirements and architectural intent. AI agents write code.",
        ),
        (
            "profile-interface",
            "work_pattern",
            "primary_interface",
            "Athanor Command Center at https://athanor.local/ (runtime fallback http://dev.athanor.local:3001 for clients that still need the local alias or internal DNS rollout). Claude Code on DEV. Terminal fallback.",
        ),
        (
            "profile-style",
            "work_pattern",
            "decision_style",
            "Research then document then decide then build. Depth over speed. Craft orientation.",
        ),
        (
            "profile-interest-agents",
            "interests",
            "ai_agents",
            "AutoGPT, MetaGPT, CrewAI, babyagi, gpt-pilot, gpt-engineer, claude-flow, eliza, Roo-Code",
        ),
        (
            "profile-interest-llm",
            "interests",
            "llm_infrastructure",
            "vllm, litellm, open-webui, gpt4all, SillyTavern, unsloth, LibreChat",
        ),
        (
            "profile-interest-rag",
            "interests",
            "rag_knowledge",
            "ragflow, private-gpt, quivr, DocsGPT, anything-llm, Perplexica",
        ),
        (
            "profile-interest-creative",
            "interests",
            "creative_ai",
            "civitai, ComfyUI, Flux, Wan2.x video generation",
        ),
        (
            "profile-interest-claude",
            "interests",
            "claude_ecosystem",
            "SuperClaude, claude-mem, awesome-claude-code-subagents, context7, hookify",
        ),
        (
            "profile-project-athanor",
            "projects",
            "athanor",
            "Unified local AI, media, creative, and home automation. 4 nodes, 8 GPUs, 9 agents, Command Center dashboard.",
        ),
        (
            "profile-project-eoq",
            "projects",
            "eoq",
            "Empire of Broken Queens - AI-driven interactive cinematic adult game. Deployed on Workshop:3002.",
        ),
        (
            "profile-project-energy",
            "projects",
            "ulrich_energy",
            "Ulrich Energy - business project, energy auditing tools.",
        ),
        (
            "profile-project-kindred",
            "projects",
            "kindred",
            "Kindred - passion-based social matching. Concept phase, dual-embedding architecture.",
        ),
    ]

    for point_id, category, key, value in items:
        total += 1
        if upsert_point(point_id, category, key, value):
            ok += 1

    print()
    print(f"=== Done: {ok}/{total} points upserted ===")
    if ok < total:
        print(f"({total - ok} failed - check embedding or Qdrant connectivity)")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
