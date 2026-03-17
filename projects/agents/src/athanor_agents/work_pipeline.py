"""Work Pipeline — the perpetual self-feeding engine.

Mines intent → deduplicates → generates plans → approves or queues →
decomposes into tasks → governor gates → agents execute → feedback loops.

Runs on a schedule (06:00, 12:00, 18:00) and on-demand via API.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

# Redis keys
PIPELINE_OUTCOMES_KEY = "athanor:pipeline:outcomes"
PIPELINE_PROJECT_LAST_TASK_KEY = "athanor:pipeline:project_last_task"
PIPELINE_CYCLE_HISTORY_KEY = "athanor:pipeline:cycle_history"
PIPELINE_GENERATION_CONTEXT_KEY = "athanor:pipeline:generation_context"

OUTCOMES_MAX = 200
CYCLE_HISTORY_MAX = 30
MAX_QUEUE_DEPTH = 20  # Skip generation if queue has >20 pending tasks


@dataclass
class WorkOutcome:
    """Record of a task outcome for the learning loop."""
    task_id: str
    agent: str
    prompt: str
    quality_score: float
    success: bool
    plan_id: str = ""
    project_id: str = ""
    retried: bool = False
    ts: float = 0.0

    def __post_init__(self):
        if not self.ts:
            self.ts = time.time()


@dataclass
class CycleResult:
    """Result of a pipeline cycle."""
    timestamp: float
    intents_mined: int
    intents_new: int
    plans_created: int
    tasks_submitted: int
    tasks_held: int
    errors: list[str] = field(default_factory=list)


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def run_pipeline_cycle() -> CycleResult:
    """Execute one full pipeline cycle.

    1. Check queue depth — skip if overloaded
    2. Mine all intent sources
    3. Deduplicate against known intents
    4. Generate plans for new intents
    5. Auto-approve low-risk plans (governor Level A)
    6. Decompose approved plans into tasks
    7. Submit tasks through governor gate
    8. Record cycle results
    """
    result = CycleResult(
        timestamp=time.time(),
        intents_mined=0,
        intents_new=0,
        plans_created=0,
        tasks_submitted=0,
        tasks_held=0,
    )

    # 1. Check queue depth
    try:
        from .tasks import get_task_stats
        stats = await get_task_stats()
        pending = stats.get("by_status", {}).get("pending", 0)
        if pending > MAX_QUEUE_DEPTH:
            logger.info("Pipeline cycle skipped: queue depth %d > %d", pending, MAX_QUEUE_DEPTH)
            result.errors.append(f"Queue depth {pending} exceeds max {MAX_QUEUE_DEPTH}")
            await _record_cycle(result)
            return result
    except Exception as e:
        logger.warning("Queue depth check failed: %s", e)

    # 2a. Ensure owner model is fresh
    try:
        from .owner_model import ensure_fresh
        await ensure_fresh()
    except Exception as e:
        logger.warning("Owner model refresh failed: %s", e)

    # 2b. Synthesize strategic intents (cross-domain, vision-aware)
    synthesis_intents: list = []
    try:
        from .intent_synthesizer import synthesize_strategic_intents
        synthesis_intents = await synthesize_strategic_intents()
        logger.info("Synthesis produced %d strategic intents", len(synthesis_intents))
    except Exception as e:
        logger.warning("Intent synthesis failed: %s", e)
        result.errors.append(f"Synthesis failed: {e}")

    # 2c. Mine reactive intent sources (existing 15 miners)
    try:
        from .intent_miner import mine_all_sources
        mined_intents = await mine_all_sources()
    except Exception as e:
        logger.error("Intent mining failed: %s", e)
        result.errors.append(f"Mining failed: {e}")
        mined_intents = []

    raw_intents = synthesis_intents + mined_intents
    result.intents_mined = len(raw_intents)

    if not raw_intents:
        await _record_cycle(result)
        return result

    # 3. Deduplicate
    from .plan_generator import is_duplicate_intent, record_intent_hash
    new_intents = []
    for intent in raw_intents:
        if not await is_duplicate_intent(intent.text):
            new_intents.append(intent)
    result.intents_new = len(new_intents)

    if not new_intents:
        logger.info("Pipeline cycle: %d intents mined, 0 new", result.intents_mined)
        await _record_cycle(result)
        return result

    # 4. Generate plans (limit to 8 per cycle — each is an LLM call)
    from .plan_generator import generate_plan_from_intent, decompose_plan_to_tasks, approve_plan
    plans = []
    for intent in new_intents[:8]:
        try:
            plan = await generate_plan_from_intent(
                intent_source=intent.source,
                intent_text=intent.text,
                priority_hint=intent.priority_hint,
                metadata=intent.metadata,
            )
            plans.append(plan)
            await record_intent_hash(intent.text, plan.id)
            result.plans_created += 1
        except Exception as e:
            logger.warning("Plan generation failed for intent: %s", e)
            result.errors.append(f"Plan gen failed: {e}")

    # 5. Auto-approve low-risk plans
    from .governor import Governor
    gov = Governor.get()

    for plan in plans:
        if plan.risk_level == "low" or (
            plan.risk_level == "medium" and getattr(plan, "estimated_minutes", 60) < 30
        ):
            # Auto-approve low-risk and short medium-risk plans
            try:
                decision = await gov.gate_task_submission(
                    agent=plan.assigned_agents[0] if plan.assigned_agents else "general-assistant",
                    prompt=plan.title,
                    priority="normal",
                    metadata={"source": "pipeline", "plan_id": plan.id},
                    source="pipeline",
                )
                if decision.autonomy_level == "A":
                    approved = await approve_plan(plan.id, actor="auto")
                    if approved:
                        plan = approved
            except Exception as e:
                logger.debug("Auto-approve check failed: %s", e)

    # 6. Decompose approved plans into tasks
    for plan in plans:
        if plan.status == "approved":
            try:
                task_specs = await decompose_plan_to_tasks(plan)
                # 7. Submit through governor
                for spec in task_specs:
                    try:
                        decision = await gov.gate_task_submission(
                            agent=spec["agent"],
                            prompt=spec["prompt"],
                            priority=spec.get("priority", "normal"),
                            metadata=spec.get("metadata", {}),
                            source="pipeline",
                        )

                        from .tasks import submit_task, _update_task
                        task = await submit_task(
                            agent=spec["agent"],
                            prompt=spec["prompt"],
                            priority=spec.get("priority", "normal"),
                            metadata={
                                **spec.get("metadata", {}),
                                "governor_decision": decision.reason,
                            },
                        )
                        if decision.status_override == "pending_approval":
                            task.status = "pending_approval"
                            await _update_task(task)
                            result.tasks_held += 1
                        else:
                            result.tasks_submitted += 1
                    except Exception as e:
                        logger.warning("Task submission failed: %s", e)
                        result.errors.append(f"Task submit failed: {e}")
            except Exception as e:
                logger.warning("Plan decomposition failed: %s", e)
                result.errors.append(f"Decomposition failed: {e}")

    # 8. Record cycle
    await _record_cycle(result)
    await _check_starvation()

    logger.info(
        "Pipeline cycle complete: mined=%d new=%d plans=%d submitted=%d held=%d",
        result.intents_mined, result.intents_new, result.plans_created,
        result.tasks_submitted, result.tasks_held,
    )
    return result


async def record_outcome(
    task_id: str,
    agent: str,
    prompt: str,
    quality_score: float,
    success: bool,
    plan_id: str = "",
    project_id: str = "",
):
    """Record a task outcome for the learning loop."""
    outcome = WorkOutcome(
        task_id=task_id,
        agent=agent,
        prompt=prompt[:500],
        quality_score=quality_score,
        success=success,
        plan_id=plan_id,
        project_id=project_id,
    )
    r = await _get_redis()
    await r.lpush(PIPELINE_OUTCOMES_KEY, json.dumps(asdict(outcome)))
    await r.ltrim(PIPELINE_OUTCOMES_KEY, 0, OUTCOMES_MAX - 1)

    # Update project last task timestamp
    if project_id:
        await r.hset(PIPELINE_PROJECT_LAST_TASK_KEY, project_id, str(time.time()))


async def get_recent_outcomes(limit: int = 20) -> list[dict]:
    """Get recent task outcomes."""
    r = await _get_redis()
    raw = await r.lrange(PIPELINE_OUTCOMES_KEY, 0, limit - 1)
    results = []
    for item in raw:
        text = item.decode() if isinstance(item, bytes) else item
        try:
            results.append(json.loads(text))
        except json.JSONDecodeError:
            pass
    return results


async def get_pipeline_status() -> dict:
    """Get pipeline status for dashboard."""
    r = await _get_redis()

    # Recent cycle history
    raw_cycles = await r.lrange(PIPELINE_CYCLE_HISTORY_KEY, 0, 4)
    cycles = []
    for item in raw_cycles:
        text = item.decode() if isinstance(item, bytes) else item
        try:
            cycles.append(json.loads(text))
        except json.JSONDecodeError:
            pass

    # Pending plans count
    from .plan_generator import get_pending_count
    pending_plans = await get_pending_count()

    # Recent outcomes
    outcomes = await get_recent_outcomes(10)
    avg_quality = 0.0
    if outcomes:
        scores = [o.get("quality_score", 0) for o in outcomes]
        avg_quality = sum(scores) / len(scores)

    return {
        "recent_cycles": cycles,
        "pending_plans": pending_plans,
        "recent_outcomes_count": len(outcomes),
        "avg_quality": round(avg_quality, 3),
        "last_cycle": cycles[0] if cycles else None,
    }


async def _record_cycle(result: CycleResult):
    """Record cycle result to history."""
    r = await _get_redis()
    await r.lpush(PIPELINE_CYCLE_HISTORY_KEY, json.dumps(asdict(result)))
    await r.ltrim(PIPELINE_CYCLE_HISTORY_KEY, 0, CYCLE_HISTORY_MAX - 1)


async def _check_starvation():
    """Check if any project has had no tasks in 24h."""
    try:
        r = await _get_redis()
        last_tasks = await r.hgetall(PIPELINE_PROJECT_LAST_TASK_KEY)
        now = time.time()
        threshold = 24 * 3600  # 24 hours

        starved = []
        for project_id, ts in last_tasks.items():
            pid = project_id.decode() if isinstance(project_id, bytes) else project_id
            ts_val = float(ts.decode() if isinstance(ts, bytes) else ts)
            if now - ts_val > threshold:
                hours_idle = round((now - ts_val) / 3600, 1)
                logger.info("Starvation detected: project %s idle for %.1f hours", pid, hours_idle)
                starved.append(pid)

        # Auto-recovery: publish starvation event and submit a general-assistant
        # planning task to review the starved project
        if starved:
            from .tasks import submit_task
            for pid in starved[:2]:  # Max 2 recovery tasks per cycle
                try:
                    await submit_task(
                        agent="general-assistant",
                        prompt=(
                            f"Project '{pid}' has had no activity for over 24 hours. "
                            f"Review its current status, check for blockers, and suggest "
                            f"the next actionable step. Be specific and practical."
                        ),
                        priority="low",
                        metadata={"source": "pipeline", "trigger": "starvation_recovery", "project": pid},
                    )
                    logger.info("Starvation recovery task submitted for project %s", pid)
                except Exception as e:
                    logger.warning("Failed to submit recovery task for %s: %s", pid, e)

            # Publish event for dashboard visibility
            await r.publish("athanor:tasks:events", json.dumps({
                "event": "starvation_detected",
                "projects": starved,
                "timestamp": now,
            }))
    except Exception as e:
        logger.debug("Starvation check failed: %s", e)
