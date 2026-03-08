#!/usr/bin/env python3
"""Identify failure patterns and improvement opportunities from scored interactions.

Reads scored JSON (from score-interactions.py), clusters failures by type,
detects recurring patterns, and outputs prioritized improvement suggestions.

Usage:
    python3 scripts/identify-failures.py --input /tmp/scored.json --output /tmp/failures.json
    python3 scripts/identify-failures.py --input /tmp/scored.json --threshold 3

Failure types:
    prompt_issue    — low helpfulness/conciseness, agent gave wrong framing
    routing_issue   — wrong agent handled the request
    knowledge_gap   — low accuracy, missing or wrong information
    tool_failure    — low tool_usage score, misused or missed tools
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


SCORE_THRESHOLD = 3  # Scores below this are flagged


def classify_failure(interaction: dict) -> list[str]:
    """Classify an interaction's failure types based on scores."""
    scores = interaction.get("scores")
    if not scores:
        return []

    failures = []

    helpfulness = scores.get("helpfulness")
    accuracy = scores.get("accuracy")
    conciseness = scores.get("conciseness")
    tool_usage = scores.get("tool_usage")

    if helpfulness is not None and helpfulness < SCORE_THRESHOLD:
        failures.append("prompt_issue")
    if conciseness is not None and conciseness < SCORE_THRESHOLD:
        failures.append("prompt_issue")
    if accuracy is not None and accuracy < SCORE_THRESHOLD:
        failures.append("knowledge_gap")
    if tool_usage is not None and tool_usage < SCORE_THRESHOLD:
        failures.append("tool_failure")

    # Routing heuristic: if helpfulness is low but accuracy is fine,
    # the request may have gone to the wrong agent
    if (helpfulness is not None and helpfulness < SCORE_THRESHOLD
            and accuracy is not None and accuracy >= SCORE_THRESHOLD):
        failures.append("routing_issue")

    return list(set(failures))


def compute_agent_trends(interactions: list[dict]) -> dict[str, dict]:
    """Compute per-agent quality trends."""
    agent_scores: dict[str, list[dict]] = defaultdict(list)

    for interaction in interactions:
        agent = interaction.get("agent", "unknown")
        scores = interaction.get("scores")
        if scores:
            agent_scores[agent].append({
                "timestamp": interaction.get("timestamp", ""),
                **scores,
            })

    trends = {}
    for agent, score_list in agent_scores.items():
        if len(score_list) < 2:
            continue

        # Sort by timestamp
        score_list.sort(key=lambda x: x.get("timestamp", ""))

        # Split into halves and compare averages
        mid = len(score_list) // 2
        first_half = score_list[:mid]
        second_half = score_list[mid:]

        def avg(items, key):
            vals = [s[key] for s in items if s.get(key) is not None]
            return sum(vals) / len(vals) if vals else None

        trend_data = {}
        for dim in ("helpfulness", "accuracy", "conciseness", "tool_usage"):
            first_avg = avg(first_half, dim)
            second_avg = avg(second_half, dim)
            if first_avg is not None and second_avg is not None:
                delta = second_avg - first_avg
                trend_data[dim] = {
                    "early_avg": round(first_avg, 2),
                    "recent_avg": round(second_avg, 2),
                    "delta": round(delta, 2),
                    "declining": delta < -0.3,
                }

        trends[agent] = {
            "total_interactions": len(score_list),
            "dimensions": trend_data,
            "declining": any(d.get("declining", False) for d in trend_data.values()),
        }

    return trends


def generate_suggestions(
    failure_clusters: dict[str, list[dict]],
    agent_trends: dict[str, dict],
) -> list[dict]:
    """Generate prioritized improvement suggestions."""
    suggestions = []
    priority = 0

    # Cluster-based suggestions
    for failure_type, items in sorted(
        failure_clusters.items(), key=lambda x: -len(x[1])
    ):
        if not items:
            continue

        priority += 1
        affected_agents = Counter(i.get("agent", "unknown") for i in items)
        top_agent = affected_agents.most_common(1)[0] if affected_agents else ("unknown", 0)

        if failure_type == "prompt_issue":
            suggestions.append({
                "priority": priority,
                "type": "prompt_issue",
                "title": f"Improve prompt for {top_agent[0]} ({len(items)} failures)",
                "description": (
                    f"{len(items)} interactions had low helpfulness or conciseness. "
                    f"Most affected agent: {top_agent[0]} ({top_agent[1]} occurrences). "
                    "Review system prompt for clarity, instruction specificity, "
                    "and output format guidance."
                ),
                "affected_agents": dict(affected_agents),
                "action": "review_prompt",
                "sample_trace_ids": [i.get("trace_id") for i in items[:5]],
            })

        elif failure_type == "knowledge_gap":
            suggestions.append({
                "priority": priority,
                "type": "knowledge_gap",
                "title": f"Address knowledge gaps ({len(items)} inaccurate responses)",
                "description": (
                    f"{len(items)} interactions had low accuracy scores. "
                    f"Most affected agent: {top_agent[0]}. "
                    "Consider adding RAG retrieval, updating knowledge base, "
                    "or improving context injection."
                ),
                "affected_agents": dict(affected_agents),
                "action": "improve_knowledge",
                "sample_trace_ids": [i.get("trace_id") for i in items[:5]],
            })

        elif failure_type == "tool_failure":
            suggestions.append({
                "priority": priority,
                "type": "tool_failure",
                "title": f"Fix tool usage patterns ({len(items)} failures)",
                "description": (
                    f"{len(items)} interactions had poor tool usage. "
                    f"Most affected agent: {top_agent[0]}. "
                    "Review tool descriptions, add examples to prompt, "
                    "or check for broken tool implementations."
                ),
                "affected_agents": dict(affected_agents),
                "action": "fix_tools",
                "sample_trace_ids": [i.get("trace_id") for i in items[:5]],
            })

        elif failure_type == "routing_issue":
            suggestions.append({
                "priority": priority,
                "type": "routing_issue",
                "title": f"Improve request routing ({len(items)} misrouted)",
                "description": (
                    f"{len(items)} interactions appear to have been routed to the wrong agent "
                    "(low helpfulness but acceptable accuracy). "
                    "Review routing classifier training data and decision boundaries."
                ),
                "affected_agents": dict(affected_agents),
                "action": "tune_routing",
                "sample_trace_ids": [i.get("trace_id") for i in items[:5]],
            })

    # Trend-based suggestions
    for agent, trend in agent_trends.items():
        if trend.get("declining"):
            priority += 1
            declining_dims = [
                dim for dim, data in trend.get("dimensions", {}).items()
                if data.get("declining")
            ]
            suggestions.append({
                "priority": priority,
                "type": "quality_regression",
                "title": f"Quality declining for {agent}",
                "description": (
                    f"Agent {agent} shows declining quality in: {', '.join(declining_dims)}. "
                    f"Based on {trend['total_interactions']} interactions. "
                    "May indicate prompt drift, model change, or workload shift."
                ),
                "affected_agents": {agent: trend["total_interactions"]},
                "action": "investigate_regression",
                "trend_data": trend["dimensions"],
            })

    return suggestions


