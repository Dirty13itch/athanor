"""
Self-Diagnosis Engine for Athanor Cluster.

Tracks failures, identifies patterns, suggests remediation.
Ported from Hydra's self_diagnosis.py, adapted for Athanor's infrastructure.

Storage: Redis (fast, ephemeral, already available) instead of JSON files.
Services: Athanor node names, vLLM, LiteLLM, Qdrant, Neo4j, Redis.
"""

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class FailureCategory(Enum):
    INFERENCE = "inference"
    NETWORK = "network"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    DATA = "data"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class FailurePattern:
    id: str
    category: str
    pattern_signature: str
    description: str
    occurrences: int = 0
    first_seen: str = ""
    last_seen: str = ""
    affected_services: list = field(default_factory=list)
    root_causes: list = field(default_factory=list)
    remediation_steps: list = field(default_factory=list)
    auto_remediation: Optional[str] = None
    resolved_count: int = 0
    mean_time_to_resolve: float = 0.0


@dataclass
class FailureEvent:
    id: str
    timestamp: str
    category: str
    severity: str
    service: str
    error_message: str
    stack_trace: Optional[str] = None
    context: dict = field(default_factory=dict)
    pattern_id: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class DiagnosticReport:
    generated_at: str
    time_range_hours: int
    total_failures: int
    failures_by_category: dict
    failures_by_severity: dict
    top_patterns: list
    recommendations: list
    health_score: float
    trend: str


# --- Pattern rules adapted for Athanor ---

PATTERN_RULES = {
    FailureCategory.INFERENCE: [
        (r"CUDA out of memory", "GPU memory exhaustion"),
        (r"model.*not found", "Missing model"),
        (r"timeout.*inference|inference.*timeout", "Inference timeout"),
        (r"connection refused.*(8000|8001|8002|8004|8100|8101)", "vLLM endpoint down"),
        (r"connection refused.*4000", "LiteLLM proxy down"),
        (r"rate limit", "Rate limiting"),
        (r"kv.?cache.*corrupt|nan|inf", "KV cache corruption"),
        (r"triton.*error|autotuner", "Triton kernel issue"),
    ],
    FailureCategory.NETWORK: [
        (r"connection refused", "Service connection failure"),
        (r"timeout|timed out", "Network timeout"),
        (r"DNS.*failed|resolve", "DNS resolution failure"),
        (r"connection reset", "Connection reset"),
        (r"no route to host", "Network routing failure"),
        (r"NFS.*stale|stale file handle", "NFS stale handle"),
    ],
    FailureCategory.RESOURCE: [
        (r"out of memory|OOM|oom-killer", "Memory exhaustion"),
        (r"no space left on device", "Disk space exhaustion"),
        (r"too many open files", "File descriptor exhaustion"),
        (r"resource temporarily unavailable", "Resource contention"),
        (r"GPU.*overheated|thermal", "GPU thermal throttle"),
    ],
    FailureCategory.CONFIGURATION: [
        (r"invalid.*config|configuration", "Invalid configuration"),
        (r"missing.*key|required", "Missing required config"),
        (r"yaml.*error|parse", "YAML parsing error"),
        (r"environment variable.*not set", "Missing env var"),
        (r"tool.?call.?parser.*hermes", "Wrong tool call parser (use qwen3_coder)"),
    ],
    FailureCategory.DEPENDENCY: [
        (r"service.*unavailable", "Dependent service down"),
        (r"qdrant.*connection|qdrant.*error", "Qdrant connection failure"),
        (r"neo4j.*connection|neo4j.*error", "Neo4j connection failure"),
        (r"redis.*connection|redis.*error", "Redis connection failure"),
        (r"container.*not running", "Container down"),
        (r"litellm.*error|proxy.*error", "LiteLLM proxy error"),
    ],
    FailureCategory.PERMISSION: [
        (r"permission denied", "File permission error"),
        (r"unauthorized|401", "Authentication failure"),
        (r"forbidden|403", "Authorization failure"),
    ],
    FailureCategory.DATA: [
        (r"json.*decode|invalid json", "JSON parsing error"),
        (r"validation.*error|invalid", "Data validation failure"),
        (r"embedding.*dimension|dimension.*mismatch", "Embedding dimension mismatch"),
    ],
    FailureCategory.TIMEOUT: [
        (r"deadline exceeded", "Deadline timeout"),
        (r"operation timed out", "Operation timeout"),
        (r"read timeout", "Read timeout"),
        (r"connect timeout", "Connection timeout"),
    ],
}

