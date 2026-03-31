"""
Self-Improvement Engine for Athanor.

DGM-inspired (Darwin Gödel Machine) autonomous improvement loop:
1. Run benchmarks → establish baseline
2. Analyze failures → generate improvement proposals
3. Test proposals in sandbox
4. Deploy validated improvements
5. Track improvement history for rollback

Since Athanor is NOT production, the safety boundaries are relaxed:
- Auto-deploy prompt improvements without approval
- Auto-deploy config tuning without approval
- Code changes still require review (git diff shown)
- Infrastructure changes (Ansible, systemd) require approval

Ported from Hydra's self_improvement.py, adapted for Athanor:
- Storage: Redis instead of JSON files
- Benchmarks: Athanor endpoints (vLLM, LiteLLM, agents, Qdrant)
- All async
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

from .config import settings
from .services import registry

logger = logging.getLogger(__name__)


class ImprovementStatus(Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class BenchmarkCategory(Enum):
    INFERENCE_HEALTH = "inference_health"
    INFERENCE_LATENCY = "inference_latency"
    MEMORY_RECALL = "memory_recall"
    AGENT_RELIABILITY = "agent_reliability"
    CACHE_PERFORMANCE = "cache_performance"
    ROUTING_ACCURACY = "routing_accuracy"


@dataclass
class BenchmarkResult:
    benchmark_id: str
    category: str
    name: str
    score: float
    max_score: float
    passed: bool
    timestamp: str
    details: dict = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class ImprovementProposal:
    id: str
    title: str
    description: str
    category: str  # "prompt", "config", "code", "infrastructure"
    target_files: list[str]
    proposed_changes: dict[str, str]
    expected_improvement: str
    benchmark_targets: list[str]
    status: str = ImprovementStatus.PROPOSED.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tested_at: Optional[str] = None
    deployed_at: Optional[str] = None
    baseline_scores: dict[str, float] = field(default_factory=dict)
    test_scores: dict[str, float] = field(default_factory=dict)
    author: str = "autonomous"
    auto_deploy: bool = False


class CapabilityBenchmarks:
    """Benchmark suite for measuring Athanor's capabilities."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                from .config import settings
                self._redis = aioredis.from_url(settings.redis_url, password=settings.redis_password or None, decode_responses=True)
            except Exception:
                return None
        return self._redis

    async def load(self):
        r = await self._get_redis()
        if r:
            try:
                data = await r.get("improvement:benchmarks")
                if data:
                    self.results = [BenchmarkResult(**d) for d in json.loads(data)]
            except Exception as e:
                logger.debug("Improvement Redis load/save failed: %s", e)

    async def save(self):
        r = await self._get_redis()
        if r:
            try:
                # Keep last 500 results
                if len(self.results) > 500:
                    self.results = self.results[-500:]
                await r.set(
                    "improvement:benchmarks",
                    json.dumps([asdict(r) for r in self.results]),
                    ex=86400 * 30,
                )
            except Exception as e:
                logger.debug("Improvement Redis load/save failed: %s", e)

    async def run_benchmark(
        self, category: BenchmarkCategory, name: str, test_fn,
    ) -> BenchmarkResult:
        benchmark_id = f"{category.value}:{name}"
        start = datetime.now(timezone.utc)

        try:
            score, max_score, details = await test_fn()
            duration_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            result = BenchmarkResult(
                benchmark_id=benchmark_id,
                category=category.value,
                name=name,
                score=score,
                max_score=max_score,
                passed=score >= (max_score * 0.8),
                timestamp=datetime.now(timezone.utc).isoformat(),
                details=details,
                duration_ms=duration_ms,
            )
        except Exception as e:
            result = BenchmarkResult(
                benchmark_id=benchmark_id,
                category=category.value,
                name=name,
                score=0,
                max_score=100,
                passed=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"error": str(e)},
            )

        self.results.append(result)
        await self.save()
        return result

    async def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmarks against Athanor infrastructure."""
        results = []

        results.append(await self.run_benchmark(
            BenchmarkCategory.INFERENCE_HEALTH,
            "endpoint_health",
            self._benchmark_inference_health,
        ))
        results.append(await self.run_benchmark(
            BenchmarkCategory.INFERENCE_LATENCY,
            "reasoning_latency",
            self._benchmark_inference_latency,
        ))
        results.append(await self.run_benchmark(
            BenchmarkCategory.MEMORY_RECALL,
            "qdrant_search",
            self._benchmark_memory_recall,
        ))
        results.append(await self.run_benchmark(
            BenchmarkCategory.AGENT_RELIABILITY,
            "agent_health",
            self._benchmark_agent_health,
        ))
        results.append(await self.run_benchmark(
            BenchmarkCategory.ROUTING_ACCURACY,
            "task_classification",
            self._benchmark_routing,
        ))

        return results

    async def _benchmark_inference_health(self) -> tuple[float, float, dict]:
        """Check all vLLM and LiteLLM endpoints."""
        ok = 0
        details = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, service in registry.inference_health_checks.items():
                try:
                    target = service.health_url or service.url()
                    resp = await client.get(target, headers=dict(service.headers))
                    if resp.status_code == 200:
                        ok += 1
                        details[name] = "healthy"
                    else:
                        details[name] = f"status_{resp.status_code}"
                except Exception as e:
                    details[name] = f"error: {str(e)[:50]}"

        return ok, len(registry.inference_health_checks), details

    async def _benchmark_inference_latency(self) -> tuple[float, float, dict]:
        """Measure LLM inference latency via LiteLLM."""
        import time
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                start = time.time()
                resp = await client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers=dict(registry.litellm_headers),
                    json={
                        "model": "fast",
                        "messages": [{"role": "user", "content": "Say hello in 5 words."}],
                        "max_tokens": 20,
                    },
                )
                latency_ms = (time.time() - start) * 1000

                if resp.status_code == 200:
                    # <1s = 100, >5s = 0
                    score = max(0, min(100, 100 - (latency_ms - 1000) / 40))
                    return score, 100, {"latency_ms": round(latency_ms), "status": "success"}
                return 0, 100, {"error": resp.text[:100]}
            except Exception as e:
                return 0, 100, {"error": str(e)}

    async def _benchmark_memory_recall(self) -> tuple[float, float, dict]:
        """Check Qdrant collections are healthy and searchable."""
        from .config import settings
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{settings.qdrant_url}/collections")
                if resp.status_code == 200:
                    collections = resp.json().get("result", {}).get("collections", [])
                    count = len(collections)
                    return min(count * 15, 100), 100, {
                        "collections": count,
                        "names": [c["name"] for c in collections],
                    }
                return 0, 100, {"error": f"status_{resp.status_code}"}
            except Exception as e:
                return 0, 100, {"error": str(e)}

    async def _benchmark_agent_health(self) -> tuple[float, float, dict]:
        """Check agent server health."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(registry.agent_server.url("/v1/agents"))
                if resp.status_code == 200:
                    data = resp.json()
                    agents = data.get("agents", data) if isinstance(data, dict) else data
                    count = len(agents) if isinstance(agents, list) else 0
                    return min(count * 12, 100), 100, {"agents": count}
                return 0, 100, {"error": f"status_{resp.status_code}"}
            except Exception as e:
                return 0, 100, {"error": str(e)}

    async def _benchmark_routing(self) -> tuple[float, float, dict]:
        """Test that routing classifies correctly."""
        from .routing import classify_task, TaskType

        test_cases = [
            ("Write a Python function to sort a list", TaskType.CODE),
            ("What is the capital of France?", TaskType.SIMPLE),
            ("Analyze the tradeoffs between vLLM and SGLang", TaskType.REASONING),
            ("Write a poem about autumn", TaskType.CREATIVE),
            ("Turn off the living room lights", TaskType.HOME),
            ("What movies should I watch tonight?", TaskType.MEDIA),
        ]

        correct = 0
        details = {}
        for prompt, expected in test_cases:
            result = classify_task(prompt)
            if result == expected:
                correct += 1
                details[prompt[:40]] = f"OK ({result.value})"
            else:
                details[prompt[:40]] = f"WRONG: got {result.value}, expected {expected.value}"

        score = (correct / len(test_cases)) * 100
        return score, 100, details

    def get_baseline(self) -> dict[str, float]:
        baseline = {}
        for r in reversed(self.results):
            if r.benchmark_id not in baseline:
                baseline[r.benchmark_id] = r.score
            if len(baseline) >= 10:
                break
        return baseline

    def compare_to_baseline(self, new_results: list[BenchmarkResult]) -> dict:
        baseline = self.get_baseline()
        comparison = {}
        for r in new_results:
            if r.benchmark_id in baseline:
                delta = r.score - baseline[r.benchmark_id]
                comparison[r.benchmark_id] = {
                    "baseline": baseline[r.benchmark_id],
                    "new": r.score,
                    "delta": delta,
                    "improved": delta > 0,
                    "regressed": delta < -5,
                }
            else:
                comparison[r.benchmark_id] = {
                    "baseline": None, "new": r.score, "delta": 0,
                    "improved": False, "regressed": False,
                }
        return comparison


