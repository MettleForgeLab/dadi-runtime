import os
import json
import time
import base64
import hmac
import hashlib
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")
JWT_SECRET = os.getenv("DADI_JWT_HS256_SECRET", "dev-secret")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def make_jwt(secret: str, payload: dict) -> str:
    header = {"alg":"HS256","typ":"JWT"}
    h = b64url(json.dumps(header, separators=(",",":"), sort_keys=True).encode("utf-8"))
    p = b64url(json.dumps(payload, separators=(",",":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = b64url(sig)
    return f"{h}.{p}.{s}"

def headers(scope="artifact:read_bytes"):
    token = make_jwt(JWT_SECRET, {"tenant_id":"tenant_a","scope":scope,"exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def test_revoke_endpoints_smoke():
    did = "00000000-0000-0000-0000-000000000000"
    bid = "00000000-0000-0000-0000-000000000000"
    eid = "00000000-0000-0000-0000-000000000000"
    r1 = requests.post(f"{API}/deliverables/{did}/bundles/{bid}/revoke", headers=headers(), timeout=30)
    assert r1.status_code in (404, 401, 403)
    r2 = requests.post(f"{API}/deliverables/{did}/evidence/{eid}/revoke", headers=headers(), timeout=30)
    assert r2.status_code in (404, 401, 403)
