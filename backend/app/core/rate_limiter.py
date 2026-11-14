"""
ServicePulse - In-Memory Sliding Window Rate Limiter
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Thread-safe (in single-event-loop async context) in-memory sliding window rate limiter.
    Cleans up old timestamps automatically.
    """

    def __init__(self, requests_per_minute: int = 10, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        # Mapping: key -> list of timestamp floats
        self._records: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check whether key has exceeded rate limit.
        Returns (is_limited, retry_after_seconds).
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Filter records within current window
        valid_records = [ts for ts in self._records[key] if ts > window_start]
        self._records[key] = valid_records

        if len(valid_records) >= self.requests_per_minute:
            oldest = valid_records[0]
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            return True, retry_after

        self._records[key].append(now)
        return False, 0

    def check(self, key: str) -> None:
        """
        Enforce rate limit or raise HTTP 429 Too Many Requests.
        """
        limited, retry_after = self.is_rate_limited(key)
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )


# Global instances for auth and registration endpoints
auth_rate_limiter = SlidingWindowRateLimiter(requests_per_minute=30, window_seconds=60)
registration_rate_limiter = SlidingWindowRateLimiter(requests_per_minute=10, window_seconds=60)


def get_client_ip(request: Request) -> str:
    """Extract client IP handling proxy headers."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def rate_limit_auth(request: Request) -> None:
    """FastAPI dependency for login/auth rate limiting."""
    client_ip = get_client_ip(request)
    auth_rate_limiter.check(f"auth:{client_ip}")


def rate_limit_registration(request: Request) -> None:
    """FastAPI dependency for registration and organization request rate limiting."""
    client_ip = get_client_ip(request)
    registration_rate_limiter.check(f"reg:{client_ip}")
