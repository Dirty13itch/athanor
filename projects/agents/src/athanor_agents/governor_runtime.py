"""Governor runtime and compatibility helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import settings

logger = logging.getLogger(__name__)

GOV_STATE_KEY = "athanor:governor:state"
GOV_PAUSED_LANES_KEY = "athanor:governor:paused_lanes"
GOV_PRESENCE_KEY = "athanor:governor:presence"
GOV_HEARTBEAT_KEY = "athanor:governor:heartbeat_ts"
GOV_APPROVAL_STATS_KEY = "athanor:governor:approval_stats"
GOV_DECISIONS_KEY = "athanor:governor:decisions"
RELEASE_TIER_KEY = "athanor:governor:release_tier"

LANES = {
    "scheduler": {"label": "Proactive Scheduler", "description": "Periodic agent health checks and probes"},
    "work_planner": {"label": "Work Planner", "description": "Task generation from intent mining"},
    "workspace_reaction": {"label": "Workspace Reactions", "description": "Inter-agent coordination tasks"},
    "manual": {"label": "Manual / API", "description": "Tasks submitted via API or dashboard"},
    "pipeline": {"label": "Work Pipeline", "description": "Autonomous plan-driven task generation"},
}

HIGH_IMPACT_AGENTS = {"coding-agent"}
LOW_RISK_AGENTS = {"home-agent", "stash-agent", "data-curator", "knowledge-agent"}
MEDIUM_RISK_AGENTS = {"creative-agent", "media-agent", "research-agent"}

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

HEARTBEAT_STALE_SECONDS = 120
DECISIONS_MAX = 500
TRUST_CACHE_TTL = 30

AUTONOMY_OPERATIONAL_SOURCES = {"scheduler", "auto-retry", "pipeline"}


def _is_autonomy_managed_submission(source: str, metadata: dict | None) -> bool:
    if source in AUTONOMY_OPERATIONAL_SOURCES:
        return True
    meta = dict(metadata or {})
    return bool(meta.get("_autonomy_managed"))


async def _get_redis():
    from . import governor_backbone as backbone

    return await backbone._get_redis()


def _governor_backbone():
    from . import governor_backbone as backbone

    return backbone


def _redis_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode()
    return str(val)


async def _compat_hset(redis, key: str, mapping: dict[str, str]) -> None:
    hset = getattr(redis, "hset", None)
    if callable(hset):
        try:
            await hset(key, mapping=mapping)
            return
        except TypeError:
            for field, value in mapping.items():
                await hset(key, field, value)
            return

    current = await _compat_hgetall(redis, key)
    current.update({k: str(v) for k, v in mapping.items()})
    await redis.set(key, json.dumps(current))


async def _compat_hgetall(redis, key: str) -> dict[str, str]:
    hgetall = getattr(redis, "hgetall", None)
    if callable(hgetall):
        data = await hgetall(key)
        if data:
            return {_redis_str(k): _redis_str(v) for k, v in data.items()}

    getter = getattr(redis, "get", None)
    if not callable(getter):
        return {}
    raw = await getter(key)
    if not raw:
        return {}
    try:
        return {str(k): _redis_str(v) for k, v in json.loads(_redis_str(raw)).items()}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


async def _compat_set_members(redis, key: str) -> set[str]:
    smembers = getattr(redis, "smembers", None)
    if callable(smembers):
        try:
            return {_redis_str(item) for item in await smembers(key)}
        except TypeError:
            pass

    getter = getattr(redis, "get", None)
    if not callable(getter):
        return set()
    raw = await getter(key)
    if not raw:
        return set()
    try:
        return {str(item) for item in json.loads(_redis_str(raw))}
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()


async def _compat_replace_set(redis, key: str, members: set[str]) -> None:
    smembers = getattr(redis, "smembers", None)
    srem = getattr(redis, "srem", None)
    sadd = getattr(redis, "sadd", None)
    if callable(smembers) and callable(srem) and callable(sadd):
        existing = await _compat_set_members(redis, key)
        for member in existing - members:
            await srem(key, member)
        if members:
            await sadd(key, *sorted(members))
        return

    await redis.set(key, json.dumps(sorted(members)))


async def _compat_add_set_member(redis, key: str, member: str) -> set[str]:
    sadd = getattr(redis, "sadd", None)
    if callable(sadd):
        try:
            await sadd(key, member)
            return await _compat_set_members(redis, key)
        except TypeError:
            pass
    members = await _compat_set_members(redis, key)
    members.add(member)
    await _compat_replace_set(redis, key, members)
    return members


async def _compat_remove_set_member(redis, key: str, member: str) -> set[str]:
    srem = getattr(redis, "srem", None)
    if callable(srem):
        try:
            await srem(key, member)
            return await _compat_set_members(redis, key)
        except TypeError:
            pass
    members = await _compat_set_members(redis, key)
    members.discard(member)
    await _compat_replace_set(redis, key, members)
    return members


async def _legacy_split_governor_state(redis) -> dict:
    state = await _compat_hgetall(redis, GOV_STATE_KEY)
    presence = await _compat_hgetall(redis, GOV_PRESENCE_KEY)
    release = await _compat_hgetall(redis, RELEASE_TIER_KEY)
    paused_lanes = sorted(await _compat_set_members(redis, GOV_PAUSED_LANES_KEY))

    if not state and not presence and not release and not paused_lanes:
        return {}

    operator_presence = presence.get("configured_state") or presence.get("signal_state") or "at_desk"

    return {
        "global_mode": state.get("global_mode", "active"),
        "degraded_mode": state.get("degraded_mode", "none"),
        "reason": state.get("reason", ""),
        "updated_at": state.get("updated_at"),
        "updated_by": state.get("updated_by", "system"),
        "paused_lanes": paused_lanes,
        "operator_presence": operator_presence,
        "presence_mode": presence.get("mode", "auto"),
        "presence_reason": presence.get("reason", ""),
        "presence_updated_at": presence.get("updated_at"),
        "presence_updated_by": presence.get("updated_by", state.get("updated_by", "system")),
        "presence_signal_state": presence.get("signal_state") or None,
        "presence_signal_source": presence.get("signal_source", ""),
        "presence_signal_reason": presence.get("reason", ""),
        "presence_signal_updated_at": presence.get("updated_at"),
        "presence_signal_updated_by": presence.get("updated_by", state.get("updated_by", "system")),
        "release_tier": release.get("state", "standard"),
        "tier_reason": release.get("reason", ""),
        "tier_updated_at": release.get("updated_at"),
        "tier_updated_by": release.get("updated_by", state.get("updated_by", "system")),
    }


async def _ensure_backbone_governor_state() -> dict:
    backbone = _governor_backbone()
    redis = await _get_redis()
    try:
        return await backbone.get_governor_state()
    except Exception as exc:
        if "WRONGTYPE" not in str(exc).upper():
            raise

    legacy_state = await _legacy_split_governor_state(redis)
    delete = getattr(redis, "delete", None)
    if callable(delete):
        await delete(
            GOV_STATE_KEY,
            GOV_PAUSED_LANES_KEY,
            GOV_PRESENCE_KEY,
            RELEASE_TIER_KEY,
            GOV_HEARTBEAT_KEY,
        )
    return await backbone._save_governor_state(legacy_state or {})


def _default_governor_state() -> dict:
    backbone = _governor_backbone()
    normalize = getattr(backbone, "_normalize_governor_state", None)
    if callable(normalize):
        return dict(normalize({}))
    return dict(getattr(backbone, "DEFAULT_GOVERNOR_STATE", {}))


def _job_priority_band(job_family: str, job_id: str, owner_agent: str) -> str:
    resolved_family = "benchmarks" if job_id == "benchmark-cycle" else job_family
    profile_builder = getattr(_governor_backbone(), "_job_governance_profile", None)
    if callable(profile_builder):
        profile = profile_builder(resolved_family, owner_agent)
        return str(profile.get("priority_band") or "scheduled_low_risk")
    return "scheduled_low_risk"


@dataclass
class GateDecision:
    allowed: bool
    status_override: str
    autonomy_level: str
    reason: str
    trust_score: float
    presence_state: str


def _load_autonomy_policy():
    try:
        from .model_governance import get_current_autonomy_policy

        return get_current_autonomy_policy()
    except Exception:
        return None


def _autonomy_workload_class(agent: str, prompt: str, metadata: dict | None) -> str:
    meta = dict(metadata or {})
    source = str(meta.get("source") or "").strip()
    source_overrides = {
        "daily_digest": "briefing_digest",
        "workplan": "workplan_generation",
        "workplan_refill": "workplan_generation",
        "starvation_recovery": "workplan_generation",
        "dpo_training": "background_transform",
    }
    if source in source_overrides:
        return source_overrides[source]

    try:
        from .command_hierarchy import normalize_workload_class
        from .subscriptions import infer_task_class

        return normalize_workload_class(infer_task_class(agent, prompt, meta))
    except Exception:
        return str(meta.get("task_class") or meta.get("workload_class") or "private_automation")


def _phase_gate_for_autonomous_source(
    *,
    agent: str,
    prompt: str,
    metadata: dict | None,
    source: str,
    trust_score: float,
    presence_state: str,
) -> GateDecision | None:
    if not _is_autonomy_managed_submission(source, metadata):
        return None

    policy = _load_autonomy_policy()
    if policy is None:
        return None

    phase_id = str(policy.phase_id or "")
    if not policy.is_active:
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=(
                f"Autonomy phase {phase_id or 'unset'} is not enabled "
                f"(phase_status={policy.phase_status}, activation_state={policy.activation_state})"
            ),
            trust_score=trust_score,
            presence_state=presence_state,
        )

    if policy.unmet_prerequisite_ids:
        unmet_ids = ", ".join(policy.unmet_prerequisite_ids)
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=f"Autonomy phase {phase_id or 'unset'} has unmet prerequisites: {unmet_ids}",
            trust_score=trust_score,
            presence_state=presence_state,
        )

    enabled_agents = set(policy.enabled_agents)
    if enabled_agents and agent not in enabled_agents:
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=f"Agent '{agent}' is outside autonomy phase {phase_id or 'unset'}",
            trust_score=trust_score,
            presence_state=presence_state,
        )

    workload_class = _autonomy_workload_class(agent, prompt, metadata)
    allowed_workloads = set(policy.allowed_workload_classes)
    blocked_workloads = set(policy.blocked_workload_classes)
    if workload_class in blocked_workloads:
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=(
                f"Workload '{workload_class}' is blocked in autonomy phase {phase_id}; "
                f"source '{source}' requires approval"
            ),
            trust_score=trust_score,
            presence_state=presence_state,
        )
    if allowed_workloads and workload_class not in allowed_workloads:
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=(
                f"Workload '{workload_class}' is outside autonomy phase {phase_id}; "
                f"source '{source}' requires approval"
            ),
            trust_score=trust_score,
            presence_state=presence_state,
        )

    if policy.runtime_mutations_approval_gated and bool(
        (metadata or {}).get("requires_runtime_mutation")
    ):
        return GateDecision(
            allowed=False,
            status_override="pending_approval",
            autonomy_level="D",
            reason=(
                f"Workload '{workload_class}' remains approval-gated because runtime mutations "
                f"are still gated in autonomy phase {phase_id}"
            ),
            trust_score=trust_score,
            presence_state=presence_state,
        )

    bounded_reason = (
        f"Source '{source}' is permitted inside autonomy phase {phase_id}; "
        f"agent='{agent}', workload='{workload_class}'"
    )
    if not policy.broad_autonomy_enabled:
        bounded_reason += " (bounded phase only; broad autonomy remains disabled)"
    return GateDecision(
        allowed=True,
        status_override="pending",
        autonomy_level="A",
        reason=bounded_reason,
        trust_score=trust_score,
        presence_state=presence_state,
    )


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
        return await _get_redis()

    async def load(self):
        await _ensure_backbone_governor_state()
        logger.info("Governor loaded")

    async def shutdown(self):
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("Governor shutdown")

    async def gate_task_submission(
        self,
        agent: str,
        prompt: str,
        priority: str = "normal",
        metadata: dict | None = None,
        source: str = "manual",
    ) -> GateDecision:
        metadata = metadata or {}

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
                reason="System degraded - only critical/high priority tasks allowed",
                trust_score=0.0,
                presence_state="unknown",
            )
            await self._record_decision(agent, source, priority, decision)
            return decision

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

        trust_score = await self._get_agent_trust(agent)
        presence = await self.get_effective_presence()
        presence_state = presence["state"]
        presence_mod = PRESENCE_STATES.get(presence_state, {}).get("modifier", 0.0)

        autonomous_source_decision = _phase_gate_for_autonomous_source(
            agent=agent,
            prompt=prompt,
            metadata=metadata,
            source=source,
            trust_score=trust_score,
            presence_state=presence_state,
        )
        if autonomous_source_decision is not None:
            decision = autonomous_source_decision
            await self._record_decision(agent, source, priority, decision)
            return decision

        effective_score = trust_score
        if agent in HIGH_IMPACT_AGENTS:
            effective_score -= 0.2
        if agent in LOW_RISK_AGENTS:
            effective_score += 0.15
        if source == "manual":
            effective_score += 0.1
        if source == "workspace_reaction":
            effective_score += 0.1
        if priority in ("low", "normal") and agent in LOW_RISK_AGENTS:
            effective_score += 0.1
        if priority == "critical":
            effective_score -= 0.2
        effective_score += presence_mod
        effective_score = max(0.0, min(1.0, effective_score))

        if effective_score > 0.8:
            level = "A"
        elif effective_score > 0.5:
            level = "B"
        elif effective_score > 0.3:
            level = "C"
        else:
            level = "D"

        if level == "A":
            status = "pending"
            reason = f"Level A (score={effective_score:.2f}) - auto-execute"
        elif level == "B":
            status = "pending"
            reason = f"Level B (score={effective_score:.2f}) - execute with notification"
            asyncio.create_task(self._notify_submission(agent, prompt, priority))
        elif level == "C":
            if presence_state in ("asleep", "away"):
                status = "pending_approval"
                reason = f"Level C (score={effective_score:.2f}), owner {presence_state} - deferred"
            else:
                status = "pending_approval"
                reason = f"Level C (score={effective_score:.2f}) - hold for approval"
        else:
            status = "pending_approval"
            reason = f"Level D (score={effective_score:.2f}) - requires approval"

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

    async def get_effective_presence(self) -> dict:
        backbone = _governor_backbone()
        state = await _ensure_backbone_governor_state()
        return backbone._build_presence_snapshot(state)

    async def set_presence(self, mode: str, state: str, reason: str = "", actor: str = "operator"):
        await _governor_backbone().set_operator_presence(state, reason=reason, actor=actor, mode=mode)
        await self._record_action(
            "presence_set",
            {"mode": mode, "state": state, "reason": reason, "actor": actor},
        )

    async def record_heartbeat(self, source: str = "dashboard", state: str = "at_desk"):
        await _governor_backbone().record_presence_heartbeat(
            state,
            source=source,
            reason="Dashboard heartbeat updated operator presence.",
            actor=source or "dashboard-heartbeat",
        )

    async def pause(self, scope: str = "global", actor: str = "operator", reason: str = ""):
        await _governor_backbone().pause_automation(scope=scope, reason=reason, actor=actor)
        await self._record_action("pause", {"scope": scope, "actor": actor, "reason": reason})
        logger.info("Governor paused: scope=%s by=%s reason=%s", scope, actor, reason)

    async def resume(self, scope: str = "global", actor: str = "operator", reason: str = ""):
        await _governor_backbone().resume_automation(scope=scope, actor=actor)
        await self._record_action("resume", {"scope": scope, "actor": actor, "reason": reason})
        logger.info("Governor resumed: scope=%s by=%s", scope, actor)

    async def set_release_tier(self, tier: str, reason: str = "", actor: str = "operator"):
        await _governor_backbone().set_release_tier(tier, reason=reason, actor=actor)
        await self._record_action(
            "release_tier_set",
            {"tier": tier, "reason": reason, "actor": actor},
        )

    async def record_approval(self, agent: str, category: str, approved: bool):
        r = await self._get_redis()
        key = f"{agent}:{category}"
        if approved:
            await r.hincrby(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive", 1)
        else:
            await r.hset(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive", "0")

    async def get_approval_stats(self, agent: str, category: str) -> dict:
        r = await self._get_redis()
        key = f"{agent}:{category}"
        consecutive = await r.hget(GOV_APPROVAL_STATS_KEY, f"{key}:consecutive")
        return {
            "consecutive_approvals": int(_redis_str(consecutive)) if consecutive else 0,
        }

    async def snapshot(self) -> dict:
        return await _governor_backbone().build_governor_snapshot()

    async def _get_state(self) -> dict:
        return await _ensure_backbone_governor_state()

    async def _get_paused_lanes(self) -> set:
        state = await self._get_state()
        return {str(item) for item in state.get("paused_lanes", [])}

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
        now = time.time()
        if self._trust_cache is None or now - self._trust_cache_ts > TRUST_CACHE_TTL:
            try:
                from .goals import compute_trust_scores

                self._trust_cache = await compute_trust_scores()
                self._trust_cache_ts = now
            except Exception as exc:
                logger.warning("Trust score computation failed: %s", exc)
                self._trust_cache = {"agents": {}}
                self._trust_cache_ts = now

        agents = self._trust_cache.get("agents", {})
        agent_info = agents.get(agent, {})
        return agent_info.get("score", 0.5)

    async def _notify_submission(self, agent: str, prompt: str, priority: str):
        try:
            from .escalation import _send_ntfy_notification

            await _send_ntfy_notification(
                title=f"Task submitted: {agent}",
                body=f"[{priority}] {prompt[:100]}",
                priority="default" if priority == "normal" else priority,
            )
        except Exception as exc:
            logger.debug("Governor notification failed: %s", exc)

    async def _record_decision(self, agent: str, source: str, priority: str, decision: GateDecision):
        try:
            r = await self._get_redis()
            entry = json.dumps(
                {
                    "agent": agent,
                    "source": source,
                    "priority": priority,
                    "level": decision.autonomy_level,
                    "status": decision.status_override,
                    "reason": decision.reason,
                    "trust": round(decision.trust_score, 3),
                    "presence": decision.presence_state,
                    "ts": time.time(),
                }
            )
            await r.lpush(GOV_DECISIONS_KEY, entry)
            await r.ltrim(GOV_DECISIONS_KEY, 0, DECISIONS_MAX - 1)
        except Exception as exc:
            logger.debug("Failed to record governor decision: %s", exc)

    async def _record_action(self, action: str, data: dict):
        try:
            r = await self._get_redis()
            entry = json.dumps({"action": action, **data, "ts": time.time()})
            await r.lpush(GOV_DECISIONS_KEY, entry)
            await r.ltrim(GOV_DECISIONS_KEY, 0, DECISIONS_MAX - 1)
        except Exception as exc:
            logger.debug("Failed to record governor action: %s", exc)

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
        return await _governor_backbone().build_capacity_snapshot()

    async def _probe_nodes(self) -> list[dict]:
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

                results.append(
                    {
                        "id": node_id,
                        "alive": alive,
                        "stale": not alive,
                        "max_gpu_util_pct": 0,
                        "healthy_models": 1 if alive else 0,
                        "total_models": 1,
                        "load_1m": 0,
                        "ram_available_mb": 0,
                    }
                )

        return results

    async def _get_release_tier(self) -> dict:
        snapshot = await self.snapshot()
        return dict(snapshot.get("release_tier") or {})


async def get_workspace_stats() -> dict:
    try:
        from .workspace import get_redis

        redis = await get_redis()
        items = await redis.hlen("athanor:workspace")
        return {"item_count": items}
    except Exception:
        return {"item_count": 0}
