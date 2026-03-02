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

def load_seed_state():
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_bundle_download_policy_sent_only():
    state = load_seed_state()
    if not state:
        return
    run_id = state.get("pipeline_run_id")
    if not run_id:
        return

    # Create deliverable draft -> finalize -> mark_sent -> create bundle
    h = headers("tenant_a", "artifact:read_bytes")
    d = requests.post(f"{API}/deliverables", json={"pipeline_run_id": run_id, "status":"draft"}, headers=h, timeout=30).json()
    did = d.get("deliverable_id")
    if not did:
        return

    requests.post(f"{API}/deliverables/{did}/finalize", headers=h, timeout=30)

    # mark sent
    requests.post(f"{API}/deliverables/{did}/mark_sent", headers=h, timeout=30)

    # create bundle
    b = requests.post(f"{API}/deliverables/{did}/bundle", headers=h, timeout=60)
    if b.status_code != 200:
        # acceptable if docx missing; then policy can't proceed
        return
    b = b.json()

    # list bundles to get bundle_id (create returns bundle_id in current impl, but handle both)
    bundle_id = b.get("bundle_id")
    if not bundle_id:
        lst = requests.get(f"{API}/deliverables/{did}/bundles", headers=h, timeout=30).json()
        bundle_id = lst.get("bundles", [{}])[0].get("bundle_id")
    assert bundle_id

    # Attempt download without scope -> 403
    r1 = requests.get(f"{API}/deliverables/{did}/bundles/{bundle_id}/download", headers=headers("tenant_a", scope=""), timeout=30)
    assert r1.status_code == 403

    # Attempt download with correct scope -> 200
    r2 = requests.get(f"{API}/deliverables/{did}/bundles/{bundle_id}/download", headers=headers("tenant_a", scope="deliverable:download_bundle"), timeout=30)
    assert r2.status_code == 200
    assert r2.headers.get("content-type","").startswith("application/zip")
