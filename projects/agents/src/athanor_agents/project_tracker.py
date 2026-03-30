"""Project Tracker — milestone tracking and autonomous project continuation.

Provides Redis-backed milestone management for projects, tracking progress
through acceptance criteria, linking tasks to milestones, and detecting
stalled projects that need attention.

Redis keys:
    athanor:projects:milestones:{project_id}  — hash: milestone_id -> JSON
    athanor:projects:state:{project_id}        — JSON of ProjectState
    athanor:projects:stalled                   — set of stalled project IDs
"""

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

MILESTONES_KEY_PREFIX = "athanor:projects:milestones"
STATE_KEY_PREFIX = "athanor:projects:state"
STALLED_KEY = "athanor:projects:stalled"


async def _get_redis():
    """Reuse workspace Redis connection."""
    from .workspace import get_redis
    return await get_redis()


@dataclass
class Milestone:
    id: str
    project_id: str
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    assigned_agents: list[str] = field(default_factory=list)
    status: str = "planned"  # planned | active | completed | blocked
    tasks: list[str] = field(default_factory=list)  # linked task IDs
    progress: float = 0.0  # 0-1
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Milestone":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProjectState:
    project_id: str
    milestones: list[Milestone] = field(default_factory=list)
    current_milestone: str | None = None
    total_completed: int = 0
    total_failed: int = 0
    avg_quality: float = 0.0
    last_active: float = field(default_factory=time.time)
    stalled_since: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["milestones"] = [m.to_dict() if isinstance(m, Milestone) else m for m in self.milestones]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectState":
        milestones_raw = data.pop("milestones", [])
        milestones = [
            Milestone.from_dict(m) if isinstance(m, dict) else m
            for m in milestones_raw
        ]
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        state = cls(**filtered)
        state.milestones = milestones
        return state


async def create_milestone(
    project_id: str,
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
    assigned_agents: list[str] | None = None,
    *,
    criteria: list[str] | None = None,
    agents: list[str] | None = None,
) -> Milestone:
    """Create a new milestone for a project."""
    resolved_criteria = acceptance_criteria if acceptance_criteria is not None else (criteria or [])
    resolved_agents = assigned_agents if assigned_agents is not None else (agents or [])
    milestone = Milestone(
        id=uuid.uuid4().hex[:12],
        project_id=project_id,
        title=title,
        description=description,
        acceptance_criteria=resolved_criteria,
        assigned_agents=resolved_agents,
    )

    r = await _get_redis()
    key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
    await r.hset(key, milestone.id, json.dumps(milestone.to_dict()))

    # Update project state
    state = await get_project_state(project_id)
    state.milestones.append(milestone)
    if state.current_milestone is None:
        state.current_milestone = milestone.id
        milestone.status = "active"
        await r.hset(key, milestone.id, json.dumps(milestone.to_dict()))
    state.last_active = time.time()
    await _save_project_state(state)

    logger.info(
        "Milestone %s created for project %s: %s",
        milestone.id, project_id, title,
    )
    return milestone


async def get_milestones(project_id: str) -> list[Milestone]:
    """Get all milestones for a project, ordered by creation time."""
    try:
        r = await _get_redis()
        key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
        raw = await r.hgetall(key)
        milestones = [Milestone.from_dict(json.loads(v)) for v in raw.values()]
        milestones.sort(key=lambda m: m.created_at)
        return milestones
    except Exception as e:
        logger.warning("Failed to get milestones for %s: %s", project_id, e)
        return []


async def update_milestone(
    project_id: str,
    milestone_id: str,
    **updates,
) -> Milestone | None:
    """Update a milestone's fields. Returns updated milestone or None if not found."""
    try:
        r = await _get_redis()
        key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
        raw = await r.hget(key, milestone_id)
        if not raw:
            return None

        milestone = Milestone.from_dict(json.loads(raw))
        for field_name, value in updates.items():
            if field_name in milestone.__dataclass_fields__ and field_name not in ("id", "project_id"):
                setattr(milestone, field_name, value)

        await r.hset(key, milestone_id, json.dumps(milestone.to_dict()))

        # Refresh state
        state = await get_project_state(project_id)
        state.last_active = time.time()
        await _save_project_state(state)

        logger.info("Milestone %s updated for project %s", milestone_id, project_id)
        return milestone
    except Exception as e:
        logger.warning("Failed to update milestone %s: %s", milestone_id, e)
        return None


