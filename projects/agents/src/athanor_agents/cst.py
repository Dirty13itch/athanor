"""Continuous State Tensor — unified cognitive state for the workspace.

The CST is the "mind snapshot" at any moment. Persisted in Redis,
updated every competition cycle, and injected into agent prompts
via context.py.

Tracks:
- salience_map: topic → float (0-1), what's currently important
- attention_mode: focused/diffuse/monitoring/idle
- working_memory: bounded FIFO (max 20 items)
- cycle_count: total competition cycles executed
- last_broadcast: most recent winning broadcast

Salience decays 0.95x per cycle (10-20 cycle half-life).

Ported from: reference/kaizen/cognitive/workspace/cst.py
Adapted for Athanor: Redis persistence (no numpy), async,
serializes to context string for LLM injection.
"""

import json
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)

CST_KEY = "athanor:cst"
MAX_WORKING_MEMORY = 20
SALIENCE_DECAY = 0.95
SALIENCE_FLOOR = 0.1


class AttentionMode(str, Enum):
    FOCUSED = "focused"       # Deep work on a single topic
    DIFFUSE = "diffuse"       # Creative, broad exploration
    MONITORING = "monitoring"  # Background awareness
    IDLE = "idle"             # Low activity


class ContinuousStateTensor:
    """Unified cognitive state for the GWT workspace.

    Stored in Redis as a single JSON hash. All mutations go through
    save() to maintain consistency.
    """

    def __init__(self):
        self.salience_map: dict[str, float] = {}
        self.attention_mode: AttentionMode = AttentionMode.IDLE
        self.focus_target: str | None = None
        self.working_memory: list[dict] = []
        self.cycle_count: int = 0
        self.last_broadcast: dict | None = None
        self.last_updated: float = 0.0

    def to_dict(self) -> dict:
        return {
            "salience_map": self.salience_map,
            "attention_mode": self.attention_mode.value,
            "focus_target": self.focus_target,
            "working_memory": self.working_memory[-MAX_WORKING_MEMORY:],
            "cycle_count": self.cycle_count,
            "last_broadcast": self.last_broadcast,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContinuousStateTensor":
        cst = cls()
        cst.salience_map = data.get("salience_map", {})
        cst.attention_mode = AttentionMode(
            data.get("attention_mode", "idle")
        )
        cst.focus_target = data.get("focus_target")
        cst.working_memory = data.get("working_memory", [])
        cst.cycle_count = data.get("cycle_count", 0)
        cst.last_broadcast = data.get("last_broadcast")
        cst.last_updated = data.get("last_updated", 0.0)
        return cst

    def add_to_working_memory(self, item: dict) -> None:
        """Add item to working memory with FIFO eviction."""
        item["added_at"] = time.time()
        self.working_memory.append(item)
        if len(self.working_memory) > MAX_WORKING_MEMORY:
            self.working_memory = self.working_memory[-MAX_WORKING_MEMORY:]

    def update_salience(self, topics: dict[str, float]) -> None:
        """Update salience map with new topic weights.

        Incremental: min(1.0, old + weight * 0.3).
        """
        for topic, weight in topics.items():
            old = self.salience_map.get(topic, 0.0)
            self.salience_map[topic] = min(1.0, old + weight * 0.3)

    def decay_salience(self) -> None:
        """Apply exponential decay to all salience values.

        Remove topics below floor threshold.
        """
        to_remove = []
        for topic in self.salience_map:
            self.salience_map[topic] *= SALIENCE_DECAY
            if self.salience_map[topic] < SALIENCE_FLOOR:
                to_remove.append(topic)
        for topic in to_remove:
            del self.salience_map[topic]

    def update_from_broadcast(self, broadcast: dict) -> None:
        """Update CST after a competition cycle broadcast.

        Args:
            broadcast: The winning broadcast dict containing
                specialist, content, topics, etc.
        """
        self.cycle_count += 1
        self.last_broadcast = broadcast
        self.last_updated = time.time()

        # Update salience from broadcast topics
        topics = broadcast.get("topics", {})
        if topics:
            self.update_salience(topics)

        # Add specialist boost
        specialist = broadcast.get("specialist", "")
        if specialist:
            self.update_salience({specialist: 0.2})

        # Decay old salience
        self.decay_salience()

        # Update attention mode based on broadcast
        self._update_attention_mode(broadcast)

        # Add to working memory
        self.add_to_working_memory({
            "type": "broadcast",
            "specialist": specialist,
            "content": broadcast.get("content", "")[:200],
            "cycle": self.cycle_count,
        })

    def _update_attention_mode(self, broadcast: dict) -> None:
        """Infer attention mode from broadcast characteristics."""
        confidence = broadcast.get("confidence", 0.5)
        urgency = broadcast.get("urgency", 0.0)

        if urgency > 0.7:
            self.attention_mode = AttentionMode.FOCUSED
            self.focus_target = broadcast.get("specialist")
        elif confidence > 0.7:
            self.attention_mode = AttentionMode.FOCUSED
            self.focus_target = broadcast.get("specialist")
        elif len(self.salience_map) > 5:
            self.attention_mode = AttentionMode.DIFFUSE
            self.focus_target = None
        elif self.cycle_count > 0:
            self.attention_mode = AttentionMode.MONITORING
            self.focus_target = None

    def top_salient_topics(self, n: int = 5) -> list[tuple[str, float]]:
        """Get top N salient topics sorted by weight."""
        return sorted(
            self.salience_map.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:n]

    def to_context_string(self) -> str:
        """Serialize CST to a compact context string for LLM injection."""
        parts = []

        # Attention state
        mode_desc = {
            AttentionMode.FOCUSED: "focused",
            AttentionMode.DIFFUSE: "exploring broadly",
            AttentionMode.MONITORING: "monitoring",
            AttentionMode.IDLE: "idle",
        }
        mode_str = mode_desc.get(self.attention_mode, "unknown")
        if self.focus_target:
            parts.append(f"Attention: {mode_str} on {self.focus_target}")
        else:
            parts.append(f"Attention: {mode_str}")

        # Top salient topics
        top = self.top_salient_topics(5)
        if top:
            topic_strs = [f"{t}({w:.1f})" for t, w in top]
            parts.append(f"Active topics: {', '.join(topic_strs)}")

        # Working memory size
        parts.append(f"Working memory: {len(self.working_memory)} items")

        # Cycle count
        parts.append(f"Cycles: {self.cycle_count}")

        return " | ".join(parts)


# --- Redis persistence ---

async def _get_redis():
    from .workspace import get_redis
    return await get_redis()


async def load_cst() -> ContinuousStateTensor:
    """Load CST from Redis. Returns fresh CST if not found."""
    try:
        r = await _get_redis()
        data = await r.get(CST_KEY)
        if data:
            raw = data.decode() if isinstance(data, bytes) else data
            return ContinuousStateTensor.from_dict(json.loads(raw))
    except Exception as e:
        logger.debug("Failed to load CST from Redis: %s", e)
    return ContinuousStateTensor()


async def save_cst(cst: ContinuousStateTensor) -> None:
    """Save CST to Redis."""
    try:
        r = await _get_redis()
        await r.set(CST_KEY, json.dumps(cst.to_dict()))
    except Exception as e:
        logger.warning("Failed to save CST to Redis: %s", e)


# Module-level cache (loaded once, updated in-place)
_cst: ContinuousStateTensor | None = None


async def get_cst() -> ContinuousStateTensor:
    """Get or load the CST singleton."""
    global _cst
    if _cst is None:
        _cst = await load_cst()
    return _cst


async def update_cst_from_broadcast(broadcast: dict) -> ContinuousStateTensor:
    """Update CST from a broadcast and persist."""
    cst = await get_cst()
    cst.update_from_broadcast(broadcast)
    await save_cst(cst)
    return cst
