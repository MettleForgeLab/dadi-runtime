import os
import time
import json
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

def test_deliverables_endpoints_smoke():
    token = make_jwt(JWT_SECRET, {"tenant_id":"tenant_a","scope":"artifact:read_bytes","exp": int(time.time()) + 3600})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt create with a likely-nonexistent run; should 404 or 422 depending on DB state
    r = requests.post(f"{API}/deliverables", json={"pipeline_run_id":"00000000-0000-0000-0000-000000000000"}, headers=headers)
    assert r.status_code in (404, 422, 400)
