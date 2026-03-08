"""
Circuit Breaker Pattern for Athanor Inference Services.

Prevents cascading failures by stopping requests to failing services.
Auto-recovers when services come back online.

Ported from Hydra's circuit_breaker.py — logic is directly portable.

Usage:
    breakers = get_circuit_breakers()
    result = await breakers.execute_with_breaker(
        "vllm-reasoning",
        lambda: client.post("http://192.168.1.244:8000/v1/chat/completions", ...),
        fallback=lambda: client.post("http://192.168.1.225:8100/v1/chat/completions", ...),
    )
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"        # Normal, requests allowed
    OPEN = "open"            # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3       # Failures before opening
    success_threshold: int = 2       # Successes to close from half-open
    timeout: float = 30.0            # Seconds before half-open retry
    half_open_max_calls: int = 1     # Max concurrent calls in half-open


@dataclass
class CircuitStats:
    state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    total_failures: int
    total_successes: int


class CircuitBreaker:
    """Circuit breaker for a single service."""

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._half_open_calls = 0

        self._total_failures = 0
        self._total_successes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    def stats(self) -> CircuitStats:
        return CircuitStats(
            state=self._state.value,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_success_time=self._last_success_time,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
        )

    async def _set_state(self, new_state: CircuitState):
        if new_state != self._state:
            old = self._state
            self._state = new_state
            logger.info("Circuit '%s': %s → %s", self.name, old.value, new_state.value)
            if self.on_state_change:
                try:
                    self.on_state_change(self.name, old, new_state)
                except Exception as e:
                    logger.error("State change callback error: %s", e)

    async def can_execute(self) -> bool:
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    if time.time() - self._last_failure_time >= self.config.timeout:
                        await self._set_state(CircuitState.HALF_OPEN)
                        self._half_open_calls = 0
                        return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        async with self._lock:
            self._last_success_time = time.time()
            self._total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._set_state(CircuitState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self):
        async with self._lock:
            self._last_failure_time = time.time()
            self._failure_count += 1
            self._total_failures += 1

            if self._state == CircuitState.HALF_OPEN:
                await self._set_state(CircuitState.OPEN)
                self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._set_state(CircuitState.OPEN)

    async def force_open(self):
        async with self._lock:
            await self._set_state(CircuitState.OPEN)
            self._last_failure_time = time.time()

    async def force_close(self):
        async with self._lock:
            await self._set_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and no fallback."""
    pass


class InferenceCircuitBreakers:
    """Manages circuit breakers for all inference services."""

    # Default configs per service type
    SERVICE_CONFIGS = {
        "vllm-reasoning": CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
        "vllm-fast": CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
        "vllm-coding": CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
        "vllm-creative": CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
        "litellm": CircuitBreakerConfig(failure_threshold=5, timeout=15.0),
        "qdrant": CircuitBreakerConfig(failure_threshold=5, timeout=10.0),
        "redis": CircuitBreakerConfig(failure_threshold=5, timeout=10.0),
        "embedding": CircuitBreakerConfig(failure_threshold=3, timeout=20.0),
    }

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def _on_state_change(self, service: str, old: CircuitState, new: CircuitState):
        """Log state changes — could push to diagnosis engine."""
        if new == CircuitState.OPEN:
            logger.warning("Circuit OPEN for %s — blocking requests", service)

    def get_or_create(self, service: str) -> CircuitBreaker:
        if service not in self.breakers:
            config = self.SERVICE_CONFIGS.get(service, CircuitBreakerConfig())
            self.breakers[service] = CircuitBreaker(
                name=service,
                config=config,
                on_state_change=self._on_state_change,
            )
        return self.breakers[service]

    def get_all_stats(self) -> dict[str, dict]:
        return {
            name: {
                "state": cb.stats().state,
                "failures": cb.stats().total_failures,
                "successes": cb.stats().total_successes,
                "last_failure": cb.stats().last_failure_time,
            }
            for name, cb in self.breakers.items()
        }

    async def execute_with_breaker(
        self,
        service: str,
        operation: Callable,
        fallback: Optional[Callable] = None,
    ) -> Any:
        """Execute with circuit breaker protection."""
        breaker = self.get_or_create(service)

        if not await breaker.can_execute():
            if fallback:
                logger.warning("Circuit open for %s, using fallback", service)
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise CircuitOpenError(f"Circuit breaker open for {service}")

        try:
            result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            await breaker.record_success()
            return result
        except Exception:
            await breaker.record_failure()
            raise


# Singleton
_breakers: Optional[InferenceCircuitBreakers] = None


def get_circuit_breakers() -> InferenceCircuitBreakers:
    global _breakers
    if _breakers is None:
        _breakers = InferenceCircuitBreakers()
    return _breakers


# FastAPI router
def create_circuit_breaker_router():
    from fastapi import APIRouter

    router = APIRouter(prefix="/v1/circuits", tags=["circuit-breakers"])

    @router.get("/")
    async def list_circuits():
        return get_circuit_breakers().get_all_stats()

    @router.post("/{service}/open")
    async def force_open(service: str):
        breaker = get_circuit_breakers().get_or_create(service)
        await breaker.force_open()
        return {"service": service, "state": "open"}

    @router.post("/{service}/close")
    async def force_close(service: str):
        breaker = get_circuit_breakers().get_or_create(service)
        await breaker.force_close()
        return {"service": service, "state": "closed"}

    return router
