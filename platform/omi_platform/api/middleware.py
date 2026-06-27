"""API middleware for rate limiting, logging, and security."""
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio

# Simple in-memory rate limiter (for production, use Redis)
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()

    async def check(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        async with self.lock:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=self.window_seconds)

            # Remove old requests outside the window
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff
            ]

            # Check limit
            if len(self.requests[client_id]) >= self.max_requests:
                return False

            # Record this request
            self.requests[client_id].append(now)
            return True

# Global limiter instance
_limiter = RateLimiter(max_requests=100, window_seconds=60)

async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting based on client IP."""
    client_ip = request.client.host if request.client else "unknown"

    # Exempt health checks
    if request.url.path in ["/health", "/health/ready"]:
        return await call_next(request)

    # Check rate limit
    allowed = await _limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    return await call_next(request)
