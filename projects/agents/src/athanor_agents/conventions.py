"""Convention Library — persistent patterns agents learn over time.

Extends pattern detection (daily batch) with a permanent library of
learned behaviors. Conventions are:
1. Discovered from repeated patterns across multiple daily reports
2. Stored in Redis with confirmation status
3. Injected into agent context for self-improvement
4. Surfaced to Shaun for confirmation/rejection via workspace + dashboard

Lifecycle:
  Pattern detected (3+ occurrences) → Convention proposed → Shaun confirms/rejects
  Confirmed conventions → Injected into agent context permanently
  Rejected conventions → Archived, never re-proposed

Convention types:
  - "preference": User prefers X over Y (from feedback trends)
  - "behavior": Agent should/shouldn't do X (from failure/success patterns)
  - "schedule": Optimal timing for tasks (from throughput patterns)
  - "quality": Output quality rules (from explicit feedback)
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

CONVENTIONS_KEY = "athanor:conventions"
CONVENTIONS_PROPOSED_KEY = "athanor:conventions:proposed"
CONVENTIONS_REJECTED_KEY = "athanor:conventions:rejected"


@dataclass
class Convention:
    """A learned behavioral convention."""
    id: str = ""
    type: str = "behavior"  # preference, behavior, schedule, quality
    agent: str = ""  # Agent this applies to, or "global"
    description: str = ""  # Human-readable description
    rule: str = ""  # Machine-readable rule for context injection
    source: str = ""  # What pattern triggered this
    occurrences: int = 0  # How many times the pattern was seen
    status: str = "proposed"  # proposed, confirmed, rejected
    created_at: float = field(default_factory=time.time)
    confirmed_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Convention":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def propose_convention(
    convention_type: str,
    agent: str,
    description: str,
    rule: str,
    source: str,
    occurrences: int = 1,
) -> Convention:
    """Propose a new convention from detected patterns.

    Checks for duplicates before creating. Returns existing if found.
    """
    r = await _get_redis()

    # Check for existing convention with same rule
    existing = await get_conventions(status="proposed")
    existing.extend(await get_conventions(status="confirmed"))
    for c in existing:
        if c.rule == rule and c.agent == agent:
            # Update occurrence count
            c.occurrences = max(c.occurrences, occurrences)
            key = CONVENTIONS_KEY if c.status == "confirmed" else CONVENTIONS_PROPOSED_KEY
            await r.hset(key, c.id, json.dumps(c.to_dict()))
            return c

    # Check rejected — don't re-propose
    rejected = await get_conventions(status="rejected")
    for c in rejected:
        if c.rule == rule and c.agent == agent:
            return c

    # Create new proposal
    conv = Convention(
        id=f"conv-{int(time.time())}-{agent[:8]}",
        type=convention_type,
        agent=agent,
        description=description,
        rule=rule,
        source=source,
        occurrences=occurrences,
        status="proposed",
    )

    await r.hset(CONVENTIONS_PROPOSED_KEY, conv.id, json.dumps(conv.to_dict()))
    logger.info("Convention proposed: %s for %s — %s", conv.id, agent, description)

    # Post to workspace so Shaun sees it
    from .workspace import post_item
    await post_item(
        source_agent="system:conventions",
        content=f"New convention proposed for {agent}: {description}",
        priority="normal",
        ttl=3600,
        metadata={"convention_id": conv.id, "type": convention_type},
    )

    return conv


async def confirm_convention(convention_id: str) -> Convention | None:
    """Shaun confirms a proposed convention — moves to active."""
    r = await _get_redis()

    raw = await r.hget(CONVENTIONS_PROPOSED_KEY, convention_id)
    if not raw:
        return None

    conv = Convention.from_dict(json.loads(raw))
    conv.status = "confirmed"
    conv.confirmed_at = time.time()

    # Move from proposed to confirmed
    await r.hdel(CONVENTIONS_PROPOSED_KEY, convention_id)
    await r.hset(CONVENTIONS_KEY, convention_id, json.dumps(conv.to_dict()))

    logger.info("Convention confirmed: %s — %s", convention_id, conv.description)
    return conv


async def reject_convention(convention_id: str) -> Convention | None:
    """Shaun rejects a proposed convention — archived, never re-proposed."""
    r = await _get_redis()

    raw = await r.hget(CONVENTIONS_PROPOSED_KEY, convention_id)
    if not raw:
        return None

    conv = Convention.from_dict(json.loads(raw))
    conv.status = "rejected"

    # Move from proposed to rejected
    await r.hdel(CONVENTIONS_PROPOSED_KEY, convention_id)
    await r.hset(CONVENTIONS_REJECTED_KEY, convention_id, json.dumps(conv.to_dict()))

    logger.info("Convention rejected: %s — %s", convention_id, conv.description)
    return conv


async def get_conventions(
    status: str = "confirmed",
    agent: str | None = None,
) -> list[Convention]:
    """Get conventions filtered by status and optionally by agent."""
    r = await _get_redis()

    key_map = {
        "confirmed": CONVENTIONS_KEY,
        "proposed": CONVENTIONS_PROPOSED_KEY,
        "rejected": CONVENTIONS_REJECTED_KEY,
    }
    key = key_map.get(status, CONVENTIONS_KEY)

    try:
        raw = await r.hgetall(key)
        conventions = []
        for _, data in raw.items():
            conv = Convention.from_dict(json.loads(data))
            if agent and conv.agent != agent and conv.agent != "global":
                continue
            conventions.append(conv)
        conventions.sort(key=lambda c: c.created_at, reverse=True)
        return conventions
    except Exception as e:
        logger.warning("Failed to get conventions: %s", e)
        return []


async def get_agent_conventions(agent: str) -> list[str]:
    """Get confirmed convention rules for an agent.

    Used by context injection. Returns list of rule strings.
    """
    conventions = await get_conventions(status="confirmed", agent=agent)
    return [c.rule for c in conventions]


async def extract_conventions_from_patterns(report: dict) -> list[Convention]:
    """Analyze a pattern report and extract potential conventions.

    Called after daily pattern detection. Only proposes conventions
    when a pattern has been seen multiple times across different days.
    """
    if not report:
        return []

    proposed = []

    for pattern in report.get("patterns", []):
        ptype = pattern.get("type", "")
        agent = pattern.get("agent", "global")

        # Failure cluster → behavior convention
        if ptype == "failure_cluster" and pattern.get("count", 0) >= 5:
            errors = pattern.get("sample_errors", [])
            error_hint = errors[0][:80] if errors else "unknown errors"
            conv = await propose_convention(
                convention_type="behavior",
                agent=agent,
                description=f"{agent} repeatedly fails on similar tasks ({pattern['count']}x). "
                            f"Common error: {error_hint}",
                rule=f"Avoid tasks that have historically failed. "
                     f"Before attempting, verify tool access and input validity. "
                     f"Known failure pattern: {error_hint}",
                source=f"failure_cluster:{pattern['count']}",
                occurrences=pattern["count"],
            )
            proposed.append(conv)

        # Negative feedback → quality convention
        elif ptype == "negative_feedback_trend":
            down = pattern.get("thumbs_down", 0)
            up = pattern.get("thumbs_up", 0)
            conv = await propose_convention(
                convention_type="quality",
                agent=agent,
                description=f"{agent} received more negative feedback ({down}↓ vs {up}↑). "
                            f"Output quality needs improvement.",
                rule=f"Your recent outputs received negative feedback. "
                     f"Be more careful and thorough. Double-check results before responding. "
                     f"If uncertain, explain your limitations rather than guessing.",
                source=f"negative_feedback:{down}down/{up}up",
                occurrences=down + up,
            )
            proposed.append(conv)

        # High throughput agent with good success rate → schedule convention
        elif ptype == "task_throughput":
            success_rate = pattern.get("success_rate", 0)
            total = pattern.get("total", 0)
            if success_rate >= 0.95 and total >= 20:
                conv = await propose_convention(
                    convention_type="schedule",
                    agent="global",
                    description=f"Task engine is highly reliable ({success_rate:.0%} success rate, "
                                f"{total} tasks in 24h). Consider increasing concurrent task limit.",
                    rule=f"The task engine is running reliably at {success_rate:.0%}. "
                         f"Current throughput: {total} tasks/day.",
                    source=f"throughput:{total}tasks/{success_rate:.0%}",
                    occurrences=total,
                )
                proposed.append(conv)

    return proposed
