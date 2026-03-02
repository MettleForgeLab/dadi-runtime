from __future__ import annotations

import os
import requests
from fastapi import APIRouter, HTTPException

from .signing_provider import load_signing_provider

router = APIRouter(tags=["health"])

@router.get("/health/signing")
def health_signing():
    provider = os.getenv("DADI_SIGNING_PROVIDER", "").strip().lower()
    if not provider:
        return {"ok": True, "provider": None, "note": "no signing provider configured"}
    p = load_signing_provider()
    p.healthcheck()
    return {"ok": True, "provider": provider}

@router.get("/health/oidc")
def health_oidc():
    mode = os.getenv("DADI_AUTH_MODE", "off").strip().lower()
    if mode != "oidc":
        return {"ok": True, "mode": mode, "note": "oidc not enabled"}
    jwks = os.getenv("DADI_OIDC_JWKS_URL", "").strip()
    if not jwks:
        raise HTTPException(status_code=500, detail="Missing DADI_OIDC_JWKS_URL")
    r = requests.get(jwks, timeout=5)
    return {"ok": r.ok, "jwks_url": jwks, "status_code": r.status_code}
