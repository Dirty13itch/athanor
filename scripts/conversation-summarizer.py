#!/usr/bin/env python3
"""Nightly batch: summarize unsummarized conversations in Qdrant.

Scrolls through the `conversations` collection, finds points with
user_message + assistant_response but no summary, groups multi-turn
threads by agent, generates 2-3 sentence summaries via LiteLLM, and
stores them back as payload metadata.

Usage:
    python3 scripts/conversation-summarizer.py
    python3 scripts/conversation-summarizer.py --dry-run
    python3 scripts/conversation-summarizer.py --limit 20 --dry-run
    python3 scripts/conversation-summarizer.py --help

Environment:
    ATHANOR_LITELLM_API_KEY  LiteLLM API key (default: sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d)
    ATHANOR_QDRANT_URL       Qdrant base URL (from cluster_config)
    ATHANOR_LITELLM_URL      LiteLLM base URL (from cluster_config)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict

import httpx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import LITELLM_KEY, get_url

# -- Config -------------------------------------------------------------------

QDRANT_URL = get_url("qdrant").rstrip("/")
LITELLM_URL = get_url("litellm").rstrip("/")
LITELLM_KEY = os.environ.get("ATHANOR_LITELLM_API_KEY", "sk-athanor-_rmK0ymrhtnh_lFTI8I-3QEsB8buCV5d")
COLLECTION = "conversations"
SUMMARIZE_MODEL = "worker"
MAX_CONCURRENT = 3
SCROLL_BATCH = 100

SYSTEM_PROMPT = """\
You are a concise summarizer for conversation logs in a personal AI assistant system.

Given a conversation between a user and an AI agent, write a 2-3 sentence summary that captures:
1. What the user asked for or wanted to accomplish
2. What the agent did or found
3. The outcome or key result

Be factual and specific. Use plain language. Do not editorialize."""

SINGLE_TURN_TEMPLATE = """\
Agent: {agent}
User: {user_message}
Assistant: {assistant_response}"""

MULTI_TURN_TEMPLATE = """\
Agent: {agent}
Thread: {thread_id} ({turn_count} turns)

{turns}"""

TURN_TEMPLATE = """\
[Turn {n}]
User: {user_message}
Assistant: {assistant_response}"""


# -- Logging ------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# -- Qdrant helpers -----------------------------------------------------------

async def scroll_all_points(client: httpx.AsyncClient) -> list[dict]:
    """Scroll through all points in the collection."""
    points = []
    offset = None
    while True:
        body = {
            "limit": SCROLL_BATCH,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset

        resp = await client.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data["result"]["points"]
        if not batch:
            break
        points.extend(batch)
        offset = data["result"].get("next_page_offset")
        if offset is None:
            break
    return points


async def update_payload(
    client: httpx.AsyncClient,
    point_ids: list[str],
    summary: str,
) -> None:
    """Set the summary field on one or more points."""
    resp = await client.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/payload",
        json={
            "payload": {"summary": summary},
            "points": point_ids,
        },
        timeout=30,
    )
    resp.raise_for_status()


# -- LLM helpers --------------------------------------------------------------

def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks and Qwen3.5 reasoning preambles."""
    # Standard <think> tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Qwen3.5 sometimes emits reasoning as plain "Thinking Process:\n..." blocks
    # before the actual answer. Strip everything before the real summary.
    text = re.sub(
        r"^(?:Thinking Process|Thought|Reasoning|Analysis):?\s*\n(?:.*\n)*?\n*(?=\S)",
        "",
        text,
        flags=re.MULTILINE,
    )
    return text.strip()


