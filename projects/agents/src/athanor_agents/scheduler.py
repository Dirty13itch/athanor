"""Proactive Agent Scheduler — scheduled autonomous agent tasks.

Agents run on configurable schedules without external triggers.
Uses the Task Execution Engine (tasks.py) for actual execution.
Schedules are defined per-agent with interval, prompt, and priority.

The scheduler runs as a background asyncio loop, checking every 30s
whether any agent's schedule has elapsed. When it has, it submits
a task to the task queue.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

from .config import settings
from .constitution import is_peak_hours

logger = logging.getLogger(__name__)

SCHEDULER_KEY = "athanor:scheduler:last_run"
SCHEDULER_INTERVAL = 30.0  # Check schedules every 30s

_scheduler_task: asyncio.Task | None = None


# --- Schedule definitions ---
# Each entry: interval_seconds, prompt, priority
# Only agents with schedules are included.

DAILY_DIGEST_KEY = "athanor:scheduler:daily_digest"
PATTERN_DETECTION_KEY = "athanor:scheduler:pattern_detection"
CONSOLIDATION_KEY = "athanor:scheduler:consolidation"
ALERT_CHECK_KEY = "athanor:alerts:last_check"
WORKPLAN_MORNING_KEY = "athanor:scheduler:morning_plan"
WORKPLAN_REFILL_KEY = "athanor:workplan:last_refill_check"
CONSOLIDATION_HOUR = 3  # 3:00 AM local time
CONSOLIDATION_MINUTE = 0
DIGEST_HOUR = 6   # 6:55 AM local time
DIGEST_MINUTE = 55
PATTERN_HOUR = 5   # 5:00 AM local time
PATTERN_MINUTE = 0
WORKPLAN_HOUR = 7  # 7:00 AM local time
WORKPLAN_MINUTE = 0
ALERT_CHECK_INTERVAL = 300  # 5 minutes
WORKPLAN_REFILL_INTERVAL = 7200  # 2 hours
BENCHMARK_KEY = "athanor:scheduler:benchmark"
BENCHMARK_INTERVAL = 21600  # 6 hours
CACHE_CLEANUP_KEY = "athanor:scheduler:cache_cleanup"
CACHE_CLEANUP_INTERVAL = 3600  # 1 hour

# Quality cascades — chained multi-agent improvement loops
CREATIVE_CASCADE_KEY = "athanor:scheduler:creative_cascade"
CREATIVE_CASCADE_INTERVAL = 14400  # 4 hours
CODE_CASCADE_KEY = "athanor:scheduler:code_cascade"
CODE_CASCADE_INTERVAL = 21600  # 6 hours
IMPROVEMENT_CYCLE_KEY = "athanor:scheduler:improvement_cycle"
IMPROVEMENT_CYCLE_HOUR = 5
IMPROVEMENT_CYCLE_MINUTE = 30

# Owner model full rebuild (Phase 7) — runs at 04:00
OWNER_MODEL_KEY = "athanor:scheduler:owner_model"
OWNER_MODEL_HOUR = 4
OWNER_MODEL_MINUTE = 0

# Work pipeline (Phase 2) — runs every 2 hours
PIPELINE_KEY = "athanor:scheduler:pipeline"
PIPELINE_INTERVAL = 7200  # 2 hours in seconds

# Nightly prompt optimization (Phase 6) — runs at 22:00
NIGHTLY_OPTIMIZATION_KEY = "athanor:scheduler:nightly_optimization"
NIGHTLY_OPTIMIZATION_HOUR = 22
NIGHTLY_OPTIMIZATION_MINUTE = 0

# Nightly knowledge refresh (Phase 6) — runs at 00:00
KNOWLEDGE_REFRESH_KEY = "athanor:scheduler:knowledge_refresh"
KNOWLEDGE_REFRESH_HOUR = 0
KNOWLEDGE_REFRESH_MINUTE = 0

# Weekly DPO training (Phase 6) — Saturday 02:00 on FOUNDRY 4090
DPO_TRAINING_KEY = "athanor:scheduler:dpo_training"
DPO_TRAINING_HOUR = 2
DPO_TRAINING_MINUTE = 0
DPO_TRAINING_WEEKDAY = 5  # Saturday (Monday=0)

SCHEDULED_AGENT_WORKLOADS = {
    "general-assistant": "private_automation",
    "media-agent": "background_transform",
    "home-agent": "private_automation",
    "knowledge-agent": "private_automation",
    "research-agent": "research_synthesis",
    "creative-agent": "refusal_sensitive_creative",
    "coding-agent": "coding_implementation",
    "stash-agent": "private_automation",
}


def _load_autonomy_policy():
    try:
        from .model_governance import get_current_autonomy_policy

        return get_current_autonomy_policy()
    except Exception:
        return None


def _autonomy_allows_workload(
    workload_class: str,
    *,
    agent: str = "",
    loop_id: str = "",
) -> bool:
    policy = _load_autonomy_policy()
    if policy is None:
        return True

    phase_id = str(policy.phase_id or "unset")
    label = loop_id or agent or workload_class or "autonomy_loop"
    if not policy.is_active:
        logger.info(
            "Scheduler: skipping %s while autonomy activation is %s/%s",
            label,
            policy.phase_status,
            policy.activation_state,
        )
        return False

    if policy.unmet_prerequisite_ids:
        unmet_ids = ", ".join(policy.unmet_prerequisite_ids)
        logger.info(
            "Scheduler: skipping %s because autonomy phase %s has unmet prerequisites: %s",
            label,
            phase_id,
            unmet_ids,
        )
        return False

    enabled_agents = set(policy.enabled_agents)
    if agent and enabled_agents and agent not in enabled_agents:
        logger.info("Scheduler: skipping %s because agent %s is outside phase %s", label, agent, phase_id)
        return False

    allowed_workloads = set(policy.allowed_workload_classes)
    blocked_workloads = set(policy.blocked_workload_classes)
    if workload_class in blocked_workloads:
        logger.info("Scheduler: skipping %s because workload %s is blocked in %s", label, workload_class, phase_id)
        return False
    if allowed_workloads and workload_class not in allowed_workloads:
        logger.info(
            "Scheduler: skipping %s because workload %s is outside autonomy phase %s",
            label,
            workload_class,
            phase_id,
        )
        return False
    return True

AGENT_SCHEDULES = {
    "general-assistant": {
        "interval": 1800,  # 30 min
        "prompt": (
            "You are the general operations agent. Run a deep operational cycle:\n"
            "1. Check ALL service health endpoints. For any degraded service: diagnose WHY it's "
            "degraded (check logs, check upstream dependencies, check resource usage).\n"
            "2. Check GPU utilization across all nodes. If any GPU is at 0% with a model loaded, "
            "note it as wasted VRAM. If any GPU is >95% sustained, flag potential throttling.\n"
            "3. Check recent task failure rates. If any agent has >20% failure rate in the last hour, "
            "investigate the root cause (bad prompts? service down? timeout?).\n"
            "4. If everything is healthy: pick ONE improvement from this list and do it:\n"
            "   a. Check if any Redis keys have grown unexpectedly large\n"
            "   b. Check Qdrant collection sizes — flag any >100K points for compaction review\n"
            "   c. Review the last 10 completed tasks — which agent produced the best results?\n"
            "Write a brief but specific status report. Never say 'all healthy' without evidence."
        ),
        "priority": "normal",
        "enabled": True,
    },
    "media-agent": {
        "interval": 900,  # 15 min
        "prompt": (
            "You are the media operations agent. Run a deep media management cycle:\n"
            "1. Check all download clients (Sonarr, Radarr, SABnzbd, qBittorrent). "
            "Report active downloads with progress %, ETA, and any stalled items.\n"
            "2. Check Plex for current streams and recently added content.\n"
            "3. Look for media that needs attention:\n"
            "   a. Recently added content missing subtitles\n"
            "   b. Shows with missing episodes in monitored seasons\n"
            "   c. Movies in the wanted queue for >7 days (maybe availability changed)\n"
            "4. If nothing needs attention: check library stats and report total sizes, "
            "recent growth rate, and any quality upgrade opportunities.\n"
            "Be proactive — don't just report status, identify opportunities to improve the library."
        ),
        "priority": "low",
        "enabled": True,
    },
    "home-agent": {
        "interval": 600,  # 10 min (was 5, reduced load)
        "prompt": (
            "You are the home automation agent. Run a focused HA monitoring cycle:\n"
            "1. Check ALL entity states. Flag any in 'unavailable' or 'unknown' state.\n"
            "2. Check recently triggered automations — are they firing as expected?\n"
            "3. Look for optimization opportunities:\n"
            "   a. Lights left on in unoccupied rooms\n"
            "   b. HVAC running inefficiently (heating AND cooling same zone)\n"
            "   c. Devices with low battery (<20%)\n"
            "   d. Automations that haven't fired in >30 days (may be broken or obsolete)\n"
            "4. Check energy usage patterns if available.\n"
            "Report only findings that need attention. If everything is normal, say so in ONE line."
        ),
        "priority": "low",
        "enabled": True,
    },
    "knowledge-agent": {
        "interval": 3600,  # 1 hour
        "prompt": (
            "You are the knowledge management agent. Run a deep knowledge curation cycle:\n"
            "1. Check all Qdrant collections — report sizes, recent growth, any anomalies.\n"
            "2. Search for stale knowledge: find documents indexed >30 days ago that may need refreshing.\n"
            "3. Check for knowledge gaps: search for topics mentioned in recent tasks that have "
            "zero or very few matching documents in the knowledge base.\n"
            "4. Pick ONE of these improvement actions:\n"
            "   a. Find and index a new high-value document from /data/personal/ that hasn't been indexed\n"
            "   b. Cross-reference bookmarks against indexed docs — find bookmarks not yet in the KB\n"
            "   c. Search for duplicate or near-duplicate entries and flag them for consolidation\n"
            "   d. Check semantic search quality — run 3 test queries and evaluate result relevance\n"
            "Write a brief knowledge health report with specific numbers and any actions taken."
        ),
        "priority": "low",
        "enabled": True,
    },
    "research-agent": {
        "interval": 7200,  # 2 hours
        "prompt": (
            "You are the research intelligence agent. Run a deep research cycle:\n"
            "1. Check intelligence signals for high-relevance items (min_relevance=0.7).\n"
            "2. For any actionable signals: research the full context. New vLLM release? "
            "Read the changelog and assess impact on our stack. New model? Check benchmarks.\n"
            "3. Pick ONE proactive research task:\n"
            "   a. Search for newer/better quantizations of models we're running "
            "(Qwen3.5-27B, Qwen3-Coder-30B, Flux dev). Is there a higher quality option?\n"
            "   b. Research emerging video generation techniques — anything better than LTX 2.3 GGUF?\n"
            "   c. Check ComfyUI custom nodes — new PuLID improvements, better face injection, "
            "body pose control nodes we should install\n"
            "   d. Research Ren'Py or Godot integration patterns for AI-driven visual novels\n"
            "4. Write findings to your output. Include URLs, version numbers, and actionable conclusions.\n"
            "Never report 'no signals found' without having actually searched and investigated."
        ),
        "priority": "low",
        "enabled": True,
    },
    "creative-agent": {
        "interval": 7200,  # 2 hours
        "prompt": (
            "You are the creative production agent. Run a quality cascade cycle:\n"
            "1. Check ComfyUI health and queue status.\n"
            "2. Check gallery generation history — how many images exist per queen?\n"
            "3. Run a QUALITY CASCADE:\n"
            "   a. Find the queen with the FEWEST high-quality assets\n"
            "   b. Generate a new portrait using generate_with_likeness with her exact physical "
            "blueprint from EOQB_CHARACTERS. Use photorealistic prompts — exact replica of the "
            "performer, not stylized. Fit body, big fake round implants, studio lighting, 8K.\n"
            "   c. After generation completes, evaluate: is the face accurate? Is the body realistic? "
            "Are proportions correct? If not, regenerate with adjusted prompt (different seed, "
            "tweaked descriptors).\n"
            "4. If portrait quality is good, generate a SCENE for that queen using her character "
            "context from the master doc. Explicit content is expected and encouraged.\n"
            "5. Try generating a short LTX 2.3 video (generate_video_ltx) with a motion prompt "
            "based on the queen's personality. 512x320, 41 frames, 6 steps.\n"
            "6. Report what was generated, quality assessment, and what to prioritize next.\n"
            "Always push for higher quality. Never generate generic content."
        ),
        "priority": "normal",
        "enabled": True,
    },
    "coding-agent": {
        "interval": 10800,  # 3 hours
        "prompt": (
            "You are the coding quality agent. Run a deep code improvement cycle:\n"
            "Pick ONE of these tasks (rotate through them each cycle):\n\n"
            "OPTION A — Dashboard audit:\n"
            "1. Pick a dashboard subpage you haven't audited recently.\n"
            "2. Read the page's source code and identify any issues:\n"
            "   - Empty states that could show helpful content\n"
            "   - API calls that might be failing silently\n"
            "   - Missing error handling or loading states\n"
            "3. Write a detailed review to /output/code-review-{page}-{date}.md\n\n"
            "OPTION B — Agent server improvement:\n"
            "1. Pick a Python file in the agents codebase\n"
            "2. Check for: missing type hints, unused imports, error handling gaps, "
            "logging that could be more informative\n"
            "3. Write specific improvement suggestions to /output/code-quality-{file}-{date}.md\n\n"
            "OPTION C — Configuration drift check:\n"
            "1. Read docker-compose files and compare against what's actually running\n"
            "2. Check for port mismatches, stale environment variables, or missing volumes\n"
            "3. Document any drift found in /output/drift-report-{date}.md\n\n"
            "Always produce a written artifact. Never just say 'everything looks good'."
        ),
        "priority": "low",
        "enabled": True,
    },
    "stash-agent": {
        "interval": 14400,  # 4 hours
        "prompt": (
            "You are the Stash media management agent. Run a deep organization cycle:\n"
            "1. Get library stats — total scenes, performers, studios, tags.\n"
            "2. Find unorganized content:\n"
            "   a. Scenes with 0 tags (need classification)\n"
            "   b. Scenes with 0 performers (need identification)\n"
            "   c. Performers without profile images\n"
            "   d. Duplicate scenes (check by title similarity or phash)\n"
            "3. For untagged scenes: use available metadata (filename, studio, path) to suggest tags. "
            "Apply tags if confidence is high, queue for review if uncertain.\n"
            "4. Check for scenes that could be auto-tagged based on studio or series patterns.\n"
            "5. Report: X scenes organized, Y performers identified, Z items queued for review.\n"
            "Be thorough. The goal is zero unorganized content."
        ),
        "priority": "low",
        "enabled": True,
    },
    "data-curator": {
        "interval": 14400,  # 4 hours
        "prompt": (
            "You are the personal data curator. Run a deep data indexing cycle:\n"
            "1. Check scan status — what directories have been scanned, when was the last scan?\n"
            "2. Scan for NEW files since the last scan. Prioritize:\n"
            "   a. Energy audit reports (HERS ratings, REScheck, energy models)\n"
            "   b. AI research docs and notes\n"
            "   c. Financial documents\n"
            "   d. Personal documents and records\n"
            "3. For each new file found: parse, extract key metadata, generate embeddings, "
            "and index into the appropriate Qdrant collection.\n"
            "4. Check data quality: search for entries with missing metadata, broken file paths, "
            "or suspiciously low embedding confidence scores.\n"
            "5. Report: X new files indexed, Y files updated, Z quality issues found.\n"
            "The goal is a complete, searchable personal knowledge base."
        ),
        "priority": "low",
        "enabled": True,
    },
}


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def _get_last_run(agent: str) -> float:
    """Get the last scheduled run timestamp for an agent."""
    try:
        r = await _get_redis()
        ts = await r.hget(SCHEDULER_KEY, agent)
        return float(ts) if ts else 0.0
    except Exception:
        return 0.0


async def _set_last_run(agent: str, timestamp: float):
    """Record the last scheduled run timestamp."""
    try:
        r = await _get_redis()
        await r.hset(SCHEDULER_KEY, agent, str(timestamp))
    except Exception as e:
        logger.warning("Failed to set last run for %s: %s", agent, e)


async def _check_daily_digest():
    """Check if it's time to run the daily digest (6:55 AM local)."""
    from .goals import generate_digest_prompt

    if not _autonomy_allows_workload(
        "briefing_digest",
        agent="general-assistant",
        loop_id="daily_digest",
    ):
        return

    now = datetime.now()
    if now.hour != DIGEST_HOUR or now.minute != DIGEST_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(DAILY_DIGEST_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: generating daily digest")
    try:
        prompt = await generate_digest_prompt()
        from .tasks import submit_governed_task

        submission = await submit_governed_task(
            agent="general-assistant",
            prompt=prompt,
            priority="normal",
            metadata={
                "source": "daily_digest",
                "date": now.strftime("%Y-%m-%d"),
                "task_class": "briefing_digest",
            },
            source="scheduler",
        )
        task = submission.task
        r = await _get_redis()
        await r.set(DAILY_DIGEST_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Daily digest submitted for %s", now.strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning("Scheduler: failed to submit daily digest: %s", e)


async def _check_consolidation():
    """Check if it's time to run memory consolidation (3:00 AM local)."""
    from .consolidation import run_consolidation

    if not _autonomy_allows_workload("private_automation", loop_id="consolidation"):
        return

    now = datetime.now()
    if now.hour != CONSOLIDATION_HOUR or now.minute != CONSOLIDATION_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(CONSOLIDATION_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running memory consolidation")
    try:
        results = await run_consolidation()
        r = await _get_redis()
        await r.set(CONSOLIDATION_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Memory consolidation completed: %d points deleted, %d errors",
            results.get("total_deleted", 0),
            len(results.get("errors", [])),
        )
    except Exception as e:
        logger.warning("Scheduler: memory consolidation failed: %s", e)


async def _check_pattern_detection():
    """Check if it's time to run daily pattern detection (5:00 AM local)."""
    from .patterns import run_pattern_detection

    if not _autonomy_allows_workload("private_automation", loop_id="pattern_detection"):
        return

    now = datetime.now()
    if now.hour != PATTERN_HOUR or now.minute != PATTERN_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(PATTERN_DETECTION_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running pattern detection")
    try:
        report = await run_pattern_detection()
        r = await _get_redis()
        await r.set(PATTERN_DETECTION_KEY, now.strftime("%Y-%m-%d"))

        pattern_count = len(report.get("patterns", []))
        rec_count = len(report.get("recommendations", []))
        logger.info(
            "Pattern detection completed: %d patterns, %d recommendations",
            pattern_count, rec_count,
        )
    except Exception as e:
        logger.warning("Scheduler: pattern detection failed: %s", e)

    # Apply trust → autonomy threshold adjustments after pattern detection
    try:
        from .goals import apply_trust_adjustments
        adj_result = await apply_trust_adjustments()
        logger.info(
            "Trust adjustments applied: %d agents updated",
            adj_result.get("agent_count", 0),
        )
    except Exception as e:
        logger.warning("Scheduler: trust adjustment failed: %s", e)


async def _check_morning_plan():
    """Check if it's time to run the morning work plan (7:00 AM local)."""
    from .workplanner import generate_work_plan

    if not _autonomy_allows_workload("workplan_generation", loop_id="morning_plan"):
        return

    now = datetime.now()
    if now.hour != WORKPLAN_HOUR or now.minute != WORKPLAN_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(WORKPLAN_MORNING_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return  # Already ran today
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: generating morning work plan")
    try:
        plan = await generate_work_plan(
            focus="morning planning — review all active projects, prioritize highest-impact unblocked work",
            autonomy_managed=True,
        )
        r = await _get_redis()
        await r.set(WORKPLAN_MORNING_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Morning work plan generated: %d tasks (plan_id=%s)",
            plan.get("task_count", 0),
            plan.get("plan_id", "?"),
        )
    except Exception as e:
        logger.warning("Scheduler: morning work plan failed: %s", e)


async def _check_workplan_refill():
    """Check if the task queue needs refilling (every 2 hours)."""
    from .workplanner import should_refill, generate_work_plan

    if not _autonomy_allows_workload("workplan_generation", loop_id="workplan_refill"):
        return

    try:
        r = await _get_redis()
        last_check = await r.get(WORKPLAN_REFILL_KEY)
        if last_check:
            ts = float(last_check.decode() if isinstance(last_check, bytes) else last_check)
            if time.time() - ts < WORKPLAN_REFILL_INTERVAL:
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    try:
        if not await should_refill():
            # Still update the check timestamp so we don't re-check too often
            r = await _get_redis()
            await r.set(WORKPLAN_REFILL_KEY, str(time.time()))
            return

        logger.info("Scheduler: task queue low, generating refill work plan")
        plan = await generate_work_plan(
            focus="queue refill — pick up where we left off",
            autonomy_managed=True,
        )
        r = await _get_redis()
        await r.set(WORKPLAN_REFILL_KEY, str(time.time()))
        logger.info(
            "Refill work plan generated: %d tasks (plan_id=%s)",
            plan.get("task_count", 0),
            plan.get("plan_id", "?"),
        )
    except Exception as e:
        logger.warning("Scheduler: work plan refill failed: %s", e)


async def _check_alerts():
    """Check Prometheus alerts every 5 minutes."""
    from .alerts import check_prometheus_alerts

    if not _autonomy_allows_workload("private_automation", loop_id="alerts"):
        return

    try:
        r = await _get_redis()
        last_check = await r.get(ALERT_CHECK_KEY)
        if last_check:
            ts = float(last_check.decode() if isinstance(last_check, bytes) else last_check)
            if time.time() - ts < ALERT_CHECK_INTERVAL:
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    try:
        result = await check_prometheus_alerts()
        r = await _get_redis()
        await r.set(ALERT_CHECK_KEY, str(time.time()))
        if result.get("new", 0) > 0:
            logger.info(
                "Alert check: %d active, %d new",
                result["active"],
                result["new"],
            )
    except Exception as e:
        logger.warning("Alert check failed: %s", e)


async def _check_research_jobs():
    """Check for autonomous research jobs that need to run."""
    if not _autonomy_allows_workload(
        "research_synthesis",
        agent="research-agent",
        loop_id="research_scheduler",
    ):
        return

    try:
        from .research_jobs import check_scheduled_jobs

        triggered = await check_scheduled_jobs(autonomy_managed=True)
        if triggered > 0:
            logger.info("Scheduler: triggered %d research job(s)", triggered)
    except Exception as e:
        logger.warning("Scheduler: research job check failed: %s", e)


async def _check_benchmarks():
    """Run self-improvement benchmarks every 6 hours."""
    if not _autonomy_allows_workload("judge_verification", loop_id="benchmarks"):
        return

    try:
        r = await _get_redis()
        last = await r.get(BENCHMARK_KEY)
        if last:
            ts = float(last.decode() if isinstance(last, bytes) else last)
            if time.time() - ts < BENCHMARK_INTERVAL:
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    try:
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_benchmark_suite()
        r = await _get_redis()
        await r.set(BENCHMARK_KEY, str(time.time()))

        passed = result.get("passed", 0)
        total = result.get("total", 0)
        logger.info(
            "Self-improvement benchmarks: %d/%d passed (%.0f%%)",
            passed, total, result.get("pass_rate", 0) * 100,
        )

        # Check for regressions
        for bid, comp in result.get("comparison", {}).items():
            if comp.get("regressed"):
                logger.warning(
                    "REGRESSION detected: %s (%.1f → %.1f)",
                    bid, comp.get("baseline", 0), comp.get("new", 0),
                )
    except Exception as e:
        logger.warning("Benchmark run failed: %s", e)


async def _check_owner_model():
    """Check if it's time to run the owner model full rebuild (4:00 AM local)."""
    from .owner_model import rebuild_full

    if not _autonomy_allows_workload("background_transform", loop_id="owner_model"):
        return

    now = datetime.now()
    if now.hour != OWNER_MODEL_HOUR or now.minute != OWNER_MODEL_MINUTE:
        return

    try:
        r = await _get_redis()
        last_date = await r.get(OWNER_MODEL_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running owner model full rebuild")
    try:
        profile = await rebuild_full()
        r = await _get_redis()
        await r.set(OWNER_MODEL_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Owner model rebuilt: %d domains, %d goals",
            len(profile.get("domains", {})),
            len(profile.get("active_goals", [])),
        )
    except Exception as e:
        logger.warning("Scheduler: owner model rebuild failed: %s", e)


async def _check_improvement_cycle():
    """Run the self-improvement cycle at 5:30 AM (after pattern detection at 5:00 AM).

    This is the self-feeding loop: benchmarks → read patterns → generate proposals.
    """
    from .self_improvement import get_improvement_engine

    if not _autonomy_allows_workload("background_transform", loop_id="improvement_cycle"):
        return

    now = datetime.now()
    if now.hour != IMPROVEMENT_CYCLE_HOUR or now.minute != IMPROVEMENT_CYCLE_MINUTE:
        return

    # Check if already run today
    try:
        r = await _get_redis()
        last_date = await r.get(IMPROVEMENT_CYCLE_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running self-improvement cycle")
    try:
        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_improvement_cycle()
        r = await _get_redis()
        await r.set(IMPROVEMENT_CYCLE_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Self-improvement cycle: %d proposals generated, %d patterns consumed",
            result.get("proposals_generated", 0),
            result.get("patterns_consumed", 0),
        )
    except Exception as e:
        logger.warning("Scheduler: improvement cycle failed: %s", e)


async def _check_cache_cleanup():
    """Clean expired semantic cache entries every hour."""
    if not _autonomy_allows_workload("private_automation", loop_id="cache_cleanup"):
        return

    try:
        r = await _get_redis()
        last = await r.get(CACHE_CLEANUP_KEY)
        if last:
            ts = float(last.decode() if isinstance(last, bytes) else last)
            if time.time() - ts < CACHE_CLEANUP_INTERVAL:
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    try:
        from .semantic_cache import get_semantic_cache

        cache = get_semantic_cache()
        deleted = await cache.cleanup_expired()
        r = await _get_redis()
        await r.set(CACHE_CLEANUP_KEY, str(time.time()))
        if deleted > 0:
            logger.info("Semantic cache cleanup: %d expired entries removed", deleted)
    except Exception as e:
        logger.warning("Cache cleanup failed: %s", e)


async def _check_work_pipeline():
    """Check if it's time to run the work pipeline (every 2 hours)."""
    from .work_pipeline import PIPELINE_CYCLE_TIMEOUT_SECONDS, run_pipeline_cycle

    if not _autonomy_allows_workload("workplan_generation", loop_id="work_pipeline"):
        return

    # Interval-based: check if enough time has passed since last run
    try:
        r = await _get_redis()
        last_run = await r.get(PIPELINE_KEY)
        if last_run:
            last_ts = float(last_run.decode() if isinstance(last_run, bytes) else last_run)
            if time.time() - last_ts < PIPELINE_INTERVAL:
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running work pipeline cycle (interval=%ds)", PIPELINE_INTERVAL)
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            run_pipeline_cycle(),
            timeout=PIPELINE_CYCLE_TIMEOUT_SECONDS,
        )
        r = await _get_redis()
        await r.set(PIPELINE_KEY, str(time.time()))
        logger.info(
            "Work pipeline cycle: mined=%d new=%d plans=%d tasks=%d duration_s=%.1f",
            result.intents_mined, result.intents_new,
            result.plans_created, result.tasks_submitted,
            time.monotonic() - started,
        )
        # Refresh the auto-digest after each pipeline cycle
        try:
            from .routes.digests import _generate_digest_from_tasks
            digest = await _generate_digest_from_tasks(r)
            if digest.get("task_count", 0) > 0:
                import json as _json
                await r.lpush("athanor:digests", _json.dumps(digest))
                await r.ltrim("athanor:digests", 0, 29)
                logger.info("Auto-digest stored: %d tasks, %d completed", digest["task_count"], digest["completed_count"])
        except Exception as de:
            logger.debug("Auto-digest generation failed: %s", de)
    except asyncio.TimeoutError:
        logger.warning(
            "Scheduler: work pipeline cycle timed out after %ds",
            PIPELINE_CYCLE_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.warning(
            "Scheduler: work pipeline cycle failed (%s): %s",
            type(e).__name__,
            e,
        )


async def _check_nightly_optimization():
    """Check if it's time to run nightly prompt optimization (22:00 local)."""
    from .prompt_optimizer import run_nightly_optimization

    if not _autonomy_allows_workload("background_transform", loop_id="nightly_optimization"):
        return

    now = datetime.now()
    if now.hour != NIGHTLY_OPTIMIZATION_HOUR or now.minute != NIGHTLY_OPTIMIZATION_MINUTE:
        return

    try:
        r = await _get_redis()
        last_date = await r.get(NIGHTLY_OPTIMIZATION_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running nightly prompt optimization")
    try:
        result = await run_nightly_optimization()
        r = await _get_redis()
        await r.set(NIGHTLY_OPTIMIZATION_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Nightly optimization: %d traces, %d underperformers, %d variants",
            result.get("traces_analyzed", 0),
            len(result.get("underperformers", [])),
            result.get("variants_generated", 0),
        )
    except Exception as e:
        logger.warning("Scheduler: nightly optimization failed: %s", e)


async def _check_knowledge_refresh():
    """Check if it's time to run nightly knowledge refresh (00:00 local)."""
    from .knowledge_refresh import run_knowledge_refresh

    if not _autonomy_allows_workload("private_automation", loop_id="knowledge_refresh"):
        return

    now = datetime.now()
    if now.hour != KNOWLEDGE_REFRESH_HOUR or now.minute != KNOWLEDGE_REFRESH_MINUTE:
        return

    try:
        r = await _get_redis()
        last_date = await r.get(KNOWLEDGE_REFRESH_KEY)
        if last_date:
            last_str = last_date.decode() if isinstance(last_date, bytes) else last_date
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: running nightly knowledge refresh")
    try:
        result = await run_knowledge_refresh()
        r = await _get_redis()
        await r.set(KNOWLEDGE_REFRESH_KEY, now.strftime("%Y-%m-%d"))
        logger.info(
            "Knowledge refresh: %d found, %d refreshed, %d failed",
            result.get("docs_found", 0),
            result.get("docs_refreshed", 0),
            result.get("docs_failed", 0),
        )
    except Exception as e:
        logger.warning("Scheduler: knowledge refresh failed: %s", e)


async def _check_weekly_dpo_training():
    """Check if it's time to run weekly DPO training (Saturday 02:00, FOUNDRY 4090).

    Collects preference pairs from the week's feedback (thumbs + judge scores),
    generates a DPO training dataset, and logs a training task.
    Actual LoRA fine-tuning requires stopping vllm-coder — this creates the
    dataset and submits a task for the coding-agent to orchestrate the training.
    """
    if not _autonomy_allows_workload("background_transform", loop_id="weekly_dpo_training"):
        return

    now = datetime.now()
    if now.weekday() != DPO_TRAINING_WEEKDAY:
        return
    if now.hour != DPO_TRAINING_HOUR or now.minute != DPO_TRAINING_MINUTE:
        return

    try:
        r = await _get_redis()
        last_run = await r.get(DPO_TRAINING_KEY)
        if last_run:
            last_str = last_run.decode() if isinstance(last_run, bytes) else last_run
            if last_str == now.strftime("%Y-%m-%d"):
                return
    except Exception as e:
        logger.debug("Scheduler Redis check fallback: %s", e)

    logger.info("Scheduler: collecting DPO training data for weekly fine-tune")
    try:
        # Collect preference pairs from this week's task outcomes
        r = await _get_redis()
        outcomes_raw = await r.lrange("athanor:pipeline:outcomes", 0, -1)
        if not outcomes_raw:
            logger.info("Scheduler: no outcomes for DPO training, skipping")
            await r.set(DPO_TRAINING_KEY, now.strftime("%Y-%m-%d"))
            return

        pairs = []
        for raw in outcomes_raw:
            try:
                outcome = json.loads(raw if isinstance(raw, str) else raw.decode())
                score = outcome.get("quality_score", 0.5)
                prompt = outcome.get("prompt", "")
                output = outcome.get("output_summary", "")
                if prompt and output and score != 0.5:
                    pairs.append({
                        "prompt": prompt[:2000],
                        "output": output[:2000],
                        "score": score,
                    })
            except (json.JSONDecodeError, AttributeError):
                continue

        if len(pairs) < 10:
            logger.info("Scheduler: only %d DPO pairs (need 10+), skipping", len(pairs))
            await r.set(DPO_TRAINING_KEY, now.strftime("%Y-%m-%d"))
            return

        # Store dataset for training
        dataset_key = f"athanor:dpo:dataset:{now.strftime('%Y-%m-%d')}"
        await r.set(dataset_key, json.dumps(pairs), ex=604800)  # 7 day TTL
        await r.set(DPO_TRAINING_KEY, now.strftime("%Y-%m-%d"))

        logger.info(
            "DPO training dataset ready: %d pairs stored at %s",
            len(pairs), dataset_key,
        )

        # Submit a governed coding task so phase gates can hold this background transform
        from .tasks import submit_governed_task
        await submit_governed_task(
            agent="coding-agent",
            prompt=(
                f"Weekly DPO training dataset is ready at Redis key '{dataset_key}' "
                f"with {len(pairs)} preference pairs. "
                "To run LoRA fine-tuning: 1) Stop vllm-coder container on FOUNDRY, "
                "2) Run DPO training on FOUNDRY 4090, "
                "3) Evaluate against promptfoo baseline, "
                "4) If improved, deploy as new worker model on WORKSHOP, "
                "5) Restart vllm-coder. "
                "Report dataset stats and readiness status."
            ),
            priority="low",
            metadata={
                "source": "dpo_training",
                "pairs": len(pairs),
                "date": now.strftime("%Y-%m-%d"),
                "task_class": "background_transform",
                "requires_runtime_mutation": True,
            },
            source="scheduler",
        )
    except Exception as e:
        logger.warning("Scheduler: DPO training data collection failed: %s", e)


async def _check_creative_cascade():
    """Run creative quality cascade every CREATIVE_CASCADE_INTERVAL seconds."""
    if not _autonomy_allows_workload(
        "refusal_sensitive_creative",
        agent="creative-agent",
        loop_id="creative_cascade",
    ):
        return

    try:
        r = await _get_redis()
        last = await r.get(CREATIVE_CASCADE_KEY)
        last_ts = float(last) if last else 0.0
        if time.time() - last_ts < CREATIVE_CASCADE_INTERVAL:
            return

        logger.info("Scheduler: starting creative quality cascade")
        from .cascade import CASCADE_TIMEOUT, run_creative_cascade
        result = await asyncio.wait_for(
            run_creative_cascade(autonomy_managed=True),
            timeout=CASCADE_TIMEOUT,
        )
        await r.set(CREATIVE_CASCADE_KEY, str(time.time()))
        logger.info(
            "Creative cascade completed: %d loops, quality=%.2f",
            result.get("total_loops", 0), result.get("final_quality", 0),
        )
    except asyncio.TimeoutError:
        logger.warning("Creative cascade timed out after %ds", CASCADE_TIMEOUT)
    except Exception as e:
        logger.warning("Creative cascade failed: %s", e)


async def _check_code_cascade():
    """Run code quality cascade every CODE_CASCADE_INTERVAL seconds."""
    if not _autonomy_allows_workload(
        "coding_implementation",
        agent="coding-agent",
        loop_id="code_cascade",
    ):
        return

    try:
        r = await _get_redis()
        last = await r.get(CODE_CASCADE_KEY)
        last_ts = float(last) if last else 0.0
        if time.time() - last_ts < CODE_CASCADE_INTERVAL:
            return

        logger.info("Scheduler: starting code quality cascade")
        from .cascade import CASCADE_TIMEOUT, run_code_quality_cascade
        result = await asyncio.wait_for(
            run_code_quality_cascade(autonomy_managed=True),
            timeout=CASCADE_TIMEOUT,
        )
        await r.set(CODE_CASCADE_KEY, str(time.time()))
        logger.info(
            "Code quality cascade completed: %d steps",
            len(result.get("steps", [])),
        )
    except asyncio.TimeoutError:
        logger.warning("Code quality cascade timed out after %ds", CASCADE_TIMEOUT)
    except Exception as e:
        logger.warning("Code quality cascade failed: %s", e)


async def _scheduler_loop():
    """Background scheduler — checks agent schedules and submits tasks."""

    logger.info("Proactive scheduler started (interval=%.0fs)", SCHEDULER_INTERVAL)

    # Wait 60s after startup before first check (let everything initialize)
    await asyncio.sleep(60)

    while True:
        try:
            now = time.time()

            # Check infrastructure alerts (every 5 min)
            await _check_alerts()

            # Check time-of-day tasks
            await _check_consolidation()
            await _check_pattern_detection()
            await _check_daily_digest()
            await _check_morning_plan()

            # Owner model full rebuild (4:00 AM)
            await _check_owner_model()

            # Self-improvement cycle (5:30 AM, after pattern detection)
            await _check_improvement_cycle()

            # Work pipeline cycles (06:00, 12:00, 18:00)
            await _check_work_pipeline()

            # Nightly prompt optimization (22:00)
            await _check_nightly_optimization()

            # Nightly knowledge refresh (00:00)
            await _check_knowledge_refresh()

            # Weekly DPO training (Saturday 02:00)
            await _check_weekly_dpo_training()

            # Check work plan refill (every 2 hours)
            await _check_workplan_refill()

            # Check autonomous research jobs
            await _check_research_jobs()

            # Self-improvement benchmarks (every 6h)
            await _check_benchmarks()

            # Semantic cache cleanup (every 1h)
            await _check_cache_cleanup()

            # Quality cascades — multi-agent improvement loops
            await _check_creative_cascade()
            await _check_code_cascade()

            for agent, schedule in AGENT_SCHEDULES.items():
                if not schedule.get("enabled", True):
                    continue

                interval = schedule["interval"]
                last_run = await _get_last_run(agent)

                if now - last_run >= interval:
                    workload_class = SCHEDULED_AGENT_WORKLOADS.get(agent, "private_automation")
                    if not _autonomy_allows_workload(
                        workload_class,
                        agent=agent,
                        loop_id=f"schedule:{agent}",
                    ):
                        continue

                    # INFRA-003: Skip infrastructure tasks during peak hours
                    if schedule.get("infrastructure", False) and is_peak_hours():
                        logger.info(
                            "Scheduler: skipping %s during peak hours (INFRA-003)",
                            agent,
                        )
                        continue

                    logger.info(
                        "Scheduler: submitting proactive task for %s (interval=%ds)",
                        agent, interval,
                    )
                    try:
                        from .tasks import submit_governed_task

                        submission = await submit_governed_task(
                            agent=agent,
                            prompt=schedule["prompt"],
                            priority=schedule["priority"],
                            metadata={
                                "source": "scheduler",
                                "interval": interval,
                                "task_class": workload_class,
                            },
                            source="scheduler",
                        )
                        task = submission.task
                        await _set_last_run(agent, now)

                        # Log schedule_run event for pattern detection
                        from .activity import log_event
                        asyncio.create_task(log_event(
                            event_type="schedule_run",
                            agent=agent,
                            description=f"Scheduled task submitted (interval={interval}s)",
                            data={"interval": interval, "priority": schedule["priority"]},
                        ))
                    except Exception as e:
                        logger.warning("Scheduler: failed to submit task for %s: %s", agent, e)

        except asyncio.CancelledError:
            logger.warning("Scheduler loop cancelled — stopping")
            return
        except BaseException as e:
            logger.warning("Scheduler loop error: %s", e)

        await asyncio.sleep(SCHEDULER_INTERVAL)


async def get_schedule_status() -> dict:
    """Get current schedule status for all agents."""
    now = time.time()
    statuses = []

    for agent, schedule in AGENT_SCHEDULES.items():
        last_run = await _get_last_run(agent)
        next_run = last_run + schedule["interval"] if last_run else now
        time_until = max(0, next_run - now)

        statuses.append({
            "agent": agent,
            "interval_seconds": schedule["interval"],
            "interval_human": _humanize_interval(schedule["interval"]),
            "enabled": schedule.get("enabled", True),
            "last_run": last_run if last_run else None,
            "next_run_in": int(time_until),
            "priority": schedule["priority"],
        })

    return {
        "schedules": statuses,
        "scheduler_running": _scheduler_task is not None and not _scheduler_task.done(),
    }


def _humanize_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}min"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


async def start_scheduler():
    """Start the proactive agent scheduler."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.info("Scheduler already running")
        return

    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Proactive agent scheduler started")


async def stop_scheduler():
    """Stop the proactive agent scheduler."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("Proactive agent scheduler stopped")


async def get_scheduler_health() -> dict:
    """Return scheduler health: running state and last-run timestamps per agent."""
    running = _scheduler_task is not None and not _scheduler_task.done()
    now = time.time()

    schedules = {}
    for agent, config in AGENT_SCHEDULES.items():
        last_run = await _get_last_run(agent)
        interval = config["interval"]
        ago = int(now - last_run) if last_run > 0 else None
        schedules[agent] = {
            "interval_s": interval,
            "enabled": config.get("enabled", True),
            "last_run_ago_s": ago,
            "overdue": ago is not None and ago > interval * 2,
        }

    # Special schedules
    try:
        r = await _get_redis()
        digest_ts = await r.get(DAILY_DIGEST_KEY)
        pattern_ts = await r.get(PATTERN_DETECTION_KEY)
        alert_ts = await r.get(ALERT_CHECK_KEY)
        owner_ts = await r.get(OWNER_MODEL_KEY)
    except Exception:
        digest_ts = pattern_ts = alert_ts = owner_ts = None

    def _safe_float(val):
        if not val:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # Synthesis stats
    synthesis_stats = {}
    try:
        from .intent_synthesizer import get_synthesis_stats
        synthesis_stats = await get_synthesis_stats()
    except Exception:
        pass

    # Owner model freshness
    owner_model_info = {}
    try:
        from .owner_model import get_owner_profile
        profile = await get_owner_profile()
        if profile:
            owner_model_info = {
                "refreshed_at": profile.get("refreshed_at"),
                "domains": len(profile.get("domains", {})),
                "goals": len(profile.get("active_goals", [])),
            }
    except Exception:
        pass

    return {
        "running": running,
        "check_interval_s": SCHEDULER_INTERVAL,
        "agent_schedules": schedules,
        "special_schedules": {
            "daily_digest": {"last_run": _safe_float(digest_ts)},
            "pattern_detection": {"last_run": _safe_float(pattern_ts)},
            "alert_check": {"last_run": _safe_float(alert_ts)},
            "owner_model": {"last_run": _safe_float(owner_ts)},
        },
        "owner_model": owner_model_info,
        "synthesis": synthesis_stats,
    }



# --- Backbone governance hooks (reconciled from backbone branch) ---
# These additions are appended after all existing scheduler code.
# They provide governance-aware job control and manual job execution.

from typing import Any

BUILTIN_JOB_SCOPES: dict[str, str] = {
    "daily-digest": "scheduler",
    "pattern-detection": "scheduler",
    "consolidation": "scheduler",
    "morning-plan": "scheduler",
    "workplan-refill": "scheduler",
    "pipeline-cycle": "scheduler",
    "owner-model": "scheduler",
    "nightly-optimization": "scheduler",
    "creative-cascade": "scheduler",
    "code-cascade": "scheduler",
    "research:scheduler": "research_jobs",
    "alert-check": "alerts",
    "benchmark-cycle": "benchmark_cycle",
    "weekly-dpo-training": "benchmark_cycle",
    "cache-cleanup": "maintenance",
    "knowledge-refresh": "maintenance",
    "improvement-cycle": "scheduler",
}

def get_schedule_control_scope(job_id: str) -> str | None:
    if job_id.startswith("agent-schedule:"):
        return "scheduler"
    if job_id.startswith("research:"):
        return "research_jobs"
    return BUILTIN_JOB_SCOPES.get(job_id)


async def get_model_intelligence_cadence() -> list[dict[str, Any]]:
    """Return the modeled cadence records for the model-intelligence lane.

    This is a compatibility/export seam used by model governance snapshots and
    the dashboard read model. The records are registry-backed, but they still
    inherit current governor posture so the UI does not report a schedule as
    runnable when the control plane would defer it.
    """

    from .model_governance import get_model_intelligence_lane

    cadence = dict(get_model_intelligence_lane().get("cadence") or {})
    definitions = [
        {
            "id": "model-intelligence:weekly-horizon-scan",
            "cadence_key": "weekly_horizon_scan",
            "title": "Weekly horizon scan",
            "job_family": "research_job",
            "owner_agent": "research-agent",
            "control_scope": "research_jobs",
            "trigger_mode": "weekly",
            "deep_link": "/learning",
        },
        {
            "id": "model-intelligence:weekly-candidate-triage",
            "cadence_key": "weekly_candidate_triage",
            "title": "Weekly candidate triage",
            "job_family": "research_job",
            "owner_agent": "research-agent",
            "control_scope": "research_jobs",
            "trigger_mode": "weekly",
            "deep_link": "/learning",
        },
        {
            "id": "model-intelligence:monthly-rebaseline",
            "cadence_key": "monthly_rebaseline",
            "title": "Monthly rebaseline",
            "job_family": "benchmarks",
            "owner_agent": "system",
            "control_scope": "benchmark_cycle",
            "trigger_mode": "monthly",
            "deep_link": "/learning",
        },
        {
            "id": "model-intelligence:urgent-scan",
            "cadence_key": "urgent_scan",
            "title": "Urgent model scan",
            "job_family": "research_job",
            "owner_agent": "research-agent",
            "control_scope": "research_jobs",
            "trigger_mode": "manual",
            "deep_link": "/learning",
        },
    ]

    try:
        from .governor_backbone import build_capacity_snapshot, evaluate_job_governance

        capacity_snapshot = await build_capacity_snapshot()
    except Exception as exc:
        logger.debug("Model intelligence cadence using degraded posture fallback: %s", exc)
        capacity_snapshot = None
        evaluate_job_governance = None

    records: list[dict[str, Any]] = []
    for definition in definitions:
        governance: dict[str, Any] = {}
        allowed = True

        if evaluate_job_governance is not None:
            try:
                governance = await evaluate_job_governance(
                    job_id=definition["id"],
                    job_family=definition["job_family"],
                    control_scope=definition["control_scope"],
                    owner_agent=definition["owner_agent"],
                    capacity_snapshot=capacity_snapshot,
                )
                allowed = bool(governance.get("allowed"))
            except Exception as exc:
                logger.debug(
                    "Model intelligence cadence governance degraded for %s: %s",
                    definition["id"],
                    exc,
                )
                governance = {"reason": str(exc), "status": "degraded"}
                allowed = False

        records.append(
            {
                "id": definition["id"],
                "cadence_key": definition["cadence_key"],
                "title": definition["title"],
                "cadence": str(cadence.get(definition["cadence_key"]) or "manual"),
                "trigger_mode": definition["trigger_mode"],
                "job_family": definition["job_family"],
                "owner_agent": definition["owner_agent"],
                "control_scope": definition["control_scope"],
                "current_state": "scheduled" if allowed else "deferred",
                "can_run_now": allowed,
                "can_override_now": not allowed,
                "governor_reason": None if allowed else str(governance.get("reason") or "") or None,
                "presence_state": str(governance.get("presence_state") or ""),
                "release_tier": str(governance.get("release_tier") or ""),
                "capacity_posture": str(governance.get("capacity_posture") or ""),
                "queue_posture": str(governance.get("queue_posture") or ""),
                "provider_posture": str(governance.get("provider_posture") or ""),
                "active_window_ids": list(governance.get("active_window_ids") or []),
                "deep_link": definition["deep_link"],
            }
        )

    return records


async def _governor_allows(
    *,
    job_id: str,
    job_family: str,
    owner_agent: str,
    capacity_snapshot: dict[str, Any] | None = None,
) -> bool:
    from .governor_backbone import evaluate_job_governance

    decision = await evaluate_job_governance(
        job_id=job_id,
        job_family=job_family,
        control_scope=get_schedule_control_scope(job_id),
        owner_agent=owner_agent,
        capacity_snapshot=capacity_snapshot,
    )
    return bool(decision.get("allowed"))


def _manual_job_governance_context(job_id: str) -> tuple[str, str]:
    if job_id.startswith("agent-schedule:"):
        agent = job_id.split(":", 1)[1]
        return "agent_schedule", agent
    if job_id == "daily-digest":
        return "daily_digest", "general-assistant"
    if job_id == "consolidation":
        return "consolidation", "system"
    if job_id == "pattern-detection":
        return "pattern_detection", "system"
    if job_id == "morning-plan":
        return "workplan", "system"
    if job_id == "workplan-refill":
        return "workplan_refill", "system"
    if job_id == "pipeline-cycle":
        return "pipeline", "system"
    if job_id == "owner-model":
        return "owner_model", "system"
    if job_id == "nightly-optimization":
        return "nightly_optimization", "system"
    if job_id == "knowledge-refresh":
        return "knowledge_refresh", "system"
    if job_id == "alert-check":
        return "alerts", "system"
    if job_id == "research:scheduler":
        return "research_jobs", "research-agent"
    if job_id.startswith("research:"):
        return "research_job", "research-agent"
    if job_id == "benchmark-cycle":
        return "benchmarks", "system"
    if job_id == "weekly-dpo-training":
        return "weekly_dpo_training", "system"
    if job_id == "improvement-cycle":
        return "improvement_cycle", "system"
    if job_id == "creative-cascade":
        return "creative_cascade", "creative-agent"
    if job_id == "code-cascade":
        return "code_cascade", "coding-agent"
    if job_id == "cache-cleanup":
        return "cache_cleanup", "system"
    raise KeyError(job_id)


async def _emit_schedule_event(
    *,
    event_type: str,
    job_id: str,
    job_family: str,
    owner_agent: str,
    trigger_mode: str,
    summary: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    from .activity import log_event

    payload: dict[str, Any] = {
        "job_id": job_id,
        "job_family": job_family,
        "owner_agent": owner_agent,
        "trigger_mode": trigger_mode,
        "outcome": outcome,
        "summary": summary,
        "control_scope": get_schedule_control_scope(job_id),
        "error": error,
    }
    if metadata:
        payload.update(metadata)

    await log_event(
        event_type=event_type,
        agent=owner_agent,
        description=summary,
        data=payload,
    )




async def _run_agent_schedule(
    agent: str,
    schedule: dict[str, Any],
    *,
    trigger_mode: str,
    actor: str,
    force_override: bool,
) -> dict[str, Any]:
    from .tasks import submit_governed_task

    interval = int(schedule.get("interval", 0) or 0)
    priority = str(schedule.get("priority") or "normal")
    workload_class = SCHEDULED_AGENT_WORKLOADS.get(agent, "private_automation")
    submission = await submit_governed_task(
        agent=agent,
        prompt=str(schedule.get("prompt") or ""),
        priority=priority,
        metadata={
            "source": "scheduler",
            "interval": interval,
            "task_class": workload_class,
        },
        source="scheduler",
    )
    task = submission.task
    await _set_last_run(agent, time.time())
    status = "pending_approval" if submission.held_for_approval else "queued"
    summary = f"Manual {agent} proactive loop submitted as task {task.id}"
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id=f"agent-schedule:{agent}",
        job_family="agent_schedule",
        owner_agent=agent,
        trigger_mode=trigger_mode,
        summary=summary,
        outcome=status,
        metadata={
            "actor": actor,
            "force_override": force_override,
            "interval": interval,
            "priority": priority,
            "task_id": task.id,
            "held_for_approval": submission.held_for_approval,
        },
    )
    return {
        "job_id": f"agent-schedule:{agent}",
        "status": status,
        "summary": summary,
        "task_id": task.id,
    }


async def _run_daily_digest(*, trigger_mode: str, actor: str, force_override: bool) -> dict[str, Any]:
    from .goals import generate_digest_prompt
    from .tasks import submit_governed_task

    now = datetime.now()
    prompt = await generate_digest_prompt()
    submission = await submit_governed_task(
        agent="general-assistant",
        prompt=prompt,
        priority="normal",
        metadata={
            "source": "daily_digest",
            "date": now.strftime("%Y-%m-%d"),
            "task_class": "briefing_digest",
        },
        source="scheduler",
    )
    task = submission.task
    r = await _get_redis()
    await r.set(DAILY_DIGEST_KEY, now.strftime("%Y-%m-%d"))
    status = "pending_approval" if submission.held_for_approval else "queued"
    summary = f"Manual daily digest submitted as task {task.id}"
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="daily-digest",
        job_family="daily_digest",
        owner_agent="general-assistant",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome=status,
        metadata={
            "actor": actor,
            "force_override": force_override,
            "task_id": task.id,
            "held_for_approval": submission.held_for_approval,
            "date": now.strftime("%Y-%m-%d"),
        },
    )
    return {
        "job_id": "daily-digest",
        "status": status,
        "summary": summary,
        "task_id": task.id,
    }


async def _run_consolidation_job(*, trigger_mode: str, actor: str, force_override: bool) -> dict[str, Any]:
    from .consolidation import run_consolidation

    now = datetime.now()
    results = await run_consolidation()
    r = await _get_redis()
    await r.set(CONSOLIDATION_KEY, now.strftime("%Y-%m-%d"))
    error_count = len(results.get("errors", []))
    status = "warning" if error_count else "completed"
    summary = (
        f"Manual consolidation deleted {results.get('total_deleted', 0)} points "
        f"with {error_count} error(s)"
    )
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="consolidation",
        job_family="consolidation",
        owner_agent="system",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome=status,
        metadata={
            "actor": actor,
            "force_override": force_override,
            "total_deleted": results.get("total_deleted", 0),
            "error_count": error_count,
        },
        error="; ".join(results.get("errors", [])),
    )
    return {
        "job_id": "consolidation",
        "status": status,
        "summary": summary,
        "result": results,
    }


async def _run_pattern_detection_job(*, trigger_mode: str, actor: str, force_override: bool) -> dict[str, Any]:
    from .patterns import run_pattern_detection

    now = datetime.now()
    report = await run_pattern_detection()
    r = await _get_redis()
    await r.set(PATTERN_DETECTION_KEY, now.strftime("%Y-%m-%d"))

    adjustment_error = ""
    adjustment_count = 0
    try:
        from .goals import apply_trust_adjustments

        adjustment_result = await apply_trust_adjustments()
        adjustment_count = int(adjustment_result.get("agent_count", 0) or 0)
    except Exception as exc:
        adjustment_error = str(exc)

    pattern_count = len(report.get("patterns", []))
    recommendation_count = len(report.get("recommendations", []))
    status = "warning" if adjustment_error else "completed"
    summary = (
        f"Manual pattern detection found {pattern_count} pattern(s), "
        f"{recommendation_count} recommendation(s), and updated {adjustment_count} agent threshold(s)"
    )
    await _emit_schedule_event(
        event_type="schedule_run",
        job_id="pattern-detection",
        job_family="pattern_detection",
        owner_agent="system",
        trigger_mode=trigger_mode,
        summary=summary,
        outcome=status,
        metadata={
            "actor": actor,
            "force_override": force_override,
            "pattern_count": pattern_count,
            "recommendation_count": recommendation_count,
            "adjustment_count": adjustment_count,
        },
        error=adjustment_error,
    )
    return {
        "job_id": "pattern-detection",
        "status": status,
        "summary": summary,
        "result": report,
        "adjustment_error": adjustment_error or None,
    }


async def run_scheduled_job(
    job_id: str,
    actor: str = "operator",
    *,
    force: bool = False,
) -> dict[str, Any]:
    from .governor_backbone import build_capacity_snapshot, evaluate_job_governance

    job_family, owner_agent = _manual_job_governance_context(job_id)
    capacity_snapshot = await build_capacity_snapshot()
    governance = await evaluate_job_governance(
        job_id=job_id,
        job_family=job_family,
        control_scope=get_schedule_control_scope(job_id),
        owner_agent=owner_agent,
        capacity_snapshot=capacity_snapshot,
    )
    if not governance.get("allowed") and not force:
        summary = (
            f"Governor deferred manual run for {job_id}: "
            f"{str(governance.get('reason') or 'not permitted under current posture')}"
        )
        await _emit_schedule_event(
            event_type="schedule_skipped",
            job_id=job_id,
            job_family=job_family,
            owner_agent=owner_agent,
            trigger_mode="manual",
            summary=summary,
            outcome="deferred",
            metadata={
                "actor": actor,
                "governor_status": governance.get("status"),
                "presence_state": governance.get("presence_state"),
                "release_tier": governance.get("release_tier"),
                "capacity_posture": governance.get("capacity_posture"),
                "queue_posture": governance.get("queue_posture"),
                "provider_posture": governance.get("provider_posture"),
                "active_window_ids": governance.get("active_window_ids"),
                "deferred_by": governance.get("deferred_by"),
                "force_override": False,
            },
        )
        return {
            "job_id": job_id,
            "status": "deferred",
            "summary": summary,
            "governor_decision": governance,
            "override_available": True,
        }

    if job_id.startswith("agent-schedule:"):
        agent = job_id.split(":", 1)[1]
        schedule = AGENT_SCHEDULES.get(agent)
        if not schedule:
            raise KeyError(job_id)
        return await _run_agent_schedule(
            agent,
            schedule,
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "daily-digest":
        return await _run_daily_digest(trigger_mode="manual", actor=actor, force_override=force)

    if job_id == "consolidation":
        return await _run_consolidation_job(
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "pattern-detection":
        return await _run_pattern_detection_job(
            trigger_mode="manual",
            actor=actor,
            force_override=force,
        )

    if job_id == "morning-plan":
        from .workplanner import generate_work_plan

        plan = await generate_work_plan(focus="morning planning - prioritize creative work for EoBQ")
        summary = f"Manual morning work plan generated with {plan.get('task_count', 0)} tasks"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="workplan",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "plan_id": plan.get("plan_id"),
                "task_count": plan.get("task_count", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary, "plan_id": plan.get("plan_id")}

    if job_id == "workplan-refill":
        from .workplanner import generate_work_plan, should_refill

        needs_refill = await should_refill()
        if not needs_refill:
            summary = "Manual workplan refill skipped because queue posture is healthy"
            await _emit_schedule_event(
                event_type="schedule_skipped",
                job_id=job_id,
                job_family="workplan_refill",
                owner_agent="system",
                trigger_mode="manual",
                summary=summary,
                outcome="skipped",
                metadata={"actor": actor, "force_override": force},
            )
            return {"job_id": job_id, "status": "skipped", "summary": summary}

        plan = await generate_work_plan(focus="queue refill - pick up where we left off")
        summary = f"Manual workplan refill generated {plan.get('task_count', 0)} tasks"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="workplan_refill",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "plan_id": plan.get("plan_id"),
                "task_count": plan.get("task_count", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary, "plan_id": plan.get("plan_id")}

    if job_id == "pipeline-cycle":
        from .work_pipeline import run_pipeline_cycle

        result = await asyncio.wait_for(run_pipeline_cycle(), timeout=900)
        summary = (
            f"Manual pipeline cycle mined {result.intents_mined} intents, created "
            f"{result.plans_created} plans, and submitted {result.tasks_submitted} task(s)"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="pipeline",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if not result.errors else "warning",
            metadata={
                "intents_mined": result.intents_mined,
                "intents_new": result.intents_new,
                "plans_created": result.plans_created,
                "tasks_submitted": result.tasks_submitted,
                "tasks_held": result.tasks_held,
                "error_count": len(result.errors),
                "actor": actor,
                "force_override": force,
            },
            error="; ".join(result.errors),
        )
        return {
            "job_id": job_id,
            "status": "completed" if not result.errors else "warning",
            "summary": summary,
            "result": {
                "intents_mined": result.intents_mined,
                "intents_new": result.intents_new,
                "plans_created": result.plans_created,
                "tasks_submitted": result.tasks_submitted,
                "tasks_held": result.tasks_held,
                "errors": list(result.errors),
            },
        }

    if job_id == "alert-check":
        from .alerts import check_prometheus_alerts

        result = await check_prometheus_alerts()
        summary = f"Manual alert check saw {result.get('active', 0)} active and {result.get('new', 0)} new alerts"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="alerts",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if result.get("checked") else "failed",
            metadata={
                "active": result.get("active", 0),
                "new": result.get("new", 0),
                "actor": actor,
                "force_override": force,
            },
            error=str(result.get("error", "")) if result.get("error") else "",
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "research:scheduler":
        from .research_jobs import check_scheduled_jobs

        triggered = await check_scheduled_jobs()
        summary = f"Manual research scheduler run triggered {triggered} job(s)"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="research_jobs",
            owner_agent="research-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="queued" if triggered > 0 else "completed",
            metadata={"triggered": triggered, "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "queued" if triggered > 0 else "completed", "summary": summary}

    if job_id == "owner-model":
        from .owner_model import rebuild_full

        profile = await rebuild_full()
        summary = (
            f"Manual owner-model rebuild completed with {len(profile.get('domains', {}))} domains "
            f"and {len(profile.get('active_goals', []))} active goals"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="owner_model",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id.startswith("research:"):
        from .research_jobs import execute_job

        research_job_id = job_id.split(":", 1)[1]
        result = await execute_job(research_job_id)
        if result.get("error"):
            await _emit_schedule_event(
                event_type="schedule_failed",
                job_id=job_id,
                job_family="research_job",
                owner_agent="research-agent",
                trigger_mode="manual",
                summary="Research job execution failed",
                outcome="failed",
                error=str(result["error"]),
            )
            return {"job_id": job_id, "status": "failed", "summary": str(result["error"])}

        summary = f"Research job {research_job_id} submitted"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="research_job",
            owner_agent="research-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="queued",
            metadata={"task_id": result.get("task_id"), "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "queued", "task_id": result.get("task_id"), "summary": summary}

    if job_id == "benchmark-cycle":
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_benchmark_suite()
        summary = f"Manual benchmark cycle completed: {result.get('passed', 0)}/{result.get('total', 0)} passed"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="benchmarks",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={
                "passed": result.get("passed", 0),
                "total": result.get("total", 0),
                "actor": actor,
                "force_override": force,
            },
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "improvement-cycle":
        from .self_improvement import get_improvement_engine

        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_improvement_cycle()
        summary = (
            f"Manual improvement cycle generated {result.get('proposals_generated', 0)} proposals "
            f"from {result.get('patterns_consumed', 0)} patterns"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="improvement_cycle",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "nightly-optimization":
        from .prompt_optimizer import run_nightly_optimization

        result = await run_nightly_optimization()
        summary = (
            f"Manual nightly optimization analyzed {result.get('traces_analyzed', 0)} traces, "
            f"found {len(result.get('underperformers', []))} underperformers, and generated "
            f"{result.get('variants_generated', 0)} variants"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="nightly_optimization",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    if job_id == "knowledge-refresh":
        from .knowledge_refresh import run_knowledge_refresh

        result = await run_knowledge_refresh()
        summary = (
            f"Manual knowledge refresh found {result.get('docs_found', 0)} documents, refreshed "
            f"{result.get('docs_refreshed', 0)}, and failed {result.get('docs_failed', 0)}"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="knowledge_refresh",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if not result.get("docs_failed") else "warning",
            metadata={"actor": actor, "force_override": force},
        )
        return {
            "job_id": job_id,
            "status": "completed" if not result.get("docs_failed") else "warning",
            "summary": summary,
        }

    if job_id == "weekly-dpo-training":
        now = datetime.now()
        r = await _get_redis()
        outcomes_raw = await r.lrange("athanor:pipeline:outcomes", 0, -1)
        pairs = []
        for raw in outcomes_raw:
            try:
                outcome = json.loads(raw if isinstance(raw, str) else raw.decode())
                score = outcome.get("quality_score", 0.5)
                prompt = outcome.get("prompt", "")
                output = outcome.get("output_summary", "")
                if prompt and output and score != 0.5:
                    pairs.append(
                        {
                            "prompt": prompt[:2000],
                            "output": output[:2000],
                            "score": score,
                        }
                    )
            except (json.JSONDecodeError, AttributeError):
                continue

        if len(pairs) < 10:
            summary = f"Manual weekly DPO training skipped because only {len(pairs)} preference pairs are available"
            await _emit_schedule_event(
                event_type="schedule_skipped",
                job_id=job_id,
                job_family="weekly_dpo_training",
                owner_agent="system",
                trigger_mode="manual",
                summary=summary,
                outcome="skipped",
                metadata={"actor": actor, "force_override": force, "pairs": len(pairs)},
            )
            return {"job_id": job_id, "status": "skipped", "summary": summary}

        dataset_key = f"athanor:dpo:dataset:{now.strftime('%Y-%m-%d')}"
        await r.set(dataset_key, json.dumps(pairs), ex=604800)
        await r.set(DPO_TRAINING_KEY, now.strftime("%Y-%m-%d"))

        from .tasks import submit_governed_task

        submission = await submit_governed_task(
            agent="coding-agent",
            prompt=(
                f"Weekly DPO training dataset is ready at Redis key '{dataset_key}' "
                f"with {len(pairs)} preference pairs. "
                "To run LoRA fine-tuning: 1) Stop vllm-coder container on FOUNDRY, "
                "2) Run DPO training on FOUNDRY 4090, "
                "3) Evaluate against promptfoo baseline, "
                "4) If improved, deploy as new worker model on WORKSHOP, "
                "5) Restart vllm-coder. "
                "Report dataset stats and readiness status."
            ),
            priority="low",
            metadata={
                "source": "dpo_training",
                "pairs": len(pairs),
                "date": now.strftime("%Y-%m-%d"),
                "task_class": "background_transform",
                "requires_runtime_mutation": True,
            },
            source="scheduler",
        )
        task = submission.task
        summary = (
            f"Manual weekly DPO training prepared {len(pairs)} preference pairs and submitted task {task.id}"
        )
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="weekly_dpo_training",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="queued" if not submission.held_for_approval else "pending_approval",
            metadata={
                "pairs": len(pairs),
                "dataset_key": dataset_key,
                "actor": actor,
                "force_override": force,
                "task_id": task.id,
                "held_for_approval": submission.held_for_approval,
            },
        )
        return {
            "job_id": job_id,
            "status": "pending_approval" if submission.held_for_approval else "queued",
            "summary": summary,
            "task_id": task.id,
        }

    if job_id == "creative-cascade":
        from .cascade import CASCADE_TIMEOUT, run_creative_cascade

        result = await asyncio.wait_for(
            run_creative_cascade(autonomy_managed=True),
            timeout=CASCADE_TIMEOUT,
        )
        final_quality = float(result.get("final_quality", 0.0) or 0.0)
        error = str(result.get("error") or "") or None
        summary = (
            f"Manual creative cascade completed {result.get('total_loops', 0)} loop(s) "
            f"with final quality {final_quality:.2f}"
        )
        await _emit_schedule_event(
            event_type="schedule_run" if not error else "schedule_failed",
            job_id=job_id,
            job_family="creative_cascade",
            owner_agent="creative-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if not error else "failed",
            metadata={
                "actor": actor,
                "force_override": force,
                "total_loops": result.get("total_loops", 0),
                "final_quality": final_quality,
            },
            error=error or "",
        )
        return {
            "job_id": job_id,
            "status": "completed" if not error else "failed",
            "summary": summary,
            "result": {
                "cascade_id": result.get("cascade_id"),
                "total_loops": result.get("total_loops", 0),
                "final_quality": final_quality,
                "error": error,
            },
        }

    if job_id == "code-cascade":
        from .cascade import CASCADE_TIMEOUT, run_code_quality_cascade

        result = await asyncio.wait_for(
            run_code_quality_cascade(autonomy_managed=True),
            timeout=CASCADE_TIMEOUT,
        )
        steps = list(result.get("steps") or [])
        error = str(result.get("error") or "") or None
        summary = f"Manual code cascade completed {len(steps)} step(s)"
        await _emit_schedule_event(
            event_type="schedule_run" if not error else "schedule_failed",
            job_id=job_id,
            job_family="code_cascade",
            owner_agent="coding-agent",
            trigger_mode="manual",
            summary=summary,
            outcome="completed" if not error else "failed",
            metadata={
                "actor": actor,
                "force_override": force,
                "step_count": len(steps),
            },
            error=error or "",
        )
        return {
            "job_id": job_id,
            "status": "completed" if not error else "failed",
            "summary": summary,
            "result": {
                "cascade_id": result.get("cascade_id"),
                "step_count": len(steps),
                "error": error,
            },
        }

    if job_id == "cache-cleanup":
        from .semantic_cache import get_semantic_cache

        cache = get_semantic_cache()
        deleted = await cache.cleanup_expired()
        summary = f"Manual cache cleanup removed {deleted} expired entries"
        await _emit_schedule_event(
            event_type="schedule_run",
            job_id=job_id,
            job_family="cache_cleanup",
            owner_agent="system",
            trigger_mode="manual",
            summary=summary,
            outcome="completed",
            metadata={"deleted": deleted, "actor": actor, "force_override": force},
        )
        return {"job_id": job_id, "status": "completed", "summary": summary}

    raise KeyError(job_id)

