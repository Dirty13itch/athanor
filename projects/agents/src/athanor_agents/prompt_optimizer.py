"""
Nightly Prompt Optimization — Layer 4 of Athanor Operating System.

Triggered by scheduler at 22:00 each night:
1. Query LangFuse for today's traces
2. Identify bottom 10% by quality/latency/failure
3. Generate 2-3 prompt variants for up to 2 underperforming agents
4. Store variants in Redis for evaluation

Redis keys:
- athanor:improvement:nightly_results — list of last 30 optimization run results
- athanor:improvement:prompt_variants — hash: agent name -> JSON list of variants
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import settings
from .workspace import get_redis

logger = logging.getLogger(__name__)

# Agent prompt directory inside the container
PROMPT_DIR = Path("/opt/athanor/agents/src/athanor_agents/agents")

# Agents eligible for prompt optimization
OPTIMIZABLE_AGENTS = [
    "general-assistant",
    "research-agent",
    "media-agent",
    "home-agent",
    "creative-agent",
    "knowledge-agent",
    "coding-agent",
    "stash-agent",
    "data-curator",
]

# Maximum agents to optimize per nightly run
MAX_AGENTS_PER_NIGHT = 2

# Minimum traces needed before considering an agent underperforming
MIN_TRACES_THRESHOLD = 5

# Bottom percentile to flag as underperforming
BOTTOM_PERCENTILE = 0.10

# Improvement threshold to mark a variant as deployable
IMPROVEMENT_THRESHOLD = 0.05


async def _fetch_langfuse_traces(date_str: str) -> list[dict]:
    """Fetch today's traces from LangFuse API.

    Args:
        date_str: ISO date string (YYYY-MM-DD) to filter traces.

    Returns:
        List of trace dicts from LangFuse.
    """
    url = f"{settings.langfuse_url}/api/public/traces"
    params = {
        "fromTimestamp": f"{date_str}T00:00:00Z",
        "toTimestamp": f"{date_str}T23:59:59Z",
        "limit": 500,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
            logger.warning(
                "LangFuse traces fetch failed: status %d", resp.status_code
            )
            return []
        except Exception as e:
            logger.error("LangFuse traces fetch error: %s", e)
            return []


def _score_trace(trace: dict) -> float:
    """Score a trace on 0-1 scale based on quality signals.

    Scoring factors:
    - Success (no error): 0.4
    - Latency under 5s: 0.3 (linear scale, 0s=0.3, 5s+=0)
    - Has output (non-empty): 0.2
    - User feedback if present: 0.1
    """
    score = 0.0

    # Success factor
    status = trace.get("status") or trace.get("statusMessage", "")
    if status not in ("ERROR", "error"):
        score += 0.4

    # Latency factor — favor responses under 5 seconds
    latency_ms = trace.get("latency")
    if latency_ms is not None:
        latency_s = latency_ms / 1000.0
        if latency_s < 5.0:
            score += 0.3 * (1.0 - latency_s / 5.0)

    # Output presence
    output = trace.get("output")
    if output:
        score += 0.2

    # User feedback (scores from LangFuse)
    scores = trace.get("scores", [])
    if scores:
        avg_feedback = sum(s.get("value", 0) for s in scores) / len(scores)
        score += 0.1 * max(0.0, min(1.0, avg_feedback))

    return round(score, 4)


def _extract_agent_name(trace: dict) -> Optional[str]:
    """Extract the agent name from a LangFuse trace.

    Checks metadata.agent, tags, and trace name for agent identification.
    """
    # Check metadata
    metadata = trace.get("metadata") or {}
    if isinstance(metadata, dict):
        agent = metadata.get("agent")
        if agent and agent in OPTIMIZABLE_AGENTS:
            return agent

    # Check tags
    tags = trace.get("tags") or []
    for tag in tags:
        if tag in OPTIMIZABLE_AGENTS:
            return tag

    # Check trace name
    name = trace.get("name", "")
    for agent in OPTIMIZABLE_AGENTS:
        if agent in name:
            return agent

    return None


def _identify_underperformers(
    agent_scores: dict[str, list[float]],
) -> list[tuple[str, float]]:
    """Identify the bottom-performing agents by average score.

    Returns list of (agent_name, avg_score) for agents in the bottom percentile,
    limited to MAX_AGENTS_PER_NIGHT.
    """
    # Filter agents with enough traces
    eligible = {
        agent: scores
        for agent, scores in agent_scores.items()
        if len(scores) >= MIN_TRACES_THRESHOLD
    }

    if not eligible:
        return []

    # Calculate averages
    averages = {
        agent: sum(scores) / len(scores)
        for agent, scores in eligible.items()
    }

    # Sort by score ascending (worst first)
    sorted_agents = sorted(averages.items(), key=lambda x: x[1])

    # Take bottom percentile, but at least 1 if any exist
    cutoff_count = max(1, int(len(sorted_agents) * BOTTOM_PERCENTILE))
    underperformers = sorted_agents[:cutoff_count]

    # Cap at MAX_AGENTS_PER_NIGHT
    return underperformers[:MAX_AGENTS_PER_NIGHT]


async def _generate_prompt_variants(
    agent: str, avg_score: float, sample_traces: list[dict]
) -> list[dict]:
    """Generate 2-3 prompt variants for an underperforming agent.

    Uses the 'reasoning' model via LiteLLM to analyze failures and
    propose improved system prompts.

    Returns list of variant dicts with 'variant_id', 'description', 'prompt_delta'.
    """
    # Build context from sample traces
    failure_summaries = []
    for trace in sample_traces[:5]:
        summary = {
            "input": str(trace.get("input", ""))[:200],
            "output": str(trace.get("output", ""))[:200],
            "status": trace.get("status") or trace.get("statusMessage", "unknown"),
            "latency_ms": trace.get("latency"),
            "score": _score_trace(trace),
        }
        failure_summaries.append(summary)

    generation_prompt = f"""You are optimizing the system prompt for the '{agent}' agent in the Athanor AI system.

