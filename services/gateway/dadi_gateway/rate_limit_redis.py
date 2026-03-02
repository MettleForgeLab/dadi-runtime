from __future__ import annotations

import os
import time
from typing import Optional, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Redis is optional dependency; import lazily to keep dev simple.

from .rate_limit import classify_lane, lane_limits


class RedisRateLimiter:
    """Redis-backed token bucket limiter.

    Stores per (tenant, lane) in Redis with:
    - tokens
    - updated_at

    NOTE: This is a pragmatic implementation for gateway limiting.
    For high throughput, consider Lua scripts for atomicity.
    """

    def __init__(self, redis_url: str):
        try:
            import redis  # type: ignore
        except Exception as e:
            raise RuntimeError("redis package not installed; add dependency") from e
        self.r = redis.Redis.from_url(redis_url, decode_responses=True)

    def allow(self, tenant: str, lane: str, capacity: int, refill_per_sec: float) -> bool:
        key = f"dadi:rl:{tenant}:{lane}"
        now = time.time()

        # Use WATCH/MULTI for atomic read-modify-write
        with self.r.pipeline() as p:
            while True:
                try:
                    p.watch(key)
                    data = p.hgetall(key)
                    if not data:
                        tokens = float(capacity)
                        updated_at = now
                    else:
                        tokens = float(data.get("tokens", capacity))
                        updated_at = float(data.get("updated_at", now))

                    elapsed = max(0.0, now - updated_at)
                    tokens = min(float(capacity), tokens + elapsed * refill_per_sec)

                    allowed = tokens >= 1.0
                    if allowed:
                        tokens -= 1.0

                    p.multi()
                    p.hset(key, mapping={"tokens": tokens, "updated_at": now})
                    # Expire idle buckets to avoid unbounded growth
                    p.expire(key, 3600)
                    p.execute()
                    return allowed
                except Exception:
                    try:
                        p.reset()
                    except Exception:
                        pass
                    continue


class RateLimitRedisMiddleware(BaseHTTPMiddleware):
    """Tenant-scoped rate limiting with Redis backend.

    Env:
      - DADI_RATE_LIMIT_BACKEND=redis
      - REDIS_URL=redis://redis:6379/0
      - DADI_RATE_LIMIT_ENABLED=true/false
      - Lane configs via DADI_RL_* env vars (see rate_limit.py)
    """

    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("DADI_RATE_LIMIT_ENABLED", "true").strip().lower() in ("1","true","yes")
        self.backend = os.getenv("DADI_RATE_LIMIT_BACKEND", "memory").strip().lower()
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0").strip()
        self.fail_closed = os.getenv("DADI_RATE_LIMIT_FAIL_CLOSED", "true").strip().lower() in ("1","true","yes")

        if self.backend == "redis":
            self.limiter = RedisRateLimiter(self.redis_url)
        else:
            self.limiter = None

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or self.backend != "redis":
            return await call_next(request)

        tenant = getattr(request.state, "tenant_id", None) or "anonymous"
        lane = classify_lane(request.url.path, request.method)
        cap, rps = lane_limits(lane)

        try:
            allowed = self.limiter.allow(tenant, lane, cap, rps)  # type: ignore
        except Exception as e:
            if self.fail_closed:
                return JSONResponse({"detail":"Rate limiter unavailable"}, status_code=503)
            return await call_next(request)

        if not allowed:
            return JSONResponse({"detail":"Too Many Requests","tenant":tenant,"lane":lane}, status_code=429)

        return await call_next(request)
