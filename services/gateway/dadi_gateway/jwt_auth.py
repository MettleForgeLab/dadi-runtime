\
from __future__ import annotations

import base64
import json
import os
import time
import hmac
import hashlib
from typing import Any, Dict, Optional, Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class JWTError(Exception):
    pass


def verify_hs256_jwt(token: str, secret: str) -> Dict[str, Any]:
    """
    Minimal HS256 JWT verification.

    Returns payload dict if valid, raises JWTError otherwise.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("Invalid JWT format")

    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise JWTError("Invalid JWT encoding")

    if header.get("alg") != "HS256":
        raise JWTError("Unsupported alg")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected)

    if not hmac.compare_digest(expected_b64, sig_b64):
        raise JWTError("Invalid signature")

    # exp check (optional)
    exp = payload.get("exp")
    if exp is not None:
        try:
            exp_i = int(exp)
        except Exception:
            raise JWTError("Invalid exp")
        if int(time.time()) >= exp_i:
            raise JWTError("Token expired")

    return payload


def parse_scopes(payload: Dict[str, Any], scope_claim: str = "scope") -> Set[str]:
    v = payload.get(scope_claim)
    if v is None:
        return set()
    if isinstance(v, str):
        return set(s for s in v.split(" ") if s)
    if isinstance(v, list):
        return set(str(s) for s in v)
    return set()


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Gateway middleware:
      - Requires Authorization: Bearer <jwt>
      - Verifies HS256 using DADI_JWT_HS256_SECRET
      - Extracts tenant_id claim to request.state.tenant_id

    Env:
      DADI_AUTH_MODE=jwt
      DADI_JWT_HS256_SECRET=...
      DADI_TENANT_CLAIM=tenant_id
      DADI_SCOPE_CLAIM=scope
    """

    def __init__(self, app):
        super().__init__(app)
        self.mode = os.getenv("DADI_AUTH_MODE", "off").lower()
        self.secret = os.getenv("DADI_JWT_HS256_SECRET", "")
        self.tenant_claim = os.getenv("DADI_TENANT_CLAIM", "tenant_id")
        self.scope_claim = os.getenv("DADI_SCOPE_CLAIM", "scope")

    async def dispatch(self, request: Request, call_next):
        if self.mode != "jwt":
            return await call_next(request)

        if not self.secret:
            return JSONResponse({"detail": "DADI_JWT_HS256_SECRET not set"}, status_code=500)

        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        token = auth.split(" ", 1)[1].strip()

        try:
            payload = verify_hs256_jwt(token, self.secret)
        except JWTError as e:
            return JSONResponse({"detail": f"Unauthorized: {str(e)}"}, status_code=401)

        tenant_id = payload.get(self.tenant_claim)
        if not isinstance(tenant_id, str) or not tenant_id:
            return JSONResponse({"detail": "Unauthorized: missing tenant claim"}, status_code=401)

        request.state.tenant_id = tenant_id
        request.state.subject = payload.get("sub")
        request.state.scopes = parse_scopes(payload, self.scope_claim)

        return await call_next(request)


def require_scope(request: Request, required: str) -> Optional[JSONResponse]:
    scopes: Set[str] = getattr(request.state, "scopes", set())
    if required not in scopes:
        return JSONResponse({"detail": "Forbidden: insufficient scope"}, status_code=403)
    return None