Current performance: average score {avg_score:.2f}/1.0 (bottom percentile).

Here are sample traces showing underperformance:
{json.dumps(failure_summaries, indent=2)}

Analyze the failure patterns and generate exactly 2 prompt improvement suggestions.
Each suggestion should be a specific, actionable change to the agent's system prompt.

Respond in this exact JSON format:
[
  {{
    "description": "Brief description of the change",
    "prompt_delta": "The specific text to add, modify, or emphasize in the system prompt",
    "rationale": "Why this should improve performance"
  }},
  {{
    "description": "Brief description of the change",
    "prompt_delta": "The specific text to add, modify, or emphasize in the system prompt",
    "rationale": "Why this should improve performance"
  }}
]

Focus on:
- Reducing errors and failures
- Improving response quality and relevance
- Reducing unnecessary latency (e.g., over-thinking for simple tasks)
- Better tool usage patterns

Respond with ONLY the JSON array, no other text."""

    url = f"{settings.litellm_url}/v1/chat/completions"
    headers = {}
    if settings.litellm_api_key:
        headers["Authorization"] = f"Bearer {settings.litellm_api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "model": "reasoning",
                    "messages": [{"role": "user", "content": generation_prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "extra_body": {
                        "metadata": {
                            "trace_name": "prompt_optimizer",
                            "tags": ["system", "optimization"],
                        },
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                },
            )

            if resp.status_code != 200:
                logger.warning(
                    "Variant generation failed for %s: status %d",
                    agent, resp.status_code,
                )
                return []

            content = resp.json()["choices"][0]["message"]["content"]

            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            variants_raw = json.loads(content)

            # Tag each variant
            variants = []
            timestamp = datetime.now(timezone.utc).isoformat()
            for i, v in enumerate(variants_raw[:3]):
                variants.append({
                    "variant_id": f"{agent}_{timestamp}_{i}",
                    "agent": agent,
                    "description": v.get("description", ""),
                    "prompt_delta": v.get("prompt_delta", ""),
                    "rationale": v.get("rationale", ""),
                    "created_at": timestamp,
                    "status": "pending",
                    "baseline_score": avg_score,
                })

            return variants

        except json.JSONDecodeError as e:
            logger.error("Failed to parse variant JSON for %s: %s", agent, e)
            return []
        except Exception as e:
            logger.error("Variant generation error for %s: %s", agent, e)
            return []


async def run_nightly_optimization() -> dict[str, Any]:
    """Main entry point for nightly prompt optimization.

    Triggered by scheduler at 22:00. Queries LangFuse for today's traces,
    identifies underperforming agents, generates prompt variants, and
    stores them in Redis for later evaluation.

    Returns:
        Dict with optimization results summary.
    """
    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")

    result: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "date": date_str,
        "traces_analyzed": 0,
        "agents_found": 0,
        "underperformers": [],
        "variants_generated": 0,
        "errors": [],
    }

    # 1. Fetch today's traces from LangFuse
    try:
        traces = await _fetch_langfuse_traces(date_str)
        result["traces_analyzed"] = len(traces)
    except Exception as e:
        result["errors"].append(f"trace_fetch: {e}")
        traces = []

    if not traces:
        logger.info("Nightly optimization: no traces found for %s", date_str)
        await _store_nightly_result(result)
        return result

    # 2. Group traces by agent and score them
    agent_scores: dict[str, list[float]] = {}
    agent_traces: dict[str, list[dict]] = {}

    for trace in traces:
        agent = _extract_agent_name(trace)
        if not agent:
            continue

        score = _score_trace(trace)
        agent_scores.setdefault(agent, []).append(score)
        agent_traces.setdefault(agent, []).append(trace)

    result["agents_found"] = len(agent_scores)

    # 3. Identify bottom performers
    underperformers = _identify_underperformers(agent_scores)
    result["underperformers"] = [
        {"agent": agent, "avg_score": round(avg, 4)}
        for agent, avg in underperformers
    ]

    if not underperformers:
        logger.info("Nightly optimization: no underperformers identified")
        await _store_nightly_result(result)
        return result

    # 4. Generate variants for each underperformer
    redis = await get_redis()

    for agent, avg_score in underperformers:
        try:
            # Get sample traces (worst first)
            samples = sorted(
                agent_traces.get(agent, []),
                key=lambda t: _score_trace(t),
            )

            variants = await _generate_prompt_variants(agent, avg_score, samples)

            if variants:
                # Store variants in Redis hash
                existing_raw = await redis.hget(
                    "athanor:improvement:prompt_variants", agent
                )
                existing = json.loads(existing_raw) if existing_raw else []
                existing.extend(variants)
                # Keep last 10 variants per agent
                existing = existing[-10:]
                await redis.hset(
                    "athanor:improvement:prompt_variants",
                    agent,
                    json.dumps(existing),
                )
                result["variants_generated"] += len(variants)
                logger.info(
                    "Generated %d variants for %s (avg score: %.2f)",
                    len(variants), agent, avg_score,
                )
        except Exception as e:
            error_msg = f"variant_gen_{agent}: {e}"
            result["errors"].append(error_msg)
            logger.error("Variant generation failed for %s: %s", agent, e)

    await _store_nightly_result(result)

    logger.info(
        "Nightly optimization complete: %d traces, %d agents, "
        "%d underperformers, %d variants generated",
        result["traces_analyzed"],
        result["agents_found"],
        len(result["underperformers"]),
        result["variants_generated"],
    )

    return result


async def evaluate_variants(agent: str) -> dict[str, Any]:
    """Evaluate stored prompt variants for an agent against baseline.

    Reads current prompt and variants from Redis, compares pass rates.
    If a variant improves by >5% with zero regression, marks it as deployable.

    Note: Actual eval integration (running promptfoo or similar) is future work.
    Currently logs comparison results for manual review.

    Args:
        agent: Agent name (e.g., 'general-assistant').

    Returns:
        Dict with evaluation results.
    """
    redis = await get_redis()
    result: dict[str, Any] = {
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "variants_evaluated": 0,
        "deployable": [],
        "rejected": [],
        "errors": [],
    }

    # Read variants from Redis
    variants_raw = await redis.hget("athanor:improvement:prompt_variants", agent)
    if not variants_raw:
        result["errors"].append("no_variants_found")
        return result

    try:
        variants = json.loads(variants_raw)
    except json.JSONDecodeError:
        result["errors"].append("invalid_variants_json")
        return result

    pending = [v for v in variants if v.get("status") == "pending"]
    if not pending:
        result["errors"].append("no_pending_variants")
        return result

    result["variants_evaluated"] = len(pending)

    for variant in pending:
        variant_id = variant.get("variant_id", "unknown")
        baseline_score = variant.get("baseline_score", 0.0)

        # Future: run actual eval here (promptfoo, test suite, etc.)
        # For now, log the variant for manual review and mark as evaluated.
        logger.info(
            "Variant %s for %s: baseline=%.4f, delta='%s'",
            variant_id,
            agent,
            baseline_score,
            variant.get("description", "")[:80],
        )

        # Mark as evaluated (no actual score yet — future work)
        variant["status"] = "evaluated"
        variant["evaluated_at"] = datetime.now(timezone.utc).isoformat()
        variant["eval_result"] = "manual_review_required"

        result["rejected"].append({
            "variant_id": variant_id,
            "reason": "auto_eval_not_yet_implemented",
            "description": variant.get("description", ""),
        })

    # Write updated variants back
    all_variants = json.loads(variants_raw)
    # Update statuses for evaluated variants
    evaluated_ids = {v["variant_id"] for v in pending}
    for v in all_variants:
        if v.get("variant_id") in evaluated_ids:
            matching = next(
                (p for p in pending if p["variant_id"] == v["variant_id"]),
                None,
            )
            if matching:
                v["status"] = matching["status"]
                v["evaluated_at"] = matching.get("evaluated_at")
                v["eval_result"] = matching.get("eval_result")

    await redis.hset(
        "athanor:improvement:prompt_variants",
        agent,
        json.dumps(all_variants),
    )

    return result


async def get_optimization_status() -> dict[str, Any]:
    """Get current prompt optimization status for dashboard visibility.

    Returns:
        Dict with optimization state: last run, pending variants, history.
    """
    redis = await get_redis()

    status: dict[str, Any] = {
        "last_run": None,
        "pending_variants": {},
        "total_variants": 0,
        "history_count": 0,
        "agent_summaries": {},
    }

    # Last nightly result
    try:
        results_raw = await redis.lindex("athanor:improvement:nightly_results", 0)
        if results_raw:
            status["last_run"] = json.loads(results_raw)
    except Exception as e:
        logger.debug("Failed to read last nightly result: %s", e)

    # History count
    try:
        status["history_count"] = await redis.llen(
            "athanor:improvement:nightly_results"
        )
    except Exception:
        pass

    # Per-agent variant summaries
    try:
        all_variants = await redis.hgetall("athanor:improvement:prompt_variants")
        for agent, variants_json in all_variants.items():
            variants = json.loads(variants_json)
            pending = [v for v in variants if v.get("status") == "pending"]
            evaluated = [v for v in variants if v.get("status") == "evaluated"]
            deployed = [v for v in variants if v.get("status") == "deployed"]

            status["agent_summaries"][agent] = {
                "total": len(variants),
                "pending": len(pending),
                "evaluated": len(evaluated),
                "deployed": len(deployed),
            }
            status["pending_variants"][agent] = len(pending)
            status["total_variants"] += len(variants)
    except Exception as e:
        logger.debug("Failed to read variant summaries: %s", e)

    return status


async def _store_nightly_result(result: dict[str, Any]) -> None:
    """Store a nightly optimization result in Redis."""
    try:
        redis = await get_redis()
        key = "athanor:improvement:nightly_results"
        await redis.lpush(key, json.dumps(result))
        await redis.ltrim(key, 0, 29)  # Keep last 30
    except Exception as e:
        logger.error("Failed to store nightly result: %s", e)