def analyze(interactions: list[dict], threshold: int) -> dict[str, Any]:
    """Run full failure analysis."""
    global SCORE_THRESHOLD
    SCORE_THRESHOLD = threshold

    # Separate scored vs unscored
    scored = [i for i in interactions if i.get("scores") is not None]
    unscored = [i for i in interactions if i.get("scores") is None]

    if not scored:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_interactions": len(interactions),
            "scored_interactions": 0,
            "failure_clusters": {},
            "agent_trends": {},
            "improvement_suggestions": [],
            "summary": "No scored interactions to analyze.",
        }

    # Classify failures
    failure_clusters: dict[str, list[dict]] = defaultdict(list)
    low_scoring = []

    for interaction in scored:
        failures = classify_failure(interaction)
        if failures:
            low_scoring.append(interaction)
            for f_type in failures:
                failure_clusters[f_type].append({
                    "trace_id": interaction.get("trace_id"),
                    "agent": interaction.get("agent", "unknown"),
                    "timestamp": interaction.get("timestamp"),
                    "scores": interaction.get("scores"),
                    "user_message": interaction.get("user_message", "")[:200],
                    "scoring_rationale": interaction.get("scoring_rationale", ""),
                })

    # Agent trends
    agent_trends = compute_agent_trends(scored)

    # Suggestions
    suggestions = generate_suggestions(dict(failure_clusters), agent_trends)

    # Compute aggregate stats
    all_scores = {"helpfulness": [], "accuracy": [], "conciseness": [], "tool_usage": []}
    for interaction in scored:
        for dim in all_scores:
            val = interaction["scores"].get(dim)
            if val is not None:
                all_scores[dim].append(val)

    avg_scores = {}
    for dim, vals in all_scores.items():
        if vals:
            avg_scores[dim] = round(sum(vals) / len(vals), 2)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_interactions": len(interactions),
        "scored_interactions": len(scored),
        "unscored_interactions": len(unscored),
        "low_scoring_count": len(low_scoring),
        "threshold": threshold,
        "average_scores": avg_scores,
        "failure_clusters": {
            k: {"count": len(v), "items": v}
            for k, v in failure_clusters.items()
        },
        "agent_trends": agent_trends,
        "improvement_suggestions": suggestions,
        "summary": (
            f"{len(low_scoring)}/{len(scored)} interactions below threshold ({threshold}). "
            f"Top failure type: {max(failure_clusters, key=lambda k: len(failure_clusters[k])) if failure_clusters else 'none'}. "
            f"{len(suggestions)} improvement suggestions generated."
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Identify failure patterns in scored interactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 scripts/identify-failures.py --input /tmp/scored.json --output /tmp/failures.json
  python3 scripts/identify-failures.py --input /tmp/scored.json --threshold 2
  cat /tmp/scored.json | python3 scripts/identify-failures.py""",
    )
    parser.add_argument("--input", default="-", help="Scored JSON file (- for stdin)")
    parser.add_argument("--output", default="-", help="Output JSON file (- for stdout)")
    parser.add_argument("--threshold", type=int, default=3, help="Score threshold for flagging (default: 3)")
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
        print("ERROR: Input must be a JSON array of scored interactions", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {len(interactions)} interactions (threshold={args.threshold})...", file=sys.stderr)

    result = analyze(interactions, args.threshold)

    print(f"Found {result['low_scoring_count']} low-scoring interactions", file=sys.stderr)
    print(f"Generated {len(result['improvement_suggestions'])} suggestions", file=sys.stderr)

    output = json.dumps(result, indent=2, default=str)
    if args.output == "-":
        print(output)
    else:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
