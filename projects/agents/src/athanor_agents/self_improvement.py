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
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
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
            except Exception:
                pass

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
            except Exception:
                pass

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
        endpoints = {
            "vllm-reasoning": "http://192.168.1.244:8000/health",
            "vllm-creative": "http://192.168.1.244:8002/health",
            "vllm-coding": "http://192.168.1.244:8004/health",
            "vllm-fast": "http://192.168.1.225:8100/health",
            "litellm": "http://192.168.1.203:4000/health",
            "embedding": "http://192.168.1.189:8001/health",
        }

        ok = 0
        details = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in endpoints.items():
                try:
                    headers = {}
                    if "4000" in url:
                        headers["Authorization"] = "Bearer sk-athanor-litellm-2026"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        ok += 1
                        details[name] = "healthy"
                    else:
                        details[name] = f"status_{resp.status_code}"
                except Exception as e:
                    details[name] = f"error: {str(e)[:50]}"

        return ok, len(endpoints), details

    async def _benchmark_inference_latency(self) -> tuple[float, float, dict]:
        """Measure LLM inference latency via LiteLLM."""
        import time
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                start = time.time()
                resp = await client.post(
                    "http://192.168.1.203:4000/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-athanor-litellm-2026"},
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
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get("http://192.168.1.203:6333/collections")
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
                resp = await client.get("http://192.168.1.244:9000/v1/agents")
                if resp.status_code == 200:
                    agents = resp.json()
                    count = len(agents) if isinstance(agents, list) else agents.get("count", 0)
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
                self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
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
        except Exception:
            pass

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
        except Exception:
            pass

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
        """Validate a proposal (syntax check for Python, YAML validation)."""
        proposal = next((p for p in self.proposals if p.id == proposal_id), None)
        if not proposal:
            return {"error": "Proposal not found"}

        proposal.status = ImprovementStatus.TESTING.value
        proposal.tested_at = datetime.now(timezone.utc).isoformat()
        proposal.baseline_scores = self.benchmarks.get_baseline()

        results = {"valid": True, "checks": []}

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

    async def get_improvement_summary(self) -> dict[str, Any]:
        """Summary of improvement activity."""
        return {
            "total_proposals": len(self.proposals),
            "pending": len([p for p in self.proposals if p.status == ImprovementStatus.PROPOSED.value]),
            "validated": len([p for p in self.proposals if p.status == ImprovementStatus.VALIDATED.value]),
            "deployed": len([p for p in self.proposals if p.status == ImprovementStatus.DEPLOYED.value]),
            "failed": len([p for p in self.proposals if p.status == ImprovementStatus.FAILED.value]),
            "archive_entries": len(self.archive),
            "benchmark_results": len(self.benchmarks.results),
            "latest_baseline": self.benchmarks.get_baseline(),
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
    from fastapi import APIRouter
    from pydantic import BaseModel

    router = APIRouter(prefix="/v1/improvement", tags=["self-improvement"])

    class ProposalInput(BaseModel):
        title: str
        description: str
        category: str = "prompt"
        target_files: list[str] = []
        proposed_changes: dict[str, str] = {}
        expected_improvement: str = ""
        benchmark_targets: list[str] = []

    @router.post("/benchmarks/run")
    async def run_benchmarks():
        """Run the full benchmark suite."""
        engine = get_improvement_engine()
        return await engine.run_benchmark_suite()

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
    async def create_proposal(inp: ProposalInput):
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
        return asdict(proposal)

    @router.get("/proposals")
    async def list_proposals(status: str = ""):
        engine = get_improvement_engine()
        proposals = engine.proposals
        if status:
            proposals = [p for p in proposals if p.status == status]
        return {"proposals": [asdict(p) for p in proposals]}

    @router.post("/proposals/{proposal_id}/validate")
    async def validate(proposal_id: str):
        engine = get_improvement_engine()
        return await engine.validate_proposal(proposal_id)

    @router.get("/summary")
    async def summary():
        engine = get_improvement_engine()
        return await engine.get_improvement_summary()

    return router
