"""Small process-local limiter for sensitive endpoints.

For a multi-instance deployment this should be replaced by a shared Redis
counter or an API gateway policy. It still provides safe-by-default protection
for the single-process development/container deployment.
"""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int = 10, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                return False, retry_after
            events.append(now)
            return True, 0


login_limiter = SlidingWindowLimiter(limit=10, window_seconds=60)
register_limiter = SlidingWindowLimiter(limit=5, window_seconds=60)