# Athanor-specific remediation
REMEDIATION_SUGGESTIONS = {
    FailureCategory.INFERENCE: {
        "GPU memory exhaustion": [
            "Check GPU usage: ssh node1 nvidia-smi / ssh node2 nvidia-smi",
            "Reduce --max-model-len or --max-num-batched-tokens",
            "Unload unused models via LiteLLM config",
        ],
        "vLLM endpoint down": [
            "Check systemd: ssh node1 'sudo systemctl status vllm-*'",
            "Check logs: ssh node1 'journalctl -u vllm-reasoning -n 50'",
            "Restart: ansible-playbook playbooks/foundry.yml --tags vllm",
        ],
        "LiteLLM proxy down": [
            "Check container: python3 scripts/vault-ssh.py 'docker ps | grep litellm'",
            "Restart: ansible-playbook playbooks/vault.yml --tags litellm",
        ],
        "KV cache corruption": [
            "CRITICAL: Qwen3.5 requires --kv-cache-dtype auto (NOT fp8)",
            "Restart affected vLLM instance with correct flags",
        ],
        "Inference timeout": [
            "Check GPU utilization on target node",
            "Consider routing to faster model via Quality Cascade",
        ],
    },
    FailureCategory.NETWORK: {
        "NFS stale handle": [
            "Remount: sudo umount -f /mnt/vault/models && sudo mount -a",
            "Check VAULT NFS exports: python3 scripts/vault-ssh.py 'exportfs -v'",
        ],
        "Service connection failure": [
            "Verify service is running on target node",
            "Check 10GbE link status between nodes",
        ],
    },
    FailureCategory.RESOURCE: {
        "Memory exhaustion": [
            "Check: ssh <node> free -h && docker stats --no-stream",
            "FOUNDRY has 224GB — if OOM, likely vLLM misconfigured",
            "WORKSHOP has 128GB — check if 5090 model + dashboard RAM-tight",
        ],
        "Disk space exhaustion": [
            "Check: df -h on affected node",
            "Clean Docker: docker system prune -af",
            "Clear old vLLM cache: rm -rf ~/.cache/vllm",
        ],
    },
    FailureCategory.DEPENDENCY: {
        "Qdrant connection failure": [
            "Check: python3 scripts/vault-ssh.py 'docker ps | grep qdrant'",
            "Qdrant runs on VAULT:6333",
        ],
        "Redis connection failure": [
            "Check: python3 scripts/vault-ssh.py 'docker ps | grep redis'",
            "Redis runs on VAULT:6379",
        ],
        "Neo4j connection failure": [
            "Check: python3 scripts/vault-ssh.py 'docker ps | grep neo4j'",
            "Neo4j runs on VAULT:7474 (HTTP) / 7687 (Bolt)",
        ],
        "Container down": [
            "Restart via Ansible: ansible-playbook playbooks/<node>.yml",
            "Or manual: python3 scripts/vault-ssh.py 'docker restart <name>'",
        ],
    },
    FailureCategory.CONFIGURATION: {
        "Wrong tool call parser (use qwen3_coder)": [
            "Qwen3.5 uses XML format, NOT hermes",
            "Set --tool-call-parser qwen3_coder in vLLM serve command",
        ],
    },
}

# Athanor critical services
CRITICAL_SERVICES = [
    "vllm-reasoning", "vllm-fast", "litellm", "qdrant",
    "redis", "neo4j", "athanor-agents", "grafana",
]


