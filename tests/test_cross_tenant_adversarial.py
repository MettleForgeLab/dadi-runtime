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

def auth_headers(tenant: str, scope: str = "artifact:read_bytes"):
    token = make_jwt(JWT_SECRET, {"tenant_id": tenant, "scope": scope, "exp": int(time.time()) + 3600})
    return {"Authorization": f"Bearer {token}"}

def load_seed_state():
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / ".seed_state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def test_cross_tenant_artifact_metadata_denied_by_isolation():
    state = load_seed_state()
    if not state:
        return
    doc_sha = state.get("docpack_sha_a")
    if not doc_sha:
        return

    # tenant_b should not see tenant_a artifact; expect 404
    r = requests.get(f"{API}/artifacts/{doc_sha}", headers=auth_headers("tenant_b"), timeout=30)
    assert r.status_code == 404

def test_cross_tenant_manifest_verify_denied():
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    msha = state.get("manifest_artifact_sha256")
    if not did or not msha:
        return

    # tenant_b attempts to verify tenant_a manifest -> should be 403 (tenant mismatch) or 404 (can't read manifest bytes)
    r = requests.post(
        f"{API}/deliverables/{did}/bundle/verify",
        json={"manifest_artifact_sha256": msha},
        headers=auth_headers("tenant_b"),
        timeout=30
    )
    assert r.status_code in (403, 404)

def test_cross_tenant_bundle_create_denied():
    state = load_seed_state()
    if not state:
        return
    did = state.get("deliverable_id")
    if not did:
        return

    # tenant_b should not be able to create a bundle for tenant_a deliverable; expect 404
    r = requests.post(f"{API}/deliverables/{did}/bundle", headers=auth_headers("tenant_b"), timeout=30)
    assert r.status_code == 404

def test_content_endpoint_scope_required():
    state = load_seed_state()
    if not state:
        return
    # Use a known artifact hash from tenant_a if present
    bsha = state.get("bundle_artifact_sha256") or state.get("docpack_sha_a")
    if not bsha:
        return

    # Same tenant but no scope should get 403 if artifact exists; if not found, 404 acceptable.
    r = requests.get(f"{API}/artifacts/{bsha}/content", headers=auth_headers("tenant_a", scope=""), timeout=30)
    assert r.status_code in (403, 404)
