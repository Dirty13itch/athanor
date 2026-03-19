#!/usr/bin/env python3
"""Context Compression Pipeline — local 50K → 2K brief → cloud.

Reduces cloud subscription token consumption by 25x.
Routes long context through local Qwen3.5-27B (free, unlimited) to generate
a compressed brief before sending to expensive cloud models.

Usage:
  # As a library
  from context_compress import compress_context
  brief = await compress_context(long_text, max_tokens=2000)

  # As a CLI
  echo "long text..." | python3 context-compress.py
  python3 context-compress.py < large_file.txt
  python3 context-compress.py --file /path/to/codebase.md --max-tokens 2000
"""
import argparse
import asyncio
import json
import os
import sys

import httpx

LITELLM_URL = os.environ.get("LITELLM_URL", "http://192.168.1.203:4000/v1")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "sk-athanor-litellm-2026")
LOCAL_MODEL = os.environ.get("COMPRESS_MODEL", "reasoning")  # Free local Qwen3.5-27B

COMPRESS_SYSTEM_PROMPT = """You are a context compression engine. Your job is to read a large body of text and produce a dense, information-preserving brief.

Rules:
1. Preserve ALL technical details: names, numbers, versions, URLs, config values, error messages
2. Preserve ALL decisions and their rationale
3. Preserve ALL action items and their status
4. Remove filler, pleasantries, repeated information, verbose explanations
5. Use bullet points and terse language
6. Keep code snippets only if they are the core of the information
7. The output must be self-contained — someone reading ONLY the brief must understand the full context

Output format: Dense markdown bullets, no headers unless structurally necessary."""


async def compress_context(
    text: str,
    max_tokens: int = 2000,
    model: str = LOCAL_MODEL,
) -> str:
    """Compress long text into a dense brief using local LLM."""
    # If already short, return as-is
    word_count = len(text.split())
    if word_count < max_tokens:
        return text

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{LITELLM_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": COMPRESS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Compress this context into ~{max_tokens} tokens. Preserve ALL technical details:\n\n{text}"},
                ],
                "max_tokens": max_tokens + 500,  # Some headroom
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        brief = data["choices"][0]["message"]["content"]

        # Log compression stats
        input_words = word_count
        output_words = len(brief.split())
        ratio = input_words / max(output_words, 1)
        print(f"[compress] {input_words} words → {output_words} words ({ratio:.1f}x compression)", file=sys.stderr)

        return brief


async def compress_for_cloud(
    text: str,
    question: str,
    cloud_model: str = "claude",
    max_brief_tokens: int = 2000,
) -> str:
    """Full pipeline: compress context locally, then query cloud with the brief."""
    brief = await compress_context(text, max_tokens=max_brief_tokens)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{LITELLM_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": cloud_model,
                "messages": [
                    {"role": "system", "content": "You are answering based on compressed context. The brief below contains all relevant information."},
                    {"role": "user", "content": f"Context brief:\n{brief}\n\nQuestion: {question}"},
                ],
                "max_tokens": 4000,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def main():
    parser = argparse.ArgumentParser(description="Context compression pipeline")
    parser.add_argument("--file", "-f", help="File to compress")
    parser.add_argument("--max-tokens", "-t", type=int, default=2000, help="Max output tokens")
    parser.add_argument("--model", "-m", default=LOCAL_MODEL, help="Model for compression")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("No input text", file=sys.stderr)
        sys.exit(1)

    brief = asyncio.run(compress_context(text, max_tokens=args.max_tokens, model=args.model))
    print(brief)


if __name__ == "__main__":
    main()