async def on_task_complete(
    task_id: str,
    project_id: str,
    quality_score: float,
) -> None:
    """Handle task completion — update milestone progress and advance if complete.

    Called when a task linked to a milestone finishes. Updates quality tracking,
    checks if the current milestone's acceptance criteria are met, and advances
    to the next milestone if so.
    """
    state = await get_project_state(project_id)
    state.total_completed += 1
    # Running average for quality
    total = state.total_completed + state.total_failed
    state.avg_quality = (
        (state.avg_quality * (total - 1) + quality_score) / total
        if total > 0 else quality_score
    )
    state.last_active = time.time()
    state.stalled_since = None

    # Remove from stalled set if present
    try:
        r = await _get_redis()
        await r.srem(STALLED_KEY, project_id)
    except Exception as e:
        logger.debug("Failed to remove %s from stalled set: %s", project_id, e)

    # Find and update the current milestone
    if state.current_milestone:
        milestone = await _get_milestone(project_id, state.current_milestone)
        if milestone and task_id not in milestone.tasks:
            milestone.tasks.append(task_id)
            # Progress = tasks completed / acceptance criteria count
            criteria_count = max(len(milestone.acceptance_criteria), 1)
            milestone.progress = min(1.0, len(milestone.tasks) / criteria_count)

            if milestone.progress >= 1.0:
                milestone.status = "completed"
                milestone.completed_at = time.time()
                logger.info(
                    "Milestone %s completed for project %s: %s",
                    milestone.id, project_id, milestone.title,
                )
                # Advance to next milestone
                await _advance_to_next_milestone(project_id, state)

            r = await _get_redis()
            key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
            await r.hset(key, milestone.id, json.dumps(milestone.to_dict()))

    await _save_project_state(state)


async def get_project_state(project_id: str) -> ProjectState:
    """Get or create project state."""
    try:
        r = await _get_redis()
        key = f"{STATE_KEY_PREFIX}:{project_id}"
        raw = await r.get(key)
        if raw:
            return ProjectState.from_dict(json.loads(raw))
    except Exception as e:
        logger.warning("Failed to get project state for %s: %s", project_id, e)

    # Return fresh state if none exists
    return ProjectState(project_id=project_id)


async def get_stalled_projects(threshold_hours: float = 24) -> list[str]:
    """Get project IDs that have been inactive beyond the threshold.

    Checks all projects with state, marks those inactive for longer than
    threshold_hours as stalled, and returns their IDs.
    """
    threshold_seconds = threshold_hours * 3600
    now = time.time()
    stalled = []

    try:
        r = await _get_redis()

        # Scan for all project state keys
        cursor = 0
        state_keys = []
        while True:
            cursor, keys = await r.scan(cursor, match=f"{STATE_KEY_PREFIX}:*", count=100)
            state_keys.extend(keys)
            if cursor == 0:
                break

        for key in state_keys:
            raw = await r.get(key)
            if not raw:
                continue
            state = ProjectState.from_dict(json.loads(raw))
            inactive_duration = now - state.last_active

            if inactive_duration > threshold_seconds:
                stalled.append(state.project_id)
                if state.stalled_since is None:
                    state.stalled_since = now
                    await _save_project_state(state)
                await r.sadd(STALLED_KEY, state.project_id)
            else:
                # No longer stalled
                if state.stalled_since is not None:
                    state.stalled_since = None
                    await _save_project_state(state)
                await r.srem(STALLED_KEY, state.project_id)

    except Exception as e:
        logger.warning("Failed to check stalled projects: %s", e)

    return stalled


async def advance_project(project_id: str) -> dict:
    """Trigger an advancement check for a project.

    Returns a summary of the current state and any advancement that occurred.
    """
    state = await get_project_state(project_id)
    result = {
        "project_id": project_id,
        "current_milestone": state.current_milestone,
        "total_completed": state.total_completed,
        "total_failed": state.total_failed,
        "avg_quality": round(state.avg_quality, 3),
        "advanced": False,
    }

    if not state.current_milestone:
        result["status"] = "no_active_milestone"
        return result

    milestone = await _get_milestone(project_id, state.current_milestone)
    if not milestone:
        result["status"] = "milestone_not_found"
        return result

    result["milestone_title"] = milestone.title
    result["milestone_progress"] = milestone.progress
    result["milestone_status"] = milestone.status

    if milestone.status == "completed":
        advanced = await _advance_to_next_milestone(project_id, state)
        result["advanced"] = advanced
        if advanced:
            result["new_milestone"] = state.current_milestone
            result["status"] = "advanced"
        else:
            result["status"] = "all_milestones_complete"
        await _save_project_state(state)
    else:
        result["status"] = "in_progress"

    return result


# --- Internal helpers ---


async def _get_milestone(project_id: str, milestone_id: str) -> Milestone | None:
    """Fetch a single milestone from Redis."""
    try:
        r = await _get_redis()
        key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
        raw = await r.hget(key, milestone_id)
        if raw:
            return Milestone.from_dict(json.loads(raw))
    except Exception as e:
        logger.warning("Failed to get milestone %s: %s", milestone_id, e)
    return None


async def _save_project_state(state: ProjectState) -> None:
    """Persist project state to Redis."""
    try:
        r = await _get_redis()
        key = f"{STATE_KEY_PREFIX}:{state.project_id}"
        await r.set(key, json.dumps(state.to_dict()))
    except Exception as e:
        logger.warning("Failed to save project state for %s: %s", state.project_id, e)


async def _advance_to_next_milestone(project_id: str, state: ProjectState) -> bool:
    """Advance to the next planned milestone. Returns True if advanced."""
    milestones = await get_milestones(project_id)
    for m in milestones:
        if m.status == "planned":
            m.status = "active"
            state.current_milestone = m.id

            r = await _get_redis()
            key = f"{MILESTONES_KEY_PREFIX}:{project_id}"
            await r.hset(key, m.id, json.dumps(m.to_dict()))

            logger.info(
                "Project %s advanced to milestone %s: %s",
                project_id, m.id, m.title,
            )
            return True

    # No more milestones to advance to
    state.current_milestone = None
    return False
