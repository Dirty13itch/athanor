"""Owner Model — continuously maintained representation of who Shaun is.

Aggregates identity, domain interest, behavioral parameters, capacity state,
and recent activity from ~11 sources into a single JSON profile stored in
Redis. The intent synthesizer consumes this profile every pipeline cycle
to generate cross-domain strategic intents.

Full rebuild: daily at 4 AM.  Light refresh (capacity + activity): every cycle.
"""

import json
import logging
import os
import time

import httpx

from .config import settings

logger = logging.getLogger(__name__)

OWNER_PROFILE_KEY = "athanor:owner:profile"
OWNER_REACTIONS_KEY = "athanor:owner:reactions"
OWNER_SUPPRESS_KEY = "athanor:owner:suppress"  # domain suppress TTL keys
FULL_REBUILD_INTERVAL = 86400  # 24h

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
))))

# The Twelve Words — baseline behavioral parameters from VISION.md
TWELVE_WORDS = {
    "autotelic": {"meaning": "the activity is the reward", "category": "identity"},
    "zetetic": {"meaning": "the seeking never resolves", "category": "identity"},
    "dharma": {"meaning": "the path fits the nature", "category": "identity"},
    "kaizen": {"meaning": "continuous improvement as philosophy", "category": "method"},
    "phronesis": {"meaning": "wisdom about where to be rigorous", "category": "method"},
    "affordance_sensitivity": {"meaning": "seeing what something could become", "category": "method"},
    "meraki": {"meaning": "soul poured into the work", "category": "experience"},
    "sisu": {"meaning": "you don't quit", "category": "experience"},
    "jouissance": {"meaning": "the overwhelm that isn't unpleasant", "category": "experience"},
    "compressivist": {"meaning": "elegance is shorter truth", "category": "cognition"},
    "endogenous_attention": {"meaning": "the internal signal is loudest", "category": "cognition"},
    "tuftler": {"meaning": "the one who refines what already works", "category": "cognition"},
}


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def get_owner_profile() -> dict:
    """Return the current owner profile from Redis, or empty dict if none."""
    try:
        r = await _get_redis()
        raw = await r.get(OWNER_PROFILE_KEY)
        if raw:
            return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception as e:
        logger.debug("Owner profile load failed: %s", e)
    return {}


async def ensure_fresh(max_age: int = 7200) -> dict:
    """Ensure the owner profile exists and isn't stale. Returns the profile."""
    profile = await get_owner_profile()
    age = time.time() - profile.get("refreshed_at", 0)
    if not profile or age > FULL_REBUILD_INTERVAL:
        return await rebuild_full()
    if age > max_age:
        return await refresh_light(profile)
    return profile


async def rebuild_full() -> dict:
    """Full rebuild of the owner profile from all sources."""
    logger.info("Owner model: full rebuild starting")

    profile: dict = {
        "identity": {"twelve_words": {}},
        "domains": {},
        "behavioral_params": {},
        "capacity": {},
        "active_goals": [],
        "recent_interests": [],
        "refreshed_at": time.time(),
    }

    # 1. Twelve words — static baseline, adjusted by reactions
    tw_weights = await _load_reaction_weights()
    for word, meta in TWELVE_WORDS.items():
        base_score = 0.7
        adj = tw_weights.get(word, 0.0)
        profile["identity"]["twelve_words"][word] = {
            "score": max(0.1, min(1.0, base_score + adj)),
            "meaning": meta["meaning"],
            "category": meta["category"],
        }

    # 2. Domain interest — from projects + reactions + implicit feedback
    profile["domains"] = await _build_domain_state()

    # 3. Behavioral parameters — derived from twelve-word scores
    tw = profile["identity"]["twelve_words"]
    profile["behavioral_params"] = {
        "prefers_refinement_over_new": tw["tuftler"]["score"],
        "exploration_appetite": tw["zetetic"]["score"],
        "aesthetic_sensitivity": tw["meraki"]["score"],
        "process_over_outcome": tw["autotelic"]["score"],
        "intensity_seeking": tw["jouissance"]["score"],
        "self_directed_attention": tw["endogenous_attention"]["score"],
        "persistence": tw["sisu"]["score"],
        "elegance_drive": tw["compressivist"]["score"],
    }

    # 4. Capacity — GPU/queue/agent state
    profile["capacity"] = await _gather_capacity()

    # 5. Active goals
    try:
        from .goals import list_goals
        goals = await list_goals(active_only=True)
        profile["active_goals"] = [
            g.get("text", "") if isinstance(g, dict) else str(g)
            for g in goals[:10]
        ]
    except Exception as e:
        logger.debug("Owner model: goals fetch failed: %s", e)

    # 6. Recent interests from activity/preferences
    profile["recent_interests"] = await _gather_recent_interests()

    # 7. Pipeline outcomes
    try:
        from .work_pipeline import get_recent_outcomes
        outcomes = await get_recent_outcomes(20)
        profile["recent_outcomes_summary"] = {
            "count": len(outcomes),
            "avg_quality": round(sum(o.get("quality_score", 0) for o in outcomes) / max(len(outcomes), 1), 2),
            "agents_used": list(set(o.get("agent", "") for o in outcomes if o.get("agent"))),
        }
    except Exception as e:
        logger.debug("Owner model: outcomes fetch failed: %s", e)

    # Store
    r = await _get_redis()
    await r.set(OWNER_PROFILE_KEY, json.dumps(profile))
    logger.info("Owner model: full rebuild complete — %d domains, %d goals",
                len(profile["domains"]), len(profile["active_goals"]))
    return profile