class SelfImprovementEngine:
    """
    Coordinates benchmarking, proposals, testing, and deployment.

    Since Athanor isn't production:
    - Prompt improvements auto-deploy
    - Config tuning auto-deploys
    - Code changes require diff review
    - Infra changes require approval
    """

    # Auto-deploy categories (no approval needed)
    AUTO_DEPLOY_CATEGORIES = {"prompt", "config"}

    def __init__(self):
        self.benchmarks = CapabilityBenchmarks()
        self.proposals: list[ImprovementProposal] = []
        self.archive: list[dict] = []
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                from .config import settings
                self._redis = aioredis.from_url(settings.redis_url, password=settings.redis_password or None, decode_responses=True)
            except Exception:
                return None
        return self._redis

    async def load(self):
        """Load state from Redis."""
        await self.benchmarks.load()
        r = await self._get_redis()
        if not r:
            return
        try:
            data = await r.get("improvement:proposals")
            if data:
                self.proposals = [ImprovementProposal(**p) for p in json.loads(data)]
            data = await r.get("improvement:archive")
            if data:
                self.archive = json.loads(data)
        except Exception as e:
            logger.debug("Improvement state load/save failed: %s", e)

    async def save(self):
        r = await self._get_redis()
        if not r:
            return
        try:
            await r.set(
                "improvement:proposals",
                json.dumps([asdict(p) for p in self.proposals]),
                ex=86400 * 30,
            )
            await r.set(
                "improvement:archive",
                json.dumps(self.archive),
                ex=86400 * 90,
            )
        except Exception as e:
            logger.debug("Improvement state load/save failed: %s", e)

    async def run_benchmark_suite(self) -> dict[str, Any]:
        """Run full benchmark suite and compare to baseline."""
        results = await self.benchmarks.run_all()
        comparison = self.benchmarks.compare_to_baseline(results)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": passed,
            "total": total,
            "pass_rate": passed / total if total else 0,
            "results": [asdict(r) for r in results],
            "comparison": comparison,
        }

    async def propose_improvement(
        self,
        title: str,
        description: str,
        category: str,
        target_files: list[str],
        proposed_changes: dict[str, str],
        expected_improvement: str,
        benchmark_targets: Optional[list[str]] = None,
    ) -> ImprovementProposal:
        """Create an improvement proposal."""
        proposal = ImprovementProposal(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            category=category,
            target_files=target_files,
            proposed_changes=proposed_changes,
            expected_improvement=expected_improvement,
            benchmark_targets=benchmark_targets or [],
            auto_deploy=category in self.AUTO_DEPLOY_CATEGORIES,
        )
        self.proposals.append(proposal)
        await self.save()
        return proposal

    async def validate_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Validate a proposal (forbidden file check + syntax check)."""
        from .constitution import check_forbidden_file

        proposal = next((p for p in self.proposals if p.id == proposal_id), None)
        if not proposal:
            return {"error": "Proposal not found"}

        proposal.status = ImprovementStatus.TESTING.value
        proposal.tested_at = datetime.now(timezone.utc).isoformat()
        proposal.baseline_scores = self.benchmarks.get_baseline()

        results = {"valid": True, "checks": []}

        # AUTO-003: Check all target files against forbidden modifications list
        for target in proposal.target_files:
            allowed, reason = check_forbidden_file(target, actor="self_improvement")
            if not allowed:
                proposal.status = ImprovementStatus.FAILED.value
                results["valid"] = False
                results["checks"].append({"file": target, "status": "forbidden", "error": reason})
                await self.save()
                return {
                    "status": proposal.status,
                    "proposal_id": proposal_id,
                    "results": results,
                    "auto_deploy": False,
                    "ready_to_deploy": False,
                }

        for file_path in proposal.proposed_changes:
            allowed, reason = check_forbidden_file(file_path, actor="self_improvement")
            if not allowed:
                proposal.status = ImprovementStatus.FAILED.value
                results["valid"] = False
                results["checks"].append({"file": file_path, "status": "forbidden", "error": reason})
                await self.save()
                return {
                    "status": proposal.status,
                    "proposal_id": proposal_id,
                    "results": results,
                    "auto_deploy": False,
                    "ready_to_deploy": False,
                }

        for file_path, content in proposal.proposed_changes.items():
            if file_path.endswith(".py"):
                import py_compile
                import tempfile
                import os
                try:
                    fd, tmp = tempfile.mkstemp(suffix=".py")
                    os.write(fd, content.encode())
                    os.close(fd)
                    py_compile.compile(tmp, doraise=True)
                    os.unlink(tmp)
                    results["checks"].append({"file": file_path, "status": "valid"})
                except py_compile.PyCompileError as e:
                    results["valid"] = False
                    results["checks"].append({"file": file_path, "status": "invalid", "error": str(e)})
                    if os.path.exists(tmp):
                        os.unlink(tmp)

            elif file_path.endswith((".yml", ".yaml")):
                import yaml
                try:
                    yaml.safe_load(content)
                    results["checks"].append({"file": file_path, "status": "valid"})
                except yaml.YAMLError as e:
                    results["valid"] = False
                    results["checks"].append({"file": file_path, "status": "invalid", "error": str(e)})

        if results["valid"]:
            proposal.status = ImprovementStatus.VALIDATED.value
        else:
            proposal.status = ImprovementStatus.FAILED.value

        await self.save()
        return {
            "status": proposal.status,
            "proposal_id": proposal_id,
            "results": results,
            "auto_deploy": proposal.auto_deploy,
            "ready_to_deploy": results["valid"],
        }

    async def run_improvement_cycle(self) -> dict[str, Any]:
        """Full improvement cycle: benchmarks → patterns → proposals → auto-deploy.

        This is the self-feeding loop that makes Athanor an athanor.
        Runs daily after pattern detection (5:30 AM).
        """
        await self.load()
        cycle_log: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "benchmarks": None,
            "patterns_consumed": 0,
            "proposals_generated": 0,
            "auto_deployed": 0,
            "errors": [],
        }

        # 1. Run benchmarks and compare to baseline
        try:
            bench_result = await self.run_benchmark_suite()
            cycle_log["benchmarks"] = {
                "passed": bench_result["passed"],
                "total": bench_result["total"],
                "pass_rate": bench_result["pass_rate"],
            }
        except Exception as e:
            cycle_log["errors"].append(f"benchmarks: {e}")
            bench_result = {"comparison": {}, "results": []}

        # 2. Read today's pattern detection report
        patterns_report: dict = {}
        try:
            r = await self._get_redis()
            if r:
                data = await r.get("athanor:patterns:report")
                if data:
                    patterns_report = json.loads(data)
                    cycle_log["patterns_consumed"] = len(
                        patterns_report.get("patterns", [])
                    )
        except Exception as e:
            cycle_log["errors"].append(f"patterns: {e}")

        # 3. Generate proposals from regressions
        for bid, comp in bench_result.get("comparison", {}).items():
            if comp.get("regressed"):
                try:
                    proposal = await self.propose_improvement(
                        title=f"Fix regression: {bid}",
                        description=(
                            f"Benchmark {bid} regressed from "
                            f"{comp['baseline']:.1f} to {comp['new']:.1f} "
                            f"(delta: {comp['delta']:.1f}). "
                            f"Investigate root cause and restore performance."
                        ),
                        category="config",
                        target_files=[],
                        proposed_changes={},
                        expected_improvement=f"Restore {bid} to baseline ({comp['baseline']:.1f}+)",
                        benchmark_targets=[bid],
                    )
                    cycle_log["proposals_generated"] += 1
                    logger.info("Improvement cycle: proposed fix for regression %s", bid)
                except Exception as e:
                    cycle_log["errors"].append(f"proposal for {bid}: {e}")

        # 4. Generate proposals from pattern recommendations
        for rec in patterns_report.get("recommendations", []):
            try:
                proposal = await self.propose_improvement(
                    title=f"Pattern insight: {rec[:60]}",
                    description=rec,
                    category="prompt",
                    target_files=[],
                    proposed_changes={},
                    expected_improvement="Reduce failure rate / improve agent quality",
                )
                cycle_log["proposals_generated"] += 1
            except Exception as e:
                cycle_log["errors"].append(f"pattern proposal: {e}")

        # 5. Log the cycle results
        try:
            r = await self._get_redis()
            if r:
                await r.set(
                    "improvement:last_cycle",
                    json.dumps(cycle_log),
                    ex=86400 * 7,
                )
                # Append to cycle history (keep last 30)
                history_key = "improvement:cycle_history"
                await r.lpush(history_key, json.dumps(cycle_log))
                await r.ltrim(history_key, 0, 29)
        except Exception as e:
            cycle_log["errors"].append(f"save cycle: {e}")

        logger.info(
            "Improvement cycle complete: %d benchmarks (%d%% pass), "
            "%d patterns consumed, %d proposals generated",
            bench_result.get("total", 0),
            int(bench_result.get("pass_rate", 0) * 100),
            cycle_log["patterns_consumed"],
            cycle_log["proposals_generated"],
        )

        return cycle_log

    async def get_improvement_summary(self) -> dict[str, Any]:
        """Summary of improvement activity."""
        # Include last cycle info
        last_cycle = None
        try:
            r = await self._get_redis()
            if r:
                data = await r.get("improvement:last_cycle")
                if data:
                    last_cycle = json.loads(data)
        except Exception as e:
            logger.debug("Improvement state load/save failed: %s", e)

        return {
            "total_proposals": len(self.proposals),
            "pending": len([p for p in self.proposals if p.status == ImprovementStatus.PROPOSED.value]),
            "validated": len([p for p in self.proposals if p.status == ImprovementStatus.VALIDATED.value]),
            "deployed": len([p for p in self.proposals if p.status == ImprovementStatus.DEPLOYED.value]),
            "failed": len([p for p in self.proposals if p.status == ImprovementStatus.FAILED.value]),
            "archive_entries": len(self.archive),
            "benchmark_results": len(self.benchmarks.results),
            "latest_baseline": self.benchmarks.get_baseline(),
            "last_cycle": last_cycle,
        }


# Singleton
_engine: Optional[SelfImprovementEngine] = None


def get_improvement_engine() -> SelfImprovementEngine:
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine()
    return _engine


# FastAPI router
def create_improvement_router():
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, ValidationError

    from .operator_contract import build_operator_action, emit_operator_audit_event, require_operator_action

    router = APIRouter(prefix="/v1/improvement", tags=["self-improvement"])

    class ProposalInput(BaseModel):
        title: str
        description: str
        category: str = "prompt"
        target_files: list[str] = []
        proposed_changes: dict[str, str] = {}
        expected_improvement: str = ""
        benchmark_targets: list[str] = []

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

    @router.post("/benchmarks/run")
    async def run_benchmarks(request: Request):
        """Run the full benchmark suite."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/improvement/benchmarks/run",
            action_class="admin",
            default_reason="Ran benchmark suite",
        )
        if denial:
            return denial

        engine = get_improvement_engine()
        result = await engine.run_benchmark_suite()
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/improvement/benchmarks/run",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail="Ran benchmark suite",
            metadata={
                "passed": int(result.get("passed", 0) or 0),
                "total": int(result.get("total", 0) or 0),
                "pass_rate": float(result.get("pass_rate", 0.0) or 0.0),
            },
        )
        return result

    @router.get("/benchmarks/baseline")
    async def get_baseline():
        engine = get_improvement_engine()
        return engine.benchmarks.get_baseline()

    @router.get("/benchmarks/history")
    async def benchmark_history(limit: int = 20):
        engine = get_improvement_engine()
        return {
            "results": [asdict(r) for r in engine.benchmarks.results[-limit:]],
        }

    @router.post("/proposals")
    async def create_proposal(request: Request):
        body, action, denial = await _load_operator_body(
            request,
            route="/v1/improvement/proposals",
            action_class="admin",
            default_reason="Created improvement proposal",
        )
        if denial:
            return denial

        try:
            inp = ProposalInput.model_validate(body)
        except ValidationError as exc:
            await emit_operator_audit_event(
                service="agent-server",
                route="/v1/improvement/proposals",
                action_class="admin",
                decision="denied",
                status_code=422,
                action=action,
                detail=str(exc),
            )
            return JSONResponse(status_code=422, content={"error": "Invalid proposal payload", "detail": str(exc)})

        engine = get_improvement_engine()
        proposal = await engine.propose_improvement(
            title=inp.title,
            description=inp.description,
            category=inp.category,
            target_files=inp.target_files,
            proposed_changes=inp.proposed_changes,
            expected_improvement=inp.expected_improvement,
            benchmark_targets=inp.benchmark_targets,
        )
        payload = asdict(proposal)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/improvement/proposals",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Created improvement proposal {payload.get('id', '')}",
            target=str(payload.get("id", "")),
            metadata={
                "category": payload.get("category", ""),
                "target_file_count": len(payload.get("target_files", []) or []),
            },
        )
        return payload

    @router.get("/proposals")
    async def list_proposals(status: str = ""):
        engine = get_improvement_engine()
        proposals = engine.proposals
        if status:
            proposals = [p for p in proposals if p.status == status]
        return {"proposals": [asdict(p) for p in proposals]}

    @router.post("/proposals/{proposal_id}/validate")
    async def validate(proposal_id: str, request: Request):
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/improvement/proposals/{proposal_id}/validate",
            action_class="admin",
            default_reason=f"Validated improvement proposal {proposal_id}",
        )
        if denial:
            return denial

        engine = get_improvement_engine()
        result = await engine.validate_proposal(proposal_id)
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/improvement/proposals/{proposal_id}/validate",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail=f"Validated improvement proposal {proposal_id}",
            target=proposal_id,
            metadata={"valid": bool(result.get("valid", False)) if isinstance(result, dict) else False},
        )
        return result

    @router.post("/cycle")
    async def run_cycle(request: Request):
        """Run a full improvement cycle (benchmarks → patterns → proposals)."""
        _, action, denial = await _load_operator_body(
            request,
            route="/v1/improvement/cycle",
            action_class="admin",
            default_reason="Ran improvement cycle",
        )
        if denial:
            return denial
        engine = get_improvement_engine()
        await engine.load()
        result = await engine.run_improvement_cycle()
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/improvement/cycle",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail="Ran improvement cycle",
            metadata={
                "patterns_consumed": int(result.get("patterns_consumed", 0) or 0),
                "proposals_generated": int(result.get("proposals_generated", 0) or 0),
                "auto_deployed": int(result.get("auto_deployed", 0) or 0),
            },
        )
        return result

    @router.get("/summary")
    async def summary():
        engine = get_improvement_engine()
        await engine.load()
        return await engine.get_improvement_summary()

    @router.post("/trigger")
    async def trigger_nightly(request: Request):
        """Trigger nightly prompt optimization cycle."""
        from .prompt_optimizer import run_nightly_optimization

        _, action, denial = await _load_operator_body(
            request,
            route="/v1/improvement/trigger",
            action_class="admin",
            default_reason="Triggered nightly optimization",
        )
        if denial:
            return denial
        result = await run_nightly_optimization()
        await emit_operator_audit_event(
            service="agent-server",
            route="/v1/improvement/trigger",
            action_class="admin",
            decision="accepted",
            status_code=200,
            action=action,
            detail="Triggered nightly optimization",
            metadata={"status": str(result.get("status", "")) if isinstance(result, dict) else ""},
        )
        return result

    @router.get("/optimization-status")
    async def optimization_status():
        """Get prompt optimization status."""
        from .prompt_optimizer import get_optimization_status
        return await get_optimization_status()

    return router
