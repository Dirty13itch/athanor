#!/usr/bin/env python3
"""Export LangFuse traces for self-improvement analysis.

Fetches recent traces from LangFuse API, extracts interactions,
and outputs structured JSON for scoring and analysis.

Usage:
    python3 scripts/export-langfuse-traces.py --since 24h --output /tmp/traces.json
    python3 scripts/export-langfuse-traces.py --since 7d --limit 500

Requires: ATHANOR_LANGFUSE_PUBLIC_KEY / ATHANOR_LANGFUSE_SECRET_KEY
or LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES

# Defaults — LangFuse on VAULT
def env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def default_langfuse_host() -> str:
    vault_host = NODES["vault"]
    return f"http://{vault_host}:3030"


LANGFUSE_HOST = env_value("ATHANOR_LANGFUSE_URL", "LANGFUSE_HOST") or default_langfuse_host()
LANGFUSE_PUBLIC_KEY = env_value("ATHANOR_LANGFUSE_PUBLIC_KEY", "LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = env_value("ATHANOR_LANGFUSE_SECRET_KEY", "LANGFUSE_SECRET_KEY")


def parse_duration(s: str) -> timedelta:
    """Parse '24h', '7d', '30m' into timedelta."""
    unit = s[-1]
    val = int(s[:-1])
    if unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    elif unit == "m":
        return timedelta(minutes=val)
    else:
        raise ValueError(f"Unknown duration unit: {unit}. Use h/d/m.")


def fetch_traces(host: str, pub_key: str, sec_key: str,
                 since: datetime, limit: int = 100) -> list[dict]:
    """Fetch traces from LangFuse API."""
    traces = []
    page = 1

    with httpx.Client(timeout=30.0) as client:
        while len(traces) < limit:
            resp = client.get(
                f"{host}/api/public/traces",
                auth=(pub_key, sec_key),
                params={
                    "page": page,
                    "limit": min(50, limit - len(traces)),
                    "orderBy": "timestamp",
                    "orderDirection": "desc",
                },
            )

            if resp.status_code != 200:
                print(f"ERROR: LangFuse API returned {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                break

            data = resp.json()
            batch = data.get("data", [])
            if not batch:
                break

            for trace in batch:
                ts = trace.get("timestamp", "")
                if ts:
                    trace_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if trace_time < since:
                        return traces  # Past our window

                traces.append({
                    "id": trace.get("id"),
                    "name": trace.get("name"),
                    "timestamp": trace.get("timestamp"),
                    "input": trace.get("input"),
                    "output": trace.get("output"),
                    "metadata": trace.get("metadata", {}),
                    "tags": trace.get("tags", []),
                    "latency_ms": trace.get("latency"),
                    "total_cost": trace.get("totalCost"),
                    "model": trace.get("metadata", {}).get("model", ""),
                    "user_id": trace.get("userId"),
                    "session_id": trace.get("sessionId"),
                    "observations": trace.get("observations", []),
                })

            page += 1

    return traces


def extract_interactions(traces: list[dict]) -> list[dict]:
    """Extract structured interactions from raw traces."""
    interactions = []
    for trace in traces:
        inp = trace.get("input")
        out = trace.get("output")

        # Extract user message from input
        user_msg = ""
        if isinstance(inp, list):
            for m in inp:
                if isinstance(m, dict) and m.get("role") == "user":
                    user_msg = m.get("content", "")
        elif isinstance(inp, dict):
            user_msg = inp.get("content", "") or inp.get("prompt", "") or str(inp)
        elif isinstance(inp, str):
            user_msg = inp

        # Extract assistant response from output
        assistant_msg = ""
        if isinstance(out, dict):
            assistant_msg = out.get("content", "") or out.get("text", "") or str(out)
        elif isinstance(out, str):
            assistant_msg = out
        elif isinstance(out, list):
            for m in out:
                if isinstance(m, dict) and m.get("role") == "assistant":
                    assistant_msg = m.get("content", "")

        if user_msg and assistant_msg:
            interactions.append({
                "trace_id": trace["id"],
                "timestamp": trace["timestamp"],
                "model": trace.get("model", ""),
                "agent": trace.get("name", ""),
                "user_message": user_msg[:2000],
                "assistant_response": assistant_msg[:4000],
                "latency_ms": trace.get("latency_ms"),
                "tags": trace.get("tags", []),
            })

    return interactions


def main():
    parser = argparse.ArgumentParser(description="Export LangFuse traces for analysis")
    parser.add_argument("--since", default="24h", help="Time window (e.g., 24h, 7d, 30m)")
    parser.add_argument("--limit", type=int, default=200, help="Max traces to fetch")
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    parser.add_argument("--host", default=LANGFUSE_HOST)
    parser.add_argument("--raw", action="store_true", help="Output raw traces (not extracted)")
    args = parser.parse_args()

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        print(
            "ERROR: set ATHANOR_LANGFUSE_PUBLIC_KEY / ATHANOR_LANGFUSE_SECRET_KEY "
            "or LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY before exporting traces",
            file=sys.stderr,
        )
        sys.exit(1)

    since = datetime.now(timezone.utc) - parse_duration(args.since)

    print(f"Fetching traces since {since.isoformat()}...", file=sys.stderr)

    traces = fetch_traces(args.host, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
                          since, args.limit)

    print(f"Fetched {len(traces)} traces", file=sys.stderr)

    if args.raw:
        result = traces
    else:
        result = extract_interactions(traces)
        print(f"Extracted {len(result)} interactions", file=sys.stderr)

    output = json.dumps(result, indent=2, default=str)

    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