class SelfDiagnosisEngine:
    """
    Failure analysis engine. Stores events in memory with Redis persistence.
    """

    def __init__(self, max_events: int = 10000, pattern_threshold: int = 3):
        self.max_events = max_events
        self.pattern_threshold = pattern_threshold
        self.events: list[FailureEvent] = []
        self.patterns: dict[str, FailurePattern] = {}
        self._redis = None

    async def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                from .config import settings
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
            except Exception:
                return None
        return self._redis

    async def load_from_redis(self):
        """Load persisted state from Redis."""
        r = await self._get_redis()
        if not r:
            return

        try:
            events_data = await r.get("diagnosis:events")
            if events_data:
                self.events = [FailureEvent(**e) for e in json.loads(events_data)]

            patterns_data = await r.get("diagnosis:patterns")
            if patterns_data:
                self.patterns = {
                    k: FailurePattern(**v)
                    for k, v in json.loads(patterns_data).items()
                }
        except Exception:
            pass

    async def _save_to_redis(self):
        """Persist state to Redis."""
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        r = await self._get_redis()
        if not r:
            return

        try:
            await r.set(
                "diagnosis:events",
                json.dumps([asdict(e) for e in self.events]),
                ex=86400 * 7,  # 7 day TTL
            )
            await r.set(
                "diagnosis:patterns",
                json.dumps({k: asdict(v) for k, v in self.patterns.items()}),
                ex=86400 * 30,  # 30 day TTL
            )
        except Exception:
            pass

    def _generate_pattern_signature(self, error_message: str) -> str:
        normalized = re.sub(r"\d+\.\d+\.\d+\.\d+", "<IP>", error_message)
        normalized = re.sub(r":\d+", ":<PORT>", normalized)
        normalized = re.sub(r"[a-f0-9]{8,}", "<ID>", normalized.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _classify_failure(self, error_message: str) -> tuple[FailureCategory, str]:
        error_lower = error_message.lower()
        for category, rules in PATTERN_RULES.items():
            for pattern, description in rules:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return category, description
        return FailureCategory.UNKNOWN, "Unclassified failure"

    def _determine_severity(
        self, category: FailureCategory, service: str, error_message: str,
    ) -> Severity:
        if any(svc in service.lower() for svc in CRITICAL_SERVICES):
            if category in [FailureCategory.RESOURCE, FailureCategory.DEPENDENCY]:
                return Severity.CRITICAL
            return Severity.HIGH

        if category == FailureCategory.RESOURCE:
            return Severity.HIGH

        pattern_sig = self._generate_pattern_signature(error_message)
        if pattern_sig in self.patterns and self.patterns[pattern_sig].occurrences > 10:
            return Severity.HIGH

        severity_map = {
            FailureCategory.INFERENCE: Severity.MEDIUM,
            FailureCategory.NETWORK: Severity.MEDIUM,
            FailureCategory.CONFIGURATION: Severity.LOW,
            FailureCategory.PERMISSION: Severity.MEDIUM,
            FailureCategory.DATA: Severity.LOW,
            FailureCategory.TIMEOUT: Severity.MEDIUM,
            FailureCategory.UNKNOWN: Severity.LOW,
        }
        return severity_map.get(category, Severity.LOW)

    async def record_failure(
        self,
        service: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> FailureEvent:
        now = datetime.now(timezone.utc)
        category, description = self._classify_failure(error_message)
        severity = self._determine_severity(category, service, error_message)
        pattern_sig = self._generate_pattern_signature(error_message)

        event = FailureEvent(
            id=f"fail-{now.strftime('%Y%m%d%H%M%S')}-{len(self.events) % 10000:04d}",
            timestamp=now.isoformat(),
            category=category.value,
            severity=severity.value,
            service=service,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context or {},
            pattern_id=pattern_sig,
        )
        self.events.append(event)

        # Update or create pattern
        if pattern_sig in self.patterns:
            p = self.patterns[pattern_sig]
            p.occurrences += 1
            p.last_seen = event.timestamp
            if service not in p.affected_services:
                p.affected_services.append(service)
        else:
            similar = [e for e in self.events[-100:] if e.pattern_id == pattern_sig]
            if len(similar) >= self.pattern_threshold:
                remediation = []
                if category in REMEDIATION_SUGGESTIONS:
                    remediation = REMEDIATION_SUGGESTIONS[category].get(description, [])

                self.patterns[pattern_sig] = FailurePattern(
                    id=pattern_sig,
                    category=category.value,
                    pattern_signature=pattern_sig,
                    description=description,
                    occurrences=len(similar),
                    first_seen=similar[0].timestamp,
                    last_seen=event.timestamp,
                    affected_services=[service],
                    root_causes=[description],
                    remediation_steps=remediation,
                )

        await self._save_to_redis()
        return event

    async def resolve_failure(self, event_id: str, notes: Optional[str] = None) -> bool:
        for event in self.events:
            if event.id == event_id:
                event.resolved = True
                event.resolution_time = datetime.now(timezone.utc).isoformat()
                event.resolution_notes = notes

                if event.pattern_id and event.pattern_id in self.patterns:
                    p = self.patterns[event.pattern_id]
                    p.resolved_count += 1
                    event_time = datetime.fromisoformat(event.timestamp)
                    resolve_time = datetime.fromisoformat(event.resolution_time)
                    mins = (resolve_time - event_time).total_seconds() / 60
                    if p.mean_time_to_resolve == 0:
                        p.mean_time_to_resolve = mins
                    else:
                        p.mean_time_to_resolve = p.mean_time_to_resolve * 0.8 + mins * 0.2

                await self._save_to_redis()
                return True
        return False

    def analyze(self, hours: int = 24, include_resolved: bool = False) -> DiagnosticReport:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)

        relevant = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp) >= cutoff
            and (include_resolved or not e.resolved)
        ]

        by_category: dict[str, int] = defaultdict(int)
        by_severity: dict[str, int] = defaultdict(int)
        for e in relevant:
            by_category[e.category] += 1
            by_severity[e.severity] += 1

        pattern_counts: dict[str, int] = defaultdict(int)
        for e in relevant:
            if e.pattern_id:
                pattern_counts[e.pattern_id] += 1

        top_patterns = []
        for pid, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            if pid in self.patterns:
                p = self.patterns[pid]
                top_patterns.append({
                    "id": pid,
                    "description": p.description,
                    "count": count,
                    "category": p.category,
                    "remediation": p.remediation_steps[:2],
                })

        recommendations = self._recommendations(relevant, dict(by_category), dict(by_severity))
        health_score = self._health_score(len(relevant), dict(by_severity), hours)
        trend = self._trend(hours)

        return DiagnosticReport(
            generated_at=now.isoformat(),
            time_range_hours=hours,
            total_failures=len(relevant),
            failures_by_category=dict(by_category),
            failures_by_severity=dict(by_severity),
            top_patterns=top_patterns,
            recommendations=recommendations,
            health_score=health_score,
            trend=trend,
        )

    def _recommendations(self, events, by_cat, by_sev) -> list[str]:
        recs = []
        if by_sev.get("critical", 0) > 0:
            recs.append(f"URGENT: {by_sev['critical']} critical failures need immediate attention")
        if by_cat:
            top = max(by_cat.items(), key=lambda x: x[1])
            if top[1] >= 3:
                recs.append(f"Focus on {top[0]} issues — {top[1]} occurrences")
        if by_cat.get("resource", 0) >= 2:
            recs.append("Resource constraints detected — check GPU VRAM and disk space")
        if by_cat.get("inference", 0) >= 2:
            recs.append("Inference issues — verify vLLM health on FOUNDRY and WORKSHOP")
        for e in events[:10]:
            if e.pattern_id and e.pattern_id in self.patterns:
                p = self.patterns[e.pattern_id]
                if p.remediation_steps and p.occurrences > 5:
                    rec = f"Recurring: {p.description} — {p.remediation_steps[0]}"
                    if rec not in recs:
                        recs.append(rec)
        if not recs:
            recs.append("No critical issues — cluster operating normally")
        return recs[:6]

    def _health_score(self, failure_count, by_sev, hours) -> float:
        score = 100.0
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 0.5}
        for sev, count in by_sev.items():
            score -= count * weights.get(sev, 1)
        if hours > 24:
            score *= 1 + (hours - 24) / 100
        return max(0.0, min(100.0, score))

    def _trend(self, hours: int) -> str:
        now = datetime.now(timezone.utc)
        current_cutoff = now - timedelta(hours=hours)
        previous_cutoff = current_cutoff - timedelta(hours=hours)

        current = sum(
            1 for e in self.events
            if datetime.fromisoformat(e.timestamp) >= current_cutoff
        )
        previous = sum(
            1 for e in self.events
            if previous_cutoff <= datetime.fromisoformat(e.timestamp) < current_cutoff
        )

        if previous == 0:
            return "stable" if current < 5 else "degrading"
        ratio = current / previous
        if ratio < 0.7:
            return "improving"
        elif ratio > 1.3:
            return "degrading"
        return "stable"

    def suggest_auto_remediation(self, event: FailureEvent) -> Optional[dict]:
        if not event.pattern_id or event.pattern_id not in self.patterns:
            return None

        pattern = self.patterns[event.pattern_id]
        auto = {
            "Container down": {
                "action": f"Restart container: {event.service}",
                "command": f"docker restart {event.service}",
                "confidence": 0.8,
                "requires_confirmation": False,
            },
            "Disk space exhaustion": {
                "action": "Clean Docker system",
                "command": "docker system prune -f",
                "confidence": 0.6,
                "requires_confirmation": True,
            },
            "GPU memory exhaustion": {
                "action": "Restart vLLM service",
                "command": f"sudo systemctl restart {event.service}",
                "confidence": 0.5,
                "requires_confirmation": True,
            },
            "Redis connection failure": {
                "action": "Restart Redis container",
                "command": "python3 scripts/vault-ssh.py 'docker restart athanor-redis'",
                "confidence": 0.7,
                "requires_confirmation": False,
            },
            "NFS stale handle": {
                "action": "Remount NFS",
                "command": "sudo umount -f /mnt/vault/models && sudo mount -a",
                "confidence": 0.9,
                "requires_confirmation": False,
            },
        }
        return auto.get(pattern.description)

    async def execute_auto_remediation(self, event: FailureEvent) -> Optional[dict]:
        """Execute auto-remediation for a failure if safe.

        Only executes actions that don't require confirmation.
        Records the action and marks the failure as resolved on success.
        """
        suggestion = self.suggest_auto_remediation(event)
        if not suggestion:
            return {"status": "no_remediation", "event_id": event.id}

        if suggestion.get("requires_confirmation"):
            return {
                "status": "needs_confirmation",
                "event_id": event.id,
                "action": suggestion["action"],
                "command": suggestion["command"],
            }

        # Execute the remediation
        import asyncio
        import subprocess
        import logging

        logger = logging.getLogger(__name__)
        command = suggestion["command"]

        logger.info(
            "Auto-remediating %s: %s (confidence=%.2f)",
            event.service, suggestion["action"], suggestion["confidence"],
        )

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            success = result.returncode == 0
            if success:
                await self.resolve_failure(
                    event.id,
                    notes=f"Auto-remediated: {suggestion['action']}",
                )

            return {
                "status": "executed",
                "event_id": event.id,
                "action": suggestion["action"],
                "command": command,
                "success": success,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else "",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "event_id": event.id,
                "action": suggestion["action"],
            }
        except Exception as e:
            return {
                "status": "error",
                "event_id": event.id,
                "error": str(e),
            }

    async def auto_remediate_recent(self, hours: int = 1) -> list[dict]:
        """Auto-remediate all unresolved failures from the last N hours.

        Only acts on safe (no-confirmation) remediations.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        results = []

        for event in self.events:
            if event.resolved:
                continue
            if datetime.fromisoformat(event.timestamp) < cutoff:
                continue

            result = await self.execute_auto_remediation(event)
            if result and result.get("status") == "executed":
                results.append(result)

        return results


# Singleton
_engine = SelfDiagnosisEngine()


def get_diagnosis_engine() -> SelfDiagnosisEngine:
    return _engine


# FastAPI router
def create_diagnosis_router():
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/v1/diagnosis", tags=["diagnosis"])

    class FailureInput(BaseModel):
        service: str
        error_message: str
        stack_trace: Optional[str] = None
        context: Optional[dict] = None

    class ResolutionInput(BaseModel):
        event_id: str
        notes: Optional[str] = None

    @router.post("/failure")
    async def record_failure(inp: FailureInput):
        event = await _engine.record_failure(
            service=inp.service,
            error_message=inp.error_message,
            stack_trace=inp.stack_trace,
            context=inp.context,
        )
        return {
            "event_id": event.id,
            "category": event.category,
            "severity": event.severity,
            "pattern_id": event.pattern_id,
        }

    @router.post("/resolve")
    async def resolve(inp: ResolutionInput):
        ok = await _engine.resolve_failure(event_id=inp.event_id, notes=inp.notes)
        if not ok:
            raise HTTPException(404, "Event not found")
        return {"status": "resolved", "event_id": inp.event_id}

    @router.get("/report")
    async def report(hours: int = 24):
        return asdict(_engine.analyze(hours=hours))

    @router.get("/patterns")
    async def patterns():
        return {
            "patterns": [
                {
                    "id": p.id,
                    "description": p.description,
                    "category": p.category,
                    "occurrences": p.occurrences,
                    "last_seen": p.last_seen,
                }
                for p in _engine.patterns.values()
            ]
        }

    @router.get("/patterns/{pattern_id}")
    async def pattern_detail(pattern_id: str):
        p = _engine.patterns.get(pattern_id)
        if not p:
            raise HTTPException(404, "Pattern not found")
        return asdict(p)

    @router.get("/remediation/{event_id}")
    async def remediation(event_id: str):
        event = next((e for e in _engine.events if e.id == event_id), None)
        if not event:
            raise HTTPException(404, "Event not found")
        return {"event_id": event_id, "remediation": _engine.suggest_auto_remediation(event)}

    @router.get("/health")
    async def health():
        report = _engine.analyze(hours=1)
        return {
            "status": "healthy" if report.health_score >= 80 else "degraded",
            "health_score": report.health_score,
            "recent_failures": report.total_failures,
            "trend": report.trend,
        }

    @router.get("/inference")
    async def inference_health():
        """Check all inference endpoints."""
        import httpx

        endpoints = {
            "vllm-reasoning": "http://192.168.1.244:8000/health",
            "vllm-coding": "http://192.168.1.244:8004/health",
            "vllm-creative": "http://192.168.1.244:8002/health",
            "vllm-fast": "http://192.168.1.225:8100/health",
            "litellm": "http://192.168.1.203:4000/health",
            "embedding": "http://192.168.1.244:8001/health",
        }

        results = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in endpoints.items():
                try:
                    headers = {}
                    if "4000" in url:
                        headers["Authorization"] = "Bearer sk-athanor-litellm-2026"
                    resp = await client.get(url, headers=headers)
                    results[name] = {
                        "status": "healthy" if resp.status_code == 200 else "degraded",
                        "status_code": resp.status_code,
                    }
                except Exception as e:
                    results[name] = {"status": "down", "error": str(e)[:200]}

        healthy = sum(1 for r in results.values() if r["status"] == "healthy")
        total = len(results)
        pct = (healthy / total) * 100 if total else 0

        return {
            "status": "healthy" if pct >= 66 else "degraded" if pct >= 33 else "critical",
            "health_score": pct,
            "services": results,
            "healthy_count": healthy,
            "total_count": total,
        }

    @router.post("/auto-remediate/{event_id}")
    async def auto_remediate_event(event_id: str):
        """Execute auto-remediation for a specific event."""
        event = next((e for e in _engine.events if e.id == event_id), None)
        if not event:
            raise HTTPException(404, "Event not found")
        return await _engine.execute_auto_remediation(event)

    @router.post("/auto-remediate")
    async def auto_remediate_recent(hours: int = 1):
        """Auto-remediate all safe unresolved failures from last N hours."""
        results = await _engine.auto_remediate_recent(hours=hours)
        return {"remediated": len(results), "results": results}

    return router
