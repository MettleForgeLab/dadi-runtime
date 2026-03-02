from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

@dataclass(frozen=True)
class Policy:
    content_enabled: bool
    content_require_auth: bool
    content_require_explicit_header: bool
    explicit_header_name: str
    explicit_header_value: str

def load_policy(path: str) -> Policy:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ce = data.get("content_endpoints", {})
    return Policy(
        content_enabled=bool(ce.get("enabled", True)),
        content_require_auth=bool(ce.get("require_auth", True)),
        content_require_explicit_header=bool(ce.get("require_explicit_header", True)),
        explicit_header_name=str(ce.get("explicit_header_name", "X-DADI-Allow-Content")),
        explicit_header_value=str(ce.get("explicit_header_value", "true")),
    )

def bearer_token_required(req: Request, expected_token: str) -> bool:
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth:
        return False
    if not auth.lower().startswith("bearer "):
        return False
    token = auth.split(" ", 1)[1].strip()
    return token == expected_token

class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Bearer token auth.

    - Controlled by env:
      - DADI_AUTH_MODE=bearer|off (default off)
      - DADI_BEARER_TOKEN=<secret>
      - DADI_POLICY_PATH=/path/to/policy.json (optional)
    """

    def __init__(self, app, policy: Optional[Policy] = None):
        super().__init__(app)
        self.mode = os.getenv("DADI_AUTH_MODE", "off").lower()
        self.expected = os.getenv("DADI_BEARER_TOKEN", "")
        self.policy = policy

    async def dispatch(self, request: Request, call_next):
        if self.mode == "off":
            return await call_next(request)

        if self.mode != "bearer":
            return JSONResponse({"detail": "Unsupported auth mode"}, status_code=500)

        if not self.expected:
            return JSONResponse({"detail": "DADI_BEARER_TOKEN not set"}, status_code=500)

        # Auth required for all routes by default
        if not bearer_token_required(request, self.expected):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)

def allow_content(policy: Policy, request: Request) -> bool:
    if not policy.content_enabled:
        return False
    if policy.content_require_explicit_header:
        v = request.headers.get(policy.explicit_header_name)
        if v != policy.explicit_header_value:
            return False
    return True
