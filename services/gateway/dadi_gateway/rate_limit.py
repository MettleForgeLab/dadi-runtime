from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class Bucket:
    capacity: int
    refill_per_sec: float
    tokens: float
    updated_at: float


def _now() -> float:
    return time.time()


class InMemoryRateLimiter:
    """In-memory token bucket limiter.

    Note: For multi-instance production, replace with Redis or gateway-level rate limiting (NGINX/Envoy).
    """

    def __init__(self) -> None:
        self._buckets: Dict[Tuple[str, str], Bucket] = {}

    def allow(self, tenant: str, lane: str, capacity: int, refill_per_sec: float) -> bool:
        key = (tenant, lane)
        now = _now()
        b = self._buckets.get(key)
        if b is None:
            b = Bucket(capacity=capacity, refill_per_sec=refill_per_sec, tokens=float(capacity), updated_at=now)
            self._buckets[key] = b

        # refill
        elapsed = max(0.0, now - b.updated_at)
        b.tokens = min(float(b.capacity), b.tokens + elapsed * b.refill_per_sec)
        b.updated_at = now

        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True
        return False


def classify_lane(path: str, method: str) -> str:
    # High-risk byte endpoints
    if path.endswith("/content"):
        return "bytes"
    if "/bundles/" in path and path.endswith("/download"):
        return "bundle_download"
    # Bundle/evidence creation (expensive)
    if method == "POST" and path.endswith("/bundle"):
        return "bundle_create"
    if method == "POST" and path.endswith("/evidence"):
        return "evidence_create"
    # Artifact uploads
    if method == "POST" and path == "/artifacts":
        return "artifact_upload"
    # Default metadata lane
    return "meta"


def lane_limits(lane: str) -> tuple[int, float]:
    """Return (capacity, refill_per_sec). Override via env if desired."""
    # Defaults are intentionally conservative for bytes and expensive endpoints.
    if lane == "bytes":
        return (int(os.getenv("DADI_RL_BYTES_CAP", "30")), float(os.getenv("DADI_RL_BYTES_RPS", "0.5")))
    if lane == "bundle_download":
        return (int(os.getenv("DADI_RL_BDL_DL_CAP", "10")), float(os.getenv("DADI_RL_BDL_DL_RPS", "0.1")))
    if lane == "bundle_create":
        return (int(os.getenv("DADI_RL_BDL_CREATE_CAP", "5")), float(os.getenv("DADI_RL_BDL_CREATE_RPS", "0.05")))
    if lane == "evidence_create":
        return (int(os.getenv("DADI_RL_EVID_CREATE_CAP", "5")), float(os.getenv("DADI_RL_EVID_CREATE_RPS", "0.05")))
    if lane == "artifact_upload":
        return (int(os.getenv("DADI_RL_UPLOAD_CAP", "10")), float(os.getenv("DADI_RL_UPLOAD_RPS", "0.1")))
    return (int(os.getenv("DADI_RL_META_CAP", "120")), float(os.getenv("DADI_RL_META_RPS", "2.0")))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Tenant-scoped rate limiting.

    Requires request.state.tenant_id to be set by auth middleware.
    If tenant_id is not set, applies a shared 'anonymous' tenant bucket.

    Disable with DADI_RATE_LIMIT_ENABLED=false
    """

    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("DADI_RATE_LIMIT_ENABLED", "true").strip().lower() in ("1", "true", "yes")
        self.limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        tenant = getattr(request.state, "tenant_id", None) or "anonymous"
        lane = classify_lane(request.url.path, request.method)
        cap, rps = lane_limits(lane)

        if not self.limiter.allow(tenant, lane, cap, rps):
            return JSONResponse(
                {"detail": "Too Many Requests", "tenant": tenant, "lane": lane},
                status_code=429
            )

        return await call_next(request)
