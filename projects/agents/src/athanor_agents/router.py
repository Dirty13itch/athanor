"""
Tiered Processing Router + Task-Type Detection

Classifies incoming requests by complexity tier and task type before agent
invocation. Determines which LiteLLM model to use, timeout, max_tokens,
and temperature.

Ported from:
- reference/kaizen/cognitive/workspace/tiered.py (tier scoring heuristics)
- reference/hydra/src/hydra_tools/routellm.py (regex complexity patterns)
- reference/hydra/src/hydra_tools/intelligent_router.py (task-type detection)

Adapted for Athanor: async, LiteLLM aliases, Redis state, LangFuse tracing.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# --- Enums ---


class ProcessingTier(str, Enum):
    """Processing tiers mapped to inference cost/latency budgets."""
    REACTIVE = "reactive"        # <100ms budget, simple queries
    TACTICAL = "tactical"        # 100ms-5s budget, standard work
    DELIBERATIVE = "deliberative" # 5s-5min budget, deep reasoning


class TaskType(str, Enum):
    """Task classification for routing and metrics."""
    CONVERSATION = "conversation"
    CODING = "coding"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    SUMMARIZATION = "summarization"
    QUICK_QUERY = "quick_query"
    SYSTEM = "system"
    MEDIA = "media"


# --- Configuration ---


@dataclass
class TierConfig:
    """Configuration for a processing tier."""
    model: str          # LiteLLM alias
    max_tokens: int
    temperature: float
    timeout_s: float
    use_agent: bool     # Whether to run full agent graph or direct LLM


def _build_tier_configs() -> dict[ProcessingTier, TierConfig]:
    """Build tier configs from settings (deferred import to avoid circular)."""
    from .config import settings

    return {
        ProcessingTier.REACTIVE: TierConfig(
            model=settings.router_reactive_model,
            max_tokens=settings.router_reactive_max_tokens,
            temperature=settings.router_reactive_temperature,
            timeout_s=10,
            use_agent=False,
        ),
        ProcessingTier.TACTICAL: TierConfig(
            model=settings.router_tactical_model,
            max_tokens=settings.router_tactical_max_tokens,
            temperature=0.7,
            timeout_s=30,
            use_agent=True,
        ),
        ProcessingTier.DELIBERATIVE: TierConfig(
            model=settings.router_deliberative_model,
            max_tokens=settings.router_deliberative_max_tokens,
            temperature=0.8,
            timeout_s=300,
            use_agent=True,
        ),
    }


# Lazy-initialized
_tier_configs: dict[ProcessingTier, TierConfig] | None = None


def get_tier_configs() -> dict[ProcessingTier, TierConfig]:
    global _tier_configs
    if _tier_configs is None:
        _tier_configs = _build_tier_configs()
    return _tier_configs


# --- Routing Decision ---


@dataclass
class RoutingDecision:
    """Result of classifying a request."""
    tier: ProcessingTier
    task_type: TaskType
    tier_config: TierConfig
    confidence: float
    reason: str
    scores: dict = field(default_factory=dict)
    classification_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "task_type": self.task_type.value,
            "model": self.tier_config.model,
            "max_tokens": self.tier_config.max_tokens,
            "temperature": self.tier_config.temperature,
            "use_agent": self.tier_config.use_agent,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "classification_ms": round(self.classification_ms, 1),
        }


# --- Compiled Patterns ---

# Reactive: simple greetings, yes/no, single-word queries
REACTIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(hi|hello|hey|yo|sup|thanks|thank you|ok|okay|sure|yes|no|bye|goodbye)\s*[!.?]*$",
        r"^(good\s+(morning|afternoon|evening|night))\s*[!.]*$",
        r"^what\s+(time|day|date)\s+is\s+it",
        r"^(how are you|what's up|how's it going)",
    ]
]

# Simple patterns — short factual queries, definitions
SIMPLE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(what|who|when|where|which)\s+is\s+",
        r"^(define|meaning of|what does .+ mean)",
        r"^(translate|convert)\s+",
        r"^(how\s+(many|much|old|long|far|tall))\s+",
    ]
]

# Complex patterns — multi-step reasoning, analysis
COMPLEX_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(analyze|analysis|evaluate|assess|critique)\b",
        r"\b(compare|contrast|pros\s+and\s+cons|trade-?offs?)\b",
        r"\b(explain\s+(why|how)|reasoning|implications)\b",
        r"\b(step[- ]by[- ]step|detailed|comprehensive|thorough)\b",
        r"\b(design|architect|plan|strategy|approach)\b",
        r"\b(optimize|improve|refactor|restructure)\b",
    ]
]

# Code patterns
CODE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"```",
        r"\b(def |class |import |from |const |let |var |async |await )\b",
        r"\b(function|method|variable|parameter|argument|return)\b",
        r"\b(bug|error|fix|debug|refactor|implement|test)\b",
        r"\b(python|javascript|typescript|rust|go|java|sql|bash)\b",
        r"\b(api|endpoint|database|query|schema|migration)\b",
        r"\b(git|docker|kubernetes|ansible|terraform)\b",
    ]
]

# Creative patterns
CREATIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(write|create|compose)\s+(a\s+)?(story|poem|essay|script|song|narrative)",
        r"\b(imagine|roleplay|character|scene|describe)\b",
        r"\b(creative|artistic|fiction|fantasy|brainstorm)\b",
    ]
]

# Research patterns
RESEARCH_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(research|investigate|find\s+out|look\s+up|search\s+for)\b",
        r"\b(latest|current|recent)\s+(news|updates|developments)\b",
        r"\b(what\s+is\s+happening|what's\s+new)\s+(in|with|about)\b",
    ]
]

# Media patterns (Athanor-specific)
MEDIA_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(movie|film|show|series|episode|season|watch)\b",
        r"\b(plex|sonarr|radarr|download|torrent|subtitle)\b",
        r"\b(music|song|album|artist|playlist|spotify)\b",
    ]
]

# System/infrastructure patterns
SYSTEM_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(server|node|cluster|gpu|vram|cpu|ram|disk)\b",
        r"\b(deploy|restart|configure|install|update|upgrade)\b",
        r"\b(docker|container|service|process|systemd)\b",
        r"\b(monitor|status|health|logs|metrics|alert)\b",
        r"\b(vllm|litellm|qdrant|redis|neo4j|prometheus|grafana)\b",
    ]
]

# Summarization patterns
SUMMARIZATION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(summarize|summary|tldr|brief|overview|key\s+points)\b",
        r"\b(condense|shorten|recap)\b",
    ]
]


# --- Router ---


def _count_matches(text: str, patterns: list[re.Pattern]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


class RequestRouter:
    """
    Classifies requests by processing tier and task type.

    Combines Kaizen's tier scoring heuristics with Hydra's regex-based
    task classification, adapted for Athanor's LiteLLM model aliases.
    """

    def classify(
        self,
        prompt: str,
        agent_name: str = "",
        conversation_length: int = 0,
    ) -> RoutingDecision:
        """
        Classify a request and return routing decision.

        Args:
            prompt: The user's message text
            agent_name: The target agent (may override task type)
            conversation_length: Number of prior messages (context for tier)
        """
        start = time.monotonic()

        # --- Task type classification ---
        task_type = self._classify_task_type(prompt, agent_name)

        # --- Tier classification ---
        tier, confidence, reason, scores = self._classify_tier(
            prompt, task_type, conversation_length
        )

        tier_config = get_tier_configs()[tier]

        # Agent-specific overrides: specialized agents always use full graph
        if agent_name and agent_name not in ("general-assistant", ""):
            if tier == ProcessingTier.REACTIVE:
                # Specialized agents shouldn't use the fast bypass
                tier = ProcessingTier.TACTICAL
                tier_config = get_tier_configs()[tier]
                reason += " (upgraded: specialized agent)"

        elapsed = (time.monotonic() - start) * 1000

        decision = RoutingDecision(
            tier=tier,
            task_type=task_type,
            tier_config=tier_config,
            confidence=confidence,
            reason=reason,
            scores=scores,
            classification_ms=elapsed,
        )

        logger.info(
            "Router: %s/%s → %s (%.1fms, conf=%.2f) %s",
            tier.value, task_type.value, tier_config.model,
            elapsed, confidence, reason,
        )

        return decision

    def _classify_task_type(self, prompt: str, agent_name: str) -> TaskType:
        """Classify task type from prompt content and agent context."""
        # Agent name gives strong signal
        agent_type_map = {
            "coding-agent": TaskType.CODING,
            "creative-agent": TaskType.CREATIVE,
            "research-agent": TaskType.RESEARCH,
            "media-agent": TaskType.MEDIA,
            "home-agent": TaskType.SYSTEM,
            "knowledge-agent": TaskType.RESEARCH,
            "data-curator": TaskType.ANALYSIS,
            "stash-agent": TaskType.MEDIA,
        }
        if agent_name in agent_type_map:
            return agent_type_map[agent_name]

        # Pattern-based classification
        scores = {
            TaskType.CODING: _count_matches(prompt, CODE_PATTERNS),
            TaskType.CREATIVE: _count_matches(prompt, CREATIVE_PATTERNS),
            TaskType.RESEARCH: _count_matches(prompt, RESEARCH_PATTERNS),
            TaskType.ANALYSIS: _count_matches(prompt, COMPLEX_PATTERNS),
            TaskType.MEDIA: _count_matches(prompt, MEDIA_PATTERNS),
            TaskType.SYSTEM: _count_matches(prompt, SYSTEM_PATTERNS),
            TaskType.SUMMARIZATION: _count_matches(prompt, SUMMARIZATION_PATTERNS),
        }

        max_score = max(scores.values())
        if max_score == 0:
            # Check if it's a simple query
            if _count_matches(prompt, SIMPLE_PATTERNS) > 0:
                return TaskType.QUICK_QUERY
            return TaskType.CONVERSATION

        return max(scores, key=scores.get)

    def _classify_tier(
        self,
        prompt: str,
        task_type: TaskType,
        conversation_length: int,
    ) -> tuple[ProcessingTier, float, str, dict]:
        """
        Classify processing tier using multi-signal scoring.

        Returns (tier, confidence, reason, scores).
        """
        reactive_score = 0.0
        tactical_score = 0.0
        deliberative_score = 0.0

        tokens = _estimate_tokens(prompt)
        word_count = len(prompt.split())
        reasons = []

        # --- Signal 1: Reactive pattern match (strong signal) ---
        reactive_matches = _count_matches(prompt, REACTIVE_PATTERNS)
        if reactive_matches > 0 and word_count < 10:
            reactive_score += 0.6
            reasons.append(f"reactive_pattern({reactive_matches})")

        # --- Signal 2: Word count ---
        if word_count < 8:
            reactive_score += 0.2
        elif word_count < 50:
            tactical_score += 0.2
        elif word_count < 200:
            tactical_score += 0.1
            deliberative_score += 0.15
        else:
            deliberative_score += 0.3
            reasons.append(f"long_input({word_count}w)")

        # --- Signal 3: Complexity patterns ---
        simple_matches = _count_matches(prompt, SIMPLE_PATTERNS)
        complex_matches = _count_matches(prompt, COMPLEX_PATTERNS)

        if simple_matches > 0 and complex_matches == 0:
            reactive_score += 0.15
            tactical_score += 0.1
        if complex_matches > 0:
            deliberative_score += 0.15 * min(complex_matches, 3)
            reasons.append(f"complex_patterns({complex_matches})")

        # --- Signal 4: Code presence ---
        code_matches = _count_matches(prompt, CODE_PATTERNS)
        if code_matches >= 2 or "```" in prompt:
            deliberative_score += 0.2
            tactical_score += 0.1
            reasons.append("code_detected")

        # --- Signal 5: Question complexity ---
        question_count = prompt.count("?")
        if question_count > 2:
            deliberative_score += 0.1
            reasons.append(f"multi_question({question_count})")
        elif question_count == 1 and word_count < 15:
            tactical_score += 0.1

        # --- Signal 6: Multi-part request ---
        list_markers = len(re.findall(r"(?m)^\s*[-*\d]+[.)]\s", prompt))
        if list_markers >= 3:
            deliberative_score += 0.15
            reasons.append(f"multi_part({list_markers})")

        # --- Signal 7: Task type bias ---
        task_tier_bias = {
            TaskType.QUICK_QUERY: (0.15, 0.0, 0.0),
            TaskType.CONVERSATION: (0.1, 0.1, 0.0),
            TaskType.MEDIA: (0.0, 0.15, 0.0),
            TaskType.SYSTEM: (0.0, 0.15, 0.0),
            TaskType.SUMMARIZATION: (0.0, 0.1, 0.05),
            TaskType.CODING: (0.0, 0.05, 0.15),
            TaskType.CREATIVE: (0.0, 0.05, 0.15),
            TaskType.ANALYSIS: (0.0, 0.0, 0.2),
            TaskType.RESEARCH: (0.0, 0.05, 0.15),
        }
        r_bias, t_bias, d_bias = task_tier_bias.get(task_type, (0, 0.1, 0))
        reactive_score += r_bias
        tactical_score += t_bias
        deliberative_score += d_bias

        # --- Signal 8: Conversation context ---
        if conversation_length > 10:
            tactical_score += 0.05  # Longer conversations tend toward tactical

        # --- Decision ---
        scores = {
            "reactive": round(reactive_score, 3),
            "tactical": round(tactical_score, 3),
            "deliberative": round(deliberative_score, 3),
            "tokens_est": tokens,
            "word_count": word_count,
        }

        # Select highest scoring tier
        if reactive_score > tactical_score and reactive_score > deliberative_score:
            tier = ProcessingTier.REACTIVE
            confidence = reactive_score / (reactive_score + tactical_score + deliberative_score + 0.01)
        elif deliberative_score > tactical_score:
            tier = ProcessingTier.DELIBERATIVE
            confidence = deliberative_score / (reactive_score + tactical_score + deliberative_score + 0.01)
        else:
            tier = ProcessingTier.TACTICAL
            confidence = tactical_score / (reactive_score + tactical_score + deliberative_score + 0.01)

        reason = ", ".join(reasons) if reasons else "baseline"

        return tier, confidence, reason, scores


# Module-level singleton
_router: RequestRouter | None = None


def get_router() -> RequestRouter:
    global _router
    if _router is None:
        _router = RequestRouter()
    return _router


def classify_request(
    prompt: str,
    agent_name: str = "",
    conversation_length: int = 0,
) -> RoutingDecision:
    """Convenience function for classifying a request."""
    return get_router().classify(prompt, agent_name, conversation_length)


async def apply_preference_override(decision: RoutingDecision) -> RoutingDecision:
    """Consult preference learning to potentially override the model.

    If preference data shows a different model performs better for this
    task type (with enough samples), override the tier config's model.
    Returns the same decision object (mutated in place).
    """
    from .preferences import get_preferred_model

    try:
        preferred = await get_preferred_model(
            task_type=decision.task_type.value,
            available_models=["reasoning", "fast"],
        )
        if preferred and preferred != decision.tier_config.model:
            old_model = decision.tier_config.model
            decision.tier_config.model = preferred
            decision.reason += f" (pref override: {old_model}→{preferred})"
            logger.info(
                "Preference override: %s→%s for task_type=%s",
                old_model, preferred, decision.task_type.value,
            )
    except Exception as e:
        logger.debug("Preference lookup failed (using default): %s", e)

    return decision
