"""Governor Runtime — the control plane for all task submission.

Every task flows through the governor before reaching the task engine.
The governor decides: execute immediately, notify, hold for approval, or reject.

Decision factors:
- Global mode (active / paused / degraded)
- Lane status (scheduler, work_planner, workspace, manual — each pausable)
- Trust scores (from goals.compute_trust_scores())
- Autonomy adjustments (from escalation threshold tuning)
- Presence detection (at_desk / away / asleep / phone_only)
- Task priority and agent classification

Redis-backed singleton. Dashboard already has full governor UI running on fixtures;
this makes it live by serving the governorSnapshotSchema from contracts.ts.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)

# Redis keys
GOV_STATE_KEY = "athanor:governor:state"
GOV_PAUSED_LANES_KEY = "athanor:governor:paused_lanes"
GOV_PRESENCE_KEY = "athanor:governor:presence"
GOV_HEARTBEAT_KEY = "athanor:governor:heartbeat_ts"
GOV_APPROVAL_STATS_KEY = "athanor:governor:approval_stats"
GOV_DECISIONS_KEY = "athanor:governor:decisions"

# Lane definitions
LANES = {
    "scheduler": {"label": "Proactive Scheduler", "description": "Periodic agent health checks and probes"},
    "work_planner": {"label": "Work Planner", "description": "Task generation from intent mining"},
    "workspace_reaction": {"label": "Workspace Reactions", "description": "Inter-agent coordination tasks"},
    "manual": {"label": "Manual / API", "description": "Tasks submitted via API or dashboard"},
    "pipeline": {"label": "Work Pipeline", "description": "Autonomous plan-driven task generation"},
}

# Agents whose tasks have higher impact (require more oversight)
HIGH_IMPACT_AGENTS = {"coding-agent", "creative-agent", "home-agent"}

# Presence state labels and postures
PRESENCE_STATES = {
    "at_desk": {
        "label": "At Desk",
        "automation_posture": "standard",
        "notification_posture": "standard",
        "approval_posture": "standard",
        "modifier": 0.0,
    },
    "away": {
        "label": "Away",
        "automation_posture": "elevated",
        "notification_posture": "batch",
        "approval_posture": "deferred",
        "modifier": 0.1,
    },
    "asleep": {
        "label": "Asleep",
        "automation_posture": "maximum",
        "notification_posture": "silent",
        "approval_posture": "morning",
        "modifier": 0.2,
    },
    "phone_only": {
        "label": "Phone Only",
        "automation_posture": "elevated",
        "notification_posture": "urgent_only",
        "approval_posture": "deferred",
        "modifier": 0.15,
    },
}

HEARTBEAT_STALE_SECONDS = 120  # After 120s without heartbeat → "away"
DECISIONS_MAX = 500
TRUST_CACHE_TTL = 30  # seconds


@dataclass
class GateDecision:
    """Result of gate_task_submission."""
    allowed: bool
    status_override: str  # "pending" or "pending_approval"
    autonomy_level: str  # A, B, C, D
    reason: str
    trust_score: float
    presence_state: str


class Governor:
    """Singleton governor runtime. Redis-backed state."""

    _instance: "Governor | None" = None

    def __init__(self):
        self._trust_cache: dict | None = None
        self._trust_cache_ts: float = 0.0
        self._refresh_task: asyncio.Task | None = None

    @classmethod
    def get(cls) -> "Governor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_redis(self):
        from .workspace import get_redis
        return await get_redis()

    # --- State management ---

    async def load(self):
        """Initialize governor state in Redis if not present."""
        r = await self._get_redis()
        if not await r.exists(GOV_STATE_KEY):
            await r.hset(GOV_STATE_KEY, mapping={
                "global_mode": "active",
                "degraded_mode": "none",
                "reason": "System initialized",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "updated_by": "system",
            })
        # Initialize presence if not set
        if not await r.exists(GOV_PRESENCE_KEY):
            await r.hset(GOV_PRESENCE_KEY, mapping={
                "mode": "auto",
                "configured_state": "at_desk",
                "signal_state": "",
                "signal_source": "",
            })
        logger.info("Governor loaded")

    async def shutdown(self):
        """Clean shutdown."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("Governor shutdown")

    # --- Core gating logic ---

    async def gate_task_submission(
        self,
        agent: str,
        prompt: str,
        priority: str = "normal",
        metadata: dict | None = None,
        source: str = "manual",
    ) -> GateDecision:
        """Decide whether a task should execute, notify, or hold for approval.

        Returns a GateDecision. Callers use decision.status_override when
        submitting to the task engine.
        """
        metadata = metadata or {}

        # 1. Global mode check
        state = await self._get_state()
        global_mode = state.get("global_mode", "active")

        if global_mode == "paused":
            decision = GateDecision(
                allowed=False,
                status_override="pending_approval",
                autonomy_level="D",
                reason="System paused",
                trust_score=0.0,
                presence_state="unknown",
            )
            await self._record_decision(agent, source, priority, decision)
            return decision

        if global_mode == "degraded" and priority not in ("critical", "high"):
            decision = GateDecision(
                allowed=False,
                status_override="pending_approval",
                autonomy_level="D",
                reason="System degraded — only critical/high priority tasks allowed",
                trust_score=0.0,
                presence_state="unknown",
            )
            await self._record_decision(agent, source, priority, decision)
            return decision

        # 2. Lane check
        paused_lanes = await self._get_paused_lanes()
        lane = self._source_to_lane(source)
        if lane in paused_lanes:
            decision = GateDecision(
                allowed=False,
                status_override="pending_approval",
                autonomy_level="D",
                reason=f"Lane '{lane}' is paused",
                trust_score=0.0,
                presence_state="unknown",
            )
            await self._record_decision(agent, source, priority, decision)
            return decision

        # 3. Compute autonomy level
        trust_score = await self._get_agent_trust(agent)
        presence = await self.get_effective_presence()
        presence_state = presence["state"]
        presence_mod = PRESENCE_STATES.get(presence_state, {}).get("modifier", 0.0)

        # Scheduler, auto-retry, and pipeline tasks are operational — auto-execute
        if source in ("scheduler", "auto-retry", "pipeline"):
            decision = GateDecision(
                allowed=True,
                status_override="pending",
                autonomy_level="A",
                reason=f"Source '{source}' — auto-execute (operational task)",
                trust_score=trust_score,
                presence_state=presence_state,
            )
            await self._record_decision(agent, source, priority, decision)
            return decision

        # Modifiers
        effective_score = trust_score
        if agent in HIGH_IMPACT_AGENTS:
            effective_score -= 0.2  # More oversight for high-impact agents
        if source == "manual":
            effective_score += 0.1  # Manual submissions get more trust
        if priority == "critical":
            effective_score -= 0.2  # Critical tasks get more oversight
        effective_score += presence_mod  # Away/asleep = more autonomous

        # Clamp
        effective_score = max(0.0, min(1.0, effective_score))

        # Grade
        if effective_score > 0.8:
            level = "A"
        elif effective_score > 0.5:
            level = "B"
        elif effective_score > 0.3:
            level = "C"
        else:
            level = "D"

        # 4. Decision
        if level == "A":
            status = "pending"
            reason = f"Level A (score={effective_score:.2f}) — auto-execute"
        elif level == "B":
            status = "pending"
            reason = f"Level B (score={effective_score:.2f}) — execute with notification"
            # Fire notification (fire-and-forget)
            asyncio.create_task(self._notify_submission(agent, prompt, priority))
        elif level == "C":
            if presence_state in ("asleep", "away"):
                status = "pending_approval"
                reason = f"Level C (score={effective_score:.2f}), owner {presence_state} — deferred"
            else:
                status = "pending_approval"
                reason = f"Level C (score={effective_score:.2f}) — hold for approval"
        else:  # D
            status = "pending_approval"
            reason = f"Level D (score={effective_score:.2f}) — requires approval"

        decision = GateDecision(
            allowed=status == "pending",
            status_override=status,
            autonomy_level=level,
            reason=reason,
            trust_score=trust_score,
            presence_state=presence_state,
        )
        await self._record_decision(agent, source, priority, decision)
        return decision

    # --- Presence detection ---

    async def get_effective_presence(self) -> dict:
        """Determine current presence state.

        Priority: manual override > heartbeat freshness > time-of-day fallback.
        """
        r = await self._get_redis()

        # Read configured presence
        raw = await r.hgetall(GOV_PRESENCE_KEY)
        mode = _redis_str(raw.get("mode", raw.get(b"mode", "auto")))
        configured_state = _redis_str(raw.get("configured_state", raw.get(b"configured_state", "at_desk")))
        signal_state = _redis_str(raw.get("signal_state", raw.get(b"signal_state", "")))
        signal_source = _redis_str(raw.get("signal_source", raw.get(b"signal_source", "")))

        if mode == "manual":
            effective = configured_state
            reason = "Manual override"
        else:
            # Auto mode: check heartbeat
            heartbeat_ts = await r.get(GOV_HEARTBEAT_KEY)
            heartbeat_fresh = False
            heartbeat_age = None
            if heartbeat_ts:
                ts = float(_redis_str(heartbeat_ts))
                heartbeat_age = time.time() - ts
                heartbeat_fresh = heartbeat_age < HEARTBEAT_STALE_SECONDS

            if heartbeat_fresh and heartbeat_age is not None:
                effective = "at_desk"
                reason = f"Dashboard heartbeat fresh ({int(heartbeat_age)}s ago)"
            else:
                # Time-of-day fallback
                hour = datetime.now().hour
                if 22 <= hour or hour < 6:
                    effective = "asleep"
                    reason = "Time-of-day fallback (22:00-06:00)"
                else:
                    effective = "away"
                    reason = f"Heartbeat stale ({int(heartbeat_age)}s ago)" if heartbeat_age else "No heartbeat received"

        state_info = PRESENCE_STATES.get(effective, PRESENCE_STATES["away"])
        return {
            "state": effective,
            "label": state_info["label"],
            "automation_posture": state_info["automation_posture"],
            "notification_posture": state_info["notification_posture"],
            "approval_posture": state_info["approval_posture"],
            "updated_at": None,
            "updated_by": "auto" if mode == "auto" else "operator",
            "mode": mode,
            "configured_state": configured_state,
            "configured_label": PRESENCE_STATES.get(configured_state, {}).get("label", configured_state),
            "signal_state": signal_state or None,
            "signal_source": signal_source or None,
            "signal_updated_at": None,
            "signal_updated_by": "",
            "signal_fresh": False,
            "signal_age_seconds": None,
            "effective_reason": reason,
        }

    async def set_presence(self, mode: str, state: str, reason: str = "", actor: str = "operator"):
        """Set presence mode and state."""
        r = await self._get_redis()
        await r.hset(GOV_PRESENCE_KEY, mapping={
            "mode": mode,
            "configured_state": state,
        })
        await self._record_action("presence_set", {
            "mode": mode, "state": state, "reason": reason, "actor": actor
        })

    async def record_heartbeat(self, source: str = "dashboard"):
        """Record a heartbeat from the dashboard."""
        r = await self._get_redis()
        await r.set(GOV_HEARTBEAT_KEY, str(time.time()))

    # --- Pause / Resume ---

    async def pause(self, scope: str = "global", actor: str = "operator", reason: str = ""):
        """Pause the governor or a specific lane."""
        r = await self._get_redis()
        if scope == "global":
            await r.hset(GOV_STATE_KEY, mapping={
                "global_mode": "paused",
                "reason": reason or "Paused by operator",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "updated_by": actor,
            })
        else:
            await r.sadd(GOV_PAUSED_LANES_KEY, scope)
        await self._record_action("pause", {"scope": scope, "actor": actor, "reason": reason})
        logger.info("Governor paused: scope=%s by=%s reason=%s", scope, actor, reason)

    async def resume(self, scope: str = "global", actor: str = "operator", reason: str = ""):
        """Resume the governor or a specific lane."""
        r = await self._get_redis()
        if scope == "global":
            await r.hset(GOV_STATE_KEY, mapping={
                "global_mode": "active",
                "reason": reason or "Resumed by operator",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "updated_by": actor,
            })
        else:
            await r.srem(GOV_PAUSED_LANES_KEY, scope)
        await self._record_action("resume", {"scope": scope, "actor": actor, "reason": reason})
        logger.info("Governor resumed: scope=%s by=%s", scope, actor)

    # --- Release tier ---

    async def set_release_tier(self, tier: str, reason: str = "", actor: str = "operator"):
        """Set the release tier for cloud provider access."""
        r = await self._get_redis()
        await r.hset("athanor:governor:release_tier", mapping={
            "state": tier,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "updated_by": actor,
        })
        await self._record_action("release_tier_set", {"tier": tier, "reason": reason, "actor": actor})

    # --- Approval tracking ---

    async def record_approval(self, agent: str, category: str, approved: bool):
        """Track consecutive approvals for auto-approve graduation."""
        r = await self._get_redis()
        key = f"{agent}:{category}"
        if approved:
            await r.hincrby(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive", 1)
        else:
            await r.hset(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive", "0")

    async def get_approval_stats(self, agent: str, category: str) -> dict:
        """Get approval stats for an agent:category pair."""
        r = await self._get_redis()
        key = f"{agent}:{category}"
        consecutive = await r.hget(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive")
        return {
            "consecutive_approvals": int(_redis_str(consecutive)) if consecutive else 0,
        }

    # --- Snapshot (matches governorSnapshotSchema) ---

    async def snapshot(self) -> dict:
        """Build the full governor snapshot for the dashboard.

        Matches contracts.ts:governorSnapshotSchema exactly.
        """
        state = await self._get_state()
        presence = await self.get_effective_presence()
        capacity = await self._build_capacity()
        lanes = await self._build_lanes()
        release_tier = await self._get_release_tier()

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "status": state.get("global_mode", "active"),
            "global_mode": state.get("global_mode", "active"),
            "degraded_mode": state.get("degraded_mode", "none"),
            "reason": state.get("reason", ""),
            "updated_at": state.get("updated_at"),
            "updated_by": state.get("updated_by", "system"),
            "lanes": lanes,
            "capacity": capacity,
            "presence": presence,
            "release_tier": release_tier,
            "command_rights_version": "1.0.0",
            "control_stack": [
                {"id": "constitution", "label": "Constitutional Constraints", "status": "active"},
                {"id": "governor", "label": "Governor Runtime", "status": state.get("global_mode", "active")},
                {"id": "escalation", "label": "Escalation Protocol", "status": "active"},
                {"id": "circuit_breaker", "label": "Circuit Breakers", "status": "active"},
            ],
        }

    # --- Internal helpers ---

    async def _get_state(self) -> dict:
        r = await self._get_redis()
        raw = await r.hgetall(GOV_STATE_KEY)
        return {k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode()
                for k, v in raw.items()} if raw else {
            "global_mode": "active", "degraded_mode": "none",
            "reason": "Default", "updated_at": None, "updated_by": "system"
        }

    async def _get_paused_lanes(self) -> set:
        r = await self._get_redis()
        members = await r.smembers(GOV_PAUSED_LANES_KEY)
        return {_redis_str(m) for m in members}

    def _source_to_lane(self, source: str) -> str:
        mapping = {
            "scheduler": "scheduler",
            "work_planner": "work_planner",
            "workspace_reaction": "workspace_reaction",
            "manual": "manual",
            "pipeline": "pipeline",
            "auto-retry": "scheduler",
        }
        return mapping.get(source, "manual")

    async def _get_agent_trust(self, agent: str) -> float:
        """Get trust score for an agent (cached)."""
        now = time.time()
        if self._trust_cache is None or now - self._trust_cache_ts > TRUST_CACHE_TTL:
            try:
                from .goals import compute_trust_scores
                self._trust_cache = await compute_trust_scores()
                self._trust_cache_ts = now
            except Exception as e:
                logger.warning("Trust score computation failed: %s", e)
                self._trust_cache = {"agents": {}}
                self._trust_cache_ts = now

        agents = self._trust_cache.get("agents", {})
        agent_info = agents.get(agent, {})
        return agent_info.get("score", 0.5)

    async def _notify_submission(self, agent: str, prompt: str, priority: str):
        """Send a notification for Level B tasks."""
        try:
            from .escalation import _send_ntfy_notification
            await _send_ntfy_notification(
                title=f"Task submitted: {agent}",
                body=f"[{priority}] {prompt[:100]}",
                priority="default" if priority == "normal" else priority,
            )
        except Exception as e:
            logger.debug("Governor notification failed: %s", e)

    async def _record_decision(self, agent: str, source: str, priority: str, decision: GateDecision):
        """Record a gating decision to the audit trail."""
        try:
            r = await self._get_redis()
            entry = json.dumps({
                "agent": agent,
                "source": source,
                "priority": priority,
                "level": decision.autonomy_level,
                "status": decision.status_override,
                "reason": decision.reason,
                "trust": round(decision.trust_score, 3),
                "presence": decision.presence_state,
                "ts": time.time(),
            })
            await r.lpush(GOV_DECISIONS_KEY, entry)
            await r.ltrim(GOV_DECISIONS_KEY, 0, DECISIONS_MAX - 1)
        except Exception as e:
            logger.debug("Failed to record governor decision: %s", e)

    async def _record_action(self, action: str, data: dict):
        """Record an administrative action."""
        try:
            r = await self._get_redis()
            entry = json.dumps({"action": action, **data, "ts": time.time()})
            await r.lpush(GOV_DECISIONS_KEY, entry)
            await r.ltrim(GOV_DECISIONS_KEY, 0, DECISIONS_MAX - 1)
        except Exception as e:
            logger.debug("Failed to record governor action: %s", e)

    async def _build_lanes(self) -> list[dict]:
        paused = await self._get_paused_lanes()
        return [
            {
                "id": lane_id,
                "label": info["label"],
                "description": info["description"],
                "paused": lane_id in paused,
                "status": "paused" if lane_id in paused else "active",
            }
            for lane_id, info in LANES.items()
        ]

    async def _build_capacity(self) -> dict:
        """Build capacity snapshot from live system state."""
        from .tasks import get_task_stats
        from .scheduler import get_scheduler_health

        try:
            task_stats = await get_task_stats()
        except Exception:
            task_stats = {}

        try:
            ws_stats = await get_workspace_stats()
        except Exception:
            ws_stats = {}

        try:
            sched = await get_scheduler_health()
        except Exception:
            sched = {}

        by_status = task_stats.get("by_status", {})
        pending = by_status.get("pending", 0)
        running = task_stats.get("currently_running", 0)
        failed = by_status.get("failed", 0)
        max_concurrent = task_stats.get("max_concurrent", 2)

        ws_items = ws_stats.get("item_count", 0) if isinstance(ws_stats, dict) else 0
        ws_capacity = 7

        # Queue posture
        if pending > 20:
            q_posture = "overloaded"
        elif pending > 10:
            q_posture = "busy"
        elif running > 0:
            q_posture = "working"
        else:
            q_posture = "idle"

        # Overall posture
        if q_posture == "overloaded":
            posture = "constrained"
        elif failed > 5:
            posture = "degraded"
        else:
            posture = "healthy"

        sched_running = sched.get("running", False)
        agent_schedules = sched.get("agent_schedules", {})
        enabled_count = sum(1 for s in agent_schedules.values() if s.get("enabled", True))

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "posture": posture,
            "queue": {
                "posture": q_posture,
                "pending": pending,
                "running": running,
                "max_concurrent": max_concurrent,
                "failed": failed,
            },
            "workspace": {
                "broadcast_items": ws_items,
                "capacity": ws_capacity,
                "utilization": round(ws_items / ws_capacity, 2) if ws_capacity else 0,
            },
            "scheduler": {
                "running": sched_running,
                "enabled_count": enabled_count,
            },
            "provider_reserve": {
                "posture": "healthy",
                "constrained_count": 0,
            },
            "active_time_windows": [],
            "nodes": await self._probe_nodes(),
            "recommendations": [],
        }

    async def _probe_nodes(self) -> list[dict]:
        """Quick node health probes for capacity snapshot."""
        import httpx

        nodes = [
            ("foundry", settings.coordinator_url),
            ("workshop", settings.worker_url),
            ("vault", settings.litellm_url),
            ("dev", settings.embedding_url),
        ]

        results = []
        async with httpx.AsyncClient(timeout=3.0) as client:
            for node_id, url in nodes:
                try:
                    resp = await client.get(f"{url}/health")
                    alive = resp.status_code < 500
                except Exception:
                    alive = False

                results.append({
                    "id": node_id,
                    "alive": alive,
                    "stale": not alive,
                    "max_gpu_util_pct": 0,
                    "healthy_models": 1 if alive else 0,
                    "total_models": 1,
                    "load_1m": 0,
                    "ram_available_mb": 0,
                })

        return results

    async def _get_release_tier(self) -> dict:
        r = await self._get_redis()
        raw = await r.hgetall("athanor:governor:release_tier")
        if raw:
            data = {k if isinstance(k, str) else k.decode(): v if isinstance(v, str) else v.decode()
                    for k, v in raw.items()}
            return {
                "state": data.get("state", "standard"),
                "available_tiers": ["free", "budget", "standard", "frontier"],
                "status": "active",
                "updated_at": data.get("updated_at"),
                "updated_by": data.get("updated_by", "system"),
            }
        return {
            "state": "standard",
            "available_tiers": ["free", "budget", "standard", "frontier"],
            "status": "active",
            "updated_at": None,
            "updated_by": "system",
        }


def _redis_str(val) -> str:
    """Safely convert Redis bytes or str to str."""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode()
    return str(val)


async def get_workspace_stats() -> dict:
    """Get workspace stats safely."""
    try:
        from .workspace import get_redis
        r = await get_redis()
        items = await r.hlen("athanor:workspace")
        return {"item_count": items}
    except Exception:
        return {"item_count": 0}