async def refresh_light(profile: dict | None = None) -> dict:
    """Light refresh — updates capacity + activity only (no full source scan)."""
    if not profile:
        profile = await get_owner_profile()
    if not profile:
        return await rebuild_full()

    profile["capacity"] = await _gather_capacity()
    profile["recent_interests"] = await _gather_recent_interests()
    profile["refreshed_at"] = time.time()

    r = await _get_redis()
    await r.set(OWNER_PROFILE_KEY, json.dumps(profile))
    return profile


# --- Source gatherers ---

async def _build_domain_state() -> dict:
    """Build domain interest/momentum state from projects + reactions."""
    from .projects import get_project_registry

    domains = {}
    registry = get_project_registry()
    r = await _get_redis()

    # Map project IDs to domain names
    domain_map = {
        "eoq": "eoq",
        "media": "media",
        "athanor": "infrastructure",
        "ulrich-energy": "ulrich_energy",
        "kindred": "kindred",
    }

    # Extra domains not in project registry
    extra_domains = {
        "stash": {"status": "operational", "agents": ["stash-agent"]},
        "home": {"status": "operational", "agents": ["home-agent"]},
        "research": {"status": "active", "agents": ["research-agent"]},
        "personal_data": {"status": "idle", "agents": ["data-curator"]},
        "creative": {"status": "active", "agents": ["creative-agent"]},
    }

    for pid, proj in registry.items():
        dname = domain_map.get(pid, pid)
        # Compute momentum from recent tasks
        momentum = await _compute_momentum(pid, r)
        domains[dname] = {
            "momentum": momentum,
            "interest": 0.5,  # base, adjusted by reactions
            "status": proj.status,
            "gaps": [n.description[:80] for n in proj.needs[:3]],
            "agents": list(proj.agents),
        }

    for dname, info in extra_domains.items():
        if dname not in domains:
            momentum = await _compute_momentum(dname, r)
            domains[dname] = {
                "momentum": momentum,
                "interest": 0.4,
                "status": info["status"],
                "gaps": [],
                "agents": info["agents"],
            }

    # Apply reaction-based interest adjustments
    reactions = await _load_domain_reactions()
    for dname, adj in reactions.items():
        if dname in domains:
            domains[dname]["interest"] = max(0.1, min(1.0, domains[dname]["interest"] + adj))

    # Check for suppressed domains
    for dname in domains:
        suppress_key = f"{OWNER_SUPPRESS_KEY}:{dname}"
        if await r.exists(suppress_key):
            domains[dname]["suppressed"] = True

    # EoBQ always gets a higher baseline interest (it's the passion project)
    if "eoq" in domains:
        domains["eoq"]["interest"] = max(domains["eoq"]["interest"], 0.75)

    return domains


async def _compute_momentum(project_id: str, r) -> str:
    """Compute momentum from recent task activity for a project/domain."""
    try:
        last_ts = await r.hget("athanor:pipeline:project_last_task", project_id)
        if not last_ts:
            return "idle"
        ts = float(last_ts.decode() if isinstance(last_ts, bytes) else last_ts)
        age_h = (time.time() - ts) / 3600
        if age_h < 6:
            return "strong"
        if age_h < 24:
            return "active"
        if age_h < 72:
            return "cooling"
        return "idle"
    except Exception:
        return "unknown"


