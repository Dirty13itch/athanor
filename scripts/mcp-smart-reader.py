#!/usr/bin/env python3
"""MCP server: smart file reading with local model summarization.

Token offloading Strategy 1C from docs/research/2026-03-07-claude-code-local-model-offloading.md.
Reads files, diffs, logs, and grep results — summarizes large outputs via the local
reasoning model (Qwen3-32B) through LiteLLM, saving Claude API tokens.

Includes Redis caching keyed on file_path + mtime with 1-hour TTL.

Usage in .mcp.json:
  "smart-reader": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-smart-reader.py"],
    "env": {}
  }
"""

import hashlib
import json
import os
import subprocess
import sys

import httpx
import redis
from mcp.server.fastmcp import FastMCP

# --- Configuration ---

LITELLM_BASE = os.environ.get("LITELLM_BASE_URL", "http://192.168.1.203:4000/v1")
LITELLM_KEY = os.environ.get("LITELLM_API_KEY", "sk-athanor-litellm-2026")
LITELLM_MODEL = os.environ.get("LITELLM_MODEL", "reasoning")

REDIS_HOST = os.environ.get("REDIS_HOST", "192.168.1.203")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "athanor2026")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))  # 1 hour

CHARS_PER_TOKEN = 4  # rough estimate

# --- Clients ---

_http = httpx.Client(timeout=120, base_url=LITELLM_BASE, headers={
    "Authorization": f"Bearer {LITELLM_KEY}",
    "Content-Type": "application/json",
})

try:
    _redis = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD,
        decode_responses=True, socket_connect_timeout=3,
    )
    _redis.ping()
    _redis_ok = True
except Exception:
    _redis = None
    _redis_ok = False
    print("Warning: Redis unavailable, caching disabled", file=sys.stderr)

mcp = FastMCP("smart-reader")


# --- Helpers ---

def _estimate_tokens(text: str) -> int:
    """Rough token count estimate."""
    return len(text) // CHARS_PER_TOKEN


