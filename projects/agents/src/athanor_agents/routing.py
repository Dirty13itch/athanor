"""
Quality Cascade — Intelligent model routing for Athanor.

Routes requests to optimal LOCAL model based on:
- Prompt complexity (simple → fast, complex → reasoning)
- Task type (code/research → reasoning, simple → fast, etc.)
- Current GPU load (via scheduling.py Prometheus queries)
- Queue depth awareness (fallback when busy)

Ported from Hydra's routellm.py, adapted for Athanor's model stack.

Athanor Model Tiers (via LiteLLM at VAULT:4000):
- REASONING: Qwen3.5-27B-FP8 TP=4 (Foundry GPUs 0,1,3,4)
- FAST: Huihui-Qwen3-8B-abliterated-v2 (Foundry GPU 2, 4090)
- WORKER: Qwen3.5-35B-A3B-AWQ (Workshop 5090)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ModelTier(Enum):
    FAST = "fast"
    REASONING = "reasoning"
    WORKER = "worker"


class TaskType(Enum):
    SIMPLE = "simple"
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    RESEARCH = "research"
    CREATIVE = "creative"
    SYSTEM = "system"
    HOME = "home"
    MEDIA = "media"


@dataclass
class RoutingDecision:
    model: str
    tier: ModelTier
    confidence: float
    reason: str
    task_type: TaskType = TaskType.CHAT


# LiteLLM route names → Athanor models
TIER_MODELS = {
    ModelTier.FAST: "fast",          # Qwen3-8B-abliterated on Foundry 4090
    ModelTier.REASONING: "reasoning",  # Qwen3.5-27B-FP8 on Foundry TP=4
    ModelTier.WORKER: "worker",      # Qwen3.5-35B-A3B-AWQ on Workshop
}

# Fallback chains: if preferred model is busy, try these
FALLBACK_CHAINS = {
    "reasoning": ["worker", "fast"],
    "fast": ["worker", "reasoning"],
    "worker": ["reasoning", "fast"],
}


# --- Pattern sets for classification ---

SIMPLE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(hi|hello|hey|good morning|good evening)",
        r"^what (is|are) \w+\??$",
        r"^define ",
        r"^translate .{0,100}$",
        r"^(yes|no)\??$",
        r"^(who|what|when|where) (is|was|are|were) ",
        r"^(list|name|give me) \d+ ",
    ]
]

COMPLEX_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(explain|analyze|compare|contrast|evaluate|assess|critique)",
        r"(step[- ]by[- ]step|detailed|comprehensive|thorough)",
        r"(why|how) (does|do|did|would|could|should|might)",
        r"(pros? and cons?|tradeoffs?|advantages? and disadvantages?)",
        r"(reasoning|logic|argument|evidence|implications)",
        r"(architecture|design|system|infrastructure).{0,30}(decision|choice|approach)",
        r"(research|study|investigation|analysis)",
        r"(complex|complicated|nuanced|subtle)",
    ]
]

CODE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"```[\w]*\n",
        r"(def |class |function\s*\(|const |let |var )",
        r"(import \w+|from \w+ import|require\(['\"]|#include )",
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|sql)\b.{0,30}(code|script|program|function|bug|error|fix|debug)",
        r"(debug|fix|refactor|optimize|review) (this |the |my )?(code|function|class|script)",
        r"(implement|write|create|build) (a |an )?(function|class|method|api|script|endpoint)",
        r"(error|exception|bug|traceback|stack trace)",
    ]
]

CREATIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(write|create|compose) (a |an )?(story|poem|essay|script|song|scene|dialogue)",
        r"(imagine|pretend|roleplay|act as)",
        r"(creative|artistic|fictional|fantasy|narrative)",
        r"(brainstorm|generate ideas|come up with)",
        r"(character|protagonist|villain|plot|setting)",
    ]
]

SYSTEM_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(docker|container|service|server|node|cluster)",
        r"(deploy|restart|configure|setup|install|ansible)",
        r"(monitor|check status|health|logs|metrics)",
        r"(database|cache|queue|storage|qdrant|redis|neo4j)",
        r"(vllm|litellm|grafana|prometheus|loki)",
    ]
]

HOME_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(lights?|switch|thermostat|temperature|sensor|motion)",
        r"(home assistant|automation|scene|device)",
        r"(turn on|turn off|dim|brighten|set to)",
        r"(house|room|bedroom|kitchen|living room|garage)",
    ]
]

MEDIA_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(movie|tv show|series|film|episode|season)",
        r"(watch|download|stream|plex|sonarr|radarr)",
        r"(music|album|song|playlist|artist)",
        r"(recommend|suggest|similar to|like)",
    ]
]

RESEARCH_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(research|investigate|find out|look up|search for)",
        r"(latest|current|recent) (news|updates|developments|release)",
        r"(what is happening|what's new) (in|with|about)",
        r"(benchmark|comparison|versus|vs\.?)",
    ]
]


def _count_matches(text: str, patterns: list[re.Pattern]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def classify_task(prompt: str, system_prompt: str | None = None) -> TaskType:
    """Classify a prompt into a task type."""
    text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    # Check specific patterns first (order matters)
    if _count_matches(text, CODE_PATTERNS) >= 1 or "```" in text:
        return TaskType.CODE
    if _count_matches(text, HOME_PATTERNS) >= 1:
        return TaskType.HOME
    if _count_matches(text, MEDIA_PATTERNS) >= 1:
        return TaskType.MEDIA
    if _count_matches(text, CREATIVE_PATTERNS) >= 1:
        return TaskType.CREATIVE
    if _count_matches(text, RESEARCH_PATTERNS) >= 1:
        return TaskType.RESEARCH
    if _count_matches(text, SYSTEM_PATTERNS) >= 2:
        return TaskType.SYSTEM

    # Complexity-based fallback
    simple = _count_matches(text, SIMPLE_PATTERNS)
    complex_ = _count_matches(text, COMPLEX_PATTERNS)

    if simple + complex_ == 0:
        return TaskType.CHAT

    ratio = complex_ / (simple + complex_)
    if ratio > 0.5 or _estimate_tokens(text) > 500:
        return TaskType.REASONING
    if ratio < 0.3:
        return TaskType.SIMPLE

    return TaskType.CHAT


# Task type → preferred model tier
TASK_ROUTING = {
    TaskType.SIMPLE: ModelTier.FAST,
    TaskType.CHAT: ModelTier.FAST,
    TaskType.CODE: ModelTier.REASONING,
    TaskType.REASONING: ModelTier.REASONING,
    TaskType.RESEARCH: ModelTier.REASONING,
    TaskType.CREATIVE: ModelTier.REASONING,
    TaskType.SYSTEM: ModelTier.REASONING,
    TaskType.HOME: ModelTier.FAST,
    TaskType.MEDIA: ModelTier.FAST,
}


def route(
    prompt: str,
    system_prompt: str | None = None,
    queue_depths: dict[str, int] | None = None,
    prefer_quality: bool = False,
    high_queue_threshold: int = 5,
) -> RoutingDecision:
    """
    Route a prompt to the optimal local model.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        queue_depths: Dict of model_name → current queue depth
        prefer_quality: Bump to reasoning tier if uncertain
        high_queue_threshold: Queue depth above which to use fallback

    Returns:
        RoutingDecision with LiteLLM model name
    """
    task_type = classify_task(prompt, system_prompt)
    preferred_tier = TASK_ROUTING[task_type]

    if prefer_quality and preferred_tier == ModelTier.FAST:
        preferred_tier = ModelTier.REASONING

    model = TIER_MODELS[preferred_tier]

    # Check queue depth and fallback if needed
    if queue_depths and queue_depths.get(model, 0) >= high_queue_threshold:
        for fallback in FALLBACK_CHAINS.get(model, []):
            if queue_depths.get(fallback, 0) < high_queue_threshold:
                # Resolve the tier of the fallback model
                fallback_tier = next(
                    (t for t, m in TIER_MODELS.items() if m == fallback),
                    preferred_tier,
                )
                return RoutingDecision(
                    model=fallback,
                    tier=fallback_tier,
                    confidence=0.7,
                    reason=f"{model} busy (depth={queue_depths[model]}), fallback to {fallback}",
                    task_type=task_type,
                )

    # Calculate confidence from pattern match strength
    text = prompt if not system_prompt else f"{system_prompt}\n{prompt}"
    if task_type == TaskType.CODE:
        confidence = min(0.6 + _count_matches(text, CODE_PATTERNS) * 0.1, 0.95)
    elif task_type == TaskType.CREATIVE:
        confidence = min(0.6 + _count_matches(text, CREATIVE_PATTERNS) * 0.1, 0.95)
    elif task_type == TaskType.REASONING:
        confidence = min(0.6 + _count_matches(text, COMPLEX_PATTERNS) * 0.05, 0.95)
    else:
        confidence = 0.8

    return RoutingDecision(
        model=model,
        tier=preferred_tier,
        confidence=confidence,
        reason=f"Task: {task_type.value} → {preferred_tier.value} (tokens≈{_estimate_tokens(prompt)})",
        task_type=task_type,
    )


@dataclass
class CostRecord:
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CostTracker:
    """Track inference costs across models."""

    # Estimated power-cost per 1K tokens (local inference, electricity only)
    LOCAL_COSTS = {
        "fast": 0.001,      # 8B on 4090, efficient
        "reasoning": 0.006,  # 27B FP8, TP=4
        "worker": 0.003,    # 35B MoE on 5090
    }

    def __init__(self):
        self.records: list[CostRecord] = []

    def record(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        self.records.append(CostRecord(model, input_tokens, output_tokens, latency_ms))
        if len(self.records) > 5000:
            self.records = self.records[-5000:]

    def summary(self) -> dict:
        from collections import defaultdict
        by_model: dict[str, dict] = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})
        for r in self.records:
            by_model[r.model]["requests"] += 1
            total_tokens = r.input_tokens + r.output_tokens
            by_model[r.model]["tokens"] += total_tokens
            by_model[r.model]["cost"] += (total_tokens / 1000) * self.LOCAL_COSTS.get(r.model, 0.003)
        return {
            "total_requests": len(self.records),
            "by_model": dict(by_model),
        }


# Singleton
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _cost_tracker


# FastAPI router factory
def create_routing_router():
    """Create FastAPI router for routing endpoints."""
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/v1/routing", tags=["routing"])

    class RouteRequest(BaseModel):
        prompt: str
        system_prompt: str | None = None
        queue_depths: dict[str, int] | None = None
        prefer_quality: bool = False

    class CostRequest(BaseModel):
        model: str
        input_tokens: int
        output_tokens: int
        latency_ms: float

    @router.post("/route")
    async def route_prompt(req: RouteRequest):
        decision = route(req.prompt, req.system_prompt, req.queue_depths, req.prefer_quality)
        return {
            "model": decision.model,
            "tier": decision.tier.value,
            "task_type": decision.task_type.value,
            "confidence": decision.confidence,
            "reason": decision.reason,
        }

    @router.post("/classify")
    async def classify(req: RouteRequest):
        task = classify_task(req.prompt, req.system_prompt)
        return {"task_type": task.value, "preferred_model": TIER_MODELS[TASK_ROUTING[task]]}

    @router.post("/cost/record")
    async def record_cost(req: CostRequest):
        _cost_tracker.record(req.model, req.input_tokens, req.output_tokens, req.latency_ms)
        return {"status": "recorded"}

    @router.get("/cost/summary")
    async def cost_summary():
        return _cost_tracker.summary()

    @router.get("/matrix")
    async def routing_matrix():
        return {
            "routing": {t.value: TIER_MODELS[tier].upper() for t, tier in TASK_ROUTING.items()},
            "fallbacks": FALLBACK_CHAINS,
            "models": {t.value: m for t, m in TIER_MODELS.items()},
        }

    return router
