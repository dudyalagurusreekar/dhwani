"""
API Security: Rate Limiter Layer for Dhwani Backend.

Provides SlowAPI integration and high-performance in-memory sliding-window rate limiting
to protect against Denial-of-Service (DoS) and brute-force attacks on voice detection APIs.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


def get_client_identifier(request: Request) -> str:
    """
    Extracts a unique client identifier from the request:
    1. Authenticated user ID (if available from Bearer token)
    2. X-Forwarded-For header
    3. Client IP address
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request) or "127.0.0.1"


# SlowAPI global limiter instance for FastAPI route decoration
limiter = Limiter(key_func=get_client_identifier, default_limits=["120/minute"])


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Accurately limits request bursts within a sliding time window.
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: Dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> Tuple[bool, Dict[str, int | float]]:
        """
        Evaluates whether a request from `key` is allowed under the rate limit.

        Returns:
            Tuple of (allowed: bool, stats: dict)
        """
        now = time.monotonic()
        expiry = now - self.window_seconds

        with self._lock:
            if key not in self._records:
                self._records[key] = deque()

            timestamps = self._records[key]

            # Purge timestamps outside current window
            while timestamps and timestamps[0] <= expiry:
                timestamps.popleft()

            count = len(timestamps)
            if count < self.max_requests:
                timestamps.append(now)
                remaining = self.max_requests - count - 1
                return True, {
                    "limit": self.max_requests,
                    "remaining": remaining,
                    "reset_seconds": round(self.window_seconds, 2),
                }
            else:
                oldest = timestamps[0]
                retry_after = max(0.1, round(self.window_seconds - (now - oldest), 2))
                return False, {
                    "limit": self.max_requests,
                    "remaining": 0,
                    "retry_after": retry_after,
                }

    def check_or_raise(self, key: str) -> Dict[str, int | float]:
        """
        Evaluates rate limit and raises HTTP 429 Too Many Requests if exceeded.
        """
        allowed, stats = self.is_allowed(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {stats.get('retry_after')} seconds.",
                headers={
                    "X-RateLimit-Limit": str(stats["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(int(stats.get("retry_after", 1))),
                },
            )
        return stats

    def reset(self, key: Optional[str] = None) -> None:
        """Clears request history for a specific key or all keys."""
        with self._lock:
            if key is not None:
                self._records.pop(key, None)
            else:
                self._records.clear()


# Default singleton limiter for audio ingress routes (e.g. 30 requests per minute per IP)
_global_audio_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60.0)


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Returns global sliding window rate limiter instance."""
    return _global_audio_limiter
