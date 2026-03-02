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

def test_cache_idempotent_per_tenant():
    token = make_jwt(JWT_SECRET, {"tenant_id":"tenant_a","scope":"artifact:read_bytes","exp": int(time.time()) + 3600})
    headers = {"Authorization": f"Bearer {token}"}

    stage_name = "06_render"
    stage_schema_version = "v1"
    input_sha = "a"*64
    output_sha = "b"*64

    r1 = requests.post(f"{API}/cache/record", json={
        "stage_name": stage_name,
        "stage_schema_version": stage_schema_version,
        "input_sha256": input_sha,
        "output_sha256": output_sha
    }, headers=headers)
    assert r1.status_code in (200, 201)

    r2 = requests.post(f"{API}/cache/record", json={
        "stage_name": stage_name,
        "stage_schema_version": stage_schema_version,
        "input_sha256": input_sha,
        "output_sha256": output_sha
    }, headers=headers)
    assert r2.status_code in (200, 201)

    r3 = requests.get(f"{API}/cache/lookup", params={
        "stage_name": stage_name,
        "stage_schema_version": stage_schema_version,
        "input_sha256": input_sha
    }, headers=headers)
    assert r3.status_code == 200
    assert r3.json().get("hit") is True
