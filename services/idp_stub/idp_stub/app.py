\
from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Optional

import jwt
from fastapi import FastAPI
from pydantic import BaseModel, Field
from cryptography.hazmat.primitives.asymmetric import rsa

app = FastAPI(title="DADI IdP Stub", version="0.1.0")

ISSUER = os.getenv("IDP_ISSUER", "http://idp:9000").rstrip("/")
AUDIENCE = os.getenv("IDP_AUDIENCE", "audience")
TTL = int(os.getenv("IDP_TOKEN_TTL_SECONDS", "3600"))
KID = os.getenv("IDP_KEY_ID", "dev-k1")

# Generate an RSA keypair at startup (dev-only)
_sk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_pk = _sk.public_key()

def _b64url_uint(val: int) -> str:
    raw = val.to_bytes((val.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def jwk() -> Dict[str, Any]:
    numbers = _pk.public_numbers()
    return {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }

@app.get("/.well-known/jwks.json")
def get_jwks():
    return {"keys": [jwk()]}

class TokenRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    scope: str = Field(default="artifact:read_bytes")
    sub: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    ttl_seconds: Optional[int] = None

@app.post("/token")
def issue_token(req: TokenRequest):
    now = int(time.time())
    ttl = int(req.ttl_seconds) if req.ttl_seconds is not None else TTL
    iss = (req.iss or ISSUER).rstrip("/")
    aud = req.aud or AUDIENCE

    payload = {
        "iss": iss,
        "aud": aud,
        "exp": now + ttl,
        "iat": now,
        "tenant_id": req.tenant_id,
        "scope": req.scope,
    }
    if req.sub:
        payload["sub"] = req.sub

    token = jwt.encode(payload, _sk, algorithm="RS256", headers={"kid": KID})
    return {"access_token": token, "token_type": "Bearer", "expires_in": ttl, "issuer": iss, "audience": aud, "kid": KID}
