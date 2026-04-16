"""Preference Learning — model selection from feedback history.

Tracks per-model, per-task-type success rates and recommends models
based on learned performance data. Scores combine:
  success_rate * 0.5 + experience * 0.2 + speed * 0.2 + low_regenerations * 0.1

Ported from: reference/hydra/src/hydra_tools/preference_learning.py
Adapted for Athanor: Redis-only persistence (single user), uses router.py TaskType,
LiteLLM model aliases instead of direct model names.
"""

import json
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PREFERENCES_KEY = "athanor:preferences"

# Minimum interactions before a model's score is trusted
MIN_SAMPLES = 5

# Latency normalization ceiling (ms) — anything above this gets speed=0
LATENCY_CEILING_MS = 30_000


@dataclass
class ModelStats:
    """Per-model, per-task-type performance statistics."""
    model: str
    task_type: str
    total_uses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    regenerations: int = 0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.positive_feedback + self.negative_feedback
        if total == 0:
            return 0.5  # No data → neutral
        return self.positive_feedback / total

    @property
    def score(self) -> float:
        """Composite preference score.

        success_rate * 0.5 + experience * 0.2 + speed * 0.2 + low_regenerations * 0.1
        """
        # Experience: saturates at 100 uses
        experience = min(self.total_uses / 100.0, 1.0)

        # Speed: 1.0 for instant, 0.0 for >= LATENCY_CEILING_MS
        speed = max(0.0, 1.0 - self.avg_latency_ms / LATENCY_CEILING_MS)

        # Low regenerations: 1.0 for zero regens, 0.0 if every response regenerated
        regen_rate = self.regenerations / max(self.total_uses, 1)
        low_regens = max(0.0, 1.0 - regen_rate)

        return (
            self.success_rate * 0.5
            + experience * 0.2
            + speed * 0.2
            + low_regens * 0.1
        )

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "task_type": self.task_type,
            "total_uses": self.total_uses,
            "positive_feedback": self.positive_feedback,
            "negative_feedback": self.negative_feedback,
            "regenerations": self.regenerations,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "success_rate": round(self.success_rate, 3),
            "score": round(self.score, 3),
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelStats":
        return cls(
            model=data["model"],
            task_type=data["task_type"],
            total_uses=data.get("total_uses", 0),
            positive_feedback=data.get("positive_feedback", 0),
            negative_feedback=data.get("negative_feedback", 0),
            regenerations=data.get("regenerations", 0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
            last_used=data.get("last_used", 0.0),
        )


def _stats_key(model: str, task_type: str) -> str:
    """Redis hash field key for a model+task_type pair."""
    return f"{model}:{task_type}"


async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def load_all_stats() -> dict[str, ModelStats]:
    """Load all preference stats from Redis."""
    try:
        r = await _get_redis()
        raw = await r.hgetall(PREFERENCES_KEY)
        stats = {}
        for field_key, data in raw.items():
            key = field_key.decode() if isinstance(field_key, bytes) else field_key
            val = data.decode() if isinstance(data, bytes) else data
            ms = ModelStats.from_dict(json.loads(val))
            stats[key] = ms
        return stats
    except Exception as e:
        logger.warning("Failed to load preference stats: %s", e)
        return {}


async def _save_stats(key: str, stats: ModelStats) -> None:
    """Save a single stats entry to Redis."""
    try:
        r = await _get_redis()
        await r.hset(PREFERENCES_KEY, key, json.dumps(stats.to_dict()))
    except Exception as e:
        logger.warning("Failed to save preference stats for %s: %s", key, e)


async def record_outcome(
    model: str,
    task_type: str,
    latency_ms: float = 0.0,
    feedback: str | None = None,
) -> ModelStats:
    """Record an interaction outcome for preference learning.

    Args:
        model: LiteLLM model alias used (e.g., "reasoning", "fast").
        task_type: Router TaskType value (e.g., "coding", "creative").
        latency_ms: Response latency in milliseconds.
        feedback: One of "positive", "negative", "regenerate", or None.

    Returns:
        Updated ModelStats for this model+task_type.
    """
    key = _stats_key(model, task_type)

    # Load existing or create new
    all_stats = await load_all_stats()
    stats = all_stats.get(key, ModelStats(model=model, task_type=task_type))

    # Update counts
    stats.total_uses += 1
    stats.last_used = time.time()

    # Rolling average latency (EMA with alpha=0.1)
    if stats.avg_latency_ms == 0.0:
        stats.avg_latency_ms = latency_ms
    elif latency_ms > 0:
        stats.avg_latency_ms = stats.avg_latency_ms * 0.9 + latency_ms * 0.1

    # Update feedback
    if feedback == "positive":
        stats.positive_feedback += 1
    elif feedback == "negative":
        stats.negative_feedback += 1
    elif feedback == "regenerate":
        stats.regenerations += 1

    # Persist
    await _save_stats(key, stats)

    logger.debug(
        "Preference: %s/%s → uses=%d, score=%.3f, feedback=%s",
        model, task_type, stats.total_uses, stats.score, feedback,
    )

    return stats


async def get_preferred_model(
    task_type: str,
    available_models: list[str] | None = None,
) -> str | None:
    """Get the preferred model for a task type based on learned preferences.

    Args:
        task_type: Router TaskType value.
        available_models: Optional list of eligible model aliases.

    Returns:
        Best model alias, or None if insufficient data to recommend.
    """
    all_stats = await load_all_stats()

    # Filter to stats matching this task_type with enough samples
    candidates: list[ModelStats] = []
    for key, stats in all_stats.items():
        if stats.task_type != task_type:
            continue
        if stats.total_uses < MIN_SAMPLES:
            continue
        if available_models and stats.model not in available_models:
            continue
        candidates.append(stats)

    if not candidates:
        return None

    # Return highest scoring model
    best = max(candidates, key=lambda s: s.score)
    logger.debug(
        "Preference recommendation: %s for %s (score=%.3f, uses=%d)",
        best.model, task_type, best.score, best.total_uses,
    )
    return best.model


async def get_all_preferences() -> dict:
    """Get all preference stats, grouped by task type.

    Returns dict suitable for API response.
    """
    all_stats = await load_all_stats()

    by_task: dict[str, list[dict]] = {}
    for stats in all_stats.values():
        if stats.task_type not in by_task:
            by_task[stats.task_type] = []
        by_task[stats.task_type].append(stats.to_dict())

    # Sort each task type's models by score descending
    for task_type in by_task:
        by_task[task_type].sort(key=lambda s: s["score"], reverse=True)

    return {
        "task_types": by_task,
        "total_entries": len(all_stats),
        "min_samples": MIN_SAMPLES,
    }
