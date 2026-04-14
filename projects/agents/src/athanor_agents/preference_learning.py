"""
Athanor Preference Learning System

Tracks user preferences, model choices, and feedback to continuously improve
recommendations and system behavior.

Ported from Hydra's preference_learning.py, adapted for Athanor's stack:
- Storage: Redis (redis.asyncio) for fast state, Qdrant for vector similarity
- Inference: LiteLLM at VAULT:4000
- All methods async
- Singleton pattern with get_preference_learner()
- FastAPI router factory: create_preference_router()

Features:
- Tracks model usage patterns and learns from explicit feedback
- Adjusts routing based on past performance per task type
- Stores preferences in Redis with Qdrant vector backup
- Athanor-specific preference types: model, agent, creative style
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
import redis.asyncio as aioredis

from .config import settings

logger = logging.getLogger(__name__)

# Redis key prefix
_REDIS_PREFIX = "athanor:prefs"

# Qdrant collection for preference vectors
_QDRANT_COLLECTION = "preferences"
_QDRANT_URL = settings.qdrant_url


# ── Enums ──────────────────────────────────────────────────────────────


class FeedbackType(Enum):
    """Types of user feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    REGENERATE = "regenerate"
    EDIT = "edit"


class TaskType(Enum):
    """Categories of tasks — superset of routing.TaskType for preference tracking."""
    GENERAL = "general"
    CODE = "code"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    RESEARCH = "research"
    SYSTEM = "system"
    HOME = "home"
    MEDIA = "media"


class PreferenceCategory(Enum):
    """Athanor-specific preference categories."""
    MODEL = "model"          # Which model for which task
    AGENT = "agent"          # Which agent behavior preferences
    CREATIVE_STYLE = "creative_style"  # Creative output preferences
    RESPONSE_STYLE = "response_style"  # Verbosity, tone, etc.
    ROUTING = "routing"      # Routing weight overrides


# ── Data structures ────────────────────────────────────────────────────


@dataclass
class Interaction:
    """Record of a single interaction."""
    id: str
    timestamp: str
    prompt_hash: str
    prompt_length: int
    model: str
    response_length: int
    latency_ms: int
    task_type: str
    feedback: str | None = None
    feedback_timestamp: str | None = None
    agent: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ModelStats:
    """Statistics for a model."""
    model: str
    total_uses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    regenerations: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_used: str | None = None


@dataclass
class AgentPreferences:
    """Per-agent behavior preferences."""
    agent_id: str
    preferred_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class CreativeStylePreferences:
    """Creative output style preferences."""
    tone: str = "balanced"             # casual, balanced, formal, poetic
    verbosity: str = "balanced"        # terse, balanced, detailed
    genre_preferences: list[str] = field(default_factory=list)
    nsfw_enabled: bool = True
    preferred_formats: list[str] = field(default_factory=list)


@dataclass
class UserPreferences:
    """User's learned preferences."""
    preferred_models: dict[str, str] = field(default_factory=dict)  # task_type -> model
    model_stats: dict[str, ModelStats] = field(default_factory=dict)
    style_preferences: dict[str, Any] = field(default_factory=dict)
    agent_preferences: dict[str, AgentPreferences] = field(default_factory=dict)
    creative_style: CreativeStylePreferences = field(default_factory=CreativeStylePreferences)
    updated_at: str = ""


# ── Defaults ───────────────────────────────────────────────────────────

# Athanor model defaults by task type (LiteLLM aliases)
DEFAULT_MODELS: dict[TaskType, str] = {
    TaskType.GENERAL: "coder",
    TaskType.CODE: "coding",
    TaskType.CREATIVE: "creative",
    TaskType.ANALYSIS: "reasoning",
    TaskType.TRANSLATION: "coder",
    TaskType.SUMMARIZATION: "coder",
    TaskType.RESEARCH: "reasoning",
    TaskType.SYSTEM: "coder",
    TaskType.HOME: "coder",
    TaskType.MEDIA: "coder",
}

DEFAULT_STYLE: dict[str, Any] = {
    "verbosity": "concise",
    "tone": "professional",
    "code_style": "modern",
    "explanation_depth": "medium",
}


# ── PreferenceLearner ──────────────────────────────────────────────────


