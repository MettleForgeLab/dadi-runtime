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

def headers(tenant="tenant_a", scope="artifact:read_bytes"):
    token = make_jwt(JWT_SECRET, {"tenant_id": tenant, "scope": scope, "exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def test_evidence_download_requires_scope_and_sent():
    # Nonexistent should not 500; scope failures should be 403.
    did = "00000000-0000-0000-0000-000000000000"
    eid = "00000000-0000-0000-0000-000000000000"

    r1 = requests.get(f"{API}/deliverables/{did}/evidence/{eid}/download", headers=headers(scope=""), timeout=30)
    assert r1.status_code in (403, 404)

    r2 = requests.get(f"{API}/deliverables/{did}/evidence/{eid}/download", headers=headers(scope="deliverable:evidence_download"), timeout=30)
    assert r2.status_code in (404, 409, 403)
