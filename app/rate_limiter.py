"""
In-memory sliding-window rate limiter.

Stores request timestamps per key (user_id:ip) and evicts old entries
on each check – no background thread required.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Tuple


class RateLimiter:
    """
    Sliding-window rate limiter backed by an in-memory dict of deques.

    Args:
        max_requests: Maximum number of requests allowed per window.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> Tuple[bool, int, int]:
        """
        Check whether the given key is within its rate limit.

        Returns:
            (allowed, remaining_requests, reset_in_seconds)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._store[key]

            # Evict timestamps outside the window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                reset_in = int(oldest + self.window_seconds - now) + 1
                return False, 0, reset_in

            timestamps.append(now)
            remaining = self.max_requests - len(timestamps)
            return True, remaining, 0
