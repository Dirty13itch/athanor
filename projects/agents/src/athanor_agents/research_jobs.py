"""Autonomous Research Engine — scheduled knowledge growth.

Manages research jobs that run overnight or on schedule:
1. Job CRUD (create/list/get/cancel)
2. Execution via research-agent through the task engine
3. Results stored to Qdrant knowledge collection
4. Scheduler integration for recurring jobs

Ported from: reference/hydra/src/hydra_tools/autonomous_research.py
Adapted for Athanor: Redis job storage, task engine execution,
LiteLLM for synthesis, Qdrant for report storage.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

import httpx

from .config import settings

logger = logging.getLogger(__name__)

RESEARCH_JOBS_KEY = "athanor:research_jobs"
RESEARCH_SCHEDULE_KEY = "athanor:scheduler:research"

_QDRANT_URL = settings.qdrant_url
_LLM_BASE_URL = settings.llm_base_url
_LLM_API_KEY = settings.llm_api_key


class JobStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResearchJob:
    """An autonomous research job definition."""
    id: str
    topic: str
    description: str = ""
    sources: list[str] = field(default_factory=lambda: ["web_search", "knowledge_base"])
    schedule_hours: int = 0  # 0 = run once, >0 = recurring interval
    max_duration_minutes: int = 60
    status: JobStatus = JobStatus.SCHEDULED
    created_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    run_count: int = 0
    last_result: str = ""
    last_task_id: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "sources": self.sources,
            "schedule_hours": self.schedule_hours,
            "max_duration_minutes": self.max_duration_minutes,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "last_result": self.last_result[:500],
            "last_task_id": self.last_task_id,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchJob":
        return cls(
            id=data["id"],
            topic=data["topic"],
            description=data.get("description", ""),
            sources=data.get("sources", ["web_search", "knowledge_base"]),
            schedule_hours=data.get("schedule_hours", 0),
            max_duration_minutes=data.get("max_duration_minutes", 60),
            status=JobStatus(data.get("status", "scheduled")),
            created_at=data.get("created_at", time.time()),
            last_run=data.get("last_run", 0.0),
            run_count=data.get("run_count", 0),
            last_result=data.get("last_result", ""),
            last_task_id=data.get("last_task_id", ""),
            error=data.get("error", ""),
        )


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


# --- Job CRUD ---


async def create_job(
    topic: str,
    description: str = "",
    sources: list[str] | None = None,
    schedule_hours: int = 0,
    max_duration_minutes: int = 60,
) -> ResearchJob:
    """Create a new research job.

    Args:
        topic: Research topic (e.g., "latest vLLM optimization techniques").
        description: Detailed description of what to research.
        sources: List of source types ("web_search", "knowledge_base", "fetch_url").
        schedule_hours: 0 = run once, >0 = recurring every N hours.
        max_duration_minutes: Max execution time.

    Returns:
        The created ResearchJob.
    """
    job = ResearchJob(
        id=f"rj-{uuid.uuid4().hex[:8]}",
        topic=topic,
        description=description,
        sources=sources or ["web_search", "knowledge_base"],
        schedule_hours=schedule_hours,
        max_duration_minutes=max_duration_minutes,
    )

    r = await _get_redis()
    await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))

    logger.info("Research job created: %s — %s", job.id, topic[:60])
    return job


async def get_job(job_id: str) -> ResearchJob | None:
    """Get a research job by ID."""
    try:
        r = await _get_redis()
        raw = await r.hget(RESEARCH_JOBS_KEY, job_id)
        if raw:
            data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            return ResearchJob.from_dict(data)
    except Exception as e:
        logger.warning("Failed to get research job %s: %s", job_id, e)
    return None


async def list_jobs(status: str = "") -> list[dict]:
    """List all research jobs, optionally filtered by status."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(RESEARCH_JOBS_KEY)
        jobs = []
        for _, data in raw.items():
            val = data.decode() if isinstance(data, bytes) else data
            job = ResearchJob.from_dict(json.loads(val))
            if status and job.status.value != status:
                continue
            jobs.append(job.to_dict())
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        return jobs
    except Exception as e:
        logger.warning("Failed to list research jobs: %s", e)
        return []


async def cancel_job(job_id: str) -> bool:
    """Cancel a research job."""
    job = await get_job(job_id)
    if not job:
        return False

    job.status = JobStatus.CANCELLED
    r = await _get_redis()
    await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))
    logger.info("Research job cancelled: %s", job_id)
    return True


async def delete_job(job_id: str) -> bool:
    """Delete a research job."""
    try:
        r = await _get_redis()
        removed = await r.hdel(RESEARCH_JOBS_KEY, job_id)
        return removed > 0
    except Exception as e:
        logger.warning("Failed to delete research job %s: %s", job_id, e)
        return False


# --- Job Execution ---


