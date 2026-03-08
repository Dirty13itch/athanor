#!/usr/bin/env python3
"""Score exported LangFuse interactions using local reasoning model.

Reads interaction JSON (from export-langfuse-traces.py), sends each to the
reasoning model for quality scoring, and outputs enriched JSON with scores.

Usage:
    python3 scripts/score-interactions.py --input /tmp/traces.json --output /tmp/scored.json
    python3 scripts/score-interactions.py --input /tmp/traces.json  # stdout
    cat /tmp/traces.json | python3 scripts/score-interactions.py    # stdin

Scores each interaction on:
    helpfulness (1-5), accuracy (1-5), conciseness (1-5), tool_usage (1-5 if applicable)
"""

import argparse
import asyncio
import json
import sys
import time

import httpx

LITELLM_URL = "http://192.168.1.203:4000/v1/chat/completions"
LITELLM_KEY = "sk-athanor-litellm-2026"
DEFAULT_MODEL = "reasoning"
DEFAULT_MAX_CONCURRENT = 5

SCORING_PROMPT = """You are a quality evaluator for an AI assistant system called Athanor.

Score this interaction on each dimension using integers 1-5:
- helpfulness: Did the assistant address what was asked? (1=completely missed, 5=nailed it)
- accuracy: Is the information correct and reliable? (1=wrong, 5=verified correct)
- conciseness: Right amount of detail — not too terse, not too verbose? (1=way off, 5=perfect length)
- tool_usage: If tools were used or should have been, were they used well? (1=misused/missed, 5=optimal). Set to null if no tools were relevant.

Respond with ONLY valid JSON, no markdown fences:
{{"helpfulness": N, "accuracy": N, "conciseness": N, "tool_usage": N_or_null, "rationale": "1-2 sentence explanation"}}

## Interaction

**User:** {user_message}

**Assistant:** {assistant_response}

**Agent:** {agent}
**Model:** {model}"""


async def score_one(
    client: httpx.AsyncClient,
    interaction: dict,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    model: str,
) -> dict:
    """Score a single interaction via LLM."""
    async with semaphore:
        prompt = SCORING_PROMPT.format(
            user_message=interaction.get("user_message", "")[:1500],
            assistant_response=interaction.get("assistant_response", "")[:3000],
            agent=interaction.get("agent", "unknown"),
            model=interaction.get("model", "unknown"),
        )

        try:
            resp = await client.post(
                LITELLM_URL,
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.1,
                },
                timeout=60.0,
            )

            if resp.status_code != 200:
                print(f"  [{index+1}/{total}] HTTP {resp.status_code} for {interaction.get('trace_id', '?')}", file=sys.stderr)
                return {**interaction, "scores": None, "scoring_error": f"HTTP {resp.status_code}"}

            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Strip markdown fences if model wraps anyway
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            scores = json.loads(content)
            rationale = scores.pop("rationale", "")

            print(f"  [{index+1}/{total}] {interaction.get('trace_id', '?')[:8]} -> "
                  f"h={scores.get('helpfulness')} a={scores.get('accuracy')} "
                  f"c={scores.get('conciseness')} t={scores.get('tool_usage')}",
                  file=sys.stderr)

            return {
                **interaction,
                "scores": {
                    "helpfulness": scores.get("helpfulness"),
                    "accuracy": scores.get("accuracy"),
                    "conciseness": scores.get("conciseness"),
                    "tool_usage": scores.get("tool_usage"),
                },
                "scoring_rationale": rationale,
            }

        except json.JSONDecodeError as e:
            print(f"  [{index+1}/{total}] JSON parse error for {interaction.get('trace_id', '?')}: {e}", file=sys.stderr)
            return {**interaction, "scores": None, "scoring_error": f"JSON parse: {e}"}
        except Exception as e:
            print(f"  [{index+1}/{total}] Error for {interaction.get('trace_id', '?')}: {e}", file=sys.stderr)
            return {**interaction, "scores": None, "scoring_error": str(e)}


async def score_all(interactions: list[dict], model: str, max_concurrent: int) -> list[dict]:
    """Score all interactions with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)
    total = len(interactions)

    async with httpx.AsyncClient() as client:
        tasks = [
            score_one(client, interaction, semaphore, i, total, model)
            for i, interaction in enumerate(interactions)
        ]
        return await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(
        description="Score LangFuse interactions using local reasoning model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 scripts/score-interactions.py --input /tmp/traces.json --output /tmp/scored.json
  python3 scripts/score-interactions.py --input /tmp/traces.json
  cat /tmp/traces.json | python3 scripts/score-interactions.py""",
    )
    parser.add_argument("--input", default="-", help="Input JSON file (- for stdin)")
    parser.add_argument("--output", default="-", help="Output JSON file (- for stdout)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"LiteLLM model alias (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-concurrent", type=int, default=DEFAULT_MAX_CONCURRENT,
                        help=f"Max parallel scoring requests (default: {DEFAULT_MAX_CONCURRENT})")
    args = parser.parse_args()

    # Read input
    if args.input == "-":
        raw = sys.stdin.read()
    else:
        with open(args.input) as f:
            raw = f.read()

    try:
        interactions = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(interactions, list):
        print("ERROR: Input must be a JSON array of interactions", file=sys.stderr)
        sys.exit(1)

    print(f"Scoring {len(interactions)} interactions (model={args.model}, "
          f"max_concurrent={args.max_concurrent})...", file=sys.stderr)
    start = time.time()

    scored = asyncio.run(score_all(interactions, args.model, args.max_concurrent))

    elapsed = time.time() - start
    scored_ok = sum(1 for s in scored if s.get("scores") is not None)
    print(f"Scored {scored_ok}/{len(scored)} interactions in {elapsed:.1f}s", file=sys.stderr)

    output = json.dumps(scored, indent=2, default=str)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
