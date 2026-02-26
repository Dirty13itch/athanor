#!/usr/bin/env python3
"""
build-profile.sh (Python) — Gather user profile data and upsert to Qdrant preferences.
Run from DEV (WSL2). Requires: gh CLI, git, ssh access to Node 1.
Usage: python3 scripts/build-profile.sh
"""

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone

QDRANT_HOST = "192.168.1.244"
QDRANT_PORT = 6333
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
COLLECTION = "preferences"

# Embedding goes through SSH to Node 1 (vllm-embedding on localhost:8001 there)
EMBEDDING_MODEL = "/models/Qwen3-Embedding-0.6B"


def run(cmd: str, timeout: int = 30) -> str:
    """Run shell command, return stdout."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


def get_embedding(text: str) -> list[float] | None:
    """Get 1024-dim embedding from vLLM-embedding on Node 1 via SSH."""
    # Escape text for JSON
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "'\\''")
    payload = json.dumps({"model": EMBEDDING_MODEL, "input": text})
    # SSH to node1, curl locally
    cmd = f"""ssh node1 'curl -sf http://localhost:8001/v1/embeddings -H "Content-Type: application/json" -d {json.dumps(payload)}' 2>/dev/null"""
    result = run(cmd, timeout=30)
    if not result:
        return None
    try:
        data = json.loads(result)
        return data["data"][0]["embedding"]
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


def upsert_point(point_id: str, category: str, key: str, value: str) -> bool:
    """Upsert a single preference point to Qdrant."""
    text = f"{category}: {key} = {value}"
    vector = get_embedding(text)
    if vector is None:
        print(f"  SKIP {category}/{key} — no embedding")
        return False

    # Deterministic UUID from string ID
    uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))

    payload = {
        "agent": "global",
        "signal_type": "profile",
        "content": value,
        "category": category,
        "key": key,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timestamp_unix": int(datetime.now(timezone.utc).timestamp()),
    }

    body = json.dumps({"points": [{"id": uid, "vector": vector, "payload": payload}]})

    cmd = f"""curl -sf '{QDRANT_URL}/collections/{COLLECTION}/points' -H 'Content-Type: application/json' -X PUT -d '{body}' 2>/dev/null"""
    # Use subprocess to avoid shell quoting issues with large JSON
    try:
        r = subprocess.run(
            ["curl", "-sf", f"{QDRANT_URL}/collections/{COLLECTION}/points",
             "-H", "Content-Type: application/json", "-X", "PUT", "-d", body],
            capture_output=True, text=True, timeout=15,
        )
        result = json.loads(r.stdout) if r.stdout else {}
        if result.get("status") == "ok":
            print(f"  OK {category}/{key} ({uid[:8]}...)")
            return True
        else:
            print(f"  FAIL {category}/{key}: {r.stdout[:200]}")
            return False
    except Exception as e:
        print(f"  FAIL {category}/{key}: {e}")
        return False


def main():
    print("=== Athanor Profile Builder ===")
    print(f"Qdrant: {QDRANT_URL}/collections/{COLLECTION}")
    print(f"Embedding: {EMBEDDING_MODEL} via SSH to Node 1")
    print()

    # --- Gather data ---
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

    # --- Upsert to Qdrant ---
    print("=== Upserting to Qdrant preferences ===")
    ok = 0
    total = 0

    # Identity
    items = [
        ("profile-identity", "identity", "name", git_name),
        ("profile-email", "identity", "email", git_email),
        ("profile-github", "identity", "github", f"{gh_login} — {gh_repos_count} public repos, {len(repos)} total"),
        ("profile-reddit", "identity", "reddit", "SudoMakeMeAHotdish (NSFW access)"),
    ]

    # Work patterns
    items += [
        ("profile-schedule", "work_pattern", "schedule", "Evenings weekdays, weekends primary. Amanda is home. Keep noise/heat/power reasonable."),
        ("profile-role", "work_pattern", "role", "Orchestrator not coder. Specifies requirements and architectural intent. AI agents write code."),
        ("profile-interface", "work_pattern", "primary_interface", "Command Center PWA at Node 2:3001. Claudeman at DEV:3000. Terminal fallback."),
        ("profile-style", "work_pattern", "decision_style", "Research then document then decide then build. Depth over speed. Craft orientation."),
    ]

    # Interests (from starred repos)
    items += [
        ("profile-interest-agents", "interests", "ai_agents", "AutoGPT, MetaGPT, CrewAI, babyagi, gpt-pilot, gpt-engineer, claude-flow, eliza, Roo-Code"),
        ("profile-interest-llm", "interests", "llm_infrastructure", "vllm, litellm, open-webui, gpt4all, SillyTavern, unsloth, LibreChat"),
        ("profile-interest-rag", "interests", "rag_knowledge", "ragflow, private-gpt, quivr, DocsGPT, anything-llm, Perplexica"),
        ("profile-interest-creative", "interests", "creative_ai", "civitai, ComfyUI, Flux, Wan2.x video generation"),
        ("profile-interest-claude", "interests", "claude_ecosystem", "SuperClaude, claude-mem, awesome-claude-code-subagents, context7, hookify"),
    ]

    # Projects
    items += [
        ("profile-project-athanor", "projects", "athanor", "Unified local AI/media/creative/home automation. 4 nodes, 7 GPUs, 8 agents, Command Center PWA."),
        ("profile-project-eoq", "projects", "eoq", "Empire of Broken Queens — AI-driven interactive cinematic adult game. Deployed Node 2:3002."),
        ("profile-project-energy", "projects", "ulrich_energy", "Ulrich Energy — business project, energy auditing tools."),
        ("profile-project-kindred", "projects", "kindred", "Kindred — passion-based social matching. Concept phase, dual-embedding architecture."),
    ]

    for point_id, category, key, value in items:
        total += 1
        if upsert_point(point_id, category, key, value):
            ok += 1

    print()
    print(f"=== Done: {ok}/{total} points upserted ===")
    if ok < total:
        print(f"({total - ok} failed — check embedding/Qdrant connectivity)")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
