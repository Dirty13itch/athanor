#!/usr/bin/env python3
"""Seed Miniflux with RSS feeds for intelligence signal ingestion.

Usage: python3 scripts/seed-miniflux-feeds.py [--miniflux-url URL] [--username USER] [--password PASS]
"""

import argparse
import os
import sys

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

# Intelligence feeds organized by category
FEEDS = {
    "AI Models": [
        {"url": "https://huggingface.co/blog/feed.xml", "title": "HuggingFace Blog"},
        {"url": "https://qwenlm.github.io/feed.xml", "title": "Qwen Blog"},
        {"url": "https://www.anthropic.com/rss.xml", "title": "Anthropic Blog"},
        {"url": "https://openai.com/index/rss.xml", "title": "OpenAI Blog"},
        {"url": "https://deepmind.google/blog/rss.xml", "title": "Google DeepMind Blog"},
    ],
    "Inference Engines": [
        {"url": "https://github.com/vllm-project/vllm/releases.atom", "title": "vLLM Releases"},
        {"url": "https://github.com/sgl-project/sglang/releases.atom", "title": "SGLang Releases"},
        {"url": "https://github.com/ggml-org/llama.cpp/releases.atom", "title": "llama.cpp Releases"},
        {"url": "https://github.com/ollama/ollama/releases.atom", "title": "Ollama Releases"},
    ],
    "Dev Tools": [
        {"url": "https://github.com/anthropics/claude-code/releases.atom", "title": "Claude Code Releases"},
        {"url": "https://github.com/BerriAI/litellm/releases.atom", "title": "LiteLLM Releases"},
        {"url": "https://github.com/langchain-ai/langgraph/releases.atom", "title": "LangGraph Releases"},
        {"url": "https://github.com/langfuse/langfuse/releases.atom", "title": "LangFuse Releases"},
        {"url": "https://github.com/qdrant/qdrant/releases.atom", "title": "Qdrant Releases"},
    ],
    "Infrastructure": [
        {"url": "https://github.com/home-assistant/core/releases.atom", "title": "Home Assistant Releases"},
        {"url": "https://github.com/docker/compose/releases.atom", "title": "Docker Compose Releases"},
        {"url": "https://ubuntu.com/blog/feed", "title": "Ubuntu Blog"},
    ],
    "AI News": [
        {"url": "https://hnrss.org/newest?q=vllm+OR+llama.cpp+OR+local+llm+OR+self-hosted+AI&points=50", "title": "HN: Local AI"},
        {"url": "https://hnrss.org/newest?q=homelab+OR+home+server+OR+unraid&points=30", "title": "HN: Homelab"},
        {"url": "https://simonwillison.net/atom/everything/", "title": "Simon Willison"},
        {"url": "https://www.latent.space/feed", "title": "Latent Space Podcast"},
    ],
    "Security": [
        {"url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", "title": "CISA KEV"},
        {"url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml", "title": "NVD CVE Feed"},
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Seed Miniflux with intelligence feeds")
    parser.add_argument(
        "--miniflux-url",
        default=os.environ.get("ATHANOR_MINIFLUX_URL") or os.environ.get("MINIFLUX_URL") or "http://192.168.1.203:8070",
        help="Miniflux URL",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("ATHANOR_MINIFLUX_USER") or os.environ.get("MINIFLUX_USER") or "admin",
        help="Miniflux admin username",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("ATHANOR_MINIFLUX_PASSWORD") or os.environ.get("MINIFLUX_PASSWORD") or "",
        help="Miniflux admin password",
    )
    args = parser.parse_args()

    base = args.miniflux_url.rstrip("/")
    auth = (args.username, args.password)

    if not args.password:
        print(
            "ERROR: Set ATHANOR_MINIFLUX_PASSWORD or MINIFLUX_PASSWORD before seeding feeds.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Verify connection
    try:
        r = requests.get(f"{base}/v1/me", auth=auth, timeout=5)
        r.raise_for_status()
        print(f"Connected to Miniflux as {r.json().get('username', '?')}")
    except Exception as e:
        print(f"ERROR: Cannot connect to Miniflux at {base}: {e}", file=sys.stderr)
        sys.exit(1)

    # Get existing feeds to avoid duplicates
    existing = requests.get(f"{base}/v1/feeds", auth=auth, timeout=10).json()
    existing_urls = {f["feed_url"] for f in existing}

    # Create categories and add feeds
    categories = requests.get(f"{base}/v1/categories", auth=auth, timeout=5).json()
    cat_map = {c["title"]: c["id"] for c in categories}

    added = 0
    skipped = 0

    for category, feeds in FEEDS.items():
        # Create category if it doesn't exist
        if category not in cat_map:
            r = requests.post(
                f"{base}/v1/categories",
                auth=auth,
                json={"title": category},
                timeout=5,
            )
            if r.status_code == 201:
                cat_map[category] = r.json()["id"]
                print(f"  Created category: {category}")
            else:
                print(f"  WARN: Could not create category {category}: {r.text}", file=sys.stderr)
                continue

        cat_id = cat_map[category]

        for feed in feeds:
            if feed["url"] in existing_urls:
                skipped += 1
                continue

            r = requests.post(
                f"{base}/v1/feeds",
                auth=auth,
                json={
                    "feed_url": feed["url"],
                    "category_id": cat_id,
                },
                timeout=30,
            )

            if r.status_code == 201:
                added += 1
                print(f"  + {feed['title']}")
            else:
                error = r.json().get("error_message", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
                print(f"  WARN: {feed['title']}: {error}", file=sys.stderr)

    print(f"\nDone: {added} feeds added, {skipped} already existed")


if __name__ == "__main__":
    main()