async def summarize_text(
    client: httpx.AsyncClient,
    conversation_text: str,
    semaphore: asyncio.Semaphore,
) -> str:
    """Send conversation text to LLM and return cleaned summary."""
    async with semaphore:
        resp = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": SUMMARIZE_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": conversation_text},
                ],
                "max_tokens": 256,
                "temperature": 0.3,
                # Qwen3.5: disable thinking mode so reasoning stays in
                # <think> tags (strippable) rather than leaking into content.
                "extra_body": {
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        return strip_think_tags(raw)


# -- Core logic ---------------------------------------------------------------

def needs_summary(payload: dict) -> bool:
    """Check if a point needs summarization."""
    has_content = payload.get("user_message") and payload.get("assistant_response")
    has_summary = bool(payload.get("summary", "").strip()) if payload.get("summary") else False
    return has_content and not has_summary


def build_work_items(points: list[dict]) -> list[dict]:
    """Group points into work items for summarization.

    Multi-turn threads (>5 turns sharing a thread_id and agent) are grouped
    into a single work item. Single-turn or small-thread points become
    individual work items.
    """
    # Count turns per thread
    thread_points: dict[str, list[dict]] = defaultdict(list)
    for point in points:
        payload = point["payload"]
        if not needs_summary(payload):
            continue
        thread_id = payload.get("thread_id", "")
        if thread_id:
            thread_points[thread_id].append(point)
        else:
            thread_points[point["id"]].append(point)

    work_items = []
    for thread_id, thread in thread_points.items():
        if len(thread) > 5:
            # Group by agent within this thread
            agent_groups: dict[str, list[dict]] = defaultdict(list)
            for point in thread:
                agent = point["payload"].get("agent", "unknown")
                agent_groups[agent].append(point)

            for agent, agent_points in agent_groups.items():
                # Sort by timestamp
                agent_points.sort(
                    key=lambda p: p["payload"].get("timestamp_unix", 0)
                )
                turns_text = "\n\n".join(
                    TURN_TEMPLATE.format(
                        n=i + 1,
                        user_message=_truncate(p["payload"]["user_message"], 500),
                        assistant_response=_truncate(p["payload"]["assistant_response"], 1000),
                    )
                    for i, p in enumerate(agent_points)
                )
                text = MULTI_TURN_TEMPLATE.format(
                    agent=agent,
                    thread_id=thread_id,
                    turn_count=len(agent_points),
                    turns=turns_text,
                )
                work_items.append({
                    "point_ids": [p["id"] for p in agent_points],
                    "text": text,
                    "label": f"thread={thread_id} agent={agent} ({len(agent_points)} turns)",
                })
        else:
            # Individual points
            for point in thread:
                payload = point["payload"]
                text = SINGLE_TURN_TEMPLATE.format(
                    agent=payload.get("agent", "unknown"),
                    user_message=_truncate(payload["user_message"], 500),
                    assistant_response=_truncate(payload["assistant_response"], 2000),
                )
                work_items.append({
                    "point_ids": [point["id"]],
                    "text": text,
                    "label": f"point={point['id']} agent={payload.get('agent', '?')}",
                })
    return work_items


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, appending ellipsis if cut."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


async def run(args: argparse.Namespace) -> int:
    """Main async entry point. Returns exit code."""
    t0 = time.monotonic()

    async with httpx.AsyncClient() as client:
        # 1. Scroll all points
        log(f"Scrolling {COLLECTION} collection at {QDRANT_URL}...")
        all_points = await scroll_all_points(client)
        log(f"  Found {len(all_points)} total points")

        # 2. Build work items
        work_items = build_work_items(all_points)
        log(f"  {len(work_items)} items need summarization")

        if not work_items:
            log("Nothing to summarize. Done.")
            return 0

        # 3. Apply limit
        if args.limit and len(work_items) > args.limit:
            log(f"  Limiting to {args.limit} items")
            work_items = work_items[: args.limit]

        # 4. Dry run
        if args.dry_run:
            log("\n-- DRY RUN (no changes will be made) --\n")
            for i, item in enumerate(work_items, 1):
                log(f"  [{i}/{len(work_items)}] {item['label']}")
                if args.verbose:
                    # Show first 200 chars of the conversation text
                    preview = item["text"][:200].replace("\n", " ")
                    log(f"    Preview: {preview}...")
            log(f"\nWould summarize {len(work_items)} items. Exiting.")
            return 0

        # 5. Summarize and update
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        success = 0
        errors = 0

        for i, item in enumerate(work_items, 1):
            log(f"  [{i}/{len(work_items)}] {item['label']}")
            try:
                summary = await summarize_text(client, item["text"], semaphore)
                await update_payload(client, item["point_ids"], summary)
                success += 1
                if args.verbose:
                    log(f"    Summary: {summary[:120]}...")
            except httpx.HTTPStatusError as exc:
                errors += 1
                log(f"    ERROR: HTTP {exc.response.status_code}: {exc.response.text[:200]}")
            except Exception as exc:
                errors += 1
                log(f"    ERROR: {type(exc).__name__}: {exc}")

        elapsed = time.monotonic() - t0
        log(f"\nDone in {elapsed:.1f}s: {success} summarized, {errors} errors")

        # Output summary stats to stdout
        result = {
            "total_points": len(all_points),
            "items_processed": len(work_items),
            "success": success,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
        }
        print(json.dumps(result, indent=2))

        return 1 if errors > 0 and success == 0 else 0


# -- CLI ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize unsummarized conversations in Qdrant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                     Summarize up to 50 conversations
  %(prog)s --dry-run            Show what would be summarized
  %(prog)s --limit 10 -v        Summarize 10, verbose output
  %(prog)s --limit 0            No limit (process all)""",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be summarized without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Max conversations to process (default: 50, 0=unlimited)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show conversation previews and generated summaries",
    )
    args = parser.parse_args()

    if args.limit == 0:
        args.limit = None

    try:
        code = asyncio.run(run(args))
    except KeyboardInterrupt:
        log("\nInterrupted.")
        code = 1
    except Exception as exc:
        log(f"Fatal: {type(exc).__name__}: {exc}")
        code = 1

    sys.exit(code)


if __name__ == "__main__":
    main()