async def _gather_capacity() -> dict:
    """Gather current system capacity — GPU utilization, queue depth, idle agents."""
    capacity = {
        "gpu_idle_pct": 0,
        "cloud_models_available": 13,
        "queue_depth": 0,
        "agents_idle": [],
    }

    # Queue depth
    try:
        from .tasks import get_task_stats
        stats = await get_task_stats()
        capacity["queue_depth"] = stats.get("by_status", {}).get("pending", 0)
    except Exception:
        pass

    # Idle agents — agents with no pending/running tasks
    try:
        from .tasks import list_tasks
        pending = await list_tasks(status="pending", limit=50)
        running = await list_tasks(status="running", limit=50)
        busy_agents = set()
        for t in pending + running:
            if isinstance(t, dict):
                busy_agents.add(t.get("agent", ""))
        all_agents = [
            "general-assistant", "media-agent", "home-agent", "creative-agent",
            "research-agent", "knowledge-agent", "coding-agent", "stash-agent", "data-curator",
        ]
        capacity["agents_idle"] = [a for a in all_agents if a not in busy_agents]
    except Exception:
        pass

    # GPU utilization — try Prometheus
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.prometheus_url}/api/v1/query",
                params={"query": "avg(DCGM_FI_DEV_GPU_UTIL)"},
            )
            if resp.status_code == 200:
                result = resp.json().get("data", {}).get("result", [])
                if result:
                    avg_util = float(result[0]["value"][1])
                    capacity["gpu_idle_pct"] = round(100 - avg_util)
    except Exception:
        capacity["gpu_idle_pct"] = 85  # conservative estimate

    return capacity


async def _gather_recent_interests() -> list[str]:
    """Extract recent interests from activity and steering log."""
    interests = []
    try:
        r = await _get_redis()
        # From steering intents
        raw = await r.lrange("athanor:intents:steering_log", 0, 9)
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                entry = json.loads(text)
                interests.append(entry.get("text", "")[:100])
            except json.JSONDecodeError:
                if isinstance(text, str) and len(text) > 5:
                    interests.append(text[:100])
    except Exception:
        pass

    # Deduplicate
    seen = set()
    unique = []
    for i in interests:
        if i and i not in seen:
            seen.add(i)
            unique.append(i)
    return unique[:10]


# --- Reaction/feedback integration ---

async def _load_reaction_weights() -> dict[str, float]:
    """Load twelve-word weight adjustments from reaction history."""
    weights: dict[str, float] = {}
    try:
        r = await _get_redis()
        raw = await r.lrange(OWNER_REACTIONS_KEY, 0, 99)
        now = time.time()
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                reaction = json.loads(text)
                age_days = (now - reaction.get("ts", 0)) / 86400
                if age_days > 7:
                    continue  # Reactions decay after 7 days
                decay = max(0.3, 1.0 - (age_days / 7))
                tw = reaction.get("twelve_word", "")
                delta = reaction.get("delta", 0.0) * decay
                if tw:
                    weights[tw] = weights.get(tw, 0.0) + delta
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return weights


async def _load_domain_reactions() -> dict[str, float]:
    """Load domain interest adjustments from reactions."""
    adjustments: dict[str, float] = {}
    try:
        r = await _get_redis()
        raw = await r.lrange(OWNER_REACTIONS_KEY, 0, 99)
        now = time.time()
        for item in raw:
            text = item.decode() if isinstance(item, bytes) else item
            try:
                reaction = json.loads(text)
                age_days = (now - reaction.get("ts", 0)) / 86400
                if age_days > 7:
                    continue
                decay = max(0.3, 1.0 - (age_days / 7))
                domain = reaction.get("domain", "")
                delta = reaction.get("domain_delta", 0.0) * decay
                if domain:
                    adjustments[domain] = adjustments.get(domain, 0.0) + delta
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return adjustments


async def record_reaction(
    intent_id: str,
    reaction: str,
    intent_metadata: dict | None = None,
) -> dict:
    """Record a reaction to a synthesized intent. Adjusts twelve-word weights and domain interest.

    reaction: "more", "less", "love", "wrong"
    """
    meta = intent_metadata or {}
    twelve_word = meta.get("twelve_word", "")
    domain = meta.get("project", meta.get("domain", ""))

    # Map reaction to weight deltas
    tw_delta = {"more": 0.03, "less": -0.03, "love": 0.05, "wrong": -0.05}.get(reaction, 0)
    domain_delta = {"more": 0.1, "less": -0.1, "love": 0.15, "wrong": -0.15}.get(reaction, 0)

    entry = json.dumps({
        "intent_id": intent_id,
        "reaction": reaction,
        "twelve_word": twelve_word,
        "delta": tw_delta,
        "domain": domain,
        "domain_delta": domain_delta,
        "ts": time.time(),
    })

    r = await _get_redis()
    await r.lpush(OWNER_REACTIONS_KEY, entry)
    await r.ltrim(OWNER_REACTIONS_KEY, 0, 199)

    logger.info("Owner reaction recorded: %s on %s (tw=%s domain=%s)", reaction, intent_id, twelve_word, domain)
    return {"recorded": True, "intent_id": intent_id, "reaction": reaction}
