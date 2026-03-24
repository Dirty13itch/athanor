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

AGENT_SCHEDULES = {
    "general-assistant": {
        "interval": 1800,  # 30 min
        "prompt": (
            "Run a system health check. Check all service health, GPU status, "
            "and report anything that's down or degraded. Only report issues — "
            "don't list services that are working fine unless everything is healthy."
        ),
        "priority": "normal",
        "enabled": True,
    },
    "media-agent": {
        "interval": 900,  # 15 min
        "prompt": (
            "Check for any active downloads, new additions, or queue items in "
            "Sonarr and Radarr. Check Plex for current activity. Report only "
            "notable items — active downloads, new content added, or streams in progress."
        ),
        "priority": "low",
        "enabled": True,
    },
    "home-agent": {
        "interval": 300,  # 5 min
        "prompt": (
            "Check the current state of all Home Assistant entities. "
            "Report any unusual states, recently triggered automations, "
            "or entities that seem anomalous. If everything looks normal, "
            "report a brief status summary."
        ),
        "priority": "low",
        "enabled": True,
    },
    "knowledge-agent": {
        "interval": 3600,  # 1 hour
        "prompt": (
            "Check knowledge base health. Run get_knowledge_stats to see collection sizes. "
            "If any docs were modified recently (check timestamps), note them for re-indexing. "
            "Report collection sizes and any freshness issues."
        ),
        "priority": "low",
        "enabled": True,
    },
    "research-agent": {
        "interval": 7200,  # 2 hours
        "prompt": (
            "Check the intelligence signals pipeline. Search recent signals for "
            "high-relevance items (min_relevance=0.7). If any are actionable for "
            "Athanor (new model releases, vLLM updates, infrastructure tools), "
            "summarize the key findings. Skip if no high-relevance signals."
        ),
        "priority": "low",
        "enabled": True,
    },
    "creative-agent": {
        "interval": 14400,  # 4 hours
        "prompt": (
            "Run a creative production cycle:\n"
            "1. Check ComfyUI health (check_queue). If queue is busy, report and stop.\n"
            "2. Check video inventory (check_video_inventory). Find queens missing 'defiant' stage videos.\n"
            "3. For the first queen missing a video: generate an I2V video using generate_i2v_video "
            "with their portrait URL as anchor and a stage-appropriate motion prompt "
            "(e.g., 'cold stare at viewer, subtle breathing, imperious'). Use quality='quick'.\n"
            "4. Poll for completion (poll_video_completion). If successful, update the inventory "
            "(update_video_inventory) with the video URL.\n"
            "5. Evaluate video quality (evaluate_video_quality). Report the result.\n"
            "If no queens are missing defiant videos, check for other missing stages.\n"
            "If all stages are covered, check for quick-preview videos that could be upgraded to production."
        ),
        "priority": "low",
        "enabled": True,
    },
    "coding-agent": {
        "interval": 10800,  # 3 hours
        "prompt": (
            "Run a quick code health check. Verify the agent server is responding "
            "at the /v1/agents endpoint. Check if any recent tasks had errors. "
            "Report only issues found."
        ),
        "priority": "low",
        "enabled": True,
    },
    "stash-agent": {
        "interval": 21600,  # 6 hours
        "prompt": (
            "Check Stash library stats. Look for recently added scenes that are "
            "untagged or uncategorized. Report counts of unorganized content. "
            "Only report if there are items needing attention."
        ),
        "priority": "low",
        "enabled": True,
    },
    "data-curator": {
        "interval": 21600,  # 6 hours
        "prompt": (
            "Run an autonomous data curation cycle. "
            "1. Check what's already indexed (get_scan_status). "
            "2. Scan accessible roots for new or changed files. "
            "3. Parse and index any unindexed files, prioritizing recently modified "
            "and files in high-value directories (energy audits, AI docs, finance). "
            "4. Report a summary of what was found and indexed."
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
    from .tasks import submit_task
    from .goals import generate_digest_prompt

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
        from .governor import Governor
        gov = Governor.get()
        decision = await gov.gate_task_submission(
            agent="general-assistant", prompt=prompt, priority="normal",
            metadata={"source": "daily_digest", "date": now.strftime("%Y-%m-%d")},
            source="scheduler",
        )
        task = await submit_task(
            agent="general-assistant",
            prompt=prompt,
            priority="normal",
            metadata={"source": "daily_digest", "date": now.strftime("%Y-%m-%d"),
                       "governor_decision": decision.reason},
        )
        if decision.status_override == "pending_approval":
            task.status = "pending_approval"
            from .tasks import _update_task
            await _update_task(task)
        r = await _get_redis()
        await r.set(DAILY_DIGEST_KEY, now.strftime("%Y-%m-%d"))
        logger.info("Daily digest submitted for %s", now.strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning("Scheduler: failed to submit daily digest: %s", e)


async def _check_consolidation():
    """Check if it's time to run memory consolidation (3:00 AM local)."""
    from .consolidation import run_consolidation

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
        plan = await generate_work_plan(focus="morning planning — review all active projects, prioritize highest-impact unblocked work")
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
        plan = await generate_work_plan(focus="queue refill — pick up where we left off")
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
    try:
        from .research_jobs import check_scheduled_jobs

        triggered = await check_scheduled_jobs()
        if triggered > 0:
            logger.info("Scheduler: triggered %d research job(s)", triggered)
    except Exception as e:
        logger.warning("Scheduler: research job check failed: %s", e)


async def _check_benchmarks():
    """Run self-improvement benchmarks every 6 hours."""
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
    from .work_pipeline import run_pipeline_cycle

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
    try:
        result = await asyncio.wait_for(run_pipeline_cycle(), timeout=120)
        r = await _get_redis()
        await r.set(PIPELINE_KEY, str(time.time()))
        logger.info(
            "Work pipeline cycle: mined=%d new=%d plans=%d tasks=%d",
            result.intents_mined, result.intents_new,
            result.plans_created, result.tasks_submitted,
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
    except Exception as e:
        logger.warning("Scheduler: work pipeline cycle failed: %s", e)


async def _check_nightly_optimization():
    """Check if it's time to run nightly prompt optimization (22:00 local)."""
    from .prompt_optimizer import run_nightly_optimization

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

        # Submit a coding-agent task to orchestrate the training
        from .tasks import submit_task
        await submit_task(
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
            metadata={"source": "dpo_training", "pairs": len(pairs), "date": now.strftime("%Y-%m-%d")},
        )
    except Exception as e:
        logger.warning("Scheduler: DPO training data collection failed: %s", e)


async def _scheduler_loop():
    """Background scheduler — checks agent schedules and submits tasks."""
    from .tasks import submit_task

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

            for agent, schedule in AGENT_SCHEDULES.items():
                if not schedule.get("enabled", True):
                    continue

                interval = schedule["interval"]
                last_run = await _get_last_run(agent)

                if now - last_run >= interval:
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
                        from .governor import Governor
                        gov = Governor.get()
                        decision = await gov.gate_task_submission(
                            agent=agent, prompt=schedule["prompt"],
                            priority=schedule["priority"],
                            metadata={"source": "scheduler", "interval": interval},
                            source="scheduler",
                        )
                        task = await submit_task(
                            agent=agent,
                            prompt=schedule["prompt"],
                            priority=schedule["priority"],
                            metadata={"source": "scheduler", "interval": interval,
                                       "governor_decision": decision.reason},
                        )
                        if decision.status_override == "pending_approval":
                            task.status = "pending_approval"
                            from .tasks import _update_task
                            await _update_task(task)
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

def get_schedule_control_scope(job_id: str) -> str | None:
    if job_id.startswith("agent-schedule:"):
        return "scheduler"
    if job_id.startswith("research:"):
        return "research_jobs"
    return BUILTIN_JOB_SCOPES.get(job_id)


async def _governor_allows(
    *,
    job_id: str,
    job_family: str,
    owner_agent: str,
    capacity_snapshot: dict[str, Any] | None = None,
) -> bool:
    from .governor import evaluate_job_governance

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
    if job_id == "alert-check":
        return "alerts", "system"
    if job_id == "research:scheduler":
        return "research_jobs", "research-agent"
    if job_id.startswith("research:"):
        return "research_job", "research-agent"
    if job_id == "benchmark-cycle":
        return "benchmarks", "system"
    if job_id == "improvement-cycle":
        return "improvement_cycle", "system"
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




async def run_scheduled_job(
    job_id: str,
    actor: str = "operator",
    *,
    force: bool = False,
) -> dict[str, Any]:
    from .governor import build_capacity_snapshot, evaluate_job_governance

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