def _build_research_prompt(job: ResearchJob) -> str:
    """Build the research agent prompt from a job definition."""
    source_instructions = []
    if "web_search" in job.sources:
        source_instructions.append(
            "- Search the web for recent information on this topic"
        )
    if "knowledge_base" in job.sources:
        source_instructions.append(
            "- Search the Athanor knowledge base for existing relevant documents"
        )
    if "fetch_url" in job.sources:
        source_instructions.append(
            "- Fetch and analyze any relevant URLs you find"
        )

    sources_text = "\n".join(source_instructions) if source_instructions else "- Use all available research tools"

    return f"""Autonomous Research Job: {job.topic}

{job.description or f'Research the topic: {job.topic}'}

## Instructions

Conduct thorough research on this topic using the following sources:
{sources_text}

## Requirements

1. Search multiple sources for comprehensive coverage
2. Synthesize findings into a structured report
3. Include specific facts, data points, and citations where available
4. Identify key insights and actionable items
5. Note any gaps in available information

## Output Format

Produce a structured research report with:
- **Executive Summary** (2-3 sentences)
- **Key Findings** (bulleted list with sources)
- **Analysis** (your synthesis of the information)
- **Recommendations** (if applicable)
- **Sources Used** (list all sources consulted)

Time budget: {job.max_duration_minutes} minutes max."""


async def execute_job(job_id: str, *, autonomy_managed: bool = False) -> dict:
    """Execute a research job by submitting it to the research agent.

    Returns dict with task_id and status.
    """
    from .tasks import submit_governed_task

    job = await get_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    if job.status == JobStatus.CANCELLED:
        return {"error": f"Job {job_id} is cancelled"}

    # Update job status
    job.status = JobStatus.RUNNING
    job.last_run = time.time()
    job.run_count += 1

    r = await _get_redis()
    await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))

    # Build prompt and submit to research agent
    prompt = _build_research_prompt(job)

    try:
        submission = await submit_governed_task(
            agent="research-agent",
            prompt=prompt,
            priority="low",
            metadata={
                "source": "research_job",
                "job_id": job.id,
                "topic": job.topic,
                "_autonomy_managed": autonomy_managed,
            },
            source="research_job",
        )
        task = submission.task

        job.last_task_id = task.id
        await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))

        logger.info(
            "Research job %s executing: task=%s topic=%s",
            job.id, task.id, job.topic[:40],
        )

        return {
            "job_id": job.id,
            "task_id": task.id,
            "status": "running",
            "topic": job.topic,
        }
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))
        logger.warning("Research job %s failed to execute: %s", job.id, e)
        return {"error": str(e), "job_id": job.id}


async def complete_job(job_id: str, result: str) -> None:
    """Mark a job as completed and store the result.

    Called by the task completion handler when a research task finishes.
    """
    job = await get_job(job_id)
    if not job:
        return

    job.status = JobStatus.COMPLETED
    job.last_result = result[:5000]

    r = await _get_redis()
    await r.hset(RESEARCH_JOBS_KEY, job.id, json.dumps(job.to_dict()))

    # Store report in Qdrant knowledge collection
    await _store_report(job, result)

    logger.info("Research job %s completed: %s", job.id, job.topic[:40])


async def _store_report(job: ResearchJob, report: str) -> None:
    """Store a research report in the Qdrant knowledge collection."""
    try:
        # Get embedding for the report
        async with httpx.AsyncClient() as client:
            embed_resp = await client.post(
                f"{_LLM_BASE_URL}/embeddings",
                json={"model": "embedding", "input": f"{job.topic}: {report[:2000]}"},
                headers={"Authorization": f"Bearer {_LLM_API_KEY}"},
                timeout=15,
            )
            embed_resp.raise_for_status()
            vector = embed_resp.json()["data"][0]["embedding"]

            # Upsert to Qdrant
            point_id = str(uuid.uuid4())
            await client.put(
                f"{_QDRANT_URL}/collections/knowledge/points",
                json={
                    "points": [{
                        "id": point_id,
                        "vector": vector,
                        "payload": {
                            "text": report[:4000],
                            "title": f"Research: {job.topic}",
                            "source": f"research_job:{job.id}",
                            "category": "research",
                            "topic": job.topic,
                            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "timestamp_unix": time.time(),
                        },
                    }],
                },
                timeout=10,
            )
            logger.info("Research report stored in knowledge: %s", job.topic[:40])
    except Exception as e:
        logger.warning("Failed to store research report: %s", e)


# --- Scheduler Integration ---


async def check_scheduled_jobs(*, autonomy_managed: bool = False) -> int:
    """Check for research jobs that need to run.

    Called by the scheduler loop. Returns number of jobs triggered.
    """
    now = time.time()
    triggered = 0

    try:
        jobs = await list_jobs()
        for job_data in jobs:
            job = ResearchJob.from_dict(job_data)

            # Skip non-scheduled, cancelled, or currently running
            if job.schedule_hours <= 0:
                continue
            if job.status in (JobStatus.CANCELLED, JobStatus.RUNNING):
                continue

            # Check if interval has elapsed
            interval_seconds = job.schedule_hours * 3600
            if now - job.last_run >= interval_seconds:
                await execute_job(job.id, autonomy_managed=autonomy_managed)
                triggered += 1

    except Exception as e:
        logger.warning("Research job schedule check failed: %s", e)

    return triggered