class PreferenceLearner:
    """Learns and applies user preferences for model selection and behavior."""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self._redis: aioredis.Redis | None = None

        # In-memory cache
        self._preferences_cache: UserPreferences | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl = 300  # 5 minutes

        # Model weights for routing decisions
        self._model_weights: dict[str, dict[str, float]] = {}

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url,
                password=settings.redis_password or None,
                decode_responses=True,
            )
        return self._redis

    def _redis_key(self, key_type: str) -> str:
        """Generate Redis key."""
        return f"{_REDIS_PREFIX}:{self.user_id}:{key_type}"

    def _hash_prompt(self, prompt: str) -> str:
        """Create privacy-preserving hash of prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _classify_task(self, prompt: str) -> TaskType:
        """Classify the task type from prompt content."""
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["```", "code", "function", "class", "debug", "implement", "refactor"]):
            return TaskType.CODE
        if any(kw in prompt_lower for kw in ["write a story", "creative", "poem", "fiction", "roleplay", "scene"]):
            return TaskType.CREATIVE
        if any(kw in prompt_lower for kw in ["analyze", "compare", "evaluate", "assess", "critique"]):
            return TaskType.ANALYSIS
        if any(kw in prompt_lower for kw in ["translate", "in spanish", "in french", "to english"]):
            return TaskType.TRANSLATION
        if any(kw in prompt_lower for kw in ["summarize", "tldr", "brief", "key points"]):
            return TaskType.SUMMARIZATION
        if any(kw in prompt_lower for kw in ["research", "investigate", "find out", "look up"]):
            return TaskType.RESEARCH
        if any(kw in prompt_lower for kw in ["lights", "thermostat", "home assistant", "automation"]):
            return TaskType.HOME
        if any(kw in prompt_lower for kw in ["movie", "tv show", "plex", "sonarr", "radarr", "music"]):
            return TaskType.MEDIA
        if any(kw in prompt_lower for kw in ["docker", "ansible", "deploy", "server", "vllm", "litellm"]):
            return TaskType.SYSTEM

        return TaskType.GENERAL

    # ── Redis persistence ──────────────────────────────────────────────

    async def _save_to_redis(self, key_type: str, data: dict, ttl: int = 86400) -> bool:
        """Save data to Redis."""
        try:
            r = await self._get_redis()
            key = self._redis_key(key_type)
            await r.set(key, json.dumps(data, default=str), ex=ttl)
            return True
        except Exception as e:
            logger.warning("Failed to save to Redis: %s", e)
            return False

    async def _load_from_redis(self, key_type: str) -> dict | None:
        """Load data from Redis."""
        try:
            r = await self._get_redis()
            key = self._redis_key(key_type)
            raw = await r.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Failed to load from Redis: %s", e)
        return None

    # ── Qdrant vector storage ──────────────────────────────────────────

    async def _store_preference_vector(
        self,
        preference_id: str,
        payload: dict,
    ) -> bool:
        """Store preference data as a point in Qdrant."""
        try:
            # Get embedding from LiteLLM
            async with httpx.AsyncClient(timeout=10.0) as client:
                embed_resp = await client.post(
                    f"{settings.llm_base_url}/embeddings",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": "embedding",
                        "input": json.dumps(payload, default=str)[:500],
                    },
                )
                if embed_resp.status_code != 200:
                    return False
                vector = embed_resp.json()["data"][0]["embedding"]

                # Upsert to Qdrant
                point_id = int(hashlib.md5(preference_id.encode()).hexdigest()[:12], 16)
                await client.put(
                    f"{_QDRANT_URL}/collections/{_QDRANT_COLLECTION}/points",
                    json={
                        "points": [{
                            "id": point_id,
                            "vector": vector,
                            "payload": {
                                "preference_id": preference_id,
                                "user_id": self.user_id,
                                **payload,
                            },
                        }],
                    },
                )
                return True
        except Exception as e:
            logger.warning("Failed to store preference vector: %s", e)
            return False

    # ── Core operations ────────────────────────────────────────────────

    async def record_interaction(
        self,
        prompt: str,
        model: str,
        response: str,
        latency_ms: int = 0,
        feedback: FeedbackType | str | None = None,
        agent: str | None = None,
        metadata: dict | None = None,
    ) -> Interaction:
        """Record an interaction for learning."""
        task_type = self._classify_task(prompt)

        interaction = Interaction(
            id=f"{int(time.time() * 1000)}-{self._hash_prompt(prompt)[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            prompt_hash=self._hash_prompt(prompt),
            prompt_length=len(prompt),
            model=model,
            response_length=len(response),
            latency_ms=latency_ms,
            task_type=task_type.value,
            feedback=feedback.value if isinstance(feedback, FeedbackType) else feedback,
            agent=agent,
            metadata=metadata or {},
        )

        # Update in-memory stats
        await self._update_model_stats(model, task_type, latency_ms, feedback)

        # Persist interaction to Redis (fire-and-forget style but awaited)
        await self._save_to_redis(
            f"interaction:{interaction.id}",
            asdict(interaction),
            ttl=604800,  # 7 days
        )

        # Append to recent interactions list
        try:
            r = await self._get_redis()
            key = self._redis_key("recent_interactions")
            await r.lpush(key, json.dumps(asdict(interaction), default=str))
            await r.ltrim(key, 0, 999)  # Keep last 1000
        except Exception as e:
            logger.debug("Preference interaction store failed: %s", e)

        return interaction

    async def _update_model_stats(
        self,
        model: str,
        task_type: TaskType,
        latency_ms: int,
        feedback: FeedbackType | str | None,
    ) -> None:
        """Update running statistics for a model."""
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences()

        if model not in self._preferences_cache.model_stats:
            self._preferences_cache.model_stats[model] = ModelStats(model=model)

        stats = self._preferences_cache.model_stats[model]
        stats.total_uses += 1
        stats.last_used = datetime.now(timezone.utc).isoformat()

        # Rolling average latency
        if stats.avg_latency_ms == 0:
            stats.avg_latency_ms = latency_ms
        else:
            stats.avg_latency_ms = (stats.avg_latency_ms * 0.9) + (latency_ms * 0.1)

        # Feedback counts
        if feedback:
            feedback_val = feedback.value if isinstance(feedback, FeedbackType) else feedback
            if feedback_val == "positive":
                stats.positive_feedback += 1
            elif feedback_val == "negative":
                stats.negative_feedback += 1
            elif feedback_val == "regenerate":
                stats.regenerations += 1

        # Recalculate success rate
        total_feedback = stats.positive_feedback + stats.negative_feedback
        if total_feedback > 0:
            stats.success_rate = stats.positive_feedback / total_feedback

        self._preferences_cache.updated_at = datetime.now(timezone.utc).isoformat()

        # Persist updated preferences
        await self._persist_preferences()

    async def _persist_preferences(self) -> None:
        """Persist current preferences cache to Redis."""
        if self._preferences_cache is None:
            return
        data = self.export_preferences()
        await self._save_to_redis("preferences", data, ttl=0)  # No expiry

    async def load_preferences(self) -> UserPreferences:
        """Load preferences from Redis, or return defaults."""
        now = time.time()
        if self._preferences_cache and (now - self._cache_timestamp) < self._cache_ttl:
            return self._preferences_cache

        data = await self._load_from_redis("preferences")
        if data:
            self.import_preferences(data)
        else:
            self._preferences_cache = UserPreferences(
                style_preferences=DEFAULT_STYLE.copy(),
            )

        self._cache_timestamp = now
        return self._preferences_cache  # type: ignore[return-value]

    async def record_feedback(
        self,
        interaction_id: str,
        feedback: FeedbackType | str,
    ) -> bool:
        """Record feedback for a previous interaction."""
        feedback_val = feedback.value if isinstance(feedback, FeedbackType) else feedback

        # Load the interaction from Redis
        data = await self._load_from_redis(f"interaction:{interaction_id}")
        if not data:
            return False

        data["feedback"] = feedback_val
        data["feedback_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Update the stored interaction
        await self._save_to_redis(f"interaction:{interaction_id}", data, ttl=604800)

        # Update model stats with the new feedback
        model = data.get("model", "")
        task_type_str = data.get("task_type", "general")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.GENERAL

        await self._update_model_stats(model, task_type, 0, feedback_val)
        return True

    async def get_preferred_model(
        self,
        task_type: TaskType | str | None = None,
        prompt: str | None = None,
        available_models: list[str] | None = None,
    ) -> str:
        """Get the preferred model based on learned preferences."""
        # Ensure preferences are loaded
        await self.load_preferences()

        # Determine task type
        if task_type is None and prompt:
            task_type = self._classify_task(prompt)
        elif isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                task_type = TaskType.GENERAL
        elif task_type is None:
            task_type = TaskType.GENERAL

        # Check explicit preferences
        if self._preferences_cache and task_type.value in self._preferences_cache.preferred_models:
            preferred = self._preferences_cache.preferred_models[task_type.value]
            if available_models is None or preferred in available_models:
                return preferred

        # Score models based on stats
        model_scores: dict[str, float] = {}
        if self._preferences_cache:
            for model, stats in self._preferences_cache.model_stats.items():
                if available_models and model not in available_models:
                    continue
                score = (
                    stats.success_rate * 0.5
                    + min(stats.total_uses / 100, 1.0) * 0.2
                    + (1.0 - min(stats.avg_latency_ms / 10000, 1.0)) * 0.2
                    + (1.0 - min(stats.regenerations / max(stats.total_uses, 1), 1.0)) * 0.1
                )
                model_scores[model] = score

        if model_scores:
            return max(model_scores, key=model_scores.get)  # type: ignore[arg-type]

        # Athanor defaults (LiteLLM aliases)
        default = DEFAULT_MODELS.get(task_type, "fast")
        if available_models and default not in available_models:
            return available_models[0] if available_models else "fast"
        return default

    async def get_style_preferences(self) -> dict[str, Any]:
        """Get learned style preferences."""
        await self.load_preferences()
        if self._preferences_cache and self._preferences_cache.style_preferences:
            return self._preferences_cache.style_preferences
        return DEFAULT_STYLE.copy()

    async def set_style_preference(self, key: str, value: Any) -> None:
        """Set a specific style preference."""
        await self.load_preferences()
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences(style_preferences=DEFAULT_STYLE.copy())
        self._preferences_cache.style_preferences[key] = value
        self._preferences_cache.updated_at = datetime.now(timezone.utc).isoformat()
        await self._persist_preferences()

    async def set_preferred_model(self, task_type: str, model: str) -> None:
        """Explicitly set the preferred model for a task type."""
        await self.load_preferences()
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences()
        self._preferences_cache.preferred_models[task_type] = model
        self._preferences_cache.updated_at = datetime.now(timezone.utc).isoformat()
        await self._persist_preferences()

    async def set_agent_preferences(self, agent_id: str, prefs: dict) -> None:
        """Set preferences for a specific agent."""
        await self.load_preferences()
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences()
        self._preferences_cache.agent_preferences[agent_id] = AgentPreferences(
            agent_id=agent_id,
            preferred_model=prefs.get("preferred_model"),
            temperature=prefs.get("temperature"),
            max_tokens=prefs.get("max_tokens"),
            system_prompt_overrides=prefs.get("system_prompt_overrides", {}),
        )
        self._preferences_cache.updated_at = datetime.now(timezone.utc).isoformat()
        await self._persist_preferences()

    async def get_agent_preferences(self, agent_id: str) -> AgentPreferences | None:
        """Get preferences for a specific agent."""
        await self.load_preferences()
        if self._preferences_cache:
            return self._preferences_cache.agent_preferences.get(agent_id)
        return None

    async def set_creative_style(self, **kwargs: Any) -> None:
        """Update creative style preferences."""
        await self.load_preferences()
        if self._preferences_cache is None:
            self._preferences_cache = UserPreferences()
        style = self._preferences_cache.creative_style
        for k, v in kwargs.items():
            if hasattr(style, k):
                setattr(style, k, v)
        self._preferences_cache.updated_at = datetime.now(timezone.utc).isoformat()
        await self._persist_preferences()

    async def get_creative_style(self) -> CreativeStylePreferences:
        """Get creative style preferences."""
        await self.load_preferences()
        if self._preferences_cache:
            return self._preferences_cache.creative_style
        return CreativeStylePreferences()

    def export_preferences(self) -> dict:
        """Export all preferences as a serializable dictionary."""
        if self._preferences_cache is None:
            return {}
        return {
            "user_id": self.user_id,
            "preferred_models": self._preferences_cache.preferred_models,
            "model_stats": {
                model: asdict(stats)
                for model, stats in self._preferences_cache.model_stats.items()
            },
            "style_preferences": self._preferences_cache.style_preferences,
            "agent_preferences": {
                agent_id: asdict(prefs)
                for agent_id, prefs in self._preferences_cache.agent_preferences.items()
            },
            "creative_style": asdict(self._preferences_cache.creative_style),
            "updated_at": self._preferences_cache.updated_at,
        }

    def import_preferences(self, data: dict) -> bool:
        """Import preferences from a dictionary."""
        try:
            self._preferences_cache = UserPreferences(
                preferred_models=data.get("preferred_models", {}),
                model_stats={
                    model: ModelStats(**stats_data)
                    for model, stats_data in data.get("model_stats", {}).items()
                },
                style_preferences=data.get("style_preferences", DEFAULT_STYLE.copy()),
                agent_preferences={
                    agent_id: AgentPreferences(**prefs_data)
                    for agent_id, prefs_data in data.get("agent_preferences", {}).items()
                },
                creative_style=CreativeStylePreferences(
                    **data.get("creative_style", {})
                ) if data.get("creative_style") else CreativeStylePreferences(),
                updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            )
            return True
        except Exception as e:
            logger.error("Failed to import preferences: %s", e)
            return False

    async def close(self) -> None:
        """Clean up Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# ── Singleton ──────────────────────────────────────────────────────────

