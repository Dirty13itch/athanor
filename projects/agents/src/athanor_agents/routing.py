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
- FAST: Qwen3.5-35B-A3B-AWQ (Workshop 5090)
- WORKER: Qwen3.5-35B-A3B-AWQ (Workshop 5090)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ModelTier(Enum):
    FAST = "fast"
    REASONING = "reasoning"
    WORKER = "worker"
    CLOUD = "cloud"  # Quality escalation — cloud models for high-stakes tasks


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
    ModelTier.FAST: "coder",         # Healthy low-latency local lane on Foundry
    ModelTier.REASONING: "reasoning",  # Qwen3.5-27B-FP8 on Foundry TP=4
    ModelTier.WORKER: "worker",      # Qwen3.5-35B-A3B-AWQ on Workshop
    ModelTier.CLOUD: "claude",       # Anthropic Claude Sonnet — quality escalation
}

# Cloud model pool — rotated for cost distribution
CLOUD_MODELS = ["claude", "gpt", "gemini", "deepseek"]
SOVEREIGN_POLICY_CLASSES = {"sovereign_only", "refusal_sensitive"}
SOVEREIGN_SENSITIVITY = {"adult_sensitive", "lan_only", "sovereign_only"}

# Fallback chains: if preferred model is busy, try these
# Cloud escalation: when all local models are busy, escalate to cloud
FALLBACK_CHAINS = {
    "reasoning": ["fast", "claude", "worker"],
    "fast": ["reasoning", "claude", "worker"],
    "coder": ["reasoning", "claude", "worker"],
    "worker": ["reasoning", "fast", "claude"],
    "claude": ["gpt", "gemini", "deepseek", "reasoning"],
}

# Task types eligible for cloud escalation when local quality is insufficient
CLOUD_ESCALATION_TASKS = {TaskType.RESEARCH, TaskType.CREATIVE}

# Subscription provider names → LiteLLM model aliases
PROVIDER_TO_MODEL = {
    "athanor_local": "reasoning",
    "anthropic_claude_code": "claude",
    "openai_codex": "gpt",
    "google_gemini": "gemini",
    "moonshot_kimi": "kimi-k2.5",
    "zai_glm_coding": "glm-4.7",
    "deepseek_api": "deepseek",
    "venice_api": "venice-uncensored",
    "deepseek": "deepseek",
    "venice": "venice-uncensored",
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
        r"(home assistant|automation|device)",
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


def _is_sovereign_request(metadata: dict[str, Any] | None) -> bool:
    meta = dict(metadata or {})
    if bool(meta.get("sovereign_only")):
        return True
    if str(meta.get("policy_class") or "").strip() in SOVEREIGN_POLICY_CLASSES:
        return True
    if str(meta.get("meta_lane") or "").strip() == "sovereign_local":
        return True
    return str(meta.get("sensitivity") or "").strip().lower() in SOVEREIGN_SENSITIVITY


def _fallback_chain(model: str, *, local_only: bool) -> list[str]:
    chain = list(FALLBACK_CHAINS.get(model, []))
    if not local_only:
        return chain
    return [candidate for candidate in chain if candidate not in CLOUD_MODELS]


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
    TaskType.RESEARCH: ModelTier.REASONING,  # Local-first: Qwen3.5-27B 95.0 IFEval, cloud for escalation
    TaskType.CREATIVE: ModelTier.REASONING,  # Local-first: GPUs idle, cloud for quality eval only
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
    metadata: dict | None = None,
    prefer_local: bool = False,
) -> RoutingDecision:
    """
    Route a prompt to the optimal model — local or cloud.

    Cloud routing is activated when:
    1. Task metadata contains an execution lease with a cloud provider, OR
    2. Task type is in CLOUD_ESCALATION_TASKS and prefer_local is False, OR
    3. All local models are busy (queue depth fallback to cloud)

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        queue_depths: Dict of model_name → current queue depth
        prefer_quality: Bump to reasoning tier if uncertain
        high_queue_threshold: Queue depth above which to use fallback
        metadata: Task metadata (may contain subscription lease)
        prefer_local: Force local-only routing (for privacy-sensitive tasks)

    Returns:
        RoutingDecision with LiteLLM model name
    """
    task_type = classify_task(prompt, system_prompt)
    metadata = metadata or {}
    local_only = prefer_local or _is_sovereign_request(metadata)

    # Check for subscription lease in metadata → cloud routing
    lease = metadata.get("lease") or metadata.get("execution_lease")
    if lease and not local_only:
        provider = lease.get("provider") or lease.get("recommended_provider", "")
        if provider and provider in PROVIDER_TO_MODEL:
            cloud_model = PROVIDER_TO_MODEL[provider]
            return RoutingDecision(
                model=cloud_model,
                tier=ModelTier.CLOUD,
                confidence=0.9,
                reason=f"Subscription lease → {provider} → {cloud_model}",
                task_type=task_type,
            )

    preferred_tier = TASK_ROUTING[task_type]

    if local_only and task_type not in {TaskType.HOME, TaskType.MEDIA, TaskType.SYSTEM}:
        preferred_tier = ModelTier.REASONING

    if prefer_quality and preferred_tier == ModelTier.FAST:
        preferred_tier = ModelTier.REASONING

    # Cloud-preferred tasks use cloud when not forced local
    if preferred_tier == ModelTier.CLOUD and local_only:
        preferred_tier = ModelTier.REASONING

    model = TIER_MODELS[preferred_tier]

    # Check queue depth and fallback if needed
    if queue_depths and queue_depths.get(model, 0) >= high_queue_threshold:
        for fallback in _fallback_chain(model, local_only=local_only):
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