def _cache_key(prefix: str, *parts: str) -> str:
    """Build a deterministic cache key from parts."""
    raw = "|".join(parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"smart-reader:{prefix}:{h}"


def _cache_get(key: str) -> str | None:
    """Try to read from Redis cache."""
    if not _redis_ok:
        return None
    try:
        return _redis.get(key)
    except Exception:
        return None


def _cache_set(key: str, value: str) -> None:
    """Write to Redis cache with TTL."""
    if not _redis_ok:
        return
    try:
        _redis.set(key, value, ex=CACHE_TTL)
    except Exception:
        pass


def _file_mtime(path: str) -> str:
    """Get file mtime as string for cache invalidation."""
    try:
        return str(os.path.getmtime(path))
    except OSError:
        return "0"


def _summarize(content: str, instruction: str) -> str:
    """Send content to the local reasoning model for summarization."""
    try:
        resp = _http.post("/chat/completions", json={
            "model": LITELLM_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise technical summarizer. Produce concise, "
                        "information-dense summaries. Preserve exact names, paths, "
                        "numbers, error messages, and key identifiers. No fluff."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{instruction}\n\n---\n\n{content}",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 2048,
        })
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[Summarization failed: {e}]\n\n{content[:4000]}"


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    """Run a subprocess and return (returncode, stdout+stderr)."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=30,
    )
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
    return result.returncode, output.strip()


# --- MCP Tools ---

@mcp.tool()
def smart_read(file_path: str, max_tokens: int = 2000) -> str:
    """Read a file. If content exceeds max_tokens, summarize it with the local
    reasoning model (Qwen3-32B) to save Claude API tokens. Short files are
    returned in full.

    Args:
        file_path: Absolute path to the file to read.
        max_tokens: Token budget. Files exceeding this get summarized (default 2000).
    """
    path = os.path.expanduser(file_path)
    if not os.path.isfile(path):
        return f"Error: file not found: {path}"

    # Check cache
    mtime = _file_mtime(path)
    cache_k = _cache_key("read", path, mtime, str(max_tokens))
    cached = _cache_get(cache_k)
    if cached:
        return cached

    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return f"Error reading {path}: {e}"

    line_count = content.count("\n") + 1
    token_est = _estimate_tokens(content)

    if token_est <= max_tokens:
        return content

    # Summarize
    instruction = (
        f"Summarize this file ({path}, {line_count} lines, ~{token_est} tokens). "
        f"Preserve key structure, important definitions, config values, and any "
        f"notable patterns or issues. Output should fit within {max_tokens} tokens."
    )
    summary = _summarize(content, instruction)
    result = (
        f"[Summarized by local model — full file: {line_count} lines, "
        f"~{token_est} tokens at {path}]\n\n{summary}"
    )
    _cache_set(cache_k, result)
    return result


@mcp.tool()
def smart_diff(base_branch: str = "main", max_tokens: int = 3000) -> str:
    """Run git diff against a base branch and summarize if large. Preserves
    file names and key changes. Uses local reasoning model for summarization.

    Args:
        base_branch: Branch to diff against (default "main").
        max_tokens: Token budget before summarization kicks in (default 3000).
    """
    # Cache key uses the current HEAD and base branch ref
    rc, head_sha = _run(["git", "rev-parse", "HEAD"])
    if rc != 0:
        return "Error: not in a git repository"
    rc, base_sha = _run(["git", "rev-parse", base_branch])
    if rc != 0:
        return f"Error: branch '{base_branch}' not found"

    cache_k = _cache_key("diff", head_sha.strip(), base_sha.strip())
    cached = _cache_get(cache_k)
    if cached:
        return cached

    rc, diff_output = _run(["git", "diff", base_branch])
    if rc != 0:
        return f"Error running git diff: {diff_output}"

    if not diff_output.strip():
        return f"No differences from {base_branch}."

    token_est = _estimate_tokens(diff_output)
    if token_est <= max_tokens:
        return diff_output

    # Get stat for context
    _, stat_output = _run(["git", "diff", "--stat", base_branch])

    instruction = (
        f"Summarize this git diff (against {base_branch}, ~{token_est} tokens). "
        f"For each changed file, describe what changed and why it matters. "
        f"Preserve file paths, function/class names, and config values.\n\n"
        f"Diff stat:\n{stat_output}"
    )
    summary = _summarize(diff_output, instruction)
    result = (
        f"[Diff summarized by local model — ~{token_est} tokens raw]\n\n"
        f"Files changed:\n{stat_output}\n\n{summary}"
    )
    _cache_set(cache_k, result)
    return result


@mcp.tool()
def smart_log(file_path: str, lines: int = 500, pattern: str | None = None) -> str:
    """Read the last N lines of a log file. Optionally filter by pattern.
    Summarize with the local model to extract key events, errors, and patterns.

    Args:
        file_path: Absolute path to the log file.
        lines: Number of lines from the end to read (default 500).
        pattern: Optional regex/string pattern to filter lines before summarization.
    """
    path = os.path.expanduser(file_path)
    if not os.path.isfile(path):
        return f"Error: file not found: {path}"

    mtime = _file_mtime(path)
    filter_key = pattern or "none"
    cache_k = _cache_key("log", path, mtime, str(lines), filter_key)
    cached = _cache_get(cache_k)
    if cached:
        return cached

    # Read last N lines efficiently
    rc, output = _run(["tail", "-n", str(lines), path])
    if rc != 0:
        return f"Error reading {path}: {output}"

    if pattern:
        # Filter with grep
        try:
            result = subprocess.run(
                ["grep", "-E", pattern],
                input=output, capture_output=True, text=True, timeout=10,
            )
            output = result.stdout.strip()
            if not output:
                return f"No lines matching '{pattern}' in last {lines} lines of {path}."
        except Exception as e:
            return f"Error filtering: {e}"

    line_count = output.count("\n") + 1
    token_est = _estimate_tokens(output)

    if token_est <= 1500:
        return output

    instruction = (
        f"Analyze this log output ({path}, {line_count} lines). Extract:\n"
        f"1. Key events and state changes\n"
        f"2. Errors and warnings with exact messages\n"
        f"3. Patterns (repeated events, frequency, timing)\n"
        f"4. Any actionable findings\n"
        f"Preserve timestamps, error codes, and exact error text."
    )
    summary = _summarize(output, instruction)
    result = (
        f"[Log summarized by local model — {line_count} lines from {path}]\n\n{summary}"
    )
    _cache_set(cache_k, result)
    return result


@mcp.tool()
def smart_grep(
    pattern: str,
    path: str = ".",
    max_results: int = 50,
) -> str:
    """Run ripgrep and summarize extensive results using the local model.
    Groups findings by file and highlights key matches.

    Args:
        pattern: Regex pattern to search for.
        path: File or directory to search in (default current directory).
        max_results: Maximum number of result lines before summarizing (default 50).
    """
    cache_k = _cache_key("grep", pattern, path, str(max_results))
    cached = _cache_get(cache_k)
    if cached:
        return cached

    rc, output = _run([
        "rg", "--no-heading", "--line-number", "--max-count", "200",
        "--color", "never", pattern, path,
    ])

    if rc == 1:
        return f"No matches for '{pattern}' in {path}."
    if rc not in (0, 1):
        return f"Error running ripgrep: {output}"

    result_lines = output.strip().split("\n")
    total_matches = len(result_lines)

    if total_matches <= max_results:
        result = f"[{total_matches} matches]\n\n{output}"
        _cache_set(cache_k, result)
        return result

    # Summarize
    instruction = (
        f"Summarize these ripgrep results for pattern '{pattern}' "
        f"({total_matches} matches). Group by file, describe what was found "
        f"in each, and highlight the most significant matches. "
        f"Preserve file paths and line numbers for key findings."
    )
    summary = _summarize(output, instruction)
    result = (
        f"[Grep summarized by local model — {total_matches} matches for "
        f"'{pattern}' in {path}]\n\n{summary}"
    )
    _cache_set(cache_k, result)
    return result


if __name__ == "__main__":
    mcp.run()