_instance: PreferenceLearner | None = None


def get_preference_learner(user_id: str = "default") -> PreferenceLearner:
    """Get the singleton PreferenceLearner instance."""
    global _instance
    if _instance is None:
        _instance = PreferenceLearner(user_id=user_id)
    return _instance


# ── FastAPI router factory ─────────────────────────────────────────────


def create_preference_router():
    """Create FastAPI router for preference learning endpoints."""
    from fastapi import APIRouter, HTTPException, Request
    from pydantic import BaseModel
    from starlette.responses import JSONResponse

    from .operator_contract import (
        build_operator_action,
        emit_operator_audit_event,
        require_operator_action,
    )

    router = APIRouter(prefix="/v1/preferences/learning", tags=["preference-learning"])
    learner = get_preference_learner()

    async def _load_operator_body(
        request: Request,
        *,
        route: str,
        action_class: str,
        default_reason: str,
    ):
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        if not isinstance(body, dict):
            body = {}

        candidate = build_operator_action(body, default_reason=default_reason)
        try:
            action = require_operator_action(body, action_class=action_class, default_reason=default_reason)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            status_code = getattr(exc, "status_code", 400)
            await emit_operator_audit_event(
                service="agent-server",
                route=route,
                action_class=action_class,
                decision="denied",
                status_code=status_code,
                action=candidate,
                detail=str(detail),
            )
            return None, None, JSONResponse(status_code=status_code, content={"error": detail})

        return body, action, None

    # ── Request models ─────────────────────────────────────────────

    class InteractionRequest(BaseModel):
        prompt: str
        model: str
        response: str
        latency_ms: int = 0
        feedback: str | None = None
        agent: str | None = None
        metadata: dict | None = None

    class FeedbackRequest(BaseModel):
        interaction_id: str
        feedback: str

    class ModelRecommendationRequest(BaseModel):
        task_type: str | None = None
        prompt: str | None = None
        available_models: list[str] | None = None

    class StylePreferenceRequest(BaseModel):
        key: str
        value: Any

    class PreferredModelRequest(BaseModel):
        task_type: str
        model: str

    class AgentPreferencesRequest(BaseModel):
        agent_id: str
        preferred_model: str | None = None
        temperature: float | None = None
        max_tokens: int | None = None
        system_prompt_overrides: dict[str, str] | None = None

    class CreativeStyleRequest(BaseModel):
        tone: str | None = None
        verbosity: str | None = None
        genre_preferences: list[str] | None = None
        nsfw_enabled: bool | None = None
        preferred_formats: list[str] | None = None

    class ImportRequest(BaseModel):
        data: dict

    # ── Endpoints ──────────────────────────────────────────────────

    @router.post("/interaction")
    async def record_interaction(request: Request, req: InteractionRequest):
        """Record an interaction for preference learning."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/interaction",
            action_class="operator",
            default_reason="Record preference-learning interaction",
        )
        if denial:
            return denial
        interaction = await learner.record_interaction(
            prompt=req.prompt,
            model=req.model,
            response=req.response,
            latency_ms=req.latency_ms,
            feedback=req.feedback,
            agent=req.agent,
            metadata=req.metadata,
        )
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/interaction",
            action_class="operator",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Recorded preference-learning interaction {interaction.id}",
            target=interaction.id,
            metadata={"model": req.model, "task_type": interaction.task_type},
        )
        return {"id": interaction.id, "task_type": interaction.task_type}

    @router.post("/feedback")
    async def record_feedback(request: Request, req: FeedbackRequest):
        """Record feedback for a previous interaction."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/feedback",
            action_class="operator",
            default_reason="Record preference-learning feedback",
        )
        if denial:
            return denial
        success = await learner.record_feedback(req.interaction_id, req.feedback)
        if not success:
            await emit_operator_audit_event(
                service="agent-server",
                route="/v1/preferences/learning/feedback",
                action_class="operator",
                decision="denied",
                status_code=404,
                action=action,
                detail="Interaction not found",
                target=req.interaction_id,
            )
            raise HTTPException(status_code=404, detail="Interaction not found")
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/feedback",
            action_class="operator",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Recorded preference feedback for {req.interaction_id}",
            target=req.interaction_id,
            metadata={"feedback": req.feedback},
        )
        return {"status": "recorded"}

    @router.post("/recommend")
    async def get_recommendation(req: ModelRecommendationRequest):
        """Get model recommendation based on learned preferences."""
        model = await learner.get_preferred_model(
            task_type=req.task_type,
            prompt=req.prompt,
            available_models=req.available_models,
        )
        return {"recommended_model": model}

    @router.get("/export")
    async def export_prefs():
        """Export all preferences."""
        await learner.load_preferences()
        return learner.export_preferences()

    @router.post("/import")
    async def import_prefs(request: Request, req: ImportRequest):
        """Import preferences from a dictionary."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/import",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        success = learner.import_preferences(req.data)
        if success:
            await learner._persist_preferences()
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/import",
            action_class="admin",
            decision="accepted" if success else "denied",
            status_code=200 if success else 400,
            action=action,
            detail="Imported preference snapshot" if success else "Failed to import preference snapshot",
            metadata={"key_count": len(req.data)},
        )
        return {"status": "imported" if success else "failed"}

    @router.get("/style")
    async def get_style():
        """Get response style preferences."""
        return await learner.get_style_preferences()

    @router.put("/style")
    async def set_style(request: Request, req: StylePreferenceRequest):
        """Set a style preference."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/style",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        await learner.set_style_preference(req.key, req.value)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/style",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Updated preference style key {req.key}",
            target=req.key,
        )
        return {"status": "updated"}

    @router.put("/preferred-model")
    async def set_preferred_model(request: Request, req: PreferredModelRequest):
        """Explicitly set preferred model for a task type."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/preferred-model",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        await learner.set_preferred_model(req.task_type, req.model)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/preferred-model",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Updated preferred model for task_type={req.task_type}",
            target=req.task_type,
            metadata={"model": req.model},
        )
        return {"status": "updated"}

    @router.get("/agent/{agent_id}")
    async def get_agent_prefs(agent_id: str):
        """Get preferences for a specific agent."""
        prefs = await learner.get_agent_preferences(agent_id)
        if prefs is None:
            return {"agent_id": agent_id, "preferences": None}
        return {"agent_id": agent_id, "preferences": asdict(prefs)}

    @router.put("/agent")
    async def set_agent_prefs(request: Request, req: AgentPreferencesRequest):
        """Set preferences for a specific agent."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/agent",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        await learner.set_agent_preferences(
            req.agent_id,
            {
                "preferred_model": req.preferred_model,
                "temperature": req.temperature,
                "max_tokens": req.max_tokens,
                "system_prompt_overrides": req.system_prompt_overrides or {},
            },
        )
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/agent",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Updated preference-learning agent profile {req.agent_id}",
            target=req.agent_id,
        )
        return {"status": "updated"}

    @router.get("/creative-style")
    async def get_creative():
        """Get creative style preferences."""
        style = await learner.get_creative_style()
        return asdict(style)

    @router.put("/creative-style")
    async def set_creative(request: Request, req: CreativeStyleRequest):
        """Update creative style preferences."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/preferences/learning/creative-style",
            action_class="admin",
            default_reason="",
        )
        if denial:
            return denial
        kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
        await learner.set_creative_style(**kwargs)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/preferences/learning/creative-style",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail="Updated creative style preferences",
            target="creative-style",
            metadata={"fields": sorted(kwargs.keys())},
        )
        return {"status": "updated"}

    @router.get("/stats")
    async def get_stats():
        """Get model usage statistics."""
        await learner.load_preferences()
        if learner._preferences_cache is None:
            return {"models": {}}
        return {
            "models": {
                model: asdict(stats)
                for model, stats in learner._preferences_cache.model_stats.items()
            },
        }

    @router.get("/task-types")
    async def list_task_types():
        """List available task types and their default models."""
        return {
            "task_types": {t.value: DEFAULT_MODELS[t] for t in TaskType},
            "feedback_types": [f.value for f in FeedbackType],
            "preference_categories": [c.value for c in PreferenceCategory],
        }

    return router
