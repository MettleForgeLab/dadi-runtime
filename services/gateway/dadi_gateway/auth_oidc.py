\
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Tuple

import requests
import jwt  # PyJWT
from jwt import PyJWKClient
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class OIDCConfig:
    issuer: str
    audience: str
    jwks_url: str
    tenant_claim: str
    scope_claim: str
    clock_skew_seconds: int
    jwks_cache_ttl_seconds: int


def _require_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def load_config() -> OIDCConfig:
    issuer = _require_env("DADI_OIDC_ISSUER")
    audience = _require_env("DADI_OIDC_AUDIENCE")
    jwks_url = _require_env("DADI_OIDC_JWKS_URL")

    tenant_claim = os.getenv("DADI_TENANT_CLAIM", "tenant_id").strip() or "tenant_id"
    scope_claim = os.getenv("DADI_SCOPE_CLAIM", "scope").strip() or "scope"
    clock_skew_seconds = int(os.getenv("DADI_CLOCK_SKEW_SECONDS", "60"))
    jwks_cache_ttl_seconds = int(os.getenv("DADI_JWKS_CACHE_TTL_SECONDS", "300"))

    return OIDCConfig(
        issuer=issuer,
        audience=audience,
        jwks_url=jwks_url,
        tenant_claim=tenant_claim,
        scope_claim=scope_claim,
        clock_skew_seconds=clock_skew_seconds,
        jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
    )


def parse_scopes(payload: Dict[str, Any], scope_claim: str) -> Set[str]:
    v = payload.get(scope_claim)
    if v is None:
        return set()
    if isinstance(v, str):
        return set(s for s in v.split(" ") if s)
    if isinstance(v, list):
        return set(str(s) for s in v)
    return set()


class JWKSCache:
    def __init__(self, jwks_url: str, ttl_seconds: int) -> None:
        self.jwks_url = jwks_url
        self.ttl_seconds = ttl_seconds
        self._cached_at: float = 0.0
        self._jwks_client: Optional[PyJWKClient] = None

    def client(self) -> PyJWKClient:
        now = time.time()
        if self._jwks_client is None or (now - self._cached_at) > self.ttl_seconds:
            # PyJWKClient does its own fetching; we refresh by recreating it.
            self._jwks_client = PyJWKClient(self.jwks_url)
            self._cached_at = now
        return self._jwks_client


class OIDCAuthMiddleware(BaseHTTPMiddleware):
    """
    OIDC/JWKS JWT verification middleware.

    Requires:
      DADI_AUTH_MODE=oidc
      DADI_OIDC_ISSUER, DADI_OIDC_AUDIENCE, DADI_OIDC_JWKS_URL
    """

    def __init__(self, app):
        super().__init__(app)
        self.mode = os.getenv("DADI_AUTH_MODE", "off").strip().lower()
        if self.mode == "oidc":
            self.cfg = load_config()
            self.cache = JWKSCache(self.cfg.jwks_url, self.cfg.jwks_cache_ttl_seconds)
        else:
            self.cfg = None
            self.cache = None

    async def dispatch(self, request: Request, call_next):
        if self.mode != "oidc":
            return await call_next(request)

        assert self.cfg is not None and self.cache is not None

        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        token = auth.split(" ", 1)[1].strip()

        try:
            signing_key = self.cache.client().get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256", "ES256", "EdDSA"],  # accept common OIDC algs; actual token dictates
                audience=self.cfg.audience,
                issuer=self.cfg.issuer,
                options={
                    "require": ["exp", "iss"],
                },
                leeway=self.cfg.clock_skew_seconds,
            )
        except Exception as e:
            return JSONResponse({"detail": f"Unauthorized: {str(e)}"}, status_code=401)

        tenant_id = payload.get(self.cfg.tenant_claim)
        if not isinstance(tenant_id, str) or not tenant_id:
            return JSONResponse({"detail": "Unauthorized: missing tenant claim"}, status_code=401)

        request.state.tenant_id = tenant_id
        request.state.subject = payload.get("sub")
        request.state.scopes = parse_scopes(payload, self.cfg.scope_claim)

        return await call_next(request)
