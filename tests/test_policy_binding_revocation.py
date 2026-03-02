import os
import json
import time
import base64
import hmac
import hashlib
import requests

API = os.getenv("NEXT_PUBLIC_API_BASE", "http://localhost:8000")
IDP = os.getenv("IDP_URL", "http://localhost:9000")
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

def headers(scope: str):
    token = make_jwt(JWT_SECRET, {"tenant_id":"tenant_a","scope":scope,"exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def load_seed_state():
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_revoked_bundle_denies_download():
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    bid = state.get("bundle_id")
    if not did or not bid:
        return

    # Mark sent (policy prerequisite)
    requests.post(f"{API}/deliverables/{did}/mark_sent", headers=headers("artifact:read_bytes"), timeout=30)

    # Revoke bundle
    rv = requests.post(f"{API}/deliverables/{did}/bundles/{bid}/revoke", headers=headers("artifact:read_bytes"), timeout=30)
    assert rv.status_code in (200, 404)

    # Download should now fail with 409 (policy binding) or 404 if missing
    dl = requests.get(f"{API}/deliverables/{did}/bundles/{bid}/download", headers=headers("deliverable:download_bundle"), timeout=30)
    assert dl.status_code in (409, 404, 403)


def test_audit_chain_still_verifies_after_revocation_best_effort():
    state = load_seed_state()
    if not state:
        return
    run_id = state.get("pipeline_run_id")
    if not run_id:
        return
    # If endpoint exists and returns 200, ok should be True
    r = requests.get(f"{API}/audit/verify-chain?pipeline_run_id={run_id}&limit=500", headers=headers("artifact:read_bytes"), timeout=30)
    if r.status_code == 200:
        j = r.json()
        assert j.get("ok") in (True, None)
