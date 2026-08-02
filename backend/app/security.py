"""Small dependency-free HTTP abuse controls for the single-node deployment."""

import math
import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_s
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(events[0] + window_s - now))
                return False, retry_after
            events.append(now)
            return True, 0


limiter = SlidingWindowLimiter()


def client_ip(headers, fallback: str) -> str:
    """Use the address supplied by the ASGI server for abuse controls."""
    return fallback
