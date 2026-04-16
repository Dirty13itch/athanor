"""In-memory sliding-window circuit breaker for the Athanor Watchdog MVW.

Phase 1: counters reset on watchdog restart (acceptable for MVW — a restart
clears the slate naturally). Phase 2 will swap to Redis ZADD/ZRANGEBYSCORE
with the same API.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque


class CircuitBreaker:
    def __init__(self, window_seconds: int = 3600):
        self.window_seconds = window_seconds
        self.attempts: dict[str, deque] = defaultdict(deque)
        self.last_attempt: dict[str, float] = {}

    def _prune(self, service_id: str) -> None:
        cutoff = time.time() - self.window_seconds
        q = self.attempts[service_id]
        while q and q[0] < cutoff:
            q.popleft()

    def can_attempt(
        self,
        service_id: str,
        max_per_hour: int,
        cooldown_seconds: int = 120,
    ) -> bool:
        if max_per_hour <= 0:
            return False  # never auto-remediate
        self._prune(service_id)
        if len(self.attempts[service_id]) >= max_per_hour:
            return False
        last = self.last_attempt.get(service_id, 0)
        if time.time() - last < cooldown_seconds:
            return False
        return True

    def record_attempt(self, service_id: str) -> None:
        now = time.time()
        self.attempts[service_id].append(now)
        self.last_attempt[service_id] = now

    def reset(self, service_id: str) -> None:
        self.attempts[service_id].clear()
        self.last_attempt.pop(service_id, None)

    def state_snapshot(self) -> dict:
        out = {}
        for sid in list(self.attempts.keys()):
            self._prune(sid)
            out[sid] = {
                "attempts_in_window": len(self.attempts[sid]),
                "last_attempt": self.last_attempt.get(sid),
            }
        return out
